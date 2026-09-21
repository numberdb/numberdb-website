"""Zeros of the Krawtchouk polynomials K_n(x;p,N) -- numberdb.org/T369.

This generator fills the draft table of zeros of the Askey-normalised
Krawtchouk polynomials

    K_n(x; p, N) = _2F_1(-n, -x; -N; 1/p).

The grid inherits the p and N values from numberdb.org/T270. The full zero grid
for every n <= N is too large for a first table, so this draft keeps the
nonconstant degrees n <= 4 and every zero of each retained polynomial.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import json
import os
import sys
import urllib.request
from functools import lru_cache

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = os.environ.get("NUMBERDB_TABLE", "T369")
WORKING_GUARD = 128

P_VALUES = (
    QQ(1) / QQ(4),
    QQ(1) / QQ(3),
    QQ(1) / QQ(2),
    QQ(2) / QQ(3),
    QQ(3) / QQ(4),
)
MAX_N = 16
MAX_DEGREE = 4

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


def hamming_krawtchouk(q, N, n):
    """The Hamming-scheme Krawtchouk polynomial, computed independently."""
    q, N, n = int(q), int(N), int(n)
    total = R.zero()
    for j in range(n + 1):
        total += (
            QQ((-1) ** j)
            * QQ(q - 1) ** (n - j)
            * _falling_binomial(x, j)
            * _falling_binomial(QQ(N) - x, n - j)
        )
    return R(total)


@lru_cache(maxsize=None)
def roots_for(p_text, N, n, digits):
    """The isolated roots of K_n(x;p,N), in increasing order."""
    p = QQ(p_text)
    N, n = int(N), int(n)
    precision = numberdb.bits(digits, losing=WORKING_GUARD)
    interval_field = RealIntervalField(precision)
    polynomial = krawtchouk_askey(p, N, n)
    roots = polynomial.roots(interval_field, multiplicities=True)
    roots = sorted(roots, key=lambda pair: pair[0].lower())

    if len(roots) != n:
        raise ArithmeticError(
            "expected %d roots at p=%s, N=%d, n=%d; got %d"
            % (n, p, N, n, len(roots))
        )

    out = []
    for root, multiplicity in roots:
        if multiplicity != 1:
            raise ArithmeticError(
                "multiple root at p=%s, N=%d, n=%d: %s"
                % (p, N, n, root)
            )
        if not (root.lower() > 0 and root.upper() < N):
            raise ArithmeticError(
                "root outside (0,N) at p=%s, N=%d, n=%d: %s"
                % (p, N, n, root)
            )
        if not polynomial(interval_field(root)).contains_zero():
            raise ArithmeticError(
                "root interval does not contain a zero at p=%s, N=%d, n=%d: %s"
                % (p, N, n, root)
            )
        out.append(root)
    return tuple(out)


class KrawtchoukPolynomialZeros(numberdb.Generator):
    """Generator for T369, the zeros of the Krawtchouk polynomials."""

    table = TABLE
    parameters = ("p", "N", "n", "k")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_N=MAX_N):
        for p in P_VALUES:
            for N in range(1, max_N + 1):
                for n in range(1, min(N, MAX_DEGREE) + 1):
                    for k in range(1, n + 1):
                        yield {"p": str(p), "N": str(N), "n": str(n), "k": str(k)}

    def value(self, params, digits):
        roots = roots_for(params["p"], int(params["N"]), int(params["n"]), digits)
        return roots[int(params["k"]) - 1]


def _check_generating_function():
    Z = PolynomialRing(QQ, "z")
    z = Z.gen()
    for p in P_VALUES:
        a = (QQ(1) - p) / p
        for N in range(1, MAX_N + 1):
            for point in range(N + 1):
                rhs = (QQ(1) - a * z) ** point * (QQ(1) + z) ** (N - point)
                for n in range(min(N, MAX_DEGREE) + 1):
                    polynomial = krawtchouk_askey(p, N, n)
                    expected = QQ(binomial(N, n)) * polynomial(point)
                    if rhs[n] != expected:
                        raise ArithmeticError(
                            "generating function failed at p=%s, N=%d, x=%d, n=%d"
                            % (p, N, point, n)
                        )


def _check_vieta(digits=100):
    precision = numberdb.bits(digits, losing=WORKING_GUARD)
    interval_field = RealIntervalField(precision)
    for p in P_VALUES:
        for N in range(1, MAX_N + 1):
            for n in range(1, min(N, MAX_DEGREE) + 1):
                polynomial = krawtchouk_askey(p, N, n)
                leading = polynomial.monomial_coefficient(x ** n)
                next_coefficient = polynomial.monomial_coefficient(x ** (n - 1))
                constant = polynomial.monomial_coefficient(x ** 0)
                expected_sum = -next_coefficient / leading
                expected_product = ((-1) ** n) * constant / leading

                roots = roots_for(str(p), N, n, digits)
                root_sum = interval_field(0)
                root_product = interval_field(1)
                for root in roots:
                    root_sum += root
                    root_product *= root
                if not (root_sum - interval_field(expected_sum)).contains_zero():
                    raise ArithmeticError(
                        "Vieta sum failed at p=%s, N=%d, n=%d" % (p, N, n)
                    )
                if not (root_product - interval_field(expected_product)).contains_zero():
                    raise ArithmeticError(
                        "Vieta product failed at p=%s, N=%d, n=%d" % (p, N, n)
                    )


def _check_reflection(digits=100):
    precision = numberdb.bits(digits, losing=WORKING_GUARD)
    interval_field = RealIntervalField(precision)
    for p in P_VALUES:
        reflected = QQ(1) - p
        if reflected not in P_VALUES or p > reflected:
            continue
        for N in range(1, MAX_N + 1):
            for n in range(1, min(N, MAX_DEGREE) + 1):
                left = roots_for(str(p), N, n, digits)
                right = roots_for(str(reflected), N, n, digits)
                for k, root in enumerate(left):
                    total = root + right[n - 1 - k]
                    if not (total - interval_field(N)).contains_zero():
                        raise ArithmeticError(
                            "reflection failed at p=%s, N=%d, n=%d, k=%d"
                            % (p, N, n, k + 1)
                        )


def _check_hamming_scaling():
    for q in (2, 3, 4):
        p = QQ(q - 1) / QQ(q)
        for N in range(1, MAX_N + 1):
            for n in range(N + 1):
                factor = QQ(binomial(N, n)) * QQ(q - 1) ** n
                expected = factor * krawtchouk_askey(p, N, n)
                if hamming_krawtchouk(q, N, n) != expected:
                    raise ArithmeticError(
                        "Hamming scaling failed at q=%d, N=%d, n=%d"
                        % (q, N, n)
                    )


def run_integrity_checks(digits=100):
    _check_generating_function()
    _check_vieta(digits)
    _check_reflection(digits)
    _check_hamming_scaling()


def stored_values():
    """Read the table from the API, to confirm every generated key is present."""
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

    found = set()
    for p_text, by_N in tree.get("Numbers", {}).items():
        for N_text, by_n in by_N.items():
            for n_text, by_k in by_n.items():
                for k_text in by_k:
                    found.add((p_text, N_text, n_text, k_text))

    expected = {
        (str(params["p"]), str(params["N"]), str(params["n"]), str(params["k"]))
        for params in KrawtchoukPolynomialZeros().enumerate()
    }
    if found != expected:
        missing = sorted(expected - found)[:5]
        extra = sorted(found - expected)[:5]
        raise ArithmeticError(
            "stored key set disagrees, missing=%s extra=%s" % (missing, extra)
        )
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
    generator = KrawtchoukPolynomialZeros()
    run_integrity_checks(generator.digits)

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="proven intervals for Krawtchouk polynomial zeros"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        stored_values()
        print("stored key-set check passed")
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
