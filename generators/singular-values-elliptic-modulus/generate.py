"""Singular values k_r of the elliptic modulus -- numberdb.org/T295.

This generator fills T295 with the singular values at tau = i*sqrt(r),
1 <= r <= 100, storing both the modulus k_r and the parameter m_r = k_r^2.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T295")
DIGITS = 100
WORKING_GUARD = 256
CHECK_GUARD = 384
MAX_R = 100
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


def _tau(r, digits, guard=WORKING_GUARD):
    field = _complex_field(digits, guard)
    return field.gen(0) * field(r).sqrt()


def _lambda_parameter(r, digits, guard=WORKING_GUARD):
    value = _tau(r, digits, guard).modular_lambda()
    if not value.imag().contains_zero():
        raise ArithmeticError("lambda(i*sqrt(%s)) has nonzero imaginary part: %s" % (r, value))
    real = value.real()
    if not (real > 0 and real < 1):
        raise ArithmeticError("lambda(i*sqrt(%s)) is not contained in (0, 1): %s" % (r, real))
    return real


def _singular_value(r, digits, guard=WORKING_GUARD):
    return _lambda_parameter(r, digits, guard).sqrt()


def _theta_parameter(r, digits, terms=THETA_TERMS, guard=CHECK_GUARD):
    """m_r from the theta q-series with an explicit geometric tail bound."""
    field = _real_field(digits, guard)
    r = ZZ(r)
    q = (-field.pi() * field(r).sqrt()).exp()

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


def _elliptic_integral_ratio(r, digits, guard=CHECK_GUARD):
    field = _complex_field(digits, guard)
    m = _lambda_parameter(r, digits, guard)
    ratio = field(1 - m).elliptic_k() / field(m).elliptic_k()
    if not ratio.imag().contains_zero():
        raise ArithmeticError("K'(k_%s)/K(k_%s) has nonzero imaginary part: %s" % (r, r, ratio))
    return ratio.real()


def _j_from_parameter(m):
    return 256 * (1 - m + m * m) ** 3 / (m * m * (1 - m) ** 2)


def _j_direct(r, digits, guard=CHECK_GUARD):
    value = _tau(r, digits, guard).modular_j()
    if not value.imag().contains_zero():
        raise ArithmeticError("j(i*sqrt(%s)) has nonzero imaginary part: %s" % (r, value))
    return value.real()


class SingularValuesEllipticModulus(numberdb.Generator):
    """Generator for T295, the singular values k_r and m_r = k_r^2."""

    table = TABLE
    parameters = ("r", "normalisation")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_r=MAX_R):
        for r in range(1, max_r + 1):
            yield {"r": str(r), "normalisation": "modulus"}
            yield {"r": str(r), "normalisation": "parameter"}

    def value(self, params, digits):
        r = ZZ(params["r"])
        normalisation = params["normalisation"]
        if normalisation == "modulus":
            return _singular_value(r, digits)
        if normalisation == "parameter":
            if r == 1:
                return QQ(1) / QQ(2)
            return _lambda_parameter(r, digits)
        raise ValueError("unknown normalisation %r" % (normalisation,))


def _overlaps_zero(value):
    return value.contains_zero()


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    worst_check_radius = field(0)
    worst_check_at = None

    for r in range(1, MAX_R + 1):
        m = _lambda_parameter(r, DIGITS, CHECK_GUARD)
        k = m.sqrt()
        theta_m = _theta_parameter(r, DIGITS)
        if not _overlaps_zero(theta_m - m):
            raise ArithmeticError("theta-series check failed at r=%d: %s vs %s" % (r, theta_m, m))

        ratio = _elliptic_integral_ratio(r, DIGITS)
        if not _overlaps_zero(ratio - field(r).sqrt()):
            raise ArithmeticError("elliptic-integral quotient failed at r=%d: %s" % (r, ratio))

        if not _overlaps_zero(k * k - m):
            raise ArithmeticError("square relation failed at r=%d" % r)

        reciprocal = _lambda_parameter(QQ(1) / QQ(r), DIGITS, CHECK_GUARD)
        if not _overlaps_zero(reciprocal - (1 - m)):
            raise ArithmeticError("complement relation failed at r=%d" % r)

        j_formula = _j_from_parameter(m)
        j_value = _j_direct(r, DIGITS)
        if not _overlaps_zero(j_formula - j_value):
            raise ArithmeticError("j-lambda relation failed at r=%d" % r)

        for normalisation, value in (("modulus", k), ("parameter", m)):
            radius = field(value.rad())
            if radius > worst_check_radius:
                worst_check_radius = radius
                worst_check_at = (r, normalisation)

    print("integrity checks passed for r=1..%d" % MAX_R)
    print("widest check ball radius: %s at r=%s, %s" % (
        worst_check_radius, worst_check_at[0], worst_check_at[1]))


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
    generator = SingularValuesEllipticModulus()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="singular values of the elliptic modulus for r=1..100"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
