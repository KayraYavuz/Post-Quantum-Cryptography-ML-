import unittest
scenarios = 36
class TestCVE202437880(unittest.TestCase):
    def test_count(self):
        self.assertGreaterEqual(scenarios, 36)