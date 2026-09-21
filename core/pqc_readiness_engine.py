import math
import statistics

class PQCReadinessEngine:
    """
    0-100 ölçeğinde kurumsal PQC (Post-Quantum Cryptography) güvenilirlik skoru motoru.
    İşletmelerin PQC geçiş stratejilerini; kriptografik çeviklik, donanım uyumluluğu,
    yan kanal direnci ve CBOM envanter skorlarına göre hesaplar.
    """
    def __init__(self, crypto_agility=0.0, hardware_compatibility=0.0, side_channel_resistance=0.0, cbom_coverage=0.0):
        self.crypto_agility = max(0, min(100, crypto_agility))
        self.hardware_compatibility = max(0, min(100, hardware_compatibility))
        self.side_channel_resistance = max(0, min(100, side_channel_resistance))
        self.cbom_coverage = max(0, min(100, cbom_coverage))

    def calculate_score(self) -> float:
        """
        Ağırlıklı PQC Hazırlık İndeksi (Readiness Score):
        Agility: %30, Hardware: %20, SideChannel: %30, CBOM: %20
        """
        weights = [0.3, 0.2, 0.3, 0.2]
        scores = [self.crypto_agility, self.hardware_compatibility, self.side_channel_resistance, self.cbom_coverage]
        
        final_score = sum(s * w for s, w in zip(scores, weights))
        return round(final_score, 2)

    def get_risk_level(self, score: float) -> str:
        if score >= 90: return "EXCELLENT"
        if score >= 75: return "GOOD"
        if score >= 50: return "MODERATE"
        return "CRITICAL"

if __name__ == "__main__":
    # Örnek kullanım ve doğrulama
    engine = PQCReadinessEngine(crypto_agility=85.0, hardware_compatibility=70.0, side_channel_resistance=90.0, cbom_coverage=95.0)
    score = engine.calculate_score()
    print(f"PQC Readiness Score: {score} - {engine.get_risk_level(score)}")
