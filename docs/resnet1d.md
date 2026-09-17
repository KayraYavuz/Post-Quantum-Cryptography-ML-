# WS-P6.1 — Generic synthetic waveform ResNet1D

This module classifies project-owned general waveform shapes. It does not use
cryptographic labels, secret material, attack ranking, or the existing training,
CPA, trace-import, or API pipelines. The historical class name
`SideChannelResNet1D` is retained from the roadmap, not an attack-success claim.

## Design and existing interface review

The existing CNN uses PyTorch `nn.Module`, `(B,L)` / `(B,C,L)` input,
`(B,num_classes)` logits, and a `predict_probabilities` helper that leaves the
model in eval mode. The new module retains those conventions and uses existing
PyTorch Conv1d, BatchNorm1d, Identity, and AdaptiveAvgPool1d primitives. No new
library is needed for this explicitly requested custom 1D backbone; the existing
CNN lacks residual connections and is left unchanged.

A stride-2 convolution and stride-2 max pool form the stem. Each stage begins
with a stride-2 residual block; subsequent blocks have stride 1. Each block
adds Conv-BN-ReLU-Conv-BN to either identity or Conv1x1-BN, followed by ReLU.
Odd kernels align the paths, including odd input lengths. Global average pooling
feeds a two-layer classification head. Defaults: 16 stem channels, two stages
(32,64), two blocks per stage, 64 head units, four generic classes.

## API and limits

```python
import torch
from pqc_bench.models import SideChannelResNet1D

model = SideChannelResNet1D(input_length=64, num_classes=2).eval()
t = torch.linspace(0, 1, 64)
x = torch.stack([torch.sin(2 * torch.pi * t), torch.cos(4 * torch.pi * t)])
with torch.no_grad():
    logits = model(x)  # (2, 2); random initialization, not trained predictions
```

Constructor integers reject booleans and floats. Bounds:

| Field | Allowed |
|---|---|
| input_length | 32–4096, exact match at forward |
| num_classes | 2–64 |
| in_channels | 1–8 |
| stem_channels, stage widths | 1–128 |
| stage_channels | tuple of 1–3 widths |
| blocks_per_stage | 1–4 |
| fc_dim | 1–256 |
| dropout_p | finite int/float in [0,1), no bool |
| forward batch | 1–64 |

Input must be a finite, dense floating tensor with the model's dtype/device.
2D convenience input is only valid for a single-channel model. These bounds
limit workload dimensions; they are not a hard memory or execution-time quota.
Standalone residual blocks allow channels 1–128, odd kernel 1–15, stride 1–2;
full input validation is at the classifier boundary.

BatchNorm needs more than one value per channel in training. With **three
explicitly configured stages**, length 32 and batch 1 collapse to a single
position and raise PyTorch's error (potentially after earlier BN buffers update).
Use batch >=2 or eval mode for that configuration. The **default has two stages**.
`predict_probabilities` disables gradients and leaves every module in eval mode;
call `train()` before resuming training. It is not a concurrent training helper.

For serialization save `state_dict`, then load with `weights_only=True` into the
same constructor configuration. The state dict does not store constructor args
or class-label meanings. No checkpoints or trained metrics are produced here.

## Evidence

`python3 -m pytest tests/test_resnet1d.py -q` verifies shapes, identity/projected
residual sums, skip gradients, finite gradients and one optimizer update,
state-dict round trips, inference semantics, default export, and invalid bounds.
Fixtures use sine/cosine waves and random tensors with generic integer labels,
not the existing cryptographic data generators. CPU only; no GPU, convergence,
accuracy, phase-shift robustness, side-channel, or hardware claims.
