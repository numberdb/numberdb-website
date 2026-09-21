"""Arithmetic factors in the moments of quadratic Dirichlet L-functions -- numberdb.org/T380

This generator fills T380 with the arithmetic Euler-product factors in the
CFKRS leading constants for moments of quadratic Dirichlet L-functions.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

In this checkout, use the repository wrapper:

    $ agents/sage.sh generators/arithmetic-factors-quadratic-dirichlet-moments/generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generators/arithmetic-factors-quadratic-dirichlet-moments/generate.py
"""

import os
import sys
from fractions import Fraction

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T380")
DIGITS = 100
AGREEMENT_DIGITS = (140, 160)
SETTINGS = {
    140: {"small": 1000, "large": 100000, "order": 160,
          "residual_order": 35, "mobius_terms": 280},
    160: {"small": 2000, "large": 200000, "order": 220,
          "residual_order": 45, "mobius_terms": 360},
}
K_VALUES = tuple(Fraction(n, 2) for n in range(1, 13)) + tuple(
    Fraction(n) for n in range(7, 13))

_SUMS = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _fraction(text):
    return Fraction(str(text))


def _prime_sieve(bound):
    sieve = bytearray(b"\x01") * (bound + 1)
    sieve[:2] = b"\x00\x00"
    p = 2
    while p * p <= bound:
        if sieve[p]:
            start = p * p
            sieve[start:bound + 1:p] = b"\x00" * (((bound - start) // p) + 1)
        p += 1
    return [i for i in range(2, bound + 1) if sieve[i]]


def _mobius(n):
    x = n
    p = 2
    factors = 0
    while p * p <= x:
        if x % p == 0:
            x //= p
            factors += 1
            if x % p == 0:
                return 0
        p += 1 if p == 2 else 2
    if x > 1:
        factors += 1
    return -1 if factors % 2 else 1


def _rising_over_factorial(a, n):
    out = Fraction(1)
    for j in range(n):
        out *= a + j
        out /= j + 1
    return out


def _binomial(a, n):
    out = Fraction(1)
    for j in range(n):
        out *= a - j
        out /= j + 1
    return out


def _convolve(left, right, order):
    out = [Fraction(0) for _ in range(order + 1)]
    for i, a in enumerate(left[:order + 1]):
        if not a:
            continue
        for j, b in enumerate(right[:order + 1 - i]):
            if b:
                out[i + j] += a * b
    return out


def _log_series(unit, order):
    """Exact coefficients of log(unit), where unit[0] is 1."""
    if unit[0] != 1:
        raise ArithmeticError("log series needs constant term 1")
    log_unit = [Fraction(0) for _ in range(order + 1)]
    for n in range(1, order + 1):
        lower = sum(
            (j * log_unit[j] * unit[n - j] for j in range(1, n)),
            Fraction(0),
        )
        log_unit[n] = unit[n] - lower / n
    return log_unit


def _log_factor_coefficients(k, order):
    """Exact coefficients of the logarithm of the quadratic-family local factor."""
    k = Fraction(k)
    exponent = k * (k + 1) / 2

    positive_part = [Fraction(0) for _ in range(order + 1)]
    for m in range(order + 1):
        positive_part[m] = _rising_over_factorial(k, 2 * m)
    positive_part[1] += 1

    divided_by_one_plus_x = []
    for n in range(order + 1):
        coefficient = Fraction(0)
        for j in range(n + 1):
            coefficient += ((-1) ** (n - j)) * positive_part[j]
        divided_by_one_plus_x.append(coefficient)

    one_minus_x_to_exponent = [
        ((-1) ** n) * _binomial(exponent, n) for n in range(order + 1)
    ]
    local = _convolve(one_minus_x_to_exponent,
                      divided_by_one_plus_x, order)
    coefficients = _log_series(local, order)
    if coefficients[1] != 0:
        raise ArithmeticError(
            "the p^-1 coefficient did not cancel for k=%s: %s" %
            (k, coefficients[1]))
    return coefficients


def _prime_zeta(s, field, terms):
    total = field(0)
    for n in range(1, terms + 1):
        mu = _mobius(n)
        if mu:
            total += field(mu) * field(n * s).zeta().log() / field(n)
    return total


def _prime_power_sums(field, small, large, order):
    key = (field.prec(), small, large, order)
    if key in _SUMS:
        return _SUMS[key]

    primes = _prime_sieve(large)
    small_primes = [p for p in primes if p <= small]
    medium = [field(0) for _ in range(order + 1)]
    prefix = [field(0) for _ in range(order + 1)]
    for p in primes:
        inv = field(1) / field(p)
        power = field(1)
        for j in range(1, order + 1):
            power *= inv
            if p > small:
                medium[j] += power
            prefix[j] += power

    _SUMS[key] = (small_primes, medium, prefix)
    return _SUMS[key]


def _local_factor(k, p, field):
    qk = QQ(k.numerator) / QQ(k.denominator)
    exponent = qk * (qk + 1) / QQ(2)
    inv = field(1) / field(p)
    root = inv.sqrt()
    average = (((field(1) - root) ** (-qk)
                + (field(1) + root) ** (-qk)) / field(2))
    value = ((field(1) - inv) ** exponent
             * (average + inv) / (field(1) + inv))
    if value <= 0:
        raise ArithmeticError(
            "non-positive local factor for k=%s, p=%s: %s" % (k, p, value))
    return value


def _log_arithmetic_factor(k, working_digits):
    settings = SETTINGS[working_digits]
    field = RealField(numberdb.bits(working_digits, losing=192))

    small_primes, medium, prefix = _prime_power_sums(
        field,
        settings["small"],
        settings["large"],
        settings["order"],
    )
    total = field(0)
    for p in small_primes:
        total += _local_factor(k, p, field).log()

    coefficients = _log_factor_coefficients(k, settings["order"])
    for j in range(2, settings["order"] + 1):
        coefficient = coefficients[j]
        if not coefficient:
            continue
        tail = medium[j]
        if j <= settings["residual_order"]:
            tail += (_prime_zeta(j, field, settings["mobius_terms"])
                     - prefix[j])
        total += (field(coefficient.numerator)
                  / field(coefficient.denominator)) * tail
    return total


def _decimal(value, digits):
    return format(value, ".%de" % (digits - 1))


def _arithmetic_factor_decimal(k, working_digits):
    return _decimal(_log_arithmetic_factor(k, working_digits).exp(),
                    working_digits)


def _integer_local_expression(k):
    exponent = k * (k + 1) // 2
    finite_sum = "sum(m=0, %d, binomial(%d, 2*m)/p^m)" % (k // 2, k)
    return (
        "(1 - 1/p)^%d * (((%s)/(1 - 1/p)^%d + 1/p)/(1 + 1/p))"
        % (exponent, finite_sum, k)
    )


def _integer_factor_pari(k, digits=120):
    pari("default(realprecision, %d)" % digits)
    return str(pari("prodeulerrat(%s, 1, 2)"
                    % _integer_local_expression(k)))


def _value_comment(k):
    if k == Fraction(1):
        return r"The first moment has local factor $1-1/(p(p+1))$ at each prime."
    return None


def _assert_relative_close(label, left, right, field, tolerance):
    left = field(left)
    right = field(right)
    scale = max(field(1), abs(right))
    if abs(left - right) / scale > tolerance:
        raise ArithmeticError(
            "%s control failed: %s versus %s" % (label, left, right))


def run_private_checks():
    for k in K_VALUES:
        coefficients = _log_factor_coefficients(k, 20)
        if coefficients[1] != 0:
            raise ArithmeticError("the k=%s p^-1 coefficient is not zero" % k)

    field = RealField(numberdb.bits(120, losing=128))
    for k in range(1, 13):
        computed = _arithmetic_factor_decimal(Fraction(k), 160)
        controlled = _integer_factor_pari(k)
        _assert_relative_close("PARI integer k=%d" % k, computed, controlled,
                               field, field(10) ** -90)


class QuadraticDirichletMomentArithmeticFactors(numberdb.Generator):

    table = TABLE
    parameters = ("k",)
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for k in K_VALUES:
            yield {"k": str(k)}

    def value(self, params, digits):
        k = _fraction(params["k"])
        number = numberdb.agreeing(
            lambda working: _arithmetic_factor_decimal(k, working),
            at=AGREEMENT_DIGITS,
        )
        entry = {"number": number}
        comment = _value_comment(k)
        if comment:
            entry["comment"] = comment
        return entry


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


if __name__ == "__main__":
    _key_from_stdin()
    run_private_checks()
    generator = QuadraticDirichletMomentArithmeticFactors()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill quadratic Dirichlet moment arithmetic factors"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
