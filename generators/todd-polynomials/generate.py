"""Todd polynomials -- numberdb.org/T334.

This generator stores the homogeneous Todd polynomials

    Td_n(c1, c2, ...) = [degree n] prod_i x_i / (1 - exp(-x_i)),

where cj is the j-th elementary symmetric polynomial in the Chern roots x_i.
The table starts at n = 1 and stops at n = 7. The entry Td_7 has no c7 term,
so all stored polynomials use at most the six variables c1, ..., c6.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The values are exact rational polynomials. The integrity checks compare the
first four nonconstant components with the standard printed formulas, verify
the root-product definition in seven Chern roots, and check that substituting
the Chern classes of T P^m gives Todd genus 1 for 1 <= m <= 7.
"""

import os
import sys
from itertools import combinations

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T334")
MAX_DEGREE = 7
OUTPUT_VARIABLES = 6

INTERNAL_RING = PolynomialRing(
    QQ, ["c%s" % i for i in range(1, MAX_DEGREE + 1)]
)
INTERNAL_C = INTERNAL_RING.gens()

OUTPUT_RING = PolynomialRing(
    QQ, ["c%s" % i for i in range(1, OUTPUT_VARIABLES + 1)]
)
OUTPUT_C = OUTPUT_RING.gens()

H_RING = PolynomialRing(QQ, "h")
H = H_RING.gen()

ROOT_RING = PolynomialRing(
    QQ, ["x%s" % i for i in range(1, MAX_DEGREE + 1)]
)
ROOTS = ROOT_RING.gens()


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
    value = ZZ(1)
    for k in range(2, int(n) + 1):
        value *= ZZ(k)
    return value


def series_multiply(left, right, degree):
    product = [QQ(0) for _ in range(degree + 1)]
    for i, a in enumerate(left):
        if a == 0:
            continue
        for j, b in enumerate(right):
            if i + j > degree:
                break
            product[i + j] += QQ(a) * QQ(b)
    return product


def todd_series_coefficients(degree):
    """Coefficients of x / (1 - exp(-x)) through x^degree."""
    known = {
        0: QQ(1),
        1: QQ(1) / QQ(2),
        2: QQ(1) / QQ(12),
        3: QQ(0),
        4: -QQ(1) / QQ(720),
        5: QQ(0),
        6: QQ(1) / QQ(30240),
        7: QQ(0),
    }
    return [known.get(k, QQ(0)) for k in range(degree + 1)]


def log_series(series, degree):
    """Formal log of a series whose constant coefficient is 1."""
    if series[0] != 1:
        raise ValueError("log_series needs constant coefficient 1")
    u = list(series)
    u[0] -= QQ(1)
    power = [QQ(1)] + [QQ(0) for _ in range(degree)]
    out = [QQ(0) for _ in range(degree + 1)]
    for exponent in range(1, degree + 1):
        power = series_multiply(power, u, degree)
        sign = QQ(1) if exponent % 2 else -QQ(1)
        scale = sign / QQ(exponent)
        for k in range(degree + 1):
            out[k] += scale * power[k]
    return out


def weighted_degree(exponents):
    return sum((index + 1) * exponent for index, exponent in enumerate(exponents))


def ordinary_degree(exponents):
    return sum(exponents)


def truncate_weighted(polynomial, degree):
    ring = polynomial.parent()
    total = ring.zero()
    variables = ring.gens()
    for exponents, coefficient in polynomial.dict().items():
        if weighted_degree(exponents) <= degree:
            monomial = ring.one()
            for variable, exponent in zip(variables, exponents):
                if exponent:
                    monomial *= variable ** exponent
            total += coefficient * monomial
    return total


def truncate_ordinary(polynomial, degree):
    ring = polynomial.parent()
    total = ring.zero()
    variables = ring.gens()
    for exponents, coefficient in polynomial.dict().items():
        if ordinary_degree(exponents) <= degree:
            monomial = ring.one()
            for variable, exponent in zip(variables, exponents):
                if exponent:
                    monomial *= variable ** exponent
            total += coefficient * monomial
    return total


def homogeneous_weighted(polynomial, degree):
    ring = polynomial.parent()
    total = ring.zero()
    variables = ring.gens()
    for exponents, coefficient in polynomial.dict().items():
        if weighted_degree(exponents) == degree:
            monomial = ring.one()
            for variable, exponent in zip(variables, exponents):
                if exponent:
                    monomial *= variable ** exponent
            total += coefficient * monomial
    return total


def power_sums():
    """Power sums in terms of elementary symmetric polynomials."""
    sums = [INTERNAL_RING.zero()]
    for degree in range(1, MAX_DEGREE + 1):
        total = INTERNAL_RING.zero()
        for j in range(1, degree):
            sign = QQ(1) if j % 2 else -QQ(1)
            total += sign * INTERNAL_C[j - 1] * sums[degree - j]
        sign = QQ(1) if (degree + 1) % 2 == 0 else -QQ(1)
        total += sign * QQ(degree) * INTERNAL_C[degree - 1]
        sums.append(truncate_weighted(total, MAX_DEGREE))
    return sums


def total_todd_polynomial():
    log_q = log_series(todd_series_coefficients(MAX_DEGREE), MAX_DEGREE)
    p = power_sums()
    exponent = INTERNAL_RING.zero()
    for degree in range(1, MAX_DEGREE + 1):
        exponent += log_q[degree] * p[degree]
    exponent = truncate_weighted(exponent, MAX_DEGREE)

    total = INTERNAL_RING.one()
    power = INTERNAL_RING.one()
    for k in range(1, MAX_DEGREE + 1):
        power = truncate_weighted(power * exponent, MAX_DEGREE)
        total = truncate_weighted(total + power / QQ(factorial(k)), MAX_DEGREE)
    return total


TOTAL_TODD = total_todd_polynomial()


def to_output_ring(polynomial):
    total = OUTPUT_RING.zero()
    for exponents, coefficient in polynomial.dict().items():
        if exponents[OUTPUT_VARIABLES] != 0:
            raise AssertionError("c7 term survived: %s" % (polynomial,))
        monomial = OUTPUT_RING.one()
        for variable, exponent in zip(OUTPUT_C, exponents[:OUTPUT_VARIABLES]):
            if exponent:
                monomial *= variable ** exponent
        total += coefficient * monomial
    return total


def todd_polynomial(n):
    return to_output_ring(homogeneous_weighted(TOTAL_TODD, int(n)))


def root_q(root):
    coeffs = todd_series_coefficients(MAX_DEGREE)
    return sum(coeffs[k] * root ** k for k in range(MAX_DEGREE + 1))


def elementary_roots(k):
    if k == 0:
        return ROOT_RING.one()
    total = ROOT_RING.zero()
    for indexes in combinations(range(MAX_DEGREE), k):
        monomial = ROOT_RING.one()
        for index in indexes:
            monomial *= ROOTS[index]
        total += monomial
    return total


def root_product_todd():
    total = ROOT_RING.one()
    for root in ROOTS:
        total = truncate_ordinary(total * root_q(root), MAX_DEGREE)
    return total


def substitute_internal_to_roots(polynomial):
    images = [elementary_roots(k) for k in range(1, MAX_DEGREE + 1)]
    return truncate_ordinary(polynomial(*images), MAX_DEGREE)


def projective_space_substitution(polynomial, dimension):
    images = [
        binomial(dimension + 1, j) * H ** j
        for j in range(1, OUTPUT_VARIABLES + 1)
    ]
    return H_RING(polynomial(*images))


def iter_parameters():
    for n in range(1, MAX_DEGREE + 1):
        yield {"n": ZZ(n)}


def check_identities():
    expected = {
        1: QQ(1) / QQ(2) * OUTPUT_C[0],
        2: (OUTPUT_C[0] ** 2 + OUTPUT_C[1]) / QQ(12),
        3: OUTPUT_C[0] * OUTPUT_C[1] / QQ(24),
        4: (
            -OUTPUT_C[0] ** 4
            + 4 * OUTPUT_C[0] ** 2 * OUTPUT_C[1]
            + 3 * OUTPUT_C[1] ** 2
            + OUTPUT_C[0] * OUTPUT_C[2]
            - OUTPUT_C[3]
        ) / QQ(720),
    }
    for n, value in expected.items():
        found = todd_polynomial(n)
        if found != value:
            raise AssertionError("Td_%s printed formula failed: %s != %s"
                                 % (n, found, value))

    if any(exponents[OUTPUT_VARIABLES] for exponents in
           homogeneous_weighted(TOTAL_TODD, 7).dict()):
        raise AssertionError("Td_7 has a c7 term")

    via_roots = root_product_todd()
    via_components = substitute_internal_to_roots(TOTAL_TODD)
    if via_components != via_roots:
        raise AssertionError("root-product check failed")

    for dimension in range(1, MAX_DEGREE + 1):
        value = projective_space_substitution(
            todd_polynomial(dimension), dimension
        )
        if value[dimension] != 1:
            raise AssertionError(
                "Todd genus of P^%s failed: coefficient is %s"
                % (dimension, value[dimension])
            )

    lengths = [
        (len(str(todd_polynomial(n))), n)
        for n in range(1, MAX_DEGREE + 1)
    ]
    longest = max(lengths, key=lambda item: item[0])
    print("integrity checks passed for %d Todd polynomials" % MAX_DEGREE)
    print("matched the standard formulas for Td_1 through Td_4")
    print("root-product and projective-space checks passed")
    print("longest polynomial has %d characters at n=%s"
          % (longest[0], longest[1]))


class ToddPolynomials(numberdb.Generator):

    table = TABLE
    parameters = ("n",)
    type = "Q[]"
    rigour = "exact"

    def enumerate(self):
        yield from iter_parameters()

    def value(self, params, digits):
        return todd_polynomial(ZZ(params["n"]))


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
        expected = todd_polynomial(n)
        if values.get(ZZ(n)) != expected:
            raise AssertionError("stored Td_%s failed: %s != %s"
                                 % (n, values.get(ZZ(n)), expected))
    print("stored values match the independently checked generator")


def main():
    _key_from_stdin()
    check_identities()
    generator = ToddPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill Todd polynomials from exact characteristic series",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        check_stored_values()


if __name__ == "__main__":
    main()
