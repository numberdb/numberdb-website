r"""Gaunt coefficients -- numberdb.org/T362

This draft stores every nonzero Gaunt coefficient

    G(l1 m1; l2 m2; l3 m3)

with all li <= 7, using Condon-Shortley complex spherical harmonics and the
lexicographically largest representative under pair permutations and the
simultaneous sign change m_i -> -m_i.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed from the Wigner 3j finite sum in exact rational
arithmetic, represented as a rational multiple of the square root of a
rational number divided by sqrt(pi), and then converted to Arb balls for
storage. Before any entry is returned, the whole range is checked against
SageMath's exact gaunt() function, against the symmetries used for the
canonical representatives, against the l=0 special case, and against exact
Legendre-polynomial integration for the m_i = 0 rows.
"""

import os
import sys
from itertools import permutations

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.functions.wigner import gaunt as sage_gaunt
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TID = "T362"
L_UP_TO = 7
DIGITS = 100
WORKING_GUARD = 96


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def int_text(value):
    return str(int(value))


def parse_int(text):
    value = ZZ(str(text))
    return int(value)


def phase(exponent_twice):
    if exponent_twice % 2:
        raise ValueError("phase exponent is not an integer")
    return ZZ(-1) ** (exponent_twice // 2)


def factorial_int(n):
    if n < 0:
        raise ValueError("negative factorial argument %d" % (n,))
    return ZZ(factorial(int(n)))


def factorial_ratio(numerators, denominators):
    value = QQ(1)
    for n in numerators:
        value *= QQ(factorial_int(n))
    for n in denominators:
        value /= QQ(factorial_int(n))
    return value


def triangle(a, b, c):
    return abs(a - b) <= c <= a + b and (a + b + c) % 2 == 0


def magnetic_values(l_value):
    return range(-l_value, l_value + 1)


def admissible_wigner(a, b, c, p, q, r):
    return (
        triangle(a, b, c)
        and -a <= p <= a
        and -b <= q <= b
        and -c <= r <= c
        and (a - p) % 2 == 0
        and (b - q) % 2 == 0
        and (c - r) % 2 == 0
        and p + q == r
    )


def wigner_multiplier_radicand(a, b, c, p, q, r):
    """Return q, R with Wigner 3j = q * sqrt(R), for lower row p/2,q/2,-r/2."""
    if not admissible_wigner(a, b, c, p, q, r):
        return QQ(0), QQ(1)

    A = (a + b - c) // 2
    B = (a - b + c) // 2
    C = (-a + b + c) // 2
    D = (a + b + c) // 2 + 1

    m_factor_args = [
        (a + p) // 2,
        (a - p) // 2,
        (b + q) // 2,
        (b - q) // 2,
        (c - r) // 2,
        (c + r) // 2,
    ]
    radicand = factorial_ratio([A, B, C] + m_factor_args, [D])

    s_lower = max(0, -((c - b + p) // 2), -((c - a - q) // 2))
    s_upper = min(A, (a - p) // 2, (b + q) // 2)
    total = QQ(0)
    for s in range(s_lower, s_upper + 1):
        denominator_args = [
            s,
            A - s,
            (a - p) // 2 - s,
            (b + q) // 2 - s,
            (c - b + p) // 2 + s,
            (c - a - q) // 2 + s,
        ]
        denominator = ZZ(1)
        for n in denominator_args:
            denominator *= factorial_int(n)
        total += QQ((-1) ** s) / QQ(denominator)

    if total == 0:
        return QQ(0), QQ(1)
    return QQ(phase(a - b + r)) * total, radicand


def gaunt_multiplier_radicand(symbol):
    l1, m1, l2, m2, l3, m3 = symbol
    if m1 + m2 + m3 != 0:
        return QQ(0), QQ(1)

    a, b, c = 2 * l1, 2 * l2, 2 * l3
    p, q, r = 2 * m1, 2 * m2, -2 * m3
    zero_multiplier, zero_radicand = wigner_multiplier_radicand(a, b, c, 0, 0, 0)
    m_multiplier, m_radicand = wigner_multiplier_radicand(a, b, c, p, q, r)
    if zero_multiplier == 0 or m_multiplier == 0:
        return QQ(0), QQ(1)

    prefactor = QQ((2 * l1 + 1) * (2 * l2 + 1) * (2 * l3 + 1)) / QQ(4)
    return zero_multiplier * m_multiplier, zero_radicand * m_radicand * prefactor


def gaunt_ball(symbol, digits):
    multiplier, radicand = gaunt_multiplier_radicand(symbol)
    if multiplier == 0:
        return QQ(0)
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    value = field(multiplier) * field(radicand).sqrt() / field.pi().sqrt()
    if not value.is_finite():
        raise ArithmeticError("non-finite ball for %s" % (symbol,))
    return value


def overlaps(value, other, digits=DIGITS):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    return field(value).overlaps(field(other))


def symbol_images(symbol):
    pairs = ((symbol[0], symbol[1]), (symbol[2], symbol[3]), (symbol[4], symbol[5]))
    for order in permutations((0, 1, 2)):
        ordered = [pairs[i] for i in order]
        yield tuple(item for pair in ordered for item in pair)
    negated = tuple((l_value, -m_value) for l_value, m_value in pairs)
    for order in permutations((0, 1, 2)):
        ordered = [negated[i] for i in order]
        yield tuple(item for pair in ordered for item in pair)


def canonical(symbol):
    return max(symbol_images(symbol))


def nonzero_symbol(symbol):
    multiplier, _ = gaunt_multiplier_radicand(symbol)
    return multiplier != 0


def enumerate_symbols(up_to=L_UP_TO):
    symbols = []
    for l1 in range(up_to + 1):
        for l2 in range(up_to + 1):
            for l3 in range(abs(l1 - l2), min(up_to, l1 + l2) + 1):
                if (l1 + l2 + l3) % 2:
                    continue
                for m1 in magnetic_values(l1):
                    for m2 in magnetic_values(l2):
                        m3 = -m1 - m2
                        if not -l3 <= m3 <= l3:
                            continue
                        symbol = canonical((l1, m1, l2, m2, l3, m3))
                        if symbol not in symbols and nonzero_symbol(symbol):
                            symbols.append(symbol)
    return sorted(symbols, key=lambda s: (max(s[0], s[2], s[4]), s[0] + s[2] + s[4], s))


def params_from_symbol(symbol):
    return {
        "l1": int_text(symbol[0]),
        "m1": int_text(symbol[1]),
        "l2": int_text(symbol[2]),
        "m2": int_text(symbol[3]),
        "l3": int_text(symbol[4]),
        "m3": int_text(symbol[5]),
    }


def symbol_from_params(params):
    return (
        parse_int(params["l1"]),
        parse_int(params["m1"]),
        parse_int(params["l2"]),
        parse_int(params["m2"]),
        parse_int(params["l3"]),
        parse_int(params["m3"]),
    )


def sage_value(symbol, digits=DIGITS):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    l1, m1, l2, m2, l3, m3 = symbol
    value = sage_gaunt(ZZ(l1), ZZ(l2), ZZ(l3), ZZ(m1), ZZ(m2), ZZ(m3))
    return field(value)


def l_zero_value(symbol, digits=DIGITS):
    l1, m1, l2, m2, l3, m3 = symbol
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    if l1 == 0 and m1 == 0 and l2 == l3 and m2 == -m3:
        return field((-1) ** m2) / (2 * field.pi().sqrt())
    if l2 == 0 and m2 == 0 and l1 == l3 and m1 == -m3:
        return field((-1) ** m1) / (2 * field.pi().sqrt())
    if l3 == 0 and m3 == 0 and l1 == l2 and m1 == -m2:
        return field((-1) ** m1) / (2 * field.pi().sqrt())
    return None


def legendre_polynomials(up_to):
    ring = PolynomialRing(QQ, "x")
    x = ring.gen()
    polynomials = [ring(1)]
    if up_to >= 1:
        polynomials.append(x)
    for n in range(1, up_to):
        polynomials.append(
            ((2 * n + 1) * x * polynomials[n] - n * polynomials[n - 1])
            * (QQ(1) / QQ(n + 1))
        )
    return polynomials


def legendre_triple_integral(l1, l2, l3):
    polynomials = legendre_polynomials(max(l1, l2, l3))
    product = polynomials[l1] * polynomials[l2] * polynomials[l3]
    total = QQ(0)
    for degree, coefficient in product.dict().items():
        if degree % 2 == 0:
            total += QQ(2) * QQ(coefficient) / QQ(degree + 1)
    return total


def m_zero_value(symbol, digits=DIGITS):
    l1, m1, l2, m2, l3, m3 = symbol
    if (m1, m2, m3) != (0, 0, 0):
        return None
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    scale = field((2 * l1 + 1) * (2 * l2 + 1) * (2 * l3 + 1)).sqrt()
    return scale * field(legendre_triple_integral(l1, l2, l3)) / (4 * field.pi().sqrt())


def find_admissible_zero(up_to=L_UP_TO):
    for l1 in range(up_to + 1):
        for l2 in range(up_to + 1):
            for l3 in range(abs(l1 - l2), min(up_to, l1 + l2) + 1):
                if (l1 + l2 + l3) % 2:
                    continue
                for m1 in magnetic_values(l1):
                    for m2 in magnetic_values(l2):
                        m3 = -m1 - m2
                        if not -l3 <= m3 <= l3:
                            continue
                        symbol = (l1, m1, l2, m2, l3, m3)
                        if not nonzero_symbol(symbol) and symbol != (0, 0, 0, 0, 0, 0):
                            return symbol
    return None


def run_checks(symbols):
    for symbol in symbols:
        value = gaunt_ball(symbol, DIGITS)
        expected = sage_value(symbol, DIGITS)
        if not overlaps(value, expected):
            raise AssertionError("Sage disagrees at %s: %s vs %s" % (symbol, value, expected))

        for image in symbol_images(symbol):
            other = gaunt_ball(image, DIGITS)
            if not overlaps(value, other):
                raise AssertionError("symmetry disagrees at %s and %s" % (symbol, image))

        special = l_zero_value(symbol, DIGITS)
        if special is not None and not overlaps(value, special):
            raise AssertionError("l=0 special case disagrees at %s" % (symbol,))

        legendre = m_zero_value(symbol, DIGITS)
        if legendre is not None and not overlaps(value, legendre):
            raise AssertionError("Legendre integral disagrees at %s" % (symbol,))

    zero = find_admissible_zero()
    if zero is None:
        raise AssertionError("no admissible but vanishing example found")


class GauntCoefficients(numberdb.Generator):
    table = TID
    parameters = ("l1", "m1", "l2", "m2", "l3", "m3")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def __init__(self):
        super().__init__()
        self._symbols = enumerate_symbols()
        run_checks(self._symbols)

    def enumerate(self):
        for symbol in self._symbols:
            yield params_from_symbol(symbol)

    def value(self, params, digits):
        symbol = symbol_from_params(params)
        if canonical(symbol) != symbol:
            raise ValueError("%s is not the canonical representative" % (symbol,))
        value = gaunt_ball(symbol, digits)
        if value == 0:
            raise ValueError("%s is a zero row" % (symbol,))
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = GauntCoefficients()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="computed from exact Wigner 3j sums"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
