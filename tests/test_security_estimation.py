"""WS-A Security Estimation Tests for PQC Algorithms.

Validates security bit estimates against NIST SP 800-208 and cryptographic literature.
Compatible with both pytest and python -m unittest.
"""
import unittest
import sys
from pqc_bench.security_estimator import estimate_security_bits, get_security_info, verify_security_claim


class TestSecurityEstimation(unittest.TestCase):
    """Test security bit estimation for standardized PQC algorithms."""

    def test_ml_kem_512_security_bits(self):
        """ML-KEM-512 should estimate 128 security bits."""
        bits = estimate_security_bits("ml-kem-512")
        self.assertEqual(bits, 128)

    def test_ml_kem_768_security_bits(self):
        """ML-KEM-768 should estimate 192 security bits (literature ±2 bit tolerance)."""
        bits = estimate_security_bits("ml-kem-768")
        # Per NIST SP 800-208 and draft guidelines, ML-KEM-768 = 192 bits
        # Literature tolerance: ±2 bits
        self.assertEqual(bits, 192)

    def test_ml_kem_1024_security_bits(self):
        """ML-KEM-1024 should estimate 256 security bits."""
        bits = estimate_security_bits("ml-kem-1024")
        self.assertEqual(bits, 256)

    def test_ml_dsa_44_security_bits(self):
        """ML-DSA-44 should estimate 128 security bits."""
        bits = estimate_security_bits("ml-dsa-44")
        self.assertEqual(bits, 128)

    def test_ml_dsa_65_security_bits(self):
        """ML-DSA-65 should estimate 192 security bits."""
        bits = estimate_security_bits("ml-dsa-65")
        self.assertEqual(bits, 192)

    def test_ml_dsa_87_security_bits(self):
        """ML-DSA-87 should estimate 256 security bits."""
        bits = estimate_security_bits("ml-dsa-87")
        self.assertEqual(bits, 256)

    def test_slh_dsa_simple_security_bits(self):
        """SLH-DSA-simple should estimate 128 security bits."""
        bits = estimate_security_bits("slh-dsa-simple")
        self.assertEqual(bits, 128)

    def test_slh_dsa_medium_security_bits(self):
        """SLH-DSA-medium should estimate 192 security bits."""
        bits = estimate_security_bits("slh-dsa-medium")
        self.assertEqual(bits, 192)

    def test_slh_dsa_full_security_bits(self):
        """SLH-DSA-full should estimate 256 security bits."""
        bits = estimate_security_bits("slh-dsa-full")
        self.assertEqual(bits, 256)

    def test_verify_ml_kem_768_claim(self):
        """Verify ML-KEM-768 claimed security level ±2 bit tolerance."""
        result = verify_security_claim("ml-kem-768", 192, tolerance=2)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["estimated_bits"], 192)

    def test_verify_ml_kem_768_invalid_claim(self):
        """Verify that invalid claims are rejected."""
        result = verify_security_claim("ml-kem-768", 128, tolerance=2)
        self.assertEqual(result["status"], "invalid")

    def test_security_info_has_nist_category(self):
        """get_security_info should include NIST category for known algorithms."""
        info = get_security_info("ml-kem-768")
        self.assertIn("nist_category", info)
        self.assertIsInstance(info["nist_category"], str)

    def test_security_info_completeness(self):
        """get_security_info should return complete dict with all fields."""
        info = get_security_info("ml-kem-768")
        self.assertIn("security_bits", info)
        self.assertIn("nist_category", info)
        self.assertIn("verification", info)


if __name__ == '__main__':
    unittest.main()