"""
Hardware Power Calibration and Simulation Module.
Models CPU nanometre power consumption profiles (x86_64, ARM64, Apple Silicon)
and correlates power signatures with cryptographic operations (NTT, Keccak, AES).
"""

import math
from typing import Dict, Any, List, Optional


class PowerCalibrationEngine:
    """Simulates hardware power consumption and power-trace calibration for PQC operations."""

    SUPPORTED_ARCHS = {
        "x86_64": {
            "node_nm": 7,  # e.g., AMD Ryzen / Intel Core 7nm/10nm
            "base_power_mw": 15000.0,
            "peak_power_mw": 65000.0,
            "voltage_v": 1.25,
            "thermal_coefficient": 0.035,
        },
        "arm64": {
            "node_nm": 5,  # e.g., Neoverse N1/N2 5nm
            "base_power_mw": 2500.0,
            "peak_power_mw": 15000.0,
            "voltage_v": 0.90,
            "thermal_coefficient": 0.020,
        },
        "apple_silicon": {
            "node_nm": 3,  # e.g., M2/M3 Pro 3nm
            "base_power_mw": 1200.0,
            "peak_power_mw": 10000.0,
            "voltage_v": 0.80,
            "thermal_coefficient": 0.015,
        }
    }

    def __init__(self, architecture: str = "x86_64"):
        if architecture not in self.SUPPORTED_ARCHS:
            raise ValueError(f"Unsupported architecture: {architecture}. Choose from {list(self.SUPPORTED_ARCHS.keys())}")
        self.arch = architecture
        self.specs = self.SUPPORTED_ARCHS[architecture]

    def calibrate_operation(self, op_name: str, iterations: int = 1000) -> Dict[str, Any]:
        """
        Calibrates estimated power consumption profile for a given cryptographic operation.
        """
        base = self.specs["base_power_mw"]
        peak = self.specs["peak_power_mw"]
        v = self.specs["voltage_v"]
        
        # Operation complexity factors
        weights = {
            "ntt": 1.4,
            "intt": 1.45,
            "keccak": 1.1,
            "ml_kem_encaps": 1.8,
            "ml_kem_decaps": 2.1,
            "ml_dsa_sign": 2.5,
            "ml_dsa_verify": 1.6
        }
        
        factor = weights.get(op_name.lower(), 1.0)
        
        # Dynamic power estimation model: P = C * V^2 * f * factor
        estimated_active_mw = base + (peak - base) * min(1.0, (factor * math.log(iterations + 1)) / 10.0)
        energy_microjoules = (estimated_active_mw * (iterations * 0.001))  # rough proxy
        
        return {
            "architecture": self.arch,
            "node_nm": self.specs["node_nm"],
            "operation": op_name,
            "iterations": iterations,
            "voltage_v": v,
            "estimated_power_mw": round(estimated_active_mw, 2),
            "estimated_energy_uj": round(energy_microjoules, 2),
            "correlation_coefficient": round(0.85 + (0.13 * (self.specs["node_nm"] / 10.0)), 4)
        }

    def simulate_power_trace(self, op_name: str, sample_points: int = 500) -> List[float]:
        """
        Generates a synthetic simulated power trace (milliwatts) over sample points for side-channel analysis.
        """
        import random
        base = self.specs["base_power_mw"]
        peak = self.specs["peak_power_mw"]
        
        trace = []
        for i in range(sample_points):
            # Create rhythmic peaks corresponding to crypto rounds
            wave = math.sin(i * 2.0 * math.pi / 50.0) * (peak - base) * 0.3
            noise = random.gauss(0, (peak - base) * 0.05)
            val = base + ((peak - base) * 0.4) + wave + noise
            trace.append(round(max(0.0, val), 2))
            
        return trace
