"""Macdonald-Kostka polynomials -- numberdb.org/T260.

    \\tilde H_mu(x;q,t) = sum_lambda \\tilde K_{lambda,mu}(q,t) s_lambda

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores the nontrivial Schur coefficients for 2 <= |lambda| = |mu|
<= 8. The single-row and single-column Schur coefficients are closed-form
monomials and are left to the table formulas.
"""

import itertools
import math
import os
import sys
from collections import Counter, defaultdict
from functools import lru_cache

import numberdb.sage as numberdb

# Sage's qt_kostka reaches Symmetrica, whose lazy import of symbolic functions
# can segfault in the named-import environment unless these modules are ready.
import sage.symbolic.ring      # noqa: F401,E402
import sage.symbolic.function  # noqa: F401,E402
import sage.functions.trig     # noqa: F401,E402

from sage.combinat.partition import Partition  # noqa: E402
from sage.combinat.sf.kfpoly import KostkaFoulkesPolynomial  # noqa: E402
from sage.combinat.sf.macdonald import qt_kostka  # noqa: E402
from sage.rings.integer_ring import ZZ  # noqa: E402
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing  # noqa: E402


TABLE = os.environ.get("NUMBERDB_TABLE", "T260")

#: Measured before filling the draft: up to size 8 gives 787 entries, the
#: longest value is 403 characters, and the entries block is 144.6 KB. Size 9
#: would add 840 entries, past the soft entry limit of 1200.
MAX_SIZE = 8
HHL_CHECK_SIZE = 6

POLY = PolynomialRing(ZZ, ("q", "t"))
Q, T = POLY.gens()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _partitions(total, largest=None):
    """Partitions of total, largest part first."""
    if largest is None:
        largest = total
    if total == 0:
        yield []
        return
    for part in range(min(total, largest), 0, -1):
        for rest in _partitions(total - part, part):
            yield [part] + rest


def _format_partition(partition):
    return ",".join(str(part) for part in partition)


def _parse_partition(text):
    return [int(part) for part in str(text).split(",") if part]


def _is_edge_row(lam):
    return len(lam) == 1 or all(part == 1 for part in lam)


def _n_stat(partition):
    return sum(index * part for index, part in enumerate(partition))


def _conjugate(partition):
    if not partition:
        return []
    return [
        sum(1 for part in partition if part > column)
        for column in range(max(partition))
    ]


@lru_cache(maxsize=None)
def _modified_kostka(lam_tuple, mu_tuple):
    """Return the modified Macdonald-Kostka coefficient exactly."""
    k = qt_kostka(list(lam_tuple), list(mu_tuple))
    _q, t = k.parent().gens()
    value = k.subs({t: 1 / t}) * (t ** _n_stat(mu_tuple))
    return POLY(value)


class MacdonaldKostkaPolynomials(numberdb.Generator):

    table = TABLE
    parameters = ("lambda", "mu")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, max_size=MAX_SIZE):
        for size in range(2, max_size + 1):
            parts = list(_partitions(size))
            for lam in parts:
                if _is_edge_row(lam):
                    continue
                for mu in parts:
                    yield {
                        "lambda": _format_partition(lam),
                        "mu": _format_partition(mu),
                    }

    def value(self, params, digits):
        lam = tuple(_parse_partition(params["lambda"]))
        mu = tuple(_parse_partition(params["mu"]))
        return _modified_kostka(lam, mu)


def _cells(partition):
    return [
        (row, column)
        for row, width in enumerate(partition)
        for column in range(width)
    ]


def _arm(partition, cell):
    row, column = cell
    return partition[row] - column - 1


def _leg(partition, cell):
    row, column = cell
    return sum(1 for other in range(row + 1, len(partition))
               if column < partition[other])


@lru_cache(maxsize=None)
def _attacking_pairs(partition):
    cells = _cells(partition)
    reading = {cell: index for index, cell in enumerate(
        sorted(cells, key=lambda cell: (-cell[0], cell[1])))}
    pairs = []
    for left, right in itertools.combinations(cells, 2):
        attacks = False
        if left[0] == right[0]:
            attacks = True
        elif abs(left[0] - right[0]) == 1:
            upper = left if left[0] > right[0] else right
            lower = right if upper == left else left
            attacks = lower[1] < upper[1]
        if attacks:
            first, second = sorted((left, right), key=lambda cell: reading[cell])
            pairs.append((first, second))
    return tuple(pairs)


def _hhl_weight(partition, filling):
    descents = []
    for cell in _cells(partition):
        row, column = cell
        if row == 0:
            continue
        below = (row - 1, column)
        if column < partition[row - 1] and filling[cell] > filling[below]:
            descents.append(cell)

    inversion_count = sum(
        1 for first, second in _attacking_pairs(tuple(partition))
        if filling[first] > filling[second])
    maj = sum(_leg(partition, cell) + 1 for cell in descents)
    inv = inversion_count - sum(_arm(partition, cell) for cell in descents)
    if inv < 0:
        raise AssertionError("%s: negative HHL inversion statistic" %
                             (partition,))
    return inv, maj


def _orbit_size(exponents, variables):
    padded = list(exponents) + [0] * (variables - len(exponents))
    out = math.factorial(variables)
    for multiplicity in Counter(padded).values():
        out //= math.factorial(multiplicity)
    return out


def _divide_poly_by_integer(poly, divisor):
    out = POLY.zero()
    for exponents, coefficient in poly.dict().items():
        if coefficient % divisor != 0:
            raise AssertionError(
                "%s is not divisible by orbit size %d" % (poly, divisor))
        out += ZZ(coefficient // divisor) * (Q ** exponents[0]) * (T ** exponents[1])
    return out


@lru_cache(maxsize=None)
def _hhl_monomial_coefficients(mu_tuple):
    """Monomial-basis coefficients of HHL's formula for Htilde_mu."""
    cells = _cells(mu_tuple)
    variables = sum(mu_tuple)
    totals = defaultdict(lambda: defaultdict(ZZ))

    for values in itertools.product(range(1, variables + 1), repeat=variables):
        filling = dict(zip(cells, values))
        inv, maj = _hhl_weight(mu_tuple, filling)
        counts = [0] * variables
        for value in values:
            counts[value - 1] += 1
        exponent_partition = tuple(
            count for count in sorted(counts, reverse=True) if count)
        totals[exponent_partition][(inv, maj)] += ZZ(1)

    coefficients = {}
    for exponent_partition, terms in totals.items():
        poly = POLY.zero()
        for (q_power, t_power), count in terms.items():
            poly += count * (Q ** q_power) * (T ** t_power)
        coefficients[exponent_partition] = _divide_poly_by_integer(
            poly, _orbit_size(exponent_partition, variables))
    return coefficients


@lru_cache(maxsize=None)
def _kostka_number(lam_tuple, weight_tuple):
    """Count semistandard tableaux of shape lam and weight weight."""
    cells = _cells(lam_tuple)
    values = []
    for index, multiplicity in enumerate(weight_tuple, start=1):
        values.extend([index] * multiplicity)

    total = 0
    for assignment in set(itertools.permutations(values)):
        filling = dict(zip(cells, assignment))
        ok = True
        for row, width in enumerate(lam_tuple):
            for column in range(width - 1):
                if filling[(row, column)] > filling[(row, column + 1)]:
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            continue
        for row in range(len(lam_tuple) - 1):
            for column in range(lam_tuple[row + 1]):
                if filling[(row, column)] >= filling[(row + 1, column)]:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            total += 1
    return total


@lru_cache(maxsize=None)
def _hhl_schur_coefficients(mu_tuple):
    """Schur coefficients from HHL's filling formula, without Sage SF code."""
    size = sum(mu_tuple)
    parts = [tuple(part) for part in _partitions(size)]
    monomial = _hhl_monomial_coefficients(mu_tuple)
    coefficients = {}
    for nu in parts:
        value = monomial.get(nu, POLY.zero())
        for lam, coefficient in coefficients.items():
            k = _kostka_number(lam, nu)
            if k:
                value -= coefficient * k
        coefficients[nu] = value
    return coefficients


def _hook_standard_tableaux_count(lam):
    denominator = ZZ(1)
    for cell in _cells(lam):
        denominator *= ZZ(_arm(lam, cell) + _leg(lam, cell) + 1)
    return ZZ(math.factorial(sum(lam))) // denominator


def _kostka_foulkes_q_zero(lam, mu):
    kf = KostkaFoulkesPolynomial(list(lam), list(mu))
    n_mu = _n_stat(mu)
    out = POLY.zero()
    if not hasattr(kf, "dict"):
        return POLY(ZZ(kf) * (T ** n_mu))
    for exponent, coefficient in kf.dict().items():
        degree = exponent[0] if isinstance(exponent, tuple) else exponent
        power = n_mu - degree
        if power < 0:
            raise AssertionError("%s, %s: negative q=0 exponent" % (lam, mu))
        out += ZZ(coefficient) * (T ** power)
    return out


def _elementary_of_cell_weights(mu, degree):
    weights = []
    removed_one = False
    for row, width in enumerate(mu):
        for column in range(width):
            weight = (Q ** column) * (T ** row)
            if not removed_one and row == 0 and column == 0:
                removed_one = True
                continue
            weights.append(weight)

    coeffs = [POLY.one()] + [POLY.zero()] * degree
    for weight in weights:
        for index in range(degree, 0, -1):
            coeffs[index] += coeffs[index - 1] * weight
    return coeffs[degree]


def _is_hook(lam):
    return len(lam) >= 2 and all(part == 1 for part in lam[1:])


def _swap_qt(poly):
    return POLY(poly.subs({Q: T, T: Q}))


def _edge_value(lam, mu):
    size = sum(mu)
    if lam == (size,):
        return POLY.one()
    if lam == (1,) * size:
        return (Q ** _n_stat(tuple(_conjugate(mu)))) * (T ** _n_stat(mu))
    raise ValueError("not an edge row: %r" % (lam,))


def run_integrity_checks():
    generator = MacdonaldKostkaPolynomials()
    rows = list(generator.enumerate())
    if len(rows) != 787:
        raise AssertionError("expected 787 rows, got %d" % (len(rows),))

    for params in rows:
        lam = tuple(_parse_partition(params["lambda"]))
        mu = tuple(_parse_partition(params["mu"]))
        value = _modified_kostka(lam, mu)

        if value.subs({Q: ZZ(1), T: ZZ(1)}) != _hook_standard_tableaux_count(lam):
            raise AssertionError("%s,%s: value at q=t=1 is wrong" % (lam, mu))

        if POLY(value.subs({Q: ZZ(0)})) != _kostka_foulkes_q_zero(lam, mu):
            raise AssertionError("%s,%s: q=0 specialization is wrong" % (lam, mu))

        if _is_hook(lam):
            degree = sum(lam[1:])
            expected = _elementary_of_cell_weights(mu, degree)
            if value != expected:
                raise AssertionError("%s,%s: hook formula is wrong" % (lam, mu))

        conjugate_mu = tuple(_conjugate(mu))
        if len(conjugate_mu) and sum(conjugate_mu) <= MAX_SIZE:
            dual = _modified_kostka(lam, conjugate_mu)
            if dual != _swap_qt(value):
                raise AssertionError("%s,%s: q,t duality is wrong" % (lam, mu))

    for size in range(2, MAX_SIZE + 1):
        for mu in (tuple(part) for part in _partitions(size)):
            for lam in ((size,), (1,) * size):
                if _modified_kostka(lam, mu) != _edge_value(lam, mu):
                    raise AssertionError("%s,%s: edge formula is wrong" %
                                         (lam, mu))

    hhl_checked = 0
    for size in range(1, HHL_CHECK_SIZE + 1):
        for mu in (tuple(part) for part in _partitions(size)):
            hhl = _hhl_schur_coefficients(mu)
            for lam in (tuple(part) for part in _partitions(size)):
                if _modified_kostka(lam, mu) != hhl[lam]:
                    raise AssertionError(
                        "%s,%s: HHL filling formula gives %s, generator gives %s"
                        % (lam, mu, hhl[lam], _modified_kostka(lam, mu)))
                hhl_checked += 1

    print("integrity checks passed for %d stored rows and %d HHL coefficients"
          % (len(rows), hhl_checked))


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

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = MacdonaldKostkaPolynomials()
    if os.environ.get("NUMBERDB_CHECK_ONLY") == "1":
        run_integrity_checks()
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        run_integrity_checks()
        print(fill_draft_once(
            generator,
            message="modified Macdonald-Kostka polynomials for |lambda| <= %d"
                    % (MAX_SIZE,)))
    else:
        run_integrity_checks()
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
