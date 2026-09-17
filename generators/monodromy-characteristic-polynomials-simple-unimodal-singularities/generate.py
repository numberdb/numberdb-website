"""Characteristic polynomials of the monodromy of the simple and unimodal singularities -- numberdb.org/T291

For each modulus-zero normal form f and each number n of variables from the
corank through 3, this stores the exact characteristic polynomial Delta_f(t)
of the geometric monodromy on the middle homology of the Milnor fibre.

The generator computes the rational monodromy exponents

    sum_i w_i + deg_w(m) + (n - c)/2,

where m runs through a monomial basis of the Milnor algebra and c is the
corank.  It then groups the corresponding roots of unity into cyclotomic
factors and expands the product in ZZ[t].

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
from sage.arith.misc import gcd
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = "T291"
VARIABLES = ("x", "y", "z")
MAX_A = 12
MAX_D = 12

_ZT = PolynomialRing(ZZ, "t")
_t = _ZT.gen()


class Singularity:

    def __init__(self, label, weights, monomials, latex, basis=None):
        self.label = label
        self.weights = tuple(QQ(weight) for weight in weights)
        self.monomials = tuple(
            (QQ(coefficient), tuple(exponents))
            for coefficient, exponents in monomials
        )
        self.latex = latex
        self.basis = None if basis is None else tuple(tuple(item) for item in basis)
        self.mu = int(re.search(r"\d+$", label).group(0))

    @property
    def corank(self):
        return len(self.weights)


def q(n, d=1):
    return QQ(n) / QQ(d)


def rectangle_basis(*bounds):
    if not bounds:
        return [()]
    out = []

    def extend(prefix, rest):
        if not rest:
            out.append(tuple(prefix))
            return
        for exponent in range(rest[0]):
            extend(prefix + [exponent], rest[1:])

    extend([], list(bounds))
    return out


def d_basis(k):
    return [(0, j) for j in range(k - 1)] + [(1, 0)]


def singularities():
    for k in range(1, MAX_A + 1):
        yield Singularity(
            "A%d" % k,
            (q(1, k + 1),),
            ((1, (k + 1,)),),
            "x^{%d}" % (k + 1),
            basis=[(j,) for j in range(k)],
        )

    for k in range(4, MAX_D + 1):
        yield Singularity(
            "D%d" % k,
            (q(k - 2, 2 * (k - 1)), q(1, k - 1)),
            ((1, (2, 1)), (1, (0, k - 1))),
            "x^2y+y^{%d}" % (k - 1),
            basis=d_basis(k),
        )

    fixed = [
        Singularity("E6", (q(1, 3), q(1, 4)),
                    ((1, (3, 0)), (1, (0, 4))), "x^3+y^4",
                    basis=rectangle_basis(2, 3)),
        Singularity("E7", (q(1, 3), q(2, 9)),
                    ((1, (3, 0)), (1, (1, 3))), "x^3+xy^3",
                    basis=[(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0),
                           (2, 1)]),
        Singularity("E8", (q(1, 3), q(1, 5)),
                    ((1, (3, 0)), (1, (0, 5))), "x^3+y^5",
                    basis=rectangle_basis(2, 4)),
        Singularity("P8", (q(1, 3), q(1, 3), q(1, 3)),
                    ((1, (3, 0, 0)), (1, (0, 3, 0)),
                     (1, (0, 0, 3))), "x^3+y^3+z^3",
                    basis=rectangle_basis(2, 2, 2)),
        Singularity("X9", (q(1, 4), q(1, 4)),
                    ((1, (4, 0)), (1, (0, 4))), "x^4+y^4",
                    basis=rectangle_basis(3, 3)),
        Singularity("J10", (q(1, 3), q(1, 6)),
                    ((1, (3, 0)), (1, (0, 6))), "x^3+y^6",
                    basis=rectangle_basis(2, 5)),
        Singularity("E12", (q(1, 3), q(1, 7)),
                    ((1, (3, 0)), (1, (0, 7))), "x^3+y^7",
                    basis=rectangle_basis(2, 6)),
        Singularity("E13", (q(1, 3), q(2, 15)),
                    ((1, (3, 0)), (1, (1, 5))), "x^3+xy^5",
                    basis=[(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0),
                           (0, 3), (1, 2), (2, 1), (0, 4), (1, 3), (2, 2),
                           (2, 3)]),
        Singularity("E14", (q(1, 3), q(1, 8)),
                    ((1, (3, 0)), (1, (0, 8))), "x^3+y^8",
                    basis=rectangle_basis(2, 7)),
        Singularity("Z11", (q(4, 15), q(1, 5)),
                    ((1, (3, 1)), (1, (0, 5))), "x^3y+y^5",
                    basis=[(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0),
                           (0, 3), (1, 2), (3, 0), (1, 3), (4, 0)]),
        Singularity("Z12", (q(3, 11), q(2, 11)),
                    ((1, (3, 1)), (1, (1, 4))), "x^3y+xy^4",
                    basis=[(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0),
                           (0, 3), (1, 2), (2, 1), (3, 0), (2, 2), (4, 0)]),
        Singularity("Z13", (q(5, 18), q(1, 6)),
                    ((1, (3, 1)), (1, (0, 6))), "x^3y+y^6",
                    basis=[(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0),
                           (0, 3), (1, 2), (3, 0), (0, 4), (1, 3), (4, 0),
                           (1, 4)]),
        Singularity("W12", (q(1, 4), q(1, 5)),
                    ((1, (4, 0)), (1, (0, 5))), "x^4+y^5",
                    basis=rectangle_basis(3, 4)),
        Singularity("W13", (q(1, 4), q(3, 16)),
                    ((1, (4, 0)), (1, (1, 4))), "x^4+xy^4",
                    basis=[(0, 0), (0, 1), (1, 0), (0, 2), (1, 1), (2, 0),
                           (0, 3), (1, 2), (2, 1), (3, 0), (2, 2), (3, 1),
                           (3, 2)]),
        Singularity("Q10", (q(1, 3), q(1, 4), q(3, 8)),
                    ((1, (3, 0, 0)), (1, (0, 4, 0)),
                     (1, (0, 1, 2))), "x^3+y^4+yz^2",
                    basis=[(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0),
                           (0, 0, 2), (0, 2, 0), (1, 0, 1), (1, 1, 0),
                           (1, 0, 2), (1, 2, 0)]),
        Singularity("Q11", (q(1, 3), q(7, 18), q(2, 9)),
                    ((1, (3, 0, 0)), (1, (0, 2, 1)),
                     (1, (1, 0, 3))), "x^3+y^2z+xz^3",
                    basis=[(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0),
                           (0, 0, 2), (0, 2, 0), (1, 0, 1), (1, 1, 0),
                           (2, 0, 0), (1, 2, 0), (2, 0, 1)]),
        Singularity("Q12", (q(1, 3), q(1, 5), q(2, 5)),
                    ((1, (3, 0, 0)), (1, (0, 5, 0)),
                     (1, (0, 1, 2))), "x^3+y^5+yz^2",
                    basis=[(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0),
                           (0, 0, 2), (0, 2, 0), (1, 0, 1), (1, 1, 0),
                           (0, 3, 0), (1, 0, 2), (1, 2, 0), (1, 3, 0)]),
        Singularity("S11", (q(1, 4), q(5, 16), q(3, 8)),
                    ((1, (4, 0, 0)), (1, (0, 2, 1)),
                     (1, (1, 0, 2))), "x^4+y^2z+xz^2",
                    basis=[(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0),
                           (0, 0, 2), (1, 0, 1), (1, 1, 0), (2, 0, 0),
                           (0, 0, 3), (2, 0, 1), (2, 1, 0)]),
        Singularity("S12", (q(4, 13), q(5, 13), q(3, 13)),
                    ((1, (2, 1, 0)), (1, (0, 2, 1)),
                     (1, (1, 0, 3))), "x^2y+y^2z+xz^3",
                    basis=[(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0),
                           (0, 0, 2), (0, 1, 1), (0, 2, 0), (1, 0, 1),
                           (1, 1, 0), (0, 1, 2), (0, 3, 0), (1, 1, 1)]),
        Singularity("U12", (q(1, 3), q(1, 3), q(1, 4)),
                    ((1, (3, 0, 0)), (1, (0, 3, 0)),
                     (1, (0, 0, 4))), "x^3+y^3+z^4",
                    basis=rectangle_basis(2, 2, 3)),
    ]
    for item in fixed:
        yield item


SPECS = tuple(singularities())
SPEC_BY_LABEL = {spec.label: spec for spec in SPECS}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def milnor_basis_exponents(spec):
    return spec.basis


def monodromy_exponents(spec, n):
    shift = QQ(n - spec.corank) / QQ(2)
    base = sum(spec.weights) + shift
    values = []
    for exponents in milnor_basis_exponents(spec):
        degree = sum(QQ(power) * weight
                     for power, weight in zip(exponents, spec.weights))
        values.append(base + degree)
    return values


def cyclotomic_factors_from_exponents(exponents):
    residues_by_order = {}
    for exponent in exponents:
        exponent = QQ(exponent)
        denominator = ZZ(exponent.denominator())
        numerator = ZZ(exponent.numerator()) % denominator
        if numerator == 0:
            order = ZZ(1)
            residue = ZZ(0)
        else:
            order = denominator
            residue = (-numerator) % order
        residues = residues_by_order.setdefault(order, {})
        residues[residue] = residues.get(residue, 0) + 1

    factors = []
    for order in sorted(residues_by_order, key=int):
        residues = residues_by_order[order]
        if order == 1:
            units = [ZZ(0)]
        else:
            units = [ZZ(r) for r in range(1, int(order) + 1)
                     if gcd(ZZ(r), order) == 1]
        multiplicities = [residues.get(unit % order, 0) for unit in units]
        if len(set(multiplicities)) != 1:
            raise ArithmeticError(
                "roots of order %s are not a full Galois orbit: %s"
                % (order, residues))
        if multiplicities[0]:
            factors.append((order, multiplicities[0]))
    return factors


def polynomial_from_cyclotomic_factors(factors):
    polynomial = _ZT.one()
    for order, multiplicity in factors:
        polynomial *= _ZT.cyclotomic_polynomial(int(order)) ** int(multiplicity)
    return polynomial


def monodromy_polynomial(label, n):
    spec = SPEC_BY_LABEL[label]
    return polynomial_from_cyclotomic_factors(
        cyclotomic_factors_from_exponents(monodromy_exponents(spec, ZZ(n))))


def factor_latex(factors):
    pieces = []
    for order, multiplicity in factors:
        factor = r"\Phi_{%s}(t)" % order
        if multiplicity > 1:
            factor += "^{%d}" % multiplicity
        pieces.append(factor)
    return r"\,".join(pieces) if pieces else "1"


def normal_form_latex(spec, n):
    pieces = [spec.latex]
    for variable in VARIABLES[spec.corank:n]:
        pieces.append("%s^2" % variable)
    return "+".join(pieces)


def entry_comment(spec, n):
    factors = cyclotomic_factors_from_exponents(monodromy_exponents(spec, n))
    return (
        r"$f=%s$, with $\mu=%d$; $\Delta_f(t)=%s$."
        % (normal_form_latex(spec, n), spec.mu, factor_latex(factors))
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


def parse_singular_spectrum(values_text, multiplicities_text):
    values = [QQ(match) for match in re.findall(r"_\[\d+\]=(-?\d+(?:/\d+)?)",
                                                values_text)]
    multiplicities = [
        int(part.strip())
        for part in multiplicities_text.strip().split(",")
        if part.strip()
    ]
    if len(values) != len(multiplicities):
        raise AssertionError("could not parse Singular spectrum %r and %r"
                             % (values_text, multiplicities_text))
    out = []
    for value, multiplicity in zip(values, multiplicities):
        out.extend([value] * multiplicity)
    return out


def singular_spectrum_polynomial(spec, n):
    from sage.interfaces.singular import Singular

    singular = Singular()
    singular.eval('LIB "gmssing.lib";')
    singular.eval("ring r = 0,(%s),ds;" % ",".join(VARIABLES[:n]))
    singular.eval("poly F = %s;" % singular_expression(spec, n))
    singular.eval("list S = spectrum(F);")
    exponents = parse_singular_spectrum(singular.eval("S[1];"),
                                        singular.eval("S[2];"))
    return polynomial_from_cyclotomic_factors(
        cyclotomic_factors_from_exponents(exponents))


def coxeter_exponents(label):
    letter = label[0]
    rank = int(label[1:])
    if letter == "A":
        return rank + 1, list(range(1, rank + 1))
    if letter == "D":
        return 2 * rank - 2, list(range(1, 2 * rank - 2, 2)) + [rank - 1]
    if label == "E6":
        return 12, [1, 4, 5, 7, 8, 11]
    if label == "E7":
        return 18, [1, 5, 7, 9, 11, 13, 17]
    if label == "E8":
        return 30, [1, 7, 11, 13, 17, 19, 23, 29]
    raise ValueError("no Coxeter exponents for %s" % label)


def coxeter_polynomial(label):
    h, exponents = coxeter_exponents(label)
    return polynomial_from_cyclotomic_factors(
        cyclotomic_factors_from_exponents(QQ(m) / QQ(h) for m in exponents))


def run_integrity_checks():
    for spec in SPECS:
        if len(milnor_basis_exponents(spec)) != spec.mu:
            raise AssertionError("%s has wrong Milnor basis length" % spec.label)
        for n in range(spec.corank, 4):
            polynomial = monodromy_polynomial(spec.label, n)
            if polynomial.degree() != spec.mu:
                raise AssertionError("%s n=%d has degree %d, not mu=%d"
                                     % (spec.label, n, polynomial.degree(),
                                        spec.mu))
            if n < 3:
                suspended = monodromy_polynomial(spec.label, n + 1)
                expected = (-1) ** spec.mu * polynomial(-_t)
                if suspended != expected:
                    raise AssertionError("%s n=%d suspension gives %s, not %s"
                                         % (spec.label, n, suspended, expected))
        if spec.label[0] in ("A", "D") or spec.label in ("E6", "E7", "E8"):
            if monodromy_polynomial(spec.label, 3) != coxeter_polynomial(spec.label):
                raise AssertionError("%s n=3 disagrees with Coxeter exponents"
                                     % spec.label)


def run_singular_checks():
    control = Singularity(
        "control2", (q(1, 2), q(1, 3)),
        ((1, (2, 0)), (1, (0, 3))), "x^2+y^3")
    expected = _t**2 - _t + 1
    got = singular_spectrum_polynomial(control, 2)
    if got != expected:
        raise AssertionError("Singular spectrum control returned %s, not %s"
                             % (got, expected))

    checked = 0
    for spec in SPECS:
        for n in range(spec.corank, 4):
            formula = monodromy_polynomial(spec.label, n)
            independent = singular_spectrum_polynomial(spec, n)
            if formula != independent:
                raise AssertionError(
                    "%s n=%d: formula gives %s, Singular spectrum gives %s"
                    % (spec.label, n, formula, independent))
            checked += 1
    print("checked %d monodromy polynomials against Singular spectrum" % checked)


class MonodromyCharacteristicSimpleUnimodal(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("singularity", "n")
    type = "Z[]"
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
            "number": monodromy_polynomial(label, n),
            "comment": entry_comment(spec, n),
        }


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries, to_text

    table = generator.table
    run = _run_name(generator)
    entries = Entries(*generator.parameters)

    for params in generator.enumerate():
        params = dict(params)
        wanted = generator.digits_for(params)
        entry = generator._entry(params, wanted)
        value = entry["number"]
        identity = ",".join(str(params[name]) for name in generator.parameters)
        _check_rigour(generator, table, identity, value)

        written = to_text(value, wanted, generator.format)
        _check_precision(table, identity, written, wanted, lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=wanted)

    answer = submit_entries(
        table,
        entries,
        message=message,
        produced_by=_producer(generator, os.environ.get("NUMBERDB_ASSISTED_BY", "")),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = MonodromyCharacteristicSimpleUnimodal()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_SELF_CHECK") == "1":
        run_singular_checks()
        sys.exit(0)

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact singularity monodromy characteristic polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
