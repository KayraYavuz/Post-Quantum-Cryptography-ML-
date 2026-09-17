# WS-P6.4 — Generic synthetic waveform leaderboard

## Scope and existing components

This is a local Python data contract, not a training pipeline or public service.
It uses Python's maintained dataclasses, fractions, hashlib and JSON facilities;
existing PyTorch CNN/ResNet/Transformer implementations are reused in the CPU
inference smoke test. No new dependency or tracking server is needed. MLflow
(already declared by the repository) would add persistence/service overhead not
needed for this bounded, in-memory comparison.

Only project-owned generic synthetic classes are supported, with fixed ordered
labels `0=sine`, `1=cosine`, `2=noise`. No cryptographic labels, secret material,
CPA, key recovery, hardware trace imports, existing attack metrics or GAN
scores are consumed. No FastAPI endpoint or dashboard integration is added.

## Contract

Import `SyntheticSplit`, `EvaluationResult`, and `build_leaderboard` from
`pqc_bench.waveform_leaderboard`.

1. Construct a frozen `SyntheticSplit(split_id, preprocessing_id, waveforms,
   targets)` from the actual post-preprocessing evaluation data. Nested tuples
   are required: 3..256 examples, one channel, equal length 32..4096; finite
   samples in [-1, 1]. All three classes must occur. Integer class IDs reject
   bools, floats, invalid ranges and wrong lengths.
2. Perform real classifier inference on that split; convert argmax class IDs to
   a tuple. Construct `EvaluationResult(model_id, family, training_status,
   split, predictions)`. Family is CNN, ResNet or Transformer; training status
   is explicitly `untrained` or `trained`. Use a configuration/checkpoint-specific
   model ID (1..64 alphanumeric/underscore/dot/hyphen characters).
3. Pass a tuple of at most 64 results to `build_leaderboard`. It derives accuracy
   from correct predictions/count; callers cannot inject scalar accuracy or
   discriminator scores. Report rows are ordered by descending exact accuracy
   (rational count/sample count), with lexicographic model ID order within ties.
   Competition ranks are 1, 1, 3. Duplicate model IDs are rejected, not overwritten.
4. Serialize the fresh report with `json.dumps(report, allow_nan=False)`. No file,
   network, checkpoint loading or model execution is performed by the contract.

```python
import json
from pqc_bench.waveform_leaderboard import build_leaderboard

# Before real measurements exist, return an honest empty report, not fake scores.
print(json.dumps(build_leaderboard(()), allow_nan=False))
```

## Comparability and missing measurements

The SHA-256 split fingerprint covers schema version, ordered fixed labels,
post-preprocessing waveform values and order, target values and order, split ID
and preprocessing ID. Integer/float representations and signed zero are
canonicalized. Different fingerprints or training statuses are rejected; rows
cannot quietly combine different data, label order or preprocessing. Timing,
throughput and loss are always `null` with explicit `unmeasured_metrics` entries;
there is no secondary speed tie-break or unmeasured zero value.

Prediction provenance is **caller-attested**, not independently authenticated.
The contract checks structural consistency, not whether supplied waveforms are
truly synthetic, whether predictions were actually measured, training leakage,
checkpoint identity, or equal training budgets. A fingerprint is not a signature.
Use only genuinely observed predictions; don't submit fabricated results or
interpret a ranking as evidence of statistical significance or model superiority.
Repeated seeds/splits need separate comparisons; aggregation is not implemented.
Frozen tuples prevent normal mutation; this is not a security sandbox against
malicious Python callers who bypass dataclass validation.

## Verification and limitations

`tests/test_waveform_leaderboard.py` tests ranking/ties, order independence,
empty reports, missing metrics, JSON finiteness, strict bounds/types, invalid
metrics/predictions, duplicate IDs, mismatched splits/preprocessing/targets and
training status, numeric canonicalization and immutable inputs.

The CPU inference smoke test uses three **randomly initialized, untrained**
models on the same three tiny synthetic waveforms (sine/cosine/seeded noise).
Its predictions are actually computed; accuracy is verified against those
predictions, not asserted to be high. Other prediction fixtures are fabricated
unit-test data solely for arithmetic/validation. No trained evaluation artifacts,
benchmark accuracy, training improvement, robustness, GPU speed, latency or
hardware results are claimed. No leaderboard file with invented scores ships.

Run:

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 -m pytest -q tests/test_waveform_leaderboard.py
```
