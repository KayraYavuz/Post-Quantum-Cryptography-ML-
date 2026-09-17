"""Read-only local prerequisite discovery; never executes QEMU or guest firmware.

Executable lookup is not toolchain validation. This module cannot produce a
benchmark result, even if every prerequisite is found on PATH.
"""
from __future__ import annotations

import json
import shutil
from typing import Any

REQUIRED_TOOLS = (
    "qemu-system-arm", "arm-none-eabi-gcc", "arm-none-eabi-objcopy",
    "arm-none-eabi-size", "make",
)
METRICS = (
    "host_elapsed_ns", "guest_virtual_time_ns", "guest_instruction_count",
    "hardware_cycles", "stack_high_water_bytes", "firmware_size_bytes",
)
LIMITATIONS = (
    "PATH lookup only: versions, tool behavior and local board/CPU support are unverified.",
    "QEMU icount and virtual time are not Cortex-M4 hardware cycles.",
    "No firmware was built or run; no benchmark, stack or code-size measurement exists.",
    "Documented mps2-an386 support does not establish local runtime support.",
    "No network, service, device, trace capture or attack integration is provided.",
)


def _report(availability: dict[str, bool | None], evidence: str) -> dict[str, Any]:
    if type(availability) is not dict or set(availability) != set(REQUIRED_TOOLS):
        raise ValueError("availability must contain exactly the required tool names")
    if any(value is not None and type(value) is not bool for value in availability.values()):
        raise ValueError("tool availability must be bool or null (unknown)")
    missing = [name for name in REQUIRED_TOOLS if availability[name] is False]
    unknown = [name for name in REQUIRED_TOOLS if availability[name] is None]
    status = (
        "blocked_missing_tools" if missing else
        "unresolved_tool_discovery" if unknown else
        "prerequisites_unverified"
    )
    return {
        "schema_version": 1,
        "scope": "project_local_functional_benchmark_feasibility",
        "status": status,
        "evidence": evidence,
        "tools": {
            name: ("unknown" if availability[name] is None else
                   "found_on_path" if availability[name] else "not_found_on_path")
            for name in REQUIRED_TOOLS
        },
        "missing_tools": missing,
        "unknown_tools": unknown,
        "target": {
            "board": "mps2-an386",
            "cpu": "cortex-m4",
            "upstream_documented_support": True,
            "local_runtime_support": "not_verified",
        },
        "remaining_checks": [
            "tool_versions_and_board_cpu_support",
            "pinned_implementation_and_build_dependencies",
            "project_owned_firmware_build_and_functional_test",
            "bounded_offline_runner_not_implemented",
        ],
        "execution_status": "not_run",
        "metrics": {name: None for name in METRICS},
        "unmeasured_metrics": list(METRICS),
        "limitations": list(LIMITATIONS),
    }


def assess_toolchain(availability: dict[str, bool | None]) -> dict[str, Any]:
    """Assess exact caller assertions, including explicit unknowns; no I/O.

    True means claimed executable presence only, never a working toolchain.
    The returned data owns its containers and does not retain caller input.
    """
    return _report(availability, "caller_attested_tool_discovery")


def inspect_local_tools() -> dict[str, Any]:
    """Look up five fixed executable names without running any of them.

    Lookup errors remain unknown rather than being reported as absent. Only
    presence is retained: local paths/environment values are not exported.
    """
    availability: dict[str, bool | None] = {}
    for name in REQUIRED_TOOLS:
        try:
            availability[name] = shutil.which(name) is not None
        except OSError:
            availability[name] = None
    return _report(availability, "local_path_lookup")


def main() -> None:
    """Print the current local discovery report as deterministic JSON."""
    print(json.dumps(inspect_local_tools(), sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
