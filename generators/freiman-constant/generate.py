"""Freiman's constant -- numberdb.org/T431

Freiman's constant is the endpoint of the last gap in the Lagrange spectrum,

    c_F = (2221564096 + 283748*sqrt(462)) / 491993569.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE") or "T431"
DIGITS = 100
WORKING_GUARD = 64

A = ZZ(2221564096)
B = ZZ(283748)
D = ZZ(462)
Q = ZZ(491993569)

MINPOLY = (ZZ(491993569), ZZ(-4443128192), ZZ(10031248672))
OEIS_PREFIX = (
    "4.52782956616087914088269598807046964692983363276972837406506179200"
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def freiman_ball(digits):
    R = field(digits)
    value = (R(A) + R(B) * R(D).sqrt()) / R(Q)
    if not value.is_finite():
        raise ArithmeticError("non-finite ball for Freiman's constant")
    return value


def _contains_decimal_record(ball, value_text):
    R = ball.parent()
    places = len(value_text.split(".", 1)[1])
    recorded = R(value_text).add_error(R(10) ** (-places))
    return (ball - recorded).contains_zero()


def _polynomial_value(x):
    c2, c1, c0 = MINPOLY
    R = x.parent()
    return R(c2) * x * x + R(c1) * x + R(c0)


def run_integrity_checks():
    value = freiman_ball(DIGITS)

    if not _contains_decimal_record(value, OEIS_PREFIX):
        raise ArithmeticError("computed ball does not contain OEIS A118472 prefix")

    residual = _polynomial_value(value)
    if not residual.contains_zero():
        raise ArithmeticError("computed ball does not satisfy the minimal polynomial")
    if value.parent()(residual.rad()) > value.parent()(10) ** (-90):
        raise ArithmeticError("minimal-polynomial residual is too wide")

    higher = freiman_ball(130)
    if not (value - higher).contains_zero():
        raise ArithmeticError("100-digit and 130-digit computations disagree")


class FreimanConstant(numberdb.Generator):
    table = TABLE
    parameters = ()
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        yield {}

    def value(self, params, digits):
        return freiman_ball(digits)


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
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = FreimanConstant()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="computed Freiman's constant in real ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
