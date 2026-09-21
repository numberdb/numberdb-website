"""Moments of the characteristic polynomials of unitary, orthogonal and symplectic matrices -- numberdb.org/T379

This generator fills T379 with the exact CFKRS random-matrix factors
g_G(k) for the unitary, orthogonal and symplectic symmetry types.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

In this checkout, use the repository wrapper:

    $ agents/sage.sh generators/random-matrix-characteristic-polynomial-moments/generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generators/random-matrix-characteristic-polynomial-moments/generate.py
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T379")
K_UP_TO = 12
GROUPS = ("U", "O", "USp")


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _product(terms):
    out = QQ(1)
    for term in terms:
        out *= term
    return out


def _factorial_ratio(numerator, denominator):
    return QQ(factorial(numerator)) / QQ(factorial(denominator))


def _exponent(group, k):
    if group == "U":
        return k * k
    if group == "O":
        return k * (k - 1) // 2
    if group == "USp":
        return k * (k + 1) // 2
    raise ValueError("unknown group %r" % (group,))


def _unitary(k):
    return QQ(factorial(k * k)) * _product(
        _factorial_ratio(j, k + j) for j in range(k))


def _symplectic(k):
    exponent = _exponent("USp", k)
    return QQ(factorial(exponent)) * _product(
        _factorial_ratio(j, 2 * j) for j in range(1, k + 1))


def _orthogonal(k):
    exponent = _exponent("O", k)
    return QQ(2) ** (k - 1) * QQ(factorial(exponent)) * _product(
        _factorial_ratio(j, 2 * j) for j in range(1, k))


def _value(group, k):
    if group == "U":
        return _unitary(k)
    if group == "O":
        return _orthogonal(k)
    if group == "USp":
        return _symplectic(k)
    raise ValueError("unknown group %r" % (group,))


def _cfkrs_leading_from_matrix_formula(group, k):
    """Leading CFKRS factor after converting N to conductor units."""
    if group == "U":
        raw = _product(_factorial_ratio(j, k + j) for j in range(k))
        return raw
    if group == "USp":
        exponent = _exponent(group, k)
        raw = QQ(2) ** exponent * _product(
            _factorial_ratio(j, 2 * j) for j in range(1, k + 1))
        return raw / (QQ(2) ** exponent)
    if group == "O":
        exponent = _exponent(group, k)
        raw_so = QQ(2) ** (k * (k + 1) // 2) * _product(
            _factorial_ratio(j, 2 * j) for j in range(1, k))
        # The full orthogonal model gives half the SO(2N) central moment:
        # the O^-(2N) central characteristic polynomial vanishes.
        return (raw_so / QQ(2)) / (QQ(2) ** exponent)
    raise ValueError("unknown group %r" % (group,))


def run_private_checks():
    expected_unitary = {
        1: ZZ(1),
        2: ZZ(2),
        3: ZZ(42),
        4: ZZ(24024),
        5: ZZ(701149020),
    }
    for k, expected in expected_unitary.items():
        if _unitary(k) != expected:
            raise ArithmeticError("unitary printed-value check failed at k=%d" % k)

    for group in GROUPS:
        for k in range(1, K_UP_TO + 1):
            exponent = _exponent(group, k)
            from_leading_term = (
                QQ(factorial(exponent))
                * _cfkrs_leading_from_matrix_formula(group, k)
            )
            if _value(group, k) != from_leading_term:
                raise ArithmeticError(
                    "%s k=%d leading-term check failed: %s != %s" %
                    (group, k, _value(group, k), from_leading_term))

    if _orthogonal(1) != 1:
        raise ArithmeticError("empty-product check failed for O, k=1")
    if _symplectic(1) != QQ(1) / QQ(2):
        raise ArithmeticError("USp first-row check failed")


class RandomMatrixCharacteristicPolynomialMoments(numberdb.Generator):

    table = TABLE
    parameters = ("group", "k")
    type = "Q"
    rigour = "exact"

    def enumerate(self):
        for group in GROUPS:
            for k in range(1, K_UP_TO + 1):
                yield {"group": group, "k": str(k)}

    def value(self, params, digits):
        return _value(params["group"], int(params["k"]))


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe."""
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
        produced_by=_producer(
            generator,
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex-cli"),
        ),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    files = _source_files(generator)
    stored = []
    for name, body in sorted(files.items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


if __name__ == "__main__":
    _key_from_stdin()
    run_private_checks()
    generator = RandomMatrixCharacteristicPolynomialMoments()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill random-matrix characteristic polynomial moment factors"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
