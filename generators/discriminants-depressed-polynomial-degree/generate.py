"""Discriminants of the depressed polynomial of degree n -- numberdb.org/T382

For n = 2, ..., 6 this stores the discriminant of

    f_n(x) = x^n + a_{n-2} x^{n-2} + ... + a_1 x + a_0.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The discriminant is computed from the exact resultant formula for a monic
polynomial. The integrity checks compare the rows with the root-product
definition on sum-zero roots, with the stored general-polynomial discriminants
where those rows exist, and with Sage's univariate discriminant at integer
specializations.
"""

import os
import sys
from itertools import combinations

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T382")
UP_TO_N = 6
GENERAL_TABLE = "T381"


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def coefficient_ring(n):
    return PolynomialRing(ZZ, ["a%s" % i for i in range(n - 1)])


def discriminant_polynomial(n):
    coefficients = coefficient_ring(n).gens()
    base = coefficients[0].parent()
    poly_ring = PolynomialRing(base, "x")
    x = poly_ring.gen()
    f = x ** n + sum(coefficients[i] * x ** i for i in range(n - 1))
    sign = -1 if (n * (n - 1) // 2) % 2 else 1
    return sign * f.resultant(f.derivative())


def elementary_symmetric(values, k, ring):
    if k == 0:
        return ring(1)
    total = ring(0)
    for terms in combinations(values, k):
        product = ring(1)
        for term in terms:
            product *= term
        total += product
    return total


def root_product_polynomial(n):
    ring = PolynomialRing(ZZ, ["r%s" % i for i in range(n - 1)])
    roots = list(ring.gens())
    roots.append(-sum(roots))

    product = ring(1)
    for i, alpha in enumerate(roots):
        for beta in roots[i + 1:]:
            product *= (alpha - beta) ** 2
    return ring, roots, product


def check_root_product(n):
    ring, roots, product = root_product_polynomial(n)
    discriminant = discriminant_polynomial(n)
    images = [
        (-1) ** (n - i) * elementary_symmetric(roots, n - i, ring)
        for i in range(n - 1)
    ]
    mapped = discriminant.parent().hom(images, ring)(discriminant)
    if mapped != product:
        raise ArithmeticError("root-product check failed at n=%s" % n)


def check_small_formulas(values):
    ring2 = coefficient_ring(2)
    a0 = ring2.gens()[0]
    if values[2] != -4 * a0:
        raise ArithmeticError("quadratic formula check failed")

    ring3 = coefficient_ring(3)
    a0, a1 = ring3.gens()
    if values[3] != -4 * a1 ** 3 - 27 * a0 ** 2:
        raise ArithmeticError("cubic formula check failed")


def integer_samples(n):
    samples = []
    for seed in range(5):
        samples.append([
            ZZ(((i + 2) * (seed + 3) + seed * seed) % 9 - 4)
            for i in range(n - 1)
        ])
    samples.append([ZZ(0) for _ in range(n - 1)])
    return samples


def check_integer_specializations(values):
    poly_ring = PolynomialRing(ZZ, "x")
    x = poly_ring.gen()
    for n, discriminant in values.items():
        coefficient_parent = discriminant.parent()
        for sample in integer_samples(n):
            specialized = coefficient_parent.hom(sample, ZZ)(discriminant)
            f = x ** n + sum(sample[i] * x ** i for i in range(n - 1))
            expected = f.discriminant()
            if specialized != expected:
                raise ArithmeticError(
                    "integer specialization failed at n=%s, sample=%s"
                    % (n, sample)
                )


def check_against_general_table(values):
    try:
        general = numberdb.table(GENERAL_TABLE)
    except Exception as trouble:  # noqa: BLE001
        print("skipped stored T381 comparison: %s" % trouble)
        return

    for n in range(2, min(5, UP_TO_N) + 1):
        text = general["Numbers"][str(n)]
        general_ring = PolynomialRing(ZZ, ["a%s" % i for i in range(n + 1)])
        general_discriminant = general_ring(text)
        target_ring = values[n].parent()
        target_gens = list(target_ring.gens())
        images = target_gens + [target_ring(0), target_ring(1)]
        specialized = general_ring.hom(images, target_ring)(general_discriminant)
        if specialized != values[n]:
            raise ArithmeticError("stored T381 specialization failed at n=%s" % n)


def run_integrity_checks(up_to_n=UP_TO_N):
    values = {n: discriminant_polynomial(n) for n in range(2, up_to_n + 1)}
    check_small_formulas(values)
    for n in values:
        check_root_product(n)
    check_integer_specializations(values)
    check_against_general_table(values)
    longest = max((len(str(value)), n) for n, value in values.items())
    print("integrity checks passed for depressed discriminants n=2..%s" % up_to_n)
    print("longest stored discriminant has %d characters at n=%s" % longest)
    return values


class DepressedPolynomialDiscriminants(numberdb.Generator):

    table = TABLE
    parameters = ("n",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, up_to_n=UP_TO_N):
        for n in range(2, up_to_n + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return {"number": discriminant_polynomial(int(params["n"]))}


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
    generator = DepressedPolynomialDiscriminants()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill depressed polynomial discriminants from exact resultants",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
