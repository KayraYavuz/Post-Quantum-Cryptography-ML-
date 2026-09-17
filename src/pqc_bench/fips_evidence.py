"""Bounded offline document assertions, never FIPS module validation.

Public entry points accept plain dictionaries (or load_request JSON). No files,
URLs, modules or certificates are opened; references are caller-supplied text.
"""
from __future__ import annotations

import html
import json
import unicodedata
from typing import Any

SOURCES = {
    "fips140_3": "https://csrc.nist.gov/pubs/fips/140-3/final",
    "cmvp_modules": (
        "https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules"
    ),
    "cmvp_faq": "https://csrc.nist.gov/projects/cryptographic-module-validation-program/faqs",
}
FIELDS = (
    "module_id", "version", "environment", "certificate_reference",
    "certificate_standard", "certificate_status", "security_policy_reference",
    "approved_mode", "services",
)
TARGET_FIELDS = ("module_id", "version", "environment", "approved_mode", "services")
LIMITATIONS = (
    "Local caller-supplied document assertions only; not a module validation or certification.",
    "Document authenticity, current CMVP status and deployed runtime mode are not verified.",
    "Algorithm names, FIPS 203/204, cryptography and CBOM policy labels are not module evidence.",
    "Exact scope comparison only; no environment equivalence, portability or product-wide claim.",
    "Not an exhaustive FIPS 140-3 requirements audit; no laboratory or service integration.",
)


def _object(value: Any, allowed: set[str], required: set[str], label: str) -> dict:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a plain object")
    if any(type(key) is not str for key in value):
        raise ValueError(f"{label} keys must be strings")
    if set(value) - allowed or required - set(value):
        raise ValueError(f"{label} has unknown or missing keys")
    return value


def _text(value: Any, label: str) -> str:
    if (type(value) is not str or not 1 <= len(value) <= 512
            or value != value.strip()
            or any(unicodedata.category(c).startswith("C") for c in value)):
        raise ValueError(f"{label} must be 1..512 trimmed printable characters")
    return value


def _value(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field == "services":
        if type(value) is not list or not 1 <= len(value) <= 32:
            raise ValueError("services must be a nonempty list of at most 32 strings or null")
        items = [_text(item, field) for item in value]
        if len(set(items)) != len(items):
            raise ValueError("duplicate services")
        return sorted(items)
    value = _text(value, field)
    enums = {
        "certificate_standard": {"FIPS 140-3", "FIPS 140-2", "unknown"},
        "certificate_status": {"active", "historical", "revoked", "unknown"},
    }
    if field in enums and value not in enums[field]:
        raise ValueError(f"invalid {field}")
    return value


def _normalize(request: Any) -> tuple[dict, list[dict]]:
    request = _object(request, {"target", "documents"}, {"target", "documents"}, "request")
    target = _object(request["target"], set(TARGET_FIELDS), {"module_id"}, "target")
    target = {field: _value(field, target.get(field)) for field in TARGET_FIELDS}
    if target["module_id"] is None:
        raise ValueError("target module_id is required")
    documents = request["documents"]
    if type(documents) is not list or len(documents) > 64:
        raise ValueError("documents must be a list of at most 64 objects")
    normalized = []
    ids: set[str] = set()
    for document in documents:
        document = _object(document, {*FIELDS, "document_id", "locator"},
                           {"document_id", "locator"}, "document")
        doc_id = _text(document["document_id"], "document_id")
        if doc_id in ids:
            raise ValueError("duplicate document_id")
        ids.add(doc_id)
        normalized.append({
            "document_id": doc_id,
            "locator": _text(document["locator"], "locator"),
            **{field: _value(field, document.get(field)) for field in FIELDS},
        })
    return target, sorted(normalized, key=lambda doc: doc["document_id"])


def load_request(text: str) -> dict:
    """Parse bounded JSON, rejecting duplicate keys, nonfinite values and extra fields."""
    if type(text) is not str or len(text) > 262144:
        raise ValueError("JSON must be a string of at most 262144 characters")

    def pairs(items: list) -> dict:
        result: dict = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"nonfinite JSON constant: {value}")

    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid JSON request") from exc
    _normalize(data)
    return data


def build_matrix(request: dict) -> dict:
    """Review one intended module against up to 64 local document assertions.

    Every supplied assertion is unverified. unknown means no usable assertion;
    not_verified means assertions exist, NOT that they are valid. Gap codes
    distinguish absence, conflicting documents and target-scope mismatches.
    Certificate status and standard are document assertions, never live facts.
    """
    target, documents = _normalize(request)
    rows = []
    gaps: set[tuple[str, str]] = set()
    for field in FIELDS:
        evidence = [{"document_id": doc["document_id"], "locator": doc["locator"],
                     "value": doc[field]} for doc in documents if doc[field] is not None]
        usable = [entry for entry in evidence if entry["value"] != "unknown"]
        codes: set[str] = set()
        if not usable:
            codes.add("missing_evidence")
        # Compare set-valued service scopes canonically, not input list order.
        values = {json.dumps(entry["value"], sort_keys=True) for entry in usable}
        if len(values) > 1:
            codes.add("conflicting_evidence")
        if field in TARGET_FIELDS:
            desired = target[field]
            if desired is None or desired == "unknown":
                codes.add("missing_target_scope")
            else:
                for entry in usable:
                    matches = (set(desired).issubset(entry["value"]) if field == "services"
                               else desired == entry["value"])
                    if not matches:
                        codes.add("target_scope_mismatch")
        if field == "certificate_standard" and any(
                entry["value"] != "FIPS 140-3" for entry in usable):
            codes.add("wrong_standard")
        if field == "certificate_status":
            for entry in usable:
                if entry["value"] in {"historical", "revoked"}:
                    codes.add("certificate_" + entry["value"])
        gaps.update((field, code) for code in codes)
        rows.append({"field": field, "target": target.get(field), "evidence": evidence,
                     "status": "not_verified" if usable else "unknown",
                     "gaps": sorted(codes),
                     "rule_sources": ["fips140_3", "cmvp_modules", "cmvp_faq"]})
    # Never silently merge fragments from unidentified or scope-less documents.
    for doc in documents:
        if any(doc[field] is not None for field in FIELDS):
            for field in ("module_id", "version", "environment", "certificate_reference"):
                if doc[field] is None or doc[field] == "unknown":
                    gaps.add((f"document:{doc['document_id']}:{field}", "unbound_document_scope"))
    gaps.add(("review", "authenticity_not_verified"))
    gaps.add(("review", "current_cmvp_status_not_verified"))
    gaps.add(("review", "runtime_mode_not_verified"))
    return {
        "schema_version": 1, "scope": "local_document_review",
        "overall_status": "not_verified", "target": target, "documents": documents,
        "rows": rows,
        "gaps": [{"field": field, "code": code} for field, code in sorted(gaps)],
        "sources": dict(SOURCES), "limitations": list(LIMITATIONS),
    }


def matrix_json(request: dict) -> str:
    """Canonical JSON with a trailing newline; no clock, randomness or I/O."""
    return json.dumps(build_matrix(request), indent=2, sort_keys=True,
                      ensure_ascii=True, allow_nan=False) + "\n"


def _cell(value: Any) -> str:
    # Encode punctuation as entities: caller strings cannot create Markdown
    # links, HTML, table cells, code spans or emphasis. Values remain readable.
    text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    return "".join(c if c.isalnum() or c == " " else f"&#{ord(c)};" for c in text)


def matrix_markdown(request: dict) -> str:
    """Deterministic escaped matrix including raw document assertions and gaps."""
    report = build_matrix(request)
    lines = ["# FIPS 140-3 local document evidence review", "",
             "**Overall: not_verified** — not module certification.", "",
             "| Field | Intended scope | Document assertions | Status | Gaps |",
             "|---|---|---|---|---|"]
    for row in report["rows"]:
        lines.append("| " + " | ".join(_cell(row[key]) for key in
                     ("field", "target", "evidence", "status", "gaps")) + " |")
    lines += ["", "## All review gaps", ""]
    lines.extend("- " + _cell(gap) for gap in report["gaps"])
    lines += ["", "## Local document assertions (not authenticated)", ""]
    lines.extend("- " + _cell(doc) for doc in report["documents"])
    lines += ["", "## Limitations", ""]
    lines.extend("- " + html.escape(line) for line in LIMITATIONS)
    lines += ["", "## Official rule sources (not certificate evidence)", ""]
    lines.extend(f"- [{key}]({url})" for key, url in sorted(SOURCES.items()))
    return "\n".join(lines) + "\n"
