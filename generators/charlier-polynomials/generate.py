"""Charlier polynomials C_n(x; a) -- numberdb.org/T267.

This generator fills the table of KLS/DLMF Charlier polynomials

    C_n(x; a) = _2F_0(-n, -x; -; -1/a).

The table uses the Poisson mean parameter a and stores C_n itself, not the
monic rescaling (-a)^n C_n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T267")

# Measured before filling the draft: these ten Poisson means and n <= 20 give
# 210 entries. The longest written value has 813 characters, and the entries
# block is 56.7 KB in the dry-run measurement.
A_VALUES = (
    QQ(1) / QQ(4),
    QQ(1) / QQ(3),
    QQ(1) / QQ(2),
    QQ(2) / QQ(3),
    QQ(1),
    QQ(3) / QQ(2),
    QQ(2),
    QQ(5) / QQ(2),
    QQ(3),
    QQ(4),
)
UP_TO = 20

R = PolynomialRing(QQ, "x")
x = R.gen()

OEIS_A046716_PREFIX = (
    1,
    1, 1,
    1, 3, 1,
    1, 6, 8, 1,
    1, 10, 29, 24, 1,
    1, 15, 75, 145, 89, 1,
    1, 21, 160, 545, 814, 415, 1,
    1, 28, 301, 1575, 4179, 5243, 2372, 1,
    1, 36, 518, 3836, 15659, 34860, 38618, 16072, 1,
    1, 45, 834, 8274, 47775, 163191, 318926, 321690, 125673, 1,
    1, 55, 1275, 16290, 125853, 606417, 1809905, 3197210, 2995011, 1112083, 1,
    1, 66, 1870, 29865, 296703, 1908060, 8002742, 21474255, 34975061,
    30840304, 10976184, 1,
    1, 78, 2651, 51700, 641058, 5289306, 29515079, 110836572, 272757166,
    415371726, 348114711, 119481296, 1,
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _falling_binomial(argument, count):
    """The polynomial binomial(argument, count), with exact divisions."""
    value = R.one()
    argument = R(argument)
    for offset in range(count):
        value *= argument - QQ(offset)
        value *= QQ(1) / QQ(offset + 1)
    return R(value)


def charlier_polynomial(n, a):
    """The KLS/DLMF Charlier polynomial C_n(x; a)."""
    n = int(n)
    a = QQ(a)
    total = R.zero()
    for k in range(n + 1):
        total += (
            QQ(factorial(n)) / QQ(factorial(k) * factorial(n - k))
            * _falling_binomial(x, k)
            * QQ(factorial(k))
            * (-QQ(1) / a) ** k
        )
    return R(total)


class CharlierPolynomials(numberdb.Generator):
    """Generator for T267, the Charlier polynomials C_n(x; a)."""

    table = TABLE
    parameters = ("a", "n")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for a in A_VALUES:
            for n in range(up_to + 1):
                yield {"a": str(a), "n": str(n)}

    def value(self, params, digits):
        return charlier_polynomial(int(params["n"]), QQ(params["a"]))


def _computed_values():
    return {
        (a, n): charlier_polynomial(n, a)
        for a in A_VALUES
        for n in range(UP_TO + 1)
    }


def _check_recurrence(values):
    for a in A_VALUES:
        if values[(a, 0)] != R.one():
            raise ArithmeticError("C_0 failed at a=%s" % (a,))
        if values[(a, 1)] != R.one() - x / a:
            raise ArithmeticError("C_1 failed at a=%s" % (a,))
        for n in range(1, UP_TO):
            expected = ((QQ(n) + a - x) * values[(a, n)]
                        - QQ(n) * values[(a, n - 1)]) / a
            if values[(a, n + 1)] != expected:
                raise ArithmeticError("recurrence failed at a=%s, n=%d"
                                      % (a, n))


def _check_generating_function(values):
    for a in A_VALUES:
        for point in range(9):
            for n in range(UP_TO + 1):
                coefficient = QQ(0)
                for j in range(n + 1):
                    coefficient += (
                        QQ(1) / QQ(factorial(n - j))
                        * QQ(_integer_binomial(point, j))
                        * (-QQ(1) / a) ** j
                    )
                expected = QQ(factorial(n)) * coefficient
                if values[(a, n)](point) != expected:
                    raise ArithmeticError(
                        "generating function failed at a=%s, x=%d, n=%d"
                        % (a, point, n))


def _integer_binomial(top, count):
    if count < 0 or count > top:
        return 0
    return factorial(top) // (factorial(count) * factorial(top - count))


def _check_special_values(values):
    for a in A_VALUES:
        for n in range(UP_TO + 1):
            if values[(a, n)](0) != 1:
                raise ArithmeticError("C_n(0; a) failed at a=%s, n=%d"
                                      % (a, n))
    for a in A_VALUES:
        expected = (x ** 2 + a ** 2 - x * (QQ(1) + 2 * a)) / (a ** 2)
        if values[(a, 2)] != expected:
            raise ArithmeticError("MathWorld C_2 failed at a=%s" % (a,))


def _check_oeis_prefix(values):
    flattened = []
    for n in range(13):
        polynomial = values[(QQ(1), n)]
        row = [abs(polynomial.monomial_coefficient(x ** degree))
               for degree in range(n, -1, -1)]
        flattened.extend(int(coefficient) for coefficient in row)
    if tuple(flattened) != OEIS_A046716_PREFIX:
        raise ArithmeticError("OEIS A046716 prefix disagrees")


def run_integrity_checks():
    values = _computed_values()
    _check_recurrence(values)
    _check_generating_function(values)
    _check_special_values(values)
    _check_oeis_prefix(values)


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
    generator = CharlierPolynomials()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact Charlier polynomials in the KLS/DLMF normalisation"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
