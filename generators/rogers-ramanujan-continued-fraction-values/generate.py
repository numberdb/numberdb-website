"""Values of the Rogers-Ramanujan continued fraction R(e^(-pi*sqrt(r))) -- numberdb.org/T298.

This generator fills T298 with R(q), where q = exp(-pi*sqrt(r)) and
1 <= r <= 100.

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


TABLE = os.environ.get("NUMBERDB_TABLE", "T298")
DIGITS = 100
WORKING_GUARD = 256
CHECK_GUARD = 512
MAX_R = 100
PRODUCT_TERMS = 80
CONTINUED_FRACTION_TERMS = 220


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


def _complex_field(digits, guard=CHECK_GUARD):
    return ComplexBallField(numberdb.bits(digits, losing=guard))


def _q_for_r(r, field):
    return (-field.pi() * field(r).sqrt()).exp()


def _product_tail_log_bound(q, terms):
    first = 5 * terms + 1
    numerator = q ** first * (1 + q + q ** 2 + q ** 3)
    return numerator / ((1 - q ** 5) * (1 - q ** first))


def _rogers_product(r, digits, terms=PRODUCT_TERMS, guard=WORKING_GUARD):
    field = _real_field(digits, guard)
    q = _q_for_r(ZZ(r), field)
    value = q ** (QQ(1) / QQ(5))
    for k in range(terms):
        value *= (1 - q ** (5 * k + 1)) * (1 - q ** (5 * k + 4))
        value /= (1 - q ** (5 * k + 2)) * (1 - q ** (5 * k + 3))

    tail_log_bound = _product_tail_log_bound(q, terms)
    tail_error = abs(value) * (tail_log_bound.exp() - 1)
    return value.add_error(tail_error)


def _rogers_continued_fraction(r, digits, terms=CONTINUED_FRACTION_TERMS,
                               guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    q = _q_for_r(ZZ(r), field)
    numerators = {0: field(1), 1: field(1)}
    denominators = {-1: field(1), 0: field(1)}
    for n in range(1, terms + 1):
        if n >= 2:
            numerators[n] = numerators[n - 1] + q ** n * numerators[n - 2]
        denominators[n] = denominators[n - 1] + q ** n * denominators[n - 2]
    return q ** (QQ(1) / QQ(5)) * numerators[terms] / denominators[terms]


def _j_invariant_for_q(r, digits, guard=CHECK_GUARD):
    field = _complex_field(digits, guard)
    z = field.gen(0) * field(r).sqrt() / 2
    value = z.modular_j()
    if not value.imag().contains_zero():
        raise ArithmeticError("j(i*sqrt(%s)/2) has nonzero imaginary part: %s" % (r, value))
    return value.real()


def _j_from_rogers(u):
    numerator = (u ** 20 - 228 * u ** 15 + 494 * u ** 10 + 228 * u ** 5 + 1) ** 3
    denominator = u ** 5 * (u ** 10 + 11 * u ** 5 - 1) ** 5
    return -numerator / denominator


class RogersRamanujanContinuedFraction(numberdb.Generator):
    """Generator for T298, values of R(e^(-pi*sqrt(r)))."""

    table = TABLE
    parameters = ("r",)
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_r=MAX_R):
        for r in range(1, max_r + 1):
            yield {"r": str(r)}

    def value(self, params, digits):
        return _rogers_product(ZZ(params["r"]), digits)


def _overlaps_zero(value):
    return value.contains_zero()


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    values = {}
    worst_value_radius = field(0)
    worst_value_at = None
    worst_check_radius = field(0)
    worst_check_at = None

    for r in range(1, MAX_R + 1):
        value = _rogers_product(ZZ(r), DIGITS, guard=CHECK_GUARD)
        values[r] = value
        value_radius = field(value.rad())
        if value_radius > worst_value_radius:
            worst_value_radius = value_radius
            worst_value_at = r

        convergent = _rogers_continued_fraction(ZZ(r), DIGITS)
        difference = convergent - value
        if not _overlaps_zero(difference):
            raise ArithmeticError(
                "continued-fraction check failed at r=%d: %s vs %s"
                % (r, convergent, value))
        check_radius = field(convergent.rad())
        if check_radius > worst_check_radius:
            worst_check_radius = check_radius
            worst_check_at = (r, "continued fraction")

        j_formula = _j_from_rogers(value)
        j_value = _j_invariant_for_q(ZZ(r), DIGITS)
        difference = j_formula - j_value
        if not _overlaps_zero(difference):
            raise ArithmeticError(
                "j-invariant check failed at r=%d: %s vs %s"
                % (r, j_formula, j_value))
        check_radius = field(j_formula.rad())
        if check_radius > worst_check_radius:
            worst_check_radius = check_radius
            worst_check_at = (r, "j formula")

    for r in range(1, MAX_R // 4 + 1):
        u = values[r]
        v = values[4 * r]
        difference = u * v ** 2 - (v - u ** 2) / (v + u ** 2)
        if not _overlaps_zero(difference):
            raise ArithmeticError("order-two modular equation failed at r=%d: %s" % (
                r, difference))
        check_radius = field(difference.rad())
        if check_radius > worst_check_radius:
            worst_check_radius = check_radius
            worst_check_at = (r, "order-two modular equation")

    print("integrity checks passed for r=1..%d" % MAX_R)
    print("widest value ball radius: %s at r=%s" % (
        worst_value_radius, worst_value_at))
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
    generator = RogersRamanujanContinuedFraction()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Rogers-Ramanujan continued fraction values for r=1..100"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
