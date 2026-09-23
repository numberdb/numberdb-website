"""Values of the Dickman-de Bruijn function rho(u) -- numberdb.org/T433

The Dickman-de Bruijn function is defined by rho(u) = 1 on 0 <= u <= 1
and by the delay differential equation

    u rho'(u) = -rho(u - 1)        (u > 1).

This generator represents rho on each unit interval by a midpoint Taylor
polynomial with real ball coefficients. The Taylor series for 1/u has a
geometric tail on each interval, and that omitted tail is added to the ball
radius before values are written.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


DIGITS = 100

# Bits of working precision beyond the requested decimal digits. With the
# degree below, the measured 1.00 <= u <= 10.00 grid carries at least the
# 100 significant digits requested by the table.
WORKING_GUARD = 512

DEGREE = 260
SERIES_EXTRA = 60
MAX_ARGUMENT = 10
STEP = 100
HALF = QQ(1) / QQ(2)


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
    tail_from_inverse = (
        poly_bound(previous, R)
        * inverse_tail(denominator_midpoint, series_degree, R)
    )
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
    for k in range(1, MAX_ARGUMENT + 1):
        intervals.append(next_rho_interval(intervals[-1], k, R))
    return intervals


_INTERVALS = {}


def intervals_for(digits):
    if digits not in _INTERVALS:
        R = field(digits)
        _INTERVALS[digits] = (R, rho_intervals(R))
    return _INTERVALS[digits]


def grid_value(n):
    return QQ(n) / QQ(STEP)


def step_value(u, digits):
    """Evaluate the Taylor-step representation, including on 1 < u <= 2."""
    u = QQ(u)
    R, intervals = intervals_for(digits)
    k = int(u.floor())
    if k > MAX_ARGUMENT:
        k = MAX_ARGUMENT
    centre = QQ(k) + HALF
    return eval_poly(intervals[k], u - centre, R)


def rho_value(u, digits):
    u = QQ(u)
    if u < 0 or u > MAX_ARGUMENT:
        raise ValueError("u must satisfy 0 <= u <= %d" % MAX_ARGUMENT)
    if u <= 1:
        return ZZ(1)
    R = field(digits)
    if u <= 2:
        return R(1) - R(u).log()
    return step_value(u, digits)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _contains(left, right):
    parent = getattr(left, "parent", lambda: None)()
    if parent is not None:
        right = parent(right)
    return (left - right).contains_zero()


def check_first_interval(digits):
    R = field(digits)
    for n in range(STEP + 1, 2 * STEP + 1):
        u = grid_value(n)
        direct = R(1) - R(u).log()
        stepped = step_value(u, digits)
        if not _contains(stepped, direct):
            raise AssertionError(
                "Taylor step disagrees with 1 - log(u) at u=%s" % (u,)
            )


class DickmanRhoValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T433"
    parameters = ("u",)
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for n in range(STEP, MAX_ARGUMENT * STEP + 1):
            yield {"u": str(grid_value(n))}

    def value(self, params, digits):
        u = QQ(params["u"])
        if u < 1 or u > MAX_ARGUMENT:
            raise ValueError("u must satisfy 1 <= u <= %d" % MAX_ARGUMENT)
        if u == 1:
            return {
                "number": ZZ(1),
                "comment": (
                    "The boundary value. The function is identically $1$ "
                    "on $0\\leq u\\leq1$."
                ),
            }
        return rho_value(u, digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = DickmanRhoValues()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="Dickman-de Bruijn rho values"))
    else:
        report = generator.verify(sample=None)
        print(report)
        if report.ok:
            check_first_interval(generator.digits)
            print("first interval check passed")
        sys.exit(0 if report.ok else 1)
