"""Division polynomials psi_n of elliptic curves over Q -- numberdb.org/T341.

This generator fills T341 with the full division polynomials psi_n in
ZZ[x,y], including the factor 2*y + a1*x + a3 for even n. The curves are the
reduced global minimal models in Sage's mini Cremona database with conductor
N <= 60, and the table stores 1 <= n <= 5.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The computation is exact. Polynomials are represented as A(x) + B(x)*y in the
coordinate ring of y^2 + a1*x*y + a3*y = x^3 + a2*x^2 + a4*x + a6. The
integrity check compares the odd division polynomials, and the even ones after
multiplication by 2*y + a1*x + a3, with PARI/GP's exact elldivpol.
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.databases.cremona import CremonaDatabase
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T341")
CONDUCTOR_BOUND = 60
MAX_N = 5
DIGITS = 100

QQX = PolynomialRing(QQ, "x")
x = QQX.gen()
ZZX = PolynomialRing(ZZ, "x")
ZZXY = PolynomialRing(ZZ, ("x", "y"))
X, Y = ZZXY.gens()


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


def cremona_rows(bound=CONDUCTOR_BOUND):
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


class DivisionPolynomialRing:
    """Coordinate-ring arithmetic for one Weierstrass model."""

    def __init__(self, ainvs):
        self.a1, self.a2, self.a3, self.a4, self.a6 = [QQ(a) for a in ainvs]
        self.b2, self.b4, self.b6, self.b8, _, _ = [
            QQ(value) for value in invariants(ainvs)
        ]
        self.p = self.a1 * x + self.a3
        self.f = x**3 + self.a2 * x**2 + self.a4 * x + self.a6
        self.psi = {
            0: (QQX(0), QQX(0)),
            1: (QQX(1), QQX(0)),
            2: (self.p, QQX(2)),
            3: (
                3 * x**4
                + self.b2 * x**3
                + 3 * self.b4 * x**2
                + 3 * self.b6 * x
                + self.b8,
                QQX(0),
            ),
        }
        q4 = (
            2 * x**6
            + self.b2 * x**5
            + 5 * self.b4 * x**4
            + 10 * self.b6 * x**3
            + 10 * self.b8 * x**2
            + (self.b2 * self.b8 - self.b4 * self.b6) * x
            + self.b4 * self.b8
            - self.b6**2
        )
        self.psi[4] = self.multiply(self.psi[2], (q4, QQX(0)))

    def multiply(self, left, right):
        A, B = left
        C, D = right
        return (
            A * C + B * D * self.f,
            A * D + B * C - B * D * self.p,
        )

    def subtract(self, left, right):
        return left[0] - right[0], left[1] - right[1]

    def power(self, value, exponent):
        result = (QQX(1), QQX(0))
        base = value
        n = exponent
        while n:
            if n % 2:
                result = self.multiply(result, base)
            base = self.multiply(base, base)
            n //= 2
        return result

    def divide_by_psi2(self, value):
        R, S = value
        denominator = self.p**2 + 4 * self.f
        numerator = 2 * R - self.p * S
        quotient, remainder = numerator.quo_rem(denominator)
        if remainder != 0:
            raise ArithmeticError("division by psi_2 left remainder %s" % remainder)
        return (S + self.p * quotient) / QQ(2), quotient

    def division_polynomial_pair(self, n):
        if n in self.psi:
            return self.psi[n]
        for k in range(max(self.psi) + 1, n + 1):
            if k in self.psi:
                continue
            if k % 2:
                m = (k - 1) // 2
                value = self.subtract(
                    self.multiply(self.psi[m + 2], self.power(self.psi[m], 3)),
                    self.multiply(self.psi[m - 1], self.power(self.psi[m + 1], 3)),
                )
            else:
                m = k // 2
                term = self.subtract(
                    self.multiply(self.psi[m + 2], self.power(self.psi[m - 1], 2)),
                    self.multiply(self.psi[m - 2], self.power(self.psi[m + 1], 2)),
                )
                value = self.divide_by_psi2(self.multiply(self.psi[m], term))
            self.psi[k] = value
        return self.psi[n]

    def division_polynomial(self, n):
        return pair_to_polynomial(self.division_polynomial_pair(n))

    def pari_comparison_polynomial(self, n):
        ainvs = [str(ZZ(a)) for a in (self.a1, self.a2, self.a3, self.a4, self.a6)]
        curve = pari("ellinit([%s])" % ",".join(ainvs))
        return ZZX(str(pari("elldivpol(%s,%s)" % (curve, n))))

    def sage_default_polynomial_from_pair(self, pair):
        value = self.multiply(pair, self.psi[2])
        A, B = value
        if B != 0:
            raise ArithmeticError("even comparison is not x-only: %s" % B)
        return pair_to_univariate((A, QQX(0)))


def _integral_univariate(poly):
    if poly == 0:
        return ZZX(0)
    coeffs = []
    for degree in range(poly.degree() + 1):
        coefficient = poly[degree]
        if coefficient.denominator() != 1:
            raise ArithmeticError("nonintegral coefficient %s" % coefficient)
        coeffs.append(ZZ(coefficient))
    return ZZX(coeffs)


def pair_to_univariate(pair):
    A, B = pair
    if B != 0:
        raise ArithmeticError("not a univariate polynomial: %s + (%s)y" % (A, B))
    return _integral_univariate(A)


def pair_to_polynomial(pair):
    A, B = pair
    result = ZZXY(0)
    for poly, factor in ((A, ZZXY(1)), (B, Y)):
        if poly == 0:
            continue
        integral = _integral_univariate(poly)
        for degree, coefficient in integral.dict().items():
            result += coefficient * (X**degree) * factor
    return result


def curve_for_params(params):
    wanted = (ZZ(params["N"]), ZZ(params["c4"]), ZZ(params["c6"]))
    for row in cremona_rows():
        _b2, _b4, _b6, _b8, c4, c6 = invariants(row["ainvs"])
        if (row["N"], c4, c6) == wanted:
            return row
    raise KeyError("no stored curve has N=%s, c4=%s, c6=%s" % wanted)


class DivisionPolynomialsEllipticCurvesQ(numberdb.Generator):
    """Generator for T341, division polynomials of elliptic curves over Q."""

    table = TABLE
    parameters = ("N", "c4", "c6", "n")
    type = "Z[]"
    rigour = "exact"
    digits = DIGITS

    def enumerate(self):
        for row in cremona_rows():
            _b2, _b4, _b6, _b8, c4, c6 = invariants(row["ainvs"])
            for n in range(1, MAX_N + 1):
                yield {
                    "N": str(row["N"]),
                    "c4": str(c4),
                    "c6": str(c6),
                    "n": str(n),
                }

    def value(self, params, digits):
        row = curve_for_params(params)
        ring = DivisionPolynomialRing(row["ainvs"])
        return {
            "number": ring.division_polynomial(ZZ(params["n"])),
            "comment": "Cremona label %s%s." % (row["N"], row["label"]),
        }


def _check_degree_and_leading(ring, n):
    pair = ring.division_polynomial_pair(n)
    if n % 2:
        poly = pair_to_univariate(pair)
        expected_degree = (n * n - 1) // 2
        expected_leading = ZZ(n)
    else:
        quotient = ring.divide_by_psi2(pair)
        poly = pair_to_univariate(quotient)
        expected_degree = (n * n - 4) // 2
        expected_leading = ZZ(n // 2)
    if poly.degree() != expected_degree:
        raise ArithmeticError(
            "n=%s has degree %s, expected %s"
            % (n, poly.degree(), expected_degree)
        )
    if poly.leading_coefficient() != expected_leading:
        raise ArithmeticError(
            "n=%s has leading coefficient %s, expected %s"
            % (n, poly.leading_coefficient(), expected_leading)
        )


def _check_pari(row, n):
    ring = DivisionPolynomialRing(row["ainvs"])
    pair = ring.division_polynomial_pair(n)
    expected = ring.pari_comparison_polynomial(n)
    if n % 2:
        found = pair_to_univariate(pair)
    else:
        found = ring.sage_default_polynomial_from_pair(pair)
    if found != expected:
        raise ArithmeticError(
            "%s%s n=%s: recurrence gives %s, PARI gives %s"
            % (row["N"], row["label"], n, found, expected)
        )


def run_integrity_checks():
    rows = list(cremona_rows())
    if len(rows) != 161:
        raise ArithmeticError("expected 161 curves, found %d" % len(rows))

    longest = ("", 0)
    entries = 0
    for row in rows:
        ring = DivisionPolynomialRing(row["ainvs"])
        for n in range(1, MAX_N + 1):
            polynomial = ring.division_polynomial(n)
            length = len(str(polynomial))
            if length > longest[1]:
                longest = ("%s%s, n=%s" % (row["N"], row["label"], n), length)
            _check_degree_and_leading(ring, n)
            _check_pari(row, n)
            entries += 1

    example = next(row for row in rows if row["N"] == 37 and row["label"] == "a1")
    example_polynomial = DivisionPolynomialRing(example["ainvs"]).division_polynomial(3)
    expected = ZZXY("3*x^4 - 6*x^2 + 3*x - 1")
    if example_polynomial != expected:
        raise ArithmeticError("37a1 psi_3 is %s, expected %s" % (
            example_polynomial, expected))

    print("integrity checks passed for %d division polynomials" % entries)
    print("matched PARI elldivpol on every row, with the even-n psi_2 factor")
    print("checked the degree and leading coefficient formula for every row")
    print("37a1 psi_3 is %s" % expected)
    print("longest polynomial has %d characters at %s" % (longest[1], longest[0]))


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
    generator = DivisionPolynomialsEllipticCurvesQ()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill division-polynomial draft from exact recurrences",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
