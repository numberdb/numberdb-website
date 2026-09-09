"""Mahler polynomials g_n(x) -- numberdb.org/T182.

    sum_{n >= 0} g_n(x) t^n/n! = exp(x(1 + t - exp(t)))

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
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: Measured before the draft was created: n = 0..50 gives 51 entries, g_50 is
#: 1128 characters written out, and the entries block is 20.4 KB.
UP_TO = 50

_R = PolynomialRing(ZZ, "x")
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


def _associated_stirling_rows(up_to):
    """Partitions of an n-set into k blocks, each block of size at least two."""
    rows = [[ZZ(0) for _ in range(up_to // 2 + 2)] for _ in range(up_to + 1)]
    rows[0][0] = ZZ(1)
    for n in range(1, up_to + 1):
        for k in range(1, n // 2 + 1):
            total = ZZ(k) * rows[n - 1][k]
            if n >= 2:
                total += ZZ(n - 1) * rows[n - 2][k - 1]
            rows[n][k] = total
    return rows


def mahler_polynomials(up_to=UP_TO):
    if up_to in _CACHE:
        return _CACHE[up_to]

    rows = _associated_stirling_rows(up_to)
    values = []
    for n in range(up_to + 1):
        polynomial = _R.zero()
        for k in range(n // 2 + 1):
            if rows[n][k]:
                polynomial += ZZ((-1) ** k) * rows[n][k] * _x**k
        values.append(polynomial)
    _CACHE[up_to] = values
    return values


def mahler_polynomial(n):
    return mahler_polynomials(n)[n]


class MahlerPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T182")
    parameters = ("n",)
    type = "Z[]"

    # Exact: integer coefficients, no precision to choose.
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return mahler_polynomial(int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = MahlerPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Mahler polynomials from the egf, n = 0..%d" % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
