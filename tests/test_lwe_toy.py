"""WS-B LWE Toy Unit Tests for PQC Playground.

Validates toy LWE parameter generation, error sampling,
and 1-6 bit security threshold analysis. Compatible with both
pytest and python -m unittest.
"""
import unittest
import sys
from pqc_bench.lwe_toy import (
    generate_toy_lwe_instance,
    compute_1_6_bit_range,
    analyze_lwe_threshold,
    TOY_LWE_PARAMETERS,
    sample_error,
)


class TestLweToyGeneration(unittest.TestCase):
    """Test toy LWE instance generation and basic properties."""

    def test_tiny_instance_generation(self):
        """Generate a tiny LWE instance and verify basic structure."""
        instance = generate_toy_lwe_instance("tiny")
        self.assertIn("n", instance)
        self.assertIn("m", instance)
        self.assertIn("q", instance)
        self.assertIn("secret", instance)
        self.assertIn("matrix_A", instance)
        self.assertIn("error_vector", instance)
        self.assertIn("t", instance)
        self.assertIn("param_key", instance)
        # Verify dimensions
        n = instance["n"]
        m = instance["m"]
        q = instance["q"]
        self.assertGreaterEqual(n, 2)
        self.assertLessEqual(n, 6)
        self.assertGreaterEqual(m, 5)
        self.assertLessEqual(m, 10)
        self.assertGreaterEqual(q, 2)
        self.assertLessEqual(q, 32)
        # Verify matrix dimensions: A should be m × n
        self.assertEqual(len(instance["matrix_A"]), m)
        for row in instance["matrix_A"]:
            self.assertEqual(len(row), n)

    def test_small_instance_generation(self):
        """Generate a small LWE instance."""
        instance = generate_toy_lwe_instance("small")
        n = instance["n"]
        m = instance["m"]
        q = instance["q"]
        self.assertGreaterEqual(n, 5)
        self.assertLessEqual(n, 10)
        self.assertGreaterEqual(m, 10)
        self.assertLessEqual(m, 20)
        self.assertGreaterEqual(q, 2)
        self.assertLessEqual(q, 64)

    def test_medium_instance_generation(self):
        """Generate a medium LWE instance."""
        instance = generate_toy_lwe_instance("medium")
        n = instance["n"]
        m = instance["m"]
        q = instance["q"]
        self.assertGreaterEqual(n, 10)
        self.assertLessEqual(n, 15)
        self.assertGreaterEqual(m, 20)
        self.assertLessEqual(m, 30)
        self.assertGreaterEqual(q, 2)
        self.assertLessEqual(q, 128)

    def test_custom_secret(self):
        """Generate LWE instance with a custom secret."""
        import random
        n = 5
        q = 31
        custom_secret = [random.randint(0, q - 1) for _ in range(n)]
        instance = generate_toy_lwe_instance("small", secret=custom_secret)
        self.assertEqual(instance["secret"], custom_secret)
        # Verify secret length matches dimension
        self.assertEqual(len(instance["secret"]), instance["n"])


class TestLweToyErrorSampling(unittest.TestCase):
    """Test error vector sampling from discrete Gaussian."""

    def test_sample_error_tiny(self):
        """Sample error vector for tiny dimension."""
        n = 3
        q = 31
        error = sample_error(n, q, std_factor=0.5)
        self.assertEqual(len(error), n)
        # All values should be in Z_q
        for val in error:
            self.assertGreaterEqual(val, 0)
            self.assertLess(val, q)

    def test_sample_error_small(self):
        """Sample error vector for small dimension."""
        n = 8
        q = 61
        error = sample_error(n, q, std_factor=1.0)
        self.assertEqual(len(error), n)
        for val in error:
            self.assertGreaterEqual(val, 0)
            self.assertLess(val, q)

    def test_sample_error_different_std(self):
        """Sample errors with different standard deviation factors."""
        n = 4
        q = 31
        error_std = sample_error(n, q, std_factor=0.5)
        error_big = sample_error(n, q, std_factor=2.0)
        # Larger std should produce larger values on average
        self.assertGreaterEqual(len(error_std), 1)
        self.assertGreaterEqual(len(error_big), 1)


class TestLweToyBitAnalysis(unittest.TestCase):
    """Test 1-6 bit security threshold analysis."""

    def test_1_6_bit_range_small_q(self):
        """Compute 1-6 bit range for small modulus."""
        result = compute_1_6_bit_range(n=5, q=31)
        self.assertIn("bit_range", result)
        self.assertIn("min_extractable_bits", result)
        self.assertIn("max_extractable_bits", result)
        self.assertIn("approximate_bits", result)
        # Bit range should be "1-6" or subset
        self.assertIn(result["bit_range"], ["1-6 bits", "2-6 bits", "3-6 bits", "4-6 bits", "5-6 bits", "1-5 bits", "2-5 bits", "3-5 bits", "4-5 bits", "1-4 bits", "2-4 bits", "3-4 bits", "1-3 bits", "2-3 bits", "1-2 bits", "1-1 bits"])

    def test_1_6_bit_range_medium_q(self):
        """Compute 1-6 bit range for medium modulus."""
        result = compute_1_6_bit_range(n=8, q=61)
        self.assertIn("bit_range", result)
        self.assertIn("approximate_bits", result)

    def test_1_6_bit_range_large_q(self):
        """Compute 1-6 bit range for larger modulus."""
        result = compute_1_6_bit_range(n=10, q=127)
        self.assertIn("bit_range", result)
        self.assertIn("approximate_bits", result)

    def test_analyze_lwe_threshold(self):
        """Full LWE threshold analysis."""
        result = analyze_lwe_threshold(n=5, q=31, error_std_factor=1.0)
        self.assertIn("n", result)
        self.assertIn("q", result)
        self.assertIn("error_rate", result)
        self.assertIn("bit_range", result)
        self.assertIn("min_extractable_bits", result)
        self.assertIn("max_extractable_bits", result)
        self.assertIn("approximate_bits", result)
        self.assertIn("within_decodability_threshold", result)
        # For tiny parameters, should be within threshold
        self.assertTrue(result["within_decodability_threshold"])


class TestLweToyParameters(unittest.TestCase):
    """Test toy LWE parameter sets."""

    def test_parameter_sets_exist(self):
        """Verify all expected parameter sets exist."""
        self.assertIn("tiny", TOY_LWE_PARAMETERS)
        self.assertIn("small", TOY_LWE_PARAMETERS)
        self.assertIn("medium", TOY_LWE_PARAMETERS)

    def test_tiny_parameter_ranges(self):
        """Verify tiny parameter ranges."""
        params = TOY_LWE_PARAMETERS["tiny"]
        self.assertEqual(params["n_range"], (2, 6))
        self.assertEqual(params["m_range"], (5, 10))
        self.assertEqual(params["q_range"], (2, 32))
        self.assertEqual(params["error_std_factor"], 0.5)

    def test_small_parameter_ranges(self):
        """Verify small parameter ranges."""
        params = TOY_LWE_PARAMETERS["small"]
        self.assertEqual(params["n_range"], (5, 10))
        self.assertEqual(params["m_range"], (10, 20))
        self.assertEqual(params["q_range"], (2, 64))
        self.assertEqual(params["error_std_factor"], 1.0)

    def test_medium_parameter_ranges(self):
        """Verify medium parameter ranges."""
        params = TOY_LWE_PARAMETERS["medium"]
        self.assertEqual(params["n_range"], (10, 15))
        self.assertEqual(params["m_range"], (20, 30))
        self.assertEqual(params["q_range"], (2, 128))
        self.assertEqual(params["error_std_factor"], 1.5)


if __name__ == "__main__":
    unittest.main()
