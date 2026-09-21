"""Sharp constants in the Hardy-Littlewood-Sobolev inequality -- numberdb.org/T355.

This generator fills T355 with the sharp constants C_{n,lambda} for the
diagonal Hardy-Littlewood-Sobolev inequality, for n = 1..20 and rational
lambda of denominator at most 4 in the range 0 < lambda < n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T355")
DIGITS = 100
WORKING_GUARD = 160
CHECK_GUARD = 256
MAX_N = 20
MAX_DENOMINATOR = 4
SOBOLEV_TABLE = "T92"


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _real_field(digits, guard=WORKING_GUARD):
    return RealBallField(numberdb.bits(digits, losing=guard))


def _admissible_lambdas(n):
    values = set()
    for denominator in range(1, MAX_DENOMINATOR + 1):
        for numerator in range(1, n * denominator):
            lam = QQ(numerator) / QQ(denominator)
            if lam.denominator() <= MAX_DENOMINATOR:
                values.add(lam)
    return sorted(values)


def _constant(n, lam, digits, guard=WORKING_GUARD):
    field = _real_field(digits, guard)
    n = ZZ(n)
    lam = QQ(lam)
    n_ball = field(n)
    lam_ball = field(lam)
    gamma_ratio = (
        field((QQ(n) - lam) / QQ(2)).gamma()
        / field(QQ(n) - lam / QQ(2)).gamma()
    )
    volume_ratio = field(QQ(n)).gamma() / field(QQ(n) / QQ(2)).gamma()
    return (
        field.pi() ** (lam_ball / 2)
        * gamma_ratio
        * volume_ratio ** (1 - lam_ball / n_ball)
    )


def _green_kernel_constant(n, s, digits, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    n = QQ(n)
    s = QQ(s)
    return (
        field(2) ** (-2 * field(s))
        * field.pi() ** (-field(n) / 2)
        * field((n - 2 * s) / 2).gamma()
        / field(s).gamma()
    )


def _sobolev_p2_values():
    table = numberdb.table(SOBOLEV_TABLE)
    values = {}
    for n_text, by_p in (table.get("Numbers") or {}).items():
        if "2" not in by_p:
            continue
        by_q = by_p["2"]
        if len(by_q) != 1:
            raise ArithmeticError("unexpected T92 p=2 row for n=%s" % n_text)
        values[ZZ(n_text)] = next(iter(by_q.values()))
    return values


def _stored_decimal_ball(text, digits, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    value = field(text)
    found = re.fullmatch(r"-?\d+\.(\d+)(?:[eE](-?\d+))?", str(text))
    if not found:
        return value
    places = len(found.group(1)) - int(found.group(2) or 0)
    return value.add_error(field(10) ** (-places))


def _contains_zero(value):
    return value.contains_zero()


class HardyLittlewoodSobolevConstants(numberdb.Generator):
    """Generator for T355, the sharp diagonal HLS constants."""

    table = TABLE
    parameters = ("n", "lambda")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_n=MAX_N):
        for n in range(1, max_n + 1):
            for lam in _admissible_lambdas(n):
                yield {"n": str(n), "lambda": str(lam)}

    def value(self, params, digits):
        return _constant(ZZ(params["n"]), QQ(params["lambda"]), digits)


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    generator = HardyLittlewoodSobolevConstants()
    values = {}
    widest_radius = field(0)
    widest_at = None

    for params in generator.enumerate():
        n = ZZ(params["n"])
        lam = QQ(params["lambda"])
        value = _constant(n, lam, DIGITS, CHECK_GUARD)
        values[(n, lam)] = value
        radius = field(value.rad())
        if radius > widest_radius:
            widest_radius = radius
            widest_at = (n, lam)

    sobolev = _sobolev_p2_values()
    checked = []
    for n in sorted(k for k in sobolev if 3 <= k <= MAX_N):
        lam = QQ(n - 2)
        hls = values[(n, lam)]
        s = QQ(1)
        green = _green_kernel_constant(n, s, DIGITS)
        sobolev_constant = _stored_decimal_ball(sobolev[n], DIGITS)
        dual = 1 / (green * sobolev_constant * sobolev_constant)
        if not _contains_zero(hls - dual):
            raise ArithmeticError(
                "Sobolev duality check failed at n=%s: %s vs %s"
                % (n, hls, dual)
            )
        checked.append(n)

    print("integrity checks passed for %d entries" % len(values))
    print("widest value ball radius: %s at n=%s, lambda=%s" % (
        widest_radius, widest_at[0], widest_at[1]))
    print("Sobolev duality checked against %s for n=%s" % (
        SOBOLEV_TABLE, ",".join(str(n) for n in checked)))


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
    generator = HardyLittlewoodSobolevConstants()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="HLS sharp constants for n<=20 and denominator <=4"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
