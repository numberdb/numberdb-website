r"""Wigner 9j symbols -- numberdb.org/T363

This draft stores every nonzero Wigner 9j symbol

    { j1 j2 j3 }
    { j4 j5 j6 }
    { j7 j8 j9 }

with all ji <= 5/2, using the lexicographically largest representative among
the 72 row, column and transposition symmetries. The all-zero symbol, whose
value is 1, is omitted.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed from the DLMF finite sum of three Wigner 6j symbols.
Each 6j symbol is computed by Racah's finite sum in exact rational arithmetic.
The resulting radical terms are kept as rational multiples of square roots of
squarefree rationals until they are converted to Arb balls for storage. Sums
that are exact rationals are written exactly.
"""

import os
import sys
from itertools import permutations

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TID = "T363"
TWICE_J_UP_TO = 5
DIGITS = 100
WORKING_GUARD = 160


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


def six_j_admissible(symbol):
    a, b, c, d, e, f = symbol
    return (
        triangle(a, b, c)
        and triangle(a, e, f)
        and triangle(d, b, f)
        and triangle(d, e, c)
    )


def nine_j_admissible(symbol):
    a, b, c, d, e, f, g, h, i = symbol
    return (
        triangle(a, b, c)
        and triangle(d, e, f)
        and triangle(g, h, i)
        and triangle(a, d, g)
        and triangle(b, e, h)
        and triangle(c, f, i)
    )


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
    if not six_j_admissible(symbol):
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


def squarefree_rational_factor(value):
    if value < 0:
        raise ValueError("negative radicand %s" % (value,))
    if value == 0:
        return QQ(0), QQ(1)

    outside_num = ZZ(1)
    inside_num = ZZ(1)
    for prime, exponent in ZZ(value.numerator()).factor():
        outside_num *= prime ** (exponent // 2)
        if exponent % 2:
            inside_num *= prime

    outside_den = ZZ(1)
    inside_den = ZZ(1)
    for prime, exponent in ZZ(value.denominator()).factor():
        outside_den *= prime ** (exponent // 2)
        if exponent % 2:
            inside_den *= prime

    return QQ(outside_num) / QQ(outside_den), QQ(inside_num) / QQ(inside_den)


def add_radical_term(terms, coefficient, radicand):
    coefficient = QQ(coefficient)
    radicand = QQ(radicand)
    if coefficient == 0 or radicand == 0:
        return
    outside, inside = squarefree_rational_factor(radicand)
    coefficient *= outside
    terms[inside] = terms.get(inside, QQ(0)) + coefficient
    if terms[inside] == 0:
        del terms[inside]


def scaled_terms(terms, factor):
    factor = QQ(factor)
    if factor == 0:
        return {}
    return {radicand: coefficient * factor for radicand, coefficient in terms.items()}


def single_radical_terms(coefficient, radicand):
    terms = {}
    add_radical_term(terms, coefficient, radicand)
    return terms


def product_term(factors):
    coefficient = QQ(1)
    radicand = QQ(1)
    for multiplier, factor_radicand in factors:
        if multiplier == 0:
            return QQ(0), QQ(1)
        coefficient *= multiplier
        radicand *= factor_radicand
    return coefficient, radicand


def exact_or_ball(terms, digits):
    if not terms:
        return QQ(0)
    if len(terms) == 1 and QQ(1) in terms:
        return terms[QQ(1)]

    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    total = field(0)
    for radicand, coefficient in sorted(terms.items(), key=lambda item: item[0]):
        total += field(coefficient) * field(radicand).sqrt()
    if not total.is_finite():
        raise ArithmeticError("non-finite ball for radical sum %s" % (terms,))
    return total


def terms_overlap(first, second, digits=DIGITS):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    return field(exact_or_ball(first, digits)).overlaps(
        field(exact_or_ball(second, digits))
    )


def wigner_9j_terms(symbol):
    if not nine_j_admissible(symbol):
        return {}

    a, b, c, d, e, f, g, h, i = symbol
    total = {}
    for t in range(sum(symbol) + 1):
        first = wigner_6j_multiplier_radicand(a, d, g, h, i, t)
        if first[0] == 0:
            continue
        second = wigner_6j_multiplier_radicand(b, e, h, d, t, f)
        if second[0] == 0:
            continue
        third = wigner_6j_multiplier_radicand(c, f, i, t, a, b)
        if third[0] == 0:
            continue

        coefficient, radicand = product_term((first, second, third))
        coefficient *= QQ((-1) ** t) * QQ(t + 1)
        add_radical_term(total, coefficient, radicand)
    return total


def wigner_3j_multiplier_radicand(a, b, c, p, q, r):
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


def magnetic_values(twice_j):
    return range(-twice_j, twice_j + 1, 2)


def allowed_m(twice_j, twice_m):
    return (
        -twice_j <= twice_m <= twice_j
        and (twice_j - twice_m) % 2 == 0
    )


def wigner_9j_terms_from_3j(symbol):
    if not nine_j_admissible(symbol):
        return {}

    a, b, c, d, e, f, g, h, i = symbol
    total = {}
    for ma in magnetic_values(a):
        for mb in magnetic_values(b):
            mc = -ma - mb
            if not allowed_m(c, mc):
                continue
            for md in magnetic_values(d):
                for me in magnetic_values(e):
                    mf = -md - me
                    if not allowed_m(f, mf):
                        continue
                    mg = -ma - md
                    mh = -mb - me
                    mi = -mc - mf
                    if (
                        not allowed_m(g, mg)
                        or not allowed_m(h, mh)
                        or not allowed_m(i, mi)
                        or mg + mh + mi != 0
                    ):
                        continue
                    factors = [
                        wigner_3j_multiplier_radicand(a, b, c, ma, mb, mc),
                        wigner_3j_multiplier_radicand(d, e, f, md, me, mf),
                        wigner_3j_multiplier_radicand(g, h, i, mg, mh, mi),
                        wigner_3j_multiplier_radicand(a, d, g, ma, md, mg),
                        wigner_3j_multiplier_radicand(b, e, h, mb, me, mh),
                        wigner_3j_multiplier_radicand(c, f, i, mc, mf, mi),
                    ]
                    coefficient, radicand = product_term(factors)
                    add_radical_term(total, coefficient, radicand)
    return total


def permutation_parity(order):
    inversions = 0
    for left in range(len(order)):
        for right in range(left + 1, len(order)):
            if order[left] > order[right]:
                inversions += 1
    return inversions % 2


def as_array(symbol):
    return [list(symbol[0:3]), list(symbol[3:6]), list(symbol[6:9])]


def flatten(array):
    return tuple(array[row][column] for row in range(3) for column in range(3))


def symmetry_images(symbol):
    total = sum(symbol)
    if total % 2:
        raise ValueError("sum of 9j arguments is not an integer")
    base = as_array(symbol)
    for transpose in (False, True):
        if transpose:
            array = [[base[column][row] for column in range(3)] for row in range(3)]
        else:
            array = base
        for row_order in permutations((0, 1, 2)):
            row_parity = permutation_parity(row_order)
            for column_order in permutations((0, 1, 2)):
                column_parity = permutation_parity(column_order)
                image = [
                    [array[row_order[row]][column_order[column]] for column in range(3)]
                    for row in range(3)
                ]
                phase = ZZ(1)
                if (row_parity + column_parity) % 2:
                    phase = phase_from_sum(total)
                yield flatten(image), phase


def canonical(symbol):
    return max(image for image, _phase in symmetry_images(symbol))


def triads(up_to):
    for a in range(up_to + 1):
        for b in range(up_to + 1):
            for c in range(up_to + 1):
                if triangle(a, b, c):
                    yield (a, b, c)


def enumerate_symbols(up_to=TWICE_J_UP_TO):
    rows = list(triads(up_to))
    symbols = []
    for first in rows:
        for second in rows:
            for third in rows:
                symbol = first + second + third
                if symbol == (0,) * 9:
                    continue
                if not nine_j_admissible(symbol):
                    continue
                if canonical(symbol) != symbol:
                    continue
                if not wigner_9j_terms(symbol):
                    continue
                symbols.append(symbol)
    symbols.sort(key=lambda item: (max(item), sum(item), item))
    return symbols


def params_from_symbol(symbol):
    return {
        "j1": half_text(symbol[0]),
        "j2": half_text(symbol[1]),
        "j3": half_text(symbol[2]),
        "j4": half_text(symbol[3]),
        "j5": half_text(symbol[4]),
        "j6": half_text(symbol[5]),
        "j7": half_text(symbol[6]),
        "j8": half_text(symbol[7]),
        "j9": half_text(symbol[8]),
    }


def symbol_from_params(params):
    return (
        parse_half(params["j1"]),
        parse_half(params["j2"]),
        parse_half(params["j3"]),
        parse_half(params["j4"]),
        parse_half(params["j5"]),
        parse_half(params["j6"]),
        parse_half(params["j7"]),
        parse_half(params["j8"]),
        parse_half(params["j9"]),
    )


def zero_entry_terms(symbol):
    a, b, c, d, e, f, g, h, i = symbol
    if i != 0 or f != c or h != g:
        return None
    multiplier, radicand = wigner_6j_multiplier_radicand(a, b, c, e, d, g)
    denominator = QQ((c + 1) * (g + 1))
    phase = phase_from_sum(b + d + c + g)
    return single_radical_terms(QQ(phase) * multiplier, radicand / denominator)


_CHECKED = False
_SYMBOLS = None


def all_symbols():
    global _SYMBOLS
    if _SYMBOLS is None:
        _SYMBOLS = enumerate_symbols()
    return _SYMBOLS


def self_check():
    global _CHECKED
    if _CHECKED:
        return

    symbols = all_symbols()
    if len(symbols) != 764:
        raise ArithmeticError("expected 764 stored symbols, got %d" % len(symbols))

    admissible = [
        symbol
        for symbol in (
            first + second + third
            for first in triads(TWICE_J_UP_TO)
            for second in triads(TWICE_J_UP_TO)
            for third in triads(TWICE_J_UP_TO)
        )
        if symbol != (0,) * 9
        and nine_j_admissible(symbol)
        and canonical(symbol) == symbol
    ]
    vanished = [symbol for symbol in admissible if not wigner_9j_terms(symbol)]
    if len(admissible) != 803 or len(vanished) != 39:
        raise ArithmeticError(
            "admissible/vanishing count changed: %d/%d"
            % (len(admissible), len(vanished))
        )

    for symbol in symbols:
        terms = wigner_9j_terms(symbol)

        via_3j = wigner_9j_terms_from_3j(symbol)
        if terms != via_3j and not terms_overlap(terms, via_3j):
            raise ArithmeticError("3j finite sum failed at %s" % (symbol,))

        for image, phase in symmetry_images(symbol):
            image_terms = wigner_9j_terms(image)
            expected = scaled_terms(terms, phase)
            if image_terms != expected and not terms_overlap(image_terms, expected):
                raise ArithmeticError(
                    "9j symmetry failed at %s -> %s" % (symbol, image)
                )
            special = zero_entry_terms(image)
            if special is not None:
                if image_terms != special and not terms_overlap(image_terms, special):
                    raise ArithmeticError("zero-entry formula failed at %s" % (image,))

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


class Wigner9jSymbols(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE", TID)
    parameters = ("j1", "j2", "j3", "j4", "j5", "j6", "j7", "j8", "j9")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, twice_j_up_to=TWICE_J_UP_TO):
        for symbol in all_symbols():
            if max(symbol) <= twice_j_up_to:
                yield params_from_symbol(symbol)

    def value(self, params, digits):
        self_check()
        return exact_or_ball(wigner_9j_terms(symbol_from_params(params)), digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = Wigner9jSymbols()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if mode == "1" or "--publish" in sys.argv:
        print(
            fill_draft_once(
                generator,
                message="Wigner 9j symbols with j <= 5/2",
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
