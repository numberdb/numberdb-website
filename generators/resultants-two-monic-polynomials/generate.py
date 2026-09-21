"""Resultants of two monic polynomials -- numberdb.org/T384.

For m, n >= 1 with m + n <= 6, this stores the exact polynomial

    Res(x^m + a_{m-1} x^{m-1} + ... + a_0,
        x^n + b_{n-1} x^{n-1} + ... + b_0).

The resultant convention is

    product(g(alpha) for f(alpha) = 0),

counting roots with multiplicity. The range is the complete antidiagonal
m + n <= 6 because the next antidiagonal would use seven coefficient variables,
beyond NumberDB's polynomial-search limit. The measured longest stored entry
has 476 characters at (m, n) = (3, 3).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          NUMBERDB_ASSISTED_BY=codex-cli agents/sage.sh generate.py

The values are exact integer polynomials. The integrity checks compare the
computed resultants with the root-product definition, with an independently
assembled Sylvester determinant, with the printed small formulas, and with
integer specializations over ZZ[x].
"""

import os
import sys
from itertools import combinations, permutations

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T384")
MAX_TOTAL_DEGREE = 6


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def coefficient_ring(m, n):
    return PolynomialRing(
        ZZ, ["a%s" % i for i in range(m)] + ["b%s" % j for j in range(n)]
    )


def polynomial_pair(m, n):
    ring = coefficient_ring(m, n)
    gens = ring.gens()
    a = gens[:m]
    b = gens[m:]
    poly_ring = PolynomialRing(ring, "x")
    x = poly_ring.gen()
    f = x ** m + sum(a[i] * x ** i for i in range(m))
    g = x ** n + sum(b[j] * x ** j for j in range(n))
    return ring, a, b, poly_ring, x, f, g


def resultant_polynomial(m, n):
    _, _, _, _, _, f, g = polynomial_pair(m, n)
    return f.resultant(g)


def iter_parameters(max_total=MAX_TOTAL_DEGREE):
    for total in range(2, max_total + 1):
        for m in range(1, total):
            n = total - m
            yield {"m": str(m), "n": str(n)}


RESULTANTS = {
    (int(params["m"]), int(params["n"])): resultant_polynomial(
        int(params["m"]), int(params["n"])
    )
    for params in iter_parameters()
}


def _product(factors, ring):
    total = ring.one()
    for factor in factors:
        total *= factor
    return total


def elementary_symmetric(values, k, ring):
    if k == 0:
        return ring.one()
    total = ring.zero()
    for indexes in combinations(range(len(values)), k):
        total += _product((values[i] for i in indexes), ring)
    return total


def root_formula_images(m, n, ring, roots, b_variables):
    images = []
    for i in range(m):
        k = m - i
        sign = ZZ(1) if k % 2 == 0 else ZZ(-1)
        images.append(sign * elementary_symmetric(roots, k, ring))
    images.extend(b_variables)
    return images


def check_root_formula(values):
    for (m, n), resultant in values.items():
        names = ["alpha%s" % i for i in range(1, m + 1)] + [
            "b%s" % j for j in range(n)
        ]
        target_ring = PolynomialRing(ZZ, names)
        roots = target_ring.gens()[:m]
        b_variables = target_ring.gens()[m:]
        images = root_formula_images(m, n, target_ring, roots, b_variables)
        found = resultant.parent().hom(images, target_ring)(resultant)
        expected = _product(
            (
                alpha ** n
                + sum(b_variables[j] * alpha ** j for j in range(n))
                for alpha in roots
            ),
            target_ring,
        )
        if found != expected:
            raise ArithmeticError("root-product formula failed for m=%s, n=%s" % (m, n))


def permutation_sign(permutation):
    inversions = 0
    for i in range(len(permutation)):
        for j in range(i + 1, len(permutation)):
            if permutation[i] > permutation[j]:
                inversions += 1
    return ZZ(-1) if inversions % 2 else ZZ(1)


def determinant_by_permutations(rows, ring):
    total = ring.zero()
    size = len(rows)
    for perm in permutations(range(size)):
        term = ring.one()
        for i, j in enumerate(perm):
            term *= rows[i][j]
        total += permutation_sign(perm) * term
    return total


def sylvester_resultant(m, n):
    ring, a, b, _, _, _, _ = polynomial_pair(m, n)
    zero = ring.zero()
    f_desc = [ring.one()] + [a[i] for i in range(m - 1, -1, -1)]
    g_desc = [ring.one()] + [b[j] for j in range(n - 1, -1, -1)]

    rows = []
    for shift in range(n):
        rows.append([zero] * shift + f_desc + [zero] * (n - 1 - shift))
    for shift in range(m):
        rows.append([zero] * shift + g_desc + [zero] * (m - 1 - shift))
    return determinant_by_permutations(rows, ring)


def check_sylvester_formula(values):
    for key, resultant in values.items():
        expected = sylvester_resultant(*key)
        if resultant != expected:
            raise ArithmeticError("Sylvester determinant failed for m=%s, n=%s" % key)


def check_printed_formulas(values):
    ring11 = coefficient_ring(1, 1)
    a0, b0 = ring11.gens()
    if values[(1, 1)] != b0 - a0:
        raise ArithmeticError("linear formula check failed")

    ring12 = coefficient_ring(1, 2)
    a0, b0, b1 = ring12.gens()
    if values[(1, 2)] != a0 ** 2 - a0 * b1 + b0:
        raise ArithmeticError("linear-quadratic formula check failed")

    ring21 = coefficient_ring(2, 1)
    a0, a1, b0 = ring21.gens()
    if values[(2, 1)] != b0 ** 2 - a1 * b0 + a0:
        raise ArithmeticError("quadratic-linear formula check failed")


def integer_samples(m, n):
    samples = []
    for seed in range(4):
        a_values = [
            ZZ(((i + 2) * (seed + 3) + m + seed * seed) % 11 - 5)
            for i in range(m)
        ]
        b_values = [
            ZZ(((j + 3) * (seed + 2) + n + 2 * seed) % 13 - 6)
            for j in range(n)
        ]
        samples.append((a_values, b_values))
    samples.append(([ZZ(0) for _ in range(m)], [ZZ(0) for _ in range(n)]))
    return samples


INTEGER_X_RING = PolynomialRing(ZZ, "x")
INTEGER_X = INTEGER_X_RING.gen()


def integer_polynomial(coefficients):
    degree = len(coefficients)
    return INTEGER_X ** degree + sum(coefficients[i] * INTEGER_X ** i
                                     for i in range(degree))


def check_integer_specializations(values):
    for (m, n), resultant in values.items():
        source_ring = resultant.parent()
        for a_values, b_values in integer_samples(m, n):
            found = source_ring.hom(a_values + b_values, ZZ)(resultant)
            expected = integer_polynomial(a_values).resultant(
                integer_polynomial(b_values)
            )
            if found != expected:
                raise ArithmeticError(
                    "integer specialization failed for m=%s, n=%s, a=%s, b=%s"
                    % (m, n, a_values, b_values)
                )


def run_integrity_checks(values=None):
    values = RESULTANTS if values is None else values
    check_root_formula(values)
    check_sylvester_formula(values)
    check_printed_formulas(values)
    check_integer_specializations(values)
    longest = max((len(str(value)), key) for key, value in values.items())
    print("integrity checks passed for %d monic resultants" % len(values))
    print("root-product, Sylvester, and integer-specialization checks passed")
    print("longest polynomial has %d characters at m=%s, n=%s"
          % (longest[0], longest[1][0], longest[1][1]))
    return values


class ResultantsOfTwoMonicPolynomials(numberdb.Generator):

    table = TABLE
    parameters = ("m", "n")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        yield from iter_parameters()

    def value(self, params, digits):
        return RESULTANTS[(int(params["m"]), int(params["n"]))]


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
        for m_text, by_n in numbers.items():
            if not isinstance(by_n, dict):
                continue
            for n_text, value in by_n.items():
                if isinstance(value, dict):
                    value = value.get("number")
                m = int(m_text)
                n = int(n_text)
                values[(m, n)] = coefficient_ring(m, n)(str(value))
    else:
        for row in numbers:
            params = row.get("params", row)
            value = row.get("number")
            m = int(params["m"])
            n = int(params["n"])
            values[(m, n)] = coefficient_ring(m, n)(str(value))
    return values


def check_stored_values():
    values = stored_values()
    if len(values) != len(RESULTANTS):
        raise AssertionError(
            "stored table has %s values, expected %s"
            % (len(values), len(RESULTANTS))
        )
    for key, expected in RESULTANTS.items():
        if values.get(key) != expected:
            raise AssertionError(
                "stored resultant m=%s, n=%s failed" % (key[0], key[1])
            )
    print("stored values match the independently checked generator")


def main():
    _key_from_stdin()
    run_integrity_checks()
    generator = ResultantsOfTwoMonicPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill monic polynomial resultants from exact resultants",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        check_stored_values()


if __name__ == "__main__":
    main()
