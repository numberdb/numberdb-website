"""Complete elliptic integral of the first kind K(k_r) at the singular values -- numberdb.org/T296.

This generator fills T296 with K(k_r), where tau = i*sqrt(r),
q = exp(-pi*sqrt(r)), and k_r^2 = lambda(tau), for 1 <= r <= 100.

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


TABLE = os.environ.get("NUMBERDB_TABLE", "T296")
DIGITS = 100
WORKING_GUARD = 256
CHECK_GUARD = 384
MAX_R = 100
THETA_TERMS = 80
HYPERGEOMETRIC_TERMS = 500

K_TABLE = "Complete_elliptic_integral_of_the_first_kind_K"


CLOSED_FORM_COMMENTS = {
    1: (
        "MathWorld gives $K(k_1)=\\Gamma(1/4)^2/(4\\sqrt\\pi)$ "
        "CITE{MathWorldSingularValue}."
    ),
    2: (
        "MathWorld gives $K(k_2)=\\sqrt{1+\\sqrt2}\\,\\Gamma(1/8)"
        "\\Gamma(3/8)/(2^{13/4}\\sqrt\\pi)$ CITE{MathWorldSingularValue}."
    ),
    3: (
        "MathWorld gives $K(k_3)=3^{1/4}\\Gamma(1/3)^3/(2^{7/3}\\pi)$ "
        "CITE{MathWorldSingularValue}."
    ),
    4: (
        "MathWorld gives $K(k_4)=(1+\\sqrt2)\\Gamma(1/4)^2/"
        "(2^{7/2}\\sqrt\\pi)$ CITE{MathWorldSingularValue}."
    ),
    5: (
        "MathWorld gives $K(k_5)=(2+\\sqrt5)^{1/4}"
        "\\sqrt{\\Gamma(1/20)\\Gamma(3/20)\\Gamma(7/20)\\Gamma(9/20)/(160\\pi)}$ "
        "CITE{MathWorldSingularValue}."
    ),
    6: (
        "MathWorld gives $K(k_6)=\\sqrt{(\\sqrt2-1)(\\sqrt3+\\sqrt2)(2+\\sqrt3)}"
        "\\sqrt{\\Gamma(1/24)\\Gamma(5/24)\\Gamma(7/24)\\Gamma(11/24)/(384\\pi)}$ "
        "CITE{MathWorldSingularValue}."
    ),
    7: (
        "MathWorld gives $K(k_7)=\\Gamma(1/7)\\Gamma(2/7)\\Gamma(4/7)/"
        "(4\\cdot7^{1/4}\\pi)$ CITE{MathWorldSingularValue}."
    ),
    8: (
        "MathWorld gives $K(k_8)=\\sqrt{(2\\sqrt2+\\sqrt{1+5\\sqrt2})/(4\\sqrt2)}"
        "(1+\\sqrt2)^{1/4}\\Gamma(1/8)\\Gamma(3/8)/(8\\sqrt\\pi)$ "
        "CITE{MathWorldSingularValue}."
    ),
    9: (
        "MathWorld gives $K(k_9)=3^{1/4}\\sqrt{2+\\sqrt3}\\,\\Gamma(1/4)^2/"
        "(12\\sqrt\\pi)$ CITE{MathWorldSingularValue}."
    ),
    10: (
        "MathWorld gives $K(k_{10})=\\sqrt{2+3\\sqrt2+\\sqrt5}$ "
        "\\sqrt{\\Gamma(1/40)\\Gamma(7/40)\\Gamma(9/40)\\Gamma(11/40)"
        "\\Gamma(13/40)\\Gamma(19/40)\\Gamma(23/40)\\Gamma(37/40)/(2560\\pi^3)}$ "
        "CITE{MathWorldSingularValue}."
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


def _elliptic_k_at_parameter(m, digits, guard=WORKING_GUARD):
    field = _complex_field(digits, guard)
    value = field(m).elliptic_k()
    if not value.imag().contains_zero():
        raise ArithmeticError("K(%s) has nonzero imaginary part: %s" % (m, value))
    return value.real()


def _singular_k_value(r, digits, guard=WORKING_GUARD):
    return _elliptic_k_at_parameter(_lambda_parameter(r, digits, guard), digits, guard)


def _theta_check_value(r, digits, terms=THETA_TERMS, guard=CHECK_GUARD):
    """K(k_r) from theta_3, with a geometric tail bound."""
    field = _real_field(digits, guard)
    r = ZZ(r)
    q = (-field.pi() * field(r).sqrt()).exp()

    theta3 = field(1)
    for n in range(1, terms):
        theta3 += 2 * q ** (n * n)
    tail = 2 * q ** (terms * terms) / (1 - q ** (2 * terms + 1))
    theta3 = theta3.add_error(tail)

    return field.pi() * theta3 * theta3 / 2


def _hypergeometric_check_value(r, digits, terms=HYPERGEOMETRIC_TERMS, guard=CHECK_GUARD):
    """K(k_r) from pi/2 * 2F1(1/2, 1/2; 1; m_r), with a tail bound."""
    field = _real_field(digits, guard)
    m = field(_lambda_parameter(r, digits, guard))
    total = field(1)
    term = field(1)
    for n in range(terms - 1):
        ratio = field(2 * n + 1) / field(2 * n + 2)
        term *= ratio * ratio * m
        total += term
    tail = m ** terms / (1 - m)
    total = total.add_error(tail)
    return field.pi() * total / 2


def _gamma(field, numerator, denominator):
    return field(QQ(numerator) / QQ(denominator)).gamma()


def _closed_form(r, digits, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    pi = field.pi()
    two = field(2)
    three = field(3)
    five = field(5)
    seven = field(7)

    if r == 1:
        return _gamma(field, 1, 4) ** 2 / (4 * pi.sqrt())
    if r == 2:
        return (two.sqrt() + 1).sqrt() * _gamma(field, 1, 8) * _gamma(field, 3, 8) / (
            two ** (QQ(13) / QQ(4)) * pi.sqrt())
    if r == 3:
        return three ** (QQ(1) / QQ(4)) * _gamma(field, 1, 3) ** 3 / (
            two ** (QQ(7) / QQ(3)) * pi)
    if r == 4:
        return (two.sqrt() + 1) * _gamma(field, 1, 4) ** 2 / (
            two ** (QQ(7) / QQ(2)) * pi.sqrt())
    if r == 5:
        return (five.sqrt() + 2) ** (QQ(1) / QQ(4)) * (
            _gamma(field, 1, 20) * _gamma(field, 3, 20)
            * _gamma(field, 7, 20) * _gamma(field, 9, 20)
            / (160 * pi)
        ).sqrt()
    if r == 6:
        algebraic = ((two.sqrt() - 1) * (three.sqrt() + two.sqrt())
                     * (2 + three.sqrt())).sqrt()
        gamma_part = (
            _gamma(field, 1, 24) * _gamma(field, 5, 24)
            * _gamma(field, 7, 24) * _gamma(field, 11, 24)
            / (384 * pi)
        ).sqrt()
        return algebraic * gamma_part
    if r == 7:
        return _gamma(field, 1, 7) * _gamma(field, 2, 7) * _gamma(field, 4, 7) / (
            4 * seven ** (QQ(1) / QQ(4)) * pi)
    if r == 8:
        algebraic = ((2 * two.sqrt() + (1 + 5 * two.sqrt()).sqrt())
                     / (4 * two.sqrt())).sqrt()
        gamma_part = ((two.sqrt() + 1) ** (QQ(1) / QQ(4))
                      * _gamma(field, 1, 8) * _gamma(field, 3, 8)
                      / (8 * pi.sqrt()))
        return algebraic * gamma_part
    if r == 9:
        return three ** (QQ(1) / QQ(4)) * (2 + three.sqrt()).sqrt() * _gamma(
            field, 1, 4) ** 2 / (12 * pi.sqrt())
    if r == 10:
        algebraic = (2 + 3 * two.sqrt() + five.sqrt()).sqrt()
        gamma_part = (
            _gamma(field, 1, 40) * _gamma(field, 7, 40)
            * _gamma(field, 9, 40) * _gamma(field, 11, 40)
            * _gamma(field, 13, 40) * _gamma(field, 19, 40)
            * _gamma(field, 23, 40) * _gamma(field, 37, 40)
            / (2560 * pi ** 3)
        ).sqrt()
        return algebraic * gamma_part
    raise ValueError("no closed form recorded for r=%s" % r)


class CompleteEllipticKSingularValues(numberdb.Generator):
    """Generator for T296, the values K(k_r) at singular values."""

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
        number = _singular_k_value(r, digits)
        entry = {"number": number}
        comment = CLOSED_FORM_COMMENTS.get(int(r))
        if comment:
            entry["comment"] = comment
        if r == 1:
            entry["equals"] = "HREF{%s#1/2}" % K_TABLE
        return entry


def _overlaps_zero(value):
    return value.contains_zero()


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    worst_value_radius = field(0)
    worst_value_at = None
    worst_check_radius = field(0)
    worst_check_at = None

    for r in range(1, MAX_R + 1):
        value = _singular_k_value(r, DIGITS, CHECK_GUARD)
        theta_value = _theta_check_value(r, DIGITS)
        if not _overlaps_zero(theta_value - value):
            raise ArithmeticError("theta check failed at r=%d: %s vs %s" % (r, theta_value, value))

        hypergeometric_value = _hypergeometric_check_value(r, DIGITS)
        if not _overlaps_zero(hypergeometric_value - value):
            raise ArithmeticError(
                "hypergeometric check failed at r=%d: %s vs %s"
                % (r, hypergeometric_value, value))

        m = _lambda_parameter(r, DIGITS, CHECK_GUARD)
        complement = _elliptic_k_at_parameter(1 - m, DIGITS, CHECK_GUARD)
        ratio = complement / value
        if not _overlaps_zero(ratio - field(r).sqrt()):
            raise ArithmeticError("complement quotient failed at r=%d: %s" % (r, ratio))

        if r <= 10:
            closed = _closed_form(r, DIGITS)
            if not _overlaps_zero(closed - value):
                raise ArithmeticError("closed form failed at r=%d: %s vs %s" % (r, closed, value))

        value_radius = field(value.rad())
        if value_radius > worst_value_radius:
            worst_value_radius = value_radius
            worst_value_at = r
        for label, checked in (
            ("theta", theta_value),
            ("hypergeometric", hypergeometric_value),
        ):
            radius = field(checked.rad())
            if radius > worst_check_radius:
                worst_check_radius = radius
                worst_check_at = (r, label)

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
    generator = CompleteEllipticKSingularValues()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="complete elliptic integrals at singular values for r=1..100"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
