"""Neural Network Architectures and Training Pipelines for PQC Side-Channel & LWE Analysis."""

from .resnet1d import SideChannelResNet1D
from .side_channel_cnn import SideChannel1DCNN, LWEDistinguisherMLP
from .train_side_channel import train_side_channel_model, train_lwe_distinguisher

__all__ = [
    "SideChannel1DCNN",
    "SideChannelResNet1D",
    "LWEDistinguisherMLP",
    "train_side_channel_model",
    "train_lwe_distinguisher",
]
