"""
Fuzzing Security Report and Integration Module for Phase 9
===========================================================

This module provides comprehensive fuzzing security report generation,
integration with security estimation, and anomaly matrix reporting
for the WS-P9.4 Kuantum Sonrasi Otomatik Fuzzing & Bellek Güvenliği task.

Features:
- Generate structured JSON and Markdown security reports
- Integration with security estimation workflows
- Anomaly matrix generation and analysis
- Integration with existing pqc_bench infrastructure
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ct_fuzzer import (
    analyze_timing_variance,
    constant_time_fuzz,
    fuzz_dsa_implementation,
    fuzz_kem_implementation,
    generate_edge_case_report,
)


class FuzzingSecurityReporter:
    """Main class for generating and managing fuzzing security reports."""

    def __init__(self, output_dir: str = "./reports/fuzzing"):
        """
        Initialize the FuzzingSecurityReporter.

        Args:
            output_dir: Directory for report output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_comprehensive_report(
        self,
        crypto_api: Any,
        kem_params: Optional[List[str]] = None,
        dsa_params: Optional[List[str]] = None,
        iterations: int = 200,
        output_format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive fuzzing security report.

        Args:
            crypto_api: Crypto function API for fuzzing
            kem_params: List of KEM parameters to test
            dsa_params: List of DSA parameters to test
            iterations: Number of fuzzing iterations per parameter set
            output_format: Output format (json, markdown, both)

        Returns:
            Dict containing the comprehensive report
        """
        if kem_params is None:
            kem_params = ["mlkem512", "mlkem768", "mlkem1024"]
        if dsa_params is None:
            dsa_params = ["mlsdsa44", "mlsdsa65", "mlsdsa87"]

        # Run comprehensive fuzzing on all implementations
        kem_results = fuzz_kem_implementation(kem_params, crypto_api, iterations)
        dsa_results = fuzz_dsa_implementation(dsa_params, crypto_api, iterations)

        # Generate edge case reports for both KEM and DSA
        kem_report = generate_edge_case_report(kem_results)
        dsa_report = generate_edge_case_report(dsa_results)

        # Create comprehensive report
        comprehensive_report = {
            "metadata": {
                "report_id": f"fuzzing_security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "generation_date": datetime.now().isoformat(),
                "version": "1.0",
                "phase": "WS-P9.4",
                "description": "Kuantum Sonrasi Otomatik Fuzzing & Bellek Güvenliği",
                "iterations_per_implementation": iterations,
                "total_kem_tested": len(kem_params),
                "total_dsa_tested": len(dsa_params),
            },
            "kem_results": kem_report,
            "dsa_results": dsa_report,
            "integration_summary": self._create_integration_summary(kem_report, dsa_report),
            "compliance_matrix": self._create_compliance_matrix(kem_report, dsa_report),
        }

        # Save reports based on requested format
        self._save_reports(comprehensive_report, output_format)

        return comprehensive_report

    def _create_integration_summary(
        self, kem_report: Dict[str, Any], dsa_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create integration summary for the report."""
        return {
            "total_implementations_tested": (
                kem_report["total_implementations_tested"]
                + dsa_report["total_implementations_tested"]
            ),
            "total_passed": (
                kem_report["total_passed"] + dsa_report["total_passed"]
            ),
            "total_failed": (
                kem_report["total_failed"] + dsa_report["total_failed"]
            ),
            "total_exceptions": (
                kem_report["total_exceptions"] + dsa_report["total_exceptions"]
            ),
            "overall_success_rate": round(
                (
                    kem_report["total_passed"]
                    + dsa_report["total_passed"]
                )
                / (kem_report["total_implementations_tested"] + dsa_report["total_implementations_tested"]
                ) * 100,
                2,
            ),
            "critical_issues_count": len(
                [
                    r
                    for r in kem_report["recommendations"] + dsa_report["recommendations"]
                    if any(word in r.lower() for word in ["critical", "high", "fix"])
                ]
            ),
            "timing_side_channel_risk": any(
                t.get("variance_exceeds_threshold", False)
                for t in (
                    kem_report["timing_analysis"].values()
                    + dsa_report["timing_analysis"].values()
                )
            ),
        }

    def _create_compliance_matrix(
        self, kem_report: Dict[str, Any], dsa_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create compliance matrix for security standards."""
        matrix = {
            "nist_sp_800_208": {"status": "IN_PROGRESS", "details": {}},
            "cnsa_2_0": {"status": "IN_PROGRESS", "details": {}},
            "fips_140_3": {"status": "IN_PROGRESS", "details": {}},
            "mlkem_standards": {"status": "PASS", "details": {}},
            "mldsa_standards": {"status": "PASS", "details": {}},
        }

        # Evaluate KEM compliance
        for impl_name, timing in kem_report["timing_analysis"].items():
            matrix["mlkem_standards"]["details"][impl_name] = (
                "PASS" if timing.get("safe_from_timing_side_channels", False) else "FAIL"
            )

        # Evaluate DSA compliance
        for impl_name, timing in dsa_report["timing_analysis"].items():
            matrix["mldsa_standards"]["details"][impl_name] = (
                "PASS" if timing.get("safe_from_timing_side_channels", False) else "FAIL"
            )

        # Overall matrix status
        failed_implementations = sum(
            1
            for impl_name in kem_report["timing_analysis"].keys()
            if not kem_report["timing_analysis"][impl_name].get(
                "safe_from_timing_side_channels", False
            )
        ) + sum(
            1
            for impl_name in dsa_report["timing_analysis"].keys()
            if not dsa_report["timing_analysis"][impl_name].get(
                "safe_from_timing_side_channels", False
            )
        )

        if failed_implementations == 0:
            matrix["nist_sp_800_208"]["status"] = "PASS"
            matrix["cnsa_2_0"]["status"] = "PASS"
            matrix["fips_140_3"]["status"] = "PASS"
        elif failed_implementations <= 2:
            matrix["nist_sp_800_208"]["status"] = "CONDITIONAL_PASS"
            matrix["cnsa_2_0"]["status"] = "CONDITIONAL_PASS"
            matrix["fips_140_3"]["status"] = "CONDITIONAL_PASS"

        return matrix

    def _save_reports(
        self, report: Dict[str, Any], output_format: str
    ) -> List[str]:
        """
        Save reports in the specified format(s).

        Args:
            report: Report dictionary to save
            output_format: Output format (json, markdown, both)

        Returns:
            List of saved file paths
        """
        saved_files = []

        if output_format in ["json", "both"]:
            json_filename = (
                f"fuzzing_report_{report['metadata']['report_id']}.json"
            )
            json_path = self.output_dir / json_filename
            with open(json_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
            saved_files.append(str(json_path))

        if output_format in ["markdown", "both"]:
            markdown_filename = (
                f"fuzzing_report_{report['metadata']['report_id']}.md"
            )
            markdown_path = self.output_dir / markdown_filename
            markdown_content = self._generate_markdown_report(report)
            with open(markdown_path, "w") as f:
                f.write(markdown_content)
            saved_files.append(str(markdown_path))

        return saved_files

    def _generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Generate a Markdown format report."""
        metadata = report["metadata"]
        integration = report["integration_summary"]
        compliance = report["compliance_matrix"]

        md = f"# Fuzzing Security Report\n\n"
        md += f"**Report ID:** {metadata['report_id']}\n"
        md += f"**Generation Date:** {metadata['generation_date']}\n"
        md += f"**Phase:** {metadata['phase']}\n"
        md += f"**Description:** {metadata['description']}\n\n"

        md += f"## Summary\n\n"
        md += f"- **Total Implementations Tested:** {integration['total_implementations_tested']}\n"
        md += f"- **Total Passed:** {integration['total_passed']}\n"
        md += f"- **Total Failed:** {integration['total_failed']}\n"
        md += f"- **Total Exceptions:** {integration['total_exceptions']}\n"
        md += f"- **Overall Success Rate:** {integration['overall_success_rate']}%\n"
        md += f"- **Critical Issues:** {integration['critical_issues_count']}\n"
        md += f"- **Timing Side-Channel Risk:** {integration['timing_side_channel_risk']}\n\n"

        md += f"## Compliance Matrix\n\n"
        for standard, data in compliance.items():
            md += f"### {standard.replace('_', ' ').title()}\n"
            md += f"**Status:** {data['status']}\n"
            if "details" in data:
                md += f"**Details:** {json.dumps(data['details'], indent=2)}\n"
            md += "\n"

        md += f"## KEM Results\n\n"
        for impl, timing in report["kem_results"]["timing_analysis"].items():
            md += f"### {impl}\n"
            md += f"- **Safe from Timing Side-Channels:** {timing.get('safe_from_timing_side_channels', 'N/A')}\n"
            md += f"- **Variance Exceeds Threshold:** {timing.get('variance_exceeds_threshold', 'N/A')}\n"
            md += f"- **Variance (ns):** {timing.get('variance_ns', 'N/A')}\n"
            md += f"- **Timing Range (%):** {timing.get('timing_range_percent', 'N/A')}\n"
            md += "\n"

        md += f"## DSA Results\n\n"
        for impl, timing in report["dsa_results"]["timing_analysis"].items():
            md += f"### {impl}\n"
            md += f"- **Safe from Timing Side-Channels:** {timing.get('safe_from_timing_side_channels', 'N/A')}\n"
            md += f"- **Variance Exceeds Threshold:** {timing.get('variance_exceeds_threshold', 'N/A')}\n"
            md += f"- **Variance (ns):** {timing.get('variance_ns', 'N/A')}\n"
            md += f"- **Timing Range (%):** {timing.get('timing_range_percent', 'N/A')}\n"
            md += "\n"

        md += f"## Recommendations\n\n"
        for recommendation in (
            report["kem_results"]["recommendations"]
            + report["dsa_results"]["recommendations"]
        ):
            md += f"- {recommendation}\n"

        return md

    def generate_anomaly_matrix(
        self,
        crypto_api: Any,
        kem_params: Optional[List[str]] = None,
        dsa_params: Optional[List[str]] = None,
        iterations: int = 100,
        output_format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate anomaly matrix from fuzzing results.

        Args:
            crypto_api: Crypto function API for fuzzing
            kem_params: List of KEM parameters to test
            dsa_params: List of DSA parameters to test
            iterations: Number of fuzzing iterations per parameter set
            output_format: Output format (json, markdown, both)

        Returns:
            Dict containing the anomaly matrix
        """
        if kem_params is None:
            kem_params = ["mlkem512", "mlkem768", "mlkem1024"]
        if dsa_params is None:
            dsa_params = ["mlsdsa44", "mlsdsa65", "mlsdsa87"]

        # Run fuzzing to generate results
        kem_results = fuzz_kem_implementation(kem_params, crypto_api, iterations)
        dsa_results = fuzz_dsa_implementation(dsa_params, crypto_api, iterations)

        # Generate comprehensive reports
        kem_report = generate_edge_case_report(kem_results)
        dsa_report = generate_edge_case_report(dsa_results)

        # Create anomaly matrix
        anomaly_matrix = {
            "metadata": {
                "report_id": f"anomaly_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "generation_date": datetime.now().isoformat(),
                "version": "1.0",
                "phase": "WS-P9.4",
                "description": "Fuzzing Anomalies and Security Issues Matrix",
            },
            "kem_anomalies": self._extract_anomalies(kem_report),
            "dsa_anomalies": self._extract_anomalies(dsa_report),
            "cross_implementation_anomalies": self._extract_cross_implementation_anomalies(
                kem_report, dsa_report
            ),
        }

        # Save anomaly matrix
        self._save_anomaly_matrix(anomaly_matrix, output_format)

        return anomaly_matrix

    def _extract_anomalies(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Extract anomalies from a report."""
        anomalies = {}

        for impl_name, timing in report["timing_analysis"].items():
            impl_anomalies = {}

            # Timing variance anomalies
            if timing.get("variance_exceeds_threshold", False):
                impl_anomalies["timing_variance"] = {
                    "severity": "HIGH",
                    "description": f"Timing variance {timing['variance_ns']}ns exceeds threshold",
                    "metrics": {
                        "min_time_ns": timing.get("min_time_ns", 0),
                        "max_time_ns": timing.get("max_time_ns", 0),
                        "variance_ns": timing.get("variance_ns", 0),
                        "threshold_ns": timing.get("threshold_ns", 0),
                    },
                }

            # Exception anomalies
            exception_count = report["exception_summary"][impl_name]["exception_count"]
            if exception_count > 0:
                impl_anomalies["exceptions"] = {
                    "severity": "MEDIUM" if exception_count <= 2 else "HIGH",
                    "description": f"{exception_count} exceptions encountered",
                    "exception_types": report["exception_summary"][impl_name]["exception_types"],
                }

            # Implementation status
            impl_status = (
                "FAILED" if impl_name in report["timing_analysis"] else "PASSED"
            )
            if impl_status == "FAILED":
                impl_anomalies["implementation_status"] = {
                    "severity": "HIGH",
                    "description": f"Implementation {impl_name} failed security tests",
                }

            anomalies[impl_name] = impl_anomalies

        return anomalies

    def _extract_cross_implementation_anomalies(
        self, kem_report: Dict[str, Any], dsa_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract cross-implementation anomalies."""
        cross_anomalies = {
            "consistency_issues": [],
            "pattern_anomalies": [],
            "severity_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        }

        # Check for consistency issues between KEM and DSA
        kem_timing_vars = {
            impl: data.get("variance_ns", 0)
            for impl, data in kem_report["timing_analysis"].items()
        }
        dsa_timing_vars = {
            impl: data.get("variance_ns", 0)
            for impl, data in dsa_report["timing_analysis"].items()
        }

        # Compare variance patterns
        for kem_impl, kem_var in kem_timing_vars.items():
            for dsa_impl, dsa_var in dsa_timing_vars.items():
                variance_ratio = abs(kem_var - dsa_var) / max(kem_var, dsa_var) if max(kem_var, dsa_var) > 0 else 0

                if variance_ratio > 0.5:  # Significant difference
                    cross_anomalies["pattern_anomalies"].append({
                        "type": "variance_discrepancy",
                        "kem_implementation": kem_impl,
                        "dsa_implementation": dsa_impl,
                        "kem_variance_ns": kem_var,
                        "dsa_variance_ns": dsa_var,
                        "variance_ratio": variance_ratio,
                        "severity": "MEDIUM" if variance_ratio > 0.7 else "LOW",
                    })

        # Count severity distribution
        for anomaly in cross_anomalies["pattern_anomalies"]:
            cross_anomalies["severity_distribution"][anomaly["severity"]] += 1

        return cross_anomalies

    def _save_anomaly_matrix(
        self, matrix: Dict[str, Any], output_format: str
    ) -> List[str]:
        """
        Save anomaly matrix in the specified format(s).

        Args:
            matrix: Anomaly matrix dictionary to save
            output_format: Output format (json, markdown, both)

        Returns:
            List of saved file paths
        """
        saved_files = []

        if output_format in ["json", "both"]:
            json_filename = f"anomaly_matrix_{matrix['metadata']['report_id']}.json"
            json_path = self.output_dir / json_filename
            with open(json_path, "w") as f:
                json.dump(matrix, f, indent=2, default=str)
            saved_files.append(str(json_path))

        if output_format in ["markdown", "both"]:
            markdown_filename = f"anomaly_matrix_{matrix['metadata']['report_id']}.md"
            markdown_path = self.output_dir / markdown_filename
            markdown_content = self._generate_markdown_anomaly_matrix(matrix)
            with open(markdown_path, "w") as f:
                f.write(markdown_content)
            saved_files.append(str(markdown_path))

        return saved_files

    def _generate_markdown_anomaly_matrix(self, matrix: Dict[str, Any]) -> str:
        """Generate a Markdown format anomaly matrix."""
        metadata = matrix["metadata"]

        md = f"# Anomaly Matrix Report\n\n"
        md += f"**Report ID:** {metadata['report_id']}\n"
        md += f"**Generation Date:** {metadata['generation_date']}\n"
        md += f"**Phase:** {metadata['phase']}\n"
        md += f"**Description:** {metadata['description']}\n\n"

        md += f"## KEM Anomalies\n\n"
        for impl, anomalies in matrix["kem_anomalies"].items():
            md += f"### {impl}\n"
            if anomalies:
                for anomaly_type, anomaly_data in anomalies.items():
                    md += f"- **{anomaly_type.replace('_', ' ').title()}:** {anomaly_data['description']} (Severity: {anomaly_data['severity']})\n"
            else:
                md += f"- No anomalies detected\n"
            md += "\n"

        md += f"## DSA Anomalies\n\n"
        for impl, anomalies in matrix["dsa_anomalies"].items():
            md += f"### {impl}\n"
            if anomalies:
                for anomaly_type, anomaly_data in anomalies.items():
                    md += f"- **{anomaly_type.replace('_', ' ').title()}:** {anomaly_data['description']} (Severity: {anomaly_data['severity']})\n"
            else:
                md += f"- No anomalies detected\n"
            md += "\n"

        md += f"## Cross-Implementation Anomalies\n\n"
        for anomaly in matrix["cross_implementation_anomalies"]["pattern_anomalies"]:
            md += f"- **{anomaly['type'].replace('_', ' ').title()}:** {anomaly['kem_implementation']} vs {anomaly['dsa_implementation']} (Ratio: {anomaly['variance_ratio']:.2f}, Severity: {anomaly['severity']})\n"

        md += f"\n## Severity Distribution\n\n"
        for severity, count in matrix["cross_implementation_anomalies"]["severity_distribution"].items():
            md += f"- **{severity}:** {count}\n"

        return md

    def export_for_security_estimation(
        self,
        crypto_api: Any,
        kem_params: Optional[List[str]] = None,
        dsa_params: Optional[List[str]] = None,
        iterations: int = 200,
    ) -> Dict[str, Any]:
        """
        Export fuzzing results for integration with security estimation.

        Args:
            crypto_api: Crypto function API for fuzzing
            kem_params: List of KEM parameters to test
            dsa_params: List of DSA parameters to test
            iterations: Number of fuzzing iterations per parameter set

        Returns:
            Dict containing export data for security estimation
        """
        if kem_params is None:
            kem_params = ["mlkem512", "mlkem768", "mlkem1024"]
        if dsa_params is None:
            dsa_params = ["mlsdsa44", "mlsdsa65", "mlsdsa87"]

        # Generate comprehensive report
        report = self.generate_comprehensive_report(
            crypto_api, kem_params, dsa_params, iterations, "json"
        )

        # Create security estimation export data
        security_estimation_export = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "source": "fuzzing_security_reporter",
                "version": "1.0",
                "compatibility_with_security_estimation": True,
            },
            "key_metrics": {
                "overall_security_score": report["integration_summary"]["overall_success_rate"],
                "timing_side_channel_resistance": not report["integration_summary"]["timing_side_channel_risk"],
                "exception_handling_quality": 1.0
                - (
                    report["integration_summary"]["total_exceptions"]
                    / max(1, report["integration_summary"]["total_implementations_tested"]
                    )
                ),
                "implementation_consistency": self._calculate_implementation_consistency(
                    report
                ),
            },
            "recommendations": report["integration_summary"]["recommendations"]
            + report["kem_results"]["recommendations"]
            + report["dsa_results"]["recommendations"],
            "compliance_status": report["compliance_matrix"],
            "detailed_results": {
                "kem": report["kem_results"],
                "dsa": report["dsa_results"],
            },
        }

        return security_estimation_export

    def _calculate_implementation_consistency(
        self, report: Dict[str, Any]
    ) -> float:
        """Calculate implementation consistency score."""
        kem_results = report["kem_results"]
        dsa_results = report["dsa_results"]

        # Calculate consistency based on timing variance
        kem_consistency_scores = []
        for impl, timing in kem_results["timing_analysis"].items():
            safe_score = 1.0 if timing.get("safe_from_timing_side_channels", False) else 0.0
            variance_score = max(
                0.0,
                1.0
                - min(
                    1.0,
                    timing.get("variance_ns", 0)
                    / timing.get("threshold_ns", 1),
                ),
            )
            kem_consistency_scores.append((safe_score + variance_score) / 2)

        dsa_consistency_scores = []
        for impl, timing in dsa_results["timing_analysis"].items():
            safe_score = 1.0 if timing.get("safe_from_timing_side_channels", False) else 0.0
            variance_score = max(
                0.0,
                1.0
                - min(
                    1.0,
                    timing.get("variance_ns", 0)
                    / timing.get("threshold_ns", 1),
                ),
            )
            dsa_consistency_scores.append((safe_score + variance_score) / 2)

        # Calculate overall consistency
        all_scores = kem_consistency_scores + dsa_consistency_scores
        return sum(all_scores) / len(all_scores) if all_scores else 0.0


# Example usage function
def example_usage():
    """Example usage of FuzzingSecurityReporter."""

    def mock_crypto_func(ciphertext: bytes, params: str) -> dict:
        """Mock crypto function for demonstration."""
        import time

        time.sleep(0.001)  # Simulate computation

        if len(ciphertext) not in [16, 32, 64, 128, 256]:
            raise ValueError(f"Invalid ciphertext length for {params}")

        return {
            "status": "ok",
            "params": params,
            "ciphertext_len": len(ciphertext),
        }

    # Initialize reporter
    reporter = FuzzingSecurityReporter()

    # Generate comprehensive report
    print("Generating comprehensive fuzzing security report...")
    comprehensive_report = reporter.generate_comprehensive_report(
        mock_crypto_func, iterations=100
    )
    print(f"Report generated successfully with ID: {comprehensive_report['metadata']['report_id']}")

    # Generate anomaly matrix
    print("\nGenerating anomaly matrix...")
    anomaly_matrix = reporter.generate_anomaly_matrix(mock_crypto_func, iterations=50)
    print(f"Anomaly matrix generated successfully with ID: {anomaly_matrix['metadata']['report_id']}")

    # Export for security estimation
    print("\nExporting data for security estimation...")
    security_export = reporter.export_for_security_estimation(mock_crypto_func, iterations=75)
    print(f"Security estimation export completed successfully")

    return comprehensive_report, anomaly_matrix, security_export


if __name__ == "__main__":
    example_usage()