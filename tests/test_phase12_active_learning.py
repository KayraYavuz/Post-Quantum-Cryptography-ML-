import pytest
import numpy as np
from core.active_learning import EntropySelector

def test_entropy_calculation():
    selector = EntropySelector(model=None)
    trace = np.array([0.1, 0.2, 0.7])
    entropy = selector.calculate_entropy(trace)
    assert entropy >= 0

def test_selection():
    selector = EntropySelector(model=None)
    traces = [np.array([0.1, 0.1]), np.array([0.9, 0.1]), np.array([0.5, 0.5])]
    selected = selector.select_informative_traces(traces, n_samples=1)
    # [0.5, 0.5] entropisi en yüksek olandır
    assert np.array_equal(selected[0], np.array([0.5, 0.5]))
