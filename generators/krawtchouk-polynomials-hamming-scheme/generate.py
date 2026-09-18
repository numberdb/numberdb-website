"""Krawtchouk polynomials of the Hamming scheme -- numberdb.org/T266.

This generator fills the table of the coding-theoretic Krawtchouk
polynomials

    K_k(x; N, q) = sum_j (-1)^j (q-1)^(k-j) binom(x, j) binom(N-x, k-j),

where q is a prime power, N is the length and k is the degree. This is the
Hamming-scheme normalisation used in coding theory, not the Askey-scheme
normalisation K_k(x; p, N).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T266")

# Measured before filling the draft: q in {2, 3, 4, 5}, N <= 16 gives 608
# entries, the longest written value is 545 characters, and the entries block
# is 84.5 KB in the dry-run measurement.
Q_VALUES = (2, 3, 4, 5)
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


def _falling_binomial(argument, count):
    """The polynomial binomial(argument, count), with exact divisions."""
    value = R.one()
    argument = R(argument)
    for offset in range(count):
        value *= argument - QQ(offset)
        value *= QQ(1) / QQ(offset + 1)
    return R(value)


def _rising_scalar(argument, count):
    """The scalar Pochhammer symbol (argument)_count over QQ."""
    value = QQ(1)
    argument = QQ(argument)
    for offset in range(count):
        value *= argument + QQ(offset)
    return value


def _rising_polynomial(argument, count):
    """The polynomial Pochhammer symbol (argument)_count over QQ[x]."""
    value = R.one()
    argument = R(argument)
    for offset in range(count):
        value *= argument + QQ(offset)
    return R(value)


def krawtchouk_hamming(q, N, k):
    """The Hamming-scheme Krawtchouk polynomial."""
    q, N, k = int(q), int(N), int(k)
    total = R.zero()
    for j in range(k + 1):
        total += (
            QQ((-1) ** j) * QQ(q - 1) ** (k - j)
            * _falling_binomial(x, j)
            * _falling_binomial(N - x, k - j)
        )
    return R(total)


def krawtchouk_askey_at_hamming_p(q, N, k):
    """KLS/DLMF K_k(x; p, N) at p = 1 - 1/q."""
    q, N, k = int(q), int(N), int(k)
    inverse_p = QQ(q) / QQ(q - 1)
    total = R.zero()
    for j in range(k + 1):
        coefficient = (
            _rising_scalar(-k, j) * inverse_p ** j
            / (_rising_scalar(-N, j) * _rising_scalar(1, j))
        )
        total += coefficient * _rising_polynomial(-x, j)
    return R(total)


class HammingSchemeKrawtchoukPolynomials(numberdb.Generator):
    """Generator for T266, the Hamming-scheme Krawtchouk polynomials."""

    table = TABLE
    parameters = ("q", "N", "k")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, max_N=MAX_N):
        for q in Q_VALUES:
            for N in range(1, max_N + 1):
                for k in range(N + 1):
                    yield {"q": str(q), "N": str(N), "k": str(k)}

    def value(self, params, digits):
        return krawtchouk_hamming(int(params["q"]), int(params["N"]),
                                  int(params["k"]))


def _check_generating_function():
    Z = PolynomialRing(QQ, "z")
    z = Z.gen()
    for q in (2, 3, 4):
        for N in (5, 8, 11):
            polys = [krawtchouk_hamming(q, N, k) for k in range(N + 1)]
            for i in range(N + 1):
                rhs = (1 + (q - 1) * z) ** (N - i) * (1 - z) ** i
                for k, polynomial in enumerate(polys):
                    if polynomial(i) != rhs[k]:
                        raise ArithmeticError(
                            "generating function failed at q=%d, N=%d, x=%d, k=%d"
                            % (q, N, i, k))


def _check_orthogonality():
    for q in (2, 3):
        for N in (5, 8):
            polys = [krawtchouk_hamming(q, N, k) for k in range(N + 1)]
            for k, left in enumerate(polys):
                for ell, right in enumerate(polys):
                    total = QQ(0)
                    for i in range(N + 1):
                        total += (
                            QQ(binomial(N, i)) * QQ(q - 1) ** i
                            * left(i) * right(i)
                        )
                    expected = QQ(0)
                    if k == ell:
                        expected = QQ(q) ** N * QQ(binomial(N, k)) * QQ(q - 1) ** k
                    if total != expected:
                        raise ArithmeticError(
                            "orthogonality failed at q=%d, N=%d, k=%d, l=%d"
                            % (q, N, k, ell))


def _check_askey_normalisation():
    for q in Q_VALUES:
        for N in range(1, MAX_N + 1):
            for k in range(N + 1):
                factor = QQ(binomial(N, k)) * QQ(q - 1) ** k
                expected = factor * krawtchouk_askey_at_hamming_p(q, N, k)
                if krawtchouk_hamming(q, N, k) != expected:
                    raise ArithmeticError(
                        "Askey normalisation failed at q=%d, N=%d, k=%d"
                        % (q, N, k))


def _check_binary_small_cases():
    for N in range(1, MAX_N + 1):
        expected = [
            R.one(),
            -2 * x + N,
            2 * x ** 2 - 2 * N * x + binomial(N, 2),
            -QQ(4) / QQ(3) * x ** 3 + 2 * N * x ** 2
            - (N * N - N + QQ(2) / QQ(3)) * x + binomial(N, 3),
        ]
        for k in range(min(3, N) + 1):
            if krawtchouk_hamming(2, N, k) != expected[k]:
                raise ArithmeticError(
                    "binary small case failed at N=%d, k=%d" % (N, k))


def run_integrity_checks():
    _check_generating_function()
    _check_orthogonality()
    _check_askey_normalisation()
    _check_binary_small_cases()


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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = HammingSchemeKrawtchoukPolynomials()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact Hamming-scheme Krawtchouk polynomials"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
