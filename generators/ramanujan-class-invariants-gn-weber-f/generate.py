"""Ramanujan's class invariants G_n, with Weber's f(sqrt(-n)) -- numberdb.org/T297.

This generator fills T297 with Ramanujan's G_n and Weber's f(i*sqrt(n)),
where tau = i*sqrt(n), q = exp(-pi*sqrt(n)), and 1 <= n <= 100.

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


TABLE = os.environ.get("NUMBERDB_TABLE", "T297")
DIGITS = 100
WORKING_GUARD = 256  # Widest value ball was below 2e-252 at n=99, weber.
CHECK_GUARD = 512  # Widest q-product check ball was below 3e-220 at n=1.
MAX_N = 100
PRODUCT_TERMS = 80


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


def _tau(n, digits, guard=WORKING_GUARD):
    field = _complex_field(digits, guard)
    return field.gen(0) * field(n).sqrt()


def _weber_f_eta(n, digits, guard=WORKING_GUARD):
    tau = _tau(n, digits, guard)
    value = tau.modular_eta() ** 2 / ((tau / 2).modular_eta() * (2 * tau).modular_eta())
    if not value.imag().contains_zero():
        raise ArithmeticError("Weber f(i*sqrt(%s)) has nonzero imaginary part: %s" % (n, value))
    real = value.real()
    if not real > 0:
        raise ArithmeticError("Weber f(i*sqrt(%s)) is not positive: %s" % (n, real))
    return real


def _ramanujan_g(n, digits, guard=WORKING_GUARD):
    field = _real_field(digits, guard)
    return field(_weber_f_eta(n, digits, guard)) / field(2) ** (QQ(1) / QQ(4))


def _weber_f_product(n, digits, terms=PRODUCT_TERMS, guard=CHECK_GUARD):
    """Weber f from the q-product, with a positive tail bound."""
    field = _real_field(digits, guard)
    n = field(n)
    q = (-field.pi() * n.sqrt()).exp()
    product = field(1)
    for m in range(1, terms + 1):
        product *= 1 + q ** (2 * m - 1)
    leading = (field.pi() * n.sqrt() / 24).exp()
    partial = leading * product

    tail_sum = q ** (2 * terms + 1) / (1 - q ** 2)
    error = partial * (tail_sum.exp() - 1)
    return partial.add_error(error)


def _lambda_parameter(n, digits, guard=CHECK_GUARD):
    value = _tau(n, digits, guard).modular_lambda()
    if not value.imag().contains_zero():
        raise ArithmeticError("lambda(i*sqrt(%s)) has nonzero imaginary part: %s" % (n, value))
    real = value.real()
    if not (real > 0 and real < 1):
        raise ArithmeticError("lambda(i*sqrt(%s)) is not contained in (0, 1): %s" % (n, real))
    return real


def _j_invariant(n, digits, guard=CHECK_GUARD):
    value = _tau(n, digits, guard).modular_j()
    if not value.imag().contains_zero():
        raise ArithmeticError("j(i*sqrt(%s)) has nonzero imaginary part: %s" % (n, value))
    return value.real()


class RamanujanClassInvariantsG(numberdb.Generator):
    """Generator for T297, Ramanujan's G_n and Weber's f(i*sqrt(n))."""

    table = TABLE
    parameters = ("n", "normalisation")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_n=MAX_N):
        for n in range(1, max_n + 1):
            yield {"n": str(n), "normalisation": "ramanujan"}
            yield {"n": str(n), "normalisation": "weber"}

    def value(self, params, digits):
        n = ZZ(params["n"])
        normalisation = params["normalisation"]
        if normalisation == "ramanujan":
            if n == 1:
                return ZZ(1)
            return _ramanujan_g(n, digits)
        if normalisation == "weber":
            return _weber_f_eta(n, digits)
        raise ValueError("unknown normalisation %r" % (normalisation,))


def _overlaps_zero(value):
    return value.contains_zero()


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    worst_value_radius = field(0)
    worst_value_at = None
    worst_check_radius = field(0)
    worst_check_at = None

    for n in range(1, MAX_N + 1):
        f = _weber_f_eta(ZZ(n), DIGITS, CHECK_GUARD)
        g = field(f) / field(2) ** (QQ(1) / QQ(4))

        product_f = _weber_f_product(ZZ(n), DIGITS)
        if not _overlaps_zero(product_f - f):
            raise ArithmeticError("q-product check failed at n=%d: %s vs %s" % (n, product_f, f))

        m = _lambda_parameter(ZZ(n), DIGITS, CHECK_GUARD)
        singular_relation = g ** (-24) - 4 * m * (1 - m)
        if not _overlaps_zero(singular_relation):
            raise ArithmeticError("singular-modulus relation failed at n=%d: %s" % (
                n, singular_relation))

        reciprocal = _ramanujan_g(QQ(1) / QQ(n), DIGITS, CHECK_GUARD)
        if not _overlaps_zero(reciprocal - g):
            raise ArithmeticError("reciprocal relation failed at n=%d: %s vs %s" % (
                n, reciprocal, g))

        j_formula = (f ** 24 - 16) ** 3 / f ** 24
        j_value = _j_invariant(ZZ(n), DIGITS, CHECK_GUARD)
        if not _overlaps_zero(j_formula - j_value):
            raise ArithmeticError("j-Weber relation failed at n=%d: %s vs %s" % (
                n, j_formula, j_value))

        for normalisation, value in (("ramanujan", g), ("weber", f)):
            radius = field(value.rad())
            if radius > worst_value_radius:
                worst_value_radius = radius
                worst_value_at = (n, normalisation)
        radius = field(product_f.rad())
        if radius > worst_check_radius:
            worst_check_radius = radius
            worst_check_at = (n, "q-product")

    print("integrity checks passed for n=1..%d" % MAX_N)
    print("widest value ball radius: %s at n=%s, %s" % (
        worst_value_radius, worst_value_at[0], worst_value_at[1]))
    print("widest check ball radius: %s at n=%s, %s" % (
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
    generator = RamanujanClassInvariantsG()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Ramanujan class invariants G_n and Weber f(i*sqrt(n)) for n=1..100"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
