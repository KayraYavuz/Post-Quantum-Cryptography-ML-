import math

class ReadinessScoreEngine:
    def __init__(self):
        # Default weights for corporate readiness factors
        self.weights = {
            "algorithm_compliance": 0.30,
            "hardware_security": 0.25,
            "software_integrity": 0.25,
            "operational_resilience": 0.20
        }

    def calculate_score(self, metrics: dict) -> float:
        """
        0-100 kurumsal kuantum güvenilirlik skoru motoru.
        metrics örneği: {"algorithm_compliance": 90, "hardware_security": 85, ...}
        """
        score = 0.0
        for factor, weight in self.weights.items():
            value = metrics.get(factor, 0.0)
            score += value * weight
        return round(max(0.0, min(100.0, score)), 2)
