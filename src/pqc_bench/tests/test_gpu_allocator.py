"""WS-C.2: GPU Allocation and Side Channel Start unit tests.

Tests for the GPU allocation module with CPU fallback and side-channel
analysis channel startup for PQC benchmarks.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pqc_bench.gpu.gpu_allocator import (
    allocate_gpu_resources,
    start_side_channel_channel,
    get_optimal_configuration,
    check_cuda_availability,
    check_rocm_availability,
)


def test_check_cuda_availability():
    """Test CUDA availability checking."""
    result = check_cuda_availability()
    assert "available" in result
    assert "devices" in result
    assert "count" in result
    print("✓ CUDA availability test passed")


def test_check_rocm_availability():
    """Test ROCm availability checking."""
    result = check_rocm_availability()
    assert "available" in result
    assert "devices" in result
    assert "count" in result
    print("✓ ROCm availability test passed")


def test_allocate_gpu_resources_no_request():
    """Test GPU allocation without specific request."""
    result = allocate_gpu_resources()
    assert "mode" in result
    assert "backend" in result
    assert "device_name" in result
    assert "cpu_fallback" in result
    # Should fall back to CPU since no GPU available
    assert result["cpu_fallback"] is True
    assert result["mode"] == "cpu_only"
    print("✓ GPU allocation (no request) test passed")


def test_allocate_gpu_resources_with_request():
    """Test GPU allocation with memory request."""
    result = allocate_gpu_resources(requested_memory_mb=2048)
    assert "mode" in result
    assert "memory_allocated_mb" in result
    assert result["memory_allocated_mb"] == 2048
    # Should fall back to CPU since no GPU available
    assert result["cpu_fallback"] is True
    print("✓ GPU allocation (with request) test passed")


def test_start_side_channel_channel():
    """Test side-channel channel startup."""
    result = start_side_channel_channel(
        algorithm="ml-kem-768",
        tier="direct",
        compiler="gcc",
        flag="-O0",
        arch="x86_64",
        use_gpu=False,
    )
    assert "algorithm" in result
    assert "tier" in result
    assert "compiler" in result
    assert "flag" in result
    assert "arch" in result
    assert "ge_compatible" in result
    assert "countermeasure" in result
    assert "resources" in result
    assert "channel_started" in result
    assert "cpu_fallback" in result
    assert result["ge_compatible"] is True
    assert result["countermeasure"] == "masking"
    assert result["channel_started"] is True
    assert result["cpu_fallback"] is True
    print("✓ Side channel channel start test passed")


def test_start_side_channel_channel_with_gpu():
    """Test side-channel channel startup with GPU request."""
    result = start_side_channel_channel(
        algorithm="ml-kem-768",
        tier="direct",
        compiler="gcc",
        flag="-O0",
        arch="x86_64",
        use_gpu=True,
    )
    assert result["cpu_fallback"] is True  # Falls back since no GPU
    print("✓ Side channel channel start with GPU test passed")


def test_get_optimal_configuration():
    """Test optimal configuration generation."""
    config = get_optimal_configuration(
        algorithm="ml-dsa-65",
        target_tier="derived",
        prefer_gpu=False,
    )
    assert "algorithm" in config
    assert "target_tier" in config
    assert "resources" in config
    assert "channel" in config
    assert config["target_tier"] == "derived"
    assert config["channel"]["tier"] == "derived"
    assert "optimization" in config
    assert "entropy-based" in config["optimization"].lower()
    print("✓ Optimal configuration test passed")


def test_get_optimal_configuration_direct():
    """Test optimal configuration with direct tier."""
    config = get_optimal_configuration(
        algorithm="ml-kem-768",
        target_tier="direct",
        prefer_gpu=False,
    )
    assert config["target_tier"] == "direct"
    assert "cycle-accurate" in config["optimization"].lower()
    print("✓ Optimal configuration (direct) test passed")


def test_get_optimal_configuration_gpu_preference():
    """Test optimal configuration with GPU preference (falls back to CPU)."""
    config = get_optimal_configuration(
        algorithm="ml-kem-768",
        target_tier="direct",
        prefer_gpu=True,
    )
    # Should still fall back to CPU since no GPU available
    assert config["resources"]["mode"] == "cpu_only"
    print("✓ Optimal configuration (GPU preference) test passed")


if __name__ == "__main__":
    print("Running WS-C.2 unit tests...")
    print("=" * 60)
    
    test_check_cuda_availability()
    test_check_rocm_availability()
    test_allocate_gpu_resources_no_request()
    test_allocate_gpu_resources_with_request()
    test_start_side_channel_channel()
    test_start_side_channel_channel_with_gpu()
    test_get_optimal_configuration()
    test_get_optimal_configuration_direct()
    test_get_optimal_configuration_gpu_preference()
    
    print("=" * 60)
    print("All WS-C.2 tests passed!")
