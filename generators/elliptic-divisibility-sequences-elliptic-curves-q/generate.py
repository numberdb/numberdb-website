"""Elliptic divisibility sequences W_n of points on elliptic curves over Q -- numberdb.org/T347.

This generator fills T347 with exact integer terms W_n(P) = psi_n(P), where
psi_n is the n-th division polynomial of the reduced global minimal
Weierstrass model of E. The table stores the first sign-normalised
Mordell-Weil generator for each rank-one curve in Sage's mini Cremona
database with conductor N <= 60, and 1 <= n <= 50.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The computation is exact. The first four terms are evaluated from the standard
division polynomial formulas, and the remaining terms are computed by the
elliptic divisibility sequence recurrence. The integrity check verifies the
recurrence, verifies the x-coordinate formula against exact point
multiplication on the generalized Weierstrass model, and checks the first
terms of three sequences against OEIS.
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.databases.cremona import CremonaDatabase
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T347")
MAX_N = 50
DIGITS = 100

# Sage's EllipticCurve(...).gens()[0], with the sign changed when necessary
# so that W_2(P) = 2*y + a1*x + a3 is positive. They are kept explicit because
# the lightweight Sage environment used by agents can read Cremona's compact
# curve records but cannot construct elliptic-curve objects without importing
# sage.all.
POINTS = (
    (37, "a1", 0, 0),
    (43, "a1", 0, 0),
    (53, "a1", 0, 0),
    (57, "a1", 2, 1),
    (58, "a1", 0, 1),
)

OEIS_TERMS = {
    (37, "a1"): [1, 1, -1, 1, 2, -1, -3, -5, 7, -4, -23, 29],
    (43, "a1"): [1, 1, 1, -1, -2, -3, -1, 7, 11, 20, -19, -87],
    (53, "a1"): [1, 1, -1, -2, -1, 5, 9, -8, -41, -61, 241, 770],
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _label_key(label):
    found = re.fullmatch(r"([a-z]+)(\d+)", label)
    if found is None:
        return label, 0
    return found.group(1), int(found.group(2))


def all_cremona_rows(bound=60):
    database = CremonaDatabase()
    for conductor in range(1, bound + 1):
        rows = database.allcurves(conductor)
        for label, record in sorted(rows.items(), key=lambda item: _label_key(item[0])):
            ainvs, rank, torsion_order = record
            yield {
                "N": ZZ(conductor),
                "label": label,
                "ainvs": tuple(ZZ(a) for a in ainvs),
                "rank": ZZ(rank),
                "torsion_order": ZZ(torsion_order),
            }


def invariants(ainvs):
    a1, a2, a3, a4, a6 = [ZZ(a) for a in ainvs]
    b2 = a1 * a1 + 4 * a2
    b4 = a1 * a3 + 2 * a4
    b6 = a3 * a3 + 4 * a6
    b8 = a1 * a1 * a6 + 4 * a2 * a6 - a1 * a3 * a4 + a2 * a3 * a3 - a4 * a4
    c4 = b2 * b2 - 24 * b4
    c6 = -b2 * b2 * b2 + 36 * b2 * b4 - 216 * b6
    return b2, b4, b6, b8, c4, c6


def selected_rows():
    by_key = {(row["N"], row["label"]): row for row in all_cremona_rows()}
    for conductor, label, xP, yP in POINTS:
        row = dict(by_key[(ZZ(conductor), label)])
        row["xP"] = ZZ(xP)
        row["yP"] = ZZ(yP)
        yield row


def row_for_params(params):
    wanted = (
        ZZ(params["N"]),
        ZZ(params["c4"]),
        ZZ(params["c6"]),
        ZZ(params["xP"]),
        ZZ(params["yP"]),
    )
    for row in selected_rows():
        _b2, _b4, _b6, _b8, c4, c6 = invariants(row["ainvs"])
        found = (row["N"], c4, c6, row["xP"], row["yP"])
        if found == wanted:
            return row
    raise KeyError("no stored point has parameters %s" % (wanted,))


def point_lies_on_curve(ainvs, point):
    a1, a2, a3, a4, a6 = [QQ(a) for a in ainvs]
    x, y = [QQ(v) for v in point]
    left = y * y + a1 * x * y + a3 * y
    right = x**3 + a2 * x * x + a4 * x + a6
    return left == right


def negate_point(ainvs, point):
    if point is None:
        return None
    a1, _a2, a3, _a4, _a6 = [QQ(a) for a in ainvs]
    x, y = point
    return x, -y - a1 * x - a3


def add_points(ainvs, left, right):
    if left is None:
        return right
    if right is None:
        return left

    a1, a2, a3, a4, a6 = [QQ(a) for a in ainvs]
    x1, y1 = [QQ(v) for v in left]
    x2, y2 = [QQ(v) for v in right]

    if x1 == x2 and y1 + y2 + a1 * x2 + a3 == 0:
        return None

    if x1 == x2 and y1 == y2:
        denominator = 2 * y1 + a1 * x1 + a3
        if denominator == 0:
            return None
        slope = (3 * x1 * x1 + 2 * a2 * x1 + a4 - a1 * y1) / denominator
    else:
        slope = (y2 - y1) / (x2 - x1)

    intercept = y1 - slope * x1
    x3 = slope * slope + a1 * slope - a2 - x1 - x2
    y3 = -(slope + a1) * x3 - intercept - a3
    return x3, y3


def multiply_point(ainvs, point, n):
    n = ZZ(n)
    if n == 0:
        return None
    if n < 0:
        return multiply_point(ainvs, negate_point(ainvs, point), -n)
    result = None
    addend = (QQ(point[0]), QQ(point[1]))
    while n:
        if n % 2:
            result = add_points(ainvs, result, addend)
        addend = add_points(ainvs, addend, addend)
        n //= 2
    return result


def initial_terms(ainvs, point):
    x, y = [ZZ(v) for v in point]
    a1, _a2, a3, _a4, _a6 = [ZZ(a) for a in ainvs]
    b2, b4, b6, b8, _c4, _c6 = invariants(ainvs)

    w2 = 2 * y + a1 * x + a3
    w3 = 3 * x**4 + b2 * x**3 + 3 * b4 * x**2 + 3 * b6 * x + b8
    q4 = (
        2 * x**6
        + b2 * x**5
        + 5 * b4 * x**4
        + 10 * b6 * x**3
        + 10 * b8 * x**2
        + (b2 * b8 - b4 * b6) * x
        + b4 * b8
        - b6**2
    )
    return {0: ZZ(0), 1: ZZ(1), 2: ZZ(w2), 3: ZZ(w3), 4: ZZ(w2 * q4)}


def sequence_terms(ainvs, point, max_n):
    terms = initial_terms(ainvs, point)

    def W(n):
        n = ZZ(n)
        if n not in terms:
            if n % 2:
                m = (n - 1) // 2
                terms[n] = W(m + 2) * W(m) ** 3 - W(m - 1) * W(m + 1) ** 3
            else:
                m = n // 2
                numerator = W(m) * (
                    W(m + 2) * W(m - 1) ** 2
                    - W(m - 2) * W(m + 1) ** 2
                )
                denominator = W(2)
                quotient, remainder = ZZ(numerator).quo_rem(ZZ(denominator))
                if remainder != 0:
                    raise ArithmeticError(
                        "W_%s recurrence did not divide by W_2" % n
                    )
                terms[n] = quotient
        return terms[n]

    for n in range(0, int(max_n) + 1):
        W(n)
    return terms


def verify_recurrence(terms, max_n):
    for m in range(2, max_n // 2 + 2):
        n = 2 * m + 1
        if n <= max_n:
            expected = terms[m + 2] * terms[m] ** 3 - terms[m - 1] * terms[m + 1] ** 3
            if terms[n] != expected:
                raise ArithmeticError("W_%s failed the odd recurrence" % n)
    for m in range(3, max_n // 2 + 2):
        n = 2 * m
        if n <= max_n:
            expected = terms[m] * (
                terms[m + 2] * terms[m - 1] ** 2
                - terms[m - 2] * terms[m + 1] ** 2
            )
            if terms[n] * terms[2] != expected:
                raise ArithmeticError("W_%s failed the even recurrence" % n)


def verify_x_coordinate(row, terms, max_n):
    ainvs = row["ainvs"]
    point = (QQ(row["xP"]), QQ(row["yP"]))
    x0 = point[0]
    for n in range(1, max_n + 1):
        multiple = multiply_point(ainvs, point, n)
        if multiple is None:
            raise ArithmeticError("%s%s has torsion multiple %sP" % (
                row["N"], row["label"], n))
        expected_x = x0 - QQ(terms[n - 1] * terms[n + 1]) / QQ(terms[n] ** 2)
        if multiple[0] != expected_x:
            raise ArithmeticError(
                "%s%s n=%s: x(nP)=%s, formula gives %s"
                % (row["N"], row["label"], n, multiple[0], expected_x)
            )


def run_integrity_checks():
    rows = list(selected_rows())
    if len(rows) != len(POINTS):
        raise ArithmeticError("expected %d selected rows, found %d" % (
            len(POINTS), len(rows)))

    rank_one = [row for row in all_cremona_rows() if row["rank"] == 1]
    expected_keys = sorted((ZZ(N), label) for N, label, _x, _y in POINTS)
    found_keys = sorted((row["N"], row["label"]) for row in rank_one)
    if found_keys != expected_keys:
        raise ArithmeticError(
            "rank-one curves with N <= 60 changed: %s" % (found_keys,)
        )

    longest = ("", 0)
    entries = 0
    for row in rows:
        point = (row["xP"], row["yP"])
        if not point_lies_on_curve(row["ainvs"], point):
            raise ArithmeticError("%s%s point is not on the curve" % (
                row["N"], row["label"]))
        terms = sequence_terms(row["ainvs"], point, MAX_N + 1)
        if terms[2] <= 0:
            raise ArithmeticError("%s%s has W_2=%s, not positive" % (
                row["N"], row["label"], terms[2]))
        verify_recurrence(terms, MAX_N + 1)
        verify_x_coordinate(row, terms, MAX_N)

        expected = OEIS_TERMS.get((int(row["N"]), row["label"]))
        if expected is not None:
            found = [int(terms[n]) for n in range(1, len(expected) + 1)]
            if found != expected:
                raise ArithmeticError(
                    "%s%s first terms %s did not match OEIS %s"
                    % (row["N"], row["label"], found, expected)
                )

        for n in range(1, MAX_N + 1):
            length = len(str(terms[n]))
            if length > longest[1]:
                longest = ("%s%s, n=%s" % (row["N"], row["label"], n), length)
            entries += 1

    print("integrity checks passed for %d EDS terms" % entries)
    print("checked every recurrence through W_%s" % (MAX_N + 1))
    print("checked x(nP) against exact point multiplication for every stored n")
    print("checked 37a1, 43a1 and 53a1 first terms against OEIS")
    print("longest integer has %d digits at %s" % (longest[1], longest[0]))


class EllipticDivisibilitySequences(numberdb.Generator):
    """Generator for T347, elliptic divisibility sequences W_n."""

    table = TABLE
    parameters = ("N", "c4", "c6", "xP", "yP", "n")
    type = "Z"
    rigour = "exact"
    digits = DIGITS

    def enumerate(self):
        for row in selected_rows():
            _b2, _b4, _b6, _b8, c4, c6 = invariants(row["ainvs"])
            for n in range(1, MAX_N + 1):
                yield {
                    "N": str(row["N"]),
                    "c4": str(c4),
                    "c6": str(c6),
                    "xP": str(row["xP"]),
                    "yP": str(row["yP"]),
                    "n": str(n),
                }

    def value(self, params, digits):
        row = row_for_params(params)
        terms = sequence_terms(row["ainvs"], (row["xP"], row["yP"]), ZZ(params["n"]))
        return {
            "number": terms[ZZ(params["n"])],
            "comment": "Cremona label %s%s." % (row["N"], row["label"]),
        }


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
    generator = EllipticDivisibilitySequences()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill EDS draft from exact division-polynomial recurrence",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
