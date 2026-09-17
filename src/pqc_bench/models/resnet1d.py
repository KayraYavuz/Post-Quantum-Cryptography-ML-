"""WS-P6.1 — Residual 1D ResNet backbone for general synthetic waveform classification.

Scope: project-owned synthetic waveform shapes only. This module contains no
secret-key material, no key-recovery logic, and no attack-tooling integration.
No accuracy or training claims are made; validation is limited to shape,
residual connectivity, gradient flow, and serialization unit tests on CPU.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn


def _bounded_int(name: str, value: int, low: int, high: int) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")


class ResidualBlock1D(nn.Module):
    """Basic residual block for 1D waveforms: Conv-BN-ReLU-Conv-BN + skip.

    The skip connection is a 1x1 conv when the channel count changes,
    and an identity when shapes already match.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        stride: int = 1,
    ) -> None:
        super().__init__()
        _bounded_int("in_channels", in_channels, 1, 128)
        _bounded_int("out_channels", out_channels, 1, 128)
        _bounded_int("kernel_size", kernel_size, 1, 15)
        _bounded_int("stride", stride, 1, 2)
        if kernel_size % 2 == 0:
            raise ValueError("kernel_size must be odd to align the residual branches")
        padding = kernel_size // 2
        self.conv1 = nn.Conv1d(
            in_channels, out_channels, kernel_size=kernel_size,
            stride=stride, padding=padding, bias=False,
        )
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Conv1d(
            out_channels, out_channels, kernel_size=kernel_size,
            stride=1, padding=padding, bias=False,
        )
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU(inplace=True)

        if stride != 1 or in_channels != out_channels:
            self.downsample: nn.Module = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm1d(out_channels),
            )
        else:
            self.downsample = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = self.downsample(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + identity
        return self.relu(out)


class SideChannelResNet1D(nn.Module):
    """Residual 1D classification backbone for project-owned synthetic waveforms.

    Accepts input of shape ``(batch, in_channels, input_length)`` or the
    ``(batch, input_length)`` convenience form (a channel axis is added).
    Feature extraction is a stem plus residual stages followed by adaptive
    average pooling, so the classifier head is independent of ``input_length``.
    Output logits have shape ``(batch, num_classes)``.
    """

    def __init__(
        self,
        input_length: int = 256,
        num_classes: int = 4,
        in_channels: int = 1,
        stem_channels: int = 16,
        stage_channels: tuple[int, ...] = (32, 64),
        blocks_per_stage: int = 2,
        fc_dim: int = 64,
        dropout_p: float = 0.25,
    ) -> None:
        super().__init__()
        _bounded_int("input_length", input_length, 32, 4096)
        _bounded_int("num_classes", num_classes, 2, 64)
        _bounded_int("in_channels", in_channels, 1, 8)
        _bounded_int("stem_channels", stem_channels, 1, 128)
        _bounded_int("blocks_per_stage", blocks_per_stage, 1, 4)
        _bounded_int("fc_dim", fc_dim, 1, 256)
        if not isinstance(stage_channels, tuple) or not 1 <= len(stage_channels) <= 3:
            raise ValueError("stage_channels must be a tuple with 1 to 3 entries")
        for channels in stage_channels:
            _bounded_int("stage_channels entry", channels, 1, 128)
        if (type(dropout_p) not in (int, float) or not math.isfinite(dropout_p)
                or not 0.0 <= dropout_p < 1.0):
            raise ValueError("dropout_p must be a finite number in [0, 1)")

        self.in_channels = in_channels
        self.input_length = input_length
        self.num_classes = num_classes

        self.stem = nn.Sequential(
            nn.Conv1d(in_channels, stem_channels, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm1d(stem_channels),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(kernel_size=3, stride=2, padding=1),
        )

        stages: list[nn.Module] = []
        prev_channels = stem_channels
        for channels in stage_channels:
            for block_index in range(blocks_per_stage):
                stride = 2 if block_index == 0 else 1
                stages.append(
                    ResidualBlock1D(
                        in_channels=prev_channels,
                        out_channels=channels,
                        stride=stride,
                    )
                )
                prev_channels = channels
        self.stages = nn.Sequential(*stages)

        self.pool = nn.AdaptiveAvgPool1d(output_size=1)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(prev_channels, fc_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_p),
            nn.Linear(fc_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not isinstance(x, torch.Tensor):
            raise TypeError("input must be a torch.Tensor")
        if x.layout != torch.strided or not x.is_floating_point():
            raise ValueError("input must be a dense floating-point tensor")
        if x.dim() == 2:
            x = x.unsqueeze(1)
        if x.dim() != 3:
            raise ValueError(
                f"expected 2D or 3D input, got shape {tuple(x.shape)}"
            )
        if not 1 <= x.shape[0] <= 64:
            raise ValueError("batch size must be in [1, 64]")
        if x.shape[1] != self.in_channels:
            raise ValueError(f"expected {self.in_channels} input channels")
        if x.device != self.stem[0].weight.device or x.dtype != self.stem[0].weight.dtype:
            raise ValueError("input device and dtype must match the model")
        if x.shape[-1] != self.input_length:
            raise ValueError(
                f"input_length mismatch: model expects {self.input_length}, got {x.shape[-1]}"
            )
        if not torch.isfinite(x).all():
            raise ValueError("input contains non-finite values")
        features = self.stem(x)
        features = self.stages(features)
        pooled = self.pool(features)
        return self.classifier(pooled)

    def predict_probabilities(self, x: torch.Tensor) -> torch.Tensor:
        """Return probabilities without gradients; leave the model in eval mode.

        Call train() explicitly before resuming training, matching the existing
        CNN inference-helper convention.
        """
        self.eval()
        with torch.no_grad():
            return torch.softmax(self.forward(x), dim=-1)
