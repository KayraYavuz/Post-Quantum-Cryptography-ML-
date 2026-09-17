# WS-P6.3 — Conditional synthetic waveform GAN components

## Scope and implementation choice

These standalone components are for **project-owned, general synthetic waveform
families only** (for example sine, triangle and noise). Class IDs carry no
cryptographic or secret-dependent meaning. There is no hardware trace import,
key recovery, CPA, attack, web API, or existing attack-training integration.
Input validation checks tensor structure, not data provenance: callers remain
responsible for supplying only in-scope synthetic data.

The existing maintained `torch` dependency supplies `nn.Linear`, `nn.Embedding`,
`nn.LeakyReLU` and `nn.Tanh`; no custom autograd kernel, GAN framework or new
dependency is needed. This deliberately small conditional MLP is a baseline,
not a state-of-the-art architecture. No training loop, dataset mixing pipeline,
trained checkpoint, or automatic data augmentation is provided. Generated
values are **untrained outputs**, not validated realistic samples. Shape and
gradient tests do not establish augmentation benefit, accuracy, resistance to
phase shifts, side-channel behavior, or cryptographic security.

## API

Public exports from `pqc_bench.models`:

- `SyntheticWaveformGenerator(input_length=256, num_classes=4, in_channels=1,
  latent_dim=32, hidden_dim=64, embedding_dim=16)`
- `SyntheticWaveformDiscriminator(input_length=256, num_classes=4,
  in_channels=1, hidden_dim=64, embedding_dim=16)`

`G(noise, labels)` returns a dense `(B, C, L)` tensor in `[-1, 1]` (tanh).
Noise is explicit `(B, latent_dim)`, so reproducibility is caller-controlled;
the module never resets random seeds. Both networks concatenate a learned class
embedding with their inputs. `D(waveforms, labels)` returns **raw real/fake logits
`(B, 1)`**, not class logits. These can be used with PyTorch's
`BCEWithLogitsLoss`; do not apply sigmoid before that loss.

The discriminator accepts `(B, C, L)` or `(B, L)` for `C=1`, consistent with
ResNet/Transformer waveform input shapes. Generator output is always 3D, even
with one channel. No implicit normalization, clipping, resampling or cast is
performed on discriminator input. Non-contiguous dense inputs are supported.

`G.generate(noise, labels)` disables gradients and leaves G in eval mode.
`D.predict_probabilities(waveforms, labels)` similarly returns sigmoid scores
and leaves D in eval mode, matching the existing model-helper convention. These
scores are **uncalibrated** and are not a realism certificate. Call `.train()`
explicitly to resume training mode. Forward calls retain normal autograd.

## Bounds and validation

All configuration values must be exact Python integers (bools/floats rejected).

| Argument | Inclusive bounds |
|---|---|
| `input_length` | 32–4096 |
| `num_classes` | 2–64 |
| `in_channels` | 1–8 |
| `hidden_dim` | 4–256 |
| `embedding_dim` | 1–64 |
| `latent_dim` (generator only) | 1–256 |
| Per-call batch | 1–64 |

Floating inputs must be finite, strided/dense tensors with exact configured
shapes and the model's device and dtype. Labels must be dense `torch.long`,
shape `(B,)`, on the model device, in `[0, num_classes)`. Non-tensor arguments
raise `TypeError`; other invalid inputs/configurations raise `ValueError`.
Models can be converted with normal `.to(...)` / `.double()` APIs. Unit tests
cover CPU float32 and float64, not GPU or mixed-precision behavior. Bounded
architecture dimensions are not a guarantee of available memory or protection
against arbitrary out-of-scope tensors. Finite inputs alone do not guarantee
finite intermediate arithmetic at extreme values or after corrupting weights.

## Minimal untrained forward example

```python
import torch
from pqc_bench.models import SyntheticWaveformGenerator, SyntheticWaveformDiscriminator

# Generic synthetic family IDs only; no secret or hardware-derived labels.
g = SyntheticWaveformGenerator(input_length=32, num_classes=3)
d = SyntheticWaveformDiscriminator(input_length=32, num_classes=3)
rng = torch.Generator().manual_seed(7)  # controls noise, not model initialization
noise = torch.randn(3, 32, generator=rng)
labels = torch.tensor([0, 1, 2], dtype=torch.long)
waveforms = g.generate(noise, labels)  # (3, 1, 32), untrained
scores = d.predict_probabilities(waveforms, labels)  # (3, 1), uncalibrated
```

For reproducible weights, manage initialization separately or restore a saved
`state_dict`. Restore into an identically configured instance; configuration is
not embedded in a `state_dict`. Tests use in-memory round trips with
`torch.load(..., weights_only=True)` and compare exact CPU eval outputs. Do not
load untrusted serialized objects.

## Validation

Run `python3 -m pytest tests/test_waveform_gan.py -q` for CPU shape, conditioning,
gradient, helper, serialization and rejection tests. Test inputs are generated
locally, with no downloads, network delivery, hardware captures or benchmarks.
See `PROJECT_STATE.md` and `RUN_LOG.md` for actual commands/results and publication
status. GitHub CI success and training quality are not inferred from unit tests.
