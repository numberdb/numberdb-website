"""Bateman polynomials F_n(x) -- numberdb.org/T183.

    F_n(x) = _3F_2(-n, n + 1, (x + 1)/2; 1, 1; 1)

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

#: Measured before the draft was created: n = 0..30 gives 31 entries, F_30 is
#: about 1000 characters written out, and the entries block is about 16 KB.
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


def bateman_polynomials(up_to=UP_TO):
    if up_to in _CACHE:
        return _CACHE[up_to]
    if up_to < 0:
        raise ValueError("up_to must be nonnegative")

    values = [_R.one()]
    if up_to >= 1:
        values.append(-_x)
    for n in range(1, up_to):
        numerator = -QQ(2 * n + 1) * _x * values[n] + QQ(n * n) * values[n - 1]
        values.append(numerator / QQ((n + 1) * (n + 1)))

    _CACHE[up_to] = values
    return values


def bateman_polynomial(n):
    return bateman_polynomials(n)[n]


class BatemanPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T183")
    parameters = ("n",)
    type = "Q[]"

    # Exact: rational coefficients, no precision to choose.
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return bateman_polynomial(int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = BatemanPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Bateman polynomials F_n(x), n = 0..%d" % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
