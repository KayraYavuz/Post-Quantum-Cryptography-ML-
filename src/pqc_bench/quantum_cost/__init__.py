"""Quantum resource estimation for PQC algorithms.

Provides quantum cost analysis using AQRE (Approximate Quantum Resource Estimator)
and Qualtran (quantum circuit synthesis) toolchains for post-quantum cryptography
parameter evaluation.

Supports ML-KEM (Kyber), ML-DSA (Dilithium), and SLH-DSA parameter sets.
"""

from __future__ import annotations

import json
import subprocess
import sys
import warnings
from typing import Any

# Known quantum resource estimates for ML-KEM schemes
# These are placeholders; real values come from AQRE/Qualtran runs
ML_KEM_QUANTUM_RESOURCES: dict[str, dict[str, Any]] = {
    "ml-kem-512": {
        "n": 256,
        "q": 3329,
        "logical_qubits": 2361,
        "t_gate_count": 1707050,
        "t_depth": 3414100,
        "physical_qubits": 4740480,
        "surface_code_distance": 67,
        "runtime_seconds": 3600,
        "description": "Kyber-512 quantum resource estimate",
    },
    "ml-kem-768": {
        "n": 512,
        "q": 3329,
        "logical_qubits": 4215,
        "t_gate_count": 5474000,
        "t_depth": 10948000,
        "physical_qubits": 13459200,
        "surface_code_distance": 101,
        "runtime_seconds": 14400,
        "description": "Kyber-768 quantum resource estimate",
    },
    "ml-kem-1024": {
        "n": 1024,
        "q": 3329,
        "logical_qubits": 7281,
        "t_gate_count": 11536000,
        "t_depth": 23072000,
        "physical_qubits": 27852800,
        "surface_code_distance": 133,
        "runtime_seconds": 28800,
        "description": "Kyber-1024 quantum resource estimate",
    },
}


def get_ml_kem_resources(scheme: str) -> dict[str, Any]:
    """Get quantum resource estimates for an ML-KEM scheme.

    Args:
        scheme: ML-KEM scheme identifier (e.g., "ML-KEM-768", "ml-kem-768").

    Returns:
        Dictionary with quantum resource estimates.
    """
    key = scheme.lower()
    if key in ML_KEM_QUANTUM_RESOURCES:
        return ML_KEM_QUANTUM_RESOURCES[key]
    # Try partial match
    for k, v in ML_KEM_QUANTUM_RESOURCES.items():
        if k.startswith(key) or key.startswith(k):
            return v
    raise ValueError(f"Unknown ML-KEM scheme: {scheme}")


def estimate_quantum_resources(scheme: str) -> dict[str, Any]:
    """Estimate quantum resources for an ML-KEM scheme.

    Args:
        scheme: ML-KEM scheme identifier.

    Returns:
        Dictionary with logical qubits, T-gate count, depth, and physical resources.
    """
    params = get_ml_kem_resources(scheme)

    return {
        "scheme": scheme,
        "n": params["n"],
        "q": params["q"],
        "logical_qubits": params["logical_qubits"],
        "t_gate_count": params["t_gate_count"],
        "t_depth": params["t_depth"],
        "physical_qubits": params["physical_qubits"],
        "surface_code_distance": params["surface_code_distance"],
        "runtime_seconds": params["runtime_seconds"],
        "description": params["description"],
    }


def quantum_resource_summary(scheme: str) -> str:
    """Generate a human-readable summary of quantum resource costs.

    Args:
        scheme: ML-KEM scheme identifier.

    Returns:
        Formatted string with quantum resource analysis.
    """
    est = estimate_quantum_resources(scheme)

    lines = [
        f"Quantum Resource Estimation for {est['scheme']}",
        "=" * 55,
        f"Parameters: n={est['n']}, q={est['q']}",
        f"",
        f"Logical Qubits:    {est['logical_qubits']:,}",
        f"T-Gate Count:      {est['t_gate_count']:,}",
        f"T-Gate Depth:      {est['t_depth']:,}",
        f"",
        f"Physical Resources:",
        f"  Physical Qubits: {est['physical_qubits']:,}",
        f"  Surface Code D:  {est['surface_code_distance']}",
        f"",
        f"Runtime Estimate:  {est['runtime_seconds']:,}s ({est['runtime_seconds']/3600:.1f}h)",
        f"",
        f"Description: {est['description']}",
    ]

    return "\n".join(lines)


def run_aqre_estimation(scheme: str, timeout_seconds: int = 300) -> dict[str, Any]:
    """Run AQRE (Approximate Quantum Resource Estimator) for a scheme.

    Args:
        scheme: ML-KEM scheme identifier.
        timeout_seconds: Maximum time to wait for AQRE to complete.

    Returns:
        Estimation results from AQRE or fallback values.
    """
    try:
        # Try to locate AQRE
        result = subprocess.run(
            ["aqre", "estimate", scheme],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if result.returncode == 0:
            # Try to parse JSON output
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback to internal estimation
    warnings.warn(f"AQRE not available for {scheme}, using internal estimates")
    return estimate_quantum_resources(scheme)


def run_qualtran_estimation(scheme: str, timeout_seconds: int = 300) -> dict[str, Any]:
    """Run Qualtran (quantum circuit synthesis) for a scheme.

    Args:
        scheme: ML-KEM scheme identifier.
        timeout_seconds: Maximum time to wait for Qualtran to complete.

    Returns:
        Estimation results from Qualtran or fallback values.
    """
    try:
        # Try to locate Qualtran
        result = subprocess.run(
            ["qualtran", "estimate", scheme],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if result.returncode == 0:
            # Try to parse output
            try:
                return {"source": "qualtran", "result": result.stdout}
            except Exception:
                pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback to internal estimation
    warnings.warn(f"Qualtran not available for {scheme}, using internal estimates")
    return estimate_quantum_resources(scheme)


def main() -> int:
    """Main entry point for quantum resource estimation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Quantum resource estimation for ML-KEM schemes"
    )
    parser.add_argument(
        "scheme",
        help="ML-KEM scheme (e.g., ML-KEM-768, ml-kem-768)",
    )
    parser.add_argument(
        "--method",
        choices=["aqre", "qualtran", "internal"],
        default="internal",
        help="Estimation method to use",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        default=False,
        help="Output human-readable summary",
    )

    args = parser.parse_args()

    try:
        if args.method == "aqre":
            result = run_aqre_estimation(args.scheme)
        elif args.method == "qualtran":
            result = run_qualtran_estimation(args.scheme)
        else:
            result = estimate_quantum_resources(args.scheme)

        if args.json:
            print(json.dumps(result, indent=2))
        elif args.summary:
            print(quantum_resource_summary(args.scheme))
        else:
            r = result
            print(f"Scheme: {r['scheme']}")
            print(f"  Logical qubits: {r['logical_qubits']:,}")
            print(f"  T-gate count:   {r['t_gate_count']:,}")
            print(f"  T-gate depth:   {r['t_depth']:,}")
            print(f"  Physical qubits: {r['physical_qubits']:,}")
            print(f"  Surface code dist: {r['surface_code_distance']}")
            print(f"  Runtime: {r['runtime_seconds']:,}s")

        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())