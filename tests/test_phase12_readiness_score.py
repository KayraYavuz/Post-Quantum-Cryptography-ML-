import pytest
from core.readiness_score import get_engine

def test_readiness_score_calculation():
    engine = get_engine()
    metrics = {
        'algorithm': 90.0,
        'hardware': 80.0,
        'cloud': 70.0,
        'library': 85.0
    }
    # (90 * 0.4) + (80 * 0.2) + (70 * 0.2) + (85 * 0.2)
    # 36 + 16 + 14 + 17 = 83.0
    score = engine.calculate_score(metrics)
    assert score == 83.0
    assert 0 <= score <= 100

def test_readiness_score_clipping():
    engine = get_engine()
    metrics = {
        'algorithm': 150.0,  # OOB
        'hardware': 100.0,
        'cloud': 100.0,
        'library': 100.0
    }
    score = engine.calculate_score(metrics)
    assert score == 100.0
