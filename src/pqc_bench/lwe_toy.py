"""Toy LWE (Learning With Errors) parameters for experimentation and threshold analysis.

Provides small-scale LWE instance generation, error distribution sampling,
and 1-6 bit security threshold analysis for educational/research purposes.

Note: These are toy parameters for experimentation only; not suitable for
actual cryptographic security analysis.
"""

from __future__ import annotations

import math
import random
from typing import Any

# Toy LWE parameter sets for experimentation (n, m, q ranges suitable for
# educational use and quick threshold analysis). Small dimensions ensure
# fast experimentation while demonstrating the LWE hardness transition.
TOY_LWE_PARAMETERS: dict[str, dict[str, Any]] = {
    # Small toy set: n in [2..6], m in [5..10], q in [2..32]
    "tiny": {
        "n_range": (2, 6),
        "m_range": (5, 10),
        "q_range": (2, 32),
        "error_std_factor": 0.5,
        "description": "Minimal LWE instance for experimentation",
    },
    # Medium toy set: n in [5..10], m in [10..20], q in [2..64]
    "small": {
        "n_range": (5, 10),
        "m_range": (10, 20),
        "q_range": (2, 64),
        "error_std_factor": 1.0,
        "description": "Small LWE instance for threshold analysis",
    },
    # Larger toy set: n in [10..15], m in [20..30], q in [2..128]
    "medium": {
        "n_range": (10, 15),
        "m_range": (20, 30),
        "q_range": (2, 128),
        "error_std_factor": 1.5,
        "description": "Medium LWE instance for bit-security mapping",
    },
}


def _erfinv_approx(x: float) -> float:
    """Approximate inverse error function erfinv(x).

    Uses a polynomial approximation valid for x in (-1, 1).
    Reference: Abramowitz and Stegun 7.1.26
    """
    if x == 0.0:
        return 0.0
    if x < 0:
        return -_erfinv_approx(-x)
    if x >= 1.0:
        return 5.0  # large value approximation
    if x <= -1.0:
        return -5.0
    # Use approximation formula
    # p = 0.3275911 for |x| < 0.5, else 0.1270875
    p = 0.3275911
    if abs(x) >= 0.5:
        p = 0.1270875
    # Save sign
    sign = 1 if x >= 0 else -1
    x_abs = abs(x)
    # Taylor-like approximation for erfinv
    # a1 = 0.147, a2 = 0.063, a3 = 0.022, a4 = 0.005
    a1 = 0.147
    a2 = 0.063
    a3 = 0.022
    a4 = 0.005
    # Lagrange interpolation
    ln1mx2 = math.log(1 - x_abs * x_abs)
    erfinv_approx = sign * math.sqrt(
        -2 * (ln1mx2 / (p * (a1 + x_abs * (a2 + x_abs * (a3 + x_abs * a4)))) ** 2)
    )
    return erfinv_approx


def sample_error(n: int, q: int, std_factor: float = 1.0) -> list[int]:
    """Sample error vector from discrete Gaussian over Z_q.

    Args:
        n: LWE dimension.
        q: Modulus.
        std_factor: Standard deviation factor relative to q/(2π).

    Returns:
        Error vector e ∈ Z_q^n sampled from discrete Gaussian.
    """
    std = q / (2 * math.pi) * std_factor
    error_vector = []
    for _ in range(n):
        # Sample from discrete Gaussian using inverse CDF approximation
        u = random.random()
        # Bounded sampling for toy parameters
        val = int(random.gauss(0, std))
        # Wrap to Z_q
        val = val % q
        error_vector.append(val)
    return error_vector


def generate_toy_lwe_instance(
    param_key: str = "small",
    secret: list[int] | None = None,
) -> dict[str, Any]:
    """Generate a toy LWE instance for experimentation.

    Args:
        param_key: Parameter set key from TOY_LWE_PARAMETERS.
        secret: Optional secret vector s ∈ Z_q^n. If None, generated randomly.

    Returns:
        Dictionary containing LWE instance (A, t, s) where t = <s, e> + e0 mod q.
    """
    params = TOY_LWE_PARAMETERS[param_key]
    n_min, n_max = params["n_range"]
    m_min, m_max = params["m_range"]
    q_min, q_max = params["q_range"]
    std_factor = params["error_std_factor"]

    # Select parameters within ranges
    n = random.randint(n_min, n_max)
    m = random.randint(m_min, m_max)
    q = random.randint(q_min, q_max)

    # Generate random secret
    if secret is None:
        secret = [random.randint(0, q - 1) for _ in range(n)]
    else:
        # When custom secret is provided, use its dimension
        n = len(secret)
        if len(secret) != n:
            raise ValueError(
                f"Secret length {len(secret)} != dimension {n}"
            )

    # Generate random matrix A ∈ Z_q^(m×n)
    A = [[random.randint(0, q - 1) for _ in range(n)] for _ in range(m)]

    # Sample error vector e ∈ Z_q^m
    e = sample_error(m, q, std_factor)

    # Sample small error e0 ∈ Z_q
    e0_std = q / (2 * math.pi) * std_factor * 0.1
    val = int(e0_std * math.sqrt(2) * _erfinv_approx(1 - 2 * random.random()))
    # Wrap to Z_q
    val = val % q
    e0 = val % q

    # Compute t = <A, e> + e0 mod q = sum(A[i][j] * e[j] for j) + e0 mod q for each row
    t = []
    for i in range(m):
        inner_product = sum(A[i][j] * e[j] for j in range(n)) % q
        t_i = (inner_product + e0) % q
        t.append(t_i)

    return {
        "n": n,
        "m": m,
        "q": q,
        "secret": secret,
        "matrix_A": A,
        "error_vector": e,
        "error_scalar": e0,
        "t": t,
        "param_key": param_key,
        "description": params["description"],
    }


def compute_1_6_bit_limit(
    n: int,
    q: int,
    error_std_factor: float = 1.0,
) -> dict[str, Any]:
    """
    Compute the 1-6 bit security threshold for a toy LWE instance.

    The 1-6 bit limit represents the range of approximate security bits
    that can be read from the LWE instance before the error rate
    exceeds the decodability threshold. This is calculated using the
    Hybrid Estimate and the Gauss Smoothing parameter.

    For toy parameters, the bit limit is approximately:
      bits ≈ log2(q) - log2(error_std) - 0.5 * log2(n) - 1.0

    The "1-6 bit" range means we can reliably extract 1-6 bits of
    information before the signal-to-noise ratio degrades beyond
    the error correction capability.
    """
    std = q / (2 * math.pi) * error_std_factor

    # Approximate bit security using the LWE estimator formula
    # bits = log2(q) - log2(σ) - 0.5*log2(n) - 1.0
    if std <= 0 or q <= 0 or n <= 0:
        raise ValueError("Parameters must be positive")

    log2_q = math.log2(q)
    log2_std = math.log2(std)
    log2_n = math.log2(n)

    # Approximate security bits
    approximate_bits = log2_q - log2_std - 0.5 * log2_n - 1.0

    # The "1-6 bit" range: we can extract at least floor(bits) bits,
    # but practical extraction is limited to 1-6 bits before
    # the error rate exceeds the decoding threshold
    min_bits = max(1, int(math.floor(approximate_bits)))
    max_bits = min(6, int(math.ceil(approximate_bits)))

    # Ensure min <= max
    if min_bits > max_bits:
        min_bits, max_bits = 1, 6

    # Compute error rate
    error_rate = std / q

    # Decodability threshold: error rate should be < 0.25 for useful LWE
    # Below this, we can extract some bits; above, the instance is
    # effectively random
    decodability_threshold = 0.25
    within_threshold = error_rate < decodability_threshold

    return {
        "n": n,
        "q": q,
        "error_std_factor": error_std_factor,
        "error_rate": error_rate,
        "approximate_bits": round(approximate_bits, 2),
        "min_extractable_bits": min_bits,
        "max_extractable_bits": max_bits,
        "bit_range": f"{min_bits}-{max_bits} bits",
        "within_decodability_threshold": within_threshold,
        "decodability_threshold": decodability_threshold,
        "analysis": (
            f"LWE(n={n}, q={q}, σ/q={error_rate:.4f}) "
            f"→ approx. {approximate_bits:.2f} bits security; "
            f"extractable range: {min_bits}-{max_bits} bits"
        ),
    }


def compute_error_rate(
    n: int,
    q: int,
    std_factor: float = 1.0,
) -> float:
    """Compute the asymptotic error rate for LWE instance.

    The error rate determines when the LWE instance becomes
    trivially solvable vs. hard.

    Args:
        n: LWE dimension.
        q: Modulus.
        std_factor: Error standard deviation factor.

    Returns:
        Error rate σ/q as a float.
    """
    std = q / (2 * math.pi) * std_factor
    return std / q


def compute_1_6_bit_range(
    n: int,
    q: int,
    error_std_factor: float = 1.0,
) -> dict[str, Any]:
    """Compute the 1-6 bit security range for toy LWE instance.

    Returns the approximate bit range [min_bits, max_bits] that can
    be reliably extracted, and the confidence level.

    The formula is derived from the LWE hardness assumption:
    bits ≈ log2(q) - log2(σ) - 0.5*log2(n) - 1.0

    where σ = q/(2π) * error_std_factor is the error standard deviation.
    """
    std = q / (2 * math.pi) * error_std_factor

    # Approximate bit security using the LWE estimator formula
    # bits = log2(q) - log2(σ) - 0.5*log2(n) - 1.0
    if std <= 0 or q <= 0 or n <= 0:
        raise ValueError("Parameters must be positive")

    log2_q = math.log2(q)
    log2_std = math.log2(std)
    log2_n = math.log2(n)

    # Approximate security bits
    approximate_bits = log2_q - log2_std - 0.5 * log2_n - 1.0

    # The "1-6 bit" range: we can extract at least floor(bits) bits,
    # but practical extraction is limited to 1-6 bits before
    # the error rate exceeds the decoding threshold
    min_bits = max(1, int(math.floor(approximate_bits)))
    max_bits = min(6, int(math.ceil(approximate_bits)))

    # Ensure min <= max
    if min_bits > max_bits:
        min_bits, max_bits = 1, 6

    # Compute error rate
    error_rate = compute_error_rate(n, q, error_std_factor)

    # Decodability threshold: error rate should be < 0.25 for useful LWE
    # Below this, we can extract some bits; above, the instance is
    # effectively random
    decodability_threshold = 0.25
    within_threshold = error_rate < decodability_threshold

    return {
        "n": n,
        "q": q,
        "error_std_factor": error_std_factor,
        "error_rate": error_rate,
        "approximate_bits": round(approximate_bits, 2),
        "min_extractable_bits": min_bits,
        "max_extractable_bits": max_bits,
        "bit_range": f"{min_bits}-{max_bits} bits",
        "within_decodability_threshold": within_threshold,
        "decodability_threshold": decodability_threshold,
        "analysis": (
            f"LWE(n={n}, q={q}, σ/q={error_rate:.4f}) "
            f"→ approx. {approximate_bits:.2f} bits security; "
            f"extractable range: {min_bits}-{max_bits} bits"
        ),
    }


def analyze_lwe_threshold(
    n: int,
    q: int,
    error_std_factor: float = 1.0,
    verbose: bool = True,
) -> dict[str, Any]:
    """Full LWE threshold analysis for toy parameters.

    Combines error rate computation and 1-6 bit range analysis
    into a single comprehensive result.

    Args:
        n: LWE dimension.
        q: Modulus.
        error_std_factor: Error standard deviation factor.
        verbose: Whether to include descriptive analysis strings.

    Returns:
        Dictionary with complete threshold analysis.
    """
    error_rate = compute_error_rate(n, q, error_std_factor)
    bit_range = compute_1_6_bit_range(n, q, error_std_factor)

    result = {
        "n": n,
        "q": q,
        "error_std_factor": error_std_factor,
        "error_rate": error_rate,
        "bit_range": bit_range["bit_range"],
        "min_extractable_bits": bit_range["min_extractable_bits"],
        "max_extractable_bits": bit_range["max_extractable_bits"],
        "approximate_bits": bit_range["approximate_bits"],
        "within_decodability_threshold": bit_range["within_decodability_threshold"],
    }

    if verbose:
        result["analysis"] = bit_range["analysis"]

    return result


if __name__ == "__main__":
    # Quick demo
    print("Toy LWE Parameter Demo")
    print("=" * 50)

    # Generate a small instance
    instance = generate_toy_lwe_instance("tiny")
    print(f"Generated LWE instance: n={instance['n']}, m={instance['m']}, q={instance['q']}")
    print(f"Secret: {instance['secret']}")
    print(f"t (syndrome): {instance['t']}")

    # Analyze threshold
    threshold = analyze_lwe_threshold(instance["n"], instance["q"], instance["param_key"])
    print(f"\nThreshold analysis: {threshold['analysis']}")

    # Test 1-6 bit range
    bit_analysis = compute_1_6_bit_range(instance["n"], instance["q"])
    print(f"\n1-6 bit range: {bit_analysis['bit_range']}")
    print(f"Approximate bits: {bit_analysis['approximate_bits']}")