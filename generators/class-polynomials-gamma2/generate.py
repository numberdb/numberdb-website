"""Class polynomials of gamma_2 = j^(1/3) -- numberdb.org/T310.

For a negative discriminant Delta with Delta = 0 or 1 modulo 4 and
3 not dividing Delta, let H_Delta be the Hilbert class polynomial. This
generator fills T310 with the unique monic factor of H_Delta(x^3) whose
degree is deg(H_Delta), for every such Delta with |Delta| <= 300.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The polynomials are computed exactly from H_Delta(x^3), not from PARI's
class-polynomial routine. PARI's exact polynomial factorization is used to
factor H_Delta(x^3), and PARI's polclass(Delta, 5) is used only as an
independent convention check for the selected degree h(Delta) factor.
"""

import math
import os
import sys

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.schemes.elliptic_curves.cm import hilbert_class_polynomial


TABLE = os.environ.get("NUMBERDB_TABLE", "T310")
BOUND = 300
DIGITS = 100

ZX = PolynomialRing(ZZ, "x")
x = ZX.gen()


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
    return [
        ZZ(Delta)
        for Delta in range(-3, -bound - 1, -1)
        if Delta % 4 in (0, 1) and Delta % 3 != 0
    ]


def _pari_factor(polynomial):
    """Exact factorization over ZZ, as Sage polynomials.

    Sage's polynomial factorization reaches parts of Sage that are not loaded
    by the named imports available in this build environment. PARI's factor is
    exact here and keeps the generator away from sage.all.
    """
    factored = pari(polynomial).factor()
    return [(ZX(factored[0][i]), ZZ(factored[1][i])) for i in range(len(factored[0]))]


def _hilbert_polynomial(Delta):
    return ZX(hilbert_class_polynomial(ZZ(Delta)))


def gamma2_class_polynomial(Delta):
    """The monic degree h(Delta) factor of H_Delta(x^3)."""
    Delta = ZZ(Delta)
    hilbert = _hilbert_polynomial(Delta)
    degree = hilbert.degree()
    composed = hilbert(x ** 3)
    factors = _pari_factor(composed)
    hits = [
        factor if factor.is_monic() else -factor
        for factor, multiplicity in factors
        if factor.degree() == degree and multiplicity == 1
    ]
    if len(hits) != 1:
        raise ArithmeticError(
            "Delta=%s: expected one degree %s factor, found %d"
            % (Delta, degree, len(hits))
        )
    polynomial = hits[0]

    other_degree = sum(
        factor.degree() * multiplicity
        for factor, multiplicity in factors
        if factor != polynomial and factor != -polynomial
    )
    if other_degree != 2 * degree:
        raise ArithmeticError(
            "Delta=%s: remaining factors have degree %s, not %s"
            % (Delta, other_degree, 2 * degree)
        )

    quotient, remainder = composed.quo_rem(polynomial)
    if remainder != 0 or quotient.degree() != 2 * degree:
        raise ArithmeticError("Delta=%s: selected factor does not divide H_Delta(x^3)" % Delta)

    pari_polynomial = ZX(pari.polclass(Delta, 5))
    if polynomial != pari_polynomial:
        raise ArithmeticError(
            "Delta=%s: factor gives %s but PARI polclass gives %s"
            % (Delta, polynomial, pari_polynomial)
        )
    return polynomial


def fundamental_and_conductor(Delta):
    """(Delta0, f), where Delta = f^2 Delta0 and Delta0 is fundamental."""
    Delta = ZZ(Delta)
    conductor = ZZ(1)
    g = ZZ(2)
    while g * g <= -Delta:
        if Delta % (g * g) == 0 and (Delta // (g * g)) % 4 in (0, 1):
            conductor = g
        g += 1
    return Delta // (conductor * conductor), conductor


def _field_latex(fundamental):
    d = fundamental if fundamental % 4 == 1 else fundamental // 4
    if d == -1:
        return r"\mathbb{Q}(i)"
    return r"\mathbb{Q}(\sqrt{%d})" % d


def entry_comment(Delta, degree):
    Delta0, conductor = fundamental_and_conductor(Delta)
    field = _field_latex(Delta0)
    if conductor == 1:
        return r"$h(\Delta)=%d$; fundamental discriminant of $%s$" % (degree, field)
    return r"$h(\Delta)=%d$; order of conductor $%d$ in $%s$" % (
        degree,
        conductor,
        field,
    )


def reduced_primitive_form_count(Delta):
    """Count reduced primitive positive definite binary quadratic forms."""
    Delta = int(Delta)
    count = 0
    max_a = math.isqrt((-Delta) // 3) + 3
    for a in range(1, max_a + 1):
        for b in range(-a, a + 1):
            numerator = b * b - Delta
            denominator = 4 * a
            if numerator % denominator != 0:
                continue
            c = numerator // denominator
            if a > c:
                continue
            if math.gcd(math.gcd(abs(a), abs(b)), abs(c)) != 1:
                continue
            if (abs(b) == a or a == c) and b < 0:
                continue
            count += 1
    return ZZ(count)


class Gamma2ClassPolynomials(numberdb.Generator):
    """Generator for T310, the class polynomials of gamma_2."""

    table = TABLE
    parameters = ("Delta",)
    type = "Z[]"
    digits = DIGITS
    rigour = "exact"

    def enumerate(self, bound=BOUND):
        for Delta in discriminants(bound):
            yield {"Delta": str(Delta)}

    def value(self, params, digits):
        Delta = ZZ(params["Delta"])
        polynomial = gamma2_class_polynomial(Delta)
        return {"number": polynomial, "comment": entry_comment(Delta, polynomial.degree())}


def run_integrity_checks():
    values = []
    longest = (0, None)
    fundamental = 0
    nonfundamental = 0

    for Delta in discriminants():
        polynomial = gamma2_class_polynomial(Delta)
        degree = polynomial.degree()
        counted = reduced_primitive_form_count(Delta)
        if degree != counted:
            raise ArithmeticError(
                "Delta=%s: degree %s but counted %s reduced primitive forms"
                % (Delta, degree, counted)
            )
        Delta0, conductor = fundamental_and_conductor(Delta)
        if conductor == 1:
            fundamental += 1
        else:
            nonfundamental += 1
        text = str(polynomial)
        values.append(text)
        if len(text) > longest[0]:
            longest = (len(text), Delta)

    print("integrity checks passed for %d discriminants" % len(values))
    print("fundamental discriminants: %d; nonfundamental orders: %d" % (
        fundamental,
        nonfundamental,
    ))
    print("longest polynomial has %d characters at Delta=%s" % longest)
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
    generator = Gamma2ClassPolynomials()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="gamma2 class polynomials for |Delta| <= 300"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
