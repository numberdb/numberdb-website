"""Discriminants of the trinomials x^n+ax^m+b -- numberdb.org/T383.

For 2 <= n <= 37 and 1 <= m < n, this stores the exact polynomial

    disc(x^n + a*x^m + b)

in the coefficient variables a and b. The discriminant convention is

    (-1)^(n(n-1)/2) * resultant(f, f')

for the monic trinomial f.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The values are exact integer polynomials. The integrity checks compare Swan's
closed formula with exact resultants for n <= 12, compare the printed small
formulas, and compare integer specializations of every stored pair with Sage's
exact univariate discriminant.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T383")
MAX_DEGREE = 37
RESULTANT_CHECK_DEGREE = 12

COEFFICIENT_RING = PolynomialRing(ZZ, ["a", "b"])
A, B = COEFFICIENT_RING.gens()

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
    return ZZ(-1) if (n * (n - 1) // 2) % 2 else ZZ(1)


def swan_discriminant(n, m):
    n = int(n)
    m = int(m)
    d = gcd(n, m)
    middle_sign = ZZ(-1) if (n // d) % 2 else ZZ(1)
    middle = (
        ZZ(n - m) ** ((n - m) // d)
        * ZZ(m) ** (m // d)
        * A ** (n // d)
    )
    inner = ZZ(n) ** (n // d) * B ** ((n - m) // d) - middle_sign * middle
    return (
        sign_for_degree(n)
        * B ** (m - 1)
        * inner ** d
    )


def resultant_discriminant(n, m):
    f = X ** n + A * X ** m + B
    return sign_for_degree(n) * f.resultant(f.derivative())


def iter_parameters(max_degree=MAX_DEGREE):
    for n in range(2, max_degree + 1):
        for m in range(1, n):
            yield {"n": str(n), "m": str(m)}


DISCRIMINANTS = {
    (n, m): swan_discriminant(n, m)
    for n in range(2, MAX_DEGREE + 1)
    for m in range(1, n)
}


def integer_specializations(n, m):
    samples = [
        (ZZ(2), ZZ(3)),
        (ZZ(-1), ZZ(5)),
        (ZZ(3 - (n % 5)), ZZ(-2 - (m % 4))),
    ]
    # Include one vanishing coefficient where the trinomial becomes a binomial;
    # the exact discriminant comparison still applies.
    samples.append((ZZ(0), ZZ(1 + (n + m) % 5)))
    return samples


def integer_trinomial(n, m, a_value, b_value):
    return INTEGER_X ** n + a_value * INTEGER_X ** m + b_value


def evaluate_polynomial(polynomial, a_value, b_value):
    return ZZ(polynomial(a_value, b_value))


def check_printed_formulas(values):
    if values[(2, 1)] != A ** 2 - 4 * B:
        raise ArithmeticError("quadratic formula check failed")
    if values[(3, 1)] != -4 * A ** 3 - 27 * B ** 2:
        raise ArithmeticError("cubic m=1 formula check failed")
    if values[(3, 2)] != -4 * A ** 3 * B - 27 * B ** 2:
        raise ArithmeticError("cubic m=2 formula check failed")


def check_resultant_formula(values, up_to_n=RESULTANT_CHECK_DEGREE):
    for n in range(2, up_to_n + 1):
        for m in range(1, n):
            expected = resultant_discriminant(n, m)
            if values[(n, m)] != expected:
                raise ArithmeticError(
                    "resultant formula failed for n=%s, m=%s" % (n, m)
                )


def check_integer_specializations(values):
    for (n, m), polynomial in values.items():
        for a_value, b_value in integer_specializations(n, m):
            found = evaluate_polynomial(polynomial, a_value, b_value)
            expected = integer_trinomial(n, m, a_value, b_value).discriminant()
            if found != expected:
                raise ArithmeticError(
                    "integer specialization failed for n=%s, m=%s, a=%s, b=%s"
                    % (n, m, a_value, b_value)
                )


def run_integrity_checks(values=None):
    values = DISCRIMINANTS if values is None else values
    check_printed_formulas(values)
    check_resultant_formula(values)
    check_integer_specializations(values)
    longest = max((len(str(value)), n, m) for (n, m), value in values.items())
    print("integrity checks passed for %d trinomial discriminants" % len(values))
    print("resultant checks passed for n<=%d" % RESULTANT_CHECK_DEGREE)
    print(
        "longest polynomial has %d characters at n=%s, m=%s"
        % (longest[0], longest[1], longest[2])
    )
    return values


class TrinomialDiscriminants(numberdb.Generator):

    table = TABLE
    parameters = ("n", "m")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        yield from iter_parameters()

    def value(self, params, digits):
        return DISCRIMINANTS[(int(params["n"]), int(params["m"]))]


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
    numbers = table.get("Numbers") or []
    values = {}
    if isinstance(numbers, dict):
        for n_text, by_m in numbers.items():
            if not isinstance(by_m, dict):
                continue
            for m_text, value in by_m.items():
                if isinstance(value, dict):
                    value = value.get("number")
                values[(int(n_text), int(m_text))] = COEFFICIENT_RING(str(value))
    else:
        for row in numbers:
            params = row.get("params", row)
            value = row.get("number")
            values[(int(params["n"]), int(params["m"]))] = COEFFICIENT_RING(str(value))
    return values


def check_stored_values():
    values = stored_values()
    if len(values) != len(DISCRIMINANTS):
        raise AssertionError(
            "stored table has %s values, expected %s"
            % (len(values), len(DISCRIMINANTS))
        )
    for key, expected in DISCRIMINANTS.items():
        if values.get(key) != expected:
            raise AssertionError(
                "stored discriminant n=%s, m=%s failed" % (key[0], key[1])
            )
    print("stored values match the independently checked generator")


def main():
    _key_from_stdin()
    run_integrity_checks()
    generator = TrinomialDiscriminants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill trinomial discriminants from Swan formula",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        check_stored_values()


if __name__ == "__main__":
    main()
