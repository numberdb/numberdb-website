"""Lebesgue constants of the classical interpolation node families -- numberdb.org/T328.

For each listed interpolation node family T_n this computes

    Lambda_n(T_n) = max_{-1 <= x <= 1} sum_j |l_j(x)|,

where l_j is the Lagrange basis polynomial for the n + 1 nodes.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The nodes are algebraic. The generator forms the Lagrange basis exactly over
Sage's algebraic real field, splits [-1,1] at the nodes, and on each interval
maximizes the signed polynomial obtained from the constant sign pattern there.
The maximum is therefore checked at endpoints and at exact derivative roots.
"""

import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.qqbar import AA, _init_qqbar
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

_init_qqbar()

DIGITS = 100
WORKING_GUARD = 192
MAX_N = 4

QQX = PolynomialRing(QQ, "x")
_x = QQX.gen()
AAX = PolynomialRing(AA, "x")
_y = AAX.gen()

FAMILIES = (
    "equally-spaced",
    "chebyshev-first-kind",
    "chebyshev-lobatto",
    "stretched-chebyshev",
    "gauss-legendre",
    "gauss-lobatto",
)


@lru_cache(maxsize=None)
def chebyshev_t(n):
    if n == 0:
        return QQX.one()
    if n == 1:
        return _x
    before, current = QQX.one(), _x
    for _ in range(1, n):
        before, current = current, 2 * _x * current - before
    return current


@lru_cache(maxsize=None)
def legendre_p(n):
    if n == 0:
        return QQX.one()
    if n == 1:
        return _x
    before, current = QQX.one(), _x
    for k in range(1, n):
        before, current = (
            current,
            (QQ(2 * k + 1) * _x * current - QQ(k) * before) / QQ(k + 1),
        )
    return current


def all_real_roots(poly):
    found = [AA(root) for root in poly.roots(AA, multiplicities=False)]
    if len(found) != poly.degree():
        raise ValueError(
            "expected %d real roots and found %d for %s"
            % (poly.degree(), len(found), poly)
        )
    return tuple(sorted(found))


@lru_cache(maxsize=None)
def nodes(family, n):
    if n < 1:
        raise ValueError("n must be at least 1")
    if family == "equally-spaced":
        return tuple(AA(QQ(-1) + QQ(2 * j) / QQ(n)) for j in range(n + 1))
    if family == "chebyshev-first-kind":
        return all_real_roots(chebyshev_t(n + 1))
    if family == "chebyshev-lobatto":
        if n == 1:
            return (AA(-1), AA(1))
        return (AA(-1),) + all_real_roots(chebyshev_t(n).derivative()) + (AA(1),)
    if family == "stretched-chebyshev":
        base = all_real_roots(chebyshev_t(n + 1))
        scale = max(base)
        return tuple(sorted(node / scale for node in base))
    if family == "gauss-legendre":
        return all_real_roots(legendre_p(n + 1))
    if family == "gauss-lobatto":
        if n == 1:
            return (AA(-1), AA(1))
        return (AA(-1),) + all_real_roots(legendre_p(n).derivative()) + (AA(1),)
    raise ValueError("unknown family %r" % (family,))


@lru_cache(maxsize=None)
def lagrange_basis(family, n):
    xs = nodes(family, n)
    basis = []
    for j, xj in enumerate(xs):
        polynomial = AAX.one()
        for m, xm in enumerate(xs):
            if m != j:
                polynomial *= (_y - AAX(xm)) / AA(xj - xm)
        basis.append(polynomial)
    return tuple(basis)


def abs_aa(value):
    return value if value >= 0 else -value


def unique_sorted(points):
    out = []
    for point in sorted(points):
        if not out or point != out[-1]:
            out.append(point)
    return tuple(out)


@lru_cache(maxsize=None)
def lebesgue_algebraic(family, n):
    basis = lagrange_basis(family, n)
    boundaries = unique_sorted((AA(-1),) + nodes(family, n) + (AA(1),))

    best = AA(1)
    for point in boundaries:
        value = sum(abs_aa(polynomial(point)) for polynomial in basis)
        if value > best:
            best = value

    for left, right in zip(boundaries, boundaries[1:]):
        if left == right:
            continue
        midpoint = (left + right) / AA(2)
        signed = AAX.zero()
        for polynomial in basis:
            value = polynomial(midpoint)
            if value > 0:
                signed += polynomial
            elif value < 0:
                signed -= polynomial
            else:
                raise ValueError("a Lagrange basis polynomial vanished inside an interval")

        derivative = signed.derivative()
        if derivative.is_zero():
            continue
        for root in derivative.roots(AA, multiplicities=False):
            root = AA(root)
            if left < root < right:
                value = signed(root)
                if value > best:
                    best = value
    return best


def as_numberdb_value(value, digits):
    try:
        return QQ(value)
    except (TypeError, ValueError):
        pass
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    ball = field(value)
    if not ball.is_finite():
        raise ValueError("non-finite ball for %s" % (value,))
    return ball


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


class LebesgueConstantsInterpolationNodes(numberdb.Generator):
    table = "T328"
    parameters = ("family", "n")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_n=MAX_N):
        for family in FAMILIES:
            for n in range(1, max_n + 1):
                yield {"family": family, "n": str(n)}

    def value(self, params, digits):
        family = str(params["family"])
        n = int(params["n"])
        return as_numberdb_value(lebesgue_algebraic(family, n), digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = LebesgueConstantsInterpolationNodes()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="computed Lebesgue constants", removing=True))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
