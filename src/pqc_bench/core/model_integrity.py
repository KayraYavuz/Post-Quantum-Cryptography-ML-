"""WS-P12.1 — Model Weight Integrity Validator & Poisoning Protection.

Scope: SHA-256 integrity verification, baseline manifest tracking, and model
poisoning / tampering detection for neural network state dictionaries and model files.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional
import torch


class ModelIntegrityValidator:
    """SHA-256 based model weight integrity and poisoning detection engine."""

    def __init__(self, baseline_manifest: Optional[Dict[str, str]] = None) -> None:
        self.baseline_manifest: Dict[str, str] = baseline_manifest or {}

    @staticmethod
    def compute_file_hash(filepath: str) -> str:
        """Compute SHA-256 hash of a binary file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def compute_state_dict_hash(state_dict: Dict[str, torch.Tensor]) -> str:
        """Compute deterministic SHA-256 hash of a PyTorch state_dict."""
        sha256_hash = hashlib.sha256()
        sorted_keys = sorted(state_dict.keys())
        for key in sorted_keys:
            tensor = state_dict[key]
            sha256_hash.update(key.encode("utf-8"))
            if isinstance(tensor, torch.Tensor):
                tensor_bytes = tensor.detach().cpu().numpy().tobytes()
                sha256_hash.update(tensor_bytes)
        return sha256_hash.hexdigest()

    def register_baseline(self, model_name: str, state_dict: Dict[str, torch.Tensor]) -> str:
        """Register a model's state_dict hash as the trusted baseline."""
        h = self.compute_state_dict_hash(state_dict)
        self.baseline_manifest[model_name] = h
        return h

    def verify_state_dict(self, model_name: str, state_dict: Dict[str, torch.Tensor]) -> bool:
        """Verify if current state_dict matches the registered baseline hash."""
        if model_name not in self.baseline_manifest:
            raise ValueError(f"No baseline registered for model: {model_name}")
        current_hash = self.compute_state_dict_hash(state_dict)
        return current_hash == self.baseline_manifest[model_name]

    def detect_poisoning(
        self,
        original_state_dict: Dict[str, torch.Tensor],
        current_state_dict: Dict[str, torch.Tensor],
        max_relative_change: float = 0.25,
    ) -> Dict[str, Any]:
        """Detect potential model poisoning or unauthorized weight tampering."""
        anomalies = []
        total_params = 0
        max_diff = 0.0

        for key, orig_tensor in original_state_dict.items():
            if key not in current_state_dict:
                anomalies.append({"parameter": key, "issue": "missing_tensor"})
                continue
            curr_tensor = current_state_dict[key]
            if orig_tensor.shape != curr_tensor.shape:
                anomalies.append({"parameter": key, "issue": "shape_mismatch"})
                continue

            orig_norm = torch.norm(orig_tensor.float()).item()
            curr_norm = torch.norm(curr_tensor.float()).item()
            diff_norm = torch.norm((orig_tensor - curr_tensor).float()).item()

            rel_diff = diff_norm / (orig_norm + 1e-8)
            if rel_diff > max_relative_change:
                anomalies.append({
                    "parameter": key,
                    "issue": "excessive_weight_shift",
                    "relative_change": rel_diff,
                })
            if rel_diff > max_diff:
                max_diff = rel_diff
            total_params += orig_tensor.numel()

        is_poisoned = len(anomalies) > 0
        return {
            "is_poisoned": is_poisoned,
            "anomalies": anomalies,
            "max_relative_change": max_diff,
            "total_parameters_checked": total_params,
        }
