"""numberdb.org/T264 -- Carlitz-Riordan $q$-Catalan numbers $C_n(q)$.

This generator fills T264, the table of the Carlitz-Riordan specialisation
$C_n(q)=C_n(q,1)$. The two-variable $q,t$-Catalan table is T262, and the
MacMahon one-variable convention is T265.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.combinat.q_analogues import qt_catalan_number
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T264")

# Measured before filling the draft: the chosen rows n=3..11 have largest value
# 438 characters at n=11, and the entries block is small enough to leave room
# for extension.
MAX_N = 11

POLY = PolynomialRing(ZZ, ("q", "t"))
Q, T = POLY.gens()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _qt(n):
    return POLY(qt_catalan_number(n))


def _carlitz(n):
    return POLY(_qt(n)(q=Q, t=1))


def _area_sequences(n):
    def extend(prefix):
        if len(prefix) == n:
            yield tuple(prefix)
            return
        top = 0 if not prefix else prefix[-1] + 1
        for next_area in range(top + 1):
            prefix.append(next_area)
            yield from extend(prefix)
            prefix.pop()

    yield from extend([])


def _dyck_area(n):
    total = POLY.zero()
    for sequence in _area_sequences(n):
        total += Q ** sum(sequence)
    return total


def _catalan(n):
    return ZZ(binomial(2 * n, n) // (n + 1))


class CarlitzRiordanQCatalanNumbers(numberdb.Generator):
    """Generator for T264, the table of $C_n(q)=C_n(q,1)$."""

    table = TABLE
    parameters = ("n",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, max_n=MAX_N):
        for n in range(3, max_n + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return _carlitz(int(params["n"]))


def run_integrity_checks():
    for n in range(0, MAX_N + 1):
        carlitz = _carlitz(n)
        if carlitz != _dyck_area(n):
            raise ArithmeticError("Carlitz area check failed at n=%d" % n)
        if carlitz(q=1, t=1) != _catalan(n):
            raise ArithmeticError("Carlitz Catalan specialization failed at n=%d" % n)

    if _carlitz(0) != 1 or _carlitz(1) != 1 or _carlitz(2) != Q + 1:
        raise ArithmeticError("small Carlitz-Riordan q-Catalan cases failed")


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
    generator = CarlitzRiordanQCatalanNumbers()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="exact Carlitz-Riordan q-Catalan polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
