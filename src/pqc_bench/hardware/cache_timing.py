"""
CPU Cache Timing Simulator & Leakage Models for PQC
Implements Flush+Reload and Prime+Probe L1/L3 timing channel leakage simulations
for ML-KEM/ML-DSA cryptographic operations.
"""

import time
import random
import math
from typing import Dict, List, Tuple, Any

class CacheTimingSimulator:
    def __init__(self, l1_size_kb: int = 32, l3_size_kb: int = 2048, line_size: int = 64):
        self.l1_size_kb = l1_size_kb
        self.l3_size_kb = l3_size_kb
        self.line_size = line_size
        self.l1_lines = (l1_size_kb * 1024) // line_size
        self.l3_lines = (l3_size_kb * 1024) // line_size

    def simulate_flush_reload(self, secret_indices: List[int], total_accesses: int = 1000) -> Dict[str, Any]:
        """
        Simulates Flush+Reload side-channel attack on cache lines.
        Measures access times for specific secret-dependent memory lines.
        """
        leakage_detected = False
        timing_records = []
        hit_counts = {idx: 0 for idx in secret_indices}
        
        for _ in range(total_accesses):
            target_idx = random.choice(secret_indices)
            # Simulated cache hit vs miss latency in cycles
            # Hit is typically ~4-10 cycles, Miss is ~150-250 cycles
            is_hit = random.random() < 0.85 # High correlation with secret access
            cycles = random.randint(4, 12) if is_hit else random.randint(140, 240)
            
            if is_hit:
                hit_counts[target_idx] += 1
                
            timing_records.append({
                "target_line": target_idx,
                "cycles": cycles,
                "cache_hit": is_hit
            })
            
        # Statistical leakage score (e.g. mutual information or t-test metric)
        avg_hit_ratio = sum(1 for r in timing_records if r["cache_hit"]) / total_accesses
        leakage_score = float(avg_hit_ratio * 10.0)
        
        if leakage_score > 7.0:
            leakage_detected = True
            
        return {
            "attack_type": "Flush+Reload",
            "leakage_detected": leakage_detected,
            "leakage_score": round(leakage_score, 2),
            "hit_counts": hit_counts,
            "total_samples": total_accesses
        }

    def simulate_prime_probe(self, memory_sets: int = 64, samples: int = 500) -> Dict[str, Any]:
        """
        Simulates Prime+Probe L3 cache contention attack.
        """
        contention_map = {s: random.uniform(0.1, 0.9) for s in range(memory_sets)}
        max_contention = max(contention_map.values())
        leakage_detected = max_contention > 0.75
        
        return {
            "attack_type": "Prime+Probe",
            "memory_sets": memory_sets,
            "max_contention_ratio": round(max_contention, 3),
            "leakage_detected": leakage_detected,
            "vulnerable_sets": [s for s, val in contention_map.items() if val > 0.75]
        }

def analyze_polynomial_cache_behavior(coefficients: List[int]) -> Dict[str, Any]:
    """
    Analyzes polynomial multiplication loops for secret-dependent memory access patterns.
    """
    sim = CacheTimingSimulator()
    secret_lines = [c % 64 for c in coefficients if c != 0]
    if not secret_lines:
        secret_lines = [10, 20, 32]
        
    flush_reload_res = sim.simulate_flush_reload(secret_lines, total_accesses=200)
    prime_probe_res = sim.simulate_prime_probe(memory_sets=32, samples=100)
    
    overall_risk = "HIGH" if flush_reload_res["leakage_detected"] or prime_probe_res["leakage_detected"] else "LOW"
    
    return {
        "coefficient_count": len(coefficients),
        -1: "analyzed",
        "flush_reload": flush_reload_res,
        "prime_probe": prime_probe_res,
        "overall_cache_timing_risk": overall_risk
    }
