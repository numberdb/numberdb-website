"""Faulhaber polynomials F_p(a) -- numberdb.org/T181.

    F_p(N(N+1)/2) = sum_{k=1}^N k^p, for p positive and odd

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
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: How far the table runs. Measured before the draft was created: odd
#: p = 1..49 gives 25 entries, F_49 is 768 characters written out, and the
#: whole entries block is 7.6 KB.
UP_TO_P = 49

_R = PolynomialRing(QQ, "a")
_a = _R.gen()
_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _lagrange(points):
    value = _R.zero()
    for i, (xi, yi) in enumerate(points):
        term = _R(yi)
        for j, (xj, _yj) in enumerate(points):
            if i == j:
                continue
            term *= (_a - QQ(xj)) / QQ(xi - xj)
        value += term
    return value


def faulhaber_polynomial(p):
    if p < 1 or p % 2 == 0:
        raise ValueError("p must be a positive odd integer")
    if p in _CACHE:
        return _CACHE[p]

    degree = (p + 1) // 2
    points = []
    for N in range(degree + 1):
        x = QQ(N * (N + 1)) / QQ(2)
        y = sum(QQ(k) ** p for k in range(1, N + 1))
        points.append((x, y))

    value = _lagrange(points)
    _CACHE[p] = value
    return value


class FaulhaberPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T181")
    parameters = ("p",)
    type = "Q[]"

    # Exact: rational coefficients, no precision to choose.
    rigour = "exact"

    def enumerate(self, up_to_p=UP_TO_P):
        for p in range(1, up_to_p + 1, 2):
            yield {"p": str(p)}

    def value(self, params, digits):
        return faulhaber_polynomial(int(params["p"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = FaulhaberPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Faulhaber polynomials in a = n(n+1)/2, odd p = 1..%d"
                    % (UP_TO_P,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
