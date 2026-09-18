"""Hahn polynomials Q_n(x; alpha, beta, N) -- numberdb.org/T268.

This generator fills the table of DLMF/KLS Hahn polynomials

    Q_n(x; alpha, beta, N)
      = _3F_2(-n, n + alpha + beta + 1, -x; alpha + 1, -N; 1).

The lower parameter is -N, not the -N+1 convention used in some secondary
sources. The table stores the polynomial in x, with shape parameters alpha
and beta, support endpoint N, and degree n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T268")

# Measured before filling the draft: these seven shape pairs, 2 <= N <= 14 and
# 0 <= n <= N give 819 entries. The longest written value has 379 characters,
# and the entries block is 112.6 KB in the dry-run measurement.
PARAMETER_PAIRS = (
    (QQ(0), QQ(0)),
    (QQ(1), QQ(1)),
    (QQ(1), QQ(2)),
    (QQ(2), QQ(1)),
    (QQ(2), QQ(2)),
    (QQ(1) / QQ(2), QQ(1) / QQ(2)),
    (-QQ(1) / QQ(2), -QQ(1) / QQ(2)),
)
MIN_N = 2
MAX_N = 14

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


def _rising_polynomial(argument, count):
    """The polynomial Pochhammer symbol (argument)_count over QQ[x]."""
    value = R.one()
    argument = R(argument)
    for offset in range(count):
        value *= argument + QQ(offset)
    return R(value)


def hahn_polynomial(alpha, beta, N, n):
    """The DLMF/KLS Hahn polynomial Q_n(x; alpha, beta, N)."""
    alpha, beta = QQ(alpha), QQ(beta)
    N, n = int(N), int(n)
    total = R.zero()
    for k in range(n + 1):
        coefficient = (
            _rising_scalar(-n, k)
            * _rising_scalar(n + alpha + beta + 1, k)
            / (
                _rising_scalar(alpha + 1, k)
                * _rising_scalar(-N, k)
                * _rising_scalar(1, k)
            )
        )
        total += coefficient * _rising_polynomial(-x, k)
    return R(total)


class HahnPolynomials(numberdb.Generator):
    """Generator for T268, the Hahn polynomials Q_n(x; alpha, beta, N)."""

    table = TABLE
    parameters = ("alpha", "beta", "N", "n")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, max_N=MAX_N):
        for alpha, beta in PARAMETER_PAIRS:
            for N in range(MIN_N, max_N + 1):
                for n in range(N + 1):
                    yield {
                        "alpha": str(alpha),
                        "beta": str(beta),
                        "N": str(N),
                        "n": str(n),
                    }

    def value(self, params, digits):
        return hahn_polynomial(
            QQ(params["alpha"]),
            QQ(params["beta"]),
            int(params["N"]),
            int(params["n"]),
        )


def _computed_values():
    return {
        (alpha, beta, N, n): hahn_polynomial(alpha, beta, N, n)
        for alpha, beta in PARAMETER_PAIRS
        for N in range(MIN_N, MAX_N + 1)
        for n in range(N + 1)
    }


def _hahn_weight(alpha, beta, N, point):
    return (
        _rising_scalar(alpha + 1, point)
        * _rising_scalar(beta + 1, N - point)
        / (QQ(factorial(point)) * QQ(factorial(N - point)))
    )


def _check_orthogonality(values):
    for alpha, beta in PARAMETER_PAIRS:
        for N in range(MIN_N, MAX_N + 1):
            polynomials = [values[(alpha, beta, N, n)] for n in range(N + 1)]
            for m, left in enumerate(polynomials):
                for n, right in enumerate(polynomials):
                    if m == n:
                        continue
                    total = QQ(0)
                    for point in range(N + 1):
                        total += (
                            _hahn_weight(alpha, beta, N, point)
                            * left(point)
                            * right(point)
                        )
                    if total != 0:
                        raise ArithmeticError(
                            "orthogonality failed at alpha=%s, beta=%s, N=%d, m=%d, n=%d"
                            % (alpha, beta, N, m, n)
                        )


def _check_special_value(values):
    for (alpha, beta, N, n), polynomial in values.items():
        if polynomial(0) != 1:
            raise ArithmeticError(
                "Q_n(0) failed at alpha=%s, beta=%s, N=%d, n=%d"
                % (alpha, beta, N, n)
            )


def _check_forward_difference(values):
    for (alpha, beta, N, n), polynomial in values.items():
        if n == 0:
            continue
        left = polynomial(x + 1) - polynomial
        factor = -(
            QQ(n)
            * (QQ(n) + alpha + beta + 1)
            / ((alpha + 1) * QQ(N))
        )
        right = factor * hahn_polynomial(alpha + 1, beta + 1, N - 1, n - 1)
        if R(left) != R(right):
            raise ArithmeticError(
                "forward difference failed at alpha=%s, beta=%s, N=%d, n=%d"
                % (alpha, beta, N, n)
            )


def _inner_uniform(left, right, N):
    return sum(left(point) * right(point) for point in range(N + 1))


def _gram_polynomials(N):
    """Discrete Chebyshev polynomials from Gram-Schmidt, normalized at 0."""
    polynomials = []
    for degree in range(N + 1):
        candidate = R(x ** degree)
        for previous in polynomials:
            candidate -= (
                _inner_uniform(candidate, previous, N)
                / _inner_uniform(previous, previous, N)
            ) * previous
            candidate = R(candidate)
        at_zero = candidate(0)
        if at_zero == 0:
            raise ArithmeticError(
                "Gram-Schmidt polynomial vanishes at zero for N=%d, degree=%d"
                % (N, degree)
            )
        polynomials.append(R(candidate / at_zero))
    return polynomials


def _check_gram_case(values):
    for N in range(MIN_N, MAX_N + 1):
        independent = _gram_polynomials(N)
        for n, expected in enumerate(independent):
            if values[(QQ(0), QQ(0), N, n)] != expected:
                raise ArithmeticError("Gram case failed at N=%d, n=%d" % (N, n))


def _rising_in(parent, argument, count):
    value = parent.one()
    argument = parent(argument)
    for offset in range(count):
        value *= argument + parent(offset)
    return value


def _limit_at_infinity(fraction, polynomial_ring):
    fraction = fraction.parent()(fraction)
    numerator = polynomial_ring(fraction.numerator())
    denominator = polynomial_ring(fraction.denominator())
    num_degree = numerator.degree()
    den_degree = denominator.degree()
    if num_degree < den_degree:
        return QQ(0)
    if num_degree == den_degree:
        return QQ(numerator.leading_coefficient()) / QQ(denominator.leading_coefficient())
    raise ArithmeticError("coefficient has no finite limit at infinity: %s" % (fraction,))


def _hahn_jacobi_limit(alpha, beta, n):
    S = PolynomialRing(QQ, "M")
    M = S.gen()
    K = S.fraction_field()
    Y = PolynomialRing(K, "y")
    y = Y.gen()

    total = Y.zero()
    for k in range(n + 1):
        coefficient = (
            _rising_in(K, -n, k)
            * _rising_in(K, QQ(n) + alpha + beta + 1, k)
            / (
                _rising_in(K, alpha + 1, k)
                * _rising_in(K, -K(M), k)
                * _rising_in(K, 1, k)
            )
        )
        total += coefficient * _rising_in(Y, -K(M) * y, k)

    QY = PolynomialRing(QQ, "y")
    yy = QY.gen()
    out = QY.zero()
    for degree in range(n + 1):
        out += _limit_at_infinity(total.monomial_coefficient(y ** degree), S) * yy ** degree
    return QY(out)


def _normalized_jacobi_limit(alpha, beta, n):
    QY = PolynomialRing(QQ, "y")
    y = QY.gen()
    total = QY.zero()
    for k in range(n + 1):
        coefficient = (
            _rising_scalar(-n, k)
            * _rising_scalar(n + alpha + beta + 1, k)
            / (_rising_scalar(alpha + 1, k) * _rising_scalar(1, k))
        )
        total += coefficient * y ** k
    return QY(total)


def _check_jacobi_limit():
    for alpha, beta in PARAMETER_PAIRS:
        for n in range(MAX_N + 1):
            got = _hahn_jacobi_limit(alpha, beta, n)
            expected = _normalized_jacobi_limit(alpha, beta, n)
            if got != expected:
                raise ArithmeticError(
                    "Jacobi limit failed at alpha=%s, beta=%s, n=%d"
                    % (alpha, beta, n)
                )


def run_integrity_checks():
    values = _computed_values()
    _check_orthogonality(values)
    _check_special_value(values)
    _check_forward_difference(values)
    _check_gram_case(values)
    _check_jacobi_limit()


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
    generator = HahnPolynomials()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact Hahn polynomials in the DLMF normalisation"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
