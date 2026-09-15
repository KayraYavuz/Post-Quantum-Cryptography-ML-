#!/usr/bin/env python3
"""
Matrix Runner for Fixed-Time Verification (WS-G.1)

Builds and evaluates the compiler matrix:
  {gcc, clang} x {-O0, -O1, -Os} x {x86_64, aarch64}

Attempts to build KyberSlash, Clangover, and mlkem-native references
across the full matrix for fixed-time analysis.
"""

import subprocess
import sys
import json
from pathlib import Path
from itertools import product

# --- Compiler Matrix Definition ---
# {gcc, clang} x {-O0, -O1, -Os} x {x86_64, aarch64}
COMPILER_MATRIX = [
    {"cc": "gcc", "cflags": ["-O0", "-O1", "-Os"], "arch": ["x86_64", "aarch64"]},
    {"cc": "clang", "cflags": ["-O0", "-O1", "-Os"], "arch": ["x86_64", "aarch64"]},
]

# Reference packages to attempt building
REFERENCES = [
    "mlkem-native",
    "clangover",  # placeholder/CVE-2024-37880 regression wrapper
    "kyberslash", # placeholder/alternative implementation
]

# Working base directory (relative to repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def build_reference(reference: str, cc: str, cflag: str, arch: str) -> dict:
    """
    Attempt to build a reference implementation for a given matrix cell.
    Returns a status dict with success/failure and relevant output.
    """
    result = {
        "reference": reference,
        "compiler": cc,
        "flag": cflag,
        "arch": arch,
        "status": "skipped",
        "output": "",
        "error": "",
    }

    # Construct a minimal build command based on reference type
    build_cmd = []
    if reference == "mlkem-native":
        src_dir = REPO_ROOT / "third_party" / "mlkem-native"
        if not src_dir.exists():
            result["status"] = "skipped"
            result["error"] = f"mlkem-native source not found at {src_dir}"
            return result
        build_cmd = ["make", f"CC={cc}", f"CFLAGS={cflag}"]
        if arch == "aarch64":
            build_cmd.append("ARCH=ARM")
    elif reference == "clangover":
        # Placeholder: simulate CVE-2024-37880 regression test build
        result["status"] = "simulated"
        result["output"] = f"Clangover regression build configured: {cc} {cflag} {arch}"
        return result
    elif reference == "kyberslash":
        # Placeholder: KyberSlash build script
        result["status"] = "skipped"
        result["error"] = "KyberSlash build not yet integrated in this workspace"
        return result

    if build_cmd:
        try:
            proc = subprocess.run(
                build_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(src_dir) if src_dir else ".",
            )
            result["output"] = proc.stdout[-200:] if proc.stdout else ""
            result["error"] = proc.stderr[-200:] if proc.stderr else ""
            if proc.returncode == 0:
                result["status"] = "success"
            else:
                result["status"] = "failed"
                result["error"] += f" (exit code: {proc.returncode})"
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = "Build timed out after 120s"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

    return result


def run_matrix():
    """Iterate the full compiler matrix and attempt builds for all references."""
    results = []
    for cell in COMPILER_MATRIX:
        cc = cell["cc"]
        for cflag in cell["cflags"]:
            for arch in cell["arch"]:
                for ref in REFERENCES:
                    r = build_reference(ref, cc, cflag, arch)
                    r["matrix_cell"] = f"{cc} {cflag} {arch}"
                    results.append(r)
    return results


if __name__ == "__main__":
    if "--build-matrix" in sys.argv:
        results = run_matrix()
        # Output as JSON for downstream consumption (Kueue, dashboards, etc.)
        print(json.dumps({
            "matrix": [
                {
                    "compiler": r["compiler"],
                    "flag": r["flag"],
                    "arch": r["arch"],
                    "reference": r["reference"],
                    "status": r["status"],
                    "output": r["output"],
                    "error": r["error"],
                }
                for r in results
            ],
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] in ("failed", "error", "timeout")),
        }))
    else:
        print("Usage: python -m pqc_bench.constant_time.matrix_runner --build-matrix")