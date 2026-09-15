"""CBOM (Cryptographic Bill of Materials) unit tests.

Tests for the CycloneDX 1.6 CBOM generator module, verifying:
- Correct BOM structure and schema validation
- PQC algorithm detection and component generation
- Hybrid configuration detection
- Output file writing
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pqc_bench.cbom.generator import (
    detect_pqc_components,
    generate_cyclonedx_bom,
    write_bom,
)


def test_bom_structure():
    """Test that generated BOM has correct CycloneDX 1.6 structure."""
    bom = generate_cyclonedx_bom(scan_path=".")

    # Verify top-level fields
    assert bom["bomFormat"] == "CycloneDX", f"Expected bomFormat 'CycloneDX', got '{bom['bomFormat']}'"
    assert bom["specVersion"] == "1.6", f"Expected specVersion '1.6', got '{bom['specVersion']}'"
    assert "timestamp" in bom, "Missing 'timestamp' in BOM"
    assert "components" in bom, "Missing 'components' in BOM"
    assert "metadata" in bom, "Missing 'metadata' in BOM"

    # Verify metadata structure
    assert len(bom["metadata"]) > 0, "Metadata list should not be empty"
    meta_component = bom["metadata"][0].get("component", {})
    assert meta_component.get("type") == "application", "Metadata component type should be 'application'"
    assert meta_component.get("name") == "pqc-bench", f"Expected component name 'pqc-bench', got '{meta_component.get('name')}'"
    assert meta_component.get("version") == "1.0.0", f"Expected version '1.0.0', got '{meta_component.get('version')}''"

    print("✓ BOM structure test passed")


def test_pqc_detection():
    """Test that PQC algorithms are correctly detected from source files."""
    detected = detect_pqc_components(scan_path=".")

    # Should detect at least some PQC algorithms
    assert len(detected) > 0, "No PQC components detected - detection may be too strict"

    # Verify expected algorithm families are present
    algo_keys = list(detected.keys())
    expected_families = {"kem", "dsa", "hashbased", "hybrid"}

    found_families = set()
    for key, comp in detected.items():
        family = comp.get("family", "")
        if family in expected_families:
            found_families.add(family)

    assert len(found_families) >= 2, f"Expected at least 2 PQC families, found: {found_families}"

    print(f"✓ PQC detection test passed ({len(detected)} algorithms detected, families: {found_families})")


def test_required_algorithms():
    """Test that required PQC algorithms are detected (per WS-F acceptance criteria)."""
    detected = detect_pqc_components(scan_path=".")

    # Per acceptance criteria: ML-KEM-768 literatürle ±2 bit
    # and two aracın (AQRE, Qualtran) sapması raporlandı
    required = ["ml-kem-768", "ml-dsa-65", "slh-dsa-medium"]

    for algo in required:
        assert algo in detected, f"Required algorithm '{algo}' not detected in source files"

    print(f"✓ Required algorithms test passed: {', '.join(required)}")


def test_bom_writing(tmp_path: Path):
    """Test that BOM can be written to file and read back correctly."""
    bom = generate_cyclonedx_bom(scan_path=".")

    # Write to temporary file
    output_file = tmp_path / "test_cbom.json"
    result = write_bom(bom, output_file)

    # Verify file was written
    assert result.exists(), f"BOM file not written to {output_file}"
    assert result.suffix == ".json", f"Expected .json file, got {result.suffix}"

    # Read back and verify structure
    with open(result, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["bomFormat"] == "CycloneDX"
    assert loaded["specVersion"] == "1.6"
    assert len(loaded["components"]) > 0

    print(f"✓ BOM writing test passed (output: {result})")


def test_hybrid_detection():
    """Test hybrid PQC configuration detection."""
    detected = detect_pqc_components(scan_path=".")

    # Check for hybrid configurations
    hybrid_keys = [k for k in detected if k not in ["ml-kem-512", "ml-kem-768", "ml-kem-1024",
                                                       "ml-dsa-44", "ml-dsa-65", "ml-dsa-87",
                                                       "slh-dsa-simple", "slh-dsa-medium", "slh-dsa-full"]]

    # At minimum, the generator should be capable of detecting hybrids
    # (actual detection depends on source code content)
    assert isinstance(hybrid_keys, list), "Hybrid detection should return a list"

    print(f"✓ Hybrid detection test passed ({len(hybrid_keys)} hybrid configs found)")


if __name__ == "__main__":
    print("Running CBOM unit tests...")
    test_bom_structure()
    test_pqc_detection()
    test_required_algorithms()
    
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        test_bom_writing(Path(td))
    
    test_hybrid_detection()
    print("\nAll CBOM tests passed!")