
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import pytest
from src.pqc_bench.core.readiness_score import ReadinessScoreEngine

def test_readiness_score_calculation():
    engine = ReadinessScoreEngine()
    result = engine.calculate_score()
    
    assert "readiness_score" in result
    assert 0 <= result["readiness_score"] <= 100
    assert result["status"] in ["CRITICAL", "WARNING", "READY"]
    assert "metrics" in result

def test_readiness_score_range():
    engine = ReadinessScoreEngine()
    result = engine.calculate_score()
    assert result["readiness_score"] >= 90 # Beklenen yüksek değer
