"""Values of the elliptic alpha function alpha(r) -- numberdb.org/T299.

This generator fills T299 with Ramanujan's elliptic alpha function at
tau = i*sqrt(r), q = exp(-pi*sqrt(r)), and 1 <= r <= 100.

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


TABLE = os.environ.get("NUMBERDB_TABLE", "T299")
DIGITS = 100
WORKING_GUARD = 256
CHECK_GUARD = 384
MAX_R = 100
THETA_TERMS = 80


CLOSED_FORM_COMMENTS = {
    1: "MathWorld gives $\\alpha(1)=1/2$ CITE{MathWorldAlpha}.",
    2: "MathWorld gives $\\alpha(2)=\\sqrt2-1$ CITE{MathWorldAlpha}.",
    3: "MathWorld gives $\\alpha(3)=(\\sqrt3-1)/2$ CITE{MathWorldAlpha}.",
    4: "MathWorld gives $\\alpha(4)=2(\\sqrt2-1)^2$ CITE{MathWorldAlpha}.",
    5: (
        "MathWorld gives $\\alpha(5)=(\\sqrt5-\\sqrt{2\\sqrt5-2})/2$ "
        "CITE{MathWorldAlpha}."
    ),
    6: (
        "MathWorld gives $\\alpha(6)=5\\sqrt6+6\\sqrt3-8\\sqrt2-11$ "
        "CITE{MathWorldAlpha}."
    ),
    7: "MathWorld gives $\\alpha(7)=(\\sqrt7-2)/2$ CITE{MathWorldAlpha}.",
    8: (
        "MathWorld gives $\\alpha(8)=2(10+7\\sqrt2)(1-\\sqrt{\\sqrt8-2})^2$ "
        "CITE{MathWorldAlpha}."
    ),
    9: (
        "MathWorld gives $\\alpha(9)=(3-3^{3/4}\\sqrt2(\\sqrt3-1))/2$ "
        "CITE{MathWorldAlpha}."
    ),
    10: (
        "MathWorld gives $\\alpha(10)=-103+72\\sqrt2-46\\sqrt5+33\\sqrt{10}$ "
        "CITE{MathWorldAlpha}."
    ),
}


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
    if ZZ(r) == 1:
        return QQ(1) / QQ(2)
    value = _tau(r, digits, guard).modular_lambda()
    if not value.imag().contains_zero():
        raise ArithmeticError("lambda(i*sqrt(%s)) has nonzero imaginary part: %s" % (r, value))
    real = value.real()
    if not (real > 0 and real < 1):
        raise ArithmeticError("lambda(i*sqrt(%s)) is not contained in (0, 1): %s" % (r, real))
    return real


def _singular_value(r, digits, guard=WORKING_GUARD):
    return _lambda_parameter(r, digits, guard).sqrt()


def _alpha_value(r, digits, guard=WORKING_GUARD):
    field = _complex_field(digits, guard)
    m = _lambda_parameter(r, digits, guard)
    parameter = field(m)
    elliptic_k = parameter.elliptic_k()
    elliptic_e = parameter.elliptic_e()
    sqrt_r = field(r).sqrt()
    value = field.pi() / (4 * elliptic_k * elliptic_k) + sqrt_r * (
        1 - elliptic_e / elliptic_k
    )
    if not value.imag().contains_zero():
        raise ArithmeticError("alpha(%s) has nonzero imaginary part: %s" % (r, value))
    real = value.real()
    if not (real > 0):
        raise ArithmeticError("alpha(%s) is not positive: %s" % (r, real))
    return real


def _theta_tail(q, start):
    return 2 * q ** (start * start) / (1 - q ** (2 * start + 1))


def _theta_derivative_tail(q, start):
    rho = q ** (2 * start + 1)
    weighted = (
        start * start / (1 - rho)
        + 2 * start * rho / (1 - rho) ** 2
        + rho * (1 + rho) / (1 - rho) ** 3
    )
    return 2 * q ** (start * start) * weighted


def _theta_alpha_value(r, digits, terms=THETA_TERMS, guard=CHECK_GUARD):
    """alpha(r) from the theta_3/theta_4 formula, with explicit tail bounds."""
    field = _real_field(digits, guard)
    r = ZZ(r)
    q = (-field.pi() * field(r).sqrt()).exp()

    theta3 = field(1)
    theta4 = field(1)
    q_theta4_prime = field(0)
    for n in range(1, terms):
        q_power = q ** (n * n)
        theta3 += 2 * q_power
        sign = -1 if n % 2 else 1
        theta4 += 2 * sign * q_power
        q_theta4_prime += 2 * sign * n * n * q_power

    theta_tail = _theta_tail(q, terms)
    theta3 = theta3.add_error(theta_tail)
    theta4 = theta4.add_error(theta_tail)
    q_theta4_prime = q_theta4_prime.add_error(_theta_derivative_tail(q, terms))

    return (
        1 / field.pi()
        - 4 * field(r).sqrt() * q_theta4_prime / theta4
    ) / theta3 ** 4


def _closed_form(r, digits, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    two = field(2)
    three = field(3)
    five = field(5)
    six = field(6)
    seven = field(7)
    ten = field(10)

    if r == 1:
        return field(QQ(1) / QQ(2))
    if r == 2:
        return two.sqrt() - 1
    if r == 3:
        return (three.sqrt() - 1) / 2
    if r == 4:
        return 2 * (two.sqrt() - 1) ** 2
    if r == 5:
        return (five.sqrt() - (2 * five.sqrt() - 2).sqrt()) / 2
    if r == 6:
        return 5 * six.sqrt() + 6 * three.sqrt() - 8 * two.sqrt() - 11
    if r == 7:
        return (seven.sqrt() - 2) / 2
    if r == 8:
        return 2 * (10 + 7 * two.sqrt()) * (1 - (field(8).sqrt() - 2).sqrt()) ** 2
    if r == 9:
        return (3 - three ** (QQ(3) / QQ(4)) * two.sqrt() * (three.sqrt() - 1)) / 2
    if r == 10:
        return -103 + 72 * two.sqrt() - 46 * five.sqrt() + 33 * ten.sqrt()
    raise ValueError("no closed form recorded for r=%s" % r)


class EllipticAlphaFunctionValues(numberdb.Generator):
    """Generator for T299, the values of Ramanujan's alpha(r)."""

    table = TABLE
    parameters = ("r",)
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_r=MAX_R):
        for r in range(1, max_r + 1):
            yield {"r": str(r)}

    def value(self, params, digits):
        r = ZZ(params["r"])
        if r == 1:
            entry = {"number": QQ(1) / QQ(2)}
        else:
            entry = {"number": _alpha_value(r, digits)}
        comment = CLOSED_FORM_COMMENTS.get(int(r))
        if comment:
            entry["comment"] = comment
        return entry


def _overlaps_zero(value):
    return value.contains_zero()


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    worst_value_radius = field(0)
    worst_value_at = None
    worst_check_radius = field(0)
    worst_check_at = None

    values = {}
    for r in range(1, MAX_R + 1):
        value = _alpha_value(r, DIGITS, CHECK_GUARD)
        values[r] = value

        theta_value = _theta_alpha_value(r, DIGITS)
        if not _overlaps_zero(theta_value - value):
            raise ArithmeticError("theta formula failed at r=%d: %s vs %s" % (r, theta_value, value))

        if r <= 10:
            closed = _closed_form(r, DIGITS)
            if not _overlaps_zero(closed - value):
                raise ArithmeticError("closed form failed at r=%d: %s vs %s" % (r, closed, value))

        value_radius = field(value.rad())
        if value_radius > worst_value_radius:
            worst_value_radius = value_radius
            worst_value_at = r
        radius = field(theta_value.rad())
        if radius > worst_check_radius:
            worst_check_radius = radius
            worst_check_at = (r, "theta")

    for r in range(1, MAX_R // 4 + 1):
        left = values[4 * r]
        k4 = _singular_value(4 * r, DIGITS, CHECK_GUARD)
        right = (1 + k4) ** 2 * values[r] - 2 * field(r).sqrt() * k4
        if not _overlaps_zero(left - right):
            raise ArithmeticError("order-two formula failed at r=%d: %s vs %s" % (r, left, right))

    print("integrity checks passed for r=1..%d" % MAX_R)
    print("widest value ball radius: %s at r=%s" % (worst_value_radius, worst_value_at))
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
    generator = EllipticAlphaFunctionValues()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="elliptic alpha function values for r=1..100"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
