"""Bounded Transformer for general, project-owned synthetic waveform classes.

No cryptographic labels, key recovery, trace import, or attack integration.
Uses PyTorch's maintained MultiheadAttention rather than a custom attention kernel.
"""

from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F

from .resnet1d import _bounded_int


class _EncoderBlock(nn.Module):
    def __init__(self, d_model: int, num_heads: int, ff_dim: int, dropout_p: float):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attention = nn.MultiheadAttention(
            d_model, num_heads, dropout=dropout_p, batch_first=True,
        )
        self.norm2 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, ff_dim), nn.GELU(), nn.Dropout(dropout_p),
            nn.Linear(ff_dim, d_model),
        )
        self.dropout = nn.Dropout(dropout_p)

    def forward(self, x: torch.Tensor, token_mask: torch.Tensor) -> torch.Tensor:
        normalized = self.norm1(x)
        attended, _ = self.attention(
            normalized, normalized, normalized,
            key_padding_mask=token_mask, need_weights=False,
        )
        x = x + self.dropout(attended)
        x = x + self.dropout(self.ff(self.norm2(x)))
        return x.masked_fill(token_mask.unsqueeze(-1), 0)


class WaveformTransformer1D(nn.Module):
    """Patchwise multi-head self-attention classifier; returns (batch, classes).

    ResNet-compatible input shapes: (B, C, L), or (B, L) for one channel.
    Optional boolean padding_mask is (B, L): True ignores that sample in all
    channels. Partial patches zero masked samples; fully masked patches are
    excluded as attention keys/values and from mean pooling. Each row must
    contain a valid sample. This is a padding mask, not a causal attention mask.

    Fixed sinusoidal positions encode patch order; no phase-shift robustness
    or accuracy claim is made. Input length is fixed per model, 32..4096;
    at most 256 patch tokens and 64 examples are accepted per forward call.
    """

    def __init__(
        self,
        input_length: int = 256,
        num_classes: int = 4,
        in_channels: int = 1,
        d_model: int = 32,
        num_heads: int = 4,
        num_layers: int = 2,
        ff_dim: int = 64,
        fc_dim: int = 64,
        dropout_p: float = 0.25,
        patch_size: int = 8,
    ) -> None:
        super().__init__()
        for name, value, low, high in (
            ('input_length', input_length, 32, 4096),
            ('num_classes', num_classes, 2, 64),
            ('in_channels', in_channels, 1, 8),
            ('d_model', d_model, 4, 128),
            ('num_heads', num_heads, 1, 8),
            ('num_layers', num_layers, 1, 4),
            ('ff_dim', ff_dim, 4, 512),
            ('fc_dim', fc_dim, 1, 256),
            ('patch_size', patch_size, 1, 64),
        ):
            _bounded_int(name, value, low, high)
        if d_model % 2 or d_model % num_heads:
            raise ValueError('d_model must be even and divisible by num_heads')
        tokens = (input_length + patch_size - 1) // patch_size
        if tokens > 256:
            raise ValueError('configuration exceeds 256 patch tokens')
        if (type(dropout_p) not in (int, float) or not math.isfinite(dropout_p)
                or not 0 <= dropout_p < 1):
            raise ValueError('dropout_p must be a finite number in [0, 1)')
        self.input_length = input_length
        self.num_classes = num_classes
        self.in_channels = in_channels
        self.patch_size = patch_size
        self.num_tokens = tokens
        self.patch_projection = nn.Linear(in_channels * patch_size, d_model)
        positions = torch.arange(tokens, dtype=torch.float32).unsqueeze(1)
        frequencies = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000) / d_model))
        encoding = torch.zeros(1, tokens, d_model)
        encoding[0, :, 0::2] = torch.sin(positions * frequencies)
        encoding[0, :, 1::2] = torch.cos(positions * frequencies)
        self.register_buffer('position_encoding', encoding)
        self.blocks = nn.ModuleList(
            [_EncoderBlock(d_model, num_heads, ff_dim, dropout_p) for _ in range(num_layers)]
        )
        self.norm = nn.LayerNorm(d_model)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, fc_dim), nn.ReLU(), nn.Dropout(dropout_p),
            nn.Linear(fc_dim, num_classes),
        )

    def forward(
        self, x: torch.Tensor, padding_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if not isinstance(x, torch.Tensor):
            raise TypeError('input must be a torch.Tensor')
        if x.layout != torch.strided or not x.is_floating_point():
            raise ValueError('input must be a dense floating-point tensor')
        if x.dim() == 2:
            x = x.unsqueeze(1)
        if x.dim() != 3:
            raise ValueError('expected 2D or 3D input')
        if not 1 <= x.shape[0] <= 64:
            raise ValueError('batch size must be in [1, 64]')
        if x.shape[1] != self.in_channels:
            raise ValueError(f'expected {self.in_channels} input channels')
        if x.shape[-1] != self.input_length:
            raise ValueError(f'input_length mismatch: expected {self.input_length}')
        weight = self.patch_projection.weight
        if x.device != weight.device or x.dtype != weight.dtype:
            raise ValueError('input device and dtype must match the model')
        if not torch.isfinite(x).all():
            raise ValueError('input contains non-finite values')
        batch = x.shape[0]
        if padding_mask is None:
            padding_mask = torch.zeros(batch, self.input_length, dtype=torch.bool, device=x.device)
        else:
            if not isinstance(padding_mask, torch.Tensor):
                raise TypeError('padding_mask must be a torch.Tensor')
            if padding_mask.layout != torch.strided or padding_mask.dtype != torch.bool:
                raise ValueError('padding_mask must be a dense boolean tensor')
            if padding_mask.shape != (batch, self.input_length):
                raise ValueError('padding_mask must have shape (batch, input_length)')
            if padding_mask.device != x.device:
                raise ValueError('padding_mask device must match input')
            if padding_mask.all(dim=1).any():
                raise ValueError('each row must contain at least one unmasked sample')
        # Mask before projection so even partially masked patches are independent
        # of ignored values. End padding is always treated as masked, not data.
        x = x.masked_fill(padding_mask.unsqueeze(1), 0)
        extra = self.num_tokens * self.patch_size - self.input_length
        x = F.pad(x, (0, extra))
        sample_mask = F.pad(padding_mask, (0, extra), value=True)
        token_mask = sample_mask.reshape(batch, self.num_tokens, self.patch_size).all(dim=-1)
        patches = x.unfold(-1, self.patch_size, self.patch_size)
        patches = patches.permute(0, 2, 1, 3).reshape(batch, self.num_tokens, -1)
        tokens = self.patch_projection(patches) + self.position_encoding
        tokens = tokens.masked_fill(token_mask.unsqueeze(-1), 0)
        for block in self.blocks:
            tokens = block(tokens, token_mask)
        tokens = self.norm(tokens).masked_fill(token_mask.unsqueeze(-1), 0)
        counts = (~token_mask).sum(dim=1, keepdim=True).to(tokens.dtype)
        return self.classifier(tokens.sum(dim=1) / counts)

    def predict_probabilities(
        self, x: torch.Tensor, padding_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Return softmax without gradients; leave model in eval mode like ResNet."""
        self.eval()
        with torch.no_grad():
            return torch.softmax(self(x, padding_mask=padding_mask), dim=-1)
