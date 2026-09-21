"""
PQC Readiness Score Engine.
Evaluates enterprise post-quantum cryptographic readiness (0-100 score) based on:
- Algorithm migration status (ML-KEM, ML-SLH, XMSS, Hybrid X25519Kyber)
- Side-channel protection level (Masking, DPA resistance, Active learning)
- Hardware security & tamper resistance (Secure element, QEMU ARM tests)
- Compliance with NIST SP 800-208 / CNSA 2.0
"""

class PQCReadinessCalculator:
    def __init__(self, config: dict):
        self.config = config

    def calculate_score(self) -> float:
        score = 0.0
        
        # 1. Algorithm Migration (Max 30 pts)
        algo_status = self.config.get("algorithm_migration", "none")
        if algo_status == "full_pqc":
            score += 30.0
        elif algo_status == "hybrid":
            score += 25.0
        elif algo_status == "transitional":
            score += 10.0

        # 2. Side-Channel Protection (Max 25 pts)
        sc_level = self.config.get("side_channel_protection", 0) # 0 to 3
        score += (sc_level / 3.0) * 25.0

        # 3. Hardware Security & FIPS / Secure Element (Max 25 pts)
        hw_sec = self.config.get("hardware_security", False)
        fips = self.config.get("fips_compliant", False)
        if hw_sec:
            score += 15.0
        if fips:
            score += 10.0

        # 4. Continuous Fuzzing & Integrity (Max 20 pts)
        fuzzing = self.config.get("fuzzing_passed", False)
        integrity = self.config.get("model_integrity_verified", False)
        if fuzzing:
            score += 10.0
        if integrity:
            score += 10.0

        return round(min(100.0, max(0.0, score)), 2)

    def get_recommendations(self) -> list:
        recs = []
        if self.config.get("algorithm_migration") != "full_pqc":
            recs.append("Upgrade legacy algorithms to NIST-standardized ML-KEM and ML-DSA / SLH-DSA.")
        if self.config.get("side_channel_protection", 0) < 3:
            recs.append("Implement higher-order masking and active learning defense mechanisms.")
        if not self.config.get("fips_compliant", False):
            recs.append("Obtain FIPS 140-3 validation for cryptographic modules.")
        if not self.config.get("model_integrity_verified", False):
            recs.append("Enable model poisoning protection and cryptographic weight verification.")
        return recs
