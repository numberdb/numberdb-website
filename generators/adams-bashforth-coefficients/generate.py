"""Adams-Bashforth coefficients -- numberdb.org/T305

For s >= 1, the s-step Adams-Bashforth method is

    y_{n+s} = y_{n+s-1} + h * sum_{j=0}^{s-1} beta_{s,j} f_{n+j}.

This table stores the exact rational coefficients beta_{s,j}, indexed from
the oldest value to the newest one, for 1 <= s <= 12.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The coefficients are computed by solving the moment equations exactly over QQ:
sum_j beta_{s,j} j^m = (s^(m+1) - (s-1)^(m+1))/(m+1), 0 <= m <= s-1.
Before any entry is returned, the whole row is checked against the moments,
against the integral of the Lagrange basis polynomial, and against the
Adams-Bashforth rows through s = 5 quoted in the source.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.matrix.constructor import matrix
from sage.modules.free_module_element import vector
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


MAX_S = 12

QUOTED_ROWS = {
    1: ("1",),
    2: ("-1/2", "3/2"),
    3: ("5/12", "-16/12", "23/12"),
    4: ("-9/24", "37/24", "-59/24", "55/24"),
    5: ("251/720", "-1274/720", "2616/720", "-2774/720", "1901/720"),
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
    nodes = list(range(s))
    rows = [[QQ(j) ** m for j in nodes] for m in range(s)]
    system = matrix(QQ, rows)
    moments = vector(QQ, [_moment(s, m) for m in range(s)])
    return tuple(system.solve_right(moments))


def _lagrange_integral(s, j):
    ring = PolynomialRing(QQ, "x")
    x = ring.gen()
    basis = ring(1)
    for k in range(s):
        if k != j:
            basis *= (x - k) * (QQ(1) / QQ(j - k))
    anti = basis.integral()
    return anti(s) - anti(s - 1)


def _check_row(s, values):
    if len(values) != s:
        raise ArithmeticError("s=%d: got %d coefficients" % (s, len(values)))
    if any(value == 0 for value in values):
        raise ArithmeticError("s=%d: a zero coefficient would need to be omitted" % s)
    for m in range(s):
        got = sum(values[j] * QQ(j) ** m for j in range(s))
        if got != _moment(s, m):
            raise ArithmeticError("s=%d: moment %d disagrees" % (s, m))
    if sum(values[j] * QQ(j) ** s for j in range(s)) == _moment(s, s):
        raise ArithmeticError("s=%d: first unforced moment did not fail" % s)
    for j, value in enumerate(values):
        if value != _lagrange_integral(s, j):
            raise ArithmeticError("s=%d j=%d: Lagrange integral disagrees" % (s, j))
    if s in QUOTED_ROWS:
        quoted = tuple(QQ(value) for value in QUOTED_ROWS[s])
        if values != quoted:
            raise ArithmeticError("s=%d: quoted row disagrees" % s)


def row(s):
    s = int(s)
    if s < 1:
        raise ValueError("s must be positive")
    if s not in _ROWS:
        solved = _solve_row(s)
        _check_row(s, solved)
        _ROWS[s] = solved
    return _ROWS[s]


def _method_comment(s):
    newest_first = tuple(reversed(row(s)))
    form = _common_denominator_form(newest_first)
    if s == 1:
        return "Euler method: %s." % form
    return "%d-step Adams-Bashforth formula, from newest to oldest: %s." % (s, form)


class AdamsBashforthCoefficients(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T305")
    parameters = ("s", "j")
    type = "Q"
    rigour = "exact"

    def enumerate(self, max_s=MAX_S):
        for s in range(1, max_s + 1):
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
    generator = AdamsBashforthCoefficients()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Adams-Bashforth coefficients"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
