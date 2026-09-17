"""PQC Bench Python Client SDK v1.0.

Auto-generated client for the Post-Quantum Cryptography & ML Engine API.
Provides convenient access to all REST endpoints.
"""

import json
import requests
from typing import Optional, Dict, Any, List, Union, Tuple


class PQCClient:
    """Client for the Post-Quantum Cryptography & ML Engine API."""

    def __init__(self, base_url: str = "http://claw.lan:8090", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    # GET endpoints

    def health_check(self) -> Any:
        """Health Check"""
        url = "{self.base_url + "/health"}"
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_cbom_data(self) -> Any:
        """Get CBOM Data"""
        url = "{self.base_url + "/api/v1/cbom"}"
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_constant_time_analysis(self) -> Any:
        """Get Constant Time Analysis"""
        url = "{self.base_url + "/api/v1/constant-time/analysis"}"
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def export_compliance_report(self) -> Any:
        """Export Compliance Report"""
        url = "{self.base_url + "/api/v1/report/export"}"
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_model_metrics(self) -> Any:
        """Get Model Training Metrics"""
        url = "{self.base_url + "/api/v1/model/metrics"}"
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_project_status(self) -> Any:
        """Get Project Status"""
        url = "{self.base_url + "/api/v1/status"}"
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_visualize_trace(self) -> Any:
        """Get Visualize Trace"""
        url = "{self.base_url + "/api/v1/visualize/trace"}"
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # POST endpoints

    def estimate_security(self, json_data: Dict[str, Any]) -> Any:
        """Estimate Security"""
        url = "{self.base_url + "/api/v1/security-estimate"}"
        response = self.session.post(
            url,
            json=json_data,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def calculate_quantum_cost(self, json_data: Dict[str, Any]) -> Any:
        """Calculate Quantum Cost"""
        url = "{self.base_url + "/api/v1/quantum-cost"}"
        response = self.session.post(
            url,
            json=json_data,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def predict_side_channel(self, json_data: Dict[str, Any]) -> Any:
        """Predict Side Channel Leakage"""
        url = "{self.base_url + "/api/v1/model/predict"}"
        response = self.session.post(
            url,
            json=json_data,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def benchmark_cpa_dl(self, json_data: Dict[str, Any]) -> Any:
        """Benchmark CPA vs Deep Learning"""
        url = "{self.base_url + "/api/v1/model/cpa-benchmark"}"
        response = self.session.post(
            url,
            json=json_data,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    # Convenience method for health check
    @staticmethod
    def quick_health(base_url: str = "http://claw.lan:8090") -> dict:
        """Quick health check."""
        import requests
        resp = requests.get(f"{base_url.rstrip('/')}/health", timeout=10)
        resp.raise_for_status()
        return resp.json()

    # Main entry point
    @classmethod
    def from_env(cls):
        """Create client from environment configuration."""
        import os
        base_url = os.getenv("PQC_API_BASE", "http://claw.lan:8090")
        timeout = int(os.getenv("PQC_API_TIMEOUT", "30"))
        return cls(base_url=base_url, timeout=timeout)


# Example usage:
# client = PQCClient.from_env()
# health = client.health_check()
