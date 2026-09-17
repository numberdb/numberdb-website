"""Newton-Cotes weights -- numberdb.org/T302

For n >= 1, the closed Newton-Cotes rule on the equally spaced nodes
0, 1, ..., n is

    int_0^n f(x) dx  ~  sum_{j=0}^n w_{n,j} f(j).

This table stores the exact rational weights w_{n,j} and the unit-interval
Cotes numbers C_{n,j} = w_{n,j}/n for 1 <= n <= 12.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The weights are computed by solving the moment equations exactly over QQ:
sum_j w_{n,j} j^m = n^(m+1)/(m+1), 0 <= m <= n. Before any entry is returned,
the row is checked against the moments, the symmetry, the unit-interval
normalisation, the OEIS A093735/A093736 prefix, and the quoted named rules.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.matrix.constructor import matrix
from sage.modules.free_module_element import vector
from sage.rings.rational_field import QQ


MAX_N = 12
NORMALISATIONS = ("step", "unit-interval")

RULE_NAMES = {
    1: "Trapezoidal rule",
    2: "Simpson's rule",
    3: "Simpson's 3/8 rule",
    4: "Boole's rule",
}

QUOTED_ROWS = {
    1: ("1/2", "1/2"),
    2: ("1/3", "4/3", "1/3"),
    3: ("3/8", "9/8", "9/8", "3/8"),
    4: ("14/45", "64/45", "8/15", "64/45", "14/45"),
}

OEIS_NUMERATORS = (
    1, 1,
    1, 4, 1,
    3, 9, 9, 3,
    14, 64, 8, 64, 14,
    95, 125, 125, 125, 125, 95,
    41, 54, 27, 68, 27, 54, 41,
    5257, 25039, 343, 20923, 20923, 343, 25039, 5257,
    3956, 23552, -3712, 41984, -3632, 41984, -3712, 23552, 3956,
    25713, 141669, 243, 10881, 26001,
)

OEIS_DENOMINATORS = (
    2, 2,
    3, 3, 3,
    8, 8, 8, 8,
    45, 45, 15, 45, 45,
    288, 96, 144, 144, 96, 288,
    140, 35, 140, 35, 140, 35, 140,
    17280, 17280, 640, 17280, 17280, 640, 17280, 17280,
    14175, 14175, 14175, 14175, 2835, 14175, 14175, 14175, 14175,
    89600, 89600, 2240, 5600, 44800,
)

OEIS_PREFIX = tuple(
    QQ(a) / QQ(b) for a, b in zip(OEIS_NUMERATORS, OEIS_DENOMINATORS)
)

_WEIGHTS = {}


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


def _moment(n, m):
    return QQ(n) ** (m + 1) / QQ(m + 1)


def _solve_weights(n):
    rows = []
    for m in range(n + 1):
        rows.append([QQ(j) ** m for j in range(n + 1)])
    system = matrix(QQ, rows)
    moments = vector(QQ, [_moment(n, m) for m in range(n + 1)])
    return tuple(system.solve_right(moments))


def _oeis_start(n):
    return (n - 1) * (n + 2) // 2


def _check_oeis(n, weights):
    start = _oeis_start(n)
    if start >= len(OEIS_PREFIX):
        return
    width = min(n + 1, len(OEIS_PREFIX) - start)
    expected = OEIS_PREFIX[start:start + width]
    if tuple(weights[:width]) != expected:
        raise ArithmeticError("n=%d: OEIS prefix disagrees" % n)


def _check_row(n, weights):
    if len(weights) != n + 1:
        raise ArithmeticError("n=%d: got %d weights" % (n, len(weights)))
    if any(w == 0 for w in weights):
        raise ArithmeticError("n=%d: a zero weight would need to be omitted" % n)
    for m in range(n + 1):
        got = sum(weights[j] * QQ(j) ** m for j in range(n + 1))
        if got != _moment(n, m):
            raise ArithmeticError("n=%d: moment %d disagrees" % (n, m))
    extra = n + 1
    got = sum(weights[j] * QQ(j) ** extra for j in range(n + 1))
    if n % 2 == 0:
        if got != _moment(n, extra):
            raise ArithmeticError("n=%d: even-row extra moment disagrees" % n)
        first_failure = n + 2
    else:
        if got == _moment(n, extra):
            raise ArithmeticError("n=%d: odd row should fail at degree n+1" % n)
        first_failure = extra
    failed = sum(weights[j] * QQ(j) ** first_failure for j in range(n + 1))
    if failed == _moment(n, first_failure):
        raise ArithmeticError("n=%d: first failure did not fail" % n)
    for j in range(n + 1):
        if weights[j] != weights[n - j]:
            raise ArithmeticError("n=%d: symmetry fails at j=%d" % (n, j))
    if sum(weights) != QQ(n):
        raise ArithmeticError("n=%d: weights do not sum to n" % n)
    cotes = tuple(w / QQ(n) for w in weights)
    if sum(cotes) != 1:
        raise ArithmeticError("n=%d: Cotes numbers do not sum to 1" % n)
    if n in QUOTED_ROWS:
        expected = tuple(QQ(x) for x in QUOTED_ROWS[n])
        if weights != expected:
            raise ArithmeticError("n=%d: quoted row disagrees" % n)
    _check_oeis(n, weights)


def weights(n):
    n = int(n)
    if n < 1:
        raise ValueError("n must be positive")
    if n not in _WEIGHTS:
        row = _solve_weights(n)
        _check_row(n, row)
        _WEIGHTS[n] = row
    return _WEIGHTS[n]


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


def _rule_comment(n):
    form = _common_denominator_form(weights(n))
    if n in RULE_NAMES:
        return "%s: %s." % (RULE_NAMES[n], form)
    return "The closed Newton-Cotes rule with $n=%d$: %s." % (n, form)


class NewtonCotesWeights(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T302")
    parameters = ("n", "j", "normalisation")
    type = "Q"
    rigour = "exact"

    def enumerate(self, max_n=MAX_N):
        for n in range(1, max_n + 1):
            row = weights(n)
            for j, value in enumerate(row):
                if value == 0:
                    continue
                for normalisation in NORMALISATIONS:
                    yield {
                        "n": str(n),
                        "j": str(j),
                        "normalisation": normalisation,
                    }

    def value(self, params, digits=None):
        n = int(params["n"])
        j = int(params["j"])
        value = weights(n)[j]
        if params["normalisation"] == "unit-interval":
            value = value / QQ(n)
        elif params["normalisation"] != "step":
            raise ValueError("unknown normalisation %r" % params["normalisation"])
        if j == 0 and params["normalisation"] == "step":
            return {"number": value, "comment": _rule_comment(n)}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = NewtonCotesWeights()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Newton-Cotes weights"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
