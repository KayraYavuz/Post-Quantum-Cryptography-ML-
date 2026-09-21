import pytest
from core.pqc_readiness_engine import PQCReadinessEngine

def test_readiness_score_calculation():
    # Agility: 85, HW: 70, SC: 90, CBOM: 95
    # (85*0.3) + (70*0.2) + (90*0.3) + (95*0.2)
    # 25.5 + 14 + 27 + 19 = 85.5
    engine = PQCReadinessEngine(crypto_agility=85.0, hardware_compatibility=70.0, side_channel_resistance=90.0, cbom_coverage=95.0)
    assert engine.calculate_score() == 85.5

def test_risk_levels():
    engine = PQCReadinessEngine()
    assert engine.get_risk_level(95.0) == "EXCELLENT"
    assert engine.get_risk_level(80.0) == "GOOD"
    assert engine.get_risk_level(60.0) == "MODERATE"
    assert engine.get_risk_level(30.0) == "CRITICAL"

def test_boundary_values():
    engine = PQCReadinessEngine(120, -10, 50, 50) # Clamping test
    assert engine.crypto_agility == 100
    assert engine.hardware_compatibility == 0
