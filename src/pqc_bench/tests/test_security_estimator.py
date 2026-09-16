"""Security level estimation unit tests for PQC algorithms.

Tests for the security_estimator module, verifying:
- Correct security bit estimation for PQC algorithms
- NIST category assignments
- Security claim verification with ±2 bit tolerance
- Comprehensive security info retrieval
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pqc_bench.security_estimator import (
    estimate_security_bits,
    get_nist_category,
    verify_security_claim,
    get_security_info,
)


def test_ml_kem_768_security():
    """Test ML-KEM-768 security estimation ±2 bits."""
    # Per WS-A acceptance criteria: ML-KEM-768 literatürle ±2 bit
    bits = estimate_security_bits("ml-kem-768")
    assert bits == 192, f"Expected 192 bits for ml-kem-768, got {bits}"

    # Verify security claim
    verification = verify_security_claim("ml-kem-768", 192)
    assert verification["status"] == "valid", f"Expected valid claim, got {verification['status']}"
    assert verification["estimated_bits"] == 192

    print("✓ ML-KEM-768 security test passed")


def test_ml_kem_512_security():
    """Test ML-KEM-512 security estimation."""
    bits = estimate_security_bits("ml-kem-512")
    assert bits == 128, f"Expected 128 bits for ml-kem-512, got {bits}"

    verification = verify_security_claim("ml-kem-512", 128)
    assert verification["status"] == "valid"

    print("✓ ML-KEM-512 security test passed")


def test_ml_kem_1024_security():
    """Test ML-KEM-1024 security estimation."""
    bits = estimate_security_bits("ml-kem-1024")
    assert bits == 256, f"Expected 256 bits for ml-kem-1024, got {bits}"

    verification = verify_security_claim("ml-kem-1024", 256)
    assert verification["status"] == "valid"

    print("✓ ML-KEM-1024 security test passed")


def test_ml_dsa_65_security():
    """Test ML-DSA-65 security estimation."""
    bits = estimate_security_bits("ml-dsa-65")
    assert bits == 192, f"Expected 192 bits for ml-dsa-65, got {bits}"

    verification = verify_security_claim("ml-dsa-65", 192)
    assert verification["status"] == "valid"

    print("✓ ML-DSA-65 security test passed")


def test_slh_dsa_medium_security():
    """Test SLH-DSA-Medium security estimation."""
    bits = estimate_security_bits("slh-dsa-medium")
    assert bits == 192, f"Expected 192 bits for slh-dsa-medium, got {bits}"

    verification = verify_security_claim("slh-dsa-medium", 192)
    assert verification["status"] == "valid"

    print("✓ SLH-DSA-Medium security test passed")


def test_nist_categories():
    """Test NIST security category assignments."""
    # ML-KEM-768 should be cat3
    cat = get_nist_category("ml-kem-768")
    assert cat == "cat3", f"Expected cat3 for ml-kem-768, got {cat}"

    # ML-KEM-512 should be cat1
    cat = get_nist_category("ml-kem-512")
    assert cat == "cat1", f"Expected cat1 for ml-kem-512, got {cat}"

    # ML-DSA-65 should be cat3
    cat = get_nist_category("ml-dsa-65")
    assert cat == "cat3", f"Expected cat3 for ml-dsa-65, got {cat}"

    print("✓ NIST category test passed")


def test_security_info_comprehensive():
    """Test comprehensive security info retrieval."""
    info = get_security_info("ml-kem-768")
    assert info["algorithm"] == "ml-kem-768"
    assert info["security_bits"] == 192
    assert info["nist_category"] == "cat3"
    assert info["verification"]["status"] == "valid"

    info = get_security_info("ml-dsa-65")
    assert info["algorithm"] == "ml-dsa-65"
    assert info["security_bits"] == 192
    assert info["nist_category"] == "cat3"
    assert info["verification"]["status"] == "valid"

    print("✓ Comprehensive security info test passed")


def test_invalid_security_claim():
    """Test that invalid security claims are detected."""
    # Claim 100 bits for ML-KEM-768 (should be 192, so invalid)
    verification = verify_security_claim("ml-kem-768", 100)
    assert verification["status"] == "invalid", f"Expected invalid claim, got {verification['status']}"
    assert verification["estimated_bits"] == 192
    assert verification["lower_bound"] == 190  # 192 - 2
    assert verification["upper_bound"] == 194  # 192 + 2

    # Claim 200 bits for ML-KEM-768 (should be valid within ±2)
    verification = verify_security_claim("ml-kem-768", 193)
    assert verification["status"] == "valid", f"Expected valid claim, got {verification['status']}"

    print("✓ Invalid security claim detection test passed")


def test_unknown_algorithm_fallback():
    """Test fallback estimation for unknown algorithms."""
    # Unknown algorithm should still return a reasonable default
    bits = estimate_security_bits("unknown-alg")
    # Should default to 128 bits
    assert bits == 128, f"Expected 128 bits fallback, got {bits}"

    print("✓ Unknown algorithm fallback test passed")


if __name__ == "__main__":
    print("Running security estimator tests...")
    print("=" * 40)

    test_ml_kem_768_security()
    test_ml_kem_512_security()
    test_ml_kem_1024_security()
    test_ml_dsa_65_security()
    test_slh_dsa_medium_security()
    test_nist_categories()
    test_security_info_comprehensive()
    test_invalid_security_claim()
    test_unknown_algorithm_fallback()

    print("=" * 40)
    print("All security estimator tests passed!")