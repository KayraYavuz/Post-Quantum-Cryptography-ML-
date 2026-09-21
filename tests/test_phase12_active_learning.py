import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import torch
import torch.nn as nn
from core.active_learning import EntropySelector, FineTuneEngine

class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 2)
    def forward(self, x):
        return self.fc(x)

def test_entropy_selection():
    model = SimpleModel()
    selector = EntropySelector(model)
    traces = torch.randn(20, 10)
    selected, indices = selector.select_critical_traces(traces, top_k=5)
    assert len(indices) == 5
    assert selected.shape == (5, 10)

def test_fine_tune_step():
    model = SimpleModel()
    engine = FineTuneEngine(model)
    traces = torch.randn(5, 10)
    labels = torch.randint(0, 2, (5,))
    loss = engine.train_step(traces, labels)
    assert isinstance(loss, float)
    assert loss >= 0

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
