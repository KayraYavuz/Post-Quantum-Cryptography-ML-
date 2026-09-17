"""Local inert ELF fixtures only: no compiler, external binaries, or execution."""

import json
import os
import struct

import pytest

from pqc_bench.constant_time import binary_auditor as auditor


def make_elf(
    bits=64,
    elf_type=1,
    code=b"\x90\xf7\xf1\xf7\xf9\xc3",
    *,
    machine=None,
    endian="<",
    executable=True,
    section_type=1,
    section_flags=None,
):
    """Assemble only ELF header, inert byte sections, and section headers."""
    is64 = bits == 64
    header_size, section_size = (64, 64) if is64 else (52, 40)
    ident = b"\x7fELF" + bytes([2 if is64 else 1, 1 if endian == "<" else 2, 1, 0, 0])
    ident += bytes(7)
    names = b"\0.text\0.data\0.shstrtab\0"
    # Division-looking bytes are deliberately placed in non-executable data.
    inert_data = b"\xf7\xf1\xf7\xf9"
    text_offset = header_size
    data_offset = text_offset + len(code)
    names_offset = data_offset + len(inert_data)
    table_offset = names_offset + len(names)
    flags = (6 if executable else 2) if section_flags is None else section_flags
    address = 0 if elf_type == 1 else 0x401000
    headers = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (1, section_type, flags, address, text_offset, len(code), 0, 0, 1, 0),
        (7, 1, 2, 0, data_offset, len(inert_data), 0, 0, 1, 0),
        (13, 3, 0, 0, names_offset, len(names), 0, 0, 1, 0),
    ]
    header_format = endian + ("HHIQQQIHHHHHH" if is64 else "HHIIIIIHHHHHH")
    header = struct.pack(
        header_format,
        elf_type, machine if machine is not None else (62 if is64 else 3),
        1, 0, 0, table_offset, 0, header_size, 0, 0, section_size, len(headers), 3,
    )
    section_format = endian + ("IIQQQQIIQQ" if is64 else "IIIIIIIIII")
    return ident + header + code + inert_data + names + b"".join(
        struct.pack(section_format, *h) for h in headers
    )


def save_elf(tmp_path, **kwargs):
    path = tmp_path / "owned-fixture.elf"
    path.write_bytes(make_elf(**kwargs))
    return path


def patch_header(data, field, value, bits=64):
    formats = "HHIQQQIHHHHHH" if bits == 64 else "HHIIIIIHHHHHH"
    values = list(struct.unpack_from("<" + formats, data, 16))
    names = [
        "type", "machine", "version", "entry", "phoff", "shoff", "flags", "ehsize",
        "phentsize", "phnum", "shentsize", "shnum", "shstrndx",
    ]
    values[names.index(field)] = value
    result = bytearray(data)
    struct.pack_into("<" + formats, result, 16, *values)
    return result


def patch_section(data, index, field, value, bits=64):
    table = struct.unpack_from("<Q" if bits == 64 else "<I", data, 40 if bits == 64 else 32)[0]
    fmt = "IIQQQQIIQQ" if bits == 64 else "IIIIIIIIII"
    start = table + index * struct.calcsize("<" + fmt)
    values = list(struct.unpack_from("<" + fmt, data, start))
    names = [
        "name", "type", "flags", "address", "offset", "size", "link", "info", "align", "entsize",
    ]
    values[names.index(field)] = value
    result = bytearray(data)
    struct.pack_into("<" + fmt, result, start, *values)
    return result


@pytest.mark.parametrize("bits", [32, 64])
@pytest.mark.parametrize("elf_type,label", [(1, "ET_REL"), (2, "ET_EXEC"), (3, "ET_DYN")])
def test_supported_types_and_instruction_locations(tmp_path, bits, elf_type, label):
    path = save_elf(tmp_path, bits=bits, elf_type=elf_type)
    report = auditor.audit_binary(path, project_root=tmp_path)
    assert report["status"] == "complete"
    assert report["scan_complete"] is True
    assert report["elf_type"] == label
    assert report["architecture"] == ("x86" if bits == 32 else "x86_64")
    assert report["instruction_count"] == 4
    assert report["finding_count"] == 2
    assert [f["mnemonic"] for f in report["findings"]] == ["div", "idiv"]
    assert [f["section_offset"] for f in report["findings"]] == [1, 3]
    assert report["findings"][0]["file_offset"] == (52 if bits == 32 else 64) + 1
    assert report["findings"][0]["address"] == (0 if elf_type == 1 else 0x401000) + 1
    assert report["findings"][0]["instruction_bytes"] == "f7f1"
    assert report["sections"][0]["name"] == ".text"
    assert report["input"] == path.name
    assert "neither a leakage finding nor a constant-time verdict" in report["disclaimer"]
    assert "verdict" not in report


@pytest.mark.parametrize("bits", [32, 64])
def test_data_and_immediate_bytes_are_not_findings(tmp_path, bits):
    # mov eax, imm32 containing div/idiv-looking bytes, followed by ret.
    path = save_elf(tmp_path, bits=bits, code=b"\xb8\xf7\xf1\xf7\xf9\xc3")
    report = auditor.audit_binary(path, project_root=tmp_path)
    assert report["findings"] == []
    assert report["status"] == "complete"
    assert report["instruction_count"] == 2
    assert len(report["sections"]) == 1


@pytest.mark.parametrize("bits", [32, 64])
@pytest.mark.parametrize("code,decoded", [(b"\x0f", 0), (b"\x90\x0f", 1), (b"\xf7\xf1\x0f", 2)])
def test_incomplete_decode_never_looks_complete(tmp_path, bits, code, decoded):
    path = save_elf(tmp_path, bits=bits, code=code)
    report = auditor.audit_binary(path, project_root=tmp_path)
    assert report["status"] == "incomplete"
    assert report["scan_complete"] is False
    section = report["sections"][0]
    assert section["decoded_bytes"] == decoded
    assert section["unexamined_bytes"] == 1
    assert section["stop_section_offset"] == decoded
    assert section["incomplete_reason"] == "decode_stopped"


def test_instruction_and_finding_output_limits(tmp_path, monkeypatch):
    path = save_elf(tmp_path, code=b"\xf7\xf1" * 5)
    monkeypatch.setattr(auditor, "MAX_INSTRUCTIONS", 3)
    monkeypatch.setattr(auditor, "MAX_FINDINGS", 1)
    report = auditor.audit_binary(path, project_root=tmp_path)
    assert report["status"] == "incomplete"
    assert report["instruction_count"] == 3
    assert report["finding_count"] == 3
    assert len(report["findings"]) == 1
    assert report["findings_truncated"] is True
    assert report["sections"][0]["incomplete_reason"] == "instruction_limit"
    assert report["sections"][0]["unexamined_bytes"] == 4


def test_truncated_findings_even_when_scan_complete(tmp_path, monkeypatch):
    path = save_elf(tmp_path)
    monkeypatch.setattr(auditor, "MAX_FINDINGS", 1)
    report = auditor.audit_binary(path, project_root=tmp_path)
    assert report["status"] == "incomplete"
    assert report["scan_complete"] is True
    assert report["findings_truncated"] is True


def test_exact_instruction_budget_complete(tmp_path, monkeypatch):
    path = save_elf(tmp_path, code=b"\x90\xc3")
    monkeypatch.setattr(auditor, "MAX_INSTRUCTIONS", 2)
    assert auditor.audit_binary(path, project_root=tmp_path)["status"] == "complete"


def test_multiple_executable_sections(tmp_path):
    path = save_elf(tmp_path, code=b"\x90")
    path.write_bytes(patch_section(path.read_bytes(), 2, "flags", 6))
    report = auditor.audit_binary(path, project_root=tmp_path)
    assert len(report["sections"]) == 2
    assert report["finding_count"] == 2
    assert all(f["section_index"] == 2 for f in report["findings"])


@pytest.mark.parametrize("kwargs,match", [
    ({"machine": 183}, "x86"),
    ({"bits": 32, "machine": 62}, "x86"),
    ({"bits": 64, "machine": 3}, "x86"),
    ({"endian": ">"}, "little-endian"),
    ({"elf_type": 4}, "ET_REL"),
    ({"executable": False}, "no executable"),
    ({"code": b""}, "invalid executable"),
    ({"section_type": 8}, "invalid executable"),
    ({"section_flags": 0x806}, "invalid executable"),
])
def test_unsupported_or_invalid_sections(tmp_path, kwargs, match):
    path = save_elf(tmp_path, **kwargs)
    with pytest.raises(auditor.BinaryAuditError, match=match):
        auditor.audit_binary(path, project_root=tmp_path)


@pytest.mark.parametrize("field,value", [
    ("ehsize", 1), ("version", 0), ("shoff", 999999), ("shoff", 0),
    ("shentsize", 1), ("shnum", 0), ("shnum", 300), ("shstrndx", 400),
])
def test_invalid_headers(tmp_path, field, value):
    path = save_elf(tmp_path)
    path.write_bytes(patch_header(path.read_bytes(), field, value))
    with pytest.raises(auditor.BinaryAuditError):
        auditor.audit_binary(path, project_root=tmp_path)


@pytest.mark.parametrize("index,field,value", [
    (0, "type", 1), (1, "offset", 999999), (1, "offset", 0),
    (1, "size", 999999), (1, "name", 999999), (1, "align", 3),
    (1, "address", 2**64 - 1), (3, "type", 1), (3, "offset", 999999),
])
def test_malformed_section_headers(tmp_path, index, field, value):
    path = save_elf(tmp_path)
    path.write_bytes(patch_section(path.read_bytes(), index, field, value))
    with pytest.raises(auditor.BinaryAuditError):
        auditor.audit_binary(path, project_root=tmp_path)


def test_section_table_overlap_and_exec_overlap(tmp_path):
    path = save_elf(tmp_path)
    original = path.read_bytes()
    table_offset = struct.unpack_from("<Q", original, 40)[0]
    path.write_bytes(patch_section(original, 1, "offset", table_offset))
    with pytest.raises(auditor.BinaryAuditError, match="invalid executable"):
        auditor.audit_binary(path, project_root=tmp_path)
    overlap = patch_section(original, 2, "flags", 6)
    path.write_bytes(patch_section(overlap, 2, "offset", 64))
    with pytest.raises(auditor.BinaryAuditError, match="overlapping"):
        auditor.audit_binary(path, project_root=tmp_path)


@pytest.mark.parametrize("data", [b"", b"not an ELF", b"\x7fELF", make_elf()[:-1]])
def test_malformed_input(tmp_path, data):
    path = tmp_path / "bad.elf"
    path.write_bytes(data)
    with pytest.raises(auditor.BinaryAuditError):
        auditor.audit_binary(path, project_root=tmp_path)


def test_file_and_executable_byte_limits(tmp_path, monkeypatch):
    path = save_elf(tmp_path)
    monkeypatch.setattr(auditor, "MAX_FILE_BYTES", path.stat().st_size - 1)
    with pytest.raises(auditor.BinaryAuditError, match="byte limit"):
        auditor.audit_binary(path, project_root=tmp_path)
    monkeypatch.setattr(auditor, "MAX_FILE_BYTES", 8192)
    monkeypatch.setattr(auditor, "MAX_EXECUTABLE_BYTES", 1)
    with pytest.raises(auditor.BinaryAuditError, match="bytes exceed"):
        auditor.audit_binary(path, project_root=tmp_path)


def test_explicit_project_root_required(tmp_path):
    path = save_elf(tmp_path)
    with pytest.raises(TypeError):
        auditor.audit_binary(path)


def test_containment_and_symlinks(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    path = save_elf(root)
    outside = save_elf(tmp_path)
    escape = root / "escape.elf"
    escape.symlink_to(outside)
    inside = root / "internal.elf"
    inside.symlink_to(path)
    for candidate in [outside, root / ".." / outside.name, escape]:
        with pytest.raises(auditor.BinaryAuditError, match="inside project_root"):
            auditor.audit_binary(candidate, project_root=root)
    assert auditor.audit_binary(inside, project_root=root)["input"] == path.name


def test_relative_paths_are_cwd_relative(tmp_path, monkeypatch):
    path = save_elf(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert auditor.audit_binary(path.name, project_root=".")["input"] == path.name


def test_missing_path_root_and_nonregular_files(tmp_path):
    path = save_elf(tmp_path)
    for candidate, root in [
        (tmp_path / "missing", tmp_path), (path, tmp_path / "missing"),
        (path, path), (tmp_path, tmp_path),
    ]:
        with pytest.raises(auditor.BinaryAuditError):
            auditor.audit_binary(candidate, project_root=root)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(auditor.BinaryAuditError, match="regular file"):
        auditor.audit_binary(fifo, project_root=tmp_path)


def test_missing_dependencies_are_clear(tmp_path, monkeypatch):
    import builtins

    path = save_elf(tmp_path)
    real_import = builtins.__import__
    for dependency in ("elftools", "capstone"):
        def guarded_import(name, *args, **kwargs):
            if name.startswith(dependency):
                raise ImportError("fixture missing dependency")
            return real_import(name, *args, **kwargs)

        with monkeypatch.context() as context:
            context.setattr(builtins, "__import__", guarded_import)
            with pytest.raises(auditor.BinaryAuditError, match="required"):
                auditor.audit_binary(path, project_root=tmp_path)


def test_cli_json_success_incomplete_error(tmp_path, capsys):
    path = save_elf(tmp_path)
    assert auditor.main([str(path), "--project-root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "complete"
    path.write_bytes(make_elf(code=b"\x0f"))
    assert auditor.main([str(path), "--project-root", str(tmp_path)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "incomplete"
    path.write_bytes(b"not ELF")
    assert auditor.main([str(path), "--project-root", str(tmp_path)]) == 2
    error = json.loads(capsys.readouterr().out)
    assert error["status"] == "error"
    assert "ELF" in error["error"]
    assert auditor.main([str(path)]) == 2
    assert "--project-root" in json.loads(capsys.readouterr().out)["error"]


def test_module_entrypoint(tmp_path, monkeypatch, capsys):
    # Run only our Python entry point, never the ELF fixture or a shell.
    import runpy
    import sys
    import warnings

    path = save_elf(tmp_path)
    monkeypatch.setattr(sys, "argv", ["binary_auditor", str(path), "--project-root", str(tmp_path)])
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, message=".*found in sys.modules.*"
        )
        with pytest.raises(SystemExit) as exit_info:
            runpy.run_module("pqc_bench.constant_time.binary_auditor", run_name="__main__")
    assert exit_info.value.code == 0
    assert json.loads(capsys.readouterr().out)["analysis"] == "local_elf_static_instruction_review"


@pytest.mark.parametrize("root", ["", "\x00"])
def test_invalid_root_argument_is_a_clear_error(tmp_path, root):
    path = save_elf(tmp_path)
    with pytest.raises(auditor.BinaryAuditError):
        auditor.audit_binary(path, project_root=root)


def test_invalid_program_header_table_is_rejected(tmp_path):
    path = save_elf(tmp_path)
    path.write_bytes(patch_header(path.read_bytes(), "phnum", 1))
    with pytest.raises(auditor.BinaryAuditError, match="program header table"):
        auditor.audit_binary(path, project_root=tmp_path)


def test_instruction_budget_is_global_across_sections(tmp_path, monkeypatch):
    path = save_elf(tmp_path, code=b"\x90\x90")
    path.write_bytes(patch_section(path.read_bytes(), 2, "flags", 6))
    monkeypatch.setattr(auditor, "MAX_INSTRUCTIONS", 2)
    report = auditor.audit_binary(path, project_root=tmp_path)
    assert report["instruction_count"] == 2
    assert report["sections"][0]["decode_complete"] is True
    assert report["sections"][1]["decoded_bytes"] == 0
    assert report["sections"][1]["incomplete_reason"] == "instruction_limit"
    assert report["status"] == "incomplete"
