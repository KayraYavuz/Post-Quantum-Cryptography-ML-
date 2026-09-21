"""
Fuzzing Module for Post-Quantum Cryptography
===========================================================

This module provides comprehensive fuzzing capabilities for testing and validating
ML-KEM and ML-DSA implementations for timing side-channels and security vulnerabilities.

Key Features:
- Constant-time fuzzing engine
- Security report generation
- Anomaly matrix analysis
- Integration with existing pqc_bench infrastructure

The module is designed to support the WS-P9.4 (Fuzzing Security Report) task,
providing both low-level fuzzing capabilities and high-level reporting tools.
"""

from .ct_fuzzer import (
    constant_time_fuzz,
    fuzz_kem_implementation,
    fuzz_dsa_implementation,
    analyze_timing_variance,
    generate_edge_case_report,
    EDGE_CASES,
    KEM_PARAMS,
    DSA_PARAMS,
)

from .fuzzing_report import FuzzingSecurityReporter

__all__ = [
    # Core fuzzing functions
    "constant_time_fuzz",
    "fuzz_kem_implementation",
    "fuzz_dsa_implementation",
    "analyze_timing_variance",
    "generate_edge_case_report",
    # Edge case definitions
    "EDGE_CASES",
    "KEM_PARAMS",
    "DSA_PARAMS",
    # Reporting classes
    "FuzzingSecurityReporter",
]

# Version information
__version__ = "1.0.0"
__author__ = "Post-Quantum Cryptography Project"
__date__ = "2026-09-21"