import unittest
import numpy as np

class ReadinessScoreEngine:
    """
    0-100 ölçeğinde kurumsal PQC hazırlık skoru hesaplar.
    Ağırlıklar:
    - Kriptografik Uyumluluk (40%): FIPS, CNSA, hibrit yapılar.
    - Donanım Direnci (30%): Sabit zamanlılık, maskeleme, yan kanal.
    - İşletimsel Güvenlik (30%): Fuzzing, bellek güvenliği, CI/CD.
    """
    def __init__(self, crypto_score, hardware_score, operational_score):
        self.crypto_score = np.clip(crypto_score, 0, 100)
        self.hardware_score = np.clip(hardware_score, 0, 100)
        self.operational_score = np.clip(operational_score, 0, 100)

    def calculate(self):
        score = (self.crypto_score * 0.4) + (self.hardware_score * 0.3) + (self.operational_score * 0.3)
        return round(score, 2)

    def get_status(self):
        score = self.calculate()
        if score >= 90: return "EXCELLENT"
        if score >= 70: return "READY"
        if score >= 50: return "WARNING"
        return "CRITICAL"
