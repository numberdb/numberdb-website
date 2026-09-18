"""Adams-Moulton coefficients -- numberdb.org/T306

For s >= 0, the s-step Adams-Moulton method is

    y_{n+s} = y_{n+s-1} + h * sum_{j=0}^{s} beta^*_{s,j} f_{n+j}.

This table stores the exact rational coefficients beta^*_{s,j}, indexed from
the oldest value to the newest one, for 0 <= s <= 12.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The coefficients are computed by solving the moment equations exactly over QQ:
sum_j beta^*_{s,j} j^m = (s^(m+1) - (s-1)^(m+1))/(m+1), 0 <= m <= s.
Before any entry is returned, the whole row is checked against the moments,
against the integral of the Lagrange basis polynomial, against the
Adams-Moulton rows through s = 4 quoted in the source, against two OEIS
triangles, and against the Gregory-coefficient identity from the Bernoulli
polynomials of the second kind.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.matrix.constructor import matrix
from sage.modules.free_module_element import vector
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


MAX_S = 12

QUOTED_ROWS = {
    0: ("1",),
    1: ("1/2", "1/2"),
    2: ("-1/12", "2/3", "5/12"),
    3: ("1/24", "-5/24", "19/24", "3/8"),
    4: ("-19/720", "53/360", "-11/30", "323/360", "251/720"),
}

# OEIS rows are printed from newest to oldest, as in the literature. Each row
# is divided by its own sum before comparison, so unreduced rows are accepted.
OEIS_A260781 = {
    0: (1,),
    1: (1, 1),
    2: (5, 8, -1),
    3: (27, 57, -15, 3),
    4: (502, 1292, -528, 212, -38),
    5: (2375, 7135, -3990, 2410, -865, 135),
}

OEIS_A235936 = {
    0: (1,),
    1: (1, 1),
    2: (5, 8, -1),
    3: (9, 19, -5, 1),
    4: (251, 646, -264, 106, -19),
    5: (475, 1427, -798, 482, -173, 27),
    6: (19087, 65112, -46461, 37504, -20211, 6312, -863),
    7: (36799, 139849, -121797, 123133, -88547, 41499, -11351, 1375),
}

_ROWS = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _lcm(a, b):
    return abs(a * b) // gcd(a, b)


def _latex_rational(q):
    q = QQ(q)
    numerator = int(q.numerator())
    denominator = int(q.denominator())
    if denominator == 1:
        return str(numerator)
    sign = "-" if numerator < 0 else ""
    return r"%s\tfrac{%d}{%d}" % (sign, abs(numerator), denominator)


def _common_denominator_form(row):
    denominator = 1
    for value in row:
        denominator = _lcm(denominator, int(value.denominator()))
    numerators = [int(value * denominator) for value in row]
    content = 0
    for numerator in numerators:
        content = gcd(content, abs(numerator))
    reduced = [numerator // content for numerator in numerators]
    factor = QQ(content) / QQ(denominator)
    return "$%s(%s)$" % (_latex_rational(factor), ",".join(str(n) for n in reduced))


def _moment(s, m):
    return (QQ(s) ** (m + 1) - QQ(s - 1) ** (m + 1)) / QQ(m + 1)


def _solve_row(s):
    nodes = list(range(s + 1))
    rows = [[QQ(j) ** m for j in nodes] for m in range(s + 1)]
    system = matrix(QQ, rows)
    moments = vector(QQ, [_moment(s, m) for m in range(s + 1)])
    return tuple(system.solve_right(moments))


def _lagrange_integral(s, j):
    ring = PolynomialRing(QQ, "x")
    x = ring.gen()
    basis = ring(1)
    for k in range(s + 1):
        if k != j:
            basis *= (x - k) * (QQ(1) / QQ(j - k))
    anti = basis.integral()
    return anti(s) - anti(s - 1)


def _psi_at_zero(n):
    ring = PolynomialRing(QQ, "u")
    u = ring.gen()
    value = ring(1)
    for k in range(n):
        value *= u - k
    return value.integral()(1) - value.integral()(0)


def _gregory_star(n):
    return ((-1) ** n) * _psi_at_zero(n) / QQ(factorial(n))


def _row_from_integer_numerators(numerators):
    denominator = sum(numerators)
    return tuple(QQ(value) / QQ(denominator) for value in numerators)


def _check_oeis_row(s, values, source, name):
    if s not in source:
        return
    newest_first = tuple(reversed(values))
    expected = _row_from_integer_numerators(source[s])
    if newest_first != expected:
        raise ArithmeticError("s=%d: %s row disagrees" % (s, name))


def _check_row(s, values):
    if len(values) != s + 1:
        raise ArithmeticError("s=%d: got %d coefficients" % (s, len(values)))
    if any(value == 0 for value in values):
        raise ArithmeticError("s=%d: a zero coefficient would need to be omitted" % s)
    for m in range(s + 1):
        got = sum(values[j] * QQ(j) ** m for j in range(s + 1))
        if got != _moment(s, m):
            raise ArithmeticError("s=%d: moment %d disagrees" % (s, m))
    if sum(values[j] * QQ(j) ** (s + 1) for j in range(s + 1)) == _moment(s, s + 1):
        raise ArithmeticError("s=%d: first unforced moment did not fail" % s)
    for j, value in enumerate(values):
        if value != _lagrange_integral(s, j):
            raise ArithmeticError("s=%d j=%d: Lagrange integral disagrees" % (s, j))
    if values[0] != ((-1) ** s) * _gregory_star(s):
        raise ArithmeticError("s=%d: Gregory coefficient identity disagrees" % s)
    if s in QUOTED_ROWS:
        quoted = tuple(QQ(value) for value in QUOTED_ROWS[s])
        if values != quoted:
            raise ArithmeticError("s=%d: quoted row disagrees" % s)
    _check_oeis_row(s, values, OEIS_A260781, "OEIS A260781")
    _check_oeis_row(s, values, OEIS_A235936, "OEIS A235936")


def row(s):
    s = int(s)
    if s < 0:
        raise ValueError("s must be nonnegative")
    if s not in _ROWS:
        solved = _solve_row(s)
        _check_row(s, solved)
        _ROWS[s] = solved
    return _ROWS[s]


def _method_comment(s):
    newest_first = tuple(reversed(row(s)))
    form = _common_denominator_form(newest_first)
    if s == 0:
        return "Backward Euler method: $1$."
    if s == 1:
        return "Trapezoidal rule, from newest to oldest: %s." % form
    return "%d-step Adams-Moulton formula, from newest to oldest: %s." % (s, form)


class AdamsMoultonCoefficients(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T306")
    parameters = ("s", "j")
    type = "Q"
    rigour = "exact"

    def enumerate(self, max_s=MAX_S):
        for s in range(0, max_s + 1):
            values = row(s)
            for j, value in enumerate(values):
                if value == 0:
                    continue
                yield {"s": str(s), "j": str(j)}

    def value(self, params, digits=None):
        s = int(params["s"])
        j = int(params["j"])
        value = row(s)[j]
        if value == 0:
            raise ValueError("zero coefficients are omitted")
        if j == 0:
            return {"number": value, "comment": _method_comment(s)}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = AdamsMoultonCoefficients()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Adams-Moulton coefficients"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
