"""Conditional GAN components for general, project-owned synthetic waveforms.

Uses maintained PyTorch layers. No cryptographic labels, hardware trace import,
key recovery, training pipeline, or attack/service integration is provided.
Untrained outputs are not evidence of realism, augmentation benefit, or security.
"""

from __future__ import annotations

import torch
from torch import nn

from .resnet1d import _bounded_int


def _validate_float_tensor(name: str, value: torch.Tensor, weight: torch.Tensor) -> None:
    if not isinstance(value, torch.Tensor):
        raise TypeError(f'{name} must be a torch.Tensor')
    if value.layout != torch.strided or not value.is_floating_point():
        raise ValueError(f'{name} must be a dense floating-point tensor')
    if value.device != weight.device or value.dtype != weight.dtype:
        raise ValueError(f'{name} device and dtype must match the model')
    if not torch.isfinite(value).all():
        raise ValueError(f'{name} contains non-finite values')


class _ConditionalWaveformModule(nn.Module):
    def __init__(
        self, input_length: int, num_classes: int, in_channels: int,
        hidden_dim: int, embedding_dim: int,
    ) -> None:
        super().__init__()
        for name, value, low, high in (
            ('input_length', input_length, 32, 4096),
            ('num_classes', num_classes, 2, 64),
            ('in_channels', in_channels, 1, 8),
            ('hidden_dim', hidden_dim, 4, 256),
            ('embedding_dim', embedding_dim, 1, 64),
        ):
            _bounded_int(name, value, low, high)
        self.input_length = input_length
        self.num_classes = num_classes
        self.in_channels = in_channels
        self.label_embedding = nn.Embedding(num_classes, embedding_dim)

    def _condition(self, labels: torch.Tensor, batch: int) -> torch.Tensor:
        if not 1 <= batch <= 64:
            raise ValueError('batch size must be in [1, 64]')
        if not isinstance(labels, torch.Tensor):
            raise TypeError('labels must be a torch.Tensor')
        if labels.layout != torch.strided or labels.dtype != torch.long:
            raise ValueError('labels must be a dense torch.long tensor')
        if labels.shape != (batch,):
            raise ValueError('labels must have shape (batch,)')
        if labels.device != self.label_embedding.weight.device:
            raise ValueError('labels device must match the model')
        if ((labels < 0) | (labels >= self.num_classes)).any():
            raise ValueError('labels must be in [0, num_classes)')
        return self.label_embedding(labels)


class SyntheticWaveformGenerator(_ConditionalWaveformModule):
    """Map explicit noise (B, latent_dim) and generic class IDs to (B, C, L).

    A small conditional MLP baseline with tanh output in [-1, 1]. Class IDs
    denote only generic waveform families, never secret-dependent quantities.
    Supply noise explicitly for reproducibility; no global RNG is reset here.
    Configurations are bounded, and each call accepts 1..64 examples.
    """

    def __init__(
        self, input_length: int = 256, num_classes: int = 4,
        in_channels: int = 1, latent_dim: int = 32, hidden_dim: int = 64,
        embedding_dim: int = 16,
    ) -> None:
        _bounded_int('latent_dim', latent_dim, 1, 256)
        super().__init__(input_length, num_classes, in_channels, hidden_dim, embedding_dim)
        self.latent_dim = latent_dim
        self.network = nn.Sequential(
            nn.Linear(latent_dim + embedding_dim, hidden_dim), nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, hidden_dim), nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, in_channels * input_length), nn.Tanh(),
        )

    def forward(self, noise: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        _validate_float_tensor('noise', noise, self.network[0].weight)
        if noise.dim() != 2 or noise.shape[1] != self.latent_dim:
            raise ValueError('noise must have shape (batch, latent_dim)')
        condition = self._condition(labels, noise.shape[0])
        output = self.network(torch.cat((noise, condition), dim=1))
        return output.reshape(noise.shape[0], self.in_channels, self.input_length)

    def generate(self, noise: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """Generate without gradients; leave eval mode, like existing model helpers."""
        self.eval()
        with torch.no_grad():
            return self(noise, labels)


class SyntheticWaveformDiscriminator(_ConditionalWaveformModule):
    """Conditional real/fake scoring MLP, not a waveform-class classifier.

    Accepts (B, C, L), or (B, L) for C=1, matching classifier input shapes.
    Returns raw logits (B, 1), suitable for BCEWithLogitsLoss. The sigmoid
    helper reports model scores, not calibrated probabilities or realism.
    No normalization or clipping is silently applied to input waveforms.
    """

    def __init__(
        self, input_length: int = 256, num_classes: int = 4,
        in_channels: int = 1, hidden_dim: int = 64, embedding_dim: int = 16,
    ) -> None:
        super().__init__(input_length, num_classes, in_channels, hidden_dim, embedding_dim)
        self.network = nn.Sequential(
            nn.Linear(in_channels * input_length + embedding_dim, hidden_dim),
            nn.LeakyReLU(0.2), nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(0.2), nn.Linear(hidden_dim, 1),
        )

    def forward(self, waveforms: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        _validate_float_tensor('waveforms', waveforms, self.network[0].weight)
        if waveforms.dim() == 2:
            waveforms = waveforms.unsqueeze(1)
        if waveforms.dim() != 3:
            raise ValueError('expected 2D or 3D waveforms')
        if waveforms.shape[1] != self.in_channels:
            raise ValueError(f'expected {self.in_channels} input channels')
        if waveforms.shape[2] != self.input_length:
            raise ValueError(f'input_length mismatch: expected {self.input_length}')
        condition = self._condition(labels, waveforms.shape[0])
        return self.network(torch.cat((waveforms.flatten(1), condition), dim=1))

    def predict_probabilities(
        self, waveforms: torch.Tensor, labels: torch.Tensor,
    ) -> torch.Tensor:
        """Return sigmoid scores without gradients; leave the model in eval mode."""
        self.eval()
        with torch.no_grad():
            return torch.sigmoid(self(waveforms, labels))
