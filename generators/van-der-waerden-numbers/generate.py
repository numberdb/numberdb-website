"""Van der Waerden numbers w(r; k_1,...,k_r) -- numberdb.org/T440

This generator fills the draft table of exact Van der Waerden numbers listed
in the cited source table, together with the finite trivial rows that cover the
same displayed range.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = os.environ.get("NUMBERDB_TABLE", "T440")
MAX_ONE_COLOR_LENGTH = 20
MAX_ALL_TWO_COLORS = 21

SOURCE_ROWS = (
    (2, (3, 3), 9),
    (2, (3, 4), 18),
    (2, (3, 5), 22),
    (2, (3, 6), 32),
    (2, (3, 7), 46),
    (2, (3, 8), 58),
    (2, (3, 9), 77),
    (2, (3, 10), 97),
    (2, (3, 11), 114),
    (2, (3, 12), 135),
    (2, (3, 13), 160),
    (2, (3, 14), 186),
    (2, (3, 15), 218),
    (2, (3, 16), 238),
    (2, (3, 17), 279),
    (2, (3, 18), 312),
    (2, (3, 19), 349),
    (2, (3, 20), 389),
    (2, (4, 4), 35),
    (2, (4, 5), 55),
    (2, (4, 6), 73),
    (2, (4, 7), 109),
    (2, (4, 8), 146),
    (2, (4, 9), 309),
    (2, (5, 5), 178),
    (2, (5, 6), 206),
    (2, (5, 7), 260),
    (2, (6, 6), 1132),
    (3, (2, 3, 3), 14),
    (3, (2, 3, 4), 21),
    (3, (2, 3, 5), 32),
    (3, (2, 3, 6), 40),
    (3, (2, 3, 7), 55),
    (3, (2, 3, 8), 72),
    (3, (2, 3, 9), 90),
    (3, (2, 3, 10), 108),
    (3, (2, 3, 11), 129),
    (3, (2, 3, 12), 150),
    (3, (2, 3, 13), 171),
    (3, (2, 3, 14), 202),
    (3, (2, 4, 4), 40),
    (3, (2, 4, 5), 71),
    (3, (2, 4, 6), 83),
    (3, (2, 4, 7), 119),
    (3, (2, 4, 8), 157),
    (3, (2, 5, 5), 180),
    (3, (2, 5, 6), 246),
    (3, (3, 3, 3), 27),
    (3, (3, 3, 4), 51),
    (3, (3, 3, 5), 80),
    (3, (3, 3, 6), 107),
    (3, (3, 4, 4), 89),
    (3, (4, 4, 4), 293),
    (4, (2, 2, 3, 3), 17),
    (4, (2, 2, 3, 4), 25),
    (4, (2, 2, 3, 5), 43),
    (4, (2, 2, 3, 6), 48),
    (4, (2, 2, 3, 7), 65),
    (4, (2, 2, 3, 8), 83),
    (4, (2, 2, 3, 9), 99),
    (4, (2, 2, 3, 10), 119),
    (4, (2, 2, 3, 11), 141),
    (4, (2, 2, 3, 12), 163),
    (4, (2, 2, 4, 4), 53),
    (4, (2, 2, 4, 5), 75),
    (4, (2, 2, 4, 6), 93),
    (4, (2, 2, 4, 7), 143),
    (4, (2, 3, 3, 3), 40),
    (4, (2, 3, 3, 4), 60),
    (4, (2, 3, 3, 5), 86),
    (4, (2, 3, 3, 6), 115),
    (4, (3, 3, 3, 3), 76),
    (5, (2, 2, 2, 3, 3), 20),
    (5, (2, 2, 2, 3, 4), 29),
    (5, (2, 2, 2, 3, 5), 44),
    (5, (2, 2, 2, 3, 6), 56),
    (5, (2, 2, 2, 3, 7), 72),
    (5, (2, 2, 2, 3, 8), 88),
    (5, (2, 2, 2, 3, 9), 107),
    (5, (2, 2, 2, 4, 4), 54),
    (5, (2, 2, 2, 4, 5), 79),
    (5, (2, 2, 2, 4, 6), 101),
    (5, (2, 2, 3, 3, 3), 41),
    (5, (2, 2, 3, 3, 4), 63),
    (5, (2, 2, 3, 3, 5), 95),
    (6, (2, 2, 2, 2, 3, 3), 21),
    (6, (2, 2, 2, 2, 3, 4), 33),
    (6, (2, 2, 2, 2, 3, 5), 50),
    (6, (2, 2, 2, 2, 3, 6), 60),
    (6, (2, 2, 2, 2, 4, 4), 56),
    (6, (2, 2, 2, 3, 3, 3), 42),
    (7, (2, 2, 2, 2, 2, 3, 3), 24),
    (7, (2, 2, 2, 2, 2, 3, 4), 36),
    (7, (2, 2, 2, 2, 2, 3, 5), 55),
    (7, (2, 2, 2, 2, 2, 3, 6), 65),
    (7, (2, 2, 2, 2, 2, 4, 4), 66),
    (7, (2, 2, 2, 2, 3, 3, 3), 45),
    (8, (2, 2, 2, 2, 2, 2, 3, 3), 25),
    (8, (2, 2, 2, 2, 2, 2, 3, 4), 40),
    (8, (2, 2, 2, 2, 2, 2, 3, 5), 61),
    (8, (2, 2, 2, 2, 2, 2, 3, 6), 71),
    (8, (2, 2, 2, 2, 2, 2, 4, 4), 67),
    (8, (2, 2, 2, 2, 2, 3, 3, 3), 49),
    (9, (2, 2, 2, 2, 2, 2, 2, 3, 3), 28),
    (9, (2, 2, 2, 2, 2, 2, 2, 3, 4), 42),
    (9, (2, 2, 2, 2, 2, 2, 2, 3, 5), 65),
    (9, (2, 2, 2, 2, 2, 2, 3, 3, 3), 52),
    (10, (2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 31),
    (10, (2, 2, 2, 2, 2, 2, 2, 2, 3, 4), 45),
    (10, (2, 2, 2, 2, 2, 2, 2, 2, 3, 5), 70),
    (11, (2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 33),
    (11, (2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 4), 48),
    (12, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 35),
    (12, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 4), 52),
    (13, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 37),
    (13, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 4), 55),
    (14, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 39),
    (15, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 42),
    (16, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 44),
    (17, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 46),
    (18, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 48),
    (19, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 50),
    (20, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 51),
    (21, (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3), 52),
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _tuple_text(parts):
    return ",".join(str(part) for part in parts)


def _all_rows():
    rows = {}
    for k in range(1, MAX_ONE_COLOR_LENGTH + 1):
        rows[(1, (k,))] = k
    for r in range(1, MAX_ALL_TWO_COLORS + 1):
        rows[(r, tuple([2] * r))] = r + 1
    for r, parts, value in SOURCE_ROWS:
        rows[(r, parts)] = value
    if len(SOURCE_ROWS) != 124:
        raise AssertionError("the transcribed source table should have 124 rows")
    return rows


VALUES = _all_rows()


def _check_parameters(r, parts):
    if r != len(parts):
        raise ValueError("r=%s but k has %s parts" % (r, len(parts)))
    if tuple(sorted(parts)) != parts:
        raise ValueError("k is not weakly increasing: %r" % (parts,))
    if any(part < 1 for part in parts):
        raise ValueError("all progression lengths must be positive: %r" % (parts,))


class VanDerWaerdenNumbers(numberdb.Generator):

    table = TABLE
    parameters = ("r", "k")
    type = "Z"
    rigour = "exact"

    def enumerate(self):
        for r, parts in sorted(VALUES):
            yield {"r": str(r), "k": _tuple_text(parts)}

    def value(self, params, digits):
        r = int(params["r"])
        parts = tuple(int(part) for part in params["k"].split(","))
        _check_parameters(r, parts)
        return ZZ(VALUES[(r, parts)])


def _identity_checks():
    for k in range(1, MAX_ONE_COLOR_LENGTH + 1):
        assert VALUES[(1, (k,))] == k
    for r in range(1, MAX_ALL_TWO_COLORS + 1):
        assert VALUES[(r, tuple([2] * r))] == r + 1
    for r, parts, value in SOURCE_ROWS:
        assert VALUES[(r, parts)] == value


if __name__ == "__main__":
    _key_from_stdin()
    _identity_checks()
    generator = VanDerWaerdenNumbers()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="fill exact van der Waerden numbers"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
