with open('src/pqc_bench/lwe_toy.py', 'r') as f:
    content = f.read()

# Add the _erfinv_approx function before sample_error
old_func = '''def sample_error(n: int, q: int, std_factor: float = 1.0) -> list[int]:
    """Sample error vector from discrete Gaussian over Z_q.

    Args:
        n: LWE dimension.
        q: Modulus.
        std_factor: Standard deviation factor relative to q/(2π).

    Returns:
        Error vector e ∈ Z_q^n sampled from discrete Gaussian.
    '''
'''
new_func = '''def _erfinv_approx(x: float) -> float:
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
    '''
'''
if old_func in content:
    content = content.replace(old_func, new_func)
    with open('src/pqc_bench/lwe_toy.py', 'w') as f:
        f.write(content)
    print("File updated successfully")
else:
    print("Could not find old function pattern")