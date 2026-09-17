"""HOMFLY-PT polynomials of the prime knots with at most ten crossings -- numberdb.org/T312

    P_K(v,z) and P_K(l,m), shifted from Laurent polynomials to Z[v,z] and Z[l,m],

for the unknot 0_1, for every prime knot K = n_k of the Rolfsen table with
3 <= n <= 10 crossings, numbered after Perko, and for the mirror image of
each chiral one. The knot K is the one KnotInfo draws, built from the
`braid_notation` column of database_knotinfo 2026.9.1, copied into
knotinfo_prime_knots.py. The entry `mirror` is its mirror image.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The normalisation parameter names Sage's `homfly_polynomial` normalisations:

* `vz` has P(0_1)=1 and v^-1 P(L_+) - v P(L_-) = z P(L_0). Sage documents
  this as the normalisation agreeing with KnotInfo.
* `lm` has P(0_1)=1 and l P(L_+) + l^-1 P(L_-) + m P(L_0) = 0.

Each value is a Laurent polynomial multiplied by the monomial that makes the
lowest exponent of each variable zero. The removed exponents are recorded in
the entry comment.
"""

import os
import sys

import numberdb.sage as numberdb
import sage.symbolic.ring  # noqa: F401
from sage.arith.misc import binomial
from sage.groups.braid import BraidGroup
from sage.knots.link import Link
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

from knotinfo_prime_knots import (
    AMPHICHIRAL,
    KNOTINFO_BRAIDS,
    names,
)

Zvz = PolynomialRing(ZZ, ("v", "z"))
v, z = Zvz.gens()
Zlm = PolynomialRing(ZZ, ("l", "m"))
l, m = Zlm.gens()
ZT = PolynomialRing(ZZ, "t")
t = ZT.gen()
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


def laurent_terms(polynomial):
    """The exponent dictionary of a two-variable Laurent polynomial."""
    if polynomial == 0:
        return {}
    out = {}
    for exponents, coefficient in polynomial.dict().items():
        if len(exponents) != 2:
            raise ArithmeticError("expected a two-variable HOMFLY polynomial")
        out[tuple(ZZ(e) for e in exponents)] = ZZ(coefficient)
    return out


def reciprocal_first(terms):
    """Substitute the inverse of the first variable."""
    return {(-a, b): c for (a, b), c in terms.items()}


def shifted(terms, normalisation):
    """Return the shifted polynomial and the two exponents removed."""
    ring = Zvz if normalisation == "vz" else Zlm
    x, y = ring.gens()
    if not terms:
        return ring(0), (ZZ(0), ZZ(0))
    low_x = min(a for a, _b in terms)
    low_y = min(b for _a, b in terms)
    total = ring(0)
    for (a, b), coefficient in terms.items():
        total += ring(coefficient) * x ** (a - low_x) * y ** (b - low_y)
    return total, (low_x, low_y)


def laurent_from_symbolic(expression):
    """Sage's symbolic Jones polynomial as {exponent: coefficient}."""
    variables = expression.variables()
    if not variables:
        return {ZZ(0): ZZ(expression)}
    out = {}
    for coefficient, exponent in expression.coefficients(variables[0]):
        if ZZ(exponent) != exponent:
            raise ArithmeticError("Jones exponent %s is not an integer" % exponent)
        out[ZZ(exponent)] = ZZ(coefficient)
    return out


def jones_from_homfly_vz(terms):
    """Specialise P(v,z) by v=t, z=t^(-1/2)-t^(1/2)."""
    in_sqrt_t = {}
    for (v_exp, z_exp), coefficient in terms.items():
        if z_exp < 0:
            raise ArithmeticError("negative z exponent in a knot HOMFLY polynomial")
        for j in range(int(z_exp) + 1):
            exponent = 2 * v_exp - z_exp + 2 * j
            in_sqrt_t[exponent] = in_sqrt_t.get(exponent, ZZ(0)) + coefficient * ZZ(binomial(z_exp, j)) * ((-1) ** j)
    out = {}
    for exponent, coefficient in in_sqrt_t.items():
        if coefficient == 0:
            continue
        if exponent % 2:
            raise ArithmeticError("Jones specialisation has odd half-exponent %s" % exponent)
        out[ZZ(exponent // 2)] = ZZ(coefficient)
    return out


def conway_from_homfly_vz(terms):
    """Specialise P(v,z) at v=1."""
    out = ZZz(0)
    for (_v_exp, z_exp), coefficient in terms.items():
        if z_exp < 0:
            raise ArithmeticError("negative z exponent in a knot HOMFLY polynomial")
        out += ZZz(coefficient) * zz ** z_exp
    return out


def conway_polynomial(link):
    """Sage's Conway polynomial, printed in t, as an element of Z[z]."""
    return ZZz([ZZ(c) for c in link.conway_polynomial().list()])


def comment(lows):
    if lows == (0, 0):
        return ""
    if lows[1] == 0:
        return "a=%d" % lows[0]
    return "a=%d, b=%d" % (lows[0], lows[1])


class HomflyPTPolynomials(numberdb.Generator):

    table = "T312"
    parameters = ("n", "k", "knot", "normalisation")
    type = "Z[]"
    rigour = "exact"
    files = ("generate.py", "knotinfo_prime_knots.py")

    _knots = None

    def enumerate(self):
        for n, k in names():
            for normalisation in ("vz", "lm"):
                yield {"n": int(n), "k": int(k), "knot": "K", "normalisation": normalisation}
                if (n, k) != (0, 1) and (n, k) not in AMPHICHIRAL:
                    yield {"n": int(n), "k": int(k), "knot": "mirror", "normalisation": normalisation}

    def knot(self, n, k):
        if (n, k) == (0, 1):
            one = {(ZZ(0), ZZ(0)): ZZ(1)}
            return {"vz": (one, one), "lm": (one, one)}
        strands, word = KNOTINFO_BRAIDS[(n, k)]
        link = Link(BraidGroup(strands)(word))
        out = {}
        for normalisation in ("vz", "lm"):
            P = laurent_terms(link.homfly_polynomial(normalization=normalisation))
            P_mirror = laurent_terms(link.mirror_image().homfly_polynomial(normalization=normalisation))
            expected = reciprocal_first(P)
            if P_mirror != expected:
                raise ArithmeticError(
                    "%d_%d %s: mirror image gives %s, not first-variable reciprocal %s"
                    % (n, k, normalisation, P_mirror, expected)
                )
            out[normalisation] = (P, P_mirror)

        jones = laurent_from_symbolic(link.jones_polynomial())
        if jones_from_homfly_vz(out["vz"][0]) != jones:
            raise ArithmeticError("%d_%d: the HOMFLY-PT Jones specialisation disagrees" % (n, k))
        conway = conway_polynomial(link)
        if conway_from_homfly_vz(out["vz"][0]) != conway:
            raise ArithmeticError("%d_%d: the HOMFLY-PT Conway specialisation disagrees" % (n, k))
        return out

    def all_knots(self):
        if self._knots is None:
            self._knots = {(n, k): self.knot(n, k) for n, k in names()}
        return self._knots

    def value(self, params, digits):
        n, k = int(params["n"]), int(params["k"])
        image = params["knot"]
        normalisation = params["normalisation"]
        if image not in ("K", "mirror"):
            raise ValueError("knot is 'K' or 'mirror', not %r" % image)
        if normalisation not in ("vz", "lm"):
            raise ValueError("normalisation is 'vz' or 'lm', not %r" % normalisation)
        if image == "mirror" and ((n, k) == (0, 1) or (n, k) in AMPHICHIRAL):
            raise ValueError("%d_%d is its own mirror image and has one entry" % (n, k))

        P, P_mirror = self.all_knots()[(n, k)][normalisation]
        pol, lows = shifted(P if image == "K" else P_mirror, normalisation)
        entry = {"number": pol}
        note = comment(lows)
        if note:
            entry["comment"] = note
        if (n, k) == (0, 1):
            entry["equals"] = "HREF{One}"
        return entry


if __name__ == "__main__":
    _key_from_stdin()
    generator = HomflyPTPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="HOMFLY-PT polynomials of the unknot, the prime knots with at most ten crossings as KnotInfo draws them, and the mirror images of the chiral ones, in the vz and lm normalisations"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
