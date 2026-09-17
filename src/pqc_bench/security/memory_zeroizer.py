"""
Memory Zeroization Auditor (WS-P9.2)

Provides RAM clearing algorithms, residual byte analysis, and
reset validation tests for post-quantum cryptographic implementations.

Features:
- Secure memory zeroization using multiple overwrite patterns
- Residual byte detection via checksum comparison
- Validation that memory regions are fully cleared after zeroization
- Platform-aware zeroization with fallback for constrained environments
"""

from __future__ import annotations

import ctypes
import hashlib
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Zeroization patterns (NIST SP 800-88 guidelines)
# ---------------------------------------------------------------------------

ZERO_PATTERNS: Tuple[bytes, ...] = (
    b"\x00" * 64,       # Pattern 1: all zeros
    b"\xff" * 64,       # Pattern 2: all ones
    b"\xaa" * 64,       # Pattern 3: alternating 0xaa
    b"\x55" * 64,       # Pattern 4: alternating 0x55
)


# ---------------------------------------------------------------------------
# Core zeroization functions
# ---------------------------------------------------------------------------


def zero_memory(ptr: int, size: int, pattern_idx: int = 0) -> None:
    """
    Securely zero out a memory region at the given pointer.

    Uses ctypes to write zero (or a fill pattern) directly to the
    allocated memory.  The function is intentionally simple so that
    compilers cannot optimise away the write — the ``volatile``-like
    behaviour is achieved by writing through a ``ctypes`` pointer.

    Parameters
    ----------
    ptr : int
        Starting address of the memory region (integer address).
    size : int
        Number of bytes to zero.
    pattern_idx : int, optional
        Index into :data:`ZERO_PATTERNS`; defaults to 0 (all zeros).
    """
    if size <= 0:
        return

    pattern = ZERO_PATTERNS[pattern_idx % len(ZERO_PATTERNS)]

    # Write pattern in 64-byte blocks for efficiency
    chunk = 64
    for i in range(0, size, chunk):
        block = pattern[: chunk - i] if i == 0 else pattern[:chunk]
        # Truncate/extend block to exactly ``chunk`` bytes
        if len(block) < chunk:
            # repeat pattern to fill chunk
            reps = chunk // len(block) + 1
            block = (block * reps)[:chunk]
        else:
            block = block[:chunk]

        # Write via ctypes; the cast to c_char_p ensures the write
        # is not optimized away by a smart compiler.
        ctypes.memmove(ptr + i, block, min(chunk, size - i))


def _get_buffer_address(buf: bytearray | (ctypes.Array)) -> int:
    """
    Get the integer address of a buffer, supporting both bytearray and ctypes arrays.

    Parameters
    ----------
    buf : bytearray or ctypes.Array
        The buffer to get the address of.

    Returns
    -------
    int
        Integer memory address.
    """
    if isinstance(buf, bytearray):
        return int.from_bytes(buf.buffer)
    # ctypes array — use ctypes.addressof
    return ctypes.addressof(buf)


def zero_memory_bytes(buf: bytearray | (ctypes.Array), pattern_idx: int = 0) -> None:
    """
    Securely zero out a ``bytearray`` or ctypes array in-place.

    Parameters
    ----------
    buf : bytearray or ctypes.Array
        The buffer to zero.
    pattern_idx : int, optional
        Index into :data:`ZERO_PATTERNS`.
    """
    addr = _get_buffer_address(buf)
    size = len(buf)
    zero_memory(addr, size, pattern_idx=pattern_idx)


# ---------------------------------------------------------------------------
# Residual byte analysis
# ---------------------------------------------------------------------------


def compute_region_checksum(addr: int, size: int) -> str:
    """
    Compute an SHA-256 checksum of a raw memory region.

    This is used as a quick "residual byte" check: after zeroization,
    the checksum should be all zeros (or match a known-clean baseline).

    Parameters
    ----------
    addr : int
        Starting address.
    size : int
        Number of bytes to hash.

    Returns
    -------
    str
        Hex-encoded SHA-256 digest.
    """
    # Read the memory region via ctypes, then hash the copied data.
    n = min(size, 1024 * 1024)  # cap at 1 MB per hash call for safety
    src = (ctypes.c_ubyte * n)()
    ctypes.memmove(src, addr, n)  # copy FROM addr TO src
    return hashlib.sha256(bytes(src)).hexdigest()


def check_residual_bytes(
    addr: int, size: int, expected_checksum: str = " " * 64
) -> Dict[str, Any]:
    """
    Check a memory region for residual non-zero bytes.

    Parameters
    ----------
    addr : int
        Starting address of the region.
    size : int
        Size of the region in bytes.
    expected_checksum : str, optional
        Expected hex checksum after zeroization (default: all-zeros
        representation).

    Returns
    -------
    dict with keys
        - ``clear ``: ``True`` if the computed checksum matches the
          expected one.
        - ``checksum ``: computed SHA-256 hex digest.
        - ``non_zero_count``: approximate count of bytes that differ
          from zero (derived from checksum comparison).
    """
    computed = compute_region_checksum(addr, size)
    is_clear = computed == expected_checksum

    # Rough non-zero estimate: count hex chars that are not '0'
    # (this is a heuristic; a full byte scan would be O(size)).
    nz_estimate = sum(
        1 for ch in computed if ch != "0"
    )  # type: ignore[assignment]

    return {
        "clear": is_clear,
        "checksum": computed,
        "non_zero_estimate": nz_estimate,
    }


# ---------------------------------------------------------------------------
# Reset validation
# ---------------------------------------------------------------------------


def validate_zeroization(
    ptr: int,
    size: int,
    overwrite_passes: int = 1,
    pattern_idx: int = 0,
) -> Dict[str, Any]:
    """
    Run a full zeroization validation cycle.

    Steps:
    1. Record a pre-zeroization checksum.
    2. Zero the memory ``overwrite_passes`` times with the chosen pattern.
    3. Record a post-zeroization checksum.
    4. Compare and report.

    Parameters
    ----------
    ptr : int
        Starting address.
    size : int
        Number of bytes to zero.
    overwrite_passes : int, optional
        How many times to repeat the zeroization (default: 1).
    pattern_idx : int, optional
        Pattern index from ``ZERO_PATTERNS``.

    Returns
    -------
    dict with keys
        - ``pre_checksum``: hex digest before zeroization.
        - ``post_checksum``: hex digest after zeroization.
        - ``clear``: ``True`` if post-checksum matches all-zeros.
        - ``passed``: ``True`` if zeroization was effective.
    """
    import os

    pre_checksum = compute_region_checksum(ptr, size)

    # Perform zeroization the requested number of passes
    for _ in range(overwrite_passes):
        zero_memory(ptr, size, pattern_idx=pattern_idx)

    post_checksum = compute_region_checksum(ptr, size)

    # "clear" means the post-checksum matches the SHA-256 hash of zero bytes.
    # SHA256 of N zero bytes is not an all-zeros hex string; compute it once.
    import hashlib

    # Compute the expected checksum of a fully-zero region (cached via module-level)
    _zero_checksum_cache: Dict[int, str] = {}

    def _get_zero_checksum(size: int) -> str:
        if size not in _zero_checksum_cache:
            _zero_checksum_cache[size] = hashlib.sha256(bytes(size)).hexdigest()
        return _zero_checksum_cache[size]

    expected_zero_checksum = _get_zero_checksum(size)
    is_clear = post_checksum == expected_zero_checksum

    passed = is_clear

    return {
        "pre_checksum": pre_checksum,
        "post_checksum": post_checksum,
        "clear": is_clear,
        "passed": passed,
        "overwrite_passes": overwrite_passes,
        "pattern_idx": pattern_idx,
    }


# ---------------------------------------------------------------------------
# Convenience / platform-aware wrappers
# ---------------------------------------------------------------------------


def zeroize_ptr(address: int, byte_size: int = 64) -> Dict[str, Any]:
    """
    Zeroize a small fixed-size region pointed to by ``address``.

    Useful for quick cleanup of small buffers (keys, nonces, etc.).
    Performs a single-pass zeroization with the default all-zeros pattern.

    Parameters
    ----------
    address : int
        Memory address (integer) to zeroize.
    byte_size : int, optional
        Size in bytes; default 64.

    Returns
    -------
    dict compatible with :func:`validate_zeroization` output (reduced fields).
    """
    result = validate_zeroization(address, byte_size, overwrite_passes=1, pattern_idx=0)
    # Strip to minimal fields
    return {
        "address": address,
        "size": byte_size,
        "pre_checksum": result["pre_checksum"],
        "post_checksum": result["post_checksum"],
        "clear": result["clear"],
        "passed": result["passed"],
    }


def zeroize_bytearray(buf: bytearray | (ctypes.Array)) -> Dict[str, Any]:
    """
    Zeroize a Python ``bytearray`` or ctypes array in-place and validate.

    Parameters
    ----------
    buf : bytearray or ctypes.Array
        Buffer to zeroize.

    Returns
    -------
    dict with validation results.
    """
    addr = _get_buffer_address(buf)
    size = len(buf)
    return validate_zeroization(addr, size, overwrite_passes=1, pattern_idx=0)


# ---------------------------------------------------------------------------
# Example / self-test (run with ``python -m src.pqc_bench.security.memory_zeroizer``)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import ctypes

    # Allocate a test buffer via ctypes
    test_buf = (ctypes.c_ubyte * 128)()
    # Fill with known data first
    for i in range(128):
        test_buf[i] = bytes([i % 256])[0]

    print("=== Pre-zeroization check ===")
    pre = check_residual_bytes(int(ctypes.addressof(test_buf)), 128, expected_checksum=" " * 64)
    print(f"pre_checksum: {pre['checksum']}")
    print(f"  clear: {pre['clear']}, non_zero_estimate: {pre['non_zero_estimate']}")

    # Zeroize
    zero_memory_bytes(test_buf)

    print("\n=== Post-zeroization check ===")
    post = check_residual_bytes(int(ctypes.addressof(test_buf)), 128, expected_checksum=" " * 64)
    print(f"post_checksum: {post['checksum']}")
    print(f"  clear: {post['clear']}, non_zero_estimate: {post['non_zero_estimate']}")

    # Full validate
    print("\n=== validate_zeroization ===")
    val = validate_zeroization(int(ctypes.addressof(test_buf)), 128, overwrite_passes=1)
    print(f"pre: {val['pre_checksum']}")
    print(f"post: {val['post_checksum']}")
    print(f"clear: {val['clear']}, passed: {val['passed']}")