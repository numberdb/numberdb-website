"""Zeros of the Charlier polynomials C_n(x;a) -- numberdb.org/T368.

This generator fills the table of zeros of the DLMF-normalised Charlier
polynomials

    C_n(x; a) = sum_{j=0}^n binomial(n, j) (-1/a)^j x(x-1)...(x-j+1).

The table inherits the Poisson-mean grid from the Charlier polynomial table
T267 and cuts only the degree range, since storing every zero through the
parent table's n <= 20 range is larger than the table-build target.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import json
import os
import sys
import urllib.request
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache

import numberdb.sage as numberdb
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = os.environ.get("NUMBERDB_TABLE", "T368")

# The a-values are the grid inherited from T267. Measured before filling the
# draft: n <= 11 gives 660 entries. The dry-run measurement reports a longest
# raw interval string of 263 characters and a 138.4 KB entries block; n <= 12
# crosses the 160 KB build target.
A_VALUES = (
    QQ(1) / QQ(4),
    QQ(1) / QQ(3),
    QQ(1) / QQ(2),
    QQ(2) / QQ(3),
    QQ(1),
    QQ(3) / QQ(2),
    QQ(2),
    QQ(5) / QQ(2),
    QQ(3),
    QQ(4),
)
MAX_N = 11
DIGITS = 100
WORKING_GUARD = 96

R = PolynomialRing(QQ, "x")
x = R.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def charlier_polynomial(n, a):
    """The DLMF-normalised Charlier polynomial C_n(x; a)."""
    n = int(n)
    a = QQ(a)
    current = R.one()
    if n == 0:
        return current
    previous, current = current, R.one() - x / a
    for degree in range(1, n):
        previous, current = (
            current,
            ((QQ(degree) + a - x) * current - QQ(degree) * previous) / a,
        )
    return R(current)


def _contains_exact(interval, exact):
    try:
        return interval.lower() <= exact <= interval.upper()
    except TypeError:
        field = interval.parent()
        return (interval - field(exact)).contains_zero()


def _as_order_key(root):
    if hasattr(root, "lower"):
        return root.lower()
    return QQ(root)


@lru_cache(maxsize=None)
def _roots(a_text, n, digits):
    """The roots of C_n(x; a), exact where rational and otherwise intervals."""
    a = QQ(a_text)
    n = int(n)
    if n == 1:
        return (a,)

    polynomial = charlier_polynomial(n, a)
    field = RealIntervalField(numberdb.bits(digits, losing=WORKING_GUARD))
    intervals = sorted(
        polynomial.roots(field, multiplicities=False),
        key=_as_order_key,
    )
    if len(intervals) != n:
        raise ArithmeticError("got %d roots for a=%s, n=%d" % (len(intervals), a, n))

    exact_roots = sorted(polynomial.roots(QQ, multiplicities=False))
    roots = []
    for interval in intervals:
        exact = None
        for candidate in exact_roots:
            if _contains_exact(interval, candidate):
                exact = candidate
                break
        if exact is None:
            roots.append(interval)
        else:
            roots.append(exact)
            exact_roots.remove(exact)
    return tuple(roots)


class CharlierPolynomialZeros(numberdb.Generator):
    """Generator for T368, the zeros of the Charlier polynomials."""

    table = TABLE
    parameters = ("a", "n", "k")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_n=MAX_N):
        for a in A_VALUES:
            for n in range(1, max_n + 1):
                for k in range(1, n + 1):
                    yield {"a": str(a), "n": str(n), "k": str(k)}

    def value(self, params, digits):
        roots = _roots(params["a"], int(params["n"]), int(digits))
        return roots[int(params["k"]) - 1]


def _computed_values():
    return {
        (a, n, k): _roots(str(a), n, DIGITS)[k - 1]
        for a in A_VALUES
        for n in range(1, MAX_N + 1)
        for k in range(1, n + 1)
    }


def _root_lists(values):
    return {
        (a, n): [values[(a, n, k)] for k in range(1, n + 1)]
        for a in A_VALUES
        for n in range(1, MAX_N + 1)
    }


def _as_interval(value, field):
    return field(value)


def _interval_ordered(left, right):
    return left.upper() < right.lower()


def _check_parent_table():
    parent = numberdb.table("T267")
    numbers = parent.get("Numbers", {})
    for a in A_VALUES:
        by_degree = numbers.get(str(a))
        if not isinstance(by_degree, dict):
            raise ArithmeticError("T267 has no group for a=%s" % a)
        for n in range(0, MAX_N + 1):
            text = by_degree.get(str(n))
            if text is None:
                raise ArithmeticError("T267 has no polynomial for a=%s, n=%d" % (a, n))
            if R(text) != charlier_polynomial(n, a):
                raise ArithmeticError("parent polynomial disagrees at a=%s, n=%d" % (a, n))


def _check_root_order(values):
    field = RealIntervalField(numberdb.bits(DIGITS, losing=WORKING_GUARD))
    for (a, n), roots in _root_lists(values).items():
        intervals = [_as_interval(root, field) for root in roots]
        for left, right in zip(intervals, intervals[1:]):
            if not _interval_ordered(left, right):
                raise ArithmeticError("roots overlap or are unordered at a=%s, n=%d" % (a, n))


def _decimal_parts(text):
    text = str(text)
    lower = text.lower()
    if "e" in lower:
        mantissa, exponent_text = lower.split("e", 1)
        exponent = int(exponent_text)
    else:
        mantissa, exponent = lower, 0
    decimals = len(mantissa.split(".", 1)[1]) if "." in mantissa else 0
    quantum = Decimal(1).scaleb(exponent - decimals)
    centre = Decimal(text)
    lo, hi = centre - quantum, centre + quantum
    if lo > hi:
        lo, hi = hi, lo
    return Fraction(lo), Fraction(hi)


def _fraction_to_qq(value):
    return QQ(value.numerator) / QQ(value.denominator)


def _written_interval(value):
    from numberdb._write import to_text

    if getattr(value.parent(), "is_exact", lambda: False)():
        exact = QQ(value)
        return exact, exact
    text = to_text(value, DIGITS)
    if "/" in text and "." not in text and "e" not in text:
        exact = QQ(text)
        return exact, exact
    lo, hi = _decimal_parts(text)
    return _fraction_to_qq(lo), _fraction_to_qq(hi)


def _check_written_brackets(values):
    for (a, n, k), root in values.items():
        low, high = _written_interval(root)
        if low == high:
            if charlier_polynomial(n, a)(low) != 0:
                raise ArithmeticError("exact root is not a root at a=%s, n=%d, k=%d" % (a, n, k))
            continue
        left = charlier_polynomial(n, a)(low)
        right = charlier_polynomial(n, a)(high)
        if left * right >= 0:
            raise ArithmeticError("written interval does not bracket at a=%s, n=%d, k=%d" % (a, n, k))


def _check_vieta(values):
    field = RealIntervalField(numberdb.bits(DIGITS, losing=WORKING_GUARD))
    for (a, n), roots in _root_lists(values).items():
        polynomial = charlier_polynomial(n, a)
        lead = polynomial.monomial_coefficient(x ** n)
        elementary = [field(1)] + [field(0) for _ in range(n)]
        for root in roots:
            interval = _as_interval(root, field)
            for index in range(n, 0, -1):
                elementary[index] += elementary[index - 1] * interval
        for order in range(1, n + 1):
            expected = (
                QQ((-1) ** order)
                * polynomial.monomial_coefficient(x ** (n - order))
                / lead
            )
            if not (elementary[order] - field(expected)).contains_zero():
                raise ArithmeticError(
                    "Vieta relation failed at a=%s, n=%d, order=%d"
                    % (a, n, order)
                )


def _check_interlacing(values):
    field = RealIntervalField(numberdb.bits(DIGITS, losing=WORKING_GUARD))
    lists = _root_lists(values)
    for a in A_VALUES:
        for n in range(2, MAX_N + 1):
            lower_degree = [_as_interval(root, field) for root in lists[(a, n - 1)]]
            higher_degree = [_as_interval(root, field) for root in lists[(a, n)]]
            for index, middle in enumerate(lower_degree):
                if not (
                    _interval_ordered(higher_degree[index], middle)
                    and _interval_ordered(middle, higher_degree[index + 1])
                ):
                    raise ArithmeticError(
                        "interlacing failed at a=%s, n=%d, index=%d"
                        % (a, n, index + 1)
                    )


def run_integrity_checks(values=None):
    if values is None:
        values = _computed_values()
    _check_parent_table()
    _check_root_order(values)
    _check_written_brackets(values)
    _check_vieta(values)
    _check_interlacing(values)


def _flatten_numbers(tree):
    out = {}
    for a_text, by_n in tree.get("Numbers", {}).items():
        for n_text, by_k in by_n.items():
            for k_text, number in by_k.items():
                out[(QQ(a_text), int(n_text), int(k_text))] = number
    return out


def stored_values():
    """Read the table from the API and return its stored number strings."""
    key = os.environ.get("NUMBERDB_API_KEY")
    if not key:
        raise RuntimeError("NUMBERDB_API_KEY is not set")
    request = urllib.request.Request(
        "https://numberdb.org/api/table?id=%s" % TABLE,
        headers={"Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        tree = json.load(response)
    if "error" in tree:
        raise RuntimeError(tree["error"])
    return _flatten_numbers(tree)


def _stored_to_values(stored):
    values = {}
    field = RealIntervalField(numberdb.bits(DIGITS, losing=WORKING_GUARD))
    for key, text in stored.items():
        if "/" in text and "." not in text and "e" not in text:
            values[key] = QQ(text)
        else:
            low, high = _decimal_parts(text)
            values[key] = field(_fraction_to_qq(low), _fraction_to_qq(high))
    return values


def check_stored_values():
    stored = stored_values()
    expected = set(_computed_values())
    if set(stored) != expected:
        missing = sorted(expected - set(stored))[:5]
        extra = sorted(set(stored) - expected)[:5]
        raise ArithmeticError("stored key set disagrees, missing=%s extra=%s" % (missing, extra))
    run_integrity_checks(_stored_to_values(stored))


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
    generator = CharlierPolynomialZeros()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="proven zeros of the Charlier polynomials"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        check_stored_values()
        print("stored identity checks passed")
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
