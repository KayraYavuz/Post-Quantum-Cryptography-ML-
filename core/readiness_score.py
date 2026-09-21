import numpy as np

class ReadinessScoreEngine:
    def __init__(self):
        # Ağırlıklar: [FIPS 140-3, PQC-Latency, Memory-Safety, Fuzzing-Pass, Hardware-Accelerated]
        self.weights = np.array([0.3, 0.2, 0.2, 0.2, 0.1])
        
    def calculate_score(self, metrics):
        """
        metrics: list of 5 floats (0-100)
        """
        if len(metrics) != 5:
            raise ValueError("Metrics must contain exactly 5 values.")
            
        score = np.dot(np.array(metrics), self.weights)
        return float(np.clip(score, 0, 100))

# Basit bir kullanım örneği
if __name__ == "__main__":
    engine = ReadinessScoreEngine()
    # Örnek metrikler
    metrics = [95.0, 88.0, 92.0, 98.0, 85.0]
    print(f"Readiness Score: {engine.calculate_score(metrics)}")
