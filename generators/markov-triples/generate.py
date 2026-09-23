"""Markov triples -- numberdb.org/T435.

This generator fills T435 with the three components of every normalised
Markov triple (m1, m2, m3) with m3 <= 10^12, in the order used by the other
tables in this Markov-spectrum family.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import heapq
import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = os.environ.get("NUMBERDB_TABLE", "T435")
MAX_MARKOV = 10**12


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

OEIS_M3_FIRST_40 = (
    1, 2, 5, 13, 29, 34, 89, 169, 194, 233,
    433, 610, 985, 1325, 1597, 2897, 4181, 5741, 6466, 7561,
    9077, 10946, 14701, 28657, 33461, 37666, 43261, 51641, 62210, 75025,
    96557, 135137, 195025, 196418, 294685, 426389, 499393, 514229, 646018, 925765,
)

OEIS_A291694_FIRST_23 = (
    (1, 1, 1),
    (1, 1, 2),
    (1, 2, 5),
    (1, 5, 13),
    (2, 5, 29),
    (1, 13, 34),
    (1, 34, 89),
    (2, 29, 169),
    (5, 13, 194),
    (1, 89, 233),
    (5, 29, 433),
    (1, 233, 610),
    (2, 169, 985),
    (13, 34, 1325),
    (1, 610, 1597),
    (5, 194, 2897),
    (1, 1597, 4181),
    (2, 985, 5741),
    (5, 433, 6466),
    (13, 194, 7561),
    (34, 89, 9077),
    (1, 4181, 10946),
    (29, 169, 14701),
)

PARTS = ("m1", "m2", "m3")
_CHECKED = False


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def normalise(triple):
    return tuple(sorted(int(value) for value in triple))


def markov_triples(bound=MAX_MARKOV):
    """Normalised Markov triples ordered by m3, then m2, then m1."""
    start = (1, 1, 1)
    seen = {start}
    heap = [(1, 1, 1, start)]

    while heap:
        _m3, _m2, _m1, triple = heapq.heappop(heap)
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


def markov_equation_holds(triple):
    m1, m2, m3 = triple
    return m1 * m1 + m2 * m2 + m3 * m3 == 3 * m1 * m2 * m3


def run_integrity_checks():
    global _CHECKED
    if _CHECKED:
        return

    triples = tuple(markov_triples())
    if len(triples) != 152:
        raise ArithmeticError("expected 152 triples, found %d" % len(triples))
    if triples[-1][2] != 982145940029:
        raise ArithmeticError(
            "unexpected largest stored Markov number %s" % (triples[-1][2],)
        )
    if tuple(triples[:40]) != tuple(zip(
            OEIS_M1_FIRST_40, OEIS_M2_FIRST_40, OEIS_M3_FIRST_40)):
        raise ArithmeticError("first 40 triples do not match the OEIS fixtures")
    if triples[:len(OEIS_A291694_FIRST_23)] != OEIS_A291694_FIRST_23:
        raise ArithmeticError("first triples do not match OEIS A291694")

    if list(triples) != sorted(triples, key=lambda row: (row[2], row[1], row[0])):
        raise ArithmeticError("triples are not ordered by m3, then m2, then m1")
    for triple in triples:
        if not (triple[0] <= triple[1] <= triple[2]):
            raise ArithmeticError("not normalised: %s" % (triple,))
        if not markov_equation_holds(triple):
            raise ArithmeticError("not a Markov triple: %s" % (triple,))

    _CHECKED = True


class MarkovTriples(numberdb.Generator):
    """Generator for T435, Markov triples."""

    table = TABLE
    parameters = ("m1", "m2", "m3", "part")
    type = "Z"
    rigour = "exact"

    def enumerate(self, bound=MAX_MARKOV):
        run_integrity_checks()
        for m1, m2, m3 in markov_triples(bound):
            for part in PARTS:
                yield {
                    "m1": str(m1),
                    "m2": str(m2),
                    "m3": str(m3),
                    "part": part,
                }

    def value(self, params, digits):
        run_integrity_checks()
        part = params["part"]
        if part not in PARTS:
            raise ValueError("unknown Markov-triple part %s" % part)
        return ZZ(params[part])


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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = MarkovTriples()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="exact Markov triples checked against OEIS fixtures",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
