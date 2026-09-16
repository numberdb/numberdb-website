"""$q,t$-Catalan numbers -- numberdb.org/T262.

The table stores C_n(q,t), the Carlitz-Riordan q-Catalan numbers C_n(q,1),
and the MacMahon q-Catalan numbers q^(binomial(n,2)) C_n(q,q^-1).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.combinat.q_analogues import qt_catalan_number
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T262")

# Measured before filling the draft: the chosen 22 entries have longest value
# 1156 characters at n=11, specialisation=macmahon, and the entries block is
# 8.9 KB. The two-variable row for n=7 is 1781 characters, past the point
# where a polynomial is pleasant to read, so the q,t rows stop at n=6.
MAX_QT = 6
MAX_ONE_VARIABLE = 11

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


def _macmahon(n):
    exponent = n * (n - 1) // 2
    return POLY((Q ** exponent) * _qt(n)(q=Q, t=1 / Q))


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


def _dinv(area_sequence):
    total = 0
    for i, left in enumerate(area_sequence):
        for right in area_sequence[i + 1:]:
            if left - right in (0, 1):
                total += 1
    return total


def _dyck_dinv_area(n):
    total = POLY.zero()
    for sequence in _area_sequences(n):
        total += (Q ** _dinv(sequence)) * (T ** sum(sequence))
    return total


def _dyck_area(n):
    total = POLY.zero()
    for sequence in _area_sequences(n):
        total += Q ** sum(sequence)
    return total


@lru_cache(maxsize=None)
def _q_binomial(n, k):
    if k < 0 or k > n:
        return POLY.zero()
    if k == 0 or k == n:
        return POLY.one()
    return _q_binomial(n - 1, k) + (Q ** (n - k)) * _q_binomial(n - 1, k - 1)


def _q_integer(n):
    return sum(Q ** i for i in range(n))


def _macmahon_q_binomial(n):
    quotient, remainder = _q_binomial(2 * n, n).quo_rem(_q_integer(n + 1))
    if remainder != 0:
        raise ArithmeticError("MacMahon quotient was not exact for n=%d" % n)
    return quotient


def _catalan(n):
    return ZZ(binomial(2 * n, n) // (n + 1))


class QTCatalanNumbers(numberdb.Generator):

    table = TABLE
    parameters = ("n", "specialisation")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, max_qt=MAX_QT, max_one_variable=MAX_ONE_VARIABLE):
        for n in range(3, max_one_variable + 1):
            if n <= max_qt:
                yield {"n": str(n), "specialisation": "qt"}
            yield {"n": str(n), "specialisation": "carlitz"}
            yield {"n": str(n), "specialisation": "macmahon"}

    def value(self, params, digits):
        n = int(params["n"])
        specialisation = params["specialisation"]
        if specialisation == "qt":
            return _qt(n)
        if specialisation == "carlitz":
            return _carlitz(n)
        if specialisation == "macmahon":
            return _macmahon(n)
        raise ValueError("unknown specialisation %r" % (specialisation,))


def run_integrity_checks():
    for n in range(0, MAX_QT + 1):
        qt = _qt(n)
        if qt != _dyck_dinv_area(n):
            raise ArithmeticError("dinv/area Dyck path check failed at n=%d" % n)
        if qt(q=T, t=Q) != qt:
            raise ArithmeticError("q,t symmetry failed at n=%d" % n)

    for n in range(0, MAX_ONE_VARIABLE + 1):
        carlitz = _carlitz(n)
        macmahon = _macmahon(n)
        if carlitz != _dyck_area(n):
            raise ArithmeticError("Carlitz area check failed at n=%d" % n)
        if macmahon != _macmahon_q_binomial(n):
            raise ArithmeticError("MacMahon q-binomial check failed at n=%d" % n)
        if carlitz(q=1, t=1) != _catalan(n):
            raise ArithmeticError("Carlitz Catalan specialization failed at n=%d" % n)
        if macmahon(q=1, t=1) != _catalan(n):
            raise ArithmeticError("MacMahon Catalan specialization failed at n=%d" % n)
        if n <= MAX_QT and _qt(n)(q=1, t=1) != _catalan(n):
            raise ArithmeticError("q,t Catalan specialization failed at n=%d" % n)

    if _qt(0) != 1 or _qt(1) != 1 or _qt(2) != Q + T:
        raise ArithmeticError("small q,t Catalan cases failed")
    if _carlitz(2) != Q + 1 or _macmahon(2) != Q ** 2 + 1:
        raise ArithmeticError("small q-Catalan cases failed")


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
    generator = QTCatalanNumbers()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="exact q,t-Catalan and q-Catalan specialisations"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
