r"""Wigner 6j symbols -- numberdb.org/T253

This draft stores every nonzero Wigner 6j symbol

    { j1 j2 j3 }
    { j4 j5 j6 }

with all ji <= 7/2, using the lexicographically largest representative among
the 24 tetrahedral symmetries. The all-zero symbol, whose value is 1, is
omitted.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed from Racah's finite sum in exact rational arithmetic,
represented as a rational multiple of the square root of a rational number,
and then converted to Arb balls for storage. Values that are exact rationals
are written exactly. Before any entry is returned, the whole range is checked
against the zero-entry special case and against the definition as a signed sum
of four Wigner 3j symbols.
"""

import os
import sys
from itertools import permutations

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TID = "T253"
TWICE_J_UP_TO = 7
DIGITS = 100
WORKING_GUARD = 96


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def half_text(twice):
    twice = int(twice)
    if twice % 2 == 0:
        return str(twice // 2)
    sign = "-" if twice < 0 else ""
    return "%s%d/2" % (sign, abs(twice))


def parse_half(text):
    value = QQ(str(text))
    twice = 2 * value
    if twice.denominator() != 1:
        raise ValueError("%s is not an integer or half-integer" % (text,))
    return int(twice)


def phase_from_sum(twice_sum):
    if twice_sum % 2:
        raise ValueError("phase exponent is not an integer")
    return ZZ(-1) ** (twice_sum // 2)


def factorial_int(n):
    if n < 0:
        raise ValueError("negative factorial argument %d" % (n,))
    return ZZ(factorial(int(n)))


def factorial_ratio(numerators, denominators):
    value = QQ(1)
    for n in numerators:
        value *= QQ(factorial_int(n))
    for n in denominators:
        value /= QQ(factorial_int(n))
    return value


def triangle(a, b, c):
    return abs(a - b) <= c <= a + b and (a + b + c) % 2 == 0


def admissible(symbol):
    a, b, c, d, e, f = symbol
    return (
        triangle(a, b, c)
        and triangle(a, e, f)
        and triangle(d, b, f)
        and triangle(d, e, c)
    )


EVEN_SWAP_MASKS = (0, 3, 5, 6)


def tetrahedral_images(symbol):
    a, b, c, d, e, f = symbol
    columns = ((a, d), (b, e), (c, f))
    for order in permutations((0, 1, 2)):
        ordered = [columns[i] for i in order]
        for mask in EVEN_SWAP_MASKS:
            top = []
            bottom = []
            for index, (up, down) in enumerate(ordered):
                if mask & (1 << index):
                    up, down = down, up
                top.append(up)
                bottom.append(down)
            yield tuple(top + bottom)


def canonical(symbol):
    return max(tetrahedral_images(symbol))


def delta_squared(a, b, c):
    if not triangle(a, b, c):
        return QQ(0)
    return factorial_ratio(
        [
            (a + b - c) // 2,
            (a - b + c) // 2,
            (-a + b + c) // 2,
        ],
        [(a + b + c) // 2 + 1],
    )


def wigner_6j_multiplier_radicand(a, b, c, d, e, f):
    symbol = (a, b, c, d, e, f)
    if not admissible(symbol):
        return QQ(0), QQ(1)

    x1 = (a + b + c) // 2
    x2 = (a + e + f) // 2
    x3 = (d + b + f) // 2
    x4 = (d + e + c) // 2
    y1 = (a + b + d + e) // 2
    y2 = (b + c + e + f) // 2
    y3 = (c + a + f + d) // 2

    lower = max(x1, x2, x3, x4)
    upper = min(y1, y2, y3)
    total = QQ(0)
    for z in range(lower, upper + 1):
        denominator_args = [
            z - x1,
            z - x2,
            z - x3,
            z - x4,
            y1 - z,
            y2 - z,
            y3 - z,
        ]
        denominator = ZZ(1)
        for n in denominator_args:
            denominator *= factorial_int(n)
        total += QQ((-1) ** z) * QQ(factorial_int(z + 1)) / QQ(denominator)

    if total == 0:
        return QQ(0), QQ(1)
    radicand = (
        delta_squared(a, b, c)
        * delta_squared(a, e, f)
        * delta_squared(d, b, f)
        * delta_squared(d, e, c)
    )
    return total, radicand


def exact_rational_square_root(value):
    numerator = ZZ(value.numerator())
    denominator = ZZ(value.denominator())
    n_root, n_remainder = numerator.sqrtrem()
    d_root, d_remainder = denominator.sqrtrem()
    if n_remainder == 0 and d_remainder == 0:
        return QQ(n_root) / QQ(d_root)
    return None


def exact_or_ball(multiplier, radicand, digits):
    if multiplier == 0:
        return QQ(0)
    exact = exact_rational_square_root(radicand)
    if exact is not None:
        return multiplier * exact
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    value = field(multiplier) * field(radicand).sqrt()
    if not value.is_finite():
        raise ArithmeticError(
            "non-finite ball for %s * sqrt(%s)" % (multiplier, radicand)
        )
    return value


def exact_value(symbol, digits=DIGITS):
    multiplier, radicand = wigner_6j_multiplier_radicand(*symbol)
    return exact_or_ball(multiplier, radicand, digits)


def overlaps(value, other, digits=DIGITS):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    return field(value).overlaps(field(other))


def nonzero_symbol(symbol):
    multiplier, _ = wigner_6j_multiplier_radicand(*symbol)
    return multiplier != 0


def enumerate_symbols(up_to=TWICE_J_UP_TO):
    for a in range(up_to + 1):
        for b in range(up_to + 1):
            for c in range(up_to + 1):
                for d in range(up_to + 1):
                    for e in range(up_to + 1):
                        for f in range(up_to + 1):
                            symbol = (a, b, c, d, e, f)
                            if symbol == (0, 0, 0, 0, 0, 0):
                                continue
                            if not admissible(symbol):
                                continue
                            if canonical(symbol) != symbol:
                                continue
                            if not nonzero_symbol(symbol):
                                continue
                            yield symbol


def params_from_symbol(symbol):
    return {
        "j1": half_text(symbol[0]),
        "j2": half_text(symbol[1]),
        "j3": half_text(symbol[2]),
        "j4": half_text(symbol[3]),
        "j5": half_text(symbol[4]),
        "j6": half_text(symbol[5]),
    }


def symbol_from_params(params):
    return (
        parse_half(params["j1"]),
        parse_half(params["j2"]),
        parse_half(params["j3"]),
        parse_half(params["j4"]),
        parse_half(params["j5"]),
        parse_half(params["j6"]),
    )


def wigner_3j_multiplier_radicand(a, b, c, p, q, r):
    """Return q, R with Wigner 3j = q * sqrt(R)."""
    if (
        not triangle(a, b, c)
        or p + q + r != 0
        or not (-a <= p <= a and -b <= q <= b and -c <= r <= c)
        or (a - p) % 2
        or (b - q) % 2
        or (c - r) % 2
    ):
        return QQ(0), QQ(1)

    A = (a + b - c) // 2
    B = (a - b + c) // 2
    C = (-a + b + c) // 2
    D = (a + b + c) // 2 + 1
    m_factor_args = [
        (a + p) // 2,
        (a - p) // 2,
        (b + q) // 2,
        (b - q) // 2,
        (c + r) // 2,
        (c - r) // 2,
    ]
    radicand = factorial_ratio([A, B, C] + m_factor_args, [D])

    s_lower = max(0, -((c - b + p) // 2), -((c - a - q) // 2))
    s_upper = min(A, (a - p) // 2, (b + q) // 2)
    total = QQ(0)
    for s in range(s_lower, s_upper + 1):
        denominator_args = [
            s,
            A - s,
            (a - p) // 2 - s,
            (b + q) // 2 - s,
            (c - b + p) // 2 + s,
            (c - a - q) // 2 + s,
        ]
        denominator = ZZ(1)
        for n in denominator_args:
            denominator *= factorial_int(n)
        total += QQ((-1) ** s) / QQ(denominator)

    if total == 0:
        return QQ(0), QQ(1)
    return QQ(phase_from_sum(a - b - r)) * total, radicand


def ball_wigner_3j(a, b, c, p, q, r, field):
    multiplier, radicand = wigner_3j_multiplier_radicand(a, b, c, p, q, r)
    return field(exact_or_ball(multiplier, radicand, DIGITS))


def six_j_from_three_j(symbol, field):
    a, b, c, d, e, f = symbol
    total = field(0)
    for ma in range(-a, a + 1, 2):
        for mb in range(-b, b + 1, 2):
            mc = -ma - mb
            if mc < -c or mc > c or (c - mc) % 2:
                continue
            for me in range(-e, e + 1, 2):
                mf = -ma + me
                md = -ma + me - mb
                if mf < -f or mf > f or (f - mf) % 2:
                    continue
                if md < -d or md > d or (d - md) % 2:
                    continue
                sign = phase_from_sum(
                    (a - ma)
                    + (b - mb)
                    + (c - mc)
                    + (d - md)
                    + (e - me)
                    + (f - mf)
                )
                total += (
                    field(sign)
                    * ball_wigner_3j(a, b, c, -ma, -mb, -mc, field)
                    * ball_wigner_3j(a, e, f, ma, -me, mf, field)
                    * ball_wigner_3j(d, b, f, md, mb, -mf, field)
                    * ball_wigner_3j(d, e, c, -md, me, mc, field)
                )
    return total


_CHECKED = False


def self_check():
    global _CHECKED
    if _CHECKED:
        return

    field = RealBallField(numberdb.bits(DIGITS, losing=WORKING_GUARD))
    symbols = list(enumerate_symbols())
    for symbol in symbols:
        value = exact_value(symbol)

        for image in tetrahedral_images(symbol):
            if not overlaps(value, exact_value(image)):
                raise ArithmeticError("tetrahedral symmetry failed at %s" % (symbol,))

        if symbol[5] == 0 and symbol[0] == symbol[4] and symbol[1] == symbol[3]:
            a, b, c, _, _, _ = symbol
            expected = field(phase_from_sum(a + b + c)) / (
                field(a + 1).sqrt() * field(b + 1).sqrt()
            )
            if not field(value).overlaps(expected):
                raise ArithmeticError("zero-entry formula failed at %s" % (symbol,))

        via_3j = six_j_from_three_j(symbol, field)
        if not field(value).overlaps(via_3j):
            raise ArithmeticError("3j finite sum failed at %s" % (symbol,))

    _CHECKED = True


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
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
        produced_by=_producer(generator),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    files = _source_files(generator)
    stored = []
    for name, body in sorted(files.items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


class Wigner6jSymbols(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE", TID)
    parameters = ("j1", "j2", "j3", "j4", "j5", "j6")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, twice_j_up_to=TWICE_J_UP_TO):
        for symbol in enumerate_symbols(twice_j_up_to):
            yield params_from_symbol(symbol)

    def value(self, params, digits):
        self_check()
        return exact_value(symbol_from_params(params), digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = Wigner6jSymbols()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if mode == "1" or "--publish" in sys.argv:
        print(
            fill_draft_once(
                generator,
                message="Wigner 6j symbols with j <= 7/2",
            )
        )
    elif mode == "preview" or "--preview" in sys.argv:
        print(generator.preview())
    elif mode == "dry" or "--dry-run" in sys.argv:
        self_check()
        print("%d entries" % sum(1 for _ in generator.enumerate()))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
