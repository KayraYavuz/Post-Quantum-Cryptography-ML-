import unittest
from core.readiness_score import ReadinessScoreEngine

class TestReadinessScoreEngine(unittest.TestCase):
    def test_calculation(self):
        engine = ReadinessScoreEngine(100, 80, 70)
        # (100*0.4) + (80*0.3) + (70*0.3) = 40 + 24 + 21 = 85
        self.assertEqual(engine.calculate(), 85.0)

    def test_status_excellent(self):
        engine = ReadinessScoreEngine(100, 100, 90)
        self.assertEqual(engine.get_status(), "EXCELLENT")

    def test_status_critical(self):
        engine = ReadinessScoreEngine(20, 20, 20)
        self.assertEqual(engine.get_status(), "CRITICAL")

    def test_clipping(self):
        engine = ReadinessScoreEngine(150, -50, 70)
        # (100*0.4) + (0*0.3) + (70*0.3) = 40 + 0 + 21 = 61
        self.assertEqual(engine.calculate(), 61.0)

if __name__ == '__main__':
    unittest.main()
