import pytest
import torch
import torch.nn as nn
from src.pqc_bench.core.model_integrity import verify_integrity, get_model_hash

class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 2)

def test_integrity_verification():
    model = SimpleModel()
    expected_hash = get_model_hash(model)
    
    # Positive case
    assert verify_integrity(model, expected_hash) is True
    
    # Negative case (modify weights)
    with torch.no_grad():
        model.fc.weight[0, 0] += 0.1
    
    assert verify_integrity(model, expected_hash) is False
