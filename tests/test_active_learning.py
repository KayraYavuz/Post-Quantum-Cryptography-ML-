import pytest
import numpy as np
from src.active_learning.selector import calculate_entropy, select_critical_traces

def test_calculate_entropy():
    signal = np.array([1, 0, 1, 0])
    entropy = calculate_entropy(signal)
    assert entropy >= 0

def test_select_critical_traces():
    traces = [np.array([1, 2, 3]), np.array([0, 0, 0]), np.array([10, 10, 10])]
    selected = select_critical_traces(traces, n_select=1)
    assert len(selected) == 1
    assert np.array_equal(selected[0], np.array([10, 10, 10]))
