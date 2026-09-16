"""Known solutions of the Fermat-Catalan equation -- numberdb.org/T279.

    x^p + y^q = z^r

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores the nine known coprime solutions with xyz > 1, ordered so
that x^p < y^q. The infinite family 1^p + 2^3 = 3^2, with p > 6, accounts for
the OEIS A214618 term 9 and is described in the table comments rather than
stored as entries.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = os.environ.get("NUMBERDB_TABLE", "T279")


# Tuples are (x, p, y, q, z, r), with x^p < y^q.
SOLUTIONS = (
    (2, 5, 7, 2, 3, 4),
    (13, 2, 7, 3, 2, 9),
    (2, 7, 17, 3, 71, 2),
    (3, 5, 11, 4, 122, 2),
    (33, 8, 1549034, 2, 15613, 3),
    (1414, 3, 2213459, 2, 65, 7),
    (9262, 3, 15312283, 2, 113, 7),
    (17, 7, 76271, 3, 21063928, 2),
    (43, 8, 96222, 3, 30042907, 2),
)


# OEIS A214618 b-file, including the Catalan-family term 9.
OEIS_A214618 = (
    9,
    81,
    512,
    5041,
    14884,
    3805914951397,
    4902227890625,
    235260548044817,
    443689062789184,
    902576261010649,
)


_CHECKED = False


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _powers(solution):
    x, p, y, q, z, r = solution
    return ZZ(x) ** p, ZZ(y) ** q, ZZ(z) ** r


def _sum(solution):
    return _powers(solution)[2]


def _exponents(solution):
    _x, p, _y, q, _z, r = solution
    return p, q, r


def _by_sum():
    out = {}
    for solution in SOLUTIONS:
        total = int(_sum(solution))
        if total in out:
            raise ArithmeticError("duplicate sum %s" % total)
        out[total] = solution
    return out


def _check_solution(solution):
    x, p, y, q, z, r = solution
    left, right, total = _powers(solution)

    if not (left < right):
        raise ArithmeticError("%s is not ordered by summand size" % (solution,))
    if left + right != total:
        raise ArithmeticError("%s does not satisfy x^p + y^q = z^r" % (solution,))
    if gcd(gcd(x, y), z) != 1:
        raise ArithmeticError("%s is not coprime" % (solution,))
    if x * y * z <= 1:
        raise ArithmeticError("%s is not in the xyz > 1 part" % (solution,))
    if p * q + p * r + q * r >= p * q * r:
        raise ArithmeticError("%s does not satisfy 1/p + 1/q + 1/r < 1" %
                              (solution,))
    if 2 not in (p, q, r):
        raise ArithmeticError("%s has no exponent 2" % (solution,))


def _check_data():
    global _CHECKED
    if _CHECKED:
        return

    for solution in SOLUTIONS:
        _check_solution(solution)

    sums = tuple(int(_sum(solution)) for solution in SOLUTIONS)
    if sums != OEIS_A214618[1:]:
        raise ArithmeticError("stored sums do not match OEIS A214618: %s" %
                              (sums,))
    if list(sums) != sorted(sums):
        raise ArithmeticError("solutions are not ordered by z^r")

    if 65 ** 7 != 4902227890625:
        raise ArithmeticError("the 65^7 check from the proposal failed")

    _CHECKED = True


def _entry_comment(solution, part):
    p, q, r = _exponents(solution)
    if part == "x":
        return "In this solution, $x$ has exponent $p=%d$." % p
    if part == "y":
        return "In this solution, $y$ has exponent $q=%d$." % q
    if part == "z":
        return "In this solution, $z$ has exponent $r=%d$." % r
    if part == "sum":
        return "This is $z^r$ for $(p,q,r)=(%d,%d,%d)$." % (p, q, r)
    raise ValueError("unknown part %s" % part)


class FermatCatalanKnownSolutions(numberdb.Generator):

    table = TABLE
    parameters = ("sum", "part")
    type = "Z"
    rigour = "exact"

    def enumerate(self):
        _check_data()
        for solution in SOLUTIONS:
            total = str(_sum(solution))
            for part in ("x", "y", "z", "sum"):
                yield {"sum": total, "part": part}

    def value(self, params, digits):
        _check_data()
        solution = _by_sum()[int(params["sum"])]
        x, _p, y, _q, z, _r = solution
        part = params["part"]
        if part == "x":
            number = ZZ(x)
        elif part == "y":
            number = ZZ(y)
        elif part == "z":
            number = ZZ(z)
        elif part == "sum":
            number = _sum(solution)
        else:
            raise ValueError("unknown part %s" % part)
        return {"number": number, "comment": _entry_comment(solution, part)}


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
    generator = FermatCatalanKnownSolutions()
    _check_data()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="exact Fermat-Catalan solution parts checked against OEIS A214618"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
