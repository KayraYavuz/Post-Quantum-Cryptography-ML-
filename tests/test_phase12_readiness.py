import pytest
from core.readiness_score import ReadinessScoreEngine

def test_readiness_calculator_perfect():
    engine = ReadinessScoreEngine()
    metrics = {
        "algorithm": 100,
        "hardware": 100,
        "cloud": 100,
        "library": 100
    }
    score = engine.calculate_score(metrics)
    assert score == 100.0

def test_readiness_calculator_partial():
    engine = ReadinessScoreEngine()
    metrics = {
        "algorithm": 50,
        "hardware": 50,
        "cloud": 50,
        "library": 50
    }
    score = engine.calculate_score(metrics)
    assert score == 50.0
