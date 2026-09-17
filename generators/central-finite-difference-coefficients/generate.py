"""Central finite difference coefficients -- numberdb.org/T303

For integers m >= 1 and r >= ceil(m/2), the central finite difference
coefficients a_{m,r,j} are defined by

    h^m f^(m)(x) ~= sum_{j=-r}^r a_{m,r,j} f(x + j h),

with equality for every polynomial f of degree at most 2r. This table stores
the exact rational, nonzero coefficients for 1 <= m <= 6 and
ceil(m/2) <= r <= 5.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The coefficients are computed by solving the moment equations exactly over QQ.
Before any entry is returned, the whole stencil is checked against the
moments, the parity symmetry, the first nonzero error moment, the quoted rows
on Wikipedia where the row is printed, the noncentral closed formulas there,
and the central coefficients obtained from the Lagrange-product formula.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.matrix.constructor import matrix
from sage.modules.free_module_element import vector
from sage.rings.rational_field import QQ


MAX_M = 6
MAX_R = 5


QUOTED_ROWS = {
    (1, 1): ("-1/2", "0", "1/2"),
    (1, 2): ("1/12", "-2/3", "0", "2/3", "-1/12"),
    (1, 3): ("-1/60", "3/20", "-3/4", "0", "3/4", "-3/20", "1/60"),
    (1, 4): ("1/280", "-4/105", "1/5", "-4/5", "0", "4/5", "-1/5", "4/105", "-1/280"),
    (2, 1): ("1", "-2", "1"),
    (2, 2): ("-1/12", "4/3", "-5/2", "4/3", "-1/12"),
    (2, 3): ("1/90", "-3/20", "3/2", "-49/18", "3/2", "-3/20", "1/90"),
    (2, 4): ("-1/560", "8/315", "-1/5", "8/5", "-205/72", "8/5", "-1/5", "8/315", "-1/560"),
    (3, 2): ("-1/2", "1", "0", "-1", "1/2"),
    (3, 3): ("1/8", "-1", "13/8", "0", "-13/8", "1", "-1/8"),
    (3, 4): ("-7/240", "3/10", "-169/120", "61/30", "0", "-61/30", "169/120", "-3/10", "7/240"),
    (4, 2): ("1", "-4", "6", "-4", "1"),
    (4, 3): ("-1/6", "2", "-13/2", "28/3", "-13/2", "2", "-1/6"),
    (4, 4): ("7/240", "-2/5", "169/60", "-122/15", "91/8", "-122/15", "169/60", "-2/5", "7/240"),
    (5, 3): ("-1/2", "2", "-5/2", "0", "5/2", "-2", "1/2"),
    (5, 4): ("1/6", "-3/2", "13/3", "-29/6", "0", "29/6", "-13/3", "3/2", "-1/6"),
    (5, 5): ("-13/288", "19/36", "-87/32", "13/2", "-323/48", "0", "323/48", "-13/2", "87/32", "-19/36", "13/288"),
    (6, 3): ("1", "-6", "15", "-20", "15", "-6", "1"),
    (6, 4): ("-1/4", "3", "-13", "29", "-75/2", "29", "-13", "3", "-1/4"),
    (6, 5): ("13/240", "-19/24", "87/16", "-39/2", "323/8", "-1023/20", "323/8", "-39/2", "87/16", "-19/24", "13/240"),
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


def _accuracy(m, r):
    first = 2 * r + 1
    if (first - m) % 2:
        first += 1
    return first - m


def _row_comment(m, r):
    accuracy = _accuracy(m, r)
    form = _common_denominator_form(row(m, r))
    return "Derivative order $m=%d$, %d-order central formula: %s." % (m, accuracy, form)


def _harmonic(r, s):
    total = QQ(0)
    for k in range(1, r + 1):
        total += QQ(1) / (QQ(k) ** s)
    return total


def _signed_power_minus_one(exponent):
    return QQ(1) if exponent % 2 == 0 else QQ(-1)


def _central_formula(m, r):
    """The derivative at 0 of prod_k (1 - x^2/k^2)."""
    if m % 2:
        return QQ(0)
    degree = m // 2
    terms = [QQ(1)]
    for k in range(1, r + 1):
        factor = QQ(-1) / (QQ(k) ** 2)
        terms.append(QQ(0))
        for index in range(len(terms) - 2, -1, -1):
            terms[index + 1] += terms[index] * factor
    return QQ(factorial(m)) * terms[degree]


def _closed_formula(m, r, j):
    """Closed forms independent of the moment solve."""
    if j == 0:
        return _central_formula(m, r)
    p = int(j)
    h2 = _harmonic(r, 2)
    h4 = _harmonic(r, 4)
    base = (
        QQ(factorial(m))
        * _signed_power_minus_one(p + 1)
        * QQ(factorial(r)) ** 2
        / (QQ(p) ** m * QQ(factorial(r - p)) * QQ(factorial(r + p)))
    )
    if m in (1, 2):
        return base
    if m in (3, 4):
        return base * (1 - QQ(p) ** 2 * h2)
    if m in (5, 6):
        return base * (1 - QQ(p) ** 2 * h2 + (QQ(p) ** 4 / 2) * (h2 ** 2 - h4))
    raise ValueError("closed formula not implemented for m=%s" % m)


def _solve_row(m, r):
    offsets = list(range(-r, r + 1))
    rows = []
    for q in range(2 * r + 1):
        rows.append([QQ(j) ** q for j in offsets])
    system = matrix(QQ, rows)
    rhs = vector(QQ, [QQ(factorial(m)) if q == m else QQ(0) for q in range(2 * r + 1)])
    return tuple(system.solve_right(rhs))


def _moment(row_values, m, r, q):
    return sum(value * QQ(j) ** q for j, value in zip(range(-r, r + 1), row_values))


def _check_row(m, r, row_values):
    if len(row_values) != 2 * r + 1:
        raise ArithmeticError("m=%d r=%d: got %d coefficients" % (m, r, len(row_values)))
    for q in range(2 * r + 1):
        expected = QQ(factorial(m)) if q == m else QQ(0)
        if _moment(row_values, m, r, q) != expected:
            raise ArithmeticError("m=%d r=%d: moment %d disagrees" % (m, r, q))
    first_error = 2 * r + 1
    while (first_error - m) % 2:
        if _moment(row_values, m, r, first_error) != 0:
            raise ArithmeticError("m=%d r=%d: parity error moment %d is nonzero" % (m, r, first_error))
        first_error += 1
    if _moment(row_values, m, r, first_error) == 0:
        raise ArithmeticError("m=%d r=%d: first error moment vanished" % (m, r))
    for offset in range(-r, r + 1):
        if row_values[offset + r] != ((-1) ** m) * row_values[-offset + r]:
            raise ArithmeticError("m=%d r=%d: symmetry fails at j=%d" % (m, r, offset))
    for offset, value in zip(range(-r, r + 1), row_values):
        if value != _closed_formula(m, r, offset):
            raise ArithmeticError("m=%d r=%d j=%d: closed formula disagrees" % (m, r, offset))
    if (m, r) in QUOTED_ROWS:
        quoted = tuple(QQ(value) for value in QUOTED_ROWS[(m, r)])
        if row_values != quoted:
            raise ArithmeticError("m=%d r=%d: quoted row disagrees" % (m, r))


def row(m, r):
    m = int(m)
    r = int(r)
    if m < 1:
        raise ValueError("m must be positive")
    if r < (m + 1) // 2:
        raise ValueError("r=%d is too small for derivative order m=%d" % (r, m))
    key = (m, r)
    if key not in _ROWS:
        solved = _solve_row(m, r)
        _check_row(m, r, solved)
        _ROWS[key] = solved
    return _ROWS[key]


class CentralFiniteDifferenceCoefficients(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T303")
    parameters = ("m", "r", "j")
    type = "Q"
    rigour = "exact"

    def enumerate(self, max_m=MAX_M, max_r=MAX_R):
        for m in range(1, max_m + 1):
            for r in range((m + 1) // 2, max_r + 1):
                values = row(m, r)
                for index, value in enumerate(values):
                    if value == 0:
                        continue
                    yield {"m": str(m), "r": str(r), "j": str(index - r)}

    def value(self, params, digits=None):
        m = int(params["m"])
        r = int(params["r"])
        j = int(params["j"])
        value = row(m, r)[j + r]
        if value == 0:
            raise ValueError("zero coefficients are omitted")
        if j == -r:
            return {"number": value, "comment": _row_comment(m, r)}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = CentralFiniteDifferenceCoefficients()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="central finite difference coefficients"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
