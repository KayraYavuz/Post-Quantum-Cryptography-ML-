import pytest
from core.readiness_score import ReadinessScoreEngine

def test_readiness_score_basic():
    engine = ReadinessScoreEngine()
    engine.update_metric("pqc_algorithm_adoption", 80.0)
    engine.update_metric("hardware_acceleration", 90.0)
    engine.update_metric("compliance_rating", 70.0)
    engine.update_metric("fuzzing_coverage", 60.0)
    
    # (80 * 0.4) + (90 * 0.2) + (70 * 0.2) + (60 * 0.2)
    # 32 + 18 + 14 + 12 = 76
    assert engine.calculate_score() == 76.0
    assert engine.get_readiness_level() == "PROD_READY"

def test_readiness_score_bounds():
    engine = ReadinessScoreEngine()
    engine.update_metric("pqc_algorithm_adoption", 150.0) # Should clip to 100
    engine.update_metric("hardware_acceleration", -50.0)  # Should clip to 0
    engine.update_metric("compliance_rating", 0.0)
    engine.update_metric("fuzzing_coverage", 0.0)
    
    # (100 * 0.4) + (0 * 0.2) + 0 + 0 = 40
    assert engine.calculate_score() == 40.0
    assert engine.get_readiness_level() == "NON_COMPLIANT"
