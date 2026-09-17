"""Kauffman polynomials of the prime knots with at most ten crossings -- numberdb.org/T314

    a^(-m) F_K(a,z) in Z[a,z], with m the lowest exponent of a in F_K,

for the unknot 0_1, for every prime knot K = n_k of the Rolfsen table with
3 <= n <= 10 crossings, numbered after Perko, and for the mirror image of
each chiral one. The knot K is the one KnotInfo draws. The entry `mirror` is
its mirror image.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The source values are KnotInfo's Kauffman polynomial vectors from
database_knotinfo 2026.9.1. Each value is a Laurent polynomial in a,
multiplied by a power of a so the lowest exponent is zero. The removed
exponent is recorded in the entry comment.
"""

import os
import sys
from math import comb

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

from knotinfo_kauffman_data import AMPHICHIRAL, KNOTINFO_KAUFFMAN, names

ZAZ = PolynomialRing(ZZ, ("a", "z"))
a, z = ZAZ.gens()
ZZz = PolynomialRing(ZZ, "z")
zz = ZZz.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def vector_to_terms(vector):
    """KnotInfo's Kauffman vector as {(a exponent, z exponent): coefficient}."""
    low_z, high_z = ZZ(vector[0]), ZZ(vector[1])
    rows = vector[2:]
    if len(rows) != int(high_z - low_z + 1):
        raise ArithmeticError("Kauffman vector has the wrong number of z rows")
    terms = {}
    for offset, row in enumerate(rows):
        z_exp = low_z + offset
        low_a, high_a = ZZ(row[0]), ZZ(row[1])
        coefficients = row[2:]
        if len(coefficients) != int(high_a - low_a + 1):
            raise ArithmeticError("Kauffman vector has the wrong number of a coefficients")
        for index, coefficient in enumerate(coefficients):
            coefficient = ZZ(coefficient)
            if coefficient:
                terms[(low_a + index, z_exp)] = coefficient
    return terms


def jones_vector_to_terms(vector):
    """KnotInfo's Jones vector as {t exponent: coefficient}."""
    low_t, high_t = ZZ(vector[0]), ZZ(vector[1])
    coefficients = vector[2:]
    if len(coefficients) != int(high_t - low_t + 1):
        raise ArithmeticError("Jones vector has the wrong number of coefficients")
    return {
        low_t + index: ZZ(coefficient)
        for index, coefficient in enumerate(coefficients)
        if ZZ(coefficient)
    }


def q_polynomial(text):
    """KnotInfo's Q-polynomial string, with x renamed to z."""
    return ZZz(text.replace("x", "z"))


def q_from_kauffman(terms):
    """Specialise F_K(a,z) at a = 1."""
    total = ZZz(0)
    for (_a_exp, z_exp), coefficient in terms.items():
        if z_exp < 0:
            raise ArithmeticError("negative z exponent in a Kauffman polynomial")
        total += ZZz(coefficient) * zz ** z_exp
    return total


def jones_from_kauffman(terms):
    """Specialise F_K(a,z) by a=-t^(-3/4), z=t^(1/4)+t^(-1/4)."""
    in_quarter_powers = {}
    for (a_exp, z_exp), coefficient in terms.items():
        if z_exp < 0:
            raise ArithmeticError("negative z exponent in a Kauffman polynomial")
        sign = -1 if a_exp % 2 else 1
        for j in range(int(z_exp) + 1):
            quarter_exp = -3 * a_exp + 2 * j - z_exp
            in_quarter_powers[quarter_exp] = (
                in_quarter_powers.get(quarter_exp, ZZ(0))
                + coefficient * sign * ZZ(comb(int(z_exp), j))
            )

    out = {}
    for quarter_exp, coefficient in in_quarter_powers.items():
        if not coefficient:
            continue
        if quarter_exp % 4:
            raise ArithmeticError(
                "Jones specialisation has surviving nonintegral quarter exponent %s"
                % quarter_exp
            )
        out[ZZ(quarter_exp // 4)] = coefficient
    return out


def reciprocal_a(terms):
    """Substitute a -> a^(-1)."""
    return {(-a_exp, z_exp): coefficient for (a_exp, z_exp), coefficient in terms.items()}


def shifted(terms):
    """Return the shifted polynomial and the removed exponent m."""
    if not terms:
        return ZAZ(0), ZZ(0)
    low_a = min(a_exp for a_exp, _z_exp in terms)
    low_z = min(z_exp for _a_exp, z_exp in terms)
    if low_z != 0:
        raise ArithmeticError("Kauffman polynomial has lowest z exponent %s, not 0" % low_z)
    total = ZAZ(0)
    for (a_exp, z_exp), coefficient in terms.items():
        total += ZAZ(coefficient) * a ** (a_exp - low_a) * z ** z_exp
    return total, low_a


class KauffmanPolynomials(numberdb.Generator):

    table = "T314"
    parameters = ("n", "k", "knot")
    type = "Z[]"
    rigour = "exact"
    files = ("generate.py", "knotinfo_kauffman_data.py")

    _knots = None

    def enumerate(self):
        for n, k in names():
            yield {"n": int(n), "k": int(k), "knot": "K"}
            if (n, k) != (0, 1) and (n, k) not in AMPHICHIRAL:
                yield {"n": int(n), "k": int(k), "knot": "mirror"}

    def knot(self, n, k):
        if (n, k) == (0, 1):
            one = {(ZZ(0), ZZ(0)): ZZ(1)}
            return one, one

        record = KNOTINFO_KAUFFMAN[(n, k)]
        terms = vector_to_terms(record["kauffman"])

        expected_jones = jones_vector_to_terms(record["jones"])
        got_jones = jones_from_kauffman(terms)
        if got_jones != expected_jones:
            raise ArithmeticError(
                "%d_%d: the Kauffman Jones specialisation gives %s, not %s"
                % (n, k, got_jones, expected_jones)
            )

        expected_q = q_polynomial(record["q"])
        got_q = q_from_kauffman(terms)
        if got_q != expected_q:
            raise ArithmeticError(
                "%d_%d: F(1,z) gives %s, not KnotInfo's Q-polynomial %s"
                % (n, k, got_q, expected_q)
            )

        mirror = reciprocal_a(terms)
        got_mirror_jones = jones_from_kauffman(mirror)
        expected_mirror_jones = {-exponent: coefficient for exponent, coefficient in expected_jones.items()}
        if got_mirror_jones != expected_mirror_jones:
            raise ArithmeticError(
                "%d_%d: the mirror Kauffman polynomial does not specialise to V(t^-1)"
                % (n, k)
            )
        return terms, mirror

    def all_knots(self):
        if self._knots is None:
            self._knots = {(n, k): self.knot(n, k) for n, k in names()}
        return self._knots

    def value(self, params, digits):
        n, k = int(params["n"]), int(params["k"])
        image = params["knot"]
        if image not in ("K", "mirror"):
            raise ValueError("knot is 'K' or 'mirror', not %r" % image)
        if image == "mirror" and ((n, k) == (0, 1) or (n, k) in AMPHICHIRAL):
            raise ValueError("%d_%d is its own mirror image and has one entry" % (n, k))

        terms, mirror = self.all_knots()[(n, k)]
        polynomial, shift = shifted(terms if image == "K" else mirror)
        entry = {"number": polynomial}
        if (n, k) == (0, 1):
            entry["equals"] = "HREF{One}"
        else:
            entry["comment"] = "$m=%s$" % shift
        return entry


if __name__ == "__main__":
    _key_from_stdin()
    generator = KauffmanPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Kauffman polynomials of the unknot, the prime knots with at most ten crossings as KnotInfo draws them, and the mirror images of the chiral ones"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
