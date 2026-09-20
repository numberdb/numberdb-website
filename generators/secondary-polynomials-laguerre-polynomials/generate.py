"""Secondary polynomials of the Laguerre polynomials q_n -- numberdb.org/T370.

This generator fills the table of secondary polynomials

    q_n(x) = integral_0^infinity (L_n(t) - L_n(x)) / (t - x) e^-t dt

where L_n is the Laguerre polynomial with L_n(0) = 1. The Laguerre weight
e^-t on [0, infinity) has total mass 1, so this is the probability-normalised
convention used by the family numberdb-data#172. It answers
numberdb-data#93.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import json
import math
import os
import sys
import urllib.request
from fractions import Fraction

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T370")
UP_TO = 30

R = PolynomialRing(QQ, "x")
x = R.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def laguerre_polynomials(up_to=UP_TO):
    """The L_n used by T102, built from the exact three-term recurrence."""
    polynomials = [R.one()]
    if up_to == 0:
        return polynomials
    polynomials.append(R.one() - x)
    for n in range(1, up_to):
        next_polynomial = (
            (QQ(2 * n + 1) - x) * polynomials[n]
            - QQ(n) * polynomials[n - 1]
        )
        next_polynomial *= QQ(1) / QQ(n + 1)
        polynomials.append(R(next_polynomial))
    return polynomials


def secondary_polynomials(up_to=UP_TO):
    """The q_n, built from the recurrence shared with L_n."""
    polynomials = [R.zero()]
    if up_to == 0:
        return polynomials
    polynomials.append(-R.one())
    for n in range(1, up_to):
        next_polynomial = (
            (QQ(2 * n + 1) - x) * polynomials[n]
            - QQ(n) * polynomials[n - 1]
        )
        next_polynomial *= QQ(1) / QQ(n + 1)
        polynomials.append(R(next_polynomial))
    return polynomials


def moment_secondary_polynomial(laguerre):
    """Evaluate the defining integral using the moments int t^i e^-t dt."""
    total = R.zero()
    for j, coefficient in enumerate(laguerre.list()):
        for i in range(j):
            total += coefficient * QQ(factorial(i)) * x ** (j - 1 - i)
    return R(total)


def _fraction_polynomial_text(coefficients):
    total = R.zero()
    for degree, coefficient in enumerate(coefficients):
        total += QQ(coefficient.numerator) / QQ(coefficient.denominator) * x ** degree
    return R(total)


def fraction_moment_secondary(n):
    """The same moment formula, using only Python's Fraction arithmetic."""
    coefficients = [Fraction(0) for _ in range(max(n, 1))]
    for j in range(1, n + 1):
        laguerre_coefficient = (
            Fraction((-1) ** j)
            * Fraction(math.comb(n, j), math.factorial(j))
        )
        for degree in range(j):
            moment = math.factorial(j - 1 - degree)
            coefficients[degree] += laguerre_coefficient * moment
    return _fraction_polynomial_text(coefficients)


def _harmonic_number(n):
    total = QQ(0)
    for k in range(1, n + 1):
        total += QQ(1) / QQ(k)
    return total


def _reversed_at_infinity(polynomial, degree):
    """Return y^degree * polynomial(1/y) as coefficients in y."""
    out = [QQ(0) for _ in range(degree + 1)]
    for power, coefficient in enumerate(polynomial.list()):
        out[degree - power] = QQ(coefficient)
    return out


def _series_product(left, right, through):
    out = [QQ(0) for _ in range(through + 1)]
    for i, a in enumerate(left):
        if not a:
            continue
        for j, b in enumerate(right):
            if i + j > through:
                break
            out[i + j] += a * b
    return out


def _check_recurrence(laguerre, secondary):
    if secondary[0] != 0 or secondary[1] != -1:
        raise ArithmeticError("initial secondary polynomials are wrong")
    for n in range(1, UP_TO):
        expected = ((QQ(2 * n + 1) - x) * secondary[n]
                    - QQ(n) * secondary[n - 1])
        expected *= QQ(1) / QQ(n + 1)
        if secondary[n + 1] != expected:
            raise ArithmeticError("secondary recurrence failed at n=%d" % n)
    for n in range(1, UP_TO):
        expected = ((QQ(2 * n + 1) - x) * laguerre[n]
                    - QQ(n) * laguerre[n - 1])
        expected *= QQ(1) / QQ(n + 1)
        if laguerre[n + 1] != expected:
            raise ArithmeticError("Laguerre recurrence failed at n=%d" % n)


def _check_moment_definition(laguerre, secondary):
    for n in range(UP_TO + 1):
        if secondary[n] != moment_secondary_polynomial(laguerre[n]):
            raise ArithmeticError("moment definition failed at n=%d" % n)
        if secondary[n] != fraction_moment_secondary(n):
            raise ArithmeticError("Python Fraction check failed at n=%d" % n)


def _check_special_values(secondary):
    for n in range(1, UP_TO + 1):
        if secondary[n].degree() != n - 1:
            raise ArithmeticError("degree failed at n=%d" % n)
        leading = secondary[n].monomial_coefficient(x ** (n - 1))
        if leading != QQ((-1) ** n) / QQ(factorial(n)):
            raise ArithmeticError("leading coefficient failed at n=%d" % n)
        if secondary[n](0) != -_harmonic_number(n):
            raise ArithmeticError("q_n(0) failed at n=%d" % n)


def _check_quadrature_congruence(laguerre, secondary):
    """At a root of L_n, q_n/L_n' equals 1/(x L_n'^2)."""
    for n in range(1, UP_TO + 1):
        polynomial = x * secondary[n] * laguerre[n].derivative() - 1
        if polynomial.mod(laguerre[n]):
            raise ArithmeticError("Gauss-Laguerre weight identity failed at n=%d" % n)


def _check_pade(laguerre, secondary):
    moments = [QQ(0)] + [QQ(factorial(k)) for k in range(2 * UP_TO + 1)]
    for n in range(1, UP_TO + 1):
        denominator = _reversed_at_infinity(laguerre[n], n)
        numerator = _reversed_at_infinity(secondary[n], n)
        product = _series_product(denominator, moments, 2 * n)
        difference = [
            product[i] - (numerator[i] if i < len(numerator) else QQ(0))
            for i in range(2 * n + 1)
        ]
        if any(difference[1:2 * n + 1]):
            raise ArithmeticError("Pade condition failed at n=%d" % n)


def run_integrity_checks(values=None):
    laguerre = laguerre_polynomials()
    secondary = secondary_polynomials() if values is None else values
    _check_recurrence(laguerre, secondary)
    _check_moment_definition(laguerre, secondary)
    _check_special_values(secondary)
    _check_quadrature_congruence(laguerre, secondary)
    _check_pade(laguerre, secondary)
    print("integrity checks passed for q_0 through q_%d" % UP_TO)


class LaguerreSecondaryPolynomials(numberdb.Generator):
    """Generator for T370, the secondary Laguerre polynomials."""

    table = TABLE
    parameters = ("n",)
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return secondary_polynomials(UP_TO)[int(params["n"])]


def stored_values():
    """Read the draft from the API and parse its stored polynomials."""
    key = os.environ.get("NUMBERDB_API_KEY")
    if not key:
        raise RuntimeError("NUMBERDB_API_KEY is not set")
    request = urllib.request.Request(
        "https://numberdb.org/api/table?id=%s" % TABLE,
        headers={"Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        tree = json.load(response)
    if "error" in tree:
        raise RuntimeError(tree["error"])

    found = {}
    for n_text, entry in tree.get("Numbers", {}).items():
        if isinstance(entry, dict):
            entry = entry.get("number")
        found[int(n_text)] = R(entry)
    expected = set(range(UP_TO + 1))
    if set(found) != expected:
        missing = sorted(expected - set(found))[:5]
        extra = sorted(set(found) - expected)[:5]
        raise ArithmeticError(
            "stored key set disagrees, missing=%s extra=%s" % (missing, extra))
    return [found[n] for n in range(UP_TO + 1)]


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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = LaguerreSecondaryPolynomials()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact secondary Laguerre polynomials"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        run_integrity_checks(stored_values())
        print("stored identity checks passed")
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
