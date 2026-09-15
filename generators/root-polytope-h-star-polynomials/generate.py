"""Ehrhart h-star polynomials of root polytopes -- numberdb.org/T243

For the irreducible crystallographic root systems this stores the Ehrhart
h-star polynomial h^*_{P_Phi}(z) of the full root polytope
P_Phi = conv(Phi), in the root lattice.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The h-star polynomials use the closed forms for the coordinator polynomials of
root lattices.

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.
"""

import os
import sys
from math import comb

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


T243 = "T243"
CLASSICAL_UP_TO_RANK = 20

EXCEPTIONAL_H_STAR = {
    "E6": [1, 66, 645, 1384, 645, 66, 1],
    "E7": [1, 119, 2037, 8211, 8787, 2037, 119, 1],
    "E8": [1, 232, 7228, 55384, 133510, 107224, 24508, 232, 1],
    "F4": [1, 44, 198, 140, 1],
    "G2": [1, 10, 7],
}

_Z = PolynomialRing(QQ, "z")
_z = _Z.gen()


def choose(n, k):
    if k < 0 or k > n:
        return 0
    return comb(n, k)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def parse_type(root_type):
    family = root_type[0]
    rank = int(root_type[1:])
    return family, rank


def h_star_coefficients(root_type):
    if root_type in EXCEPTIONAL_H_STAR:
        return EXCEPTIONAL_H_STAR[root_type]

    family, n = parse_type(root_type)
    if family == "A":
        return [choose(n, k) ** 2 for k in range(n + 1)]
    if family == "B":
        return [
            choose(2 * n + 1, 2 * k) - 2 * n * choose(n - 1, k - 1)
            for k in range(n + 1)
        ]
    if family == "C":
        return [choose(2 * n, 2 * k) for k in range(n + 1)]
    if family == "D":
        return [
            choose(2 * n, 2 * k) - 2 * n * choose(n - 2, k - 1)
            for k in range(n + 1)
        ]
    raise ValueError("unknown root type %r" % (root_type,))


def h_star_polynomial(root_type):
    return sum(QQ(c) * _z ** i for i, c in enumerate(h_star_coefficients(root_type)))


def root_types(up_to_rank=CLASSICAL_UP_TO_RANK):
    for n in range(2, up_to_rank + 1):
        yield "A%d" % n
    for n in range(2, up_to_rank + 1):
        yield "B%d" % n
    for n in range(3, up_to_rank + 1):
        yield "C%d" % n
    for n in range(4, up_to_rank + 1):
        yield "D%d" % n
    for root_type in ("E6", "E7", "E8", "F4", "G2"):
        yield root_type


class RootPolytopeHStarPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", T243)
    parameters = ("type",)
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to_rank=CLASSICAL_UP_TO_RANK):
        for root_type in root_types(up_to_rank):
            yield {"type": root_type}

    def value(self, params, digits):
        return h_star_polynomial(params["type"])


if __name__ == "__main__":
    _key_from_stdin()
    generator = RootPolytopeHStarPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="root polytope h-star polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
