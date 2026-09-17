"""Backward differentiation formula coefficients -- numberdb.org/T307

For 1 <= s <= 6, the s-step BDF method is

    sum_{j=0}^s alpha_{s,j} y_{n+j} = h * beta_s * f(t_{n+s}, y_{n+s}).

This table stores the exact rational coefficients in two normalisations:
alpha_{s,s} = 1 and beta_s = 1. Rows fixed to 1 by the normalisation are
omitted.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The coefficients are computed by solving the order conditions exactly over QQ
in the beta_s = 1 normalisation:
sum_j alpha_{s,j} j^q = q * s^(q-1), 1 <= q <= s, with sum_j alpha_{s,j}=0.
Before any entry is returned, each row is checked against those moments,
against the derivative of the Lagrange basis at the newest node, against the
closed backward-difference formula, and against the six BDF formulas quoted
in the source.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.matrix.constructor import matrix
from sage.modules.free_module_element import vector
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


MAX_S = 6
NORMALISATIONS = ("alpha-s-one", "nabla")

QUOTED_ALPHA_NEWEST_FIRST = {
    1: ((1, 1), (-1, 1)),
    2: ((1, 1), (-4, 3), (1, 3)),
    3: ((1, 1), (-18, 11), (9, 11), (-2, 11)),
    4: ((1, 1), (-48, 25), (36, 25), (-16, 25), (3, 25)),
    5: ((1, 1), (-300, 137), (300, 137), (-200, 137), (75, 137), (-12, 137)),
    6: ((1, 1), (-360, 147), (450, 147), (-400, 147), (225, 147), (-72, 147), (10, 147)),
}

QUOTED_BETA = {
    1: (1, 1),
    2: (2, 3),
    3: (6, 11),
    4: (12, 25),
    5: (60, 137),
    6: (60, 147),
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


def _rational(pair):
    numerator, denominator = pair
    return QQ(numerator) / QQ(denominator)


def _harmonic(s):
    return sum(QQ(1) / QQ(k) for k in range(1, s + 1))


def _solve_nabla_row(s):
    nodes = list(range(s + 1))
    rows = [[QQ(j) ** q for j in nodes] for q in range(s + 1)]
    rhs = [QQ(0)] + [QQ(q) * QQ(s) ** (q - 1) for q in range(1, s + 1)]
    return tuple(matrix(QQ, rows).solve_right(vector(QQ, rhs)))


def _lagrange_derivative(s, j):
    ring = PolynomialRing(QQ, "x")
    x = ring.gen()
    basis = ring(1)
    for k in range(s + 1):
        if k != j:
            basis *= (x - k) * (QQ(1) / QQ(j - k))
    return basis.derivative()(s)


def _closed_nabla_coefficient(s, j):
    if j == s:
        return _harmonic(s)
    return QQ((-1) ** (s - j)) * QQ(binomial(s, j)) / QQ(s - j)


def _alpha_s_one_row(nabla):
    harmonic = nabla[-1]
    return tuple(value / harmonic for value in nabla), QQ(1) / harmonic


def _check_nabla_row(s, values):
    if len(values) != s + 1:
        raise ArithmeticError("s=%d: got %d coefficients" % (s, len(values)))
    if any(value == 0 for value in values):
        raise ArithmeticError("s=%d: a zero coefficient would need to be omitted" % s)
    for q in range(s + 1):
        got = sum(values[j] * QQ(j) ** q for j in range(s + 1))
        expected = QQ(0) if q == 0 else QQ(q) * QQ(s) ** (q - 1)
        if got != expected:
            raise ArithmeticError("s=%d: moment %d disagrees" % (s, q))
    if sum(values[j] * QQ(j) ** (s + 1) for j in range(s + 1)) == QQ(s + 1) * QQ(s) ** s:
        raise ArithmeticError("s=%d: first unforced moment did not fail" % s)
    for j, value in enumerate(values):
        if value != _lagrange_derivative(s, j):
            raise ArithmeticError("s=%d j=%d: Lagrange derivative disagrees" % (s, j))
        if value != _closed_nabla_coefficient(s, j):
            raise ArithmeticError("s=%d j=%d: closed nabla formula disagrees" % (s, j))


def _check_alpha_s_one_row(s, alpha, beta):
    if alpha[s] != 1:
        raise ArithmeticError("s=%d: alpha_s is not 1" % s)
    for q in range(s + 1):
        got = sum(alpha[j] * QQ(j) ** q for j in range(s + 1))
        expected = QQ(0) if q == 0 else QQ(q) * beta * QQ(s) ** (q - 1)
        if got != expected:
            raise ArithmeticError("s=%d: scaled moment %d disagrees" % (s, q))
    quoted_alpha = tuple(reversed(tuple(_rational(pair) for pair in QUOTED_ALPHA_NEWEST_FIRST[s])))
    if alpha != quoted_alpha:
        raise ArithmeticError("s=%d: quoted alpha row disagrees" % s)
    if beta != _rational(QUOTED_BETA[s]):
        raise ArithmeticError("s=%d: quoted beta disagrees" % s)


def _check_row(s, nabla):
    _check_nabla_row(s, nabla)
    alpha, beta = _alpha_s_one_row(nabla)
    _check_alpha_s_one_row(s, alpha, beta)


def nabla_row(s):
    s = int(s)
    if s < 1 or s > MAX_S:
        raise ValueError("s must satisfy 1 <= s <= %d" % MAX_S)
    if s not in _ROWS:
        solved = _solve_nabla_row(s)
        _check_row(s, solved)
        _ROWS[s] = solved
    return _ROWS[s]


def coefficients(s, normalisation):
    nabla = nabla_row(s)
    if normalisation == "nabla":
        return tuple(nabla), QQ(1)
    if normalisation == "alpha-s-one":
        return _alpha_s_one_row(nabla)
    raise ValueError("unknown normalisation %r" % normalisation)


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
    return denominator, r"$\tfrac{1}{%d}(%s)$" % (
        denominator, ",".join(str(n) for n in numerators)
    )


def _method_comment(s):
    alpha, beta = coefficients(s, "alpha-s-one")
    newest_first = tuple(reversed(alpha))
    denominator, form = _common_denominator_form(newest_first)
    beta_numerator = int(beta * denominator)
    beta_text = _latex_rational(QQ(beta_numerator) / QQ(denominator))
    if s == 1:
        return "Backward Euler method, from newest to oldest: %s, with $\\beta_1=%s$." % (form, beta_text)
    return "%d-step BDF formula, from newest to oldest: %s, with $\\beta_%d=%s$." % (
        s, form, s, beta_text)


def _coefficient_label(key):
    if key == "beta":
        return r"$\beta_s$"
    if key.startswith("alpha_"):
        return r"$\alpha_{s,%s}$" % key.split("_", 1)[1]
    raise ValueError("unknown coefficient key %r" % key)


def _entries(s, normalisation):
    alpha, beta = coefficients(s, normalisation)
    out = []
    for j, value in enumerate(alpha):
        if normalisation == "alpha-s-one" and j == s:
            continue
        key = "alpha_%d" % j
        out.append((key, value))
    if normalisation != "nabla":
        out.append(("beta", beta))
    return tuple(out)


class BackwardDifferentiationFormulaCoefficients(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T307")
    parameters = ("s", "normalisation", "coefficient")
    type = "Q"
    rigour = "exact"

    def enumerate(self, max_s=MAX_S):
        for s in range(1, max_s + 1):
            for normalisation in NORMALISATIONS:
                for key, _value in _entries(s, normalisation):
                    yield {
                        "s": str(s),
                        "normalisation": normalisation,
                        "coefficient": key,
                    }

    def value(self, params, digits=None):
        s = int(params["s"])
        normalisation = params["normalisation"]
        key = params["coefficient"]
        for index, (entry_key, value) in enumerate(_entries(s, normalisation)):
            if entry_key != key:
                continue
            record = {"number": value, "param-latex": _coefficient_label(key)}
            if normalisation == "alpha-s-one" and index == 0:
                record["comment"] = _method_comment(s)
            return record
        raise ValueError("no coefficient %r for s=%d, normalisation=%s"
                         % (key, s, normalisation))


if __name__ == "__main__":
    _key_from_stdin()
    generator = BackwardDifferentiationFormulaCoefficients()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Backward differentiation formula coefficients"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
