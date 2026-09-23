"""Values of the elliptic nome q(m) -- numberdb.org/T425.

This generator fills T425 with q(m) = exp(-pi*K(1-m)/K(m)), where K takes the
elliptic parameter m = k^2. The table uses m = j/1000 for 1 <= j <= 999.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Before publishing, the script checks q(1/2) = exp(-pi) and recovers m from the
theta constants theta_2(0,q) and theta_3(0,q) by a q-series with an explicit
geometric tail bound.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T425")
DIGITS = 100
WORKING_GUARD = 80
CHECK_GUARD = 256
DENOMINATOR = 1000
THETA_TERMS = 80


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


def _nome(m, digits, guard=WORKING_GUARD):
    field = _complex_field(digits, guard)
    parameter = field(QQ(m))
    value = (-field.pi() * (field(1) - parameter).elliptic_k()
             / parameter.elliptic_k()).exp()
    if not (value.real().is_finite() and value.imag().is_finite()):
        raise ArithmeticError("q(%s) produced a non-finite ball: %s" % (m, value))
    if not value.imag().contains_zero():
        raise ArithmeticError("q(%s) has nonzero imaginary part: %s" % (m, value.imag()))
    real = value.real()
    if not (real > 0 and real < 1):
        raise ArithmeticError("q(%s) is not contained in (0, 1): %s" % (m, real))
    return real


def _theta_parameter(q, terms=THETA_TERMS):
    """Recover m from q by theta q-series, with explicit tail bounds."""
    field = q.parent()
    q = field(q)

    theta3 = field(1)
    for n in range(1, terms):
        theta3 += 2 * q ** (n * n)
    tail3 = 2 * q ** (terms * terms) / (1 - q ** (2 * terms + 1))
    theta3 = theta3.add_error(tail3)

    theta2_sum = field(0)
    for n in range(terms):
        theta2_sum += q ** (n * (n + 1))
    leading = q.sqrt().sqrt()
    tail2 = 2 * leading * q ** (terms * (terms + 1)) / (1 - q ** (2 * terms + 2))
    theta2 = (2 * leading * theta2_sum).add_error(tail2)

    return (theta2 / theta3) ** 4


class EllipticNomeValues(numberdb.Generator):
    """Generator for T425, the elliptic nome q(m)."""

    table = TABLE
    parameters = ("m",)
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, denominator=DENOMINATOR):
        for j in range(1, denominator):
            yield {"m": str(QQ(j) / QQ(denominator))}

    def value(self, params, digits):
        return _nome(params["m"], digits)


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    generator = EllipticNomeValues()
    half_seen = False
    worst_radius = field(0)
    worst_at = None

    for params in generator.enumerate():
        m = QQ(params["m"])
        q = _nome(m, DIGITS, CHECK_GUARD)

        theta_m = _theta_parameter(q)
        if not (theta_m - field(m)).contains_zero():
            raise ArithmeticError(
                "theta inversion failed at m=%s: %s vs %s" % (m, theta_m, m))

        if m == QQ(1) / QQ(2):
            half_seen = True
            expected = (-field.pi()).exp()
            if not (field(q) - expected).contains_zero():
                raise ArithmeticError("q(1/2) did not contain exp(-pi): %s" % q)

        radius = field(q.rad())
        if radius > worst_radius:
            worst_radius = radius
            worst_at = m

    if not half_seen:
        raise ArithmeticError("the m=1/2 control was not enumerated")
    print("integrity checks passed for %d entries" % (DENOMINATOR - 1))
    print("widest value ball radius: %s at m=%s" % (worst_radius, worst_at))


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
    generator = EllipticNomeValues()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="elliptic nome values on the m=j/1000 grid"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
