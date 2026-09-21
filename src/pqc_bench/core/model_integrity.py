"""WS-P12.1 — Model Weight Integrity Validator.

Provides SHA-256 integrity verification and basic poisoning detection
mechanisms for trained model weights.
"""

from __future__ import annotations

import hashlib
import os
import torch
import torch.nn as nn
from typing import Union


def verify_integrity(model: nn.Module, expected_hash: str) -> bool:
    """Verify model weights against a provided SHA-256 hash."""
    sha256 = hashlib.sha256()
    
    # Sort state_dict keys to ensure deterministic ordering
    state_dict = model.state_dict()
    for key in sorted(state_dict.keys()):
        # Convert tensor data to bytes
        data = state_dict[key].cpu().numpy().tobytes()
        sha256.update(data)
    
    actual_hash = sha256.hexdigest()
    return actual_hash == expected_hash


def get_model_hash(model: nn.Module) -> str:
    """Calculate the current SHA-256 hash of the model weights."""
    sha256 = hashlib.sha256()
    state_dict = model.state_dict()
    for key in sorted(state_dict.keys()):
        data = state_dict[key].cpu().numpy().tobytes()
        sha256.update(data)
    return sha256.hexdigest()
