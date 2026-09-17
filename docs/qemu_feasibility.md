# WS-P8.1 — Cortex-M4 emulation feasibility and measurement contract

## Verdict (2026-09-17)

**Feasibility assessment complete; local emulation blocked by missing tools.**
No ARM firmware was compiled, no QEMU guest was executed, and no hardware or
emulator benchmark was measured. P8.1 completes the assessment, not the originally
suggested cycle-level hardware measurements. Development can proceed to P8.2
without relabeling this missing execution as a successful benchmark.

Read-only `command -v` checks found none of `qemu-system-arm`, `qemu-arm`,
`arm-none-eabi-gcc`, `arm-none-eabi-gdb`, `arm-none-eabi-objcopy`,
`arm-none-eabi-size`, `clang`, `gcc`, `make`, `cmake`, or `ninja` on PATH.
Python 3.11.2 was available at `/usr/bin/python3`. Its build-version string
mentions GCC, but that does not mean a compiler is installed. These observations
are PATH checks, not a filesystem-wide proof of absence. No packages were installed.

## Existing projects and primary-source findings

The following public upstream pages were read on 2026-09-17. They are moving
upstream documentation, not pinned or locally tested dependencies:

- [QEMU MPS2/MPS3 documentation](https://www.qemu.org/docs/master/system/arm/mps2.html)
  maps `mps2-an386` to Cortex-M4 (AN386). `mps2-an385` is Cortex-M3, not M4.
  AN386 low-memory remapping is not implemented exactly as on real hardware.
  Documented support does not prove that an absent local QEMU build supports it.
- [QEMU TCG instruction counting](https://www.qemu.org/docs/master/devel/tcg-icount.html)
  explicitly states that icount is not cycle-accurate emulation. It counts guest
  instructions and can drive virtual time; neither is physical M4 cycle timing.
- [pqm4 README](https://github.com/mupq/pqm4/blob/master/README.md) documents the
  `mps2-an386` QEMU platform (QEMU >=5.2), the GNU Arm bare-metal toolchain,
  build dependencies and stack/functionality testing. It explicitly calls QEMU
  cycle counts meaningless. Crucially, its current deprecation notice says
  **no active maintenance**, with read-only archiving planned in or after January
  2027. Do not represent pqm4 as a newly maintained dependency.
- That notice recommends [mlkem-native](https://github.com/pq-code-package/mlkem-native)
  and [mldsa-native](https://github.com/pq-code-package/mldsa-native). Their current
  READMEs were read: both offer portable C implementations under PQ Code Package.
  Listed native Arm backends are AArch64, not evidence of Cortex-M4 support.
  They are candidates for a future portable-C harness, not verified drop-in
  replacements for pqm4's board layer or M4 assembly.

No third-party cryptographic implementation was vendored or executed. Existing
QEMU/upstream benchmark frameworks are preferable to a custom emulator. Only a
small stdlib prerequisite/report adapter is added now; no new dependency.
The web search provider returned quota error 429; direct primary-source reads
succeeded. No unverified search result is used as evidence.

## Selected scope and deferred execution

The future eligible workload is one project-owned local functional smoke test
and ordinary ML-KEM-768 benchmark with generated test data, on the documented
MPS2 AN386 target. No service, network, secret-key recovery, fault injection,
trace collection or attack integration belongs to this step. No arbitrary
firmware launcher or output parser is supplied without a toolchain and validated
output fixture. There is no claimed pqm4 console-format compatibility.

Reopening execution requires verifying tool versions and actual board/CPU support,
pinning a selected implementation and its build dependencies, and building and
checking the project-owned image before accepting any result. Any later runner
must bound runtime and output, disable network/monitor/debug interfaces, avoid
host-access semihosting, and record provenance and exit status. Those controls
are requirements for deferred work, not implemented features here.

## Current API

```python
from pqc_bench.qemu_feasibility import inspect_local_tools, assess_toolchain
report = inspect_local_tools()  # shutil.which for five fixed names only
```

`python3 -m pqc_bench.qemu_feasibility` emits sorted JSON to stdout and performs
no executable launch, network access or file write. Its exit status indicates
successful report generation, **not toolchain readiness**; inspect `status`.
`assess_toolchain` accepts exactly the five required tool keys, each with a
strict boolean or `None`. It is an in-memory, caller-attested fixture/report API;
it does not authenticate assertions. `True` only claims PATH presence.

Statuses:
- `blocked_missing_tools`: at least one explicitly absent tool;
- `unresolved_tool_discovery`: no absent tool but at least one unknown lookup;
- `prerequisites_unverified`: all found, still **not ready or validated**.

Lookup `OSError` becomes unknown, not absent; tool paths and error strings are
not exported. Reports explicitly distinguish local lookup from caller assertions.
They always include `execution_status: not_run` and local support `not_verified`.

## Metrics: never interchangeable

All current values are JSON `null` and listed in `unmeasured_metrics`.
There is no API for inserting measured values in this feasibility report.

| Metric | Meaning if measured in future | Current status |
|---|---|---|
| `host_elapsed_ns` | Host monotonic duration including defined runner overhead; not hardware latency | unmeasured |
| `guest_virtual_time_ns` | QEMU virtual-clock delta under recorded settings; not wall time or cycles | unmeasured |
| `guest_instruction_count` | Guest instructions in a defined interval, if supported and instrumented | unmeasured |
| `hardware_cycles` | Real device counter with verified semantics and scope; cannot derive from QEMU | unmeasured |
| `stack_high_water_bytes` | Defined guest stack watermark, not total device RAM or host RSS | unmeasured |
| `firmware_size_bytes` | Explicit artifact/section size, not execution memory or stack | unmeasured |

DWT CYCCNT behavior has not been verified locally; an emulated register or a
pqm4 output labeled cycles must never be promoted to real hardware cycles.
Functional agreement is not timing validation, certification, or side-channel
resistance evidence. No cross-platform speed ratio or physical frequency conversion
is justified by this assessment.

## Verification

`python3 -m pytest -q tests/test_qemu_feasibility.py` uses fixed CPU fixtures,
including every combination of present/absent/unknown for the five tools, strict
input rejection, lookup error handling, path redaction, report isolation and JSON
repeatability. These tests verify the adapter only, not QEMU or ARM firmware.
The observed local discovery report is saved at
`artifacts/qemu_feasibility/local_tools_2026-09-17.json`; it records this environment,
not a reusable successful benchmark. Test results and publication outcomes are
recorded in `RUN_LOG.md` and `PROJECT_STATE.md`.
