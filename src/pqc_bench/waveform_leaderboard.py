"""Local, bounded leaderboard for project-owned generic synthetic waveforms.

No trace import, cryptographic labels, training, attack or service integration.
Only accuracy derived from supplied class predictions is ranked. Provenance is
caller-attested, not proof of execution or authenticity.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import re

CLASSES = ("sine", "cosine", "noise")
MAX_RESULTS = 64


def _identifier(name: str, value: str) -> None:
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value) is None:
        raise ValueError(f"{name} must be a 1..64 character identifier")


def _class_ids(name: str, values: tuple[int, ...], count: int) -> None:
    if type(values) is not tuple or len(values) != count:
        raise ValueError(f"{name} must be a tuple of {count} class ids")
    if any(type(value) is not int or not 0 <= value < len(CLASSES) for value in values):
        raise ValueError(f"{name} must contain integer class ids 0..2")


@dataclass(frozen=True)
class SyntheticSplit:
    """Immutable post-preprocessing evaluation data, one channel, 32..4096 samples.

    Labels are fixed: 0=sine, 1=cosine, 2=noise. Every class must be represented.
    Exact waveform values/order, labels, split_id and preprocessing_id define
    comparability; different splits are rejected rather than silently mixed.
    """

    split_id: str
    preprocessing_id: str
    waveforms: tuple[tuple[float, ...], ...]
    targets: tuple[int, ...]

    def __post_init__(self) -> None:
        _identifier("split_id", self.split_id)
        _identifier("preprocessing_id", self.preprocessing_id)
        if type(self.waveforms) is not tuple or not 3 <= len(self.waveforms) <= 256:
            raise ValueError("waveforms must be a tuple containing 3..256 examples")
        first = self.waveforms[0]
        if type(first) is not tuple or not 32 <= len(first) <= 4096:
            raise ValueError("each waveform must be a tuple with length 32..4096")
        for row in self.waveforms:
            if type(row) is not tuple or len(row) != len(first):
                raise ValueError("waveforms must be rectangular tuples")
            if any(type(v) not in (int, float) or not -1 <= v <= 1 for v in row):
                raise ValueError("waveforms must contain finite real samples in [-1, 1]")
        _class_ids("targets", self.targets, len(self.waveforms))
        if set(self.targets) != set(range(len(CLASSES))):
            raise ValueError("every generic class must be represented")

    @property
    def fingerprint(self) -> str:
        # Canonical float representation equates 0 and 0.0 (and signed zero).
        payload = {
            "schema_version": 1, "classes": CLASSES,
            "split_id": self.split_id, "preprocessing_id": self.preprocessing_id,
            "waveforms": [[float(v) if v else 0.0 for v in row] for row in self.waveforms],
            "targets": self.targets,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvaluationResult:
    """Prediction evidence for one CNN, ResNet or Transformer evaluation.

    model_id identifies a specific configuration/checkpoint, not just a family.
    Do not submit fabricated predictions. The library cannot authenticate their
    origin. No accuracy, timing, GAN score or arbitrary metric can be supplied.
    """

    model_id: str
    family: str
    training_status: str
    split: SyntheticSplit
    predictions: tuple[int, ...]

    def __post_init__(self) -> None:
        _identifier("model_id", self.model_id)
        if type(self.family) is not str or self.family not in ("CNN", "ResNet", "Transformer"):
            raise ValueError("family must be CNN, ResNet or Transformer")
        if type(self.training_status) is not str or self.training_status not in ("untrained", "trained"):
            raise ValueError("training_status must be untrained or trained")
        if type(self.split) is not SyntheticSplit:
            raise ValueError("split must be a validated SyntheticSplit")
        _class_ids("predictions", self.predictions, len(self.split.targets))

    @property
    def correct(self) -> int:
        return sum(p == t for p, t in zip(self.predictions, self.split.targets))

    @property
    def accuracy(self) -> float:
        return self.correct / len(self.split.targets)


def build_leaderboard(results: tuple[EvaluationResult, ...]) -> dict:
    """Return a fresh JSON-safe report; no I/O or model execution.

    Descending exact accuracy, competition ranks (1, 1, 3), and model_id
    lexicographic display order within ties. Training status must also match.
    Missing performance measurements remain explicit nulls, never zero values.
    """
    if type(results) is not tuple or len(results) > MAX_RESULTS:
        raise ValueError("results must be a tuple containing at most 64 evaluations")
    if any(type(result) is not EvaluationResult for result in results):
        raise ValueError("results must contain validated EvaluationResult objects")
    if len({result.model_id for result in results}) != len(results):
        raise ValueError("model_id must be unique; aggregate repeats separately")
    fingerprints = {result.split.fingerprint for result in results}
    if len(fingerprints) > 1:
        raise ValueError("incomparable evaluation splits or preprocessing contracts")
    if len({result.training_status for result in results}) > 1:
        raise ValueError("incomparable training status")
    ordered = sorted(results, key=lambda r: (-Fraction(r.correct, len(r.predictions)), r.model_id))
    rows = []
    previous = None
    rank = 0
    for position, result in enumerate(ordered, start=1):
        score = Fraction(result.correct, len(result.predictions))
        if score != previous:
            rank = position
        previous = score
        accuracy = result.accuracy
        if not math.isfinite(accuracy):  # Defense in depth; validated counts cannot produce this.
            raise ValueError("non-finite accuracy")
        rows.append({
            "rank": rank, "model_id": result.model_id, "family": result.family,
            "training_status": result.training_status,
            "correct": result.correct, "sample_count": len(result.predictions),
            "accuracy": accuracy, "accuracy_status": "computed_from_predictions",
            "latency_ms": None, "throughput_per_second": None, "loss": None,
            "unmeasured_metrics": ["latency_ms", "throughput_per_second", "loss"],
        })
    return {
        "schema_version": 1, "scope": "project_owned_generic_synthetic_waveforms",
        "classes": list(CLASSES), "metric": "accuracy", "higher_is_better": True,
        "tie_policy": "competition_rank_then_model_id",
        "split_fingerprint": next(iter(fingerprints), None),
        "provenance": "caller_attested_predictions_not_independently_authenticated",
        "rows": rows,
    }
