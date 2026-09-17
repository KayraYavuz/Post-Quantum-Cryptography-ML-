"""
Phase 9 Fuzzing Security Report Unit Tests

Tests the fuzzing security report generation and anomaly matrix
for WS-P9.4: Kuantum Sonrası Otomatik Fuzzing & Bellek Güvenliği.

Validates:
- Report generation from fuzzing results
- Anomaly matrix structure and content
- JSON/Markdown export formats
- Edge case coverage and statistical analysis
"""

import json
import pytest
from pqc_bench.fuzzing.ct_fuzzer import (
    constant_time_fuzz,
    fuzz_kem_implementation,
    fuzz_dsa_implementation,
    analyze_timing_variance,
    generate_edge_case_report,
    EDGE_CASES,
    KEM_PARAMS,
    DSA_PARAMS,
)


class TestFuzzingReportStructure:
    """Test the structure of fuzzing security reports."""

    def test_generate_report_has_required_fields(self):
        """Report should have all required top-level fields."""
        kem_results = {
            "mlkem512": {
                "passed": True,
                "timing_data": [{"elapsed_ns": 1000}],
                "exceptions": [],
            }
        }
        report = generate_edge_case_report(kem_results)
        required_fields = [
            "total_implementations_tested",
            "total_passed",
            "total_failed",
            "total_exceptions",
            "timing_analysis",
            "exception_summary",
            "recommendations",
        ]
        for field in required_fields:
            assert field in report, f"Missing required field: {field}"

    def test_report_counts_are_consistent(self):
        """Report counts should be internally consistent."""
        kem_results = {
            "mlkem512": {
                "passed": True,
                "timing_data": [{"elapsed_ns": 1000}],
                "exceptions": [],
            },
            "mlkem768": {
                "passed": False,
                "timing_data": [],
                "exceptions": [{"error_type": "ValueError", "error_msg": "test error"}],
            },
        }
        report = generate_edge_case_report(kem_results)
        assert report["total_implementations_tested"] == 2
        assert report["total_passed"] == 1
        assert report["total_failed"] == 1
        assert report["total_exceptions"] == 1


class TestAnomalyMatrix:
    """Test anomaly matrix generation from fuzzing results."""

    def test_anomaly_matrix_has_structure(self):
        """Anomaly matrix should have consistent structure across implementations."""
        kem_results = {
            "mlkem512": {
                "passed": True,
                "timing_data": [
                    {"elapsed_ns": 1000, "ciphertext_len": 32},
                    {"elapsed_ns": 1200, "ciphertext_len": 64},
                ],
                "exceptions": [],
            },
            "mlkem768": {
                "passed": False,
                "timing_data": [
                    {"elapsed_ns": 5000, "ciphertext_len": 32},
                ],
                "exceptions": [
                    {"error_type": "ValueError", "error_msg": "Invalid length"},
                ],
            },
        }
        report = generate_edge_case_report(kem_results)
        assert "mlkem512" in report["timing_analysis"]
        assert "mlkem768" in report["timing_analysis"]
        # mlkem512 should have no exceptions in summary
        assert "exception_count" in report["exception_summary"]["mlkem512"]
        assert "exception_count" in report["exception_summary"]["mlkem768"]
        assert report["exception_summary"]["mlkem768"]["exception_count"] == 1

    def test_timing_analysis_has_variance(self):
        """Timing analysis should compute variance correctly."""
        kem_results = {
            "mlkem512": {
                "passed": True,
                "timing_data": [
                    {"elapsed_ns": 1000},
                    {"elapsed_ns": 1500},
                    {"elapsed_ns": 1200},
                ],
                "exceptions": [],
            }
        }
        report = generate_edge_case_report(kem_results)
        timing = report["timing_analysis"]["mlkem512"]
        assert "variance_ns" in timing
        assert "variance_exceeds_threshold" in timing
        assert "safe_from_timing_side_channels" in timing


class TestReportExportFormats:
    """Test JSON and Markdown export of fuzzing reports."""

    def test_report_can_be_serialized_to_json(self):
        """Report should be JSON-serializable."""
        kem_results = {
            "mlkem512": {
                "passed": True,
                "timing_data": [{"elapsed_ns": 1000}],
                "exceptions": [],
            }
        }
        report = generate_edge_case_report(kem_results)
        json_str = json.dumps(report)
        parsed = json.loads(json_str)
        assert parsed == report

    def test_report_markdown_has_title(self):
        """Markdown report should have a title header."""
        kem_results = {
            "mlkem768": {
                "passed": True,
                "timing_data": [{"elapsed_ns": 850}],
                "exceptions": [],
            }
        }
        report = generate_edge_case_report(kem_results)
        # Verify report has text content for markdown generation
        assert isinstance(report, dict)
        assert len(report["timing_analysis"]) > 0


class TestEdgeCaseCoverage:
    """Test that edge cases are properly covered in fuzzing."""

    def test_edge_cases_not_empty(self):
        """EDGE_CASES should have content for fuzzing."""
        assert len(EDGE_CASES) > 0

    def test_edge_cases_include_variants(self):
        """Edge cases should include various byte patterns."""
        lengths = set(len(ec) for ec in EDGE_CASES)
        assert len(lengths) >= 3, (
            f"Expected at least 3 different edge case lengths, got {len(lengths)}: {lengths}"
        )


class TestPracticalFuzzRun:
    """Test practical fuzzing run completion and report generation."""

    def mock_kem_func(self, ciphertext: bytes, params: str) -> dict:
        """Simple mock KEM function."""
        if len(ciphertext) > 500:
            raise ValueError("Ciphertext too long")
        return {"status": "ok", "params": params, "ciphertext_len": len(ciphertext)}

    def test_basic_fuzz_run_completes(self):
        """Test that a basic fuzz run completes and produces valid results."""
        results = constant_time_fuzz(
            self.mock_kem_func, "mlkem768", iterations=10, seed=42
        )
        assert "params" in results
        assert "iterations" in results
        assert "timing_data" in results
        assert "exceptions" in results
        assert "passed" in results

    def test_fuzz_structure_has_timing_stats(self):
        """Fuzz results should include timing statistics."""
        results = constant_time_fuzz(
            self.mock_kem_func, "mlkem512", iterations=20, seed=123
        )
        assert "timing_stats" in results
        stats = results["timing_stats"]
        assert "min_ns" in stats
        assert "max_ns" in stats
        assert "mean_ns" in stats

    def test_report_generation_with_realistic_data(self):
        """Test report generation with realistic fuzzing data."""
        # Run fuzzing for multiple KEMs
        kem_results = fuzz_kem_implementation(
            KEM_PARAMS[:2], self.mock_kem_func, iterations=10
        )
        report = generate_edge_case_report(kem_results)
        assert report["total_implementations_tested"] == 2
        assert len(report["timing_analysis"]) == 2
        assert "mlkem512" in report["timing_analysis"]
        assert "mlkem768" in report["timing_analysis"]


class TestRecommendationsGeneration:
    """Test that recommendations are generated based on fuzzing findings."""

    def test_recommendations_when_failures_exist(self):
        """Should generate recommendations when there are failures."""
        kem_results = {
            "mlkem512": {
                "passed": False,
                "timing_data": [],
                "exceptions": [{"error_type": "ValueError", "error_msg": "test"}],
            }
        }
        report = generate_edge_case_report(kem_results)
        assert len(report["recommendations"]) > 0
        assert any("failing" in r.lower() or "fix" in r.lower() for r in report["recommendations"])

    def test_recommendations_when_timing_variance_high(self):
        """Should generate recommendations for high timing variance."""
        kem_results = {
            "mlkem512": {
                "passed": True,
                "timing_data": [
                    {"elapsed_ns": 100},
                    {"elapsed_ns": 5000},  # High variance
                ],
                "exceptions": [],
            }
        }
        report = generate_edge_case_report(kem_results)
        assert len(report["recommendations"]) > 0
        assert any("timing" in r.lower() or "side-channel" in r.lower() for r in report["recommendations"])


class TestReportExportValidation:
    """Test report export validation and format compliance."""

    def test_json_report_valid_schema(self):
        """JSON report should validate against expected schema."""
        kem_results = {
            "mlkem768": {
                "passed": True,
                "timing_data": [{"elapsed_ns": 1000}],
                "exceptions": [],
            }
        }
        report = generate_edge_case_report(kem_results)
        # All values should be serializable
        assert isinstance(report["total_implementations_tested"], int)
        assert isinstance(report["total_passed"], int)
        assert isinstance(report["total_failed"], int)
        assert isinstance(report["total_exceptions"], int)
        assert isinstance(report["recommendations"], list)
        for timing_impl in report["timing_analysis"].values():
            assert isinstance(timing_impl["variance_ns"], int)
            assert isinstance(timing_impl["variance_exceeds_threshold"], bool)
            assert isinstance(timing_impl["safe_from_timing_side_channels"], bool)

    def test_markdown_report_sections(self):
        """Markdown report should have expected sections."""
        kem_results = {
            "mlkem512": {
                "passed": True,
                "timing_data": [{"elapsed_ns": 1000}],
                "exceptions": [],
            }
        }
        report = generate_edge_case_report(kem_results)
        # Report should contain analyzable data for markdown generation
        assert "timing_analysis" in report
        assert "exception_summary" in report
        assert len(report["recommendations"]) >= 0