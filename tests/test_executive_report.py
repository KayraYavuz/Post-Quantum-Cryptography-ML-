"""Offline contract tests with synthetic fixtures; no external integrations."""
import copy
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

from pqc_bench.executive_report import (
    MAX_JSON_BYTES, SECTIONS, build_report, load_request, report_html, report_markdown,
)

FIXTURES = Path(__file__).parent / "fixtures" / "executive_report"


@pytest.fixture
def data():
    return load_request((FIXTURES / "manifest.json").read_text())


def test_fixture_native_outputs(data):
    from pqc_bench.security_estimation.lattice_runner import estimate_security
    from pqc_bench.quantum_cost import estimate_quantum_resources
    from pqc_bench.fips_evidence import build_matrix
    from pqc_bench.tls_simulator import SimulationResult
    native = json.loads((FIXTURES / "outputs.json").read_text())
    assert native["security"] == estimate_security("ml-kem-768")
    assert native["quantum"] == estimate_quantum_resources("ml-kem-768")
    assert native["fips"] == build_matrix({"target": {"module_id": "Synthetic module"}, "documents": []})
    assert native["tls"] == SimulationResult(123456, True, True, "0" * 64).to_report()
    for key, section in data["sections"].items():
        assert all(v == native[key][k] for k, v in section["output"].items())
        assert Path(section["input_file"]).is_file()
        assert Path(section["output_file"]).is_file()


def test_determinism_snapshot_and_no_mutation(data):
    before = copy.deepcopy(data)
    reordered = json.loads(json.dumps(data, sort_keys=True))
    reordered["sections"] = dict(reversed(list(reordered["sections"].items())))
    reordered["sections"]["fips"]["output"]["gaps"].reverse()
    for render in (build_report, report_markdown, report_html):
        assert render(data) == render(reordered) == render(data)
    assert before == data
    assert report_markdown(data) == (FIXTURES / "expected.md").read_text()
    assert report_html(data) == (FIXTURES / "expected.html").read_text()


def test_provenance(data):
    report = build_report(data)
    assert report["overall_status"] == "not_verified"
    assert len(report["sections"]) == 7
    for section in report["sections"]:
        source = section["source"]
        assert source["module"] == SECTIONS[section["id"]][0]
        assert source["evidence_kind"] == "synthetic_fixture"
        canonical = json.dumps(section["values"], sort_keys=True, ensure_ascii=True,
                               allow_nan=False, separators=(",", ":"))
        assert source["excerpt_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert "hardware_cycles" in report["unmeasured"]
    assert "network_rtt" in report["unmeasured"]


def test_missing_zero_and_false(data):
    empty = {"schema_version": 1, "title": "Missing evidence", "sections": {}}
    for section in build_report(empty)["sections"]:
        assert all(v is None for v in section["values"].values())
        assert section["source"]["input_file"] == "unmeasured"
        assert set(section["unmeasured_fields"]) == set(section["values"])
    data["sections"]["tls"]["output"] = {"local_duration_ns": 0, "client_application_match": False}
    tls = next(s for s in build_report(data)["sections"] if s["id"] == "tls")
    assert tls["values"]["local_duration_ns"] == 0
    assert tls["values"]["client_application_match"] is False
    assert tls["unmeasured_fields"] == ["server_application_match"]
    assert "unmeasured" in report_markdown(empty)
    assert "unmeasured" in report_html(empty)


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.attrs = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(attrs)


@pytest.mark.parametrize("text", ["<script>alert(1)</script>", "[click](https://example.org)",
                                  "![image](file:///etc/passwd)", "{{7*7}} ${x} `code` | #",
                                  "&lt;img src=x onerror=bad&gt;", "\" autofocus='yes'"])
def test_escape(data, text):
    data["title"] = text
    data["sections"]["fips"]["output"]["gaps"] = [{"field": text, "code": text}]
    document = report_html(data)
    parser = Elements()
    parser.feed(document)
    assert not set(parser.tags) & {"script", "img", "iframe", "a", "form", "link"}
    assert not any(k.startswith("on") or k in {"src", "href", "autofocus"} for k, _ in parser.attrs)
    assert text not in report_markdown(data)
    assert "<script>" not in document
    assert "@media print" in document and "Content-Security-Policy" in document


@pytest.mark.parametrize("value", [True, False, 1.0, "1", 0, 2, None])
def test_bad_version(data, value):
    data["schema_version"] = value
    with pytest.raises(ValueError):
        build_report(data)


@pytest.mark.parametrize("value", [None, "", " padded", "padded ", "x\ny", "x\x00", "x\u202ey", "x\ud800", "a"*513, 1, True])
def test_bad_title(data, value):
    data["title"] = value
    with pytest.raises(ValueError):
        build_report(data)


@pytest.mark.parametrize("path", ["/etc/passwd", "../file", "a/../b", "a/./b", "a//b", "a/", "file://x",
                                  "https://x", "C:\\x", "a\\b", "[x](y)", "<img>", "", None])
def test_bad_locator(data, path):
    data["sections"]["tls"]["input_file"] = path
    with pytest.raises(ValueError):
        build_report(data)


@pytest.mark.parametrize("value", [-1, True, False, "123", [], {}, float("nan"), float("inf"), 10**31])
@pytest.mark.parametrize("section,field", [("security", "classical_security_bits"), ("tls", "local_duration_ns")])
def test_bad_number(data, value, section, field):
    data["sections"][section]["output"][field] = value
    with pytest.raises(ValueError):
        build_report(data)


@pytest.mark.parametrize("value", [0, 1, "true", [], {}, 1.0])
def test_bad_boolean(data, value):
    data["sections"]["pki"]["output"]["chain_verified"] = value
    with pytest.raises(ValueError):
        build_report(data)


def test_unknown_fields_and_escalation(data):
    mutations = [
        lambda d: d.update(extra=1),
        lambda d: d["sections"].update(attack={}),
        lambda d: d["sections"].update(tls=None),
        lambda d: d["sections"]["tls"].update(module="evil"),
        lambda d: d["sections"]["tls"].update(evidence_kind="verified"),
        lambda d: d["sections"]["tls"]["output"].update(private_key="secret"),
        lambda d: d["sections"]["fips"]["output"].update(overall_status="certified"),
        lambda d: d["sections"]["tls"]["output"].update(local_duration_ns=1.5),
        lambda d: d["sections"]["constant_time"]["output"].update(status="complete"),
        lambda d: d["sections"]["constant_time"]["output"].update(finding_count=100),
        lambda d: d["sections"]["constant_time"]["output"].update(scan_complete=True),
        lambda d: d["sections"]["fips"]["output"].update(gaps=[{"field":"x", "code":"y"}]*2),
        lambda d: d["sections"]["fips"]["output"].update(gaps=[{}]*513),
    ]
    for mutate in mutations:
        bad = copy.deepcopy(data)
        mutate(bad)
        with pytest.raises(ValueError):
            build_report(bad)


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}',
                                  '[', 'null', '[]', '"string"', '['*2000+']'*2000,
                                  ' '* (MAX_JSON_BYTES+1), '\ud800'])
def test_bad_json(text):
    with pytest.raises(ValueError):
        load_request(text)


def test_render_budget(data):
    data["sections"]["fips"]["output"]["gaps"] = [
        {"field": str(i) + "a"*500, "code": "b"*512} for i in range(150)]
    with pytest.raises(ValueError, match="byte budget"):
        build_report(data)


def test_native_long_gap_and_separate_html_rows(data):
    from pqc_bench.fips_evidence import build_matrix
    native = build_matrix({"target": {"module_id": "Example"}, "documents": [
        {"document_id": "a"*512, "locator": "doc.txt", "certificate_status": "active"}]})
    data["sections"]["fips"]["output"] = {k: native[k] for k in ("overall_status", "gaps")}
    assert build_report(data)
    assert report_html(data).count("<tr><td>gap: ") == len(native["gaps"])


def test_detached_output_and_no_file_reads(data, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected file I/O")
    monkeypatch.setattr("builtins.open", forbidden)
    report = build_report(data)
    report["sections"][0]["values"]["classical_security_bits"] = 0
    assert data["sections"]["security"]["output"]["classical_security_bits"] == 192
    assert report_markdown(data) and report_html(data)
