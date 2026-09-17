"""Invented offline assertions only; no fixture represents a real certificate."""
from copy import deepcopy
import json

import pytest

from pqc_bench.fips_evidence import (
    FIELDS, TARGET_FIELDS, build_matrix, load_request, matrix_json, matrix_markdown,
)


@pytest.fixture
def request_data():
    target = dict(module_id="SYNTHETIC MODULE", version="test-1",
                  environment="synthetic CPU", approved_mode="test approved mode",
                  services=["test-sign"])
    doc = dict(target, document_id="local-1", locator="fixture:policy section 1",
               certificate_reference="SYNTHETIC-NOT-A-CERTIFICATE",
               certificate_standard="FIPS 140-3", certificate_status="active",
               security_policy_reference="fixture:security-policy")
    return {"target": target, "documents": [doc]}


def codes(report, field=None):
    return {gap["code"] for gap in report["gaps"]
            if field is None or gap["field"] == field}


def row(report, field):
    return next(r for r in report["rows"] if r["field"] == field)


def test_complete_still_unverified(request_data):
    result = build_matrix(request_data)
    assert result["overall_status"] == "not_verified"
    assert all(r["status"] == "not_verified" for r in result["rows"])
    assert codes(result) == {"authenticity_not_verified", "runtime_mode_not_verified",
                             "current_cmvp_status_not_verified"}
    assert result["documents"] == request_data["documents"]
    assert len(result["sources"]) == 3


def test_empty_evidence():
    result = build_matrix({"target": {"module_id": "cryptography ML-KEM-768 FIPS 203"},
                           "documents": []})
    assert all(r["status"] == "unknown" for r in result["rows"])
    assert all("missing_evidence" in r["gaps"] for r in result["rows"])
    assert result["overall_status"] == "not_verified"


@pytest.mark.parametrize("field", FIELDS)
def test_missing_fields(request_data, field):
    del request_data["documents"][0][field]
    result = build_matrix(request_data)
    assert row(result, field)["status"] == "unknown"
    assert "missing_evidence" in codes(result, field)


@pytest.mark.parametrize("field", TARGET_FIELDS)
def test_scope_mismatch(request_data, field):
    request_data["documents"][0][field] = ["different"] if field == "services" else "different"
    assert "target_scope_mismatch" in codes(build_matrix(request_data), field)


@pytest.mark.parametrize("field", FIELDS)
def test_conflicting_documents(request_data, field):
    second = deepcopy(request_data["documents"][0])
    second["document_id"] = "local-2"
    second[field] = {"services": ["different"], "certificate_status": "revoked",
                     "certificate_standard": "FIPS 140-2"}.get(field, "different")
    request_data["documents"].append(second)
    assert "conflicting_evidence" in codes(build_matrix(request_data), field)


@pytest.mark.parametrize("status", ["historical", "revoked", "unknown"])
def test_certificate_status(request_data, status):
    request_data["documents"][0]["certificate_status"] = status
    result = build_matrix(request_data)
    assert result["overall_status"] == "not_verified"
    assert ("missing_evidence" if status == "unknown" else "certificate_" + status) in codes(
        result, "certificate_status")


def test_wrong_standard(request_data):
    request_data["documents"][0]["certificate_standard"] = "FIPS 140-2"
    assert "wrong_standard" in codes(build_matrix(request_data))


def test_unbound_fragments(request_data):
    reference = request_data["documents"][0].pop("certificate_reference")
    request_data["documents"].append({"document_id": "fragment", "locator": "local:2",
                                      "certificate_reference": reference})
    assert "unbound_document_scope" in codes(build_matrix(request_data))


@pytest.mark.parametrize("field", ["module_id", "version", "environment",
                                  "certificate_reference"])
def test_unknown_scope_cannot_bind_document(request_data, field):
    request_data["documents"][0][field] = "unknown"
    result = build_matrix(request_data)
    assert row(result, field)["status"] == "unknown"
    assert "unbound_document_scope" in codes(result, f"document:local-1:{field}")


@pytest.mark.parametrize("field", ["module_id", "version", "environment", "approved_mode"])
def test_unknown_target_scope_is_missing_not_mismatch(request_data, field):
    request_data["target"][field] = "unknown"
    result = build_matrix(request_data)
    assert "missing_target_scope" in codes(result, field)
    assert "target_scope_mismatch" not in codes(result, field)


def test_canonical_order_and_no_mutation(request_data):
    doc = deepcopy(request_data["documents"][0])
    doc["document_id"] = "aaa"
    request_data["documents"].append(doc)
    for item in [request_data["target"], *request_data["documents"]]:
        item["services"] = ["test-sign", "test-hash"]
    original = deepcopy(request_data)
    expected_json = matrix_json(request_data)
    expected_md = matrix_markdown(request_data)
    assert request_data == original
    request_data["documents"].reverse()
    for item in [request_data["target"], *request_data["documents"]]:
        item["services"].reverse()
    assert matrix_json(request_data) == expected_json
    assert matrix_markdown(request_data) == expected_md
    assert json.loads(expected_json) == build_matrix(request_data)
    assert expected_json.endswith("\n") and expected_md.endswith("\n")


def test_services_subset(request_data):
    request_data["documents"][0]["services"].append("test-hash")
    assert "target_scope_mismatch" not in codes(build_matrix(request_data), "services")


def test_markdown_inert_user_text(request_data):
    payload = '<script>|[click](https://invalid.example/)`_*'
    request_data["documents"][0]["locator"] = payload
    output = matrix_markdown(request_data)
    assert payload not in output and '<script>' not in output
    assert "[click]" not in output and "https://invalid.example/" not in output
    assert "&#124;" in output and "&#60;" in output
    assert payload in matrix_json(request_data)


@pytest.mark.parametrize("bad", [True, 1, 1.5, [], {}, "", " ", " x", "x ", "a\nb",
                                 "a\x00b", "x" * 513, "\ud800", "a\u202eb"])
@pytest.mark.parametrize("field", [f for f in FIELDS if f != "services"])
def test_strict_document_strings(request_data, field, bad):
    request_data["documents"][0][field] = bad
    with pytest.raises(ValueError):
        build_matrix(request_data)


@pytest.mark.parametrize("bad", [True, 1, "sign", {}, (), [], ["x", "x"], [False],
                                 [""], [str(i) for i in range(33)]])
def test_strict_services(request_data, bad):
    request_data["target"]["services"] = bad
    with pytest.raises(ValueError):
        build_matrix(request_data)


@pytest.mark.parametrize("location", ["request", "target", "document"])
def test_reject_policy_labels(request_data, location):
    obj = {"request": request_data, "target": request_data["target"],
           "document": request_data["documents"][0]}[location]
    obj["compliant"] = True
    with pytest.raises(ValueError):
        build_matrix(request_data)


@pytest.mark.parametrize("bad", [None, [], True, "{}", 1])
def test_bad_request(bad):
    with pytest.raises(ValueError):
        build_matrix(bad)


@pytest.mark.parametrize("bad", [None, {}, True, (), "[]"])
def test_bad_documents(request_data, bad):
    request_data["documents"] = bad
    with pytest.raises(ValueError):
        build_matrix(request_data)


def test_document_bounds_and_duplicates(request_data):
    doc = request_data["documents"][0]
    request_data["documents"] = [dict(doc, document_id=str(i)) for i in range(64)]
    assert len(build_matrix(request_data)["documents"]) == 64
    request_data["documents"].append(dict(doc, document_id="65"))
    with pytest.raises(ValueError):
        build_matrix(request_data)
    request_data["documents"] = [doc, doc]
    with pytest.raises(ValueError):
        build_matrix(request_data)


@pytest.mark.parametrize("bad", [None, False, "", " "])
def test_module_identity_required(request_data, bad):
    request_data["target"]["module_id"] = bad
    with pytest.raises(ValueError):
        build_matrix(request_data)


@pytest.mark.parametrize("field", ["document_id", "locator"])
def test_document_provenance_required(request_data, field):
    del request_data["documents"][0][field]
    with pytest.raises(ValueError):
        build_matrix(request_data)


def test_json_loader(request_data):
    assert load_request(json.dumps(request_data)) == request_data


@pytest.mark.parametrize("text", [None, False, "x" * 262145, '{"target":{},"target":{}}',
                                  '{"target":{"module_id":NaN},"documents":[]}',
                                  '{"target":{"module_id":Infinity},"documents":[]}',
                                  '{"target":{"module_id":-Infinity},"documents":[]}',
                                  '{}', '[]', '{', '[' * 2000])
def test_json_rejections(text):
    with pytest.raises(ValueError):
        load_request(text)
