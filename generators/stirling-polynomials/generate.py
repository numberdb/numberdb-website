"""Stirling polynomials S_k(x) -- numberdb.org/T180.

    (t / (1 - exp(-t)))^(x + 1) = sum_{k >= 0} S_k(x) t^k/k!

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

#: Measured before the draft was created: k = 0..30 gives 31 entries, S_30 is
#: 1017 characters written out, and the entries block is 12.7 KB.
UP_TO = 30

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
    """Ordinary coefficients of t / (1 - exp(-t)) through t^order."""
    a = [QQ(0) for _ in range(order + 1)]
    a[0] = QQ(1)
    for r in range(2, order + 2):
        total = QQ(0)
        for m in range(2, r + 1):
            total += a[r - m] * QQ((-1) ** (m + 1)) / QQ(factorial(m))
        a[r - 1] = -total
    return a


def _binomial_x_plus_1(m):
    value = _R.one()
    for j in range(m):
        value *= _x + QQ(1 - j)
        value /= QQ(j + 1)
    return value


def stirling_polynomials(up_to=UP_TO):
    if up_to in _CACHE:
        return _CACHE[up_to]

    base = [_R(c) for c in _base_series(up_to)]
    base[0] = _R.zero()
    result = _zero_series(up_to)
    result[0] = _R.one()
    power = _zero_series(up_to)
    power[0] = _R.one()

    for m in range(1, up_to + 1):
        power = _mul(power, base, up_to)
        factor = _binomial_x_plus_1(m)
        for k in range(up_to + 1):
            if power[k]:
                result[k] += factor * power[k]

    values = [result[k] * QQ(factorial(k)) for k in range(up_to + 1)]
    _CACHE[up_to] = values
    return values


def stirling_polynomial(k):
    return stirling_polynomials(k)[k]


class StirlingPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T180")
    parameters = ("k",)
    type = "Q[]"

    # Exact: rational coefficients, no precision to choose.
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for k in range(up_to + 1):
            yield {"k": str(k)}

    def value(self, params, digits):
        return stirling_polynomial(int(params["k"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = StirlingPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Stirling polynomials in the Sheffer-sequence convention, k = 0..%d"
                    % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
