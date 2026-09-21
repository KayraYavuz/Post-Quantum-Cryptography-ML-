"""
Tests for Hardware Power Calibration & Simulation Module (WS-P10.3).
"""

import pytest
from pqc_bench.hardware.power_calibration import PowerCalibrationEngine


def test_power_calibration_init():
    engine_x86 = PowerCalibrationEngine("x86_64")
    assert engine_x86.specs["node_nm"] == 7

    engine_arm = PowerCalibrationEngine("arm64")
    assert engine_arm.specs["node_nm"] == 5

    engine_apple = PowerCalibrationEngine("apple_silicon")
    assert engine_apple.specs["node_nm"] == 3

    with pytest.raises(ValueError):
        PowerCalibrationEngine("unknown_cpu")


def test_calibrate_operation():
    engine = PowerCalibrationEngine("apple_silicon")
    res = engine.calibrate_operation("ntt", iterations=5000)
    
    assert res["architecture"] == "apple_silicon"
    assert res["node_nm"] == 3
    assert res["operation"] == "ntt"
    assert res["iterations"] == 5000
    assert "estimated_power_mw" in res
    assert "estimated_energy_uj" in res
    assert res["estimated_power_mw"] > 0


def test_simulate_power_trace():
    engine = PowerCalibrationEngine("x86_64")
    trace = engine.simulate_power_trace("ml_kem_encaps", sample_points=100)
    
    assert isinstance(trace, list)
    assert len(trace) == 100
    assert all(isinstance(x, (int, float)) for x in trace)
    assert max(trace) > min(trace)  # verify variance/peaks exist
