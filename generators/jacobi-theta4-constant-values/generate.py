"""Values of the Jacobi theta constant theta_4(0,q) -- numberdb.org/T426.

This generator fills T426 with theta_4(0,q), for the real nome q = j/1000
with 1 <= j <= 900.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Before publishing, the script compares every value with the defining q-series
using an explicit geometric tail bound, and checks the Jacobi identity
theta_3(0,q)^4 = theta_2(0,q)^4 + theta_4(0,q)^4 across the stored range.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T426")
DIGITS = 100
WORKING_GUARD = 80
CHECK_GUARD = 256
DENOMINATOR = 1000
MAX_NUMERATOR = 900
SERIES_TERMS = 100


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _complex_field(digits, guard=WORKING_GUARD):
    return ComplexBallField(numberdb.bits(digits, losing=guard))


def _real_field(digits, guard=WORKING_GUARD):
    return RealBallField(numberdb.bits(digits, losing=guard))


def _arguments():
    for j in range(1, MAX_NUMERATOR + 1):
        yield QQ(j) / QQ(DENOMINATOR)


def _tau_from_q(q, field):
    return field(0, -1) * field(q).log() / field.pi()


def theta4_arb(q, digits, guard=WORKING_GUARD):
    field = _complex_field(digits, guard)
    value = field(0).jacobi_theta(_tau_from_q(QQ(q), field))[3]
    if not (value.real().is_finite() and value.imag().is_finite()):
        raise ArithmeticError("theta4(0,%s) produced a non-finite ball: %s" % (q, value))
    if not value.imag().contains_zero():
        raise ArithmeticError("theta4(0,%s) has nonzero imaginary part: %s" % (q, value.imag()))
    real = value.real()
    if not real.is_finite():
        raise ArithmeticError("theta4(0,%s) produced a non-finite real ball: %s" % (q, real))
    return real


def _series_tail_square(q, start, field):
    q = field(q)
    return 2 * q ** (start * start) / (1 - q ** (2 * start + 1))


def theta3_series(q, digits, terms=SERIES_TERMS, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    q = field(q)
    value = field(1)
    for n in range(1, terms):
        value += 2 * q ** (n * n)
    return value.add_error(_series_tail_square(q, terms, field))


def theta4_series(q, digits, terms=SERIES_TERMS, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    q = field(q)
    value = field(1)
    sign = -1
    for n in range(1, terms):
        value += 2 * sign * q ** (n * n)
        sign *= -1
    return value.add_error(_series_tail_square(q, terms, field))


def theta2_series(q, digits, terms=SERIES_TERMS, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    q = field(q)
    value = field(0)
    for n in range(terms):
        value += q ** (n * (n + 1))
    leading = q.sqrt().sqrt()
    tail = 2 * leading * q ** (terms * (terms + 1)) / (1 - q ** (2 * terms + 2))
    return (2 * leading * value).add_error(tail)


class JacobiTheta4ConstantValues(numberdb.Generator):
    """Generator for T426, values of theta_4(0,q)."""

    table = TABLE
    parameters = ("q",)
    type = "R"
    digits = DIGITS
    rigour = "proven"
    files = ("generate.py", "table.yaml")

    def enumerate(self):
        for q in _arguments():
            yield {"q": str(q)}

    def value(self, params, digits):
        return theta4_arb(QQ(params["q"]), digits)


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    worst_value_radius = field(0)
    worst_value_at = None
    worst_series_radius = field(0)
    worst_series_at = None
    worst_identity_radius = field(0)
    worst_identity_at = None

    for q in _arguments():
        value = theta4_arb(q, DIGITS, guard=CHECK_GUARD)
        series = theta4_series(q, DIGITS)
        difference = value - series
        if not difference.contains_zero():
            raise ArithmeticError(
                "theta4 q-series check failed at q=%s: %s vs %s" % (q, value, series)
            )

        theta2 = theta2_series(q, DIGITS)
        theta3 = theta3_series(q, DIGITS)
        theta4 = series
        identity = theta3 ** 4 - theta2 ** 4 - theta4 ** 4
        if not identity.contains_zero():
            raise ArithmeticError("Jacobi identity failed at q=%s: %s" % (q, identity))

        value_radius = field(value.rad())
        if value_radius > worst_value_radius:
            worst_value_radius = value_radius
            worst_value_at = q

        series_radius = field(series.rad())
        if series_radius > worst_series_radius:
            worst_series_radius = series_radius
            worst_series_at = q

        identity_radius = field(identity.rad())
        if identity_radius > worst_identity_radius:
            worst_identity_radius = identity_radius
            worst_identity_at = q

    print("integrity checks passed for %d entries" % MAX_NUMERATOR)
    print("widest theta4 value ball radius: %s at q=%s" % (worst_value_radius, worst_value_at))
    print("widest q-series check radius: %s at q=%s" % (worst_series_radius, worst_series_at))
    print("widest identity check radius: %s at q=%s" % (worst_identity_radius, worst_identity_at))


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
    generator = JacobiTheta4ConstantValues()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Jacobi theta4 constants on the q=j/1000 grid",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
