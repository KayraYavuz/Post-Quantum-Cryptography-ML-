"""Fixed CPU fixtures: tool presence never becomes a measured benchmark."""
import itertools
import json

import pytest

from pqc_bench import qemu_feasibility as qf


def availability(value=False):
    return dict.fromkeys(qf.REQUIRED_TOOLS, value)


@pytest.mark.parametrize("values", list(itertools.product((True, False, None), repeat=5)))
def test_all_discovery_combinations(values):
    tools = dict(zip(qf.REQUIRED_TOOLS, values))
    report = qf.assess_toolchain(tools)
    expected = ("blocked_missing_tools" if False in values else
                "unresolved_tool_discovery" if None in values else
                "prerequisites_unverified")
    assert report["status"] == expected
    assert report["missing_tools"] == [k for k, v in tools.items() if v is False]
    assert report["unknown_tools"] == [k for k, v in tools.items() if v is None]
    assert report["metrics"] == dict.fromkeys(qf.METRICS)
    assert report["unmeasured_metrics"] == list(qf.METRICS)
    assert report["execution_status"] == "not_run"
    assert report["target"]["local_runtime_support"] == "not_verified"
    assert report["evidence"] == "caller_attested_tool_discovery"


@pytest.mark.parametrize("bad", [0, 1, "yes", "", [], {}, 1.0, float("nan")])
def test_reject_non_boolean_tool_claims(bad):
    tools = availability()
    tools["qemu-system-arm"] = bad
    with pytest.raises(ValueError):
        qf.assess_toolchain(tools)


@pytest.mark.parametrize("bad", [None, [], {}, {"qemu-arm": True}, "qemu-system-arm"])
def test_reject_wrong_schema(bad):
    with pytest.raises(ValueError):
        qf.assess_toolchain(bad)


def test_unknown_keys_and_missing_keys():
    tools = availability()
    tools["hardware_cycles"] = 42
    with pytest.raises(ValueError):
        qf.assess_toolchain(tools)
    del tools["hardware_cycles"]
    del tools["make"]
    with pytest.raises(ValueError):
        qf.assess_toolchain(tools)


def test_lookup_is_fixed_read_only_and_redacts_paths(monkeypatch):
    calls = []

    def lookup(name):
        calls.append(name)
        return "/private/tool/bin/" + name if name == "make" else None

    monkeypatch.setattr(qf.shutil, "which", lookup)
    report = qf.inspect_local_tools()
    assert calls == list(qf.REQUIRED_TOOLS)
    assert report["evidence"] == "local_path_lookup"
    assert report["tools"]["make"] == "found_on_path"
    assert report["tools"]["qemu-system-arm"] == "not_found_on_path"
    assert "/private" not in json.dumps(report)


def test_lookup_error_is_unknown(monkeypatch):
    def lookup(name):
        raise OSError("private filesystem error")

    monkeypatch.setattr(qf.shutil, "which", lookup)
    report = qf.inspect_local_tools()
    assert report["status"] == "unresolved_tool_discovery"
    assert report["unknown_tools"] == list(qf.REQUIRED_TOOLS)
    assert report["missing_tools"] == []
    assert "private" not in json.dumps(report)


def test_all_found_is_not_ready(monkeypatch):
    monkeypatch.setattr(qf.shutil, "which", lambda name: "/bin/" + name)
    report = qf.inspect_local_tools()
    assert report["status"] == "prerequisites_unverified"
    assert report["execution_status"] == "not_run"
    assert report["metrics"]["hardware_cycles"] is None


def test_no_mutable_aliasing():
    tools = availability()
    report = qf.assess_toolchain(tools)
    tools["make"] = True
    report["limitations"].clear()
    report["target"]["local_runtime_support"] = "fake"
    report["metrics"]["hardware_cycles"] = 123
    fresh = qf.assess_toolchain(availability())
    assert fresh["limitations"]
    assert fresh["target"]["local_runtime_support"] == "not_verified"
    assert fresh["metrics"]["hardware_cycles"] is None
    assert report["tools"]["make"] == "not_found_on_path"


def test_main_json_is_repeatable(monkeypatch, capsys):
    monkeypatch.setattr(qf.shutil, "which", lambda name: None)
    qf.main()
    first = capsys.readouterr().out
    qf.main()
    assert first == capsys.readouterr().out
    parsed = json.loads(first)
    assert parsed == qf.inspect_local_tools()
    assert parsed["status"] == "blocked_missing_tools"
