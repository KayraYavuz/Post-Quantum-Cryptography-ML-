# WS-P7.4 — Offline executive report

`pqc_bench.executive_report` produces deterministic Markdown and standalone,
printable HTML from bounded excerpts of existing local module outputs. It does
not execute those modules, open files, fetch URLs, start a service, or contact a
laboratory. Missing sections are retained and missing fields display
`unmeasured`, not zero or success. Overall status is always `not_verified`.

## Existing solutions and format choice

The existing `cbom.report_exporter` is unsuitable for this scope: it uses a clock,
reads artifacts implicitly, and uses audit/certification language. This exporter
is isolated from it and does not change existing service behavior. Python's
standard `json`, `html` and `hashlib` libraries suffice; no new dependency is
added. ReportLab, WeasyPrint, Pandoc and wkhtmltopdf were not installed when this
step was implemented. No PDF renderer was installed or external service used;
the supported formats are Markdown and printable HTML. Browser print pagination
and PDF output were not visually verified. CSS uses separate FIPS gap rows to
avoid a single multi-page JSON cell.

## API and reproducible local example

```python
from pathlib import Path
from pqc_bench.executive_report import load_request, report_markdown, report_html

# File I/O belongs to the caller; pass only an explicitly selected local manifest.
source = Path("tests/fixtures/executive_report/manifest.json")
request = load_request(source.read_text(encoding="utf-8"))
Path("executive.md").write_text(report_markdown(request), encoding="utf-8")
Path("executive.html").write_text(report_html(request), encoding="utf-8")
```

`build_report(request)` returns a detached normalized dictionary. All renderers
validate the original manifest, not a previously built report. Equal inputs give
identical bytes; dictionary order and FIPS gap order do not change output.
List order elsewhere is not part of this schema.

The committed `tests/fixtures/executive_report/expected.md` and `expected.html`
are fixed example reports. **All fixture sections are labeled synthetic**:
security/quantum values come from static module tables; FIPS comes from a fixed
no-document request; the TLS `SimulationResult` is fabricated, not timed; CBOM,
PKI and static scan values are explicitly fabricated examples. These fixtures
are not evidence of a successful real handshake, certificate validation, ELF
scan, or policy review.

## Manifest and native output mapping

Root fields are exactly `schema_version: 1`, `title` and `sections`. The latter
contains zero or more of the seven fixed IDs below. Each supplied section has
exactly `input_file`, `output_file`, `evidence_kind`, `output`. References are
relative local file locators, not clickable links. `evidence_kind` is one of
`synthetic_fixture` or `local_output_excerpt`; neither authenticates evidence.
The module identity is fixed by section and cannot be caller-overridden.

`output` is an **allowlisted projection**, not an entire native output. Omit or
set a field to null when it is unavailable. Unknown fields, including key
material, are rejected rather than silently copied into a management report.

| Section | Source module/API | Projection into output |
|---|---|---|
| security | `security_estimation.lattice_runner.estimate_security` | `scheme`, `classical_security_bits`, `quantum_security_bits` |
| quantum | `quantum_cost.estimate_quantum_resources` | `scheme`, `logical_qubits`, `t_gate_count`, `t_depth`, `physical_qubits`, `runtime_seconds` |
| cbom | `cbom.policy.generate_policy_report` | `bom_evaluation.cNSA_2_0.overall_status` → `cNSA_2_0_status`; `bom_evaluation.nist_sp_800_208.overall_status` → `nist_sp_800_208_status` |
| constant_time | `constant_time.binary_auditor.audit_binary` | `status`, `finding_count`, `instruction_count`, `scan_complete`, `findings_truncated` |
| pki | `pki.hybrid_certs.verify_chain` | Caller-recorded `chain_verified` boolean; see below |
| tls | `tls_simulator.SimulationResult.to_report` | `local_duration_ns`, `client_application_match`, `server_application_match` |
| fips | `fips_evidence.build_matrix` | `overall_status`, `gaps` (objects with `field`, `code`) |

For each section, `input_file` identifies the retained parameter request, BOM,
ELF, or local validation manifest; `output_file` identifies the retained full
module output/validation record. A combined fixture file is allowed, with the
section ID selecting its relevant entry. The exporter **does not read, execute,
existence-check, or authenticate either file**. SHA-256 binds only the canonical
normalized excerpt (sorted keys, ASCII JSON, compact separators); it is not a
file digest, signature, or proof of module execution. Keep both underlying
files to audit the caller's assertions.

PKI has no native JSON report: `verify_chain` returns `None` on success and
raises `HybridValidationError` on rejection. Record `chain_verified=True` only
after a successful call, False for that explicit validation rejection, and
omit/null for no call or an unavailable result. Do not use
`bool(verify_chain(...))` and do not turn arbitrary runtime exceptions into
recorded validation failures. Persist the explicit validation inputs, time and
trust-pin reference locally, never private keys. This report adds no PKI runner.

## Claim limits

- Static security tables are not fresh lattice-estimator measurements or a
  calibrated ±2-bit result. Quantum values are placeholders, not a tool run or
  hardware observations.
- Two CBOM statuses are separately labeled **legacy heuristic labels**. The
  existing evaluator's NIST/CNSA mappings are not normative compliance evidence;
  exporting a `compliant` label never upgrades the overall report status.
- Static division findings, including zero findings, prove neither leakage nor
  constant-time behavior. Incomplete scans remain incomplete.
- PKI is an experimental local envelope; TLS is a custom offline handshake
  model. Supplied TLS duration is caller-recorded local elapsed time, not RTT.
- FIPS remains `not_verified` even with no supplied gaps. Document authenticity,
  current CMVP status and deployed runtime mode are never verified here.
- Production security, attack resistance, hardware cycles, network RTT and FIPS
  module validation always remain explicitly unmeasured. There is no aggregate
  score, certification, deployment readiness or attack-success assessment.

## Validation and rendering

Plain dictionaries only; reject missing/unknown keys, duplicate JSON keys,
nonfinite values, control/format characters, invalid enums, bool-as-number,
negative numbers, noninteger counts and traversal/absolute/URL locators. Numbers
are capped at 10^30; text at 512 characters (derived FIPS gap fields at 550),
FIPS gap arrays at 512 unique items. JSON input and canonical normalized report
each have a 65,536-byte limit. Larger native matrices require an explicitly
scoped excerpt; retain the full source and do not label excerpts exhaustive.
Contradictory scan flags/counts are rejected when enough fields are available.

Markdown encodes caller punctuation as entities. HTML uses `html.escape`, a
fixed template, static print CSS, and a restrictive CSP; there are no active
links, scripts, remote assets, user CSS or template evaluation. No inputs are
executed. Validation does not establish that caller-provided facts are true.

## CPU verification

```sh
python3 -m pytest -q tests/test_executive_report.py
python3 -m pytest -q
```

Tests cover native table/FIPS projections, deterministic snapshots, ordering,
source references, excerpt fingerprints, absent/zero/false values, input
rejection, Unicode controls, HTML/Markdown escaping, separate printable gap
rows, maximum-length native document IDs, size limits and no file reads.
No network, service, hardware or laboratory integration is tested or claimed.
