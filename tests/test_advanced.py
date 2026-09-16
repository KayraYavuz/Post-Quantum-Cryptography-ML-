"""Unit and Integration Tests for Phase 3 Advanced Capabilities (WS-ADV.1, WS-ADV.2, WS-ADV.3).

Verifies:
1. Classical Pearson Correlation Power Analysis (CPA) attack logic and Hamming weight leakage.
2. Side-by-side benchmark comparing 1st-order CPA vs Deep Learning CNN under Boolean masking.
3. Constant-time TVLA Welch's t-test simulation and KyberSlash assembly comparison.
4. Automated NIST SP 800-208 and CNSA 2.0 compliance audit report generation.
5. FastAPI REST API contracts for all Phase 3 endpoints.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from pqc_bench.api.main import app
from pqc_bench.cbom.report_exporter import generate_compliance_audit_report
from pqc_bench.constant_time.interactive_analyzer import (
    get_assembly_comparison,
    simulate_timing_t_test,
)
from pqc_bench.models.cpa_attack import (
    CorrelationPowerAnalysis,
    generate_benchmark_traces,
    run_cpa_vs_dl_benchmark,
)


class TestCPAEngine(unittest.TestCase):
    """Verifies Pearson Correlation Power Analysis (CPA) mathematics."""

    def test_hamming_weight_calculation(self) -> None:
        self.assertEqual(CorrelationPowerAnalysis.hamming_weight(0x00), 0)
        self.assertEqual(CorrelationPowerAnalysis.hamming_weight(0xFF), 8)
        self.assertEqual(CorrelationPowerAnalysis.hamming_weight(0x2B), 4)  # 00101011 -> 4 ones

    def test_cpa_attack_execution(self) -> None:
        traces, plaintexts = generate_benchmark_traces(
            num_traces=30, trace_length=256, noise_std=0.2, masked=False, true_key=0x2B
        )
        cpa = CorrelationPowerAnalysis(trace_length=256)
        results = cpa.attack(traces, plaintexts, true_key=0x2B)

        self.assertEqual(results["num_traces"], 30)
        self.assertEqual(results["true_key"], 0x2B)
        self.assertIn("best_key_guess", results)
        self.assertIn("true_key_correlation", results)
        self.assertIn("correlation_sample_curve", results)

    def test_cpa_vs_dl_benchmark_masked(self) -> None:
        result = run_cpa_vs_dl_benchmark(num_traces=30, masked=True, noise_std=0.35)
        self.assertIn("cpa_analysis", result)
        self.assertIn("deep_learning_cnn", result)
        self.assertTrue(result["parameters"]["masked"])
        self.assertIn("Multi-layer Conv1d", result["deep_learning_cnn"]["mask_breaking_capacity"])


class TestConstantTimeSuite(unittest.TestCase):
    """Verifies KyberSlash assembly comparison and TVLA Welch's t-test logic."""

    def test_assembly_comparison_metadata(self) -> None:
        data = get_assembly_comparison("ml-kem-768")
        self.assertIn("vulnerable_implementation", data)
        self.assertIn("hardened_implementation", data)
        self.assertIn("idiv", data["vulnerable_implementation"]["assembly_snippet"])
        self.assertIn("imul", data["hardened_implementation"]["assembly_snippet"])

    def test_welch_t_test_simulation(self) -> None:
        t_data = simulate_timing_t_test(num_iterations=2000)
        self.assertGreater(t_data["variable_time_analysis"]["welch_t_statistic"], 4.5)
        self.assertLessEqual(t_data["constant_time_analysis"]["welch_t_statistic"], 4.5)
        self.assertIn("PASS", t_data["constant_time_analysis"]["status"])


class TestComplianceAuditExporter(unittest.TestCase):
    """Verifies NIST SP 800-208 & CNSA 2.0 report compilation."""

    def test_audit_report_generation(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        report = generate_compliance_audit_report(repo_root)

        self.assertIn("report_id", report)
        self.assertIn("markdown_report", report)
        self.assertIn("ML-KEM-768", report["inventory_summary"]["post_quantum_algorithms_detected"])
        self.assertIn("CNSA 2.0", report["markdown_report"])


class TestAdvancedAPIRoutes(unittest.TestCase):
    """Verifies new Phase 3 REST endpoints via TestClient."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_cpa_benchmark_endpoint(self) -> None:
        resp = self.client.post("/api/v1/model/cpa-benchmark", json={"num_traces": 30, "masked": False})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("cpa_analysis", body)
        self.assertIn("deep_learning_cnn", body)

    def test_constant_time_analysis_endpoint(self) -> None:
        resp = self.client.get("/api/v1/constant-time/analysis")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("assembly", body)
        self.assertIn("timing_test", body)

    def test_report_export_endpoint(self) -> None:
        resp = self.client.get("/api/v1/report/export")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("NIST PQC & CNSA 2.0 Cryptographic Compliance Audit Report", resp.text)


if __name__ == "__main__":
    unittest.main()
