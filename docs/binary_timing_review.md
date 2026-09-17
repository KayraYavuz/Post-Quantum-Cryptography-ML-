# WS-P5.3 — Local ELF static instruction review

This is a **defensive review aid**, not a leakage detector, exploit, timing measurement,
or constant-time certification. Only inspect files built and owned by your project.
No input binary is executed, dynamically loaded, or submitted to a remote service.
There is deliberately no upload API or network/directory scanner.

## Existing tools evaluated

- **GNU binutils (`objdump`/`readelf`)** provide established ELF inspection, but are
  not installed in the current environment. Subprocess invocation and parsing
  version-dependent text would add an unnecessary interface here.
- **pyelftools** supplies established ELF header/section parsing in Python.
- **Capstone** supplies instruction-boundary-aware x86 decoding. Matching raw
  byte sequences or searching text for `div` would misidentify data/immediates.

The implementation composes pyelftools and Capstone rather than implementing an
ELF parser or instruction decoder. Dependencies are declared in `pyproject.toml`:
`pyelftools>=0.32,<1`, `capstone>=5.0.3,<6`.

## Usage

From an installed checkout, or with `PYTHONPATH=src`:

```sh
PYTHONPATH=src python3 -m pqc_bench.constant_time.binary_auditor \
  ./artifacts/my-project-build.so --project-root .
```

The example path must be replaced with an existing **project-owned** build output;
no third-party binary is bundled or scanned by this command example.
`PATH` is relative to the current working directory, **not** `--project-root`.

Python interface:

```python
from pqc_bench.constant_time.binary_auditor import audit_binary, BinaryAuditError

report = audit_binary("./artifacts/my-project-build.so", project_root=".")
```

`project_root` is mandatory. Resolved file paths must remain inside it. This is a
filesystem scope, not proof of ownership or a sandbox for hostile files. Internal
symlinks can resolve within the scope; escaping symlinks, nonregular files, and
files changed during reading are rejected. Safe opening requires POSIX directory
file descriptors and no-follow/nonblocking flags; unsupported platforms reject.
Keep the root narrow; do not supply `/` or copy third-party targets into the scope.

## Supported scope

- Little-endian x86 ELF32 and x86-64 ELF64.
- ELF types `ET_REL`, `ET_EXEC`, and `ET_DYN` (including shared objects).
- Nonempty, uncompressed executable `SHT_PROGBITS` sections, linearly decoded.
- Integer `div` and `idiv` instructions produce `division_instruction_review`
  entries with section-relative and file offsets, address, bytes and operands.
  Addresses in relocatable objects are not runtime addresses.
- Fixed budgets: 8 MiB input, 256 section headers, 4 MiB executable section bytes,
  200,000 decoded instructions and 1,000 retained findings.

Files without usable section tables, extended section counts, unsupported
architectures, malformed/truncated sections, and overlapping executable sections
are rejected rather than reported as clean. Compressed executable sections are
not decompressed. Non-executable data sections are not scanned for instructions.

## Report and exit semantics

The CLI prints JSON to stdout:

- **Exit 0 / `status: complete`**: selected sections decoded and all findings fit
  the reporting budget. This does **not** mean that code is safe or constant-time.
- **Exit 1 / `status: incomplete`**: decoding stopped, the instruction budget was
  exhausted, or findings were truncated. Inspect per-section `incomplete_reason`,
  `unexamined_bytes`, `stop_section_offset`, and `findings_truncated`.
- **Exit 2 / `status: error`**: rejected input, arguments, unavailable dependency,
  or parser/decoder failure. No successful audit claim is made.

`finding_count` counts matching instructions among those decoded; it is not an
estimate for unexamined bytes. `scan_complete` describes decoding only, while
`status` also accounts for truncated findings. Every successful report contains
an explicit disclaimer, even when there are zero findings.

## Limits of interpretation

Division latency depends on the processor and operands. A division instruction
alone does not establish secret dependence, a vulnerability, or measurable leakage.
Zero division findings do not prove constant-time behavior: branches, memory access,
caches, speculation, other instructions, callers and runtime conditions are outside
scope. Linear decoding cannot establish reachability or distinguish inline data in
executable sections from real code. Relocations, dynamic loading and program-header
mapping are not analyzed; section decoding is not an ELF loader-validity check.

## Tests

```sh
PYTHONPATH=src python3 -m pytest tests/test_binary_auditor.py -q
python3 -m pytest -q
```

Tests build tiny, inert, project-authored ELF fixtures with Python `struct` in
pytest temporary directories. They are only read as bytes, never executed. These
fixtures validate parser/decode/report behavior, not production crypto, real
compiler output, microarchitectural timing, or hardware leakage.
