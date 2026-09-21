"""
Unit tests for CPU Cache Timing Simulator & Leakage Models (WS-P10.2).
"""

import pytest
from pqc_bench.hardware.cache_timing import CacheTimingSimulator, analyze_polynomial_cache_behavior

def test_cache_timing_simulator_init():
    sim = CacheTimingSimulator(l1_size_kb=32, l3_size_kb=2048, line_size=64)
    assert sim.l1_lines == 512
    assert sim.l3_lines == 32768

def test_simulate_flush_reload():
    sim = CacheTimingSimulator()
    result = sim.simulate_flush_reload([4, 12, 28], total_accesses=100)
    assert result["attack_type"] == "Flush+Reload"
    assert "leakage_detected" in result
    assert "leakage_score" in result
    assert result["total_samples"] == 100
    assert isinstance(result["hit_counts"], dict)

def test_simulate_prime_probe():
    sim = CacheTimingSimulator()
    result = sim.prime_probe_sets = sim.simulate_prime_probe(memory_sets=32, samples=50)
    assert result["attack_type"] == "Prime+Probe"
    assert result["memory_sets"] == 32
    assert "max_contention_ratio" in result
    assert isinstance(result["vulnerable_sets"], list)

def test_analyze_polynomial_cache_behavior():
    coeffs = [1, 255, 1023, 0, 42, 84, 168]
    report = analyze_polynomial_cache_behavior(coeffs)
    assert report["coefficient_count"] == len(coeffs)
    assert "flush_reload" in report
    assert "prime_probe" in report
    assert report["overall_cache_timing_risk"] in ["HIGH", "LOW"]
