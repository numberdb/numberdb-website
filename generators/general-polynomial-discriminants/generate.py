"""Discriminants of the general polynomial of degree n -- numberdb.org/T381.

This generator stores

    disc(a0 + a1*x + ... + an*x^n)

for 1 <= n <= 5, with the coefficient convention ai*x^i. The discriminant is
computed from

    (-1)^(n(n-1)/2) * resultant(f, f') / an.

The range stops at n = 5 because the next general discriminant would use seven
coefficient variables, beyond NumberDB's polynomial-search limit, and because
the n = 5 row is already 1338 characters.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The values are exact integer polynomials. The integrity checks compare the
quadratic and cubic rows with the standard formulas, verify the root-product
definition after substituting elementary symmetric functions of the roots, and
compare integer specialisations with Sage's exact univariate discriminant.
"""

import os
import sys
from itertools import combinations

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T381")
MAX_DEGREE = 5

COEFFICIENT_RING = PolynomialRing(
    ZZ, ["a%s" % i for i in range(MAX_DEGREE + 1)]
)
A = COEFFICIENT_RING.gens()

X_RING = PolynomialRing(COEFFICIENT_RING, "x")
X = X_RING.gen()

INTEGER_X_RING = PolynomialRing(ZZ, "x")
INTEGER_X = INTEGER_X_RING.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def sign_for_degree(n):
    return ZZ(1) if (n * (n - 1) // 2) % 2 == 0 else ZZ(-1)


def discriminant_polynomial(n):
    n = int(n)
    f = sum(A[i] * X ** i for i in range(n + 1))
    numerator = sign_for_degree(n) * f.resultant(f.derivative())
    quotient, remainder = numerator.quo_rem(A[n])
    if remainder != 0:
        raise AssertionError("resultant was not divisible by a_%s" % n)
    return quotient


DISCRIMINANTS = {
    n: discriminant_polynomial(n) for n in range(1, MAX_DEGREE + 1)
}


def iter_parameters():
    for n in range(1, MAX_DEGREE + 1):
        yield {"n": ZZ(n)}


def _product(factors, ring):
    total = ring.one()
    for factor in factors:
        total *= factor
    return total


def elementary_symmetric(roots, k, ring):
    if k == 0:
        return ring.one()
    total = ring.zero()
    for indexes in combinations(range(len(roots)), k):
        total += _product((roots[i] for i in indexes), ring)
    return total


def root_formula_images(n, ring, roots, leading):
    images = [ring.zero() for _ in range(MAX_DEGREE + 1)]
    for i in range(n + 1):
        k = n - i
        sign = ZZ(1) if k % 2 == 0 else ZZ(-1)
        images[i] = leading * sign * elementary_symmetric(roots, k, ring)
    return images


def root_formula_discriminant(n):
    names = ["alpha%s" % i for i in range(1, n + 1)] + ["leading"]
    ring = PolynomialRing(ZZ, names)
    roots = ring.gens()[:n]
    leading = ring.gens()[n]

    found = ring(DISCRIMINANTS[n](*root_formula_images(n, ring, roots, leading)))
    factors = [
        (roots[i] - roots[j]) ** 2
        for i in range(n)
        for j in range(i + 1, n)
    ]
    expected = leading ** (2 * n - 2) * _product(factors, ring)
    return found, expected


def specialised_value(polynomial, coefficients):
    values = [ZZ(0) for _ in range(MAX_DEGREE + 1)]
    for i, coefficient in enumerate(coefficients):
        values[i] = ZZ(coefficient)
    return ZZ(polynomial(*values))


def integer_polynomial(coefficients):
    return sum(ZZ(coefficients[i]) * INTEGER_X ** i
               for i in range(len(coefficients)))


def check_printed_formulas():
    expected_quadratic = A[1] ** 2 - 4 * A[0] * A[2]
    if DISCRIMINANTS[2] != expected_quadratic:
        raise AssertionError("quadratic discriminant formula failed")

    expected_cubic = (
        A[1] ** 2 * A[2] ** 2
        - 4 * A[0] * A[2] ** 3
        - 4 * A[1] ** 3 * A[3]
        + 18 * A[0] * A[1] * A[2] * A[3]
        - 27 * A[0] ** 2 * A[3] ** 2
    )
    if DISCRIMINANTS[3] != expected_cubic:
        raise AssertionError("cubic discriminant formula failed")


def check_root_formula():
    for n in range(1, MAX_DEGREE + 1):
        found, expected = root_formula_discriminant(n)
        if found != expected:
            raise AssertionError("root formula failed for n=%s" % n)


def check_integer_specialisations():
    samples = {
        1: [(2, 3), (-5, 7), (0, -2)],
        2: [(-1, 0, 1), (3, 2, -5), (4, -7, 2)],
        3: [(1, -2, 3, 1), (-3, 0, 5, -2), (4, 1, -6, 3)],
        4: [(1, -2, 3, -4, 5), (-2, 5, 0, 3, -1), (7, -3, 2, 1, 4)],
        5: [(1, -1, 2, -3, 5, 1), (-4, 3, 0, -2, 1, -1), (2, 5, -7, 1, 0, 3)],
    }
    for n, rows in samples.items():
        for coefficients in rows:
            generic = specialised_value(DISCRIMINANTS[n], coefficients)
            direct = integer_polynomial(coefficients).discriminant()
            if generic != direct:
                raise AssertionError(
                    "integer discriminant mismatch for n=%s, %s: %s != %s"
                    % (n, coefficients, generic, direct)
                )


def check_identities():
    check_printed_formulas()
    check_root_formula()
    check_integer_specialisations()

    lengths = [
        (len(str(DISCRIMINANTS[n])), n)
        for n in range(1, MAX_DEGREE + 1)
    ]
    longest = max(lengths, key=lambda item: item[0])
    print("integrity checks passed for %d general discriminants" % MAX_DEGREE)
    print("root-product and integer-specialisation checks passed")
    print("longest polynomial has %d characters at n=%s"
          % (longest[0], longest[1]))


class GeneralPolynomialDiscriminants(numberdb.Generator):

    table = TABLE
    parameters = ("n",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        yield from iter_parameters()

    def value(self, params, digits):
        return DISCRIMINANTS[int(params["n"])]


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


def stored_values():
    table = numberdb.table(TABLE)
    numbers = table.get("Numbers") or {}
    values = {}
    if isinstance(numbers, dict):
        for key, value in numbers.items():
            if isinstance(value, dict):
                value = value.get("number")
            values[ZZ(key)] = COEFFICIENT_RING(str(value))
    elif isinstance(numbers, list):
        for row in numbers:
            params = row.get("params", row)
            value = row.get("number")
            values[ZZ(params["n"])] = COEFFICIENT_RING(str(value))
    return values


def check_stored_values():
    values = stored_values()
    if len(values) != MAX_DEGREE:
        raise AssertionError("stored table has %s values, expected %s"
                             % (len(values), MAX_DEGREE))
    for n in range(1, MAX_DEGREE + 1):
        expected = DISCRIMINANTS[n]
        if values.get(ZZ(n)) != expected:
            raise AssertionError("stored discriminant n=%s failed: %s != %s"
                                 % (n, values.get(ZZ(n)), expected))
    print("stored values match the independently checked generator")


def main():
    _key_from_stdin()
    check_identities()
    generator = GeneralPolynomialDiscriminants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill general polynomial discriminants from exact resultants",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        check_stored_values()


if __name__ == "__main__":
    main()
