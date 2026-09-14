"""
WS-0 Smoke Test: Infrastructure & Package Verification.
Compatible with both pytest and python -m unittest.
"""
import unittest
import sys
import pqc_bench

class TestInfra(unittest.TestCase):
    def test_package_metadata(self):
        self.assertEqual(pqc_bench.__version__, '0.1.0')
        self.assertIn('FIPS-203 (ML-KEM)', pqc_bench.__standards__)

    def test_python_version(self):
        self.assertGreaterEqual(sys.version_info, (3, 11))

if __name__ == '__main__':
    unittest.main()
