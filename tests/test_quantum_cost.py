"""WS-D Quantum Cost Estimation Unit Tests for PQC Algorithms.

Validates quantum resource estimates (logical qubits, T-gate count/depth,
physical qubits) against AQRE/Qualtran references for post-quantum cryptography
parameter sets. Compatible with both pytest and python -m unittest.
"""
import unittest
import sys
from pqc_bench.quantum_cost import estimate_quantum_resources, get_ml_kem_resources


class TestQuantumCostEstimation(unittest.TestCase):
    """Test quantum resource estimation for standardized PQC algorithms."""

    def test_ml_kem_512_quantum_resources(self):
        """ML-KEM-512 should estimate quantum resources correctly."""
        resources = estimate_quantum_resources("ml-kem-512")
        self.assertEqual(resources["logical_qubits"], 2361)
        self.assertEqual(resources["t_gate_count"], 1707050)
        self.assertEqual(resources["surface_code_distance"], 67)

    def test_ml_kem_768_quantum_resources(self):
        """ML-KEM-768 should estimate quantum resources correctly."""
        resources = estimate_quantum_resources("ml-kem-768")
        self.assertEqual(resources["logical_qubits"], 4215)
        self.assertEqual(resources["t_gate_count"], 5474000)
        self.assertEqual(resources["surface_code_distance"], 101)

    def test_ml_kem_1024_quantum_resources(self):
        """ML-KEM-1024 should estimate quantum resources correctly."""
        resources = estimate_quantum_resources("ml-kem-1024")
        self.assertEqual(resources["logical_qubits"], 7281)
        self.assertEqual(resources["t_gate_count"], 11536000)
        self.assertEqual(resources["surface_code_distance"], 133)

    def test_get_ml_kem_resources(self):
        """get_ml_kem_resources should return complete dict with all fields."""
        info = get_ml_kem_resources("ml-kem-768")
        self.assertIn("n", info)
        self.assertIn("q", info)
        self.assertIn("logical_qubits", info)
        self.assertIn("t_gate_count", info)
        self.assertIn("t_depth", info)
        self.assertIn("physical_qubits", info)
        self.assertIn("surface_code_distance", info)
        self.assertIn("runtime_seconds", info)
        self.assertIn("description", info)

    def test_estimate_has_required_fields(self):
        """estimate_quantum_resources should return dict with all required fields."""
        resources = estimate_quantum_resources("ml-kem-768")
        required_fields = [
            "scheme", "n", "q", "logical_qubits", "t_gate_count",
            "t_depth", "physical_qubits", "surface_code_distance",
            "runtime_seconds", "description"
        ]
        for field in required_fields:
            self.assertIn(field, resources)


if __name__ == '__main__':
    unittest.main()