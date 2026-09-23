"""Values of $\\xi(u)$ in the Dickman-de Bruijn estimate -- numberdb.org/T423.

This generator fills T423, the draft table of the positive root
$\\xi(u)$ of $e^x-1=ux$ used in de Bruijn's estimate for the Dickman-de
Bruijn function.

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
from sage.rings.real_mpfi import RealIntervalField


TABLE = os.environ.get("NUMBERDB_TABLE", "T423")

MIN_CENTS = 100
MAX_CENTS = 1200
BISECTION_STEPS = 430
WORKING_GUARD = 64
SIGN_GUARDS = (WORKING_GUARD, 128, 256)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _arguments():
    for cents in range(MIN_CENTS, MAX_CENTS + 1):
        yield QQ(cents) / QQ(100)


def _field(digits, guard=WORKING_GUARD):
    return RealBallField(numberdb.bits(digits, losing=guard))


def _f(x, u):
    return x.exp() - 1 - u * x


def _sign_at(x, u, digits):
    for guard in SIGN_GUARDS:
        field = _field(digits, guard)
        value = _f(field(x), field(u))
        if not value.is_finite():
            raise ArithmeticError("non-finite sign ball at u=%s, x=%s" % (u, x))
        if value > 0:
            return 1
        if value < 0:
            return -1
    raise ArithmeticError("could not decide sign at u=%s, x=%s" % (u, x))


def xi_interval(u, digits):
    if u == 1:
        return ZZ(0)

    lo = QQ(0)
    hi = max(QQ(2), u + 1)
    while _sign_at(hi, u, digits) <= 0:
        hi *= 2

    for _ in range(BISECTION_STEPS):
        mid = (lo + hi) / 2
        if _sign_at(mid, u, digits) < 0:
            lo = mid
        else:
            hi = mid

    left = _sign_at(lo, u, digits)
    right = _sign_at(hi, u, digits)
    if not (left < 0 and right > 0):
        raise ArithmeticError("final bracket does not straddle the root at u=%s" % u)

    interval = RealIntervalField(numberdb.bits(digits, losing=WORKING_GUARD))(lo, hi)
    if not interval.is_finite() or interval.absolute_diameter() == 0:
        raise ArithmeticError("bad interval at u=%s" % u)
    return interval


class DickmanDeBruijnXiValues(numberdb.Generator):
    """Generator for T423, the table of $\\xi(u)$."""

    table = TABLE
    parameters = ("u",)
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py", "table.yaml")

    def enumerate(self):
        for u in _arguments():
            yield {"u": str(u)}

    def value(self, params, digits):
        return xi_interval(QQ(params["u"]), digits)


def _exact_real(value):
    parent = getattr(value, "parent", None)
    if parent is None or not callable(parent):
        return isinstance(value, int)
    try:
        return parent() in (ZZ, QQ)
    except Exception:  # noqa: BLE001
        return False


def run_integrity_checks(generator):
    from numberdb._write import to_text

    for u in _arguments():
        value = generator.value({"u": str(u)}, generator.digits)
        if u == 1:
            if value != 0:
                raise ArithmeticError("xi(1) should be exactly zero")
            continue
        low, high = value.lower(), value.upper()
        field = _field(generator.digits, 128)
        if not (_f(field(low), field(u)) < 0 and _f(field(high), field(u)) > 0):
            raise ArithmeticError("stored bracket does not straddle xi(%s)" % u)

    sibling = numberdb.table("T289")
    numbers = sibling["Numbers"]
    for u_int in range(2, 8):
        produced = to_text(
            generator.value({"u": str(u_int)}, generator.digits),
            generator.digits,
        )
        stored = numbers[str(u_int + 1)]["2"]["number"]
        if produced != stored:
            raise ArithmeticError(
                "xi(%d) does not match T289 lambda_{%d,2}: %s != %s"
                % (u_int, u_int + 1, produced, stored)
            )


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

        _check_rigour(
            generator,
            table,
            identity,
            value,
            bounded=True if _exact_real(value) else None,
        )
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
    generator = DickmanDeBruijnXiValues()
    run_integrity_checks(generator)
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Dickman-de Bruijn xi values by ball bisection",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
