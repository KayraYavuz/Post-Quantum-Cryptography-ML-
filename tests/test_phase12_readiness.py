import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from core.readiness_score import PQCReadinessCalculator

def test_readiness_calculator_perfect():
    config = {
        "algorithm_migration": "full_pqc",
        "side_channel_protection": 3,
        "hardware_security": True,
        "fips_compliant": True,
        "fuzzing_passed": True,
        "model_integrity_verified": True
    }
    calc = PQCReadinessCalculator(config)
    score = calc.calculate_score()
    assert score == 100.0
    assert len(calc.get_recommendations()) == 0

def test_readiness_calculator_partial():
    config = {
        "algorithm_migration": "hybrid",
        "side_channel_protection": 2,
        "hardware_security": False,
        "fips_compliant": False,
        "fuzzing_passed": True,
        "model_integrity_verified": True
    }
    calc = PQCReadinessCalculator(config)
    score = calc.calculate_score()
    assert 50.0 <= score <= 80.0
    assert len(calc.get_recommendations()) > 0
