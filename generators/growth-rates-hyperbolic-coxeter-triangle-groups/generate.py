r"""Growth rates of hyperbolic Coxeter triangle groups -- numberdb.org/T222

For the Coxeter triangle group Delta(p,q,r), this stores the exponential
growth rate with respect to the three reflection generators.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The growth series is computed exactly from Steinberg's formula

    1 / W(t^-1) = sum_{T finite} (-1)^|T| / W_T(t).

For a triangle Coxeter group the finite special subgroups are the identity,
the three rank-one subgroups, and the finite dihedral rank-two subgroups.
The growth rate is the largest real root greater than 1 of the reciprocal
of the reduced denominator.
"""

import os
import sys
from functools import lru_cache
from fractions import Fraction
from math import lcm

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = "T222"
FINITE_BOUND = 12
EXPECTED_ROWS = 345
WORKING_GUARD = 128
CHECK_LENGTH = 12

R = PolynomialRing(QQ, "t")
t = R.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def label_part(m):
    return "inf" if m is None else str(m)


def tex_part(m):
    return r"\infty" if m is None else str(m)


def reciprocal(m):
    return Fraction(0, 1) if m is None else Fraction(1, m)


def is_hyperbolic(p, q, r):
    return reciprocal(p) + reciprocal(q) + reciprocal(r) < 1


def diagram_key(p, q, r):
    if p == 2:
        return "[%s,%s]" % (label_part(r), label_part(q))
    return "[(%s,%s,%s)]" % (label_part(p), label_part(q), label_part(r))


def diagram_tex(p, q, r):
    return r"\Delta(%s,%s,%s)" % (tex_part(p), tex_part(q), tex_part(r))


def parse_diagram(key):
    if key.startswith("[(") and key.endswith(")]"):
        pieces = key[2:-2].split(",")
        if len(pieces) != 3:
            raise ValueError("bad diagram key %r" % key)
        return tuple(None if piece == "inf" else int(piece) for piece in pieces)
    if key.startswith("[") and key.endswith("]"):
        pieces = key[1:-1].split(",")
        if len(pieces) != 2:
            raise ValueError("bad diagram key %r" % key)
        r, q = (None if piece == "inf" else int(piece) for piece in pieces)
        return 2, q, r
    raise ValueError("bad diagram key %r" % key)


def triples():
    out = []
    for p in range(2, FINITE_BOUND + 1):
        for q in range(p, FINITE_BOUND + 1):
            for r in range(q, FINITE_BOUND + 1):
                if is_hyperbolic(p, q, r):
                    out.append((p, q, r))
    for p in range(2, FINITE_BOUND + 1):
        for q in list(range(p, FINITE_BOUND + 1)) + [None]:
            if is_hyperbolic(p, q, None):
                out.append((p, q, None))
    if len(out) != EXPECTED_ROWS:
        raise ArithmeticError("found %d rows, expected %d" % (len(out), EXPECTED_ROWS))
    return out


def q_integer(m):
    return sum(t ** k for k in range(m))


@lru_cache(None)
def growth_rational(p, q, r):
    one = R(1)
    expr = one - QQ(3) / (one + t)
    for m in (p, q, r):
        if m is not None:
            expr += QQ(1) / ((one + t) * q_integer(m))
    return QQ(1) / expr(t ** -1)


@lru_cache(None)
def growth_polynomial(p, q, r):
    denominator = R(growth_rational(p, q, r).denominator()).monic()
    degree = denominator.degree()
    reversed_denominator = sum(
        denominator[i] * t ** (degree - i) for i in range(degree + 1)
    )
    return R(reversed_denominator).monic()


def real_roots_greater_than_one(poly, bits):
    RIF = RealIntervalField(bits)
    roots = []
    for root, multiplicity in poly.roots(RIF):
        if root.upper() > 1 and root.lower() > 1:
            roots.append(root)
    roots.sort(key=lambda root: root.lower())
    return roots


@lru_cache(None)
def minimal_polynomial_text(p, q, r):
    poly = growth_polynomial(p, q, r)
    best = None
    for factor, multiplicity in poly.factor():
        roots = real_roots_greater_than_one(R(factor), 160)
        if not roots:
            continue
        candidate = (roots[-1].lower(), R(factor).monic())
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        raise ArithmeticError("no growth root found for %s" % (diagram_key(p, q, r),))
    return str(best[1])


@lru_cache(None)
def minimal_polynomial(p, q, r):
    return R(minimal_polynomial_text(p, q, r))


def growth_rate(p, q, r, digits):
    poly = minimal_polynomial(p, q, r)
    if poly.degree() == 1:
        root = -poly[0] / poly[1]
        if root.denominator() == 1:
            return ZZ(root.numerator())
        return root
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    roots = real_roots_greater_than_one(poly, bits)
    if not roots:
        raise ArithmeticError("no real root greater than one for %s" % poly)
    return roots[-1]


def entry_comment(p, q, r):
    sentence = (
        r"$%s$, with minimal polynomial $%s$ for $\tau$."
        % (diagram_tex(p, q, r), minimal_polynomial_text(p, q, r))
    )
    if (p, q, r) == (2, 3, 7):
        sentence += " This is Lehmer's number."
    if (p, q, r) == (2, 3, None):
        sentence += " This is the plastic number."
    return sentence


def polynomial_coefficients(poly, n):
    return [poly[i] if i <= poly.degree() else QQ(0) for i in range(n + 1)]


def growth_coefficients(p, q, r, n):
    rational = growth_rational(p, q, r)
    numerator = R(rational.numerator())
    denominator = R(rational.denominator())
    if denominator[0] != 1:
        numerator = numerator / denominator[0]
        denominator = denominator / denominator[0]
    p_coeffs = polynomial_coefficients(numerator, n)
    q_coeffs = polynomial_coefficients(denominator, min(n, denominator.degree()))
    coefficients = []
    for k in range(n + 1):
        total = p_coeffs[k]
        for i in range(1, min(k, denominator.degree()) + 1):
            total -= q_coeffs[i] * coefficients[k - i]
        if total.denominator() != 1:
            raise ArithmeticError("nonintegral coefficient %s at %d" % (total, k))
        coefficients.append(int(total))
    return coefficients


def matrix_multiply(a, b):
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def tits_generators(p, q, r):
    from sage.rings.number_field.number_field import CyclotomicField

    finite = [m for m in (p, q, r) if m is not None]
    order = 1
    for m in finite:
        order = lcm(order, 2 * m)
    K = QQ if order == 1 else CyclotomicField(order)
    zeta = None if order == 1 else K.gen()

    def cosine(m):
        if m is None:
            return K(1)
        power = order // (2 * m)
        return (zeta ** power + zeta ** (-power)) / K(2)

    labels = {(0, 1): p, (1, 2): q, (0, 2): r}
    cosines = {}
    for (i, j), m in labels.items():
        value = cosine(m)
        cosines[(i, j)] = value
        cosines[(j, i)] = value

    generators = []
    for i in range(3):
        matrix = [[K(1) if row == col else K(0) for col in range(3)] for row in range(3)]
        for col in range(3):
            if col == i:
                matrix[i][col] = K(-1)
            else:
                matrix[i][col] = K(2) * cosines[(i, col)]
        generators.append(tuple(tuple(row) for row in matrix))
    return generators


def bfs_counts(p, q, r, length):
    identity = tuple(
        tuple(QQ(1) if row == col else QQ(0) for col in range(3)) for row in range(3)
    )
    generators = tits_generators(p, q, r)
    seen = {identity}
    frontier = {identity}
    counts = [1]
    for step in range(1, length + 1):
        next_frontier = set()
        for element in frontier:
            for generator in generators:
                candidate = matrix_multiply(element, generator)
                if candidate not in seen:
                    seen.add(candidate)
                    next_frontier.add(candidate)
        counts.append(len(next_frontier))
        frontier = next_frontier
    return counts


def check_identities():
    controls = {
        (2, 3, 7): "t^10 + t^9 - t^7 - t^6 - t^5 - t^4 - t^3 + t + 1",
        (2, 3, 8): "t^10 - t^7 - t^5 - t^3 + 1",
        (2, 3, None): "t^3 - t - 1",
    }
    for triple, expected in controls.items():
        got = minimal_polynomial(*triple)
        if got != R(expected):
            raise ArithmeticError("%s polynomial %s, expected %s" % (triple, got, expected))

    for triple in [(2, 3, 7), (2, 3, None), (3, 3, 4), (2, None, None)]:
        series = growth_coefficients(*triple, CHECK_LENGTH)
        counted = bfs_counts(*triple, CHECK_LENGTH)
        if series != counted:
            raise ArithmeticError(
                "%s series counts %s, BFS counts %s" % (triple, series, counted)
            )
        print("%s counts through length %d: %s" % (triple, CHECK_LENGTH, counted))

    print("checked %d triangle groups" % len(triples()))


class HyperbolicCoxeterTriangleGrowth(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE") or TABLE
    parameters = ("diagram",)
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py",)

    def enumerate(self):
        for p, q, r in triples():
            yield {"diagram": diagram_key(p, q, r)}

    def value(self, params, digits):
        p, q, r = parse_diagram(params["diagram"])
        if not is_hyperbolic(p, q, r):
            raise ValueError("%s is not hyperbolic" % (params["diagram"],))
        return {
            "number": growth_rate(p, q, r, digits),
            "comment": entry_comment(p, q, r),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = HyperbolicCoxeterTriangleGrowth()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        check_identities()
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="growth rates of hyperbolic Coxeter triangle groups"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
