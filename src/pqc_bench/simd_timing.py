"""Synthetic SIMD-labelled timing statistics; not a hardware benchmark.

All cycle values are uncalibrated modeled units. No SIMD NTT kernel is run,
no CVE is reproduced, and no constant-time or architecture security conclusion
can be drawn from these distributions. Register widths are metadata only.
"""
from __future__ import annotations

import math
from numbers import Integral, Real

import numpy as np

AVX2_SIMD_WIDTH = 256
AVX2_ELEMENTS_PER_REG = 8
AVX512_SIMD_WIDTH = 512
AVX512_ELEMENTS_PER_REG = 16
NEON_SIMD_WIDTH = 128
NEON_ELEMENTS_PER_REG = 4
MLKEM_N = 256
MLKEM_Q = 3329
MLKEM_ROOT_OF_UNITY = 17

LIMITATION = (
    "Synthetic, uncalibrated modeled cycle units only; no hardware measurement. "
    "Lower modeled variance does not prove constant-time behavior or greater "
    "architecture security. SIMD width alone provides no such guarantee."
)


def _count(value: int, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return int(value)


def _simulate(architecture: str, width: int, base: float, low: int,
              high: int, divisor: int, n_samples: int, n_iterations: int) -> dict:
    n_samples = _count(n_samples, "n_samples", 1, 65536)
    n_iterations = _count(n_iterations, "n_iterations", 2, 1000000)
    # Arbitrary reproducible scenario parameters, not processor latency data.
    rng = np.random.default_rng(42)
    scale = n_samples / MLKEM_N
    values = (base + rng.integers(low, high, n_iterations) // divisor) * scale
    return {
        "mean_cycles": float(np.mean(values)),
        "std_cycles": float(np.std(values, ddof=1)),
        "min_cycles": float(np.min(values)),
        "max_cycles": float(np.max(values)),
        "timing_variance": float(np.var(values, ddof=1)),
        "architecture": architecture,
        "elements_per_operation": width,
        "n_samples": n_samples,
        "n_iterations": n_iterations,
        "source": "synthetic",
        "units": "uncalibrated modeled cycles",
        "limitation": LIMITATION,
    }


def simulate_avx2_ntt_timing(n_samples: int = MLKEM_N,
                             n_iterations: int = 1000) -> dict:
    """Generate an AVX2-labelled synthetic scenario; scale linearly by sample count."""
    return _simulate("AVX2", 8, 42, 12, 43, 4, n_samples, n_iterations)


def simulate_avx512_ntt_timing(n_samples: int = MLKEM_N,
                               n_iterations: int = 1000) -> dict:
    """Generate an AVX-512-labelled synthetic scenario, not an NTT benchmark."""
    return _simulate("AVX-512", 16, 30, 12, 35, 1, n_samples, n_iterations)


def simulate_neon_ntt_timing(n_samples: int = MLKEM_N,
                             n_iterations: int = 1000) -> dict:
    """Generate an ARM NEON-labelled synthetic scenario, not an NTT benchmark."""
    return _simulate("ARM NEON", 4, 55, 20, 60, 1, n_samples, n_iterations)


def _finite_nonnegative(data: dict, key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{key} must be a finite nonnegative number")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{key} must be finite") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{key} must be a finite nonnegative number")
    return value


def _ratio(numerator: float, denominator: float) -> float | None:
    # Undefined or unrepresentable ratios use JSON null, never NaN/Infinity.
    if denominator == 0:
        return None
    result = numerator / denominator
    return round(result, 4) if math.isfinite(result) else None


def analyze_timing_variance(avx2_data: dict, avx512_data: dict,
                            neon_data: dict) -> dict:
    """Descriptive ranks only (competition ranking: ties share rank).

    Ratio names mean numerator/denominator: avx512_vs_avx2 is AVX-512 / AVX2.
    Legacy best/worst and better/worse keys refer ONLY to modeled variance.
    This is not a significance test or a security recommendation.
    """
    keys = ("avx2", "avx512", "neon")
    names = ("AVX2", "AVX-512", "ARM NEON")
    data = (avx2_data, avx512_data, neon_data)
    means = [_finite_nonnegative(d, "mean_cycles") for d in data]
    variances = [_finite_nonnegative(d, "timing_variance") for d in data]
    result = {
        key: {"mean_cycles": mean, "timing_variance": variance,
              "rank": 1 + sum(v < variance for v in variances)}
        for key, mean, variance in zip(keys, means, variances)
    }
    lowest = [n for n, v in zip(names, variances) if v == min(variances)]
    highest = [n for n, v in zip(names, variances) if v == max(variances)]
    result.update({
        "source": "synthetic",
        "comparisons": {
            "avx512_is_better_than_avx2": variances[1] < variances[0],
            "neon_is_worse_than_avx2": variances[2] > variances[0],
            "avx512_vs_avx2_variance_ratio": _ratio(variances[1], variances[0]),
            "neon_vs_avx2_variance_ratio": _ratio(variances[2], variances[0]),
        },
        "analysis": {
            "best_architecture": ", ".join(lowest),
            "worst_architecture": ", ".join(highest),
            "lowest_variance_models": lowest,
            "highest_variance_models": highest,
            "mean_diff_avx512_vs_avx2": round(means[1] - means[0], 2),
            "mean_diff_neon_vs_avx2": round(means[2] - means[0], 2),
        },
        "recommendation": LIMITATION,
    })
    return result


def generate_simd_benchmark_report(avx2_data: dict, avx512_data: dict,
                                   neon_data: dict) -> str:
    """Format synthetic descriptive statistics with explicit measurement limitations."""
    analysis = analyze_timing_variance(avx2_data, avx512_data, neon_data)
    lines = ["SIMD & Fixed Timing Variance Analysis Report", LIMITATION,
             "Sample size scales the synthetic scenario, not an executed NTT.",
             "Architecture | Mean | Std | Min | Max | Variance"]
    for name, data in zip(("AVX2", "AVX-512", "ARM NEON"),
                          (avx2_data, avx512_data, neon_data)):
        fields = ["mean_cycles", "std_cycles", "min_cycles", "max_cycles", "timing_variance"]
        values = [_finite_nonnegative(data, key) for key in fields]
        lines.append(name + " | " + " | ".join(f"{v:.2f}" for v in values))
    for key in ("avx512_vs_avx2_variance_ratio", "neon_vs_avx2_variance_ratio"):
        ratio = analysis["comparisons"][key]
        lines.append(f"{key} (numerator / denominator): " +
                     ("undefined" if ratio is None else f"{ratio}x"))
    lines.extend([
        "Best (lowest modeled variance only): " + analysis["analysis"]["best_architecture"],
        "Worst (highest modeled variance only): " + analysis["analysis"]["worst_architecture"],
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_simd_benchmark_report(simulate_avx2_ntt_timing(),
                                         simulate_avx512_ntt_timing(),
                                         simulate_neon_ntt_timing()))
