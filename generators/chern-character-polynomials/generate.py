"""Chern character polynomials -- numberdb.org/T335.

This generator stores the homogeneous Chern character polynomials

    ch_n(c1, c2, ...) = p_n(c1, c2, ...) / n!,

where p_n is the n-th power sum in the Chern roots, written in the elementary
symmetric polynomials c_j by Newton's identities. The table starts at n = 1
and stops at n = 6, because ch_7 has a nonzero c7 term and the database
searches polynomials in at most six variables.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The values are exact rational polynomials. The integrity checks compare the
first three nonconstant components with the printed Chern-character formula,
verify the Chern-root definition in six roots, and check the projective-space
specialisation ch_n(T P^m) = (m+1)h^n/n! for 1 <= n <= m <= 6.
"""

import os
import sys
from itertools import combinations

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T335")
MAX_DEGREE = 6
CHECK_DEGREE = 7

OUTPUT_RING = PolynomialRing(
    QQ, ["c%s" % i for i in range(1, MAX_DEGREE + 1)]
)
OUTPUT_C = OUTPUT_RING.gens()

CHECK_RING = PolynomialRing(
    QQ, ["c%s" % i for i in range(1, CHECK_DEGREE + 1)]
)
CHECK_C = CHECK_RING.gens()

ROOT_RING = PolynomialRing(
    QQ, ["x%s" % i for i in range(1, MAX_DEGREE + 1)]
)
ROOTS = ROOT_RING.gens()

H_RING = PolynomialRing(QQ, "h")
H = H_RING.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def factorial(n):
    value = QQ(1)
    for k in range(2, int(n) + 1):
        value *= QQ(k)
    return value


def power_sums(ring, variables, degree):
    """Power sums in terms of elementary symmetric polynomials."""
    sums = {}
    for m in range(1, int(degree) + 1):
        total = ring.zero()
        for j in range(1, m):
            sign = QQ(1) if j % 2 else -QQ(1)
            total += sign * variables[j - 1] * sums[m - j]
        sign = QQ(1) if (m + 1) % 2 == 0 else -QQ(1)
        total += sign * QQ(m) * variables[m - 1]
        sums[m] = total
    return sums


def to_output_ring(polynomial):
    total = OUTPUT_RING.zero()
    for exponents, coefficient in polynomial.dict().items():
        if any(exponents[MAX_DEGREE:]):
            raise AssertionError("term beyond c6 survived: %s" % (polynomial,))
        monomial = OUTPUT_RING.one()
        for variable, exponent in zip(OUTPUT_C, exponents[:MAX_DEGREE]):
            if exponent:
                monomial *= variable ** exponent
        total += coefficient * monomial
    return total


CHECK_POWER_SUMS = power_sums(CHECK_RING, CHECK_C, CHECK_DEGREE)


def chern_character_polynomial(n):
    n = int(n)
    return to_output_ring(CHECK_POWER_SUMS[n] / factorial(n))


def elementary_roots(k):
    if k == 0:
        return ROOT_RING.one()
    total = ROOT_RING.zero()
    for indexes in combinations(range(MAX_DEGREE), int(k)):
        monomial = ROOT_RING.one()
        for index in indexes:
            monomial *= ROOTS[index]
        total += monomial
    return total


ROOT_ELEMENTARY = [elementary_roots(k) for k in range(1, MAX_DEGREE + 1)]


def root_specialisation(polynomial):
    return ROOT_RING(polynomial(*ROOT_ELEMENTARY))


def projective_space_substitution(polynomial, dimension):
    images = [
        binomial(dimension + 1, j) * H ** j
        for j in range(1, MAX_DEGREE + 1)
    ]
    return H_RING(polynomial(*images))


def iter_parameters():
    for n in range(1, MAX_DEGREE + 1):
        yield {"n": ZZ(n)}


def check_identities():
    expected = {
        1: OUTPUT_C[0],
        2: (OUTPUT_C[0] ** 2 - 2 * OUTPUT_C[1]) / QQ(2),
        3: (
            OUTPUT_C[0] ** 3
            - 3 * OUTPUT_C[0] * OUTPUT_C[1]
            + 3 * OUTPUT_C[2]
        ) / QQ(6),
    }
    for n, value in expected.items():
        found = chern_character_polynomial(n)
        if found != value:
            raise AssertionError("ch_%s printed formula failed: %s != %s"
                                 % (n, found, value))

    ch7 = CHECK_POWER_SUMS[7] / factorial(7)
    c7_coefficient = ch7.monomial_coefficient(CHECK_C[6])
    if c7_coefficient == 0:
        raise AssertionError("ch_7 unexpectedly has no c7 term")

    for n in range(1, MAX_DEGREE + 1):
        found = root_specialisation(chern_character_polynomial(n))
        expected_root = sum(root ** n for root in ROOTS) / factorial(n)
        if found != expected_root:
            raise AssertionError("root check failed for ch_%s: %s != %s"
                                 % (n, found, expected_root))

    for dimension in range(1, MAX_DEGREE + 1):
        for n in range(1, dimension + 1):
            value = projective_space_substitution(
                chern_character_polynomial(n), dimension
            )
            expected_coeff = QQ(dimension + 1) / factorial(n)
            if value[n] != expected_coeff:
                raise AssertionError(
                    "ch_%s(T P^%s) failed: coefficient is %s, expected %s"
                    % (n, dimension, value[n], expected_coeff)
                )

    lengths = [
        (len(str(chern_character_polynomial(n))), n)
        for n in range(1, MAX_DEGREE + 1)
    ]
    longest = max(lengths, key=lambda item: item[0])
    print("integrity checks passed for %d Chern character polynomials"
          % MAX_DEGREE)
    print("matched the printed formulas for ch_1 through ch_3")
    print("root-definition and projective-space checks passed")
    print("ch_7 has c7 coefficient %s" % c7_coefficient)
    print("longest polynomial has %d characters at n=%s"
          % (longest[0], longest[1]))


class ChernCharacterPolynomials(numberdb.Generator):

    table = TABLE
    parameters = ("n",)
    type = "Q[]"
    rigour = "exact"

    def enumerate(self):
        yield from iter_parameters()

    def value(self, params, digits):
        return chern_character_polynomial(ZZ(params["n"]))


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
            values[ZZ(key)] = OUTPUT_RING(str(value))
    elif isinstance(numbers, list):
        for row in numbers:
            params = row.get("params", row)
            value = row.get("number")
            values[ZZ(params["n"])] = OUTPUT_RING(str(value))
    return values


def check_stored_values():
    values = stored_values()
    if len(values) != MAX_DEGREE:
        raise AssertionError("stored table has %s values, expected %s"
                             % (len(values), MAX_DEGREE))
    for n in range(1, MAX_DEGREE + 1):
        expected = chern_character_polynomial(n)
        if values.get(ZZ(n)) != expected:
            raise AssertionError("stored ch_%s failed: %s != %s"
                                 % (n, values.get(ZZ(n)), expected))
    print("stored values match the independently checked generator")


def main():
    _key_from_stdin()
    check_identities()
    generator = ChernCharacterPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill Chern character polynomials from Newton identities",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        check_stored_values()


if __name__ == "__main__":
    main()
