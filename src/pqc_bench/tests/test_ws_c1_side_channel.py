"""WS-C.1: GE Compatible Side Channel Setup and 1st/2nd Tier Separation unit tests.

Tests for the ws_c1_side_channel module, verifying:
- GE compatibility checking
- Tier instrumentation setup
- Tier-aware analysis execution
- Tier separation filtering
- BOM generation for side-channel configurations
- Compiler matrix tier analysis
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pqc_bench.constant_time.ws_c1_side_channel import (
    TIER_1,
    TIER_2,
    TIER_LEVELS,
    GE_PROFILE,
    check_ge_compatibility,
    setup_tier_instrumentation,
    run_tier_analysis,
    separate_tiers,
    generate_side_channel_bom,
    run_compiler_matrix_tiers,
)


def test_ge_compatibility():
    """Test GE compatibility checking for known algorithms."""
    # ML-KEM should be GE compatible with masking
    assert check_ge_compatibility("ml-kem-768")["ge_compatible"] is True
    assert check_ge_compatibility("ml-kem-512")["ge_compatible"] is True
    assert check_ge_compatibility("ml-kem-1024")["ge_compatible"] is True
    
    # ML-DSA should be GE compatible with blinding
    assert check_ge_compatibility("ml-dsa-65")["ge_compatible"] is True
    assert check_ge_compatibility("ml-dsa-87")["ge_compatible"] is True
    assert check_ge_compatibility("ml-dsa-44")["ge_compatible"] is True
    
    # SLH-DSA should be GE compatible with randomization
    assert check_ge_compatibility("slh-dsa-medium")["ge_compatible"] is True
    assert check_ge_compatibility("slh-dsa-simple")["ge_compatible"] is True
    assert check_ge_compatibility("slh-dsa-full")["ge_compatible"] is True
    
    # Unknown algorithm should not be GE compatible
    assert check_ge_compatibility("unknown-alg")["ge_compatible"] is False
    assert check_ge_compatibility("")["ge_compatible"] is False
    
    print("✓ GE compatibility test passed")


def test_ge_countermeasures():
    """Test that correct countermeasures are reported."""
    checks = {
        "ml-kem-768": "masking",
        "ml-kem-512": "masking",
        "ml-kem-1024": "masking",
        "ml-dsa-65": "blinding",
        "ml-dsa-87": "blinding",
        "ml-dsa-44": "blinding",
        "slh-dsa-medium": "randomization",
        "slh-dsa-simple": "randomization",
        "slh-dsa-full": "randomization",
    }
    
    for algo, expected_countermeasure in checks.items():
        result = check_ge_compatibility(algo)
        assert result["countermeasure"] == expected_countermeasure, \
            f"Expected {expected_countermeasure} for {algo}, got {result['countermeasure']}"
    
    print("✓ GE countermeasures test passed")


def test_tier_definitions():
    """Test tier level constants are correctly defined."""
    assert TIER_1 == "direct"
    assert TIER_2 == "derived"
    assert TIER_LEVELS == ["direct", "derived"]
    assert len(TIER_LEVELS) == 2
    print("✓ Tier definitions test passed")


def test_ge_profile():
    """Test GE profile configuration."""
    assert GE_PROFILE["name"] == "GE-Profil"
    assert GE_PROFILE["version"] == "1.0"
    assert "NIST SP 800-153" in GE_PROFILE["nist_reference"]
    assert "TR-02102" in GE_PROFILE["nist_reference"]
    assert "ml-kem" in GE_PROFILE["supported_algorithms"]
    assert "ml-dsa" in GE_PROFILE["supported_algorithms"]
    assert "slh-dsa" in GE_PROFILE["supported_algorithms"]
    print("✓ GE profile test passed")


def test_tier_instrumentation_direct():
    """Test 1st tier (direct) instrumentation setup."""
    result = setup_tier_instrumentation(TIER_1, "ml-kem-768", "gcc", "-O2", "x86_64")
    
    assert result["tier"] == TIER_1
    assert result["algorithm"] == "ml-kem-768"
    assert result["compiler"] == "gcc"
    assert result["flag"] == "-O2"
    assert result["arch"] == "x86_64"
    assert result["measurement_type"] == "direct"
    assert result["instrumentation"]["type"] == "cycle-accurate-timing"
    assert result["instrumentation"]["tool"] == "custom-timer"
    assert result["instrumentation"]["granularity"] == "per-instruction"
    print("✓ Direct tier instrumentation test passed")


def test_tier_instrumentation_derived():
    """Test 2nd tier (derived) instrumentation setup."""
    result = setup_tier_instrumentation(TIER_2, "ml-dsa-65", "clang", "-O1", "aarch64")
    
    assert result["tier"] == TIER_2
    assert result["algorithm"] == "ml-dsa-65"
    assert result["compiler"] == "clang"
    assert result["flag"] == "-O1"
    assert result["arch"] == "aarch64"
    assert result["measurement_type"] == "derived"
    assert result["instrumentation"]["type"] == "entropy-based-statistical"
    assert result["instrumentation"]["tool"] == "dudect"
    assert result["instrumentation"]["confidence"] == 0.95
    print("✓ Derived tier instrumentation test passed")


def test_run_tier_analysis_tier1():
    """Test running tier-1 analysis."""
    result = run_tier_analysis(TIER_1, "ml-kem-768", "gcc", "-O0", "x86_64")
    
    assert result["tier"] == TIER_1
    assert result["algorithm"] == "ml-kem-768"
    assert result["ge_compatible"] is True
    assert result["countermeasure"] == "masking"
    assert result["status"] == "instrumentation_configured"
    print("✓ Tier 1 analysis test passed")


def test_run_tier_analysis_tier2():
    """Test running tier-2 analysis."""
    result = run_tier_analysis(TIER_2, "ml-dsa-65", "clang", "-O1", "aarch64")
    
    assert result["tier"] == TIER_2
    assert result["algorithm"] == "ml-dsa-65"
    assert result["ge_compatible"] is True
    assert result["countermeasure"] == "blinding"
    assert result["status"] == "instrumentation_configured"
    print("✓ Tier 2 analysis test passed")


def test_separate_tiers_basic():
    """Test basic tier separation logic."""
    results = [
        {"tier": TIER_1, "ge_compatible": True, "status": "instrumentation_configured"},
        {"tier": TIER_2, "ge_compatible": True, "status": "instrumentation_configured"},
        {"tier": TIER_1, "ge_compatible": False, "status": "instrumentation_configured"},
        {"tier": TIER_2, "ge_compatible": False, "status": "instrumentation_configured"},
    ]
    
    separated = separate_tiers(results)
    
    # Tier 1 should accept GE compatible results and instrumentation_configured
    assert len(separated["tier_1_direct"]) == 2  # first and third results
    # Tier 2 should only accept GE compatible results
    assert len(separated["tier_2_derived"]) == 1  # only the second result
    # One result should be GE filtered out (fourth: tier_2 but ge_compatible=False)
    
    summary = separated["separation_summary"]
    assert summary["tier_1_count"] == 2
    assert summary["tier_2_count"] == 1
    # Fourth result: tier=TIER_2, ge_compatible=False -> filtered out
    assert summary["ge_filtered_out"] == 1
    
    print("✓ Tier separation test passed")


def test_separate_tiers_all_ge_compatible():
    """Test tier separation when all results are GE compatible."""
    results = [
        {"tier": TIER_1, "ge_compatible": True, "status": "instrumentation_configured"},
        {"tier": TIER_2, "ge_compatible": True, "status": "instrumentation_configured"},
    ]
    
    separated = separate_tiers(results)
    
    assert len(separated["tier_1_direct"]) == 1
    assert len(separated["tier_2_derived"]) == 1
    assert separated["separation_summary"]["ge_filtered_out"] == 0
    
    print("✓ Tier separation all GE compatible test passed")


def test_generate_side_channel_bom():
    """Test BOM generation for side-channel analyzer."""
    bom = generate_side_channel_bom("ml-kem-768")
    
    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.6"
    assert len(bom["components"]) == 1
    
    comp = bom["components"][0]
    assert comp["type"] == "library"
    assert comp["name"] == "side-channel-analyzer-ml-kem-768"
    # Properties: [0]=algorithm, [1]=ge_compatible, [2]=countermeasure, [3]=profile, [4]=tier_support
    assert "ge_compatible" in {p["name"] for p in comp["properties"]}
    assert "countermeasure" in {p["name"] for p in comp["properties"]}
    assert "profile" in {p["name"] for p in comp["properties"]}
    assert "tier_support" in {p["name"] for p in comp["properties"]}
    
    # Check metadata
    assert len(bom["metadata"]) == 1
    assert bom["metadata"][0]["component"]["type"] == "application"
    assert bom["metadata"][0]["component"]["name"] == "pqc-bench-side-channel"
    
    print("✓ Side channel BOM generation test passed")


def test_generate_side_channel_bom_various_algos():
    """Test BOM generation for various algorithms."""
    for algo in ["ml-kem-512", "ml-dsa-65", "slh-dsa-medium"]:
        bom = generate_side_channel_bom(algo)
        assert bom["bomFormat"] == "CycloneDX"
        assert len(bom["components"]) == 1
        comp_name = bom["components"][0]["name"]
        assert algo in comp_name
    
    print("✓ BOM generation for various algorithms test passed")


def test_run_compiler_matrix_tiers():
    """Test compiler matrix tier analysis."""
    # Each cell is analyzed once (using first flag and first arch)
    matrix_cells = [
        {"cc": "gcc", "cflags": ["-O0", "-O1"], "arch": ["x86_64"]},
        {"cc": "clang", "cflags": ["-O2"], "arch": ["aarch64"]},
    ]
    
    result = run_compiler_matrix_tiers("ml-kem-768", matrix_cells)
    
    # 2 cells analyzed (using first flag and first arch from each)
    assert result["algorithm"] == "ml-kem-768"
    assert result["cells_analyzed"] == 2  # 2 cells
    assert len(result["results"]) == 2
    
    # Each result should have matrix_cell, tier_1, and tier_2_summary
    for r in result["results"]:
        assert "matrix_cell" in r
        assert "tier_1" in r
        assert "tier_2_summary" in r
        assert "tier" in r["tier_1"]
    
    print("✓ Compiler matrix tier analysis test passed")


def test_run_compiler_matrix_tiers_empty():
    """Test compiler matrix with empty cells."""
    result = run_compiler_matrix_tiers("ml-kem-768", [])
    
    assert result["algorithm"] == "ml-kem-768"
    assert result["cells_analyzed"] == 0
    assert len(result["results"]) == 0
    
    print("✓ Empty compiler matrix test passed")


def test_export_tier_report():
    """Test tier report export."""
    from pqc_bench.constant_time.ws_c1_side_channel import export_tier_report
    
    results = {
        "algorithm": "ml-kem-768",
        "cells_analyzed": 3,
        "results": [
            {
                "matrix_cell": "gcc -O0 x86_64",
                "tier_1": {"tier": TIER_1, "ge_compatible": True},
                "tier_2_summary": {"tier_1_count": 1, "tier_2_count": 0, "ge_filtered_out": 0},
            }
        ],
    }
    
    report_path = export_tier_report(results, Path("artifacts/test_tier_report.json"))
    
    assert report_path.exists()
    
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    assert report["algorithm"] == "ml-kem-768"
    assert report["cells_analyzed"] == 3
    assert "generated_at" in report
    
    # Clean up
    report_path.unlink(missing_ok=True)
    
    print("✓ Tier report export test passed")


if __name__ == "__main__":
    print("Running WS-C.1 unit tests...")
    print("=" * 60)
    
    test_ge_compatibility()
    test_ge_countermeasures()
    test_tier_definitions()
    test_ge_profile()
    test_tier_instrumentation_direct()
    test_tier_instrumentation_derived()
    test_run_tier_analysis_tier1()
    test_run_tier_analysis_tier2()
    test_separate_tiers_basic()
    test_separate_tiers_all_ge_compatible()
    test_generate_side_channel_bom()
    test_generate_side_channel_bom_various_algos()
    test_run_compiler_matrix_tiers()
    test_run_compiler_matrix_tiers_empty()
    test_export_tier_report()
    
    print("=" * 60)
    print("All WS-C.1 tests passed!")
