import numpy as np

class ReadinessScoreEngine:
    """
    Kurumsal Kuantum Güvenlik Hazırlık (Readiness) Skoru Hesaplama Motoru.
    Algoritmalar, donanım, bulut ve kütüphane bazlı güvenlik metriklerini analiz eder.
    """
    
    def __init__(self, weights=None):
        # Varsayılan ağırlıklar: [Algoritma, Donanım, Bulut, Kütüphane]
        self.weights = weights or {"algorithm": 0.4, "hardware": 0.2, "cloud": 0.2, "library": 0.2}
        
    def calculate_score(self, metrics):
        """
        metrics: dict {'algorithm': 0-100, 'hardware': 0-100, 'cloud': 0-100, 'library': 0-100}
        """
        score = sum(metrics[k] * self.weights[k] for k in metrics if k in self.weights)
        return float(np.clip(score, 0, 100))

def get_engine():
    return ReadinessScoreEngine()
