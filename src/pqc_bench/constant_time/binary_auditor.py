"""WS-P5.3: bounded, local ELF instruction review (never a timing verdict).

Only project-contained x86 ELF executable sections are linearly decoded. Inputs
are read as data, never loaded or executed. Section contents can include inline
data, and linear decoding does not establish reachability, secret dependence,
or runtime timing. Absence of findings does not establish constant-time behavior.

Run: python -m pqc_bench.constant_time.binary_auditor PATH --project-root ROOT
"""

from __future__ import annotations

import argparse
import io
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_SECTIONS = 256
MAX_EXECUTABLE_BYTES = 4 * 1024 * 1024
MAX_INSTRUCTIONS = 200_000
MAX_FINDINGS = 1_000
DISCLAIMER = (
    "Static linear instruction review only; findings require human review. "
    "This is neither a leakage finding nor a constant-time verdict. Inline data, "
    "instruction boundaries, reachability, and runtime timing are not established."
)


class BinaryAuditError(ValueError):
    """Rejected input or unavailable analysis dependency; no successful report."""


def _read_local(path: str | Path, project_root: str | Path) -> tuple[Path, bytes]:
    """Resolve containment, then walk without following replacement symlinks."""
    descriptors: list[int] = []
    try:
        if not str(project_root).strip():
            raise BinaryAuditError("project_root must be an explicit existing directory")
        root = Path(project_root).resolve(strict=True)
        target = Path(path).resolve(strict=True)
        if not root.is_dir():
            raise BinaryAuditError("project_root must be an existing directory")
        try:
            relative = target.relative_to(root)
        except ValueError as exc:
            raise BinaryAuditError("input must resolve inside project_root") from exc
        if not relative.parts:
            raise BinaryAuditError("input must be a regular file")
        # Nonblocking open prevents a raced-in FIFO from blocking before fstat.
        # Walking from / also refuses symlink substitutions in root ancestors.
        if not all(hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")):
            raise BinaryAuditError("safe local file opening is unsupported on this platform")
        fd = os.open(target.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(fd)
        for component in target.parts[1:-1]:
            fd = os.open(
                component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
            )
            descriptors.append(fd)
        fd = os.open(
            target.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd
        )
        descriptors.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise BinaryAuditError("input must be a regular file")
        if before.st_size > MAX_FILE_BYTES:
            raise BinaryAuditError(f"input exceeds {MAX_FILE_BYTES} byte limit")
        chunks: list[bytes] = []
        remaining = MAX_FILE_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(fd)
        if len(data) > MAX_FILE_BYTES:
            raise BinaryAuditError(f"input exceeds {MAX_FILE_BYTES} byte limit")
        if (
            len(data) != before.st_size
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
        ):
            raise BinaryAuditError("input changed while being read")
        return relative, data
    except BinaryAuditError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise BinaryAuditError(f"cannot read local input: {exc}") from exc
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def _elf_sections(data: bytes) -> tuple[int, str, list[dict[str, Any]]]:
    try:
        from elftools.elf.elffile import ELFFile
    except ImportError as exc:
        raise BinaryAuditError("pyelftools is required for ELF review") from exc

    try:
        elf = ELFFile(io.BytesIO(data))
        bits = elf.elfclass
        machine = elf.header["e_machine"]
        if not elf.little_endian:
            raise BinaryAuditError("only little-endian ELF is supported")
        if (bits, machine) not in ((32, "EM_386"), (64, "EM_X86_64")):
            raise BinaryAuditError("only ELF x86 (32-bit) and x86_64 (64-bit) are supported")
        elf_type = elf.header["e_type"]
        if elf_type not in ("ET_REL", "ET_EXEC", "ET_DYN"):
            raise BinaryAuditError("only ET_REL, ET_EXEC, and ET_DYN ELF types are supported")
        header_size, entry_size = (52, 40) if bits == 32 else (64, 64)
        if (
            elf.header["e_ehsize"] != header_size
            or elf.header["e_version"] != "EV_CURRENT"
            or data[6] != 1
        ):
            raise BinaryAuditError("invalid ELF header size or version")
        program_count = elf.header["e_phnum"]
        if program_count:
            program_size = 32 if bits == 32 else 56
            program_offset = elf.header["e_phoff"]
            if (
                program_count > MAX_SECTIONS
                or elf.header["e_phentsize"] != program_size
                or program_offset < header_size
                or program_offset + program_count * program_size > len(data)
            ):
                raise BinaryAuditError("invalid or excessive program header table")
        count = elf.header["e_shnum"]
        table_offset = elf.header["e_shoff"]
        if not 1 <= count <= MAX_SECTIONS:
            raise BinaryAuditError(
                "missing or excessive section table (extended counts unsupported)"
            )
        if (
            elf.header["e_shentsize"] != entry_size
            or table_offset < header_size
            or table_offset + count * entry_size > len(data)
        ):
            raise BinaryAuditError("invalid or truncated section table")
        # Parse only bounded section headers: do not interpret dynamic tables,
        # symbols, relocations, or compressed contents of unrelated sections.
        headers = [
            elf.structs.Elf_Shdr.parse(data[start : start + entry_size])
            for start in range(table_offset, table_offset + count * entry_size, entry_size)
        ]
        if headers[0]["sh_type"] != "SHT_NULL":
            raise BinaryAuditError("invalid ELF null section")
        names_index = elf.header["e_shstrndx"]
        if not isinstance(names_index, int) or not 0 <= names_index < count:
            raise BinaryAuditError("invalid section name table index")
        names = b""
        if names_index:
            name_header = headers[names_index]
            start, size = name_header["sh_offset"], name_header["sh_size"]
            if name_header["sh_type"] != "SHT_STRTAB" or start + size > len(data):
                raise BinaryAuditError("invalid section name table")
            names = data[start : start + size]
            if not names or names[0] != 0 or names[-1] != 0:
                raise BinaryAuditError("invalid section name table strings")
        executable = []
        total_bytes = 0
        for index, header in enumerate(headers):
            start, size = header["sh_offset"], header["sh_size"]
            if header["sh_type"] not in ("SHT_NULL", "SHT_NOBITS") and start + size > len(data):
                raise BinaryAuditError("section extends beyond input")
            name_offset = header["sh_name"]
            if name_offset and (not names or name_offset >= len(names)):
                raise BinaryAuditError("invalid section name offset")
            if not header["sh_flags"] & 0x4:  # SHF_EXECINSTR
                continue
            if (
                index == 0
                or header["sh_type"] != "SHT_PROGBITS"
                or header["sh_flags"] & 0x800  # ELF compressed section flag
                or size == 0
                or start < header_size
                or start + size > len(data)
                or header["sh_addr"] + size > 1 << bits
                or (start < table_offset + count * entry_size and start + size > table_offset)
            ):
                raise BinaryAuditError("invalid executable section")
            alignment = header["sh_addralign"]
            if alignment and alignment & (alignment - 1):
                raise BinaryAuditError("invalid executable section alignment")
            if any(
                start < s["file_offset"] + s["size"] and start + size > s["file_offset"]
                for s in executable
            ):
                raise BinaryAuditError("overlapping executable sections")
            total_bytes += size
            if total_bytes > MAX_EXECUTABLE_BYTES:
                raise BinaryAuditError("executable section bytes exceed review limit")
            # Names are descriptive only; index is the stable identifier.
            name = names[name_offset : name_offset + 128].split(b"\0", 1)[0]
            executable.append({
                "index": index,
                "name": name.decode("utf-8", errors="replace"),
                "file_offset": start,
                "address": header["sh_addr"],
                "size": size,
            })
        if not executable:
            raise BinaryAuditError("ELF has no executable sections")
        return bits, elf_type, executable
    except BinaryAuditError:
        raise
    except Exception as exc:
        # Parser failures must not masquerade as zero findings.
        raise BinaryAuditError("malformed or truncated ELF input") from exc


def audit_binary(path: str | Path, *, project_root: str | Path) -> dict[str, Any]:
    """Review a project-owned ELF; raise BinaryAuditError on rejected inputs.

    PATH is resolved relative to the caller's working directory, not ROOT.
    ROOT is mandatory and is a filesystem scope, not proof of ownership.
    Internal symlinks are allowed only when their resolved target stays in ROOT.
    Limits are fixed module constants. Incomplete decoding/budget exhaustion
    yields status='incomplete'; zero findings is never a security verdict.
    """
    relative, data = _read_local(path, project_root)
    bits, elf_type, sections = _elf_sections(data)
    try:
        from capstone import CS_ARCH_X86, CS_MODE_32, CS_MODE_64, Cs
        from capstone.x86_const import X86_INS_DIV, X86_INS_IDIV
    except ImportError as exc:
        raise BinaryAuditError("capstone is required for instruction review") from exc

    decoder = Cs(CS_ARCH_X86, CS_MODE_32 if bits == 32 else CS_MODE_64)
    decoder.skipdata = False
    findings: list[dict[str, Any]] = []
    instruction_count = 0
    finding_count = 0
    for section in sections:
        start = section["file_offset"]
        decoded = 0
        section_instructions = 0
        reason = None
        try:
            for instruction in decoder.disasm(
                data[start : start + section["size"]],
                section["address"],
                # Capstone allocates its decode batch before yielding results.
                # Bound that batch as well as the Python-side instruction loop.
                count=max(1, MAX_INSTRUCTIONS - instruction_count + 1),
            ):
                if instruction_count >= MAX_INSTRUCTIONS:
                    reason = "instruction_limit"
                    break
                instruction_count += 1
                section_instructions += 1
                if instruction.id in (X86_INS_DIV, X86_INS_IDIV):
                    finding_count += 1
                    if len(findings) < MAX_FINDINGS:
                        findings.append({
                            "kind": "division_instruction_review",
                            "section_index": section["index"],
                            "section_offset": decoded,
                            "file_offset": start + decoded,
                            "address": instruction.address,
                            "mnemonic": instruction.mnemonic,
                            "operands": instruction.op_str,
                            "instruction_bytes": instruction.bytes.hex(),
                            "message": "Integer division instruction; human review required.",
                        })
                decoded += instruction.size
        except Exception as exc:
            raise BinaryAuditError("instruction decoder failed") from exc
        if decoded != section["size"] and reason is None:
            reason = "decode_stopped"
        section.update({
            "decoded_bytes": decoded,
            "instruction_count": section_instructions,
            "decode_complete": decoded == section["size"],
            "incomplete_reason": reason,
            "unexamined_bytes": section["size"] - decoded,
            "stop_section_offset": decoded if reason else None,
        })
    scan_complete = all(section["decode_complete"] for section in sections)
    findings_truncated = finding_count > len(findings)
    return {
        "schema_version": 1,
        "analysis": "local_elf_static_instruction_review",
        "input": str(relative),
        "architecture": "x86" if bits == 32 else "x86_64",
        "elf_type": elf_type,
        "status": "complete" if scan_complete and not findings_truncated else "incomplete",
        "scan_complete": scan_complete,
        "disclaimer": DISCLAIMER,
        "instruction_count": instruction_count,
        "finding_count": finding_count,
        "findings_truncated": findings_truncated,
        "findings": findings,
        "sections": sections,
        "limits": {
            "file_bytes": MAX_FILE_BYTES,
            "sections": MAX_SECTIONS,
            "executable_bytes": MAX_EXECUTABLE_BYTES,
            "instructions": MAX_INSTRUCTIONS,
            "findings": MAX_FINDINGS,
        },
    }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise BinaryAuditError(message)


def main(argv: list[str] | None = None) -> int:
    """JSON CLI: exit 0 complete, 1 incomplete, 2 rejected input/arguments."""
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("path", help="local project-owned ELF file (never executed)")
    parser.add_argument("--project-root", required=True, help="explicit allowed project directory")
    try:
        args = parser.parse_args(argv)
        report = audit_binary(args.path, project_root=args.project_root)
    except BinaryAuditError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stdout)
        return 2
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
