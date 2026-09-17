"""Deterministic offline executive reports from bounded local output excerpts.

Pure data transformation: no file reads, URLs, templates, subprocesses or clocks.
Provenance is caller-attested; hashes bind excerpts, not underlying input files.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
import unicodedata
from typing import Any

# Fixed module identity and interpretation; callers cannot upgrade evidence scope.
SECTIONS = {
    "security": ("pqc_bench.security_estimation.lattice_runner", "Security estimate",
                 "Static lookup estimates, not a fresh lattice-estimator run or measured security.",
                 {"scheme": "text", "classical_security_bits": "number", "quantum_security_bits": "number"}),
    "quantum": ("pqc_bench.quantum_cost", "Quantum cost",
                "Placeholder resource model, not an AQRE/Qualtran run or hardware measurement.",
                {"scheme": "text", "logical_qubits": "integer", "t_gate_count": "integer", "t_depth": "integer",
                 "physical_qubits": "integer", "runtime_seconds": "number"}),
    "cbom": ("pqc_bench.cbom.policy", "CBOM policy labels",
             "Legacy heuristic policy labels, not normative NIST/CNSA compliance or certification.",
             {"cNSA_2_0_status": "policy", "nist_sp_800_208_status": "policy"}),
    "constant_time": ("pqc_bench.constant_time.binary_auditor", "Static instruction review",
                      "Findings and their absence prove neither leakage nor constant-time behavior.",
                      {"status": "scan", "finding_count": "integer", "instruction_count": "integer",
                       "scan_complete": "boolean", "findings_truncated": "boolean"}),
    "pki": ("pqc_bench.pki.hybrid_certs", "Offline hybrid test PKI",
            "Caller-recorded local verify_chain outcome; experimental envelope, not production PKI.",
            {"chain_verified": "boolean"}),
    "tls": ("pqc_bench.tls_simulator", "Offline handshake model",
            "Custom local model, not production TLS, peer authentication, confidentiality or network RTT.",
            {"local_duration_ns": "integer", "client_application_match": "boolean",
             "server_application_match": "boolean"}),
    "fips": ("pqc_bench.fips_evidence", "FIPS 140-3 document review",
             "Document assertions only; authenticity, current CMVP status and runtime mode not verified.",
             {"overall_status": "fips", "gaps": "gaps"}),
}
LIMITATIONS = (
    "Offline management review only; no production security, attack resistance, certification or hardware claim.",
    "All supplied excerpts and file locators are caller-attested, not authenticated or read by this exporter.",
    "Missing fields are unmeasured, never zero, passed or compliant. No aggregate security/compliance score.",
    "Synthetic fixture values are examples, not observations. A recorded local TLS duration is not network RTT.",
    "Input files and full module outputs must be retained separately; excerpt hashes do not verify those files.",
)
UNMEASURED = ("production_security", "attack_resistance", "hardware_cycles", "network_rtt",
              "fips_module_validation")
MAX_JSON_BYTES = 65536


def _object(value: Any, allowed: set, required: set) -> dict:
    if (type(value) is not dict or any(type(k) is not str for k in value)
            or set(value) - allowed or required - set(value)):
        raise ValueError("object contains invalid, missing or unknown fields")
    return value


def _text(value: Any, limit: int = 512) -> str:
    if (type(value) is not str or not 1 <= len(value) <= limit or value != value.strip()
            or any(unicodedata.category(c).startswith("C") for c in value)):
        raise ValueError(f"expected 1..{limit} trimmed printable characters")
    return value


def _locator(value: Any) -> str:
    value = _text(value)
    if (not re.fullmatch(r"[A-Za-z0-9_. /-]+", value)
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("expected relative local file locator without traversal or URL")
    return value


def _metric(value: Any, kind: str) -> Any:
    if value is None:
        return None
    if kind in {"number", "integer"}:
        types = (int, float) if kind == "number" else (int,)
        if type(value) not in types or not 0 <= value <= 10**30 or not math.isfinite(value):
            raise ValueError("expected bounded finite nonnegative number (not bool)")
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError("expected boolean")
    elif kind == "text":
        return _text(value)
    elif kind == "gaps":
        if type(value) is not list or len(value) > 512:
            raise ValueError("expected at most 512 evidence gaps")
        pairs = []
        for gap in value:
            gap = _object(gap, {"field", "code"}, {"field", "code"})
            pairs.append((_text(gap["field"], 550), _text(gap["code"])))
        if len(set(pairs)) != len(pairs):
            raise ValueError("duplicate evidence gaps")
        return [{"field": field, "code": code} for field, code in sorted(pairs)]
    else:
        enums = {"policy": {"compliant", "partial", "non-compliant", "transitional", "unknown"},
                 "scan": {"complete", "incomplete"}, "fips": {"not_verified"}}
        if type(value) is not str or value not in enums[kind]:
            raise ValueError("invalid status")
    return value


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def build_report(request: dict) -> dict:
    """Validate version-1 excerpt manifest and build a detached, deterministic report.

    Each supplied section requires input_file, output_file, evidence_kind and output.
    Output is an allowlisted excerpt, NOT an arbitrary native module report.
    Missing sections/metrics remain explicit unmeasured values.
    """
    request = _object(request, {"schema_version", "title", "sections"},
                      {"schema_version", "title", "sections"})
    if type(request["schema_version"]) is not int or request["schema_version"] != 1:
        raise ValueError("unsupported schema version")
    title = _text(request["title"])
    supplied = _object(request["sections"], set(SECTIONS), set())
    sections = []
    for key, (module, heading, limitation, fields) in SECTIONS.items():
        entry = supplied.get(key)
        values = dict.fromkeys(fields)
        source = {"module": module, "input_file": "unmeasured", "output_file": "unmeasured",
                  "evidence_kind": "unmeasured", "excerpt_sha256": "unmeasured"}
        if key in supplied:
            entry = _object(entry, {"input_file", "output_file", "evidence_kind", "output"},
                            {"input_file", "output_file", "evidence_kind", "output"})
            source["input_file"] = _locator(entry["input_file"])
            source["output_file"] = _locator(entry["output_file"])
            if type(entry["evidence_kind"]) is not str or entry["evidence_kind"] not in {
                    "synthetic_fixture", "local_output_excerpt"}:
                raise ValueError("invalid evidence kind")
            source["evidence_kind"] = entry["evidence_kind"]
            output = _object(entry["output"], set(fields), set())
            values = {name: _metric(output.get(name), kind) for name, kind in fields.items()}
            if key == "constant_time":
                if (values["status"] == "complete" and
                        (values["scan_complete"] is False or values["findings_truncated"] is True)):
                    raise ValueError("contradictory scan completion")
                if (values["status"] == "incomplete" and values["scan_complete"] is True
                        and values["findings_truncated"] is False):
                    raise ValueError("contradictory scan incompletion")
                a, b = values["finding_count"], values["instruction_count"]
                if a is not None and b is not None and a > b:
                    raise ValueError("findings exceed instruction count")
            source["excerpt_sha256"] = hashlib.sha256(_canonical(values).encode()).hexdigest()
        sections.append({"id": key, "heading": heading, "source": source,
                         "limitation": limitation, "values": values,
                         "unmeasured_fields": sorted(k for k, v in values.items() if v is None)})
    report = {"schema_version": 1, "title": title, "scope": "offline_executive_review",
              "overall_status": "not_verified", "sections": sections,
              "limitations": list(LIMITATIONS), "unmeasured": list(UNMEASURED)}
    if len(_canonical(report).encode()) > MAX_JSON_BYTES:
        raise ValueError("report exceeds byte budget")
    return report


def load_request(text: str) -> dict:
    """Strict bounded JSON parser; duplicate keys and nonfinite constants rejected."""
    if type(text) is not str or len(text) > MAX_JSON_BYTES:
        raise ValueError("invalid JSON text size")
    try:
        if len(text.encode("utf-8")) > MAX_JSON_BYTES:
            raise ValueError("JSON exceeds byte budget")
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result

        def constant(value):
            raise ValueError("nonfinite JSON constant")

        request = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
        build_report(request)
    except (RecursionError, UnicodeError) as exc:
        raise ValueError("invalid JSON encoding or nesting") from exc
    return request


def _display(value: Any) -> str:
    if value is None:
        return "unmeasured"
    return value if type(value) is str else _canonical(value)


def _md(value: Any) -> str:
    # Punctuation entities prevent raw HTML, links, tables, code and emphasis.
    return "".join(c if c.isalnum() or c == " " else f"&#{ord(c)};" for c in _display(value))


def _rows(values: dict):
    for name, value in values.items():
        if name == "gaps" and value:
            for gap in value:
                yield "gap: " + gap["field"], gap["code"]
        else:
            yield name, value


def report_markdown(request: dict) -> str:
    report = build_report(request)
    lines = ["# " + _md(report["title"]), "", "**Overall: not_verified**", ""]
    lines += ["- " + line for line in LIMITATIONS]
    lines += ["", "## Always unmeasured", "", ", ".join(UNMEASURED)]
    for section in report["sections"]:
        lines += ["", "## " + section["heading"], "", section["limitation"], ""]
        lines += ["- " + name + ": " + _md(value) for name, value in section["source"].items()]
        lines += ["", "| Output excerpt field | Caller-supplied value |", "|---|---|"]
        lines += [f"| {_md(name)} | {_md(value)} |" for name, value in _rows(section["values"])]
    return "\n".join(lines) + "\n"


def report_html(request: dict) -> str:
    """Standalone printable HTML: static CSS, no JS, external assets or active links."""
    report = build_report(request)
    esc = lambda v: html.escape(_display(v), quote=True)
    lines = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
             'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>' + esc(report["title"]) + '</title>',
             '<style>body{font:16px sans-serif;max-width:72em;margin:2em auto;padding:1em}'
             'table{border-collapse:collapse;width:100%;overflow-wrap:anywhere}'
             'td,th{border:1px solid #777;padding:.5em;text-align:left}'
             'p,li{overflow-wrap:anywhere}@media print{body{margin:0;font-size:10pt}'
             'thead{display:table-header-group}tr{break-inside:avoid}h2{break-after:avoid}}</style>',
             '</head><body><h1>' + esc(report["title"]) + '</h1>',
             '<p><strong>Overall: not_verified</strong></p><ul>']
    lines += ['<li>' + esc(line) + '</li>' for line in LIMITATIONS]
    lines += ['</ul><h2>Always unmeasured</h2><p>' + esc(', '.join(UNMEASURED)) + '</p>']
    for section in report["sections"]:
        lines += ['<section><h2>' + esc(section["heading"]) + '</h2>',
                  '<p>' + esc(section["limitation"]) + '</p><ul>']
        lines += ['<li>' + esc(k) + ': ' + esc(v) + '</li>' for k, v in section["source"].items()]
        lines += ['</ul><table><thead><tr><th>Output excerpt field</th>'
                  '<th>Caller-supplied value</th></tr></thead><tbody>']
        lines += ['<tr><td>' + esc(k) + '</td><td>' + esc(v) + '</td></tr>'
                  for k, v in _rows(section["values"])]
        lines += ['</tbody></table></section>']
    return '\n'.join(lines + ['</body></html>']) + '\n'
