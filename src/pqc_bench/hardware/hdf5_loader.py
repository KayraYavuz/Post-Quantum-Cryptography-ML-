"""HDF5 Oscilloscope Data Loader for ChipWhisperer traces.

Provides structured loading of ChipWhisperer HDF5 trace files with
automatic detection of waveform metadata, sample counts, and associated
intermediate values (HW, cryptographic operations).

Supports both .hdf5 and .hdf extension formats used by ChipWhisperer
software for trace capture and storage.

Typical HDF5 structure:
    /traces       : numpy array (N_traces x N_samples)
    /samples      : numpy array (N_samples,) time axis
    /metadata     : dict with 'sample_rate', 'offset', 'rng_seed'
    /intermediates: dict with 'HW', 'points', 'labels' per trace
"""

from __future__ import annotations

import pathlib
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# ---------------------------------------------------------------------------
# Constants / Defaults
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_RATE = 1e9   # 1 GSample/s default if not stored
DEFAULT_OFFSET_NS = 0       # time origin offset in nanoseconds

# HDF5 dataset path constants
HDF_PATH_TRACES = "traces"
HDF_PATH_SAMPLES = "samples"
HDF_PATH_METADATA = "metadata"
HDF_PATH_INTERMEDIATES = "intermediates"

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _safe_load_hdf5(path: pathlib.Path) -> Any:
    """Load HDF5 file using h5py with graceful fallback.

    Attempts h5py first; if unavailable, reports a structured error
    rather than crashing.
    """
    try:
        import h5py  # type: ignore[import]
        return h5py.File(str(path), "r")
    except ImportError as exc:
        raise RuntimeError(
            "h5py is required for HDF5 trace loading. "
            "Install with: pip install h5py"
        ) from exc


def _infer_sample_axis(data: np.ndarray, expected_samples: int) -> np.ndarray:
    """Infer or construct the sample time axis from trace data.

    Parameters
    ----------
    data:
        2D array of shape (N_traces, N_samples) or 1D (N_samples,).
    expected_samples:
        Expected number of samples if data is 1D.

    Returns
    -------
    np.ndarray of shape (N_samples,) or (N_traces, N_samples)
    """
    if data.ndim == 1:
        if len(data) == expected_samples:
            return data.copy()
        # Possibly already (N_traces, N_samples) flattened incorrectly
        raise ValueError(
            f"1D data length {len(data)} != expected samples {expected_samples}"
        )
    # data.ndim == 2: return as-is (N_traces, N_samples)
    return data


# ---------------------------------------------------------------------------
# Core Loader Class
# ---------------------------------------------------------------------------


class Hdf5OscilloscopeLoader:
    """Load and manage ChipWhisperer HDF5 oscilloscope trace files.

    Parameters
    ----------
    filepath:
        Path to .hdf5 or .hdf file captured by ChipWhisperer.
    path:
        Alias for filepath provided for API compatibility.
    """

    def __init__(self, filepath: str | pathlib.Path, path: str | pathlib.Path | None = None):
        self.filepath = pathlib.Path(filepath)
        self.path = pathlib.Path(path) if path else self.filepath
        self._h5_file: Any = None
        self._traces: np.ndarray | None = None
        self._sample_axis: np.ndarray | None = None
        self._metadata: Dict[str, Any] = {}
        self._intermediates: Dict[str, Any] = {}
        self._n_traces: int = 0
        self._n_samples: int = 0

    # ------------------------------------------------------------------
    # Open / Close
    # ------------------------------------------------------------------

    def open(self) -> "Hdf5OscilloscopeLoader":
        """Open the HDF5 file and load core arrays into memory.

        Returns
        -------
        self, for method chaining.
        """
        self._h5_file = _safe_load_hdf5(self.filepath)
        self._load_core_arrays()
        return self

    def close(self) -> None:
        """Close the underlying h5py file handle if open."""
        if self._h5_file is not None:
            self._h5_file.close()
            self._h5_file = None
            self._traces = None
            self._sample_axis = None
            self._metadata = {}
            self._intermediates = {}

    # ------------------------------------------------------------------
    # Core Data Extraction
    # ------------------------------------------------------------------

    def _load_core_arrays(self) -> None:
        """Load traces, sample axis, metadata, and intermediates from HDF5."""
        h5 = self._h5_file

        # --- traces ---
        if HDF_PATH_TRACES in h5:
            raw = h5[HDF_PATH_TRACES][:]
            self._traces = _infer_sample_axis(raw, self._expected_samples())
            self._n_traces, self._n_samples = self._traces.shape
        else:
            self._traces = np.empty((0, 0), dtype=np.float64)
            self._n_traces, self._n_samples = 0, 0

        # --- sample axis ---
        if HDF_PATH_SAMPLES in h5:
            self._sample_axis = np.asarray(h5[HDF_PATH_SAMPLES][()], dtype=np.float64)
            # If length doesn't match n_samples, generate default axis
            if self._sample_axis.size != self._n_samples:
                self._sample_axis = np.arange(self._n_samples, dtype=np.float64)
        else:
            self._sample_axis = np.arange(self._n_samples, dtype=np.float64)

        # --- metadata ---
        if HDF_PATH_METADATA in h5:
            raw_meta = {k: v for k, v in h5[HDF_PATH_METADATA].items()}
            self._metadata = {
                k: (v.item() if isinstance(v, np.generic) else v)
                for k, v in raw_meta.items()
            }
            # Ensure sample_rate defaults if missing
            if "sample_rate" not in self._metadata:
                self._metadata["sample_rate"] = DEFAULT_SAMPLE_RATE
        else:
            self._metadata = {
                "sample_rate": DEFAULT_SAMPLE_RATE,
                "offset_ns": DEFAULT_OFFSET_NS,
                "rng_seed": None,
            }

        # --- intermediates ---
        if HDF_PATH_INTERMEDIATES in h5:
            raw_int = {}
            for key in h5[HDF_PATH_INTERMEDIATES].keys():
                val = h5[HDF_PATH_INTERMEDIATES][key][:]
                raw_int[key] = (
                    val.item() if isinstance(val, np.generic) else val
                )
            self._intermediates = raw_int
        else:
            # Populate minimal defaults so callers can safely check keys
            self._intermediates = {}

    def _expected_samples(self) -> int:
        """Heuristic: return expected sample count from metadata or 0."""
        sr = self._metadata.get("sample_rate")
        return int(sr) if sr and isinstance(sr, (int, float)) else 0

    # ------------------------------------------------------------------
    # Public Accessors
    # ------------------------------------------------------------------

    @property
    def traces(self) -> np.ndarray:
        """Return (N_traces, N_samples) trace array.

        Raises RuntimeError if the file has not been opened yet.
        """
        if self._traces is None:
            raise RuntimeError("HDF5 file not opened. Call .open() first.")
        return self._traces

    @property
    def sample_axis(self) -> np.ndarray:
        """Return (N_samples,) time axis in seconds (or native units)."""
        if self._sample_axis is None:
            raise RuntimeError("HDF5 file not opened. Call .open() first.")
        return self._sample_axis

    @property
    def metadata(self) -> Dict[str, Any]:
        """Return dict of HDF5-stored metadata (sample_rate, offset, etc.)."""
        return self._metadata

    @property
    def intermediates(self) -> Dict[str, Any]:
        """Return dict of intermediate values (HW, points, labels per trace)."""
        return self._intermediates

    @property
    def n_traces(self) -> int:
        """Number of traces stored in the file."""
        return self._n_traces

    @property
    def n_samples(self) -> int:
        """Number of time samples per trace."""
        return self._n_samples

    # ------------------------------------------------------------------
    # Bulk Operations
    # ---------------------------------------------------------------------------

    def get_trace(self, index: int) -> np.ndarray:
        """Return a single trace at the given index.

        Parameters
        ----------
        index:
            Zero-based trace index.

        Returns
        -------
        np.ndarray of shape (N_samples,)
        """
        if not (0 <= index < self._n_traces):
            raise IndexError(
                f"Trace index {index} out of range [0, {self._n_traces - 1}]"
            )
        return self._traces[index]

    def get_intermediate(self, key: str, trace_index: int = 0) -> Any:
        """Return an intermediate value for a given trace index.

        Parameters
        ----------
        key:
            Intermediate key name (e.g. 'HW', 'points', 'labels').
        trace_index:
            Zero-based trace index. Default 0.

        Returns
        -------
        The intermediate value, or None if key not found.
        """
        ints = self._intermediates
        if key not in ints:
            return None
        # If stored as array, return the slice for this trace
        val = ints[key]
        if isinstance(val, np.ndarray):
            if val.ndim == 1 and self._n_traces > 0:
                if 0 <= trace_index < val.size:
                    return val[trace_index]
                return val
        return val

    # ------------------------------------------------------------------
    # SNR Analysis
    # ---------------------------------------------------------------------------

    def compute_snr(
        self,
        reference_trace: Optional[np.ndarray] = None,
        noise_trace_indices: Optional[List[int]] = None,
        signal_indices: Optional[List[int]] = None,
        noise_indices: Optional[List[int]] = None,
    ) -> Dict[str, float]:
        """Compute Signal-to-Noise Ratio (SNR) for side-channel analysis.

        SNR is computed as: SNR = |mean(signal) - mean(noise)| / stddev(noise)

        Parameters
        ----------
        reference_trace:
            Optional single trace to use as reference. If None, uses the
            mean across all traces as the "signal".
        noise_trace_indices:
            List of trace indices to average as noise. If None, averages
            all traces not in signal_indices.
        signal_indices:
            List of trace indices to use as signal. If None, uses trace 0.
        noise_indices:
            Explicit list of sample indices (within a trace) to use as
            noise. If None, uses samples outside the central 50% window.

        Returns
        -------
        Dict with keys:
            - snr_db: SNR in decibels (20 * log10(linear_snr))
            - snr_linear: Linear SNR ratio
            - signal_mean: Mean amplitude of signal portion
            - noise_std: Standard deviation of noise portion
            - snr_peak_idx: Sample index of peak SNR (if applicable)
        """
        traces = self.traces  # (N, M)
        n_traces, n_samples = traces.shape

        # --- Determine signal portion ---
        if signal_indices is None:
            # Default: use first trace as reference signal
            sig_trace = traces[0] if n_traces > 0 else np.zeros(n_samples)
        else:
            # Average of selected traces
            sig_traces = traces[signal_indices]
            sig_trace = np.mean(sig_traces, axis=0) if sig_traces.shape[0] > 1 else sig_traces[0]

        # --- Determine noise portion ---
        if noise_trace_indices is None:
            # Average all other traces as noise
            if noise_indices is None:
                # Use all traces except signal reference
                exclude = set(signal_indices) if signal_indices else {0}
                noise_trace_indices = [i for i in range(n_traces) if i not in exclude]
            else:
                noise_trace_indices = list(noise_indices)

        # Average noise traces
        noise_data = traces[noise_trace_indices]
        noise_mean = np.mean(noise_data, axis=0) if noise_data.shape[0] > 1 else noise_data[0]

        # --- If explicit sample noise_indices provided, use those ---
        if noise_indices is not None and len(noise_indices) > 0:
            # Build per-trace noise means at those sample positions
            noise_selected = traces[:, noise_indices]
            noise_mean = np.mean(noise_selected, axis=0)
            noise_std = float(np.std(noise_selected))
        else:
            # Standard: stddev across noise traces at each sample, then overall
            noise_std = float(np.std(noise_mean))

        # --- Compute SNR ---
        signal_mean = float(np.mean(sig_trace))
        linear_snr = abs(signal_mean - float(np.mean(noise_mean))) / max(noise_std, 1e-12)
        snr_linear = linear_snr
        snr_db = 20.0 * np.log10(max(linear_snr, 1e-12))

        return {
            "snr_db": round(snr_db, 4),
            "snr_linear": round(snr_linear, 4),
            "signal_mean": round(signal_mean, 6),
            "noise_std": round(noise_std, 6),
            "snr_peak_idx": int(np.argmax(np.abs(sig_trace - noise_mean))) if n_samples > 0 else -1,
        }


# ---------------------------------------------------------------------------
# Convenience / CLI
# ---------------------------------------------------------------------------

def load_hdf5_traces(filepath: str | pathlib.Path) -> Dict[str, Any]:
    """Convenience: load an HDF5 file and return a summary dict.

    Parameters
    ----------
    filepath:
        Path to .hdf5 file.

    Returns
    -------
    Dict with keys: n_traces, n_samples, metadata, intermediates_available
    """
    loader = Hdf5OscilloscopeLoader(filepath)
    loader.open()
    try:
        return {
            "n_traces": loader.n_traces,
            "n_samples": loader.n_samples,
            "metadata": loader.metadata,
            "intermediates_available": bool(loader.intermediates),
            "sample_axis_first_10": loader.sample_axis[:10].tolist(),
            "trace_0_first_10": loader.get_trace(0)[:10].tolist(),
        }
    finally:
        loader.close()


def compute_snr_from_hdf5(filepath: str | pathlib.Path) -> Dict[str, float]:
    """Convenience: compute SNR from an HDF5 oscilloscope file.

    Parameters
    ----------
    filepath:
        Path to .hdf5 file.

    Returns
    -------
    SNR dict from Hdf5OscilloscopeLoader.compute_snr()
    """
    loader = Hdf5OscilloscopeLoader(filepath)
    loader.open()
    try:
        return loader.compute_snr()
    finally:
        loader.close()
