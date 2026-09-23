"""Golomb-Dickman constant -- numberdb.org/T427

The constant is computed from

    lambda = integral_0^infinity rho(u) / (u + 1)^2 du,

where rho is the Dickman-de Bruijn function.  The generator represents rho on
each unit interval by a midpoint Taylor polynomial with ball coefficients,
using the delay differential equation u rho'(u) = -rho(u - 1).  The tails of
the geometric series for 1/u and (u + 1)^(-2) are included as ball radii, and
the integral after the last interval is bounded by monotonicity of rho.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The value is also checked against OEIS A084945 and against a direct mpmath
quadrature of the exponential-integral formula

    lambda = integral_0^infinity exp(-x - E1(x)) dx.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


DIGITS = 100
WORKING_GUARD = 512

# These were measured before the draft was filled.  With 100 requested digits
# they give a final radius below 3e-105, so the written 100 digits are covered.
DEGREE = 220
INTERVALS = 80
SERIES_EXTRA = 40

HALF = QQ(1) / QQ(2)

OEIS_PREFIX = (
    "0.6243299885435508709929363831008372441796426201805292869735519024"
    "95638088855113254462460276195539868869"
)


def field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def upper_abs(value, R):
    return R(abs(value).upper())


def add_error(value, radius, R):
    radius = R(radius)
    if radius <= 0:
        return value
    return value.add_error(radius)


def eval_poly(coefficients, y, R):
    y = R(y)
    total = R(0)
    for coefficient in reversed(coefficients):
        total = total * y + coefficient
    return total


def poly_bound(coefficients, R):
    """A uniform upper bound for |sum a_n y^n| on |y| <= 1/2."""
    power = R(1)
    total = R(0)
    h = R(HALF)
    for coefficient in coefficients:
        total += upper_abs(coefficient, R) * power
        power *= h
    return total


def inverse_coefficients(a, degree, R):
    """Taylor coefficients of 1 / (a + y) at y = 0."""
    a = R(a)
    coefficients = []
    term = R(1) / a
    ratio = -R(1) / a
    for j in range(degree + 1):
        if j:
            term *= ratio
        coefficients.append(term)
    return coefficients


def inverse_tail(a, degree, R):
    """Uniform tail bound for 1 / (a + y), |y| <= 1/2."""
    a = R(a)
    h = R(HALF)
    r = h / a
    m = degree + 1
    return (R(1) / a) * (r ** m) / (1 - r)


def inverse_square_coefficients(a, degree, R):
    """Taylor coefficients of 1 / (a + y)^2 at y = 0."""
    a = R(a)
    return [((-1) ** j) * R(j + 1) / (a ** (j + 2))
            for j in range(degree + 1)]


def inverse_square_tail(a, degree, R):
    """Uniform tail bound for 1 / (a + y)^2, |y| <= 1/2."""
    a = R(a)
    h = R(HALF)
    r = h / a
    m = degree + 1
    return ((R(1) / (a * a)) * (r ** m)
            * (R(m + 1) - R(m) * r) / ((1 - r) ** 2))


def convolve(left, right, max_degree, R):
    out = [R(0) for _ in range(max_degree + 1)]
    for i, left_i in enumerate(left):
        last = min(len(right) - 1, max_degree - i)
        for j in range(last + 1):
            out[i + j] += left_i * right[j]
    return out


def next_rho_interval(previous, k, R):
    """Build rho on [k, k+1] from rho on [k-1, k]."""
    series_degree = DEGREE + SERIES_EXTRA
    denominator_midpoint = QQ(2 * k + 1) / QQ(2)

    inv = inverse_coefficients(denominator_midpoint, series_degree, R)
    full = [-c for c in convolve(previous, inv, DEGREE + series_degree, R)]

    h = R(HALF)
    tail_from_truncated_product = R(0)
    power = h ** DEGREE
    for m in range(DEGREE, len(full)):
        if m > DEGREE:
            power *= h
        tail_from_truncated_product += upper_abs(full[m], R) * power
    tail_from_inverse = (poly_bound(previous, R)
                         * inverse_tail(denominator_midpoint, series_degree, R))
    derivative_tail = tail_from_truncated_product + tail_from_inverse

    current = [R(0) for _ in range(DEGREE + 1)]
    for n in range(1, DEGREE + 1):
        current[n] = full[n - 1] / R(n)

    left_value = eval_poly(previous, h, R)
    value_at_left_without_constant = R(0)
    y_power = -h
    for n in range(1, DEGREE + 1):
        value_at_left_without_constant += current[n] * y_power
        y_power *= -h

    current[0] = add_error(
        left_value - value_at_left_without_constant,
        derivative_tail,
        R,
    )
    return current


def rho_intervals(R):
    base = [R(0) for _ in range(DEGREE + 1)]
    base[0] = R(1)
    intervals = [base]
    for k in range(1, INTERVALS):
        intervals.append(next_rho_interval(intervals[-1], k, R))
    return intervals


def interval_integral(coefficients, k, R):
    """Integral over [k, k+1] of rho(u) / (u + 1)^2."""
    series_degree = DEGREE + SERIES_EXTRA
    denominator_midpoint = QQ(2 * k + 3) / QQ(2)

    inv2 = inverse_square_coefficients(denominator_midpoint, series_degree, R)
    full = convolve(coefficients, inv2, DEGREE + series_degree, R)

    h = R(HALF)
    total = R(0)
    for m, coefficient in enumerate(full):
        if m % 2:
            continue
        total += coefficient * (R(2) * (h ** (m + 1)) / R(m + 1))

    tail = (poly_bound(coefficients, R)
            * inverse_square_tail(denominator_midpoint, series_degree, R))
    return add_error(total, tail, R)


def golomb_dickman_ball(digits):
    R = field(digits)
    intervals = rho_intervals(R)

    total = R(0)
    for k, coefficients in enumerate(intervals):
        total += interval_integral(coefficients, k, R)

    rho_at_end = eval_poly(intervals[-1], R(HALF), R)
    tail_upper = R(rho_at_end.upper()) / R(INTERVALS + 1)
    total += tail_upper / 2
    return add_error(total, tail_upper / 2, R)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _contains(ball, value_text, R):
    return (ball - R(value_text)).contains_zero()


def _contains_decimal_record(ball, value_text, R):
    """Compare a published decimal as a last-place interval, not a point."""
    if "." not in value_text:
        return _contains(ball, value_text, R)
    fraction = value_text.split(".", 1)[1].split("e", 1)[0].split("E", 1)[0]
    recorded = R(value_text).add_error(R(10) ** (-len(fraction)))
    return (ball - recorded).contains_zero()


def independent_checks(value):
    R = value.parent()
    if not _contains_decimal_record(value, OEIS_PREFIX, R):
        raise AssertionError("computed ball does not contain the OEIS prefix")

    import mpmath

    mpmath.mp.dps = 160
    integrand = lambda x: mpmath.exp(-x - mpmath.e1(x))
    quadrature = mpmath.quad(integrand, [0, 1, mpmath.inf])
    if not _contains(value, str(quadrature), R):
        raise AssertionError("computed ball does not contain mpmath quadrature")


class GolombDickmanConstant(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T427"
    parameters = ()
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        yield {}

    def value(self, params, digits):
        if params:
            raise ValueError("the Golomb-Dickman constant has no parameters")
        return golomb_dickman_ball(digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = GolombDickmanConstant()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="Golomb-Dickman constant"))
    else:
        report = generator.verify(sample=None)
        print(report)
        if report.ok:
            independent_checks(golomb_dickman_ball(generator.digits))
            print("independent checks passed")
        sys.exit(0 if report.ok else 1)
