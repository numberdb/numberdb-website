"""Sharp constant in Nash's inequality -- numberdb.org/T359

This table stores the least constant C_n in the squared upper-bound form

    ||u||_2^(2+4/n) <= C_n ||grad u||_2^2 ||u||_1^(4/n)

on R^n. Carlen and Loss give

    C_n = 2 (1+n/2)^(1+2/n) / (n lambda_n kappa_n^(2/n)),

where kappa_n is the volume of the unit ball and lambda_n is the first
positive radial Neumann eigenvalue on that ball. The eigenvalue is
j_(n/2,1)^2, the square of the first positive zero of J_(n/2).

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish

Under the repository's agent runner, pipe the API key on stdin:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
        agents/sage.sh generators/sharp-constant-nash-inequality/generate.py

Set NUMBERDB_PUBLISH=preview to preview the write, or NUMBERDB_PUBLISH=1 to
send the entries and attach this file.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


MAX_DIMENSION = 20
WORKING_GUARD = 768
BRACKET_STEP = QQ(1) / QQ(16)
BISECTION_STEPS = 420
SERIES_TERMS = 220


def configure_key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        numberdb.configure(api_key=token)


def rational_power(base, exponent):
    return (base.parent()(exponent) * base.log()).exp()


def _with_tail(total, next_term):
    return total.add_error(abs(next_term))


def _bessel_j0_or_j1(field, order, x):
    half = x / 2
    term = field(1) if order == 0 else half
    total = term
    sign = -1
    for k in range(SERIES_TERMS):
        term *= (half * half) / (ZZ(k + 1) * ZZ(k + order + 1))
        total = total + term if sign > 0 else total - term
        sign *= -1
    return _with_tail(total, term)


def _bessel_j_integer(field, order, x):
    order = ZZ(order)
    if order == 0:
        return _bessel_j0_or_j1(field, 0, x)
    if order == 1:
        return _bessel_j0_or_j1(field, 1, x)

    previous = _bessel_j0_or_j1(field, 0, x)
    current = _bessel_j0_or_j1(field, 1, x)
    for k in range(1, int(order)):
        previous, current = current, (2 * ZZ(k) / x) * current - previous
    return current


def _spherical_bessel_j(field, order, x):
    order = ZZ(order)
    j0 = x.sin() / x
    if order == 0:
        return j0
    j1 = x.sin() / (x * x) - x.cos() / x
    if order == 1:
        return j1

    previous, current = j0, j1
    for k in range(1, int(order)):
        previous, current = current, ((2 * ZZ(k) + 1) / x) * current - previous
    return current


def _bessel_for_dimension(field, n, x):
    n = ZZ(n)
    if n % 2 == 0:
        return _bessel_j_integer(field, n // 2, x)
    return _spherical_bessel_j(field, (n - 1) // 2, x)


def _sign_of_bessel(field, n, x):
    value = _bessel_for_dimension(field, n, field(x))
    if not value.is_finite():
        raise ArithmeticError("non-finite Bessel ball at n=%s, x=%s" % (n, x))
    if value > 0:
        return 1
    if value < 0:
        return -1
    raise ArithmeticError("Bessel sign is not isolated at n=%s, x=%s: %s"
                          % (n, x, value))


def first_zero_ball(field, n):
    n = ZZ(n)
    left = BRACKET_STEP
    left_sign = _sign_of_bessel(field, n, left)
    right = left + BRACKET_STEP
    while right <= 4 * n + 20:
        right_sign = _sign_of_bessel(field, n, right)
        if right_sign != left_sign:
            break
        left, left_sign = right, right_sign
        right += BRACKET_STEP
    else:
        raise ArithmeticError("no first zero bracket found for n=%s" % n)

    for _ in range(BISECTION_STEPS):
        midpoint = (left + right) / 2
        midpoint_sign = _sign_of_bessel(field, n, midpoint)
        if midpoint_sign == left_sign:
            left, left_sign = midpoint, midpoint_sign
        else:
            right = midpoint

    center = (left + right) / 2
    radius = (right - left) / 2
    root = field(center).add_error(field(radius))
    if not _bessel_for_dimension(field, n, root).contains_zero():
        raise ArithmeticError("root ball does not contain a zero for n=%s" % n)
    return root


def unit_ball_volume(field, n):
    n = QQ(n)
    return rational_power(field.pi(), n / 2) / field(1 + n / 2).gamma()


def nash_constant(field, n):
    n = ZZ(n)
    root = first_zero_ball(field, n)
    lam = root * root
    numerator = 2 * rational_power(field(1 + QQ(n) / 2), 1 + QQ(2) / n)
    denominator = field(n) * lam * rational_power(unit_ball_volume(field, n), QQ(2) / n)
    value = numerator / denominator
    if not value.is_finite():
        raise ArithmeticError("computed a non-finite ball for n=%s" % n)
    return value


class NashInequalitySharpConstants(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE") or "T359"
    parameters = ("n",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for n in range(1, MAX_DIMENSION + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        return nash_constant(field, ZZ(params["n"]))


def run_integrity_checks():
    field = RealBallField(numberdb.bits(120, losing=WORKING_GUARD))
    expected_c1 = ZZ(27) / (ZZ(16) * field.pi() ** 2)
    if not nash_constant(field, 1).overlaps(expected_c1):
        raise ArithmeticError("the n=1 constant does not match 27/(16*pi^2)")

    for n in range(1, MAX_DIMENSION + 1):
        root = first_zero_ball(field, n)
        if root <= 0:
            raise ArithmeticError("non-positive first zero for n=%s" % n)
        if not _bessel_for_dimension(field, n, root).contains_zero():
            raise ArithmeticError("Bessel zero check failed for n=%s" % n)


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe."""
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
        produced_by=_producer(
            generator,
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex-cli"),
        ),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    files = _source_files(generator)
    stored = []
    for name, body in sorted(files.items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


def main():
    configure_key_from_stdin()
    generator = NashInequalitySharpConstants()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if "--publish" in sys.argv or mode == "1":
        run_integrity_checks()
        print(fill_draft_once(generator, "sharp Nash inequality constants"))
        return
    if "--preview" in sys.argv or mode == "preview":
        run_integrity_checks()
        print(generator.preview())
        return
    report = generator.verify(sample=None)
    print(report)
    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
