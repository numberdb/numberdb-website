"""Ehrhart h-star polynomials of Birkhoff polytopes -- numberdb.org/T242

For n = 3, ..., 6 this stores the Ehrhart h-star polynomial h^*_{B_n}(z) of
the Birkhoff polytope B_n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The h-star rows are transcribed from OEIS A259473.

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


UP_TO_N = 6

H_STAR_COEFFICIENTS = {
    3: [1, 1, 1],
    4: [1, 14, 87, 148, 87, 14, 1],
    5: [
        1, 103, 4306, 63110, 388615, 1115068, 1575669, 1115068, 388615,
        63110, 4306, 103, 1,
    ],
    6: [
        1, 694, 184015, 15902580, 567296265, 9816969306, 91422589980,
        490333468494, 1583419977390, 3166404385990, 3982599815746,
        3166404385990, 1583419977390, 490333468494, 91422589980,
        9816969306, 567296265, 15902580, 184015, 694, 1,
    ],
}

_Z = PolynomialRing(QQ, "z")
_z = _Z.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def h_star_polynomial(n):
    return sum(QQ(c) * _z ** i for i, c in enumerate(H_STAR_COEFFICIENTS[n]))


class BirkhoffPolytopeHStarPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T242")
    parameters = ("n",)
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to_n=UP_TO_N):
        for n in range(3, up_to_n + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return h_star_polynomial(int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = BirkhoffPolytopeHStarPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Birkhoff polytope h-star polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
