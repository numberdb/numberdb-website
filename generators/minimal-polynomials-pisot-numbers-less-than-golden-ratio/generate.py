"""Minimal polynomials of the Pisot numbers less than the golden ratio -- numberdb.org/T300

This table stores the monic minimal polynomial of the r-th smallest
Pisot-Vijayaraghavan number in the interval (1, phi), for the same ranks as
numberdb.org/T286. The polynomials come from the Dufresnoy-Pisot families
used by the root table.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = "T300"
ROOT_TABLE = "Pisot_numbers_less_than_the_golden_ratio"
RANKS = 50
MAX_N = 80
WORKING_GUARD = 256

R = PolynomialRing(QQ, "x")
Z_POLYS = PolynomialRing(ZZ, "x")
x = R.gen()


SOURCE_FIRST_TEN = (
    x**3 - x - 1,
    x**4 - x**3 - 1,
    x**5 - x**4 - x**3 + x**2 - 1,
    x**3 - x**2 - 1,
    x**6 - x**5 - x**4 + x**2 - 1,
    x**5 - x**3 - x**2 - x - 1,
    x**7 - x**6 - x**5 + x**2 - 1,
    x**6 - 2 * x**5 + x**4 - x**2 + x - 1,
    x**5 - x**4 - x**2 - 1,
    x**8 - x**7 - x**6 + x**2 - 1,
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def p_polynomial(n):
    return x**n * (x**2 - x - 1) + 1


def q_polynomial(n):
    return x**n * (x**2 - x - 1) + x**2 - 1


def exceptional_polynomial():
    return x**6 - 2 * x**5 + x**4 - x**2 + x - 1


def source_polynomials():
    for n in range(2, MAX_N + 1):
        yield "P", n, p_polynomial(n)
    for n in range(2, MAX_N + 1):
        yield "Q", n, q_polynomial(n)
    yield "E", None, exceptional_polynomial()


def _root_sort_key(root):
    return QQ(root.center())


def _interval_contains_less_than_phi(root, field):
    phi = (field(1) + field(5).sqrt()) / 2
    return root.lower() > 1 and root.upper() < phi.lower()


def _integer_polynomial(polynomial):
    coefficients = []
    for coefficient in polynomial.list():
        if coefficient not in ZZ:
            raise ArithmeticError("nonintegral coefficient in %s" % polynomial)
        coefficients.append(ZZ(coefficient))
    return Z_POLYS(coefficients)


def pisot_factor_and_root(polynomial, digits):
    field = RealIntervalField(numberdb.bits(digits, losing=WORKING_GUARD))
    found = []
    for factor, exponent in polynomial.factor():
        if factor.degree() == 0:
            continue
        for root, multiplicity in factor.roots(field):
            if multiplicity != 1:
                raise ArithmeticError("multiple real root in %s" % factor)
            if _interval_contains_less_than_phi(root, field):
                found.append((factor, root))
    if len(found) != 1:
        raise ArithmeticError(
            "expected one Pisot root in %s, found %d" % (polynomial, len(found))
        )
    factor, root = found[0]
    if not pari(str(factor)).polisirreducible():
        raise ArithmeticError("selected factor is reducible: %s" % factor)
    lower_value = factor(root.lower())
    upper_value = factor(root.upper())
    if not (lower_value * upper_value <= 0):
        raise ArithmeticError("root interval does not bracket a sign change")
    return _integer_polynomial(factor), root


@lru_cache(None)
def records(digits):
    by_polynomial = {}
    for family, n, polynomial in source_polynomials():
        factor, root = pisot_factor_and_root(polynomial, digits)
        key = tuple(ZZ(c) for c in factor.list())
        existing = by_polynomial.get(key)
        if existing is None or (family, n or 0) < (existing["family"], existing["n"] or 0):
            by_polynomial[key] = {
                "family": family,
                "n": n,
                "polynomial": factor,
                "root": root,
            }

    ordered = sorted(by_polynomial.values(), key=lambda record: _root_sort_key(record["root"]))
    if len(ordered) < RANKS + 1:
        raise ArithmeticError("only found %d Pisot roots" % len(ordered))
    first_ten = tuple(R(record["polynomial"]) for record in ordered[:10])
    if first_ten != SOURCE_FIRST_TEN:
        raise ArithmeticError("first ten minimal polynomials do not match the source list")
    return tuple(ordered[:RANKS])


def family_label(record):
    if record["family"] == "E":
        return "$E$"
    return "$%s_{%d}$" % (record["family"], record["n"])


def entry_comment(rank, record):
    return (
        "HREF{%s#%d}[$\\theta_{%d}$] is the root in $(1,\\varphi)$; "
        "this polynomial is selected from %s."
        % (ROOT_TABLE, rank, rank, family_label(record))
    )


class PisotMinimalPolynomialsBelowGoldenRatio(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or TABLE
    parameters = ("r",)
    type = "Z[]"
    digits = 100
    rigour = "exact"

    def enumerate(self):
        for rank in range(1, RANKS + 1):
            yield {"r": str(rank)}

    def value(self, params, digits):
        rank = int(params["r"])
        if rank < 1 or rank > RANKS:
            raise ValueError("rank must be in 1..%d" % RANKS)
        record = records(digits)[rank - 1]
        return {"number": record["polynomial"], "comment": entry_comment(rank, record)}


def main():
    _key_from_stdin()
    generator = PisotMinimalPolynomialsBelowGoldenRatio()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="computed Pisot minimal polynomials from exact families"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
