"""Babenko-Beckner constants of the Hausdorff-Young inequality -- numberdb.org/T356

This generator fills T356 with the sharp Hausdorff-Young constants

    A_p^(n) = (p^(1/p) / q^(1/q))^(n/2),  q = p/(p - 1),

for the rational exponent grid stated in the table. The endpoint rows
`p = 1` and `p = 2` are returned as the exact integer 1.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T356")
DIGITS = 100
WORKING_GUARD = 96
MAX_DIMENSION = 20
EXPONENTS = (
    QQ(1),
    QQ(5) / QQ(4),
    QQ(4) / QQ(3),
    QQ(3) / QQ(2),
    QQ(5) / QQ(3),
    QQ(7) / QQ(4),
    QQ(2),
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
    return RealBallField(numberdb.bits(digits, losing=guard))


def conjugate_exponent(p):
    if QQ(p) == 1:
        return None
    return QQ(p) / (QQ(p) - QQ(1))


def babenko_beckner_constant(n, p, digits):
    n = ZZ(n)
    p = QQ(p)
    if p == 1 or p == 2:
        return ZZ(1)
    q = conjugate_exponent(p)
    field = _field(digits)
    return (field(p) ** (QQ(1) / p) / (field(q) ** (QQ(1) / q))) ** (QQ(n) / QQ(2))


class BabenkoBecknerHausdorffYoungConstants(numberdb.Generator):

    table = TABLE
    parameters = ("n", "p")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for n in range(1, MAX_DIMENSION + 1):
            for p in EXPONENTS:
                yield {"n": n, "p": str(p)}

    def value(self, params, digits):
        return babenko_beckner_constant(ZZ(params["n"]), QQ(params["p"]), digits)


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty-upsert writability probe."""
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
    generator = BabenkoBecknerHausdorffYoungConstants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill Babenko-Beckner constants in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
