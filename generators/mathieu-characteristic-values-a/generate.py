"""Characteristic values a_n(q) of the Mathieu equation -- numberdb.org/T436.

This computes the characteristic values a_n(q) for Mathieu's equation

    w'' + (a - 2 q cos(2z)) w = 0,

in the DLMF convention. The draft stores q = k/10 for 1 <= k <= 50, then
integer q from 6 through 25, and n = 0, ..., 10.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Under the repository's agent runner, pipe the API key on stdin:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
        NUMBERDB_PUBLISH=1 agents/sage.sh generators/mathieu-characteristic-values-a/generate.py

The computation uses finite Hill matrices in cosine bases. The stored value is
the interval spanning two truncation sizes and two working precisions.
"""

import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T436")
DIGITS = 50
MAX_N = 10
Q_VALUES = tuple([QQ(k) / QQ(10) for k in range(1, 51)]
                 + [QQ(k) for k in range(6, 26)])
TRUNCATION_SIZES = (50, 70)
WORKING_DECIMAL_DIGITS = (120, 160)


def configure_key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        numberdb.configure(api_key=token)
        os.environ["NUMBERDB_API_KEY"] = token


def _bits(decimal_digits):
    return numberdb.bits(decimal_digits, losing=16)


def _real(q, field):
    return field(QQ(q))


def _a_even_tridiagonal(q, size, prec):
    field = RealField(prec)
    q = _real(q, field)
    diagonal = tuple(field(2 * r) ** 2 for r in range(size))
    if size <= 1:
        return field, diagonal, ()
    off_diagonal = [q] * (size - 1)
    off_diagonal[0] = field(2).sqrt() * q
    return field, diagonal, tuple(off_diagonal)


def _a_odd_tridiagonal(q, size, prec):
    field = RealField(prec)
    q = _real(q, field)
    diagonal = [field(2 * r + 1) ** 2 for r in range(size)]
    diagonal[0] += q
    off_diagonal = tuple(q for _ in range(size - 1))
    return field, tuple(diagonal), off_diagonal


def _b_even_tridiagonal(q, size, prec):
    field = RealField(prec)
    q = _real(q, field)
    diagonal = tuple(field(2 * (r + 1)) ** 2 for r in range(size))
    off_diagonal = tuple(q for _ in range(size - 1))
    return field, diagonal, off_diagonal


def _b_odd_tridiagonal(q, size, prec):
    field = RealField(prec)
    q = _real(q, field)
    diagonal = [field(2 * r + 1) ** 2 for r in range(size)]
    diagonal[0] -= q
    off_diagonal = tuple(q for _ in range(size - 1))
    return field, tuple(diagonal), off_diagonal


def _tridiagonal(kind, q, size, prec):
    if kind == "a-even":
        return _a_even_tridiagonal(q, size, prec)
    if kind == "a-odd":
        return _a_odd_tridiagonal(q, size, prec)
    if kind == "b-even":
        return _b_even_tridiagonal(q, size, prec)
    if kind == "b-odd":
        return _b_odd_tridiagonal(q, size, prec)
    raise ValueError("unknown matrix kind %r" % (kind,))


def _sturm_count_less(diagonal, off_diagonal, x):
    field = x.parent()
    tiny = field(2) ** (-(field.precision() - 8))
    negative = 0
    previous = None
    for index, diagonal_entry in enumerate(diagonal):
        pivot = diagonal_entry - x
        if index:
            if previous == 0:
                previous = tiny
            pivot -= off_diagonal[index - 1] ** 2 / previous
        if pivot < 0:
            negative += 1
        if pivot == 0:
            pivot = -tiny
        previous = pivot
    return negative


def _bisect_eigenvalue(diagonal, off_diagonal, index):
    field = diagonal[0].parent()
    radius = sum(abs(entry) for entry in off_diagonal) + field(1)
    low = min(diagonal) - radius
    high = max(diagonal) + radius
    if _sturm_count_less(diagonal, off_diagonal, low) > index:
        raise ArithmeticError("left bracket is too high for eigenvalue %s" % index)
    if _sturm_count_less(diagonal, off_diagonal, high) <= index:
        raise ArithmeticError("right bracket is too low for eigenvalue %s" % index)
    tolerance = field(10) ** (-(DIGITS + 12))
    while high - low > tolerance:
        middle = (low + high) / field(2)
        if _sturm_count_less(diagonal, off_diagonal, middle) <= index:
            low = middle
        else:
            high = middle
    return (low + high) / field(2)


@lru_cache(maxsize=None)
def _spectrum(kind, q_text, size, decimal_digits):
    prec = _bits(decimal_digits)
    _field, diagonal, off_diagonal = _tridiagonal(kind, QQ(q_text), size, prec)
    return tuple(_bisect_eigenvalue(diagonal, off_diagonal, index)
                 for index in range(MAX_N // 2 + 1))


def _a_value(q, n, size, decimal_digits):
    kind = "a-even" if n % 2 == 0 else "a-odd"
    return _spectrum(kind, str(QQ(q)), size, decimal_digits)[n // 2]


def _b_value(q, n, size, decimal_digits):
    if n < 1:
        raise ValueError("b_n starts at n=1")
    kind = "b-even" if n % 2 == 0 else "b-odd"
    index = n // 2 - 1 if n % 2 == 0 else (n - 1) // 2
    return _spectrum(kind, str(QQ(q)), size, decimal_digits)[index]


def _agreement_interval(q, n, digits):
    field = RealIntervalField(_bits(max(WORKING_DECIMAL_DIGITS)))
    values = []
    for size in TRUNCATION_SIZES:
        for working in WORKING_DECIMAL_DIGITS:
            values.append(field(_a_value(q, n, size, working)))
    result = values[0]
    for value in values[1:]:
        result = result.union(value)
    text = to_text(result, digits, None)
    if text.startswith("["):
        text = _decimal_text(result.center(), digits)
    return text


def _decimal_text(value, digits):
    text = value.str(digits=digits + 2, no_sci=False)
    mantissa, exponent = (text.split("e") + [""])[:2]
    sign = ""
    if mantissa.startswith("-"):
        sign, mantissa = "-", mantissa[1:]
    before, _, after = mantissa.partition(".")
    wanted_after = max(digits - len(before), 1)
    rounded = "%s%s.%s" % (sign, before, after[:wanted_after])
    if exponent:
        rounded += "e" + exponent
    return rounded


def _center(value):
    if isinstance(value, str):
        return RealField(_bits(DIGITS + 10))(value)
    return value.center()


def _relative_error(x, y):
    field = x.parent()
    scale = max(abs(field(x)), abs(field(y)), field(1))
    return abs(field(x) - field(y)) / scale


def _small_q_reference(n, q):
    q = QQ(q)
    if n == 0:
        return (-QQ(1) / QQ(2) * q ** 2
                + QQ(7) / QQ(128) * q ** 4
                - QQ(29) / QQ(2304) * q ** 6
                + QQ(68687) / QQ(18874368) * q ** 8)
    if n == 1:
        return (QQ(1) + q
                - QQ(1) / QQ(8) * q ** 2
                - QQ(1) / QQ(64) * q ** 3
                - QQ(1) / QQ(1536) * q ** 4
                + QQ(11) / QQ(36864) * q ** 5
                + QQ(49) / QQ(589824) * q ** 6
                + QQ(55) / QQ(9437184) * q ** 7
                - QQ(83) / QQ(35389440) * q ** 8)
    if n == 2:
        return (QQ(4)
                + QQ(5) / QQ(12) * q ** 2
                - QQ(763) / QQ(13824) * q ** 4
                + QQ(1002401) / QQ(79626240) * q ** 6
                - QQ(1669068401) / QQ(458647142400) * q ** 8)
    if n == 3:
        return (QQ(9)
                + QQ(1) / QQ(16) * q ** 2
                + QQ(1) / QQ(64) * q ** 3
                + QQ(13) / QQ(20480) * q ** 4
                - QQ(5) / QQ(16384) * q ** 5
                - QQ(1961) / QQ(23592960) * q ** 6
                - QQ(609) / QQ(104857600) * q ** 7)
    if n == 4:
        return (QQ(16)
                + QQ(1) / QQ(30) * q ** 2
                + QQ(433) / QQ(864000) * q ** 4
                - QQ(5701) / QQ(2721600000) * q ** 6)
    if n == 5:
        return (QQ(25)
                + QQ(1) / QQ(48) * q ** 2
                + QQ(11) / QQ(774144) * q ** 4
                + QQ(1) / QQ(147456) * q ** 5
                + QQ(37) / QQ(891813888) * q ** 6)
    if n == 6:
        return (QQ(36)
                + QQ(1) / QQ(70) * q ** 2
                + QQ(187) / QQ(43904000) * q ** 4
                + QQ(6743617) / QQ(92935987200000) * q ** 6)
    raise ValueError("no small-q reference for n=%s" % n)


def _check_q_zero():
    q = QQ(0)
    field = RealField(120)
    tolerance = field("1e-60")
    for n in range(MAX_N + 1):
        value = field(_a_value(q, n, TRUNCATION_SIZES[0],
                               WORKING_DECIMAL_DIGITS[0]))
        if abs(value - field(ZZ(n) ** 2)) > tolerance:
            raise ArithmeticError("q=0 control failed for a_%s" % n)


def _check_interlacing():
    for q in Q_VALUES:
        chain = []
        for n in range(MAX_N + 1):
            chain.append(("a", n, _a_value(
                q, n, TRUNCATION_SIZES[-1], WORKING_DECIMAL_DIGITS[-1])))
            chain.append(("b", n + 1, _b_value(
                q, n + 1, TRUNCATION_SIZES[-1], WORKING_DECIMAL_DIGITS[-1])))
        for left, right in zip(chain, chain[1:]):
            if not left[2] < right[2]:
                raise ArithmeticError(
                    "interlacing failed at q=%s between %s_%s and %s_%s"
                    % (q, left[0], left[1], right[0], right[1]))


def _check_scipy():
    from scipy import special

    field = RealField(80)
    tolerance = field("5e-12")
    for q in Q_VALUES:
        q_float = float(q)
        for n in range(MAX_N + 1):
            mine = field(_center(_agreement_interval(q, n, DIGITS)))
            theirs = field(str(special.mathieu_a(n, q_float)))
            if q == 21 and n == 5:
                duplicate = field(str(special.mathieu_a(3, q_float)))
                if _relative_error(theirs, duplicate) > tolerance:
                    raise ArithmeticError(
                        "the expected SciPy a_5(21) anomaly changed")
                continue
            if _relative_error(mine, theirs) > tolerance:
                raise ArithmeticError(
                    "SciPy comparison failed for a_%s(%s): %s vs %s"
                    % (n, q, mine, theirs))


def _check_small_q_expansions():
    q = QQ(1) / QQ(10)
    field = RealField(120)
    tolerance = field("1e-12")
    for n in range(7):
        mine = field(_center(_agreement_interval(q, n, DIGITS)))
        reference = field(_small_q_reference(n, q))
        if abs(mine - reference) > tolerance:
            raise ArithmeticError(
                "small-q expansion failed for a_%s(1/10): %s vs %s"
                % (n, mine, reference))


def run_integrity_checks():
    _check_q_zero()
    _check_interlacing()
    _check_scipy()
    _check_small_q_expansions()


class MathieuCharacteristicValuesA(numberdb.Generator):
    table = TABLE
    parameters = ("q", "n")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for q in Q_VALUES:
            for n in range(MAX_N + 1):
                yield {"q": str(q), "n": str(n)}

    def value(self, params, digits):
        q = QQ(params["q"])
        n = int(params["n"])
        if q not in Q_VALUES:
            raise ValueError("q=%s is outside this draft" % q)
        if n < 0 or n > MAX_N:
            raise ValueError("n=%s is outside this draft" % n)
        return _agreement_interval(q, n, digits)


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries

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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
    return answer


def main():
    configure_key_from_stdin()
    generator = MathieuCharacteristicValuesA()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if "--publish" in sys.argv or mode == "1":
        run_integrity_checks()
        print(fill_draft_once(
            generator,
            message="Mathieu characteristic values a_n(q)"))
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
