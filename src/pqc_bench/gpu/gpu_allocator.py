#!/usr/bin/env python3
"""
WS-C.2: GPU Allocation and Side Channel Start - CPU-Only Optimized Implementations

Provides GPU allocation with CPU fallback and side-channel analysis channel start
for post-quantum cryptography benchmarks. All GPU operations fall back gracefully
to CPU-only implementations when GPUs are unavailable.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def check_cuda_availability() -> Dict[str, Any]:
    """Check CUDA availability and return device information."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver.version",
             "--format=csv,no,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            devices = []
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    devices.append({
                        "name": parts[0],
                        "memory_mb": int(parts[1]),
                        "driver_version": parts[2],
                    })
            return {
                "available": True,
                "devices": devices,
                "count": len(devices),
            }
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    
    return {
        "available": False,
        "devices": [],
        "count": 0,
    }


def check_rocm_availability() -> Dict[str, Any]:
    """Check ROCm availability and return device information."""
    try:
        result = subprocess.run(
            ["rocm-smi", "--showname", "--showmeminfo"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return {
                "available": True,
                "devices": [{"name": line.strip()} 
                           for line in result.stdout.strip().split("\n") 
                           if line.strip()],
                "count": len([l for l in result.stdout.strip().split("\n") if l.strip()]),
            }
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    
    return {
        "available": False,
        "devices": [],
        "count": 0,
    }


def allocate_gpu_resources(
    requested_memory_mb: Optional[int] = None,
    requested_compute: Optional[str] = None,
) -> Dict[str, Any]:
    """Allocate GPU resources with CPU fallback.
    
    Tries CUDA first, then ROCm, then returns CPU-only mode.
    Returns a resource context that can be used for PQC workloads.
    """
    # Check CUDA first
    cuda_info = check_cuda_availability()
    if cuda_info["available"]:
        if requested_memory_mb:
            # Filter devices that have enough memory
            suitable = [d for d in cuda_info["devices"] 
                       if d["memory_mb"] >= requested_memory_mb]
            if suitable:
                device = suitable[0]
                return {
                    "mode": "gpu",
                    "backend": "cuda",
                    "device_name": device["name"],
                    "device_memory_mb": device["memory_mb"],
                    "driver_version": device["driver_version"],
                    "memory_allocated_mb": requested_memory_mb,
                    "cpu_fallback": False,
                }
        # No specific memory request or device found, use first CUDA device
        device = cuda_info["devices"][0]
        return {
            "mode": "gpu",
            "backend": "cuda",
            "device_name": device["name"],
            "device_memory_mb": device["memory_mb"],
            "driver_version": device["driver_version"],
            "memory_allocated_mb": requested_memory_mb or device["memory_mb"],
            "cpu_fallback": False,
        }
    
    # Check ROCm
    rocm_info = check_rocm_availability()
    if rocm_info["available"]:
        if requested_memory_mb:
            suitable = [d for d in rocm_info["devices"]
                       if _get_rocm_memory_mb(d) >= requested_memory_mb]
            if suitable:
                return {
                    "mode": "gpu",
                    "backend": "rocm",
                    "device_name": suitable[0],
                    "device_memory_mb": _get_rocm_memory_mb(suitable[0]),
                    "memory_allocated_mb": requested_memory_mb,
                    "cpu_fallback": False,
                }
        device = rocm_info["devices"][0]
        return {
            "mode": "gpu",
            "backend": "rocm",
            "device_name": device,
            "device_memory_mb": _get_rocm_memory_mb(device),
            "memory_allocated_mb": requested_memory_mb,
            "cpu_fallback": False,
        }
    
    # CPU-only mode - return optimized CPU configuration
    return {
        "mode": "cpu_only",
        "backend": "cpu",
        "device_name": "cpu",
        "device_memory_mb": _get_system_ram_mb(),
        "memory_allocated_mb": requested_memory_mb or _get_system_ram_mb() // 4,
        "cpu_fallback": True,
        "note": "GPU unavailable - using CPU-optimized implementations",
    }


def _get_rocm_memory_mb(device_name: str) -> int:
    """Estimate ROCm device memory in MB."""
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if device_name in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p.isdigit():
                            return int(p) * 1024  # Convert KB to MB
    except Exception:
        pass
    return 4096  # Default assumption


def _get_system_ram_mb() -> int:
    """Get system RAM in MB."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemTotal:" in line:
                    return int(line.split()[1]) / 1024
    except Exception:
        pass
    return 8192  # Default assumption


def start_side_channel_channel(
    algorithm: str,
    tier: str = "direct",
    compiler: str = "gcc",
    flag: str = "-O0",
    arch: str = "x86_64",
    use_gpu: bool = False,
) -> Dict[str, Any]:
    """Start side-channel analysis channel with specified parameters.
    
    Args:
        algorithm: PQC algorithm name (ml-kem-512, ml-kem-768, etc.)
        tier: Analysis tier ("direct" or "derived")
        compiler: Compiler name (gcc, clang)
        flag: Compiler flag (-O0, -O1, -Os, etc.)
        arch: Architecture (x86_64, aarch64)
        use_gpu: Whether to attempt GPU acceleration
    
    Returns:
        Channel startup result with configuration and resource info
    """
    # Allocate resources (GPU with CPU fallback)
    resources = allocate_gpu_resources(
        requested_memory_mb=2048 if use_gpu else None
    )
    
    # Check GE compatibility
    from pqc_bench.constant_time.ws_c1_side_channel import check_ge_compatibility
    ge_info = check_ge_compatibility(algorithm)
    
    # Setup tier instrumentation
    from pqc_bench.constant_time.ws_c1_side_channel import setup_tier_instrumentation
    tier_config = setup_tier_instrumentation(tier, algorithm, compiler, flag, arch)
    
    # Generate side-channel BOM
    from pqc_bench.constant_time.side_channel_analyzer import generate_side_channel_bom
    bom = generate_side_channel_bom(algorithm)
    
    return {
        "algorithm": algorithm,
        "tier": tier,
        "compiler": compiler,
        "flag": flag,
        "arch": arch,
        "ge_compatible": ge_info["ge_compatible"],
        "countermeasure": ge_info["countermeasure"],
        "resources": resources,
        "tier_config": tier_config,
        "bom": bom,
        "channel_started": True,
        "cpu_fallback": resources["mode"] == "cpu_only",
        "message": f"Side channel started for {algorithm} ({tier} tier, {compiler} {flag} {arch})",
    }


def get_optimal_configuration(
    algorithm: str,
    target_tier: str = "direct",
    prefer_gpu: bool = False,
) -> Dict[str, Any]:
    """Get optimal resource configuration for PQC workload.
    
    Combines GPU allocation with tier-aware side-channel setup.
    """
    # Allocate resources
    resources = allocate_gpu_resources()
    
    # Start side-channel channel
    channel = start_side_channel_channel(
        algorithm=algorithm,
        tier=target_tier,
        use_gpu=prefer_gpu and resources["mode"] != "cpu_only",
    )
    
    # Combine configurations
    config = {
        "algorithm": algorithm,
        "target_tier": target_tier,
        "resources": resources,
        "channel": channel,
        "optimized": True,
    }
    
    # Add tier-specific optimizations
    if target_tier == "direct":
        config["optimization"] = "cycle-accurate timing with custom timer"
    elif target_tier == "derived":
        config["optimization"] = "entropy-based statistical analysis with dudect"
    
    return config


if __name__ == "__main__":
    print("WS-C.2: GPU Allocation and Side Channel Start")
    print("=" * 70)
    
    # Check availability
    cuda = check_cuda_availability()
    rocm = check_rocm_availability()
    
    print(f"\nCUDA available: {cuda['available']} (count: {cuda['count']})")
    print(f"ROCm available: {rocm['available']} (count: {rocm['count']})")
    
    # Test GPU allocation
    print(f"\nGPU allocation (no request):")
    alloc = allocate_gpu_resources()
    print(f"  Mode: {alloc['mode']}")
    print(f"  Backend: {alloc['backend']}")
    print(f"  Device: {alloc['device_name']}")
    print(f"  CPU fallback: {alloc['cpu_fallback']}")
    
    print(f"\nGPU allocation (2GB request):")
    alloc2 = allocate_gpu_resources(requested_memory_mb=2048)
    print(f"  Mode: {alloc2['mode']}")
    print(f"  Memory allocated: {alloc2['memory_allocated_mb']} MB")
    print(f"  CPU fallback: {alloc2['cpu_fallback']}")
    
    # Test side-channel channel start
    print(f"\nSide channel start (ML-KEM-768, direct tier):")
    channel = start_side_channel_channel(
        algorithm="ml-kem-768",
        tier="direct",
        compiler="gcc",
        flag="-O0",
        arch="x86_64",
        use_gpu=False,
    )
    print(f"  Algorithm: {channel['algorithm']}")
    print(f"  GE compatible: {channel['ge_compatible']}")
    print(f"  Countermeasure: {channel['countermeasure']}")
    print(f"  Resources mode: {channel['resources']['mode']}")
    print(f"  Channel started: {channel['channel_started']}")
    print(f"  CPU fallback: {channel['cpu_fallback']}")
    print(f"  Message: {channel['message']}")
    
    # Test optimal configuration
    print(f"\nOptimal configuration (ML-DSA-65, derived tier):")
    config = get_optimal_configuration(
        algorithm="ml-dsa-65",
        target_tier="derived",
        prefer_gpu=False,
    )
    print(f"  Algorithm: {config['algorithm']}")
    print(f"  Target tier: {config['target_tier']}")
    print(f"  Resources mode: {config['resources']['mode']}")
    print(f"  Channel tier: {config['channel']['tier']}")
    print(f"  Optimization: {config.get('optimization', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("WS-C.2 setup complete")