import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

"""Unit tests for WS-P12.1 Model Weight Integrity & Poisoning Detection Engine."""

import tempfile
import torch
import pytest

from core.model_integrity import ModelIntegrityValidator


def test_state_dict_hash_consistency():
    """Test that identical state_dicts produce identical SHA-256 hashes."""
    validator = ModelIntegrityValidator()
    sd1 = {
        "layer1.weight": torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
        "layer1.bias": torch.tensor([0.1, 0.2]),
    }
    sd2 = {
        "layer1.weight": torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
        "layer1.bias": torch.tensor([0.1, 0.2]),
    }

    h1 = validator.compute_state_dict_hash(sd1)
    h2 = validator.compute_state_dict_hash(sd2)

    assert len(h1) == 64
    assert h1 == h2


def test_state_dict_hash_sensitivity():
    """Test that modifying a single weight alters the SHA-256 hash."""
    validator = ModelIntegrityValidator()
    sd1 = {
        "layer1.weight": torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
    }
    sd_modified = {
        "layer1.weight": torch.tensor([[1.0, 2.0], [3.0, 4.1]]),
    }

    h1 = validator.compute_state_dict_hash(sd1)
    h2 = validator.compute_state_dict_hash(sd_modified)

    assert h1 != h2


def test_baseline_registration_and_verification():
    """Test baseline registration and verification workflow."""
    validator = ModelIntegrityValidator()
    sd = {"weight": torch.tensor([1.0, 2.0, 3.0])}

    validator.register_baseline("model_v1", sd)
    assert validator.verify_state_dict("model_v1", sd) is True

    sd_tampered = {"weight": torch.tensor([1.0, 2.0, 99.0])}
    assert validator.verify_state_dict("model_v1", sd_tampered) is False

    with pytest.raises(ValueError):
        validator.verify_state_dict("unknown_model", sd)


def test_detect_poisoning_normal_vs_tampered():
    """Test model poisoning / tampering detection."""
    validator = ModelIntegrityValidator()
    torch.manual_seed(42)
    orig_sd = {
        "fc.weight": torch.randn((10, 10)),
        "fc.bias": torch.randn((10,)),
    }

    # Slight perturbation (normal fine-tuning)
    fine_tuned_sd = {
        "fc.weight": orig_sd["fc.weight"] + torch.randn((10, 10)) * 0.001,
        "fc.bias": orig_sd["fc.bias"] + torch.randn((10,)) * 0.001,
    }
    res_normal = validator.detect_poisoning(orig_sd, fine_tuned_sd, max_relative_change=0.25)
    assert res_normal["is_poisoned"] is False

    # Heavy poisoning / backdoor injection on fc.weight
    poisoned_sd = {
        "fc.weight": orig_sd["fc.weight"].clone(),
        "fc.bias": orig_sd["fc.bias"].clone(),
    }
    poisoned_sd["fc.weight"][0, 0] = 50.0  # Massive spike
    res_poisoned = validator.detect_poisoning(orig_sd, poisoned_sd, max_relative_change=0.25)
    assert res_poisoned["is_poisoned"] is True
    assert len(res_poisoned["anomalies"]) > 0


def test_compute_file_hash():
    """Test file SHA-256 calculation."""
    validator = ModelIntegrityValidator()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"PQC ML Model Weights Binary Stream")
        tmp_path = tmp.name

    try:
        h = validator.compute_file_hash(tmp_path)
        assert len(h) == 64
        # Verify deterministic
        h2 = validator.compute_file_hash(tmp_path)
        assert h == h2
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
