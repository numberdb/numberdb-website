"""Dimensions of the irreducible representations of the exceptional simple Lie algebras -- numberdb.org/T256

This draft stores exact dimensions of irreducible highest-weight
representations of the complex exceptional simple Lie algebras G2, F4, E6, E7
and E8. Highest weights are written as Bourbaki Dynkin labels, using Sage's
root-system node order. The zero weight, whose representation is trivial, is
omitted.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed from Weyl's dimension formula using exact rational
arithmetic. The range is every nontrivial representation whose dimension is at
most the bound set for its algebra:

    G2: 10^6, F4: 10^7, E6: 10^7, E7: 10^8, E8: 10^12.

The generator checks the range by a second enumeration by total label sum,
checks familiar fundamental dimensions, and compares the set of distinct
dimensions for each algebra with the corresponding OEIS b-file through the
same bound.
"""

import os
import sys
import urllib.request
from functools import lru_cache

import numberdb.sage as numberdb
from sage.combinat.root_system.root_system import RootSystem
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


TABLE = "T256"

ALGEBRAS = ("G2", "F4", "E6", "E7", "E8")

BOUNDS = {
    "G2": ZZ(10) ** 6,
    "F4": ZZ(10) ** 7,
    "E6": ZZ(10) ** 7,
    "E7": ZZ(10) ** 8,
    "E8": ZZ(10) ** 12,
}

EXPECTED_ROWS = {
    "G2": 232,
    "F4": 73,
    "E6": 166,
    "E7": 67,
    "E8": 61,
}

OEIS_BFILES = {
    "G2": "https://oeis.org/A104599/b104599.txt",
    "F4": "https://oeis.org/A121738/b121738.txt",
    "E6": "https://oeis.org/A121737/b121737.txt",
    "E7": "https://oeis.org/A121736/b121736.txt",
    "E8": "https://oeis.org/A121732/b121732.txt",
}

FUNDAMENTAL_DIMENSIONS = {
    "G2": {
        (1, 0): 7,
        (0, 1): 14,
    },
    "F4": {
        (1, 0, 0, 0): 52,
        (0, 1, 0, 0): 1274,
        (0, 0, 1, 0): 273,
        (0, 0, 0, 1): 26,
    },
    "E6": {
        (1, 0, 0, 0, 0, 0): 27,
        (0, 1, 0, 0, 0, 0): 78,
        (0, 0, 1, 0, 0, 0): 351,
        (0, 0, 0, 1, 0, 0): 2925,
        (0, 0, 0, 0, 1, 0): 351,
        (0, 0, 0, 0, 0, 1): 27,
    },
    "E7": {
        (1, 0, 0, 0, 0, 0, 0): 133,
        (0, 1, 0, 0, 0, 0, 0): 912,
        (0, 0, 1, 0, 0, 0, 0): 8645,
        (0, 0, 0, 1, 0, 0, 0): 365750,
        (0, 0, 0, 0, 1, 0, 0): 27664,
        (0, 0, 0, 0, 0, 1, 0): 1539,
        (0, 0, 0, 0, 0, 0, 1): 56,
    },
    "E8": {
        (1, 0, 0, 0, 0, 0, 0, 0): 3875,
        (0, 1, 0, 0, 0, 0, 0, 0): 147250,
        (0, 0, 1, 0, 0, 0, 0, 0): 6696000,
        (0, 0, 0, 1, 0, 0, 0, 0): 6899079264,
        (0, 0, 0, 0, 1, 0, 0, 0): 146325270,
        (0, 0, 0, 0, 0, 1, 0, 0): 2450240,
        (0, 0, 0, 0, 0, 0, 1, 0): 30380,
        (0, 0, 0, 0, 0, 0, 0, 1): 248,
    },
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def weight_text(labels):
    return "(" + ",".join(str(int(label)) for label in labels) + ")"


def parse_weight(text):
    text = str(text).strip()
    if not (text.startswith("(") and text.endswith(")")):
        raise ValueError("weight %r is not written as a tuple" % (text,))
    body = text[1:-1]
    if not body:
        return ()
    return tuple(int(part) for part in body.split(","))


@lru_cache(maxsize=None)
def root_data(algebra):
    ambient = RootSystem(algebra).ambient_space()
    index_set = tuple(ambient.index_set())
    weights = tuple(ambient.fundamental_weights()[i] for i in index_set)
    rho = ambient.rho()
    coroots = []
    for alpha in ambient.positive_roots():
        coroot = alpha.associated_coroot()
        denominator = QQ(rho.scalar(coroot))
        if denominator == 0:
            raise ValueError("zero Weyl denominator for %s" % (algebra,))
        coroots.append((coroot, denominator))
    return ambient, index_set, weights, rho, tuple(coroots)


def rank(algebra):
    return len(root_data(algebra)[1])


@lru_cache(maxsize=None)
def dimension(algebra, labels):
    labels = tuple(int(label) for label in labels)
    ambient, index_set, weights, rho, coroots = root_data(algebra)
    if len(labels) != len(index_set):
        raise ValueError("%s has rank %d, not %d" % (
            algebra, len(index_set), len(labels)))
    if any(label < 0 for label in labels):
        raise ValueError("Dynkin labels must be nonnegative: %r" % (labels,))

    highest_weight = ambient.zero()
    for label, fundamental_weight in zip(labels, weights):
        highest_weight += QQ(label) * fundamental_weight

    value = QQ(1)
    shifted = highest_weight + rho
    for coroot, denominator in coroots:
        value *= QQ(shifted.scalar(coroot)) / denominator

    if value.denominator() != 1:
        raise ArithmeticError("%s %s gave nonintegral dimension %s" % (
            algebra, labels, value))
    return ZZ(value.numerator())


def _enumerate_by_prefix(algebra):
    bound = BOUNDS[algebra]
    algebra_rank = rank(algebra)
    found = []

    def descend(prefix):
        if len(prefix) == algebra_rank:
            if any(prefix):
                value = dimension(algebra, tuple(prefix))
                if value <= bound:
                    found.append((value, tuple(prefix)))
            return

        remaining = algebra_rank - len(prefix) - 1
        label = 0
        while True:
            candidate = tuple(prefix + [label] + [0] * remaining)
            if any(candidate) and dimension(algebra, candidate) > bound:
                break
            descend(prefix + [label])
            label += 1

    descend([])
    return tuple(sorted(found, key=lambda item: (item[0], sum(item[1]), item[1])))


@lru_cache(maxsize=None)
def rows_for(algebra):
    return _enumerate_by_prefix(algebra)


def _compositions(total, length):
    if length == 1:
        yield (total,)
        return
    for head in range(total + 1):
        for tail in _compositions(total - head, length - 1):
            yield (head,) + tail


def _enumerate_by_total_weight(algebra):
    bound = BOUNDS[algebra]
    algebra_rank = rank(algebra)
    found = []
    total = 1
    while True:
        at_total = []
        for labels in _compositions(total, algebra_rank):
            value = dimension(algebra, labels)
            at_total.append(value)
            if value <= bound:
                found.append((value, labels))
        if min(at_total) > bound:
            break
        total += 1
    return tuple(sorted(found, key=lambda item: (item[0], sum(item[1]), item[1])))


def _download_text(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "numberdb-exceptional-lie-dimensions"})
    with urllib.request.urlopen(request, timeout=120) as answer:
        return answer.read().decode("utf8", "replace")


def _oeis_dimensions(algebra):
    values = []
    for line in _download_text(OEIS_BFILES[algebra]).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        values.append(ZZ(parts[1]))
    if not values:
        raise ValueError("OEIS b-file for %s had no values" % (algebra,))
    if max(values) < BOUNDS[algebra]:
        raise ValueError("OEIS b-file for %s stops before the bound" % (
            algebra,))
    return {value for value in values if value <= BOUNDS[algebra]}


def run_integrity_checks():
    total = 0
    for algebra in ALGEBRAS:
        rows = rows_for(algebra)
        total += len(rows)
        expected = EXPECTED_ROWS[algebra]
        if len(rows) != expected:
            raise AssertionError("%s: %d rows, expected %d" % (
                algebra, len(rows), expected))

        by_sum = _enumerate_by_total_weight(algebra)
        if rows != by_sum:
            ours = {(labels, value) for value, labels in rows}
            theirs = {(labels, value) for value, labels in by_sum}
            raise AssertionError("%s: prefix and total-weight enumerations "
                                 "differ: %r %r" % (
                                     algebra,
                                     sorted(ours - theirs)[:3],
                                     sorted(theirs - ours)[:3]))

        for labels, expected_dimension in FUNDAMENTAL_DIMENSIONS[algebra].items():
            computed = dimension(algebra, labels)
            if computed != expected_dimension:
                raise AssertionError("%s %s: %s, expected %s" % (
                    algebra, labels, computed, expected_dimension))

        ours_distinct = {ZZ(1)}
        ours_distinct.update(value for value, _ in rows)
        oeis = _oeis_dimensions(algebra)
        if ours_distinct != oeis:
            raise AssertionError("%s: OEIS disagreement, missing %r, extra %r"
                                 % (algebra,
                                    sorted(oeis - ours_distinct)[:5],
                                    sorted(ours_distinct - oeis)[:5]))

    if total != sum(EXPECTED_ROWS.values()):
        raise AssertionError("wrong total row count: %d" % (total,))
    print("integrity checks passed for %d rows" % (total,))


class ExceptionalLieRepresentationDimensions(numberdb.Generator):

    table = TABLE
    parameters = ("algebra", "weight")
    type = "Z"
    rigour = "exact"

    def enumerate(self):
        for algebra in ALGEBRAS:
            for _value, labels in rows_for(algebra):
                yield {"algebra": algebra, "weight": weight_text(labels)}

    def value(self, params, digits):
        algebra = str(params["algebra"])
        labels = parse_weight(params["weight"])
        return dimension(algebra, labels)


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
    generator = ExceptionalLieRepresentationDimensions()
    if os.environ.get("NUMBERDB_CHECK_ONLY") == "1":
        run_integrity_checks()
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        run_integrity_checks()
        print(fill_draft_once(
            generator,
            message="exceptional Lie algebra representation dimensions"))
    else:
        run_integrity_checks()
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
