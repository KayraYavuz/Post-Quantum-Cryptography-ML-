import pytest
import numpy as np
from src.pqc_bench.models.active_learning import calculate_trace_entropy, select_critical_traces

def test_calculate_trace_entropy():
    trace = np.random.normal(0, 1, 1000)
    e = calculate_trace_entropy(trace)
    assert e > 0

def test_select_critical_traces():
    traces = [np.random.normal(0, 1, 100) for _ in range(20)]
    indices = select_critical_traces(traces, top_n=5)
    assert len(indices) == 5
    assert all(i < 20 for i in indices)
