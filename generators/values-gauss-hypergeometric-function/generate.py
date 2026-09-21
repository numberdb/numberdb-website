"""Values of the Gauss hypergeometric function 2F1(a,b;c;z) -- numberdb.org/T348

This generator fills T348 with real principal values of the Gauss
hypergeometric function for the rational grid stated in the table. Exact
rational rows are omitted.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T348")
DIGITS = 100
WORKING_GUARD = 64

A_VALUES = (QQ(-1) / 2, QQ(1) / 2, QQ(1), QQ(3) / 2, QQ(2), QQ(3))
C_VALUES = (QQ(1) / 2, QQ(1), QQ(3) / 2, QQ(2), QQ(3))
Z_VALUES = (
    QQ(-4),
    QQ(-2),
    QQ(-3) / 2,
    QQ(-1),
    QQ(-3) / 4,
    QQ(-1) / 2,
    QQ(-1) / 4,
    QQ(1) / 4,
    QQ(1) / 2,
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field(digits, guard=WORKING_GUARD):
    return ComplexBallField(numberdb.bits(digits, losing=guard))


def _is_integer(x):
    return QQ(x).denominator() == 1


def _is_nonpositive_integer(x):
    return _is_integer(x) and QQ(x) <= 0


def _is_rational_row(a, b, c, z):
    """Rows whose value is known to be rational and is intentionally omitted."""
    if z == 0:
        return True
    if _is_nonpositive_integer(a) or _is_nonpositive_integer(b):
        return True
    for upper, other in ((a, b), (b, a)):
        if z == -1 and c == 1 + upper - other:
            if _is_nonpositive_integer(1 + upper / 2 - other):
                return True
        if z == QQ(1) / 2 and upper + other == 1:
            if _is_nonpositive_integer((upper + c) / 2):
                return True
            if _is_nonpositive_integer((c - upper + 1) / 2):
                return True
        if c - other == -1 and z != 1 and z / (z - 1) == c / upper:
            return True
    if c == a and _is_integer(b):
        return True
    if c == b and _is_integer(a):
        return True
    if _is_integer(a) and _is_integer(b) and _is_integer(c):
        if c - a <= 0 or c - b <= 0:
            return True
    return False


def _ordered_pair(a, b):
    return (a, b) if a <= b else (b, a)


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s: %s" % (label, value))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s: %s" % (label, value))
    return value.real()


def hypergeometric_2f1(a, b, c, z, digits):
    field = _field(digits)
    value = field(z).hypergeometric([field(a), field(b)], [field(c)])
    return _real(value, "2F1(%s,%s;%s;%s)" % (a, b, c, z))


class GaussHypergeometricValues(numberdb.Generator):

    table = TABLE
    parameters = ("a", "b", "c", "z")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for a in A_VALUES:
            for b in A_VALUES:
                if b < a:
                    continue
                for c in C_VALUES:
                    for z in Z_VALUES:
                        if _is_rational_row(a, b, c, z):
                            continue
                        yield {"a": str(a), "b": str(b), "c": str(c), "z": str(z)}

    def value(self, params, digits):
        a = QQ(params["a"])
        b = QQ(params["b"])
        c = QQ(params["c"])
        z = QQ(params["z"])
        return hypergeometric_2f1(a, b, c, z, digits)


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
    generator = GaussHypergeometricValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill Gauss hypergeometric values in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
