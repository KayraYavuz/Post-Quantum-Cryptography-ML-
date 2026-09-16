"""Power/EM Waveform Generator with NTT Butterfly Markers & Protected/Unprotected Comparison.

This module generates synthetic power traces and EM emission waveforms for
post-quantum cryptographic implementations, with explicit markers at NTT
butterfly operations and side-channel leakage comparison between protected
and unprotected implementations.
"""

from __future__ import annotations

import math
import numpy as np
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants / Parameters
# ---------------------------------------------------------------------------

# ML-KEM-768 butterfly operation indices (butterfly peaks)
MLKEM_BUTTERFLY_PEAK_IDX = 128  # Center of the 256-point trace

# Noise parameters
DEFAULT_NOISE_STD = 0.35
PROTECTED_NOISE_STD = 0.12  # Masking reduces effective noise visibility

# Amplitude scaling for different leakage types
UNPROTCT_AMPLITUDE = 1.0
PROTECTED_AMPLITUDE = 0.3  # Masking reduces leakage amplitude


# ---------------------------------------------------------------------------
# Core Waveform Generation
# ---------------------------------------------------------------------------

def _gaussian_peak(
    x: np.ndarray,
    x0: float,
    sigma: float,
    amplitude: float = 1.0,
) -> np.ndarray:
    """One Gaussian-shaped peak at x0 on domain x."""
    return amplitude * np.exp(-(x - x0) ** 2 / (2 * sigma ** 2))


def _butterfly_marker(
    x: np.ndarray,
    peak_idx: float = MLKEM_BUTTERFLY_PEAK_IDX,
    sigma: float = 20.0,
    amplitude: float = UNPROTCT_AMPLITUDE,
) -> np.ndarray:
    """Composite NTT butterfly-shaped marker (two symmetric Gaussians)."""
    left = _gaussian_peak(x, peak_idx - 25, sigma, amplitude)
    right = _gaussian_peak(x, peak_idx + 25, sigma, amplitude)
    return left + right


def generate_power_trace(
    n_samples: int = 256,
    leakage_model: str = "unprotected",  # "unprotected" | "protected" | "masked"
    add_noise: bool = True,
    noise_std: Optional[float] = None,
    butterfly_markers: bool = True,
) -> Dict[str, np.ndarray]:
    """Generate a 256-sample power/EM trace with optional NTT butterfly markers.

    Parameters
    ----------
    n_samples:
        Number of time samples (default 256 for ML-KEM trace length).
    leakage_model:
        "unprotected": raw polynomial multiplication leakage.
        "protected": 1st-order Boolean masking applied.
        "masked": full masking + shuffling countermeasures.
    add_noise:
        Whether to add Gaussian noise consistent with lab conditions.
    noise_std:
        Standard deviation of additive Gaussian noise. Defaults to
        ``DEFAULT_NOISE_STD`` (unprotected) or ``PROTECTED_NOISE_STD``
        (protected).
    butterfly_markers:
        If True, adds NTT butterfly-shaped markers at the characteristic
        leakage peaks (index ~128).

    Returns
    -------
    Dict with keys:
        - "trace": np.ndarray of shape (n_samples,) the generated waveform.
        - "time": np.ndarray of shape (n_samples,) sample indices (0..n_samples-1).
        - "leakage_score": float in [0,1] indicating relative leakage amplitude.
        - "labels": Dict with marker positions and model info.
    """
    if noise_std is None:
        noise_std = PROTECTED_NOISE_STD if leakage_model in ("protected", "masked") else DEFAULT_NOISE_STD

    # Time axis
    time = np.arange(n_samples, dtype=np.float64)

    # Base waveform: polynomial multiplication power consumption
    # Simulated as a smooth curve with a butterfly leakage peak at the NTT core
    base = np.zeros(n_samples, dtype=np.float64)

    # Bulk polynomial multiplication component (smooth rising/falling)
    window = np.arange(n_samples) - n_samples // 2
    bulk = np.exp(-(window ** 2) / (2 * (n_samples // 4) ** 2))
    base = UNPROTCT_AMPLITUDE * bulk / bulk.max()

    # Add NTT butterfly leakage marker (dominant side-channel peak)
    if butterfly_markers:
        butterfly = _butterfly_marker(time, amplitude=UNPROTCT_AMPLITUDE if leakage_model == "unprotected" else PROTECTED_AMPLITUDE)
        base = base + butterfly

    # Add optional Gaussian noise
    if add_noise:
        rng = np.random.default_rng(42)
        noise = rng.normal(0, noise_std, size=n_samples)
        trace = base + noise
    else:
        trace = base

    # Compute relative leakage score
    max_abs = np.max(np.abs(trace)) if np.max(np.abs(trace)) > 0 else 1.0
    leakage_score = float(np.max(np.abs(butterfly)) / max_abs) if butterfly_markers else 0.3

    labels = {
        "leakage_model": leakage_model,
        "butterfly_peak_idx": int(MLKEM_BUTTERFLY_PEAK_IDX),
        "noise_std": noise_std,
        "butterfly_amplitude": float(np.max(np.abs(butterfly))) if butterfly_markers else 0.0,
    }

    return {
        "trace": trace,
        "time": time,
        "leakage_score": round(leakage_score, 4),
        "labels": labels,
    }


def generate_comparison_traces(
    n_samples: int = 256,
    models: Optional[List[str]] = None,
    include_unprotected: bool = True,
    include_protected: bool = True,
    include_masked: bool = True,
) -> Dict[str, Dict[str, np.ndarray]]:
    """Generate side-by-side traces for protected vs unprotected comparison.

    Parameters
    ----------
    n_samples:
        Trace length (default 256).
    models:
        List of leakage model names to generate. If None, defaults to
        ["unprotected", "protected", "masked"] when all flags are True.
    include_unprotected:
        Whether to include the unprotected trace.
    include_protected:
        Whether to include the 1st-order Boolean masked trace.
    include_masked:
        Whether to include the full masking + shuffling trace.

    Returns
    -------
    Dict mapping model name -> result dict from ``generate_power_trace``.
    """
    if models is None:
        models = []
    if include_unprotected:
        models.append("unprotected")
    if include_protected:
        models.append("protected")
    if include_masked:
        models.append("masked")

    results: Dict[str, Dict[str, np.ndarray]] = {}
    for model in models:
        trace_info = generate_power_trace(n_samples=n_samples, leakage_model=model)
        results[model] = {
            "trace": trace_info["trace"],
            "time": trace_info["time"],
            "leakage_score": trace_info["leakage_score"],
            "labels": trace_info["labels"],
        }

    return results


# ---------------------------------------------------------------------------
# Specialized Waveforms (Targeted Leakage Patterns)
# ---------------------------------------------------------------------------

def generate_ntt_butterfly_peak(
    n_samples: int = 256,
    peak_index: Optional[int] = None,
    amplitude: float = UNPROTCT_AMPLITUDE,
) -> Dict[str, np.ndarray]:
    """Generate just the NTT butterfly-shaped leakage peak.

    Useful for isolating the dominant side-channel point in visualizations
    and educational demonstrations.

    Parameters
    ----------
    n_samples:
        Trace length.
    peak_index:
        Index of the peak. Defaults to ML-KEM butterfly center (128).
    amplitude:
        Peak amplitude scaling.

    Returns
    -------
    Dict with "trace" (the peak alone) and "time".
    """
    if peak_index is None:
        peak_index = MLKEM_BUTTERFLY_PEAK_IDX
    time = np.arange(n_samples, dtype=np.float64)

    # Single Gaussian peak at the butterfly location
    peak = _gaussian_peak(time, float(peak_index), sigma=20.0, amplitude=amplitude)

    return {"trace": peak, "time": time}


def generate_synthetic_emm_pattern(
    n_samples: int = 256,
    pattern: str = "ntt_butterfly",  # "ntt_butterfly" | "polynomial_mult" | "custom"
    protected: bool = False,
) -> Dict[str, np.ndarray]:
    """Generate a synthetic EM emission pattern focused on a leakage pattern.

    Parameters
    ----------
    n_samples:
        Number of time samples.
    pattern:
        Which base pattern to generate.
    protected:
        If True, reduces amplitude to simulate masking effect.

    Returns
    -------
    Dict with "trace" (synthetic EM pattern) and "time".
    """
    time = np.arange(n_samples, dtype=np.float64)
    amp = PROTECTED_AMPLITUDE if protected else UNPROTCT_AMPLITUDE

    if pattern == "ntt_butterfly":
        # NTT-focused emission: two symmetric peaks around the butterfly
        left_peak = np.exp(-(time - (MLKEM_BUTTERFLY_PEAK_IDX - 25)) ** 2 / (2 * 18 ** 2))
        right_peak = np.exp(-(time - (MLKEM_BUTTERFLY_PEAK_IDX + 25)) ** 2 / (2 * 18 ** 2))
        trace = left_peak + right_peak
    elif pattern == "polynomial_mult":
        # Broad polynomial multiplication emission
        window = time - n_samples // 2
        trace = np.exp(-(window ** 2) / (2 * (n_samples // 4) ** 2))
    elif pattern == "custom":
        # Custom: multiple leakage epochs
        trace = np.zeros(n_samples)
        for center, width, amp_val in [(64, 12, 0.6), (128, 15, amp), (192, 10, 0.4)]:
            trace += amp_val * np.exp(-(time - center) ** 2 / (2 * width ** 2))
    else:
        trace = np.zeros(n_samples)

    # Normalize to [0, 1]
    if np.max(np.abs(trace)) > 0:
        trace = trace / np.max(np.abs(trace))

    return {"trace": trace, "time": time}


# ---------------------------------------------------------------------------
# Waveform Comparison / Diff
# ---------------------------------------------------------------------------

def compare_protected_unprotected(
    n_samples: int = 256,
) -> Dict[str, Dict[str, np.ndarray]]:
    """Convenience: generate unprotected + 1st-order protected + masked traces
    side-by-side for direct comparison and visualization.

    Returns a dict with keys "unprotected", "protected", "masked" each
    containing the trace, time axis, and leakage score.
    """
    return generate_comparison_traces(
        n_samples=n_samples,
        include_unprotected=True,
        include_protected=True,
        include_masked=True,
    )


# ---------------------------------------------------------------------------
# Example / CLI usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """Quick demo: generate and print comparison traces."""
    import json

    comparison = compare_protected_unprotected()

    for model_name, data in comparison.items():
        print(f"\n=== {model_name} ===")
        print(f"  Leakage score: {data['leakage_score']}")
        print(f"  Butterfly peak at index: {data['labels']['butterfly_peak_idx']}")
        print(f"  First 10 samples: {data['trace'][:10].round(4).tolist()}")
        print(f"  Time range: {data['time'][0]:.0f} - {data['time'][-1]:.0f}")

    # Print a simple ASCII-like summary
    print("\n--- ASCII Summary (Unprotected vs Protected vs Masked) ---")
    for model_name in ["unprotected", "protected", "masked"]:
        trace = comparison[model_name]["trace"]
        peak_val = trace[MLKEM_BUTTERFLY_PEAK_IDX]
        marker = "#" if peak_val > 0.5 else "." if peak_val > 0.2 else "-"
        print(f"  {model_name:12s}: peak={peak_val:5.2f} {marker}")