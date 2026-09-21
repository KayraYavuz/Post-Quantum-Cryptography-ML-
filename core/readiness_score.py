import numpy as np

class ReadinessScoreEngine:
    """
    0-100 kurumsal PQC güvenlik hazırlık skoru motoru.
    İşletmenin PQC geçişindeki olgunluğunu ölçer.
    """
    def __init__(self):
        self.metrics = {
            "pqc_algorithm_adoption": 0.0,  # %0-100
            "hardware_acceleration": 0.0,   # %0-100
            "compliance_rating": 0.0,       # %0-100
            "fuzzing_coverage": 0.0         # %0-100
        }

    def update_metric(self, metric_name, value):
        if metric_name in self.metrics:
            self.metrics[metric_name] = np.clip(float(value), 0.0, 100.0)

    def calculate_score(self):
        """Ağırlıklı skor hesaplama."""
        weights = {
            "pqc_algorithm_adoption": 0.4,
            "hardware_acceleration": 0.2,
            "compliance_rating": 0.2,
            "fuzzing_coverage": 0.2
        }
        score = sum(self.metrics[m] * weights[m] for m in weights)
        return round(score, 2)

    def get_recommendations(self):
        return ["Upgrade to full PQC", "Check hardware acceleration"]

class PQCReadinessCalculator:
    def __init__(self, config):
        self.engine = ReadinessScoreEngine()
        self.engine.update_metric("pqc_algorithm_adoption", 100.0 if config.get("algorithm_migration") == "full_pqc" else 0.0)
        self.engine.update_metric("hardware_acceleration", 100.0 if config.get("hardware_security") else 0.0)
        self.engine.update_metric("compliance_rating", 100.0 if config.get("fips_compliant") else 0.0)
        self.engine.update_metric("fuzzing_coverage", 100.0 if config.get("fuzzing_passed") else 0.0)

    def calculate_score(self):
        return self.engine.calculate_score()

    def get_recommendations(self):
        return self.engine.get_recommendations()

    def get_readiness_level(self):
        score = self.calculate_score()
        if score >= 90: return "CRITICAL_READY"
        if score >= 70: return "PROD_READY"
        if score >= 50: return "DEVELOPMENT_READY"
        return "NON_COMPLIANT"
