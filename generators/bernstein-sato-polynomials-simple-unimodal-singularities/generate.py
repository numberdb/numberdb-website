"""Bernstein-Sato polynomials of the simple and unimodal singularities -- numberdb.org/T290

For each listed modulus-zero normal form f and each number n of variables
from the corank through 3, this stores the exact local Bernstein-Sato
polynomial b_f(s) in Q[s].

The generator computes the weights and a monomial basis of the Milnor algebra,
then uses the weighted-homogeneous formula

    b_f(s) = (s + 1) prod_alpha (s + alpha),

where alpha ranges over the distinct values sum_i w_i + deg_w(m) for Milnor
algebra basis monomials m.  In self-check mode it compares every row with
Singular's bfct from bfun.lib, in a fresh Singular session for each row.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ NUMBERDB_SELF_CHECK=1 agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generate.py
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = "T290"
VARIABLES = ("x", "y", "z")
MAX_A = 12
MAX_D = 12

_S = PolynomialRing(QQ, "s")
_s = _S.gen()


class Singularity:

    def __init__(self, label, weights, monomials, latex):
        self.label = label
        self.weights = tuple(QQ(weight) for weight in weights)
        self.monomials = tuple(
            (QQ(coefficient), tuple(exponents))
            for coefficient, exponents in monomials
        )
        self.latex = latex
        self.mu = int(re.search(r"\d+$", label).group(0))

    @property
    def corank(self):
        return len(self.weights)


def q(n, d=1):
    return QQ(n) / QQ(d)


def singularities():
    for k in range(1, MAX_A + 1):
        yield Singularity(
            "A%d" % k,
            (q(1, k + 1),),
            ((1, (k + 1,)),),
            "x^{%d}" % (k + 1),
        )

    for k in range(4, MAX_D + 1):
        yield Singularity(
            "D%d" % k,
            (q(k - 2, 2 * (k - 1)), q(1, k - 1)),
            ((1, (2, 1)), (1, (0, k - 1))),
            "x^2y+y^{%d}" % (k - 1),
        )

    fixed = [
        Singularity("E6", (q(1, 3), q(1, 4)),
                    ((1, (3, 0)), (1, (0, 4))), "x^3+y^4"),
        Singularity("E7", (q(1, 3), q(2, 9)),
                    ((1, (3, 0)), (1, (1, 3))), "x^3+xy^3"),
        Singularity("E8", (q(1, 3), q(1, 5)),
                    ((1, (3, 0)), (1, (0, 5))), "x^3+y^5"),
        Singularity("P8", (q(1, 3), q(1, 3), q(1, 3)),
                    ((1, (3, 0, 0)), (1, (0, 3, 0)),
                     (1, (0, 0, 3))), "x^3+y^3+z^3"),
        Singularity("X9", (q(1, 4), q(1, 4)),
                    ((1, (4, 0)), (1, (0, 4))), "x^4+y^4"),
        Singularity("J10", (q(1, 3), q(1, 6)),
                    ((1, (3, 0)), (1, (0, 6))), "x^3+y^6"),
        Singularity("E12", (q(1, 3), q(1, 7)),
                    ((1, (3, 0)), (1, (0, 7))), "x^3+y^7"),
        Singularity("E13", (q(1, 3), q(2, 15)),
                    ((1, (3, 0)), (1, (1, 5))), "x^3+xy^5"),
        Singularity("E14", (q(1, 3), q(1, 8)),
                    ((1, (3, 0)), (1, (0, 8))), "x^3+y^8"),
        Singularity("Z11", (q(4, 15), q(1, 5)),
                    ((1, (3, 1)), (1, (0, 5))), "x^3y+y^5"),
        Singularity("Z12", (q(3, 11), q(2, 11)),
                    ((1, (3, 1)), (1, (1, 4))), "x^3y+xy^4"),
        Singularity("Z13", (q(5, 18), q(1, 6)),
                    ((1, (3, 1)), (1, (0, 6))), "x^3y+y^6"),
        Singularity("W12", (q(1, 4), q(1, 5)),
                    ((1, (4, 0)), (1, (0, 5))), "x^4+y^5"),
        Singularity("W13", (q(1, 4), q(3, 16)),
                    ((1, (4, 0)), (1, (1, 4))), "x^4+xy^4"),
        Singularity("Q10", (q(1, 3), q(1, 4), q(3, 8)),
                    ((1, (3, 0, 0)), (1, (0, 4, 0)),
                     (1, (0, 1, 2))), "x^3+y^4+yz^2"),
        Singularity("Q11", (q(1, 3), q(7, 18), q(2, 9)),
                    ((1, (3, 0, 0)), (1, (0, 2, 1)),
                     (1, (1, 0, 3))), "x^3+y^2z+xz^3"),
        Singularity("Q12", (q(1, 3), q(1, 5), q(2, 5)),
                    ((1, (3, 0, 0)), (1, (0, 5, 0)),
                     (1, (0, 1, 2))), "x^3+y^5+yz^2"),
        Singularity("S11", (q(1, 4), q(5, 16), q(3, 8)),
                    ((1, (4, 0, 0)), (1, (0, 2, 1)),
                     (1, (1, 0, 2))), "x^4+y^2z+xz^2"),
        Singularity("S12", (q(4, 13), q(5, 13), q(3, 13)),
                    ((1, (2, 1, 0)), (1, (0, 2, 1)),
                     (1, (1, 0, 3))), "x^2y+y^2z+xz^3"),
        Singularity("U12", (q(1, 3), q(1, 3), q(1, 4)),
                    ((1, (3, 0, 0)), (1, (0, 3, 0)),
                     (1, (0, 0, 4))), "x^3+y^3+z^4"),
    ]
    for item in fixed:
        yield item


SPECS = tuple(singularities())
SPEC_BY_LABEL = {spec.label: spec for spec in SPECS}

BASIS_EXPONENTS = {
    "A1": [(0,)],
    "A2": [(0,), (1,)],
    "A3": [(0,), (1,), (2,)],
    "A4": [(0,), (1,), (2,), (3,)],
    "A5": [(0,), (1,), (2,), (3,), (4,)],
    "A6": [(0,), (1,), (2,), (3,), (4,), (5,)],
    "A7": [(0,), (1,), (2,), (3,), (4,), (5,), (6,)],
    "A8": [(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,)],
    "A9": [(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,)],
    "A10": [(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)],
    "A11": [(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,)],
    "A12": [(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,), (11,)],
    "D4": [(0, 0), (0, 1), (1, 0), (0, 2)],
    "D5": [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0)],
    "D6": [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (0, 3)],
    "D7": [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (0, 3), (0, 4)],
    "D8": [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (0, 3), (0, 4), (0, 5)],
    "D9": [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (0, 3), (0, 4), (0, 5), (0, 6)],
    "D10": [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7)],
    "D11": [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8)],
    "D12": [(0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9)],
    "E6": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (1, 2)],
    "E7": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0), (2, 1)],
    "E8": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (0, 3), (1, 2), (1, 3)],
    "P8": [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0), (1, 1, 1)],
    "X9": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0), (1, 2), (2, 1), (2, 2)],
    "J10": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (0, 3), (1, 2), (0, 4), (1, 3), (1, 4)],
    "E12": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (0, 3), (1, 2), (0, 4), (1, 3), (0, 5), (1, 4), (1, 5)],
    "E13": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0), (0, 3), (1, 2), (2, 1), (0, 4), (1, 3), (2, 2), (2, 3)],
    "E14": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (0, 3), (1, 2), (0, 4), (1, 3), (0, 5), (1, 4), (0, 6), (1, 5), (1, 6)],
    "Z11": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0), (0, 3), (1, 2), (3, 0), (1, 3), (4, 0)],
    "Z12": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0), (0, 3), (1, 2), (2, 1), (3, 0), (2, 2), (4, 0)],
    "Z13": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0), (0, 3), (1, 2), (3, 0), (0, 4), (1, 3), (4, 0), (1, 4)],
    "W12": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0), (0, 3), (1, 2), (2, 1), (1, 3), (2, 2), (2, 3)],
    "W13": [(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0), (0, 3), (1, 2), (2, 1), (3, 0), (2, 2), (3, 1), (3, 2)],
    "Q10": [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), (0, 0, 2), (0, 2, 0), (1, 0, 1), (1, 1, 0), (1, 0, 2), (1, 2, 0)],
    "Q11": [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), (0, 0, 2), (0, 2, 0), (1, 0, 1), (1, 1, 0), (2, 0, 0), (1, 2, 0), (2, 0, 1)],
    "Q12": [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), (0, 0, 2), (0, 2, 0), (1, 0, 1), (1, 1, 0), (0, 3, 0), (1, 0, 2), (1, 2, 0), (1, 3, 0)],
    "S11": [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), (0, 0, 2), (1, 0, 1), (1, 1, 0), (2, 0, 0), (0, 0, 3), (2, 0, 1), (2, 1, 0)],
    "S12": [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), (0, 0, 2), (0, 1, 1), (0, 2, 0), (1, 0, 1), (1, 1, 0), (0, 1, 2), (0, 3, 0), (1, 1, 1)],
    "U12": [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), (0, 0, 2), (0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 1, 2), (1, 0, 2), (1, 1, 1), (1, 1, 2)],
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def milnor_basis_exponents(spec):
    return BASIS_EXPONENTS[spec.label]


def alpha_values(spec, n):
    shift = QQ(n - spec.corank) / QQ(2)
    base = sum(spec.weights) + shift
    values = set()
    for exponents in milnor_basis_exponents(spec):
        degree = sum(QQ(power) * weight
                     for power, weight in zip(exponents, spec.weights))
        values.add(base + degree)
    return sorted(values)


def bernstein_sato_polynomial(label, n):
    spec = SPEC_BY_LABEL[label]
    polynomial = _s + 1
    for alpha in alpha_values(spec, ZZ(n)):
        polynomial *= _s + alpha
    return polynomial


def rational_latex(value):
    value = QQ(value)
    if value.denominator() == 1:
        return str(value.numerator())
    return r"\frac{%s}{%s}" % (value.numerator(), value.denominator())


def factor_latex(alphas):
    counts = {QQ(1): 1}
    for alpha in alphas:
        counts[alpha] = counts.get(alpha, 0) + 1

    factors = []
    for alpha in sorted(counts):
        if alpha == 1:
            factor = "(s+1)"
        else:
            factor = r"\left(s+%s\right)" % rational_latex(alpha)
        if counts[alpha] > 1:
            factor += "^{%d}" % counts[alpha]
        factors.append(factor)
    return "".join(factors)


def normal_form_latex(spec, n):
    pieces = [spec.latex]
    for variable in VARIABLES[spec.corank:n]:
        pieces.append("%s^2" % variable)
    return "+".join(pieces)


def entry_comment(spec, n):
    alphas = alpha_values(spec, n)
    lct = min([QQ(1)] + alphas)
    return (
        r"Normal form $f=%s$; $\mu=%d$; $\operatorname{lct}(f)=%s$. "
        r"Factored form: $b_f(s)=%s$."
        % (normal_form_latex(spec, n), spec.mu, rational_latex(lct),
           factor_latex(alphas))
    )


def singular_expression(spec, n):
    terms = []
    for coefficient, exponents in spec.monomials:
        factors = []
        if coefficient != 1:
            factors.append(str(coefficient))
        for variable, exponent in zip(VARIABLES, exponents):
            if exponent == 0:
                continue
            if exponent == 1:
                factors.append(variable)
            else:
                factors.append("%s^%d" % (variable, exponent))
        terms.append("*".join(factors))
    for variable in VARIABLES[spec.corank:n]:
        terms.append("%s^2" % variable)
    return "+".join(terms)


def parse_singular_roots(roots_text, multiplicities_text):
    roots = [QQ(match) for match in re.findall(r"_\[\d+\]=(-?\d+(?:/\d+)?)",
                                               roots_text)]
    multiplicities = [
        int(part.strip())
        for part in multiplicities_text.strip().split(",")
        if part.strip()
    ]
    if len(roots) != len(multiplicities):
        raise AssertionError("could not parse Singular roots %r and %r"
                             % (roots_text, multiplicities_text))
    return list(zip(roots, multiplicities))


def singular_b_polynomial(spec, n):
    from sage.interfaces.singular import Singular

    singular = Singular()
    singular.eval('LIB "bfun.lib";')
    singular.eval("ring r = 0,(%s),dp;" % ",".join(VARIABLES[:n]))
    singular.eval("poly F = %s;" % singular_expression(spec, n))
    singular.eval("list B = bfct(F);")
    roots = parse_singular_roots(singular.eval("B[1];"),
                                 singular.eval("B[2];"))
    polynomial = _S.one()
    for root, multiplicity in roots:
        for _ in range(multiplicity):
            polynomial *= _s - root
    return polynomial


def self_check():
    control = Singularity(
        "control2", (q(1, 2), q(1, 3)),
        ((1, (2, 0)), (1, (0, 3))), "x^2+y^3")
    expected = (_s + 1) * (_s + q(5, 6)) * (_s + q(7, 6))
    got = singular_b_polynomial(control, 2)
    if got != expected:
        raise AssertionError("Singular bfct control returned %s, not %s"
                             % (got, expected))

    checked = 0
    for spec in SPECS:
        if len(milnor_basis_exponents(spec)) != spec.mu:
            raise AssertionError("%s has wrong Milnor basis length" % spec.label)
        for n in range(spec.corank, 4):
            formula = bernstein_sato_polynomial(spec.label, n)
            independent = singular_b_polynomial(spec, n)
            if formula != independent:
                raise AssertionError(
                    "%s n=%d: formula gives %s, Singular gives %s"
                    % (spec.label, n, formula, independent))
            checked += 1
    print("checked %d Bernstein-Sato polynomials against Singular bfct" % checked)


class BernsteinSatoSimpleUnimodal(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("singularity", "n")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self):
        for spec in SPECS:
            for n in range(spec.corank, 4):
                yield {"singularity": spec.label, "n": str(n)}

    def value(self, params, digits):
        label = params["singularity"]
        n = ZZ(params["n"])
        spec = SPEC_BY_LABEL[label]
        return {
            "number": bernstein_sato_polynomial(label, n),
            "comment": entry_comment(spec, n),
        }


if __name__ == "__main__":
    _key_from_stdin()
    if os.environ.get("NUMBERDB_SELF_CHECK") == "1":
        self_check()
        sys.exit(0)

    generator = BernsteinSatoSimpleUnimodal()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Bernstein-Sato singularity polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
