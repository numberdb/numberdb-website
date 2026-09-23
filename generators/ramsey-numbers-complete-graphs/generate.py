"""Ramsey numbers of complete graphs -- numberdb.org/T439.

This generator fills T439 with the small complete-graph Ramsey numbers
selected from DS1 revision #18: a complete two-colour rectangle through
3 <= k <= 7 and l <= 13, the matching trivial rows, and the multicolour
complete-graph exact values or explicit two-sided bounds stated in DS1
section 6.1.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = os.environ.get("NUMBERDB_TABLE", "T439")
MAX_TWO_COLOUR_CLIQUE = 13


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _tuple_text(values):
    return ",".join(str(value) for value in values)


def _interval(lower, upper, comment):
    return {"number": "[%d, %d]" % (lower, upper), "comment": comment}


TABLE_IA_COMMENT = (
    "The endpoints are the lower and upper bounds in DS1 revision #18, "
    "Table Ia."
)
TABLE_IB_COMMENT = (
    "The lower endpoint is from DS1 revision #18, Table Ia. The upper "
    "endpoint is the Angeltveit-McKay bound in Table Ib."
)
SECTION_61_COMMENT = (
    "The endpoints are the lower and upper bounds stated in DS1 revision #18, "
    "section 6.1."
)


DATA = {}


def add_exact(values, number):
    values = tuple(values)
    DATA[(len(values), values)] = ZZ(number)


def add_interval(values, lower, upper, comment):
    values = tuple(values)
    DATA[(len(values), values)] = _interval(lower, upper, comment)


add_exact((1, 1), 1)
for t in range(2, MAX_TWO_COLOUR_CLIQUE + 1):
    add_exact((2, t), t)

for l, value in {
    3: 6,
    4: 9,
    5: 14,
    6: 18,
    7: 23,
    8: 28,
    9: 36,
}.items():
    add_exact((3, l), value)
for l, bounds in {
    10: (40, 41),
    11: (47, 50),
    12: (53, 59),
    13: (61, 68),
}.items():
    add_interval((3, l), *bounds, TABLE_IA_COMMENT)

add_exact((4, 4), 18)
add_exact((4, 5), 25)
for l, bounds in {
    6: (36, 40),
    7: (49, 58),
    8: (59, 79),
    9: (73, 105),
    10: (92, 135),
    11: (102, 170),
    12: (128, 210),
    13: (139, 256),
}.items():
    add_interval((4, l), *bounds, TABLE_IB_COMMENT)

for l, bounds in {
    5: (43, 46),
    6: (59, 85),
    7: (80, 133),
    8: (101, 193),
    9: (133, 282),
    10: (149, 381),
    11: (183, 511),
    12: (203, 672),
    13: (233, 860),
}.items():
    add_interval((5, l), *bounds, TABLE_IB_COMMENT)

for l, bounds in {
    6: (102, 160),
    7: (115, 270),
    8: (134, 423),
    9: (183, 651),
    10: (204, 944),
    11: (262, 1346),
    12: (294, 1855),
    13: (347, 2499),
}.items():
    add_interval((6, l), *bounds, TABLE_IB_COMMENT)

for l, bounds in {
    7: (205, 492),
    8: (219, 832),
    9: (252, 1368),
    10: (292, 2119),
    11: (405, 3197),
    12: (417, 4665),
    13: (511, 6653),
}.items():
    add_interval((7, l), *bounds, TABLE_IB_COMMENT)

add_exact((3, 3, 3), 17)
add_exact((3, 3, 4), 30)
for values, bounds in {
    (3, 3, 5): (45, 57),
    (3, 3, 6): (61, 91),
    (3, 4, 4): (55, 77),
    (3, 4, 5): (89, 157),
    (4, 4, 4): (128, 229),
    (3, 3, 3, 3): (51, 62),
    (3, 3, 3, 4): (97, 149),
    (3, 3, 4, 4): (174, 450),
    (3, 4, 4, 4): (381, 1576),
    (4, 4, 4, 4): (634, 6301),
    (3, 3, 3, 3, 3): (162, 307),
    (3, 3, 3, 3, 3, 3): (538, 1838),
    (3, 3, 3, 3, 3, 3, 3): (1698, 12861),
}.items():
    add_interval(values, *bounds, SECTION_61_COMMENT)


T6_DIAGONAL = {
    (1, 1): "1",
    (2, 2): "2",
    (3, 3): "6",
    (4, 4): "18",
    (5, 5): "[43, 46]",
    (6, 6): "[102, 160]",
    (7, 7): "[205, 492]",
}


def _number_text(value):
    if isinstance(value, dict):
        return value["number"]
    return str(value)


def _upper_bound(values):
    values = tuple(v for v in values if v != 2)
    value = DATA[(len(values), values)]
    text = _number_text(value)
    if text.startswith("["):
        return int(text.rsplit(",", 1)[1].strip(" ]"))
    return int(text)


def _recursive_upper(values):
    values = tuple(values)
    total = 2 - len(values)
    summands = []
    for index, value in enumerate(values):
        if value <= 2:
            reduced = tuple(v for i, v in enumerate(values) if i != index)
        else:
            reduced = tuple(sorted(
                value - 1 if i == index else v
                for i, v in enumerate(values)
            ))
        summands.append(_upper_bound(reduced))
        total += summands[-1]
    if total % 2 == 0 and any(bound % 2 == 0 for bound in summands):
        total -= 1
    return total


def run_integrity_checks():
    if len(DATA) != 73:
        raise ArithmeticError("expected 73 Ramsey entries, found %d" % len(DATA))

    expected_order = sorted(DATA, key=lambda item: (item[0], item[1]))
    if list(DATA) != expected_order:
        raise ArithmeticError("entries are not ordered by r and then the tuple")

    for r, values in DATA:
        if r != len(values):
            raise ArithmeticError("wrong tuple length for %s" % (values,))
        if tuple(sorted(values)) != values:
            raise ArithmeticError("tuple is not weakly increasing: %s" % (values,))

    for t in range(2, MAX_TWO_COLOUR_CLIQUE + 1):
        if _number_text(DATA[(2, (2, t))]) != str(t):
            raise ArithmeticError("R(2,%d) is not stored as %d" % (t, t))

    for values, expected in T6_DIAGONAL.items():
        found = _number_text(DATA[(2, values)])
        if found != expected:
            raise ArithmeticError(
                "diagonal value %s is %s, not T6's %s"
                % (values, found, expected)
            )

    for r, values in DATA:
        text = _number_text(DATA[(r, values)])
        if not text.startswith("[") or r < 3:
            continue
        upper = int(text.rsplit(",", 1)[1].strip(" ]"))
        formula = _recursive_upper(values)
        if upper > formula:
            raise ArithmeticError(
                "upper bound for %s is %d, exceeding recursive bound %d"
                % (values, upper, formula)
            )


class CompleteGraphRamseyNumbers(numberdb.Generator):
    """Generator for T439, complete-graph Ramsey numbers."""

    table = TABLE
    parameters = ("r", "k")
    type = "Z"
    rigour = "proven"

    def enumerate(self):
        run_integrity_checks()
        for r, values in DATA:
            yield {"r": str(r), "k": _tuple_text(values)}

    def value(self, params, digits):
        run_integrity_checks()
        values = tuple(int(part) for part in params["k"].split(","))
        return DATA[(int(params["r"]), values)]


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
    generator = CompleteGraphRamseyNumbers()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Ramsey-number bounds transcribed from DS1 revision 18",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
