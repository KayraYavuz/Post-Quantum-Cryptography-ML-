# WS-P6.2 — Generic synthetic waveform Transformer

`pqc_bench.models.WaveformTransformer1D` is a bounded patchwise classifier for
project-owned **general synthetic waveforms** (sine, cosine, noise). Its workstream
has a historical SCA title, but this implementation has no cryptographic labels,
secret material, key-recovery logic, trace import, attack evaluation, or service
integration. It is not wired into the repository's legacy attack/training paths.

## Existing-library choice

The repository already depends on PyTorch. This model uses its maintained
`torch.nn.MultiheadAttention`, `LayerNorm`, linear layers, and autograd rather
than adding a dependency or implementing an attention kernel. ResNet's input and
inference-helper conventions are retained; ResNet-specific parameters/weights
are not interchangeable.

## Interface

```python
import torch
from pqc_bench.models import WaveformTransformer1D

model = WaveformTransformer1D(input_length=64, num_classes=4)
t = torch.linspace(0, 1, 64)
x = torch.stack([torch.sin(2 * torch.pi * t), torch.cos(4 * torch.pi * t)])
mask = torch.zeros(2, 64, dtype=torch.bool)
mask[0, 48:] = True
probabilities = model.predict_probabilities(x, padding_mask=mask)
assert probabilities.shape == (2, 4)
```

- `forward(x, padding_mask=None)` returns logits `(B, num_classes)`.
- Input: dense finite floating `(B, C, L)`, or `(B, L)` with one channel;
  exact model dtype/device required. Even masked values must be finite.
- `padding_mask`: dense boolean `(B, L)` on the input device. `True` means
  ignore a sample across all channels. Arbitrary holes and left/right padding
  are supported; every row must contain at least one unmasked sample.
- Ignored values become zero **before** patch projection. A token is excluded
  from attention keys/values and pooling only when its entire patch is masked.
  Partial patches remain valid; their masked entries contribute zero, without
  rescaling for missing samples. Pooled valid tokens have equal weight, not
  weight proportional to the number of valid samples.
- Non-divisible lengths are padded internally with masked zeros. No causal or
  arbitrary pairwise attention mask is exposed.
- `predict_probabilities` applies softmax under `no_grad`, leaves the model in
  eval mode, and accepts the same padding mask. Call `train()` before training.

## Architecture and bounds

Non-overlapping patches → linear projection + fixed sinusoidal patch positions
→ pre-LayerNorm multi-head self-attention / residual feed-forward blocks
→ LayerNorm → valid-token mean → dense classifier.

| Parameter | Default | Supported bound |
|---|---|---|
| input_length | 256 | 32–4096, fixed per model |
| num_classes | 4 | 2–64 |
| in_channels | 1 | 1–8 |
| d_model | 32 | even, 4–128, divisible by num_heads |
| num_heads | 4 | 1–8 |
| num_layers | 2 | 1–4 |
| ff_dim | 64 | 4–512 |
| fc_dim | 64 | 1–256 |
| dropout_p | 0.25 | finite number in [0, 1), not bool |
| patch_size | 8 | 1–64; ceil(input_length / patch_size) ≤ 256 |

Batch size is 1–64; integer configuration rejects booleans and floats. Attention
has quadratic token cost. These are per-call/configuration bounds, not a service
rate limiter or a guarantee that every maximum configuration fits any device.
LayerNorm avoids ResNet's batch-1 BatchNorm training restriction. State-dict
loading requires an identically configured model; positional encoding is a
serialized buffer. Use `torch.load(..., weights_only=True)` for saved weights.

## Verification and non-claims

Run `python3 -m pytest tests/test_waveform_transformer.py -q` for CPU unit tests
covering shapes, mask semantics, invalid inputs, gradients, an optimizer step,
probabilities and state-dict round trips. An optimizer-step smoke test is not
model training or a measured classification benchmark. No accuracy, phase-shift
robustness, cryptographic leakage, GPU performance, or hardware result is claimed.
Fixed positional encoding and patch boundaries do not guarantee shift invariance.
See PROJECT_STATE.md and RUN_LOG.md for actual run results and publication status.
