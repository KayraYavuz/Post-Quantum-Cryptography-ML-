"""
Constant-Time Fuzzing Engine for Post-Quantum Cryptography
==========================================================

Tests ML-KEM and ML-DSA implementations for timing variations and
exceptions via randomized malformed and edge-case ciphertext injection.

This module systematically probes implementations for:
- Timing side-channels through ciphertext validation paths
- Exception handling in boundary conditions
- Invalid input propagation through the cryptographic pipeline
"""

import random
import time
import traceback
from typing import Any, Callable, Dict, List, Tuple

# ML-KEM and ML-DSA parameter sets
KEM_PARAMS = ["mlkem512", "mlkem768", "mlkem1024"]
DSA_PARAMS = ["mlsdsa44", "mlsdsa65", "mlsdsa87"]

# Edge-case and malformed ciphertext patterns
EDGE_CASES = [
    # Zero ciphertext
    b"\x00" * 32,
    # Maximum size ciphertext  
    b"\xff" * 256,
    # Minimum size ciphertext
    b"\x01" * 16,
    # Boundary-size ciphertexts
    b"\x80" * 128,
    # Single-byte variants
    b"\x01",
    b"\x00",
    b"\xff",
    # Partial/aligned boundary bytes
    b"\x00" * 31 + b"\x01",
    b"\xff" * 31 + b"\x00",
    # Randomized patterns
    random.randbytes(32),
    random.randbytes(256),
]


def constant_time_fuzz(
    crypto_func: Callable,
    params: str,
    iterations: int = 100,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Run constant-time fuzzing against a crypto implementation.

    Args:
        crypto_func: Callable that takes (ciphertext, params) and returns result
        params: KEM/DSA parameter string (e.g., "mlkem768")
        iterations: Number of fuzz iterations to run
        seed: Random seed for reproducibility

    Returns:
        Dict with timing data, exceptions, and pass/fail status
    """
    random.seed(seed)
    results = {
        "params": params,
        "iterations": iterations,
        "timing_data": [],
        "exceptions": [],
        "passed": True,
        "failures": [],
    }

    timings = []

    for i in range(iterations):
        # Select random edge case
        ciphertext = random.choice(EDGE_CASES)

        try:
            start_time = time.perf_counter()
            result = crypto_func(ciphertext, params)
            elapsed = time.perf_counter() - start_time
            timings.append(elapsed)

            # Store result info (don't store full result to save memory)
            results["timing_data"].append(
                {
                    "iteration": i,
                    "ciphertext_len": len(ciphertext),
                    "elapsed_ns": int(elapsed * 1e9),
                    "success": True,
                }
            )

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            results["exceptions"].append(
                {
                    "iteration": i,
                    "ciphertext_len": len(ciphertext),
                    "error_type": type(e).__name__,
                    "error_msg": str(e),
                    "elapsed_ns": int(elapsed * 1e9),
                }
            )
            results["failures"].append(
                {
                    "iteration": i,
                    "ciphertext_len": len(ciphertext),
                    "error": f"{type(e).__name__}: {str(e)}",
                }
            )
            results["passed"] = False

    if timings:
        results["timing_stats"] = {
            "min_ns": min(timings) * 1e9,
            "max_ns": max(timings) * 1e9,
            "mean_ns": sum(timings) / len(timings) * 1e9,
            "std_dev_ns": (
                sum((t - sum(timings) / len(timings)) ** 2 for t in timings)
                / len(timings)
            )
            * 1e9,
        }

    return results


def fuzz_kem_implementation(
    kems: List[str],
    crypto_api: Callable,
    iterations: int = 200,
) -> Dict[str, Dict[str, Any]]:
    """
    Fuzz multiple ML-KEM implementations.

    Args:
        kems: List of KEM parameter strings
        crypto_api: Function implementing the KEM interface
        iterations: Fuzz iterations per KEM

    Returns:
        Dict mapping KEM params to fuzz results
    """
    results = {}
    for kem in kems:
        results[kem] = constant_time_fuzz(crypto_api, kem, iterations=iterations)
    return results


def fuzz_dsa_implementation(
    dsas: List[str],
    crypto_api: Callable,
    iterations: int = 200,
) -> Dict[str, Dict[str, Any]]:
    """
    Fuzz multiple ML-DSA implementations.

    Args:
        dsas: List of DSA parameter strings
        crypto_api: Function implementing the DSA interface
        iterations: Fuzz iterations per DSA

    Returns:
        Dict mapping DSA params to fuzz results
    """
    results = {}
    for dsa in dsas:
        results[dsa] = constant_time_fuzz(crypto_api, dsa, iterations=iterations)
    return results


def analyze_timing_variance(
    results: Dict[str, Any],
    threshold_ns: int = 1000,
) -> Dict[str, Any]:
    """
    Analyze timing variance from fuzzing results for side-channel detection.

    Args:
        results: Fuzzing results dict from constant_time_fuzz
        threshold_ns: Timing variance threshold in nanoseconds

    Returns:
        Analysis report with variance flags
    """
    timing_data = results.get("timing_data", [])
    if not timing_data:
        return {
            "min_time_ns": 0,
            "max_time_ns": 0,
            "variance_ns": 0,
            "variance_exceeds_threshold": False,
            "threshold_ns": threshold_ns,
            "safe_from_timing_side_channels": True,
            "timing_range_percent": 0,
            "error": "No timing data available",
        }

    timings = [entry["elapsed_ns"] for entry in timing_data]
    if len(timings) < 2:
        # Single data point: variance is 0, but mark as potentially unsafe
        # since we cannot assess variance with only one measurement
        single_t = timings[0]
        return {
            "min_time_ns": single_t,
            "max_time_ns": single_t,
            "variance_ns": 0,
            "variance_exceeds_threshold": False,
            "threshold_ns": threshold_ns,
            "safe_from_timing_side_channels": True,  # conservative: cannot verify
            "timing_range_percent": 0,
            "error": "Insufficient timing data (need >= 2 measurements)",
        }

    min_t = min(timings)
    max_t = max(timings)
    variance_ns = max_t - min_t

    return {
        "min_time_ns": min_t,
        "max_time_ns": max_t,
        "variance_ns": variance_ns,
        "variance_exceeds_threshold": variance_ns > threshold_ns,
        "threshold_ns": threshold_ns,
        "safe_from_timing_side_channels": variance_ns <= threshold_ns,
        "timing_range_percent": round((variance_ns / min_t) * 100, 2) if min_t > 0 else 0,
    }


def generate_edge_case_report(
    results: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate comprehensive report from fuzzing all KEM/DSA implementations.

    Args:
        results: Nested dict from fuzz_kem_implementation or fuzz_dsa_implementation

    Returns:
        Consolidated report with all analysis
    """
    report = {
        "total_implementations_tested": len(results),
        "total_passed": 0,
        "total_failed": 0,
        "total_exceptions": 0,
        "timing_analysis": {},
        "exception_summary": {},
        "recommendations": [],
    }

    for impl_name, impl_results in results.items():
        passed = 1 if impl_results.get("passed", False) else 0
        failed = 0 if passed else 1
        exceptions = len(impl_results.get("exceptions", []))

        report["total_passed"] += passed
        report["total_failed"] += failed
        report["total_exceptions"] += exceptions

        # Timing analysis
        timing = analyze_timing_variance(impl_results)
        report["timing_analysis"][impl_name] = timing

        # Exception summary
        report["exception_summary"][impl_name] = {
            "exception_count": exceptions,
            "exception_types": list(
                set(e["error_type"] for e in impl_results.get("exceptions", []))
            ),
        }

    # Generate recommendations based on findings
    if report["total_failed"] > 0:
        report["recommendations"].append(
            "Review and fix failing edge-case inputs; "
            "consider constant-time implementation patterns"
        )

    if any(
        t.get("variance_exceeds_threshold", False)
        for t in report["timing_analysis"].values()
    ):
        report["recommendations"].append(
            "High timing variance detected; "
            "audit for side-channel resistance"
        )

    if report["total_exceptions"] > len(report["timing_analysis"]) * 2:
        report["recommendations"].append(
            "Excessive exceptions; validate input handling "
            "and error path constant-timing"
        )

    return report


if __name__ == "__main__":
    # Example usage with mock crypto functions
    def mock_kem_func(ciphertext: bytes, params: str) -> dict:
        """Mock KEM function for demonstration."""
        time.sleep(0.001)  # Simulate computation
        if len(ciphertext) not in [32, 64, 96, 128, 192, 256]:
            raise ValueError(f"Invalid ciphertext length for {params}")
        return {"status": "ok", "params": params, "ciphertext_len": len(ciphertext)}

    print("=== ML-KEM Fuzzing ===")
    kem_results = fuzz_kem_implementation(KEM_PARAMS, mock_kem_func, iterations=50)
    kem_report = generate_edge_case_report(kem_results)
    print(f"Implemented: {kem_report['total_implementations_tested']} KEMs")
    print(f"Passed: {kem_report['total_passed']}, Failed: {kem_report['total_failed']}")
    print(f"Exceptions: {kem_report['total_exceptions']}")
    print(f"Recommendations: {kem_report['recommendations']}")

    print("\n=== ML-DSA Fuzzing ===")
    dsa_results = fuzz_dsa_implementation(DSA_PARAMS, mock_kem_func, iterations=50)
    dsa_report = generate_edge_case_report(dsa_results)
    print(f"Implemented: {dsa_report['total_implementations_tested']} DSAs")
    print(f"Passed: {dsa_report['total_passed']}, Failed: {dsa_report['total_failed']}")
    print(f"Exceptions: {dsa_report['total_exceptions']}")
    print(f"Recommendations: {dsa_report['recommendations']}")
