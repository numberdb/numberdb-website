"""Meixner polynomials M_n(x; beta, c) -- numberdb.org/T269.

This generator fills the table of KLS/DLMF Meixner polynomials

    M_n(x; beta, c) = _2F_1(-n, -x; beta; 1 - 1/c).

The table uses beta for the shape parameter and c for the negative-binomial
weight parameter. It stores the DLMF normalisation with M_n(0; beta, c) = 1,
not the Wikipedia rescaling by (beta)_n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T269")

# Measured before filling the draft: these five beta values, five c values and
# n <= 16 give 425 entries. The longest written value has 780 characters, and
# the entries block is 105.9 KB in the dry-run measurement.
BETA_VALUES = (
    QQ(1) / QQ(2),
    QQ(1),
    QQ(3) / QQ(2),
    QQ(2),
    QQ(3),
)
C_VALUES = (
    QQ(1) / QQ(4),
    QQ(1) / QQ(3),
    QQ(1) / QQ(2),
    QQ(2) / QQ(3),
    QQ(3) / QQ(4),
)
UP_TO = 16

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


def _rising_in(parent, argument, count):
    """The Pochhammer symbol in the given ring."""
    value = parent.one()
    argument = parent(argument)
    for offset in range(count):
        value *= argument + parent(offset)
    return value


def _falling_binomial(argument, count):
    """The polynomial binomial(argument, count), with exact divisions."""
    value = R.one()
    argument = R(argument)
    for offset in range(count):
        value *= argument - QQ(offset)
        value *= QQ(1) / QQ(offset + 1)
    return R(value)


def _integer_binomial(top, count):
    if count < 0 or count > top:
        return 0
    numerator = 1
    denominator = 1
    for offset in range(count):
        numerator *= top - offset
        denominator *= offset + 1
    return numerator // denominator


def meixner_polynomial(n, beta, c):
    """The DLMF/KLS Meixner polynomial M_n(x; beta, c)."""
    n = int(n)
    beta = QQ(beta)
    c = QQ(c)
    z = QQ(1) - QQ(1) / c

    total = R.one()
    term = R.one()
    for k in range(n):
        term *= QQ(k - n) * (-x + QQ(k)) * z
        term *= QQ(1) / ((beta + QQ(k)) * QQ(k + 1))
        total += term
    return R(total)


class MeixnerPolynomials(numberdb.Generator):
    """Generator for T269, the Meixner polynomials M_n(x; beta, c)."""

    table = TABLE
    parameters = ("beta", "c", "n")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for beta in BETA_VALUES:
            for c in C_VALUES:
                for n in range(up_to + 1):
                    yield {"beta": str(beta), "c": str(c), "n": str(n)}

    def value(self, params, digits):
        return meixner_polynomial(
            int(params["n"]),
            QQ(params["beta"]),
            QQ(params["c"]),
        )


def _computed_values():
    return {
        (beta, c, n): meixner_polynomial(n, beta, c)
        for beta in BETA_VALUES
        for c in C_VALUES
        for n in range(UP_TO + 1)
    }


def _check_recurrence(values):
    for beta in BETA_VALUES:
        for c in C_VALUES:
            if values[(beta, c, 0)] != R.one():
                raise ArithmeticError("M_0 failed at beta=%s, c=%s" % (beta, c))
            first = R.one() + (QQ(1) - QQ(1) / c) * x / beta
            if values[(beta, c, 1)] != first:
                raise ArithmeticError("M_1 failed at beta=%s, c=%s" % (beta, c))
            for n in range(1, UP_TO):
                left = (c - QQ(1)) * x * values[(beta, c, n)]
                right = (
                    c * (QQ(n) + beta) * values[(beta, c, n + 1)]
                    - (QQ(n) + (QQ(n) + beta) * c) * values[(beta, c, n)]
                    + QQ(n) * values[(beta, c, n - 1)]
                )
                if left != right:
                    raise ArithmeticError(
                        "recurrence failed at beta=%s, c=%s, n=%d"
                        % (beta, c, n)
                    )


def _check_generating_function(values):
    for beta in BETA_VALUES:
        for c in C_VALUES:
            for n in range(UP_TO + 1):
                coefficient = R.zero()
                for j in range(n + 1):
                    coefficient += (
                        _falling_binomial(x, j)
                        * (-QQ(1) / c) ** j
                        * _rising_in(R, x + beta, n - j)
                        / _rising_scalar(1, n - j)
                    )
                expected = (
                    coefficient
                    * _rising_scalar(1, n)
                    / _rising_scalar(beta, n)
                )
                if R(expected) != values[(beta, c, n)]:
                    raise ArithmeticError(
                        "generating function failed at beta=%s, c=%s, n=%d"
                        % (beta, c, n)
                    )


def _stirling_second(maximum):
    numbers = [[0 for _ in range(maximum + 1)] for _ in range(maximum + 1)]
    numbers[0][0] = 1
    for n in range(1, maximum + 1):
        for k in range(1, n + 1):
            numbers[n][k] = numbers[n - 1][k - 1] + k * numbers[n - 1][k]
    return numbers


STIRLING_SECOND = _stirling_second(2 * UP_TO)


def _scaled_negative_binomial_sum(polynomial, beta, c):
    """(1-c)^beta times sum_x (beta)_x c^x polynomial(x) / x!."""
    polynomial = R(polynomial)
    total = QQ(0)
    for degree in range(polynomial.degree() + 1):
        coefficient = polynomial.monomial_coefficient(x ** degree)
        if coefficient == 0:
            continue
        for order in range(degree + 1):
            total += (
                coefficient
                * QQ(STIRLING_SECOND[degree][order])
                * _rising_scalar(beta, order)
                * c ** order
                / (QQ(1) - c) ** order
            )
    return QQ(total)


def _check_orthogonality(values):
    for beta in BETA_VALUES:
        for c in C_VALUES:
            for m in range(UP_TO + 1):
                left = values[(beta, c, m)]
                for n in range(UP_TO + 1):
                    right = values[(beta, c, n)]
                    total = _scaled_negative_binomial_sum(left * right, beta, c)
                    if m == n:
                        expected = (
                            c ** (-n)
                            * _rising_scalar(1, n)
                            / _rising_scalar(beta, n)
                        )
                    else:
                        expected = QQ(0)
                    if total != expected:
                        raise ArithmeticError(
                            "orthogonality failed at beta=%s, c=%s, m=%d, n=%d"
                            % (beta, c, m, n)
                        )


def _check_special_value(values):
    for (beta, c, n), polynomial in values.items():
        if polynomial(0) != 1:
            raise ArithmeticError(
                "M_n(0) failed at beta=%s, c=%s, n=%d" % (beta, c, n)
            )


def _wikipedia_polynomial(n, beta, c):
    total = R.zero()
    for k in range(n + 1):
        total += (
            QQ((-1) ** k)
            * QQ(_integer_binomial(n, k))
            * _falling_binomial(x, k)
            * _rising_scalar(1, k)
            * _rising_in(R, x + beta, n - k)
            * c ** (-k)
        )
    return R(total)


def _check_wikipedia_scaling(values):
    for beta in BETA_VALUES:
        for c in C_VALUES:
            for n in range(UP_TO + 1):
                expected = _rising_scalar(beta, n) * values[(beta, c, n)]
                if _wikipedia_polynomial(n, beta, c) != expected:
                    raise ArithmeticError(
                        "Wikipedia scaling failed at beta=%s, c=%s, n=%d"
                        % (beta, c, n)
                    )


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


def _limit_polynomial_at_infinity(polynomial, variable_ring, target_ring):
    out = target_ring.zero()
    y = target_ring.gen()
    for degree in range(polynomial.degree() + 1):
        out += _limit_at_infinity(
            polynomial.monomial_coefficient(polynomial.parent().gen() ** degree),
            variable_ring,
        ) * y ** degree
    return target_ring(out)


def _meixner_in_ring(parent, variable, n, beta, c):
    total = parent.one()
    term = parent.one()
    z = parent(1) - parent(1) / parent(c)
    for k in range(n):
        term *= parent(k - n) * (-variable + parent(k)) * z
        term *= parent(1) / ((parent(beta) + parent(k)) * parent(k + 1))
        total += term
    return parent(total)


def _hahn_in_ring(parent, variable, alpha, beta, N, n):
    total = parent.zero()
    for k in range(n + 1):
        coefficient = (
            _rising_in(parent, -n, k)
            * _rising_in(parent, parent(n) + alpha + beta + parent(1), k)
            / (
                _rising_in(parent, alpha + parent(1), k)
                * _rising_in(parent, -N, k)
                * _rising_in(parent, 1, k)
            )
        )
        total += coefficient * _rising_in(parent, -variable, k)
    return parent(total)


def _hahn_meixner_limit(beta, c, n):
    S = PolynomialRing(QQ, "N")
    N = S.gen()
    K = S.fraction_field()
    Y = PolynomialRing(K, "y")
    y = Y.gen()
    alpha = K(beta - 1)
    beta_hahn = K(N) * (QQ(1) / c - QQ(1))
    polynomial = _hahn_in_ring(Y, y, alpha, beta_hahn, K(N), n)

    QY = PolynomialRing(QQ, "y")
    return _limit_polynomial_at_infinity(polynomial, S, QY)


def _check_hahn_limit(values):
    QY = PolynomialRing(QQ, "y")
    y = QY.gen()
    for beta in BETA_VALUES:
        for c in C_VALUES:
            for n in range(UP_TO + 1):
                got = _hahn_meixner_limit(beta, c, n)
                expected = QY(str(values[(beta, c, n)]).replace("x", "y"))
                if got != expected:
                    raise ArithmeticError(
                        "Hahn-Meixner limit failed at beta=%s, c=%s, n=%d"
                        % (beta, c, n)
                    )


def _charlier_polynomial(n, a):
    total = R.zero()
    for k in range(n + 1):
        total += (
            QQ(_integer_binomial(n, k))
            * _falling_binomial(x, k)
            * _rising_scalar(1, k)
            * (-QQ(1) / a) ** k
        )
    return R(total)


def _meixner_charlier_limit(a, n):
    S = PolynomialRing(QQ, "B")
    B = S.gen()
    K = S.fraction_field()
    Y = PolynomialRing(K, "y")
    y = Y.gen()
    polynomial = _meixner_in_ring(Y, y, n, K(B), K(a) / (K(a) + K(B)))

    QY = PolynomialRing(QQ, "y")
    return _limit_polynomial_at_infinity(polynomial, S, QY)


def _check_charlier_limit():
    QY = PolynomialRing(QQ, "y")
    charlier_a = (QQ(1) / QQ(2), QQ(1), QQ(2), QQ(3))
    for a in charlier_a:
        for n in range(UP_TO + 1):
            got = _meixner_charlier_limit(a, n)
            expected = QY(str(_charlier_polynomial(n, a)).replace("x", "y"))
            if got != expected:
                raise ArithmeticError(
                    "Meixner-Charlier limit failed at a=%s, n=%d" % (a, n)
                )


def _hamming_krawtchouk_polynomial(q, N, k):
    total = R.zero()
    for j in range(k + 1):
        total += (
            QQ((-1) ** j)
            * (QQ(q) - QQ(1)) ** (k - j)
            * _falling_binomial(x, j)
            * _falling_binomial(QQ(N) - x, k - j)
        )
    return R(total)


def _check_krawtchouk_specialisation():
    for q in (2, 3, 4):
        for N in range(1, 8):
            for k in range(N + 1):
                expected = (
                    QQ(_integer_binomial(N, k))
                    * (QQ(q) - QQ(1)) ** k
                    * meixner_polynomial(k, -QQ(N), QQ(1) - QQ(q))
                )
                if _hamming_krawtchouk_polynomial(q, N, k) != expected:
                    raise ArithmeticError(
                        "Hamming Krawtchouk specialisation failed at q=%d, N=%d, k=%d"
                        % (q, N, k)
                    )


def run_integrity_checks():
    values = _computed_values()
    _check_recurrence(values)
    _check_generating_function(values)
    _check_orthogonality(values)
    _check_special_value(values)
    _check_wikipedia_scaling(values)
    _check_hahn_limit(values)
    _check_charlier_limit()
    _check_krawtchouk_specialisation()


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
    generator = MeixnerPolynomials()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact Meixner polynomials in the DLMF normalisation"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
