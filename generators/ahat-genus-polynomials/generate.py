"""A-hat genus polynomials -- numberdb.org/T337.

This generator stores the homogeneous A-hat genus polynomials

    Ahat_n(p1, p2, ...) = [degree n] prod_i (sqrt(x_i) / 2) / sinh(sqrt(x_i) / 2),

where pj is the j-th elementary symmetric polynomial in the Pontryagin roots
x_i. The table starts at n = 1 and stops at n = 6, because Ahat_7 has a
nonzero p7 term and the database searches polynomials in at most six variables.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The values are exact rational polynomials. The integrity checks compare the
first four nonconstant components with standard printed formulas, verify the
Pontryagin-root definition in seven roots, and check the K3 surface and HP^2
specialisations of the A-hat genus.
"""

import os
import sys
from itertools import combinations

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T337")
MAX_DEGREE = 6
CHECK_DEGREE = 7

OUTPUT_RING = PolynomialRing(
    QQ, ["p%s" % i for i in range(1, MAX_DEGREE + 1)]
)
OUTPUT_P = OUTPUT_RING.gens()

CHECK_RING = PolynomialRing(
    QQ, ["p%s" % i for i in range(1, CHECK_DEGREE + 1)]
)
CHECK_P = CHECK_RING.gens()

ROOT_RING = PolynomialRing(
    QQ, ["x%s" % i for i in range(1, CHECK_DEGREE + 1)]
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


def bernoulli_plus(n):
    """Bernoulli number with B_1 = +1/2. Only even values are used."""
    values = [QQ(0) for _ in range(int(n) + 1)]
    for m in range(int(n) + 1):
        values[m] = QQ(1) / QQ(m + 1)
        for j in range(m, 0, -1):
            values[j - 1] = QQ(j) * (values[j - 1] - values[j])
    return values[0]


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


def ahat_series_coefficients(degree):
    """Coefficients of (sqrt(x) / 2) / sinh(sqrt(x) / 2)."""
    return [
        (QQ(2) ** (1 - 2 * k) - QQ(1)) * bernoulli_plus(2 * k) / factorial(2 * k)
        for k in range(int(degree) + 1)
    ]


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


def monomial_from_exponents(ring, variables, exponents):
    monomial = ring.one()
    for variable, exponent in zip(variables, exponents):
        if exponent:
            monomial *= variable ** exponent
    return monomial


def truncate_weighted(polynomial, degree):
    ring = polynomial.parent()
    variables = ring.gens()
    total = ring.zero()
    for exponents, coefficient in polynomial.dict().items():
        if weighted_degree(exponents) <= degree:
            total += coefficient * monomial_from_exponents(
                ring, variables, exponents
            )
    return total


def truncate_ordinary(polynomial, degree):
    ring = polynomial.parent()
    variables = ring.gens()
    total = ring.zero()
    for exponents, coefficient in polynomial.dict().items():
        if ordinary_degree(exponents) <= degree:
            total += coefficient * monomial_from_exponents(
                ring, variables, exponents
            )
    return total


def homogeneous_weighted(polynomial, degree):
    ring = polynomial.parent()
    variables = ring.gens()
    total = ring.zero()
    for exponents, coefficient in polynomial.dict().items():
        if weighted_degree(exponents) == degree:
            total += coefficient * monomial_from_exponents(
                ring, variables, exponents
            )
    return total


def power_sums(ring, variables, degree):
    """Power sums in terms of elementary symmetric polynomials."""
    sums = [ring.zero()]
    for m in range(1, int(degree) + 1):
        total = ring.zero()
        for j in range(1, m):
            sign = QQ(1) if j % 2 else -QQ(1)
            total += sign * variables[j - 1] * sums[m - j]
        sign = QQ(1) if (m + 1) % 2 == 0 else -QQ(1)
        total += sign * QQ(m) * variables[m - 1]
        sums.append(truncate_weighted(total, degree))
    return sums


def total_ahat_polynomial():
    log_q = log_series(ahat_series_coefficients(CHECK_DEGREE), CHECK_DEGREE)
    p = power_sums(CHECK_RING, CHECK_P, CHECK_DEGREE)
    exponent = CHECK_RING.zero()
    for degree in range(1, CHECK_DEGREE + 1):
        exponent += log_q[degree] * p[degree]
    exponent = truncate_weighted(exponent, CHECK_DEGREE)

    total = CHECK_RING.one()
    power = CHECK_RING.one()
    for k in range(1, CHECK_DEGREE + 1):
        power = truncate_weighted(power * exponent, CHECK_DEGREE)
        total = truncate_weighted(total + power / factorial(k), CHECK_DEGREE)
    return total


TOTAL_AHAT = total_ahat_polynomial()


def to_output_ring(polynomial):
    total = OUTPUT_RING.zero()
    for exponents, coefficient in polynomial.dict().items():
        if any(exponents[MAX_DEGREE:]):
            raise AssertionError("term beyond p6 survived: %s" % (polynomial,))
        monomial = OUTPUT_RING.one()
        for variable, exponent in zip(OUTPUT_P, exponents[:MAX_DEGREE]):
            if exponent:
                monomial *= variable ** exponent
        total += coefficient * monomial
    return total


def ahat_polynomial(n):
    return to_output_ring(homogeneous_weighted(TOTAL_AHAT, int(n)))


def root_q(root):
    coeffs = ahat_series_coefficients(CHECK_DEGREE)
    return sum(coeffs[k] * root ** k for k in range(CHECK_DEGREE + 1))


def elementary_roots(k):
    if k == 0:
        return ROOT_RING.one()
    total = ROOT_RING.zero()
    for indexes in combinations(range(CHECK_DEGREE), int(k)):
        monomial = ROOT_RING.one()
        for index in indexes:
            monomial *= ROOTS[index]
        total += monomial
    return total


ROOT_ELEMENTARY = [elementary_roots(k) for k in range(1, CHECK_DEGREE + 1)]


def root_product_ahat():
    total = ROOT_RING.one()
    for root in ROOTS:
        total = truncate_ordinary(total * root_q(root), CHECK_DEGREE)
    return total


def substitute_check_to_roots(polynomial):
    return truncate_ordinary(ROOT_RING(polynomial(*ROOT_ELEMENTARY)), CHECK_DEGREE)


def k3_substitution(polynomial):
    """Use p1(K3) = -48 times the fundamental class."""
    return polynomial(-48, 0, 0, 0, 0, 0)


def hp2_substitution(polynomial):
    """Use p1(HP^2) = 2h and p2(HP^2) = 7h^2."""
    images = [2 * H, 7 * H ** 2, 0, 0, 0, 0]
    return H_RING(polynomial(*images))


def iter_parameters():
    for n in range(1, MAX_DEGREE + 1):
        yield {"n": ZZ(n)}


def check_identities():
    expected = {
        1: -OUTPUT_P[0] / QQ(24),
        2: (7 * OUTPUT_P[0] ** 2 - 4 * OUTPUT_P[1]) / QQ(5760),
        3: (
            -16 * OUTPUT_P[2]
            + 44 * OUTPUT_P[0] * OUTPUT_P[1]
            - 31 * OUTPUT_P[0] ** 3
        ) / QQ(967680),
        4: (
            -192 * OUTPUT_P[3]
            + 512 * OUTPUT_P[0] * OUTPUT_P[2]
            + 208 * OUTPUT_P[1] ** 2
            - 904 * OUTPUT_P[0] ** 2 * OUTPUT_P[1]
            + 381 * OUTPUT_P[0] ** 4
        ) / QQ(464486400),
    }
    for n, value in expected.items():
        found = ahat_polynomial(n)
        if found != value:
            raise AssertionError("Ahat_%s printed formula failed: %s != %s"
                                 % (n, found, value))

    ahat7 = homogeneous_weighted(TOTAL_AHAT, 7)
    p7_coefficient = ahat7.monomial_coefficient(CHECK_P[6])
    if p7_coefficient == 0:
        raise AssertionError("Ahat_7 unexpectedly has no p7 term")

    via_roots = root_product_ahat()
    via_components = substitute_check_to_roots(TOTAL_AHAT)
    if via_components != via_roots:
        raise AssertionError("root-product check failed")

    k3_value = k3_substitution(ahat_polynomial(1))
    if k3_value != 2:
        raise AssertionError("K3 A-hat genus failed: %s != 2" % (k3_value,))

    hp2_value = hp2_substitution(ahat_polynomial(2))
    if hp2_value[2] != 0:
        raise AssertionError("HP^2 A-hat genus failed: %s != 0" % (hp2_value[2],))

    lengths = [
        (len(str(ahat_polynomial(n))), n)
        for n in range(1, MAX_DEGREE + 1)
    ]
    longest = max(lengths, key=lambda item: item[0])
    print("integrity checks passed for %d A-hat genus polynomials"
          % MAX_DEGREE)
    print("matched the printed formulas for Ahat_1 through Ahat_4")
    print("root-product, K3 and HP^2 checks passed")
    print("Ahat_7 has p7 coefficient %s" % p7_coefficient)
    print("longest polynomial has %d characters at n=%s"
          % (longest[0], longest[1]))


class AhatGenusPolynomials(numberdb.Generator):

    table = TABLE
    parameters = ("n",)
    type = "Q[]"
    rigour = "exact"

    def enumerate(self):
        yield from iter_parameters()

    def value(self, params, digits):
        return ahat_polynomial(ZZ(params["n"]))


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
        expected = ahat_polynomial(n)
        if values.get(ZZ(n)) != expected:
            raise AssertionError("stored Ahat_%s failed: %s != %s"
                                 % (n, values.get(ZZ(n)), expected))
    print("stored values match the independently checked generator")


def main():
    _key_from_stdin()
    check_identities()
    generator = AhatGenusPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill A-hat genus polynomials from exact characteristic series",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        check_stored_values()


if __name__ == "__main__":
    main()
