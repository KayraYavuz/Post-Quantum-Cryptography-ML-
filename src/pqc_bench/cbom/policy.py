"""Cryptographic policy evaluator for NIST SP 800-208 / CNSA 2.0 compliance.

Evaluates cryptographic policies against NIST SP 800-208 and CNSA 2.0
requirements, providing compliance status and recommendations for PQC
algorithm transitions.

This module works in conjunction with the CBOM generator (generator.py) to
provide a complete CBOM-to-policy pipeline.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# CycloneDX 1.6 namespace
CYCLONEDX_NS = "http://cyclonedx.org/schema/bom/1.6"

# CNSA 2.0 (Commitment Level 2) algorithm requirements
# Source: NIST SP 800-208 and CNSA 2.0 guidelines
CNSA_2_0_REQUIREMENTS = {
    "tl_tls": {
        "ka": ["ml-kem-768", "ml-kem-1024"],  # Key agreement algorithms
        "kdf": ["ml-kem-768", "ml-kem-1024"],
        "signature": ["ml-dsa-65", "ml-dsa-87"],  # Signature algorithms
    },
    "tls13": {
        "ka": ["ml-kem-768", "ml-kem-1024"],
        "kdf": ["ml-kem-768", "ml-kem-1024"],
        "signature": ["ml-dsa-65", "ml-dsa-87"],
    },
    "ipsec": {
        "ka": ["ml-kem-768", "ml-kem-1024"],
        "signature": ["ml-dsa-65", "ml-dsa-87"],
    },
    "ssh": {
        "ka": ["ml-kem-768", "ml-kem-1024"],
        "signature": ["ml-dsa-65", "ml-dsa-87"],
    },
}

# NIST SP 800-208 legacy/recommended algorithms
NIST_SP_800_208 = {
    "legacy": ["rsa-2048", "ecdsa-p256", "ecdsa-p384"],
    "transitional": ["ml-kem-512", "ml-dsa-44", "slh-dsa-simple"],
    "recommended": ["ml-kem-768", "ml-kem-1024", "ml-dsa-65", "ml-dsa-87",
                    "slh-dsa-medium", "slh-dsa-full"],
}


def evaluate_cnsA_2_0_compliance(
    bom_path: Path | str,
    cNSA_level: str = "2",
) -> dict[str, Any]:
    """Evaluate a CycloneDX BOM against CNSA 2.0 compliance requirements.

    Args:
        bom_path: Path to the CycloneDX 1.6 BOM JSON file.
        cNSA_level: CNSA compliance level ("1" or "2"). Default: "2".

    Returns:
        Dictionary with compliance evaluation results.
    """
    bom_path = Path(bom_path)
    if not bom_path.exists():
        raise FileNotFoundError(f"BOM file not found: {bom_path}")

    with open(bom_path, "r", encoding="utf-8") as f:
        bom = json.load(f)

    components = bom.get("components", [])
    timestamp = bom.get("timestamp", "")

    # Extract algorithm names from BOM components
    detected_algorithms: set[str] = set()
    for comp in components:
        comp_name = comp.get("name", "").lower()
        for prop in comp.get("properties", []):
            if prop.get("name") == "algorithm":
                detected_algorithms.add(prop.get("value", "").lower())

    # CNSA 2.0 evaluation
    cNSA_req = CNSA_2_0_REQUIREMENTS.get(f"tl_tls", CNSA_2_0_REQUIREMENTS["tl_tls"])

    compliance = {
        "cNSA_level": cNSA_level,
        "timestamp": timestamp,
        "overall_status": "non-compliant",
        "ka_compliant": False,
        "signature_compliant": False,
        "missing_ka": [],
        "missing_signature": [],
        "recommendations": [],
    }

    # Check key agreement algorithms
    required_ka = cNSA_req["ka"]
    found_ka = detected_algorithms.intersection(
        {algo.lower() for algo in required_ka}
    )
    compliance["ka_compliant"] = len(found_ka) > 0
    compliance["missing_ka"] = [
        algo for algo in required_ka if algo.lower() not in detected_algorithms
    ]

    # Check signature algorithms
    required_sig = cNSA_req["signature"]
    found_sig = detected_algorithms.intersection(
        {algo.lower() for algo in required_sig}
    )
    compliance["signature_compliant"] = len(found_sig) > 0
    compliance["missing_signature"] = [
        algo for algo in required_sig if algo.lower() not in detected_algorithms
    ]

    # Determine overall status
    if compliance["ka_compliant"] and compliance["signature_compliant"]:
        compliance["overall_status"] = "compliant"
    elif len(found_ka) > 0 or len(found_sig) > 0:
        compliance["overall_status"] = "partial"
    else:
        compliance["overall_status"] = "non-compliant"

    # Generate recommendations
    if not compliance["ka_compliant"]:
        compliance["recommendations"].append(
            f"Add CNSA 2.0 compliant key agreement algorithm(s): "
            f"{', '.join(required_ka)}"
        )
    if not compliance["signature_compliant"]:
        compliance["recommendations"].append(
            f"Add CNSA 2.0 compliant signature algorithm(s): "
            f"{', '.join(required_sig)}"
        )

    # Check for legacy algorithms that should be phased out
    legacy_patterns = ["rsa-2048", "ecdsa-p256", "ecdsa-p384"]
    found_legacy = detected_algorithms.intersection(set(legacy_patterns))
    if found_legacy:
        compliance["recommendations"].append(
            f"Consider phasing out legacy algorithms: {', '.join(found_legacy)}. "
            "These do not meet CNSA 2.0 requirements."
        )

    return compliance


def evaluate_nist_sp_800_208(
    bom_path: Path | str,
) -> dict[str, Any]:
    """Evaluate a CycloneDX BOM against NIST SP 800-208 requirements.

    Args:
        bom_path: Path to the CycloneDX 1.6 BOM JSON file.

    Returns:
        Dictionary with NIST SP 800-208 evaluation results.
    """
    bom_path = Path(bom_path)
    if not bom_path.exists():
        raise FileNotFoundError(f"BOM file not found: {bom_path}")

    with open(bom_path, "r", encoding="utf-8") as f:
        bom = json.load(f)

    components = bom.get("components", [])

    # Extract algorithm names from BOM components
    detected_algorithms: set[str] = set()
    for comp in components:
        comp_name = comp.get("name", "").lower()
        for prop in comp.get("properties", []):
            if prop.get("name") == "algorithm":
                detected_algorithms.add(prop.get("value", "").lower())

    evaluation = {
        "overall_status": "unknown",
        "legacy_algorithms": list(
            detected_algorithms.intersection(
                {a.lower() for a in NIST_SP_800_208["legacy"]}
            )
        ),
        "transitional_algorithms": list(
            detected_algorithms.intersection(
                {a.lower() for a in NIST_SP_800_208["transitional"]}
            )
        ),
        "recommended_algorithms": list(
            detected_algorithms.intersection(
                {a.lower() for a in NIST_SP_800_208["recommended"]}
            )
        ),
        "missing_recommended": [],
        "unclassified_algorithms": [],
        "recommendations": [],
    }

    # Find algorithms not in any category
    all_pqc = {
        "ml-kem-512", "ml-kem-768", "ml-kem-1024",
        "ml-dsa-44", "ml-dsa-65", "ml-dsa-87",
        "slh-dsa-simple", "slh-dsa-medium", "slh-dsa-full",
    }
    unclassified = detected_algorithms - all_pqc
    if unclassified:
        evaluation["unclassified_algorithms"] = list(unclassified)

    # Check for recommended algorithms
    recommended = NIST_SP_800_208["recommended"]
    found_recommended = detected_algorithms.intersection({a.lower() for a in recommended})
    evaluation["missing_recommended"] = [
        algo for algo in recommended if algo.lower() not in detected_algorithms
    ]

    # Determine overall status
    if len(found_recommended) >= 3:  # At least 3 recommended algorithms present
        evaluation["overall_status"] = "compliant"
    elif len(found_recommended) >= 1:
        evaluation["overall_status"] = "partial"
    elif len(evaluation["transitional_algorithms"]) > 0:
        evaluation["overall_status"] = "transitional"
    else:
        evaluation["overall_status"] = "non-compliant"

    # Generate recommendations
    if evaluation["missing_recommended"]:
        eval_recs = evaluation["missing_recommended"]
        evaluation["recommendations"].append(
            f"Add recommended NIST SP 800-208 algorithms: "
            f"{', '.join(eval_recs)}"
        )

    if evaluation["legacy_algorithms"]:
        eval_recs = evaluation["legacy_algorithms"]
        evaluation["recommendations"].append(
            f"Phase out legacy NIST SP 800-208 algorithms: {', '.join(eval_recs)}. "
            "These are deprecated and should be replaced with recommended algorithms."
        )

    if not evaluation["recommended_algorithms"] and not evaluation["legacy_algorithms"]:
        evaluation["recommendations"].append(
            "No recognized PQC algorithms found. Consider adding PQC algorithms "
            "per NIST SP 800-208."
        )

    return evaluation


def generate_policy_report(
    bom_path: Path | str,
    cNSA_level: str = "2",
    output_path: Path | str = "artifacts/cbom_policy_report.json",
) -> Path:
    """Generate a comprehensive policy compliance report from a CBOM.

    Args:
        bom_path: Path to the CycloneDX 1.6 BOM JSON file.
        cNSA_level: CNSA compliance level ("1" or "2"). Default: "2".
        output_path: Path where the policy report will be written.

    Returns:
        Path to the written policy report file.
    """
    cNSA_compliance = evaluate_cnsA_2_0_compliance(bom_path, cNSA_level=cNSA_level)
    nist_sp_800_208_eval = evaluate_nist_sp_800_208(bom_path)

    report = {
        "bom_evaluation": {
            "cNSA_2_0": cNSA_compliance,
            "nist_sp_800_208": nist_sp_800_208_eval,
        },
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return output_path


def main(
    bom_path: str = "artifacts/cbom.json",
    cNSA_level: str = "2",
    output_path: str = "artifacts/cbom_policy_report.json",
) -> int:
    """Main entry point for policy evaluation.

    Evaluates a CBOM against NIST SP 800-208 and CNSA 2.0 requirements
    and generates a compliance report.

    Args:
        bom_path: Path to the CBOM JSON file.
        cNSA_level: CNSA compliance level ("1" or "2").
        output_path: Path for the policy report output.

    Returns:
        Exit code (0 for success).
    """
    print(f"Evaluating CBOM: {bom_path}")

    # Generate CNSA 2.0 compliance evaluation
    cNSA_result = evaluate_cnsA_2_0_compliance(bom_path, cNSA_level=cNSA_level)
    print(f"\nCNSA 2.0 Level {cNSA_level} Compliance:")
    print(f"  Overall status: {cNSA_result['overall_status']}")
    if cNSA_result["ka_compliant"]:
        print("  Key agreement: Compliant")
    else:
        print(f"  Key agreement: Non-compliant (missing: {', '.join(cNSA_result['missing_ka'])})")
    if cNSA_result["signature_compliant"]:
        print("  Signature: Compliant")
    else:
        print(f"  Signature: Non-compliant (missing: {', '.join(cNSA_result['missing_signature'])})")

    # Generate NIST SP 800-208 evaluation
    nist_result = evaluate_nist_sp_800_208(bom_path)
    print(f"\nNIST SP 800-208 Evaluation:")
    print(f"  Overall status: {nist_result['overall_status']}")
    if nist_result["recommended_algorithms"]:
        print(f"  Found recommended algorithms: {', '.join(nist_result['recommended_algorithms'])}")
    if nist_result["missing_recommended"]:
        print(f"  Missing recommended: {', '.join(nist_result['missing_recommended'])}")
    if nist_result["legacy_algorithms"]:
        print(f"  Legacy algorithms: {', '.join(nist_result['legacy_algorithms'])}")

    # Generate combined report
    report_path = generate_policy_report(bom_path, cNSA_level=cNSA_level, output_path=output_path)
    print(f"\nPolicy report written to: {report_path}")

    # Print all recommendations
    all_recs = []
    all_recs.extend(cNSA_result.get("recommendations", []))
    all_recs.extend(nist_result.get("recommendations", []))

    if all_recs:
        print("\nRecommendations:")
        for i, rec in enumerate(all_recs, 1):
            print(f"  {i}. {rec}")
    else:
        print("\nNo recommendations - all requirements met!")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())