"""
Phase 9 Overflow Detection Unit Tests

Tests the NTT coefficient multiplication modular integer overflow detection
implemented in src/pqc_bench/lwe_toy.py.
"""

import pytest
from pqc_bench.lwe_toy import safe_ntt_coeff_mul, check_ntt_overflow_risk


class TestSafeNttCoeffMul:
    """Tests for safe_ntt_coeff_mul function."""

    def test_basic_multiplication(self):
        """Test basic NTT coefficient multiplication without overflow."""
        result = safe_ntt_coeff_mul(5, 7, 101)
        assert result == 35 % 101  # 35

    def test_overflow_detection(self):
        """Test that overflow is tracked when product exceeds 64-bit range."""
        # Use large values that exceed 2^63-1 when multiplied
        a = 2**33  # 8589934592
        b = 2**32  # 4294967296
        q = 2**16 + 1
        result = safe_ntt_coeff_mul(a, b, q)
        # Python handles big integers, result should be (a * b) % q
        expected = (a * b) % q
        assert result == expected

    def test_small_coefficients(self):
        """Test with small coefficient values typical in NTT."""
        for a in [1, 2, 3, 10, 100]:
            for b in [1, 2, 3, 10, 100]:
                for q in [127, 257, 1024]:
                    result = safe_ntt_coeff_mul(a % q, b % q, q)
                    expected = (a * b) % q
                    assert result == expected

    def test_with_prime_moduli(self):
        """Test with common NTT prime moduli."""
        # Kyber uses q = 3329 (prime of form k*2^n + 1)
        q_kyber = 3329
        for a in [100, 500, 1000, 2000]:
            for b in [100, 500, 1000, 2000]:
                a_reduced = a % q_kyber
                b_reduced = b % q_kyber
                result = safe_ntt_coeff_mul(a_reduced, b_reduced, q_kyber)
                expected = (a_reduced * b_reduced) % q_kyber
                assert result == expected


class TestCheckNttOverflowRisk:
    """Tests for check_ntt_overflow_risk function."""

    def test_no_overflow_small_values(self):
        """No overflow risk when product is within 64-bit range."""
        result = check_ntt_overflow_risk(100, 200, 3329)
        assert result["product_exceeds_64bit"] is False
        assert result["overflow_risk"] is False
        assert result["both_operands_less_than_q"] is True

    def test_overflow_risk_detected_raw(self):
        """Overflow risk detected when raw product exceeds 64-bit before mod q."""
        # Test with raw values (not yet reduced mod q) that produce overflow
        a = 1 << 33  # 8589934592
        b = 1 << 32  # 4294967296
        q = 3329
        # Note: function receives raw a, b before mod q reduction
        result = check_ntt_overflow_risk(a, b, q)
        # product = 2^65 which exceeds 2^63-1
        assert result["product_exceeds_64bit"] is True
        # overflow_risk: product > max_safe and product > q
        assert result["overflow_risk"] is True
        # both_operands_less_than_q: a and b as-passed (not reduced)
        # After mod q reduction, they'll be < q
        assert result["both_operands_less_than_q"] is False

    def test_both_operands_less_than_q(self):
        """Test that both_operands_less_than_q flag works correctly."""
        result = check_ntt_overflow_risk(100, 200, 5000)
        # 100 < 5000 and 200 < 5000
        assert result["both_operands_less_than_q"] is True

    def test_overflow_with_reduced_coeffs(self):
        """Product exceeds 64-bit but q is smaller than product (with reduced coeffs)."""
        # When a and b are reduced mod q first, product is typically small
        # This test shows the function behavior with reduced coefficients
        a = 50  # reduced mod 101
        b = 60  # reduced mod 101
        q = 101
        result = check_ntt_overflow_risk(a, b, q)
        # 50 * 60 = 3000, well within 64-bit range
        assert result["product_exceeds_64bit"] is False
        assert result["overflow_risk"] is False
        assert result["both_operands_less_than_q"] is True

    def test_exactly_at_boundary(self):
        """Test product exactly at 2^63-1 boundary with raw values."""
        # Use raw values exactly at the 64-bit boundary
        a = 1
        b = 2**63 - 1  # Exactly at boundary (9223372036854775807)
        q = 101
        # Without mod q reduction first
        result = check_ntt_overflow_risk(a, b, q)
        # product = 2^63 - 1 which is NOT > 2^63 - 1 (it's equal)
        assert result["product_exceeds_64bit"] is False
        # With mod q reduction
        result_mod = check_ntt_overflow_risk(a % q, b % q, q)
        # After reduction, product is small
        assert result_mod["product_exceeds_64bit"] is False


class TestOverflowEdgeCases:
    """Edge case tests for overflow detection."""

    def test_reduced_coeffs_small_product(self):
        """After mod q reduction, product is typically within 64-bit range."""
        # NTT coefficients are always reduced mod q, so product (q-1)^2 is small
        # for practical modulus values
        for q in [127, 257, 1024, 3329]:
            a = q - 1  # Maximum NTT coefficient
            b = q - 1
            result = check_ntt_overflow_risk(a, b, q)
            # (q-1)^2 is well within 64-bit for all practical q values
            assert result["product_exceeds_64bit"] is False
            assert result["both_operands_less_than_q"] is True

    def test_zero_coefficients(self):
        """Test with zero coefficients."""
        result = check_ntt_overflow_risk(0, 100, 3329)
        assert result["product_exceeds_64bit"] is False
        assert result["overflow_risk"] is False
        assert result["both_operands_less_than_q"] is True

    def test_small_prime_moduli(self):
        """Test with small prime moduli typical in toy LWE implementations."""
        for q in [17, 23, 257, 65537]:
            a = q - 1
            b = q - 1
            result = check_ntt_overflow_risk(a, b, q)
            assert result["both_operands_less_than_q"] is True
            # Product (q-1)^2 should be well within 64-bit
            assert result["product_exceeds_64bit"] is False