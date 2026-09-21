"""Arithmetic factors $a_k$ in the moments of the Riemann zeta function -- numberdb.org/T377

This generator fills T377 with the arithmetic Euler-product factors in the
Keating-Snaith and CFKRS leading constants for zeta moments.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

In this checkout, use the repository wrapper:

    $ agents/sage.sh generators/arithmetic-factors-zeta-moments/generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generators/arithmetic-factors-zeta-moments/generate.py
"""

import os
import sys
from fractions import Fraction

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T377")
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


def _log_factor_coefficients(k, order):
    """Exact coefficients of log((1 - x)^(k^2) * 2F1(k,k;1;x))."""
    k = Fraction(k)
    h = [Fraction(0) for _ in range(order + 1)]
    h[0] = Fraction(1)
    coefficient = Fraction(1)
    for m in range(1, order + 1):
        coefficient *= (k + (m - 1)) ** 2
        coefficient /= m ** 2
        h[m] = coefficient

    log_h = [Fraction(0) for _ in range(order + 1)]
    for n in range(1, order + 1):
        lower = sum(
            (j * log_h[j] * h[n - j] for j in range(1, n)),
            Fraction(0),
        )
        log_h[n] = h[n] - lower / n

    k_squared = k * k
    return [Fraction(0)] + [
        log_h[n] - k_squared / n for n in range(1, order + 1)
    ]


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


def _local_factor(k, p, complex_field, real_field):
    x = complex_field(QQ(1) / p)
    value = ((1 - x) ** complex_field(k * k)
             * x.hypergeometric([complex_field(k), complex_field(k)],
                                [complex_field(1)]))
    real = value.real()
    if real.lower() <= 0:
        raise ArithmeticError(
            "non-positive local factor for k=%s, p=%s: %s" % (k, p, real))
    return real_field(real.mid())


def _log_arithmetic_factor(k, working_digits):
    settings = SETTINGS[working_digits]
    real_field = RealField(numberdb.bits(working_digits, losing=192))
    complex_field = ComplexBallField(numberdb.bits(working_digits, losing=192))
    qk = QQ(k.numerator) / QQ(k.denominator)

    small_primes, medium, prefix = _prime_power_sums(
        real_field,
        settings["small"],
        settings["large"],
        settings["order"],
    )
    total = real_field(0)
    for p in small_primes:
        total += _local_factor(qk, p, complex_field, real_field).log()

    coefficients = _log_factor_coefficients(k, settings["order"])
    for j in range(2, settings["order"] + 1):
        coefficient = coefficients[j]
        if not coefficient:
            continue
        tail = medium[j]
        if j <= settings["residual_order"]:
            tail += (_prime_zeta(j, real_field, settings["mobius_terms"])
                     - prefix[j])
        total += (real_field(coefficient.numerator)
                  / real_field(coefficient.denominator)) * tail
    return total


def _decimal(value, digits):
    return format(value, ".%de" % (digits - 1))


def _arithmetic_factor_decimal(k, working_digits):
    return _decimal(_log_arithmetic_factor(k, working_digits).exp(),
                    working_digits)


def _integer_factor_pari(k, digits=120):
    pari("default(realprecision, %d)" % digits)
    expression = (
        "(1 - 1/p)^((%d - 1)^2) * "
        "sum(j = 0, %d - 1, binomial(%d - 1, j)^2/p^j)"
        % (k, k, k)
    )
    return str(pari("prodeulerrat(%s, 1, 2)" % expression))


def _value_comment(k):
    if k == Fraction(1):
        return r"Every local factor is $1$, so $a_1=1$."
    if k == Fraction(2):
        return r"Here the finite local factor is $1-p^{-2}$, so $a_2=1/\zeta(2)=6/\pi^2$."
    return None


def _assert_relative_close(label, left, right, field, tolerance):
    left = field(left)
    right = field(right)
    scale = max(field(1), abs(right))
    if abs(left - right) / scale > tolerance:
        raise ArithmeticError(
            "%s control failed: %s versus %s" % (label, left, right))


def run_private_checks():
    coefficients = _log_factor_coefficients(Fraction(1), 20)
    if any(coefficients[1:]):
        raise ArithmeticError("the k=1 logarithmic local factor is not zero")

    field = RealField(numberdb.bits(120, losing=128))
    a2 = _arithmetic_factor_decimal(Fraction(2), 160)
    _assert_relative_close("a_2=6/pi^2", a2,
                           field(6) / (field.pi() ** 2),
                           field, field(10) ** -100)

    for k in range(2, 13):
        computed = _arithmetic_factor_decimal(Fraction(k), 160)
        controlled = _integer_factor_pari(k)
        _assert_relative_close("PARI integer k=%d" % k, computed, controlled,
                               field, field(10) ** -90)


class ZetaMomentArithmeticFactors(numberdb.Generator):

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
        if k == Fraction(1):
            return {"number": 1, "comment": _value_comment(k)}

        number = numberdb.agreeing(
            lambda working: _arithmetic_factor_decimal(k, working),
            at=AGREEMENT_DIGITS,
        )
        entry = {"number": number}
        comment = _value_comment(k)
        if comment:
            entry["comment"] = comment
        if k == Fraction(2):
            entry["equals"] = (
                r"HREF{Named_rational_Euler_products_over_primes#squarefree-density}"
                r"[$6/\pi^2$]"
            )
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
    generator = ZetaMomentArithmeticFactors()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill zeta moment arithmetic factors"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
