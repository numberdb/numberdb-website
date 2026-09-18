"""Krawtchouk polynomials K_n(x; p, N) in the Askey normalisation -- numberdb.org/T270.

This generator fills the table of KLS/DLMF Krawtchouk polynomials

    K_n(x; p, N) = _2F_1(-n, -x; -N; 1/p).

The table stores the Askey-scheme normalisation with K_n(0; p, N) = 1,
not the Hamming-scheme rescaling used in coding theory.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import json
import os
import sys
import urllib.request

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T270")

# Measured before filling the draft: these five probabilities and N <= 16 give
# 760 entries. The longest written value has 549 characters, and the entries
# block is 112.4 KB in the dry-run measurement.
P_VALUES = (
    QQ(1) / QQ(4),
    QQ(1) / QQ(3),
    QQ(1) / QQ(2),
    QQ(2) / QQ(3),
    QQ(3) / QQ(4),
)
MAX_N = 16

R = PolynomialRing(QQ, "x")
x = R.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _rising_scalar(argument, count):
    """The scalar Pochhammer symbol (argument)_count over QQ."""
    value = QQ(1)
    argument = QQ(argument)
    for offset in range(count):
        value *= argument + QQ(offset)
    return value


def _falling_binomial(argument, count):
    """The polynomial binomial(argument, count), with exact divisions."""
    value = R.one()
    argument = R(argument)
    for offset in range(count):
        value *= argument - QQ(offset)
        value *= QQ(1) / QQ(offset + 1)
    return R(value)


def krawtchouk_askey(p, N, n):
    """The KLS/DLMF Krawtchouk polynomial K_n(x; p, N)."""
    p = QQ(p)
    N, n = int(N), int(n)
    total = R.one()
    term = R.one()
    inverse_p = QQ(1) / p
    for j in range(n):
        term *= QQ(j - n) * (-x + QQ(j)) * inverse_p
        term *= QQ(1) / ((QQ(j) - QQ(N)) * QQ(j + 1))
        total += term
    return R(total)


class AskeyKrawtchoukPolynomials(numberdb.Generator):
    """Generator for T270, the Askey-normalised Krawtchouk polynomials."""

    table = TABLE
    parameters = ("p", "N", "n")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, max_N=MAX_N):
        for p in P_VALUES:
            for N in range(1, max_N + 1):
                for n in range(N + 1):
                    yield {"p": str(p), "N": str(N), "n": str(n)}

    def value(self, params, digits):
        return krawtchouk_askey(
            QQ(params["p"]),
            int(params["N"]),
            int(params["n"]),
        )


def _computed_values():
    return {
        (p, N, n): krawtchouk_askey(p, N, n)
        for p in P_VALUES
        for N in range(1, MAX_N + 1)
        for n in range(N + 1)
    }


def _hamming_krawtchouk(q, N, n):
    total = R.zero()
    for j in range(n + 1):
        total += (
            QQ((-1) ** j)
            * (QQ(q) - QQ(1)) ** (n - j)
            * _falling_binomial(x, j)
            * _falling_binomial(QQ(N) - x, n - j)
        )
    return R(total)


def _check_hamming_scaling(values):
    for q in (2, 3, 4, 5):
        p = QQ(q - 1) / QQ(q)
        for N in range(1, MAX_N + 1):
            for n in range(N + 1):
                factor = QQ(binomial(N, n)) * QQ(q - 1) ** n
                expected = factor * krawtchouk_askey(p, N, n)
                if _hamming_krawtchouk(q, N, n) != expected:
                    raise ArithmeticError(
                        "Hamming scaling failed at q=%d, N=%d, n=%d" % (q, N, n)
                    )
                if p in P_VALUES and values[(p, N, n)] != krawtchouk_askey(p, N, n):
                    raise ArithmeticError(
                        "stored Krawtchouk value changed at p=%s, N=%d, n=%d"
                        % (p, N, n)
                    )


def _check_generating_function(values):
    Z = PolynomialRing(QQ, "z")
    z = Z.gen()
    for p in P_VALUES:
        a = (QQ(1) - p) / p
        for N in range(1, MAX_N + 1):
            polynomials = [values[(p, N, n)] for n in range(N + 1)]
            for point in range(N + 1):
                rhs = (QQ(1) - a * z) ** point * (QQ(1) + z) ** (N - point)
                for n, polynomial in enumerate(polynomials):
                    expected = QQ(binomial(N, n)) * polynomial(point)
                    if rhs[n] != expected:
                        raise ArithmeticError(
                            "generating function failed at p=%s, N=%d, x=%d, n=%d"
                            % (p, N, point, n)
                        )


def _check_orthogonality(values):
    for p in P_VALUES:
        for N in range(1, MAX_N + 1):
            polynomials = [values[(p, N, n)] for n in range(N + 1)]
            for m, left in enumerate(polynomials):
                for n, right in enumerate(polynomials):
                    total = QQ(0)
                    for point in range(N + 1):
                        total += (
                            QQ(binomial(N, point))
                            * p ** point
                            * (QQ(1) - p) ** (N - point)
                            * left(point)
                            * right(point)
                        )
                    expected = QQ(0)
                    if m == n:
                        expected = ((QQ(1) - p) / p) ** n / QQ(binomial(N, n))
                    if total != expected:
                        raise ArithmeticError(
                            "orthogonality failed at p=%s, N=%d, m=%d, n=%d"
                            % (p, N, m, n)
                        )


def _check_special_value(values):
    for (p, N, n), polynomial in values.items():
        if polynomial(0) != 1:
            raise ArithmeticError("K_n(0) failed at p=%s, N=%d, n=%d" % (p, N, n))


def _check_self_duality(values):
    for p in P_VALUES:
        for N in range(1, MAX_N + 1):
            for n in range(N + 1):
                for point in range(N + 1):
                    if values[(p, N, n)](point) != values[(p, N, point)](n):
                        raise ArithmeticError(
                            "self-duality failed at p=%s, N=%d, n=%d, x=%d"
                            % (p, N, n, point)
                        )


def _check_leading_coefficient(values):
    for (p, N, n), polynomial in values.items():
        expected = p ** (-n) / _rising_scalar(-N, n)
        if polynomial.monomial_coefficient(x ** n) != expected:
            raise ArithmeticError(
                "leading coefficient failed at p=%s, N=%d, n=%d" % (p, N, n)
            )


def run_integrity_checks(values=None):
    if values is None:
        values = _computed_values()
    _check_hamming_scaling(values)
    _check_generating_function(values)
    _check_orthogonality(values)
    _check_special_value(values)
    _check_self_duality(values)
    _check_leading_coefficient(values)


def stored_values():
    """Read the table from the API and parse its stored polynomials."""
    key = os.environ.get("NUMBERDB_API_KEY")
    if not key:
        raise RuntimeError("NUMBERDB_API_KEY is not set")
    request = urllib.request.Request(
        "https://numberdb.org/api/table?id=%s" % TABLE,
        headers={"Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        tree = json.load(response)
    if "error" in tree:
        raise RuntimeError(tree["error"])

    found = {}
    for p_text, by_N in tree.get("Numbers", {}).items():
        for N_text, by_n in by_N.items():
            for n_text, polynomial_text in by_n.items():
                found[(QQ(p_text), int(N_text), int(n_text))] = R(polynomial_text)

    expected_keys = set(_computed_values())
    if set(found) != expected_keys:
        missing = sorted(expected_keys - set(found))[:5]
        extra = sorted(set(found) - expected_keys)[:5]
        raise ArithmeticError("stored key set disagrees, missing=%s extra=%s" % (missing, extra))
    return found


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
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = AskeyKrawtchoukPolynomials()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact Krawtchouk polynomials in the Askey normalisation"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        run_integrity_checks(stored_values())
        print("stored identity checks passed")
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
