"""Boole polynomials r_n(x) -- numberdb.org/T184.

    sum_{n >= 0} r_n(x) t^n/n! = 2(1 + t)^x/(2 + t)

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

#: Measured before the draft was created: n = 0..30 gives 31 entries, r_30 is
#: 934 characters written out, and the entries block is 11.4 KB.
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


def _binomial_x(j):
    value = _R.one()
    for m in range(j):
        value *= _x - QQ(m)
        value /= QQ(m + 1)
    return value


def boole_polynomials(up_to=UP_TO):
    if up_to in _CACHE:
        return _CACHE[up_to]
    values = []
    for n in range(up_to + 1):
        coefficient = _R.zero()
        for j in range(n + 1):
            coefficient += _binomial_x(j) * QQ((-1) ** (n - j)) / QQ(2 ** (n - j))
        values.append(coefficient * QQ(factorial(n)))
    _CACHE[up_to] = values
    return values


def boole_polynomial(n):
    return boole_polynomials(n)[n]


class BoolePolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T184")
    parameters = ("n",)
    type = "Q[]"

    # Exact: rational coefficients, no precision to choose.
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return boole_polynomial(int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = BoolePolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Boole polynomials in Jordan's normalisation, n = 0..%d"
                    % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
