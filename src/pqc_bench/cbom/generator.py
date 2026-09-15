"""CycloneDX 1.6 Cryptographic Bill of Materials (CBOM) generator.

Generates a CycloneDX 1.6 SBOM (Software Bill of Materials) focusing on
cryptographic assets including PQC (Post-Quantum Cryptography) primitives:
ML-KEM, ML-DSA, SLH-DSA, and hybrid configurations.

The output follows the CycloneDX 1.6 specification with proper component
identification, version tracking, and relationship mapping.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# CycloneDX 1.6 namespace
CYCLONEDX_NS = "http://cyclonedx.org/schema/bom/1.6"

# PQC algorithm identifiers following NIST and IANA conventions
PQC_ALGORITHMS = {
    "ml-kem-512": {
        "name": "ML-KEM-512",
        "type": "pkc",
        "family": "kem",
        "description": "NIST FIPS 203 KeM-512 (formerly Kyber-512)",
        "nist_ref": "FIPS-203",
    },
    "ml-kem-768": {
        "name": "ML-KEM-768",
        "type": "pkc",
        "family": "kem",
        "description": "NIST FIPS 203 KeM-768 (formerly Kyber-768)",
        "nist_ref": "FIPS-203",
    },
    "ml-kem-1024": {
        "name": "ML-KEM-1024",
        "type": "pkc",
        "family": "kem",
        "description": "NIST FIPS 203 KeM-1024 (formerly Kyber-1024)",
        "nist_ref": "FIPS-203",
    },
    "ml-dsa-44": {
        "name": "ML-DSA-44",
        "type": "pkc",
        "family": "dsa",
        "description": "NIST FIPS 204 ML-DSA-44 (formerly Dilithium-2)",
        "nist_ref": "FIPS-204",
    },
    "ml-dsa-65": {
        "name": "ML-DSA-65",
        "type": "pkc",
        "family": "dsa",
        "description": "NIST FIPS 204 ML-DSA-65 (formerly Dilithium-3)",
        "nist_ref": "FIPS-204",
    },
    "ml-dsa-87": {
        "name": "ML-DSA-87",
        "type": "pkc",
        "family": "dsa",
        "description": "NIST FIPS 204 ML-DSA-87 (formerly Dilithium-5)",
        "nist_ref": "FIPS-204",
    },
    "slh-dsa-simple": {
        "name": "SLH-DSA-Simple",
        "type": "pqc",
        "family": "hashbased",
        "description": "NIST FIPS 205 SLH-DSA-Simple (formerly SPHINCS+ Simple)",
        "nist_ref": "FIPS-205",
    },
    "slh-dsa-medium": {
        "name": "SLH-DSA-Medium",
        "type": "pqc",
        "family": "hashbased",
        "description": "NIST FIPS 205 SLH-DSA-Medium (formerly SPHINCS+ Medium)",
        "nist_ref": "FIPS-205",
    },
    "slh-dsa-full": {
        "name": "SLH-DSA-Full",
        "type": "pqc",
        "family": "hashbased",
        "description": "NIST FIPS 205 SLH-DSA-Full (formerly SPHINCS+ Full)",
        "nist_ref": "FIPS-205",
    },
}


def detect_pqc_components(
    scan_path: Path | str,
    include_hybrids: bool = True,
) -> dict[str, Any]:
    """Scan a directory for PQC-related files and detect algorithm usage.

    Args:
        scan_path: Root directory to scan for PQC references.
        include_hybrids: Whether to detect hybrid PQC configurations.

    Returns:
        Dictionary mapping detected algorithm names to component info.
    """
    scan_path = Path(scan_path)
    if not scan_path.exists():
        return {}

    detected: dict[str, Any] = {}

    # Scan for Python files with PQC references
    for py_file in scan_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace").lower()
        except (OSError, UnicodeDecodeError):
            continue

        # Detect ML-KEM references
        for algo_key, algo_info in PQC_ALGORITHMS.items():
            if algo_info["family"] == "kem" and algo_key in content:
                if algo_key not in detected:
                    detected[algo_key] = {
                        "name": algo_info["name"],
                        "type": algo_info["type"],
                        "family": algo_info["family"],
                        "files": [],
                        "nist_ref": algo_info["nist_ref"],
                        "description": algo_info["description"],
                    }
                detected[algo_key]["files"].append(
                    {"path": str(py_file), "relative": str(py_file.relative_to(scan_path))}
                )

        # Detect ML-DSA references
        if "ml-dsa" in content or "mldsa" in content:
            # Find specific ML-DSA level
            for level in ["44", "65", "87"]:
                if f"ml-dsa-{level}" in content.lower() or f"mldsa-{level}" in content.lower():
                    key = f"ml-dsa-{level}"
                    if key not in detected:
                        detected[key] = {
                            "name": PQC_ALGORITHMS[key]["name"],
                            "type": PQC_ALGORITHMS[key]["type"],
                            "family": PQC_ALGORITHMS[key]["family"],
                            "files": [],
                            "nist_ref": PQC_ALGORITHMS[key]["nist_ref"],
                            "description": PQC_ALGORITHMS[key]["description"],
                        }
                    detected[key]["files"].append(
                        {"path": str(py_file), "relative": str(py_file.relative_to(scan_path))}
                    )
                break  # Only match first level found

        # Detect SLH-DSA references
        if "slh-dsa" in content or "slhdsa" in content:
            for level in ["simple", "medium", "full"]:
                key = f"slh-dsa-{level}"
                if key not in detected:
                    detected[key] = {
                        "name": PQC_ALGORITHMS[key]["name"],
                        "type": PQC_ALGORITHMS[key]["type"],
                        "family": PQC_ALGORITHMS[key]["family"],
                        "files": [],
                        "nist_ref": PQC_ALGORITHMS[key]["nist_ref"],
                        "description": PQC_ALGORITHMS[key]["description"],
                    }
                detected[key]["files"].append(
                    {"path": str(py_file), "relative": str(py_file.relative_to(scan_path))}
                )

        # Detect hybrid configurations
        if include_hybrids:
            if any(
                term in content
                for term in ["hybrid", "combined", "parallel", "dual"]
            ):
                # Check for specific hybrid combos
                hybrid_key = _detect_hybrid(content)
                if hybrid_key and hybrid_key not in detected:
                    detected[hybrid_key] = {
                        "name": hybrid_key.replace("_", " ").title(),
                        "type": "pqc",
                        "family": "hybrid",
                        "files": [],
                        "description": f"Hybrid PQC configuration: {hybrid_key.replace('_', ' ')}",
                    }
                detected[hybrid_key]["files"].append(
                    {"path": str(py_file), "relative": str(py_file.relative_to(scan_path))}
                )

    return detected


def _detect_hybrid(content: str) -> str | None:
    """Detect hybrid PQC configuration from file content.

    Returns a key representing the hybrid combination, or None if not found.
    """
    # Common hybrid patterns
    hybrids = {
        "ml-kem-768_ml-dsa-65": ["ml-kem-768", "ml-dsa-65"],
        "ml-kem-512_ml-dsa-44": ["ml-kem-512", "ml-dsa-44"],
        "ml-kem-1024_ml-dsa-87": ["ml-kem-1024", "ml-dsa-87"],
        "ml-dsa-65_slh-dsa-simple": ["ml-dsa-65", "slh-dsa-simple"],
        "ml-kem-768_slh-dsa-medium": ["ml-kem-768", "slh-dsa-medium"],
    }

    for key, terms in hybrids.items():
        if all(term in content for term in terms):
            return key
    return None


def generate_cyclonedx_bom(
    scan_path: Path | str,
    component_name: str = "pqc-bench",
    component_version: str = "1.0.0",
    include_hybrids: bool = True,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Generate a CycloneDX 1.6 Bill of Materials document.

    Args:
        scan_path: Root directory to scan for PQC components.
        component_name: Name for the top-level software component.
        component_version: Version for the top-level software component.
        include_hybrids: Whether to include hybrid PQC configurations.
        timestamp: ISO timestamp for the BOM. Defaults to now.

    Returns:
        CycloneDX 1.6 BOM dictionary ready for serialization.
    """
    scan_path = Path(scan_path)
    if not timestamp:
        timestamp = datetime.now(UTC)

    # Detect PQC components in the scanned path
    detected = detect_pqc_components(scan_path, include_hybrids=include_hybrids)

    # Build components list
    components: list[dict[str, Any]] = []

    # Add detected PQC algorithms as components
    algo_order = [
        "ml-kem-512",
        "ml-kem-768",
        "ml-kem-1024",
        "ml-dsa-44",
        "ml-dsa-65",
        "ml-dsa-87",
        "slh-dsa-simple",
        "slh-dsa-medium",
        "slh-dsa-full",
    ]

    for key in algo_order:
        if key in detected:
            comp = detected[key]
            components.append(
                {
                    "type": "library",
                    "name": comp["name"],
                    "version": component_version,
                    "publisher": "OpenCLaw PQC Bench",
                    "properties": [
                        {"name": "algorithm", "value": comp["name"]},
                        {"name": "nist_reference", "value": comp["nist_ref"]},
                        {"name": "family", "value": comp["family"]},
                        {"name": "description", "value": comp["description"]},
                    ]
                    + comp.get("properties", []),
                    "components": comp.get("files", []),
                }
            )

    # Add hybrid components if found
    if include_hybrids:
        hybrid_keys = sorted(
            k for k in detected if k not in algo_order
        )
        for key in hybrid_keys:
            comp = detected[key]
            components.append(
                {
                    "type": "library",
                    "name": comp["name"],
                    "version": component_version,
                    "publisher": "OpenCLaw PQC Bench",
                    "properties": [
                        {"name": "algorithm", "value": comp["name"]},
                        {"name": "family", "value": comp["family"]},
                        {"name": "description", "value": comp["description"]},
                    ]
                    + comp.get("properties", []),
                    "components": comp.get("files", []),
                }
            )

    # If no PQC components detected, add a placeholder
    if not components:
        components.append(
            {
                "type": "library",
                "name": "No PQC components detected",
                "version": component_version,
                "publisher": "OpenCLaw PQC Bench",
                "properties": [
                    {"name": "note", "value": "No recognized PQC algorithms found in scan path"}
                ],
            }
        )

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "components": components,
        "metadata": [
            {
                "component": {
                    "type": "application",
                    "name": component_name,
                    "version": component_version,
                }
            }
        ],
    }

    return bom


def write_bom(
    bom: dict[str, Any],
    output_path: Path | str,
    pretty: bool = True,
) -> Path:
    """Write a CycloneDX BOM to a JSON file.

    Args:
        bom: BOM dictionary as generated by generate_cyclonedx_bom.
        output_path: Path where the BOM JSON will be written.
        pretty: Whether to pretty-print the JSON output.

    Returns:
        Path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    json_content = json.dumps(bom, indent=2 if pretty else None, ensure_ascii=False)
    output_path.write_text(json_content, encoding="utf-8")

    return output_path


def main(
    scan_path: str = ".",
    output_path: str = "artifacts/cbom.json",
    component_name: str = "pqc-bench",
    component_version: str = "1.0.0",
    include_hybrids: bool = True,
) -> int:
    """Main entry point for CBOM generation.

    Scans the given path for PQC components and generates a CycloneDX 1.6
    bill of materials.

    Args:
        scan_path: Path to scan for PQC references (default: current directory).
        output_path: Output file path for the BOM JSON.
        component_name: Name for the top-level software component.
        component_version: Version for the top-level software component.
        include_hybrids: Whether to include hybrid PQC configurations.

    Returns:
        Exit code (0 for success).
    """
    bom = generate_cyclonedx_bom(
        scan_path=scan_path,
        component_name=component_name,
        component_version=component_version,
        include_hybrids=include_hybrids,
    )

    written_path = write_bom(bom, output_path)
    print(f"CycloneDX 1.6 CBOM written to: {written_path}")

    # Print summary
    print(f"\nScanned path: {scan_path}")
    print(f"Total components found: {len(bom['components'])}")

    for comp in bom["components"]:
        comp_name = comp.get("name", "unknown")
        comp_type = comp.get("type", "unknown")
        print(f"  - {comp_name} ({comp_type})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())