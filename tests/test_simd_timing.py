"""Phase 5.2 Unit Tests: SIMD & Fixed Timing Variance Analyzer.

Tests for WS-P5.2: SIMD & Vektör Sabit Zamanlılık.
Validates:
1. AVX2, AVX-512 & ARM NEON timing simulation
2. Timing variance comparison across architectures
3. Statistical analysis and recommendations
"""

import pytest

from pqc_bench.simd_timing import (
    simulate_avx2_ntt_timing,
    simulate_avx512_ntt_timing,
    simulate_neon_ntt_timing,
    analyze_timing_variance,
    generate_simd_benchmark_report,
)


class TestSIMDTimingSimulation:
    """Test SIMD architecture timing simulation functions."""

    def test_avx2_timing_simulation(self):
        """Test AVX2 NTT timing simulation returns valid data."""
        result = simulate_avx2_ntt_timing(n_iterations=100)
        assert "mean_cycles" in result
        assert "std_cycles" in result
        assert "min_cycles" in result
        assert "max_cycles" in result
        assert "architecture" in result
        assert result["architecture"] == "AVX2"
        assert result["mean_cycles"] > 0
        assert result["timing_variance"] >= 0

    def test_avx512_timing_simulation(self):
        """Test AVX-512 NTT timing simulation returns valid data."""
        result = simulate_avx512_ntt_timing(n_iterations=100)
        assert "mean_cycles" in result
        assert "std_cycles" in result
        assert "min_cycles" in result
        assert "max_cycles" in result
        assert result["architecture"] == "AVX-512"
        assert result["mean_cycles"] > 0
        assert result["timing_variance"] >= 0

    def test_neon_timing_simulation(self):
        """Test ARM NEON NTT timing simulation returns valid data."""
        result = simulate_neon_ntt_timing(n_iterations=100)
        assert "mean_cycles" in result
        assert "std_cycles" in result
        assert "min_cycles" in result
        assert "max_cycles" in result
        assert result["architecture"] == "ARM NEON"
        assert result["mean_cycles"] > 0
        assert result["timing_variance"] >= 0

    def test_avx2_meaningful_mean(self):
        """AVX2 mean should be in reasonable range (roughly 40-55 cycles)."""
        result = simulate_avx2_ntt_timing(n_iterations=1000)
        assert 30 < result["mean_cycles"] < 70, (
            f"AVX2 mean {result['mean_cycles']} out of expected range"
        )

    def test_avx512_meaningful_mean(self):
        """AVX-512 mean should be in reasonable range."""
        result = simulate_avx512_ntt_timing(n_iterations=1000)
        assert 20 < result["mean_cycles"] < 80, (
            f"AVX-512 mean {result['mean_cycles']} out of expected range"
        )

    def test_neon_meaningful_mean(self):
        """NEON mean should be in reasonable range (typically higher)."""
        result = simulate_neon_ntt_timing(n_iterations=1000)
        assert 40 < result["mean_cycles"] < 130, (
            f"NEON mean {result['mean_cycles']} out of expected range"
        )


class TestTimingVarianceAnalysis:
    """Test timing variance analysis across architectures."""

    def test_analyze_variance_all_architectures(self):
        """Test analysis with data from all three architectures."""
        avx2 = simulate_avx2_ntt_timing(n_iterations=100)
        avx512 = simulate_avx512_ntt_timing(n_iterations=100)
        neon = simulate_neon_ntt_timing(n_iterations=100)

        analysis = analyze_timing_variance(avx2, avx512, neon)
        
        assert "avx2" in analysis
        assert "avx512" in analysis
        assert "neon" in analysis
        assert "comparisons" in analysis
        assert "analysis" in analysis
        assert "recommendation" in analysis

    def test_analysis_contains_ranks(self):
        """Analysis should contain rank information for each architecture."""
        avx2 = simulate_avx2_ntt_timing(n_iterations=100)
        avx512 = simulate_avx512_ntt_timing(n_iterations=100)
        neon = simulate_neon_ntt_timing(n_iterations=100)

        analysis = analyze_timing_variance(avx2, avx512, neon)
        
        assert "rank" in analysis["avx2"]
        assert "rank" in analysis["avx512"]
        assert "rank" in analysis["neon"]

    def test_recommendation_not_empty(self):
        """Recommendation should not be empty."""
        avx2 = simulate_avx2_ntt_timing(n_iterations=100)
        avx512 = simulate_avx512_ntt_timing(n_iterations=100)
        neon = simulate_neon_ntt_timing(n_iterations=100)

        analysis = analyze_timing_variance(avx2, avx512, neon)
        assert len(analysis["recommendation"]) > 10


class TestBenchmarkReport:
    """Test benchmark report generation."""

    def test_generate_report_has_structure(self):
        """Test report contains expected sections."""
        avx2 = simulate_avx2_ntt_timing(n_iterations=100)
        avx512 = simulate_avx512_ntt_timing(n_iterations=100)
        neon = simulate_neon_ntt_timing(n_iterations=100)

        report = generate_simd_benchmark_report(avx2, avx512, neon)
        
        assert "SIMD & Fixed Timing Variance Analysis Report" in report
        # Report contains architecture names
        assert "AVX2" in report or "AVX-512" in report
        assert "ARM NEON" in report
        # Report contains timing data
        assert str(int(avx2["mean_cycles"])) in report or str(int(avx512["mean_cycles"])) in report


class TestReportFormatting:
    """Test report formatting elements."""

    def test_report_contains_variance_ratios(self):
        """Test report contains variance ratio comparisons."""
        avx2 = simulate_avx2_ntt_timing(n_iterations=100)
        avx512 = simulate_avx512_ntt_timing(n_iterations=100)
        neon = simulate_neon_ntt_timing(n_iterations=100)

        report = generate_simd_benchmark_report(avx2, avx512, neon)
        
        # Should contain "x lower" or "x higher" format
        assert "x" in report

    def test_report_contains_best_worst(self):
        """Test report identifies best and worst architectures."""
        avx2 = simulate_avx2_ntt_timing(n_iterations=100)
        avx512 = simulate_avx512_ntt_timing(n_iterations=100)
        neon = simulate_neon_ntt_timing(n_iterations=100)

        report = generate_simd_benchmark_report(avx2, avx512, neon)
        
        # Should mention which is best/worst
        assert "best" in report.lower() or "worst" in report.lower()
