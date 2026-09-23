"""Markov quadratic irrationals -- numberdb.org/T430.

This generator fills T430 with the Markov quadratic irrational
((2k + m) + sqrt(9m^2 - 4))/(2m), one for each normalised Markov triple
(m1, m2, m) with m <= 10^12.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import heapq
import math
import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T430")
MAX_MARKOV = 10**12
DIGITS = 100
WORKING_GUARD = 64


OEIS_M1_FIRST_40 = (
    1, 1, 1, 1, 2, 1, 1, 2, 5, 1,
    5, 1, 2, 13, 1, 5, 1, 2, 5, 13,
    34, 1, 29, 1, 2, 29, 5, 13, 89, 1,
    5, 34, 2, 1, 13, 233, 169, 1, 5, 34,
)

OEIS_M2_FIRST_40 = (
    1, 1, 2, 5, 5, 13, 34, 29, 13, 89,
    29, 233, 169, 34, 610, 194, 1597, 985, 433, 194,
    89, 4181, 169, 10946, 5741, 433, 2897, 1325, 233, 28657,
    6466, 1325, 33461, 75025, 7561, 610, 985, 196418, 43261, 9077,
)

OEIS_M_FIRST_40 = (
    1, 2, 5, 13, 29, 34, 89, 169, 194, 233,
    433, 610, 985, 1325, 1597, 2897, 4181, 5741, 6466, 7561,
    9077, 10946, 14701, 28657, 33461, 37666, 43261, 51641, 62210, 75025,
    96557, 135137, 195025, 196418, 294685, 426389, 499393, 514229, 646018, 925765,
)

OEIS_K_FIRST_40 = (
    0, 1, 2, 5, 12, 13, 34, 70, 75, 89,
    179, 233, 408, 507, 610, 1120, 1597, 2378, 2673, 2923,
    3468, 4181, 6089, 10946, 13860, 15571, 16725, 19760, 23763, 28657,
    39916, 51709, 80782, 75025, 113922, 162867, 206855, 196418, 249755, 353702,
)

OEIS_PERIOD_FIRST_40 = (
    1, 1, 4, 6, 6, 8, 10, 8, 10, 12,
    10, 14, 10, 14, 16, 14, 18, 12, 14, 16,
    18, 20, 14, 22, 14, 16, 18, 20, 22, 24,
    18, 22, 16, 26, 22, 26, 18, 28, 22, 26,
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def normalise(triple):
    return tuple(sorted(int(v) for v in triple))


def markov_triples(bound=MAX_MARKOV):
    """Normalised Markov triples ordered by largest, middle, smallest member."""
    start = (1, 1, 1)
    seen = {start}
    heap = [(1, 1, 1, start)]

    while heap:
        _m, _m2, _m1, triple = heapq.heappop(heap)
        yield triple
        a, b, c = triple
        neighbours = (
            normalise((3 * b * c - a, b, c)),
            normalise((a, 3 * a * c - b, c)),
            normalise((a, b, 3 * a * b - c)),
        )
        for neighbour in neighbours:
            if neighbour in seen or neighbour[2] > bound:
                continue
            seen.add(neighbour)
            heapq.heappush(
                heap,
                (neighbour[2], neighbour[1], neighbour[0], neighbour),
            )


def markov_k(m1, m2, m):
    """Cassels's k in the closed range 0 <= k <= m/2."""
    if m == 1:
        return 0
    residue = (m1 * pow(m2, -1, m)) % m
    other = (-residue) % m
    k = min(residue, other)
    if not (2 * k <= m):
        raise ArithmeticError("k outside the selected range for %s" % ((m1, m2, m),))
    if (k * m2 - m1) % m != 0 and (k * m2 + m1) % m != 0:
        raise ArithmeticError("k does not satisfy Cassels congruence")
    return k


def l_value(k, m):
    numerator = k * k + 1
    if numerator % m != 0:
        raise ArithmeticError("l is not integral for k=%s, m=%s" % (k, m))
    return numerator // m


def floor_surd(p, q, discriminant):
    return (p + math.isqrt(discriminant)) // q


def purely_periodic_cf(m1, m2, m):
    """Return the regular continued-fraction period of xi as exact integers."""
    k = markov_k(m1, m2, m)
    discriminant = 9 * m * m - 4
    p = 2 * k + m
    q = 2 * m
    seen = {}
    period = []

    while (p, q) not in seen:
        seen[(p, q)] = len(period)
        partial = floor_surd(p, q, discriminant)
        period.append(partial)
        remainder = p - partial * q
        denominator = discriminant - remainder * remainder
        if denominator % q != 0:
            raise ArithmeticError("continued-fraction denominator is not integral")
        p = -remainder
        q = denominator // q
        if q <= 0:
            raise ArithmeticError("continued-fraction state left the positive branch")

    if seen[(p, q)] != 0:
        raise ArithmeticError("continued fraction is not purely periodic")
    return tuple(period)


def xi_ball(m1, m2, m, digits):
    k = markov_k(m1, m2, m)
    discriminant = 9 * m * m - 4
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    return (field(2 * k + m) + field(discriminant).sqrt()) / field(2 * m)


def _markov_equation_holds(triple):
    m1, m2, m = triple
    return m1 * m1 + m2 * m2 + m * m == 3 * m1 * m2 * m


def _exact_real(value):
    parent = getattr(value, "parent", None)
    if parent is None or not callable(parent):
        return isinstance(value, int)
    try:
        return parent() in (ZZ, QQ)
    except Exception:  # noqa: BLE001
        return False


class MarkovQuadraticIrrationals(numberdb.Generator):
    """Generator for T430, Markov quadratic irrationals."""

    table = TABLE
    parameters = ("m1", "m2", "m")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, bound=MAX_MARKOV):
        for m1, m2, m in markov_triples(bound):
            yield {"m1": str(m1), "m2": str(m2), "m": str(m)}

    def value(self, params, digits):
        m1 = int(params["m1"])
        m2 = int(params["m2"])
        m = int(params["m"])
        entry = {"number": xi_ball(m1, m2, m, digits)}
        if (m1, m2, m) == (1, 1, 1):
            entry["equals"] = "HREF{Golden_ratio#phi}"
            entry["comment"] = "This entry is HREF{Golden_ratio#phi}[the golden ratio $\\varphi$]."
        elif (m1, m2, m) == (1, 1, 2):
            entry["equals"] = "HREF{Algebraic_numbers_of_degree_2#1,-2,-1,2}"
            entry["comment"] = "This entry is $1+\\sqrt2$."
        return entry


def run_integrity_checks(generator=None):
    generator = generator or MarkovQuadraticIrrationals()
    triples = [
        (int(row["m1"]), int(row["m2"]), int(row["m"]))
        for row in generator.enumerate()
    ]
    if len(triples) != 152:
        raise ArithmeticError("expected 152 triples, found %d" % len(triples))
    if triples[-1][2] != 982145940029:
        raise ArithmeticError("unexpected largest stored Markov number %s" % (triples[-1][2],))

    source_triples = tuple(zip(OEIS_M1_FIRST_40, OEIS_M2_FIRST_40, OEIS_M_FIRST_40))
    if tuple(triples[:40]) != source_triples:
        raise ArithmeticError("first 40 triples do not match OEIS")

    for index, triple in enumerate(triples):
        if not _markov_equation_holds(triple):
            raise ArithmeticError("not a Markov triple: %s" % (triple,))
        m1, m2, m = triple
        k = markov_k(m1, m2, m)
        l = l_value(k, m)
        if index < len(OEIS_K_FIRST_40) and k != OEIS_K_FIRST_40[index]:
            raise ArithmeticError("k for %s is %s, OEIS gives %s" % (
                triple,
                k,
                OEIS_K_FIRST_40[index],
            ))

        a = m
        b = -(2 * k + m)
        c = l + k - 2 * m
        if b * b - 4 * a * c != 9 * m * m - 4:
            raise ArithmeticError("wrong discriminant for %s" % (triple,))

        period = purely_periodic_cf(m1, m2, m)
        if any(partial not in (1, 2) for partial in period):
            raise ArithmeticError("partial quotient outside {1, 2} for %s" % (triple,))
        if index < len(OEIS_PERIOD_FIRST_40) and len(period) != OEIS_PERIOD_FIRST_40[index]:
            raise ArithmeticError("period length for %s is %s, OEIS gives %s" % (
                triple,
                len(period),
                OEIS_PERIOD_FIRST_40[index],
            ))


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

        _check_rigour(
            generator,
            table,
            identity,
            value,
            bounded=True if _exact_real(value) else None,
        )
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
    generator = MarkovQuadraticIrrationals()
    run_integrity_checks(generator)
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Markov quadratic irrationals from exact triples",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
