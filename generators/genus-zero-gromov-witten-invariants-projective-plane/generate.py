"""Genus-zero Gromov-Witten invariants of the projective plane -- numberdb.org/T398

This generator stores the exact integers N_d counting degree-d rational plane
curves through 3d - 1 points in general position. It uses Kontsevich's
recursion and checks the computed values against the initial terms of OEIS
A013587 before writing or verifying the table.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The range is 1 <= d <= 14. At d = 14 the values already have 35 digits, so
the table records the small-degree counts rather than reproducing the 169-term
OEIS b-file.
"""

import os
import sys
from math import comb

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = "T398"
LIMIT = 14

SOURCE_VALUES = {
    1: 1,
    2: 1,
    3: 12,
    4: 620,
    5: 87304,
    6: 26312976,
    7: 14616808192,
    8: 13525751027392,
    9: 19385778269260800,
    10: 40739017561997799680,
    11: 120278021410937387514880,
    12: 482113680618029292368686080,
    13: 2551154673732472157928033617920,
    14: 17410560213476464590484763013222400,
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def kontsevich_numbers(limit):
    values = {1: ZZ(1)}
    for d in range(2, limit + 1):
        total = ZZ(0)
        for a in range(1, d):
            b = d - a
            coefficient = (
                b * comb(3 * d - 4, 3 * a - 2)
                - a * comb(3 * d - 4, 3 * a - 1)
            )
            total += values[a] * values[b] * a * a * b * coefficient
        values[d] = ZZ(total)
    return values


def check_source_values():
    values = kontsevich_numbers(LIMIT)
    for d, expected in SOURCE_VALUES.items():
        if values[d] != expected:
            raise AssertionError(
                "d=%d: recurrence gives %s, source gives %s"
                % (d, values[d], expected)
            )


class ProjectivePlaneGenusZeroGromovWitten(numberdb.Generator):
    table = TABLE
    parameters = ("d",)
    type = "Z"
    rigour = "exact"

    def enumerate(self, limit=LIMIT):
        for d in range(1, limit + 1):
            yield {"d": str(d)}

    def value(self, params, digits):
        d = int(params["d"])
        return kontsevich_numbers(d)[d]


if __name__ == "__main__":
    _key_from_stdin()
    check_source_values()
    generator = ProjectivePlaneGenusZeroGromovWitten()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="computed exact Kontsevich recurrence"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
