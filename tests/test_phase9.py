"""
Phase 9 Unit Tests: Constant-Time Fuzzing Engine

Tests the ct_fuzzer module for ML-KEM and ML-DSA constant-time
fuzzing functionality, edge-case handling, and timing analysis.
"""

import pytest
from src.pqc_bench.fuzzing.ct_fuzzer import (
    constant_time_fuzz,
    fuzz_kem_implementation,
    fuzz_dsa_implementation,
    analyze_timing_variance,
    generate_edge_case_report,
    EDGE_CASES,
    KEM_PARAMS,
    DSA_PARAMS,
)


class TestEdgeCases:
    """Test that edge cases are properly generated and handled."""

    def test_edge_cases_have_varied_lengths(self):
        """Edge cases should have different lengths for KEM vs DSA testing."""
        lengths = set(len(ec) for ec in EDGE_CASES)
        assert len(lengths) >= 3, (
            f"Expected at least 3 different edge case lengths, got {len(lengths)}: {lengths}"
        )

    def test_edge_cases_include_zeros(self):
        """Should include zero-filled edge cases."""
        has_zero = any(ec == b"\x00" * len(ec) for ec in EDGE_CASES)
        assert has_zero, "Edge cases should include zero-filled patterns"

    def test_edge_cases_include_maximums(self):
        """Should include maximum-size edge cases."""
        has_max = any(ec == b"\xff" * len(ec) for ec in EDGE_CASES)
        assert has_max, "Edge cases should include maximum-size patterns"


class TestConstantTimeFuzzBasic:
    """Basic tests for the constant_time_fuzz function."""

    def mock_kem_func(self, ciphertext: bytes, params: str) -> dict:
        """Simple mock KEM function."""
        if len(ciphertext) > 500:
            raise ValueError("Ciphertext too long")
        return {"status": "ok", "params": params, "ciphertext_len": len(ciphertext)}

    def test_basic_fuzz_run(self):
        """Test that a basic fuzz run completes without crashing."""
        results = constant_time_fuzz(
            self.mock_kem_func, "mlkem768", iterations=10, seed=42
        )
        assert "params" in results
        assert "iterations" in results
        assert "timing_data" in results
        assert "exceptions" in results

    def test_fuzz_with_seed_reproducibility(self):
        """Test that running with same seed produces consistent results."""
        results1 = constant_time_fuzz(
            self.mock_kem_func, "mlkem512", iterations=20, seed=123
        )
        results2 = constant_time_fuzz(
            self.mock_kem_func, "mlkem512", iterations=20, seed=123
        )
        # Both should have same params and iterations
        assert results1["params"] == results2["params"]
        assert results1["iterations"] == results2["iterations"]
        # Timing may vary due to system load, but structure should match

    def test_fuzz_with_too_many_iterations(self):
        """Test fuzz with very small iteration count."""
        results = constant_time_fuzz(
            self.mock_kem_func, "mlkem768", iterations=1, seed=42
        )
        assert results["iterations"] == 1
        assert len(results["timing_data"]) == 1 or len(results["exceptions"]) == 1


class TestFuzzKemImplementation:
    """Tests for fuzz_kem_implementation helper."""

    def mock_kem_api(self, ciphertext: bytes, params: str) -> dict:
        """Mock KEM API that accepts specific lengths."""
        valid_lengths = [32, 64, 96, 128, 192, 256]
        if len(ciphertext) not in valid_lengths:
            raise ValueError(f"Invalid length {len(ciphertext)} for {params}")
        return {"status": "ok", "params": params, "ciphertext_len": len(ciphertext)}

    def test_fuzz_all_kems(self):
        """Test fuzzing all KEM parameter sets."""
        results = fuzz_kem_implementation(KEM_PARAMS, self.mock_kem_api, iterations=10)
        assert len(results) == len(KEM_PARAMS)
        for kem in KEM_PARAMS:
            assert kem in results
            assert "passed" in results[kem]
            assert "timing_data" in results[kem]

    def test_fuzz_kem_results_structure(self):
        """Test that individual KEM fuzz results have correct structure."""
        results = fuzz_kem_implementation(
            ["mlkem512"], self.mock_kem_api, iterations=5
        )
        for kem, r in results.items():
            assert "params" in r
            assert "iterations" in r
            assert "timing_data" in r
            assert "exceptions" in r
            assert "passed" in r


class TestFuzzDsaImplementation:
    """Tests for fuzz_dsa_implementation helper."""

    def mock_dsa_api(self, ciphertext: bytes, params: str) -> dict:
        """Mock DSA API."""
        if params not in ["mlsdsa44", "mlsdsa65"]:
            raise ValueError(f"Unsupported DSA params: {params}")
        return {"status": "ok", "params": params, "ciphertext_len": len(ciphertext)}

    def test_fuzz_all_dsas(self):
        """Test fuzzing all DSA parameter sets."""
        results = fuzz_dsa_implementation(DSA_PARAMS, self.mock_dsa_api, iterations=10)
        assert len(results) == len(DSA_PARAMS)
        for dsa in DSA_PARAMS:
            assert dsa in results

    def test_fuzz_dsa_results_structure(self):
        """Test individual DSA fuzz results structure."""
        results = fuzz_dsa_implementation(
            ["mlsdsa44"], self.mock_dsa_api, iterations=5
        )
        for dsa, r in results.items():
            assert "params" in r
            assert "iterations" in r
            assert "timing_data" in r
            assert "exceptions" in r


class TestTimingVarianceAnalysis:
    """Tests for timing variance analysis."""

    def test_analyze_with_timing_data(self):
        """Test timing analysis with sample data."""
        results = {
            "timing_data": [
                {"elapsed_ns": 1000},
                {"elapsed_ns": 1500},
                {"elapsed_ns": 1200},
            ]
        }
        analysis = analyze_timing_variance(results, threshold_ns=100)
        assert "variance_ns" in analysis
        assert "safe_from_timing_side_channels" in analysis

    def test_analyze_with_insufficient_data(self):
        """Test analysis with too little data."""
        results = {"timing_data": [{"elapsed_ns": 500}]}
        analysis = analyze_timing_variance(results, threshold_ns=100)
        assert "error" in analysis

    def test_analyze_variance_exceeds_threshold(self):
        """Test analysis when variance exceeds threshold."""
        results = {
            "timing_data": [
                {"elapsed_ns": 100},
                {"elapsed_ns": 5000},  # Large variance
            ]
        }
        analysis = analyze_timing_variance(results, threshold_ns=100)
        assert analysis["variance_exceeds_threshold"] is True
        assert analysis["safe_from_timing_side_channels"] is False

    def test_analyze_variance_within_threshold(self):
        """Test analysis when variance is within threshold."""
        results = {
            "timing_data": [
                {"elapsed_ns": 100},
                {"elapsed_ns": 90},  # Small variance
            ]
        }
        analysis = analyze_timing_variance(results, threshold_ns=100)
        assert analysis["variance_exceeds_threshold"] is False
        assert analysis["safe_from_timing_side_channels"] is True


class TestReportGeneration:
    """Tests for report generation."""

    def test_generate_report_empty(self):
        """Test report generation with no results."""
        report = generate_edge_case_report({})
        assert report["total_implementations_tested"] == 0
        assert report["total_passed"] == 0

    def test_generate_report_with_results(self):
        """Test report generation with fuzzing results."""
        kem_results = {
            "mlkem512": {
                "passed": True,
                "timing_data": [{"elapsed_ns": 1000}],
                "exceptions": [],
            }
        }
        report = generate_edge_case_report(kem_results)
        assert report["total_implementations_tested"] == 1
        assert "mlkem512" in report["timing_analysis"]


class TestGenerateEdgeCases:
    """Tests for EDGE_CASES constant."""

    def test_edge_cases_not_empty(self):
        """EDGE_CASES should have content."""
        assert len(EDGE_CASES) > 0

    def test_edge_cases_have_random_variants(self):
        """Should include randomly generated variants."""
        has_random = any(
            len(ec) in [32, 64, 96, 128, 192, 256] and ec != b"\x00" * len(ec)
            for ec in EDGE_CASES
        )
        assert has_random, "EDGE_CASES should include random byte variants"


class TestEdgeCaseCoverage:
    """Tests for comprehensive edge case coverage."""

    def test_covers_boundary_values(self):
        """Should cover boundary/edge values."""
        boundary_found = any(
            len(ec) in [1, 16, 32, 64, 128, 256] for ec in EDGE_CASES
        )
        assert boundary_found, "Should cover boundary ciphertext lengths"

    def test_covers_zero_and_maximal(self):
        """Should cover zero and maximum byte patterns."""
        has_zero = any(ec == b"\x00" * len(ec) for ec in EDGE_CASES)
        has_max = any(ec == b"\xff" * len(ec) for ec in EDGE_CASES)
        assert has_zero and has_max, "Should cover zero and maximal patterns"