"""PyTorch Neural Network Architectures for PQC Side-Channel & LWE Analysis.

Includes:
- SideChannel1DCNN: 1D Convolutional Neural Network for power/EM trace leakage detection.
- LWEDistinguisherMLP: Multi-layer perceptron for LWE secret bit recovery and distinguishing.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class SideChannel1DCNN(nn.Module):
    """1D Convolutional Neural Network for PQC Side-Channel Power/EM Leakage Analysis.

    Designed according to deep-learning side-channel analysis (DLSCA) best practices
    (e.g., ASCAD benchmark architecture adapted for post-quantum NTT/unpacking traces).
    """

    def __init__(
        self,
        input_length: int = 256,
        num_classes: int = 9,  # Default: Hamming Weight 0..8
        in_channels: int = 1,
        conv_channels: tuple[int, ...] = (32, 64, 128),
        kernel_sizes: tuple[int, ...] = (7, 5, 3),
        fc_dim: int = 128,
        dropout_p: float = 0.25,
    ) -> None:
        super().__init__()
        self.input_length = input_length
        self.num_classes = num_classes

        # Feature Extractor Blocks
        self.block1 = nn.Sequential(
            nn.Conv1d(
                in_channels,
                conv_channels[0],
                kernel_size=kernel_sizes[0],
                stride=2,
                padding=kernel_sizes[0] // 2,
            ),
            nn.BatchNorm1d(conv_channels[0]),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(kernel_size=2, stride=2),
        )

        self.block2 = nn.Sequential(
            nn.Conv1d(
                conv_channels[0],
                conv_channels[1],
                kernel_size=kernel_sizes[1],
                stride=1,
                padding=kernel_sizes[1] // 2,
            ),
            nn.BatchNorm1d(conv_channels[1]),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(kernel_size=2, stride=2),
        )

        self.block3 = nn.Sequential(
            nn.Conv1d(
                conv_channels[1],
                conv_channels[2],
                kernel_size=kernel_sizes[2],
                stride=1,
                padding=kernel_sizes[2] // 2,
            ),
            nn.BatchNorm1d(conv_channels[2]),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(output_size=4),
        )

        # Classification Head
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(conv_channels[2] * 4, fc_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_p),
            nn.Linear(fc_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass. Expects x of shape (batch_size, input_length) or (batch_size, 1, input_length)."""
        if x.dim() == 2:
            x = x.unsqueeze(1)
        feat = self.block1(x)
        feat = self.block2(feat)
        feat = self.block3(feat)
        logits = self.classifier(feat)
        return logits

    def predict_probabilities(self, x: torch.Tensor) -> torch.Tensor:
        """Returns normalized class probabilities via Softmax."""
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            return F.softmax(logits, dim=-1)


class LWEDistinguisherMLP(nn.Module):
    """Multi-Layer Perceptron (MLP) for Learning With Errors (LWE) Secret Recovery & Distinguishing.

    Learns to differentiate valid LWE pairs (A, As + e mod q) from uniform random (A, u mod q)
    or directly predicts the secret vector coefficients.
    """

    def __init__(
        self,
        input_dim: int = 16,
        hidden_dims: tuple[int, ...] = (64, 128, 64),
        num_classes: int = 2,  # Binary: 1 = Valid LWE instance, 0 = Uniform random
        dropout_p: float = 0.2,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        prev_dim = input_dim

        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.LeakyReLU(negative_slope=0.1, inplace=True))
            layers.append(nn.Dropout(p=dropout_p))
            prev_dim = h_dim

        layers.append(nn.Linear(prev_dim, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass for LWE vector pairs. Shape: (batch_size, input_dim)."""
        return self.network(x)

    def distinguish_score(self, x: torch.Tensor) -> torch.Tensor:
        """Returns probability of sample being a valid LWE instance (class 1)."""
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probs = F.softmax(logits, dim=-1)
            return probs[:, 1]
