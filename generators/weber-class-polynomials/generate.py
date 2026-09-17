"""Weber class polynomials W_D -- numberdb.org/T308.

For a negative discriminant D congruent to 1 modulo 8, with 3 not dividing D,
put m = -D and

    omega_D = f(i sqrt(m)) / sqrt(2),
    f(tau) = eta(tau)^2 / (eta(tau/2) eta(2 tau)).

This generator fills T308 with the monic minimal polynomial W_D of omega_D,
for every such D with |D| < 1200.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The polynomials are computed exactly from the defining Weber value. For each
D, the generator forms the exact resultant of the ring class polynomial
H_{4D}(j) with

    (256 x^24 - 1)^3 - j x^24,

which is the relation for x = f(i sqrt(-D)) / sqrt(2). It factors the
resultant over ZZ and selects the unique factor whose interval evaluation at
the arb-computed Weber value contains zero. PARI's polclass(D, 1) is then used
only as an independent check: after the reciprocal transform, and after
x -> -x where PARI chose the opposite signed class invariant, it must give the
same polynomial.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.schemes.elliptic_curves.cm import hilbert_class_polynomial


TABLE = os.environ.get("NUMBERDB_TABLE", "T308")
BOUND = 1200
DIGITS = 100
SELECT_GUARD = 256

ZX = PolynomialRing(ZZ, "x")
QX = PolynomialRing(QQ, "x")
ZJ = PolynomialRing(ZZ, "j")
RESULTANT_RING = PolynomialRing(ZZ, ("x", "j"))
resultant_x, resultant_j = RESULTANT_RING.gens()
RELATION = (256 * resultant_x ** 24 - 1) ** 3 - resultant_j * resultant_x ** 24


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def discriminants(bound=BOUND):
    """The discriminants in table order."""
    return [ZZ(D) for D in range(-7, -bound, -1) if D % 8 == 1 and D % 3 != 0]


def _complex_field(digits=DIGITS, guard=SELECT_GUARD):
    return ComplexBallField(numberdb.bits(digits, losing=guard))


def weber_value(D, digits=DIGITS, guard=SELECT_GUARD):
    """omega_D = f(i sqrt(-D)) / sqrt(2), as a real ball."""
    field = _complex_field(digits, guard)
    tau = field.gen(0) * field(-ZZ(D)).sqrt()
    value = tau.modular_eta() ** 2 / ((tau / 2).modular_eta() * (2 * tau).modular_eta())
    if not value.imag().contains_zero():
        raise ArithmeticError("Weber value for D=%s has nonzero imaginary part: %s" % (D, value))
    real_field = value.real().parent()
    real = value.real() / real_field(2).sqrt()
    if not real.is_finite():
        raise ArithmeticError("Weber value for D=%s is not finite: %s" % (D, real))
    return real


def _primitive_part(polynomial):
    polynomial = ZX(polynomial)
    content = polynomial.content()
    if content == 0:
        raise ArithmeticError("zero resultant")
    return polynomial // content


def _hilbert_relation_factors(D):
    H = ZJ(hilbert_class_polynomial(4 * ZZ(D)))
    resultant = RESULTANT_RING(H(resultant_j)).resultant(RELATION, resultant_j)
    return _primitive_part(resultant).factor()


def _pari_reciprocal_transforms(D):
    """The possible W_D from PARI polclass(D, 1), depending on sign choice."""
    p = ZX(pari.polclass(ZZ(D), 1))
    degree = p.degree()
    possibilities = []
    for sign in (1, -1):
        coefficients = [ZZ(0)] * (degree + 1)
        for k, coefficient in enumerate(p.list()):
            coefficients[degree - k] = coefficient * (ZZ(sign) ** k)
        q = QX(coefficients)
        q = q * (QQ(1) / q.leading_coefficient())
        possibilities.append(ZX(q))
    return possibilities


def weber_class_polynomial(D, digits=DIGITS):
    """The monic minimal polynomial W_D."""
    D = ZZ(D)
    value = weber_value(D, digits)
    field = value.parent()
    hits = []
    for factor, multiplicity in _hilbert_relation_factors(D):
        evaluation = factor.change_ring(field)(value)
        if evaluation.contains_zero():
            hits.append((factor, multiplicity, evaluation))
    if len(hits) != 1:
        raise ArithmeticError("D=%s: expected one factor at omega_D, found %d: %s"
                              % (D, len(hits), [(f.degree(), e, v) for f, e, v in hits]))

    polynomial, multiplicity, _ = hits[0]
    if multiplicity < 1:
        raise ArithmeticError("D=%s: impossible factor multiplicity %s" % (D, multiplicity))
    if not polynomial.is_monic():
        polynomial = -polynomial

    pari_possibilities = _pari_reciprocal_transforms(D)
    if polynomial not in pari_possibilities:
        raise ArithmeticError("D=%s: resultant gives %s but PARI gives %s"
                              % (D, polynomial, pari_possibilities))
    return polynomial


def fundamental_and_conductor(D):
    """(D0, f), where D = f^2 D0 and D0 is fundamental."""
    D = ZZ(D)
    conductor = ZZ(1)
    g = ZZ(2)
    while g * g <= -D:
        if D % (g * g) == 0 and (D // (g * g)) % 4 in (0, 1):
            conductor = g
        g += 1
    return D // (conductor * conductor), conductor


def entry_comment(D, degree):
    D0, conductor = fundamental_and_conductor(D)
    field_d = D0 if D0 % 4 == 1 else D0 // 4
    field = r"\mathbb{Q}(i)" if field_d == -1 else r"\mathbb{Q}(\sqrt{%d})" % field_d
    if conductor == 1:
        return r"$h(D)=%d$; fundamental discriminant of $%s$" % (degree, field)
    return r"$h(D)=%d$; order of conductor $%d$ in $%s$" % (degree, conductor, field)


class WeberClassPolynomials(numberdb.Generator):
    """Generator for T308, Weber class polynomials W_D."""

    table = TABLE
    parameters = ("D",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, bound=BOUND):
        for D in discriminants(bound):
            yield {"D": str(D)}

    def value(self, params, digits):
        D = ZZ(params["D"])
        polynomial = weber_class_polynomial(D, digits)
        return {"number": polynomial, "comment": entry_comment(D, polynomial.degree())}


def run_integrity_checks():
    values = []
    signs = {1: 0, -1: 0}
    longest = (0, None)
    for D in discriminants():
        polynomial = weber_class_polynomial(D, DIGITS)
        first, second = _pari_reciprocal_transforms(D)
        if polynomial == first:
            signs[1] += 1
        elif polynomial == second:
            signs[-1] += 1
        else:
            raise ArithmeticError("PARI comparison was not recorded for D=%s" % D)
        text = str(polynomial)
        values.append(text)
        if len(text) > longest[0]:
            longest = (len(text), D)

    print("integrity checks passed for %d discriminants" % len(values))
    print("PARI reciprocal sign choices: +%d, -%d" % (signs[1], signs[-1]))
    print("longest polynomial has %d characters at D=%s" % longest)
    print("raw polynomial text is %.1f KB" % (sum(len(v) for v in values) / 1024.0))


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
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
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = WeberClassPolynomials()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Weber class polynomials for D congruent to 1 mod 8, |D| < 1200"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
