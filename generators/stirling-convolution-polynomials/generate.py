"""Stirling convolution polynomials sigma_n(x) -- numberdb.org/T186.

    (z * exp(z) / (exp(z) - 1))^x = sum_{n >= 0} x*sigma_n(x) z^n

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: Measured before the draft was created: n = 1..25 gives 25 entries,
#: sigma_25 is 1118 characters written out, and the entries block is 10.8 KB.
UP_TO = 25

_R = PolynomialRing(QQ, "x")
_x = _R.gen()
_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _zero_series(order):
    return [_R.zero() for _ in range(order + 1)]


def _mul(a, b, order):
    out = _zero_series(order)
    for i, ai in enumerate(a):
        if not ai:
            continue
        for j, bj in enumerate(b[:order + 1 - i]):
            if bj:
                out[i + j] += ai * bj
    return out


def _base_series(order):
    """Ordinary coefficients of z/(1-exp(-z)) through z^order."""
    a = [QQ(0) for _ in range(order + 1)]
    a[0] = QQ(1)
    for r in range(2, order + 2):
        total = QQ(0)
        for m in range(2, r + 1):
            total += a[r - m] * QQ((-1) ** (m + 1)) / QQ(factorial(m))
        a[r - 1] = -total
    return a


def _binomial_x(m):
    value = _R.one()
    for j in range(m):
        value *= _x - QQ(j)
        value /= QQ(j + 1)
    return value


def _divide_by_x(polynomial):
    quotient, remainder = polynomial.quo_rem(_x)
    if remainder:
        raise ArithmeticError("coefficient is not divisible by x")
    return quotient


def stirling_convolution_polynomials(up_to=UP_TO):
    if up_to in _CACHE:
        return _CACHE[up_to]

    base = [_R(c) for c in _base_series(up_to)]
    base[0] = _R.zero()
    coefficients = _zero_series(up_to)
    coefficients[0] = _R.one()
    power = _zero_series(up_to)
    power[0] = _R.one()

    for m in range(1, up_to + 1):
        power = _mul(power, base, up_to)
        factor = _binomial_x(m)
        for n in range(up_to + 1):
            if power[n]:
                coefficients[n] += factor * power[n]

    values = [None]
    for n in range(1, up_to + 1):
        values.append(_divide_by_x(coefficients[n]))
    _CACHE[up_to] = values
    return values


def stirling_convolution_polynomial(n):
    if n < 1:
        raise ValueError("n must be positive; sigma_0(x)=1/x is not a polynomial")
    return stirling_convolution_polynomials(n)[n]


class StirlingConvolutionPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T186")
    parameters = ("n",)
    type = "Q[]"

    # Exact: rational coefficients, no precision to choose.
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(1, up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return stirling_convolution_polynomial(int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = StirlingConvolutionPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Stirling convolution polynomials, n = 1..%d" % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
