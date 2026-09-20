"""Secondary polynomials of the Jacobi polynomials -- numberdb.org/T374

For the Jacobi polynomial P_n^(alpha,beta), normalised by
P_n^(alpha,beta)(1) = binomial(n + alpha, n), this stores

    q_n^(alpha,beta)(x)
      = integral_{-1}^{1} (P_n(t) - P_n(x)) / (t - x)
        rho_(alpha,beta)(t) dt,

where rho_(alpha,beta) is the probability density proportional to
(1 - t)^alpha (1 + t)^beta. The table follows the rational grid of T106:
alpha,beta in {-1/2, 0, 1/2, 1, 3/2, 2}, alpha < beta, and 0 <= n <= 10.
It does not store the symbolic a,b rows of T106, because this probability
normalisation makes the coefficients rational functions of a and b.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

**Exact.** Every coefficient is a Sage rational. The generator builds
P_n^(alpha,beta) from the binomial formula and applies the defining integral
using the exact moments of the probability density.

**Every entry is checked before it is returned.** The checks include the
Jacobi three-term recurrence, the Pade property of q_n/P_n for the Cauchy
transform, the algebraic Gauss-quadrature moment identity, a plain Python
Fractions implementation, direct polynomial-weight integration for the
integer-parameter controls, and the Legendre relation 2 q_n^(0,0) = T133.

Answers numberdb-data#11, #62, #93 and #171, for the Jacobi family.
"""

from fractions import Fraction
import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T374")

# The rational grid of T106, excluding the symbolic a,b rows.
PARAMETER_VALUES = (
    QQ(-1) / QQ(2),
    QQ(0),
    QQ(1) / QQ(2),
    QQ(1),
    QQ(3) / QQ(2),
    QQ(2),
)
UP_TO = 10

RING = PolynomialRing(QQ, "x")
X = RING.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _as_qq(value):
    return value if value in QQ else QQ(value)


def binomial_rational(argument, count):
    """The generalized binomial coefficient over QQ."""
    argument = _as_qq(argument)
    value = QQ(1)
    for offset in range(count):
        value *= argument - QQ(offset)
    for divisor in range(1, count + 1):
        value *= QQ(1) / QQ(divisor)
    return value


def rising(argument, count):
    """The rising factorial (argument)_count over QQ."""
    argument = _as_qq(argument)
    value = QQ(1)
    for offset in range(count):
        value *= argument + QQ(offset)
    return value


def jacobi_polynomial(alpha, beta, n):
    """P_n^(alpha,beta), by the binomial formula."""
    alpha = _as_qq(alpha)
    beta = _as_qq(beta)
    n = int(n)
    total = RING(0)
    half = QQ(1) / QQ(2)
    for s in range(n + 1):
        total += (
            binomial_rational(QQ(n) + alpha, s)
            * binomial_rational(QQ(n) + beta, n - s)
            * (half * (X - 1)) ** (n - s)
            * (half * (X + 1)) ** s
        )
    return RING(total)


def moment(alpha, beta, index):
    """The index-th moment of the probability-normalised Jacobi density."""
    alpha = _as_qq(alpha)
    beta = _as_qq(beta)
    index = int(index)
    total = QQ(0)
    for k in range(index + 1):
        total += (
            ZZ(index).binomial(k)
            * QQ(2) ** k
            * QQ(-1) ** (index - k)
            * rising(beta + 1, k)
            / rising(alpha + beta + 2, k)
        )
    return total


def secondary_from_definition(alpha, beta, n):
    """q_n from the defining integral and exact moments."""
    polynomial = jacobi_polynomial(alpha, beta, n)
    secondary = RING(0)
    for degree, coefficient in enumerate(polynomial.list()):
        if coefficient == 0:
            continue
        for i in range(degree):
            secondary += coefficient * moment(alpha, beta, i) * X ** (degree - 1 - i)
    return RING(secondary)


def jacobi_recurrence_next(alpha, beta, previous, current, n):
    """P_n or q_n from P_(n-2), P_(n-1), for n >= 2."""
    alpha = _as_qq(alpha)
    beta = _as_qq(beta)
    n = QQ(n)
    left = QQ(2) * n * (n + alpha + beta) * (QQ(2) * n + alpha + beta - 2)
    middle = (
        (QQ(2) * n + alpha + beta - 1)
        * (
            (QQ(2) * n + alpha + beta)
            * (QQ(2) * n + alpha + beta - 2)
            * X
            + alpha ** 2
            - beta ** 2
        )
        * current
    )
    last = (
        QQ(2)
        * (n + alpha - 1)
        * (n + beta - 1)
        * (QQ(2) * n + alpha + beta)
        * previous
    )
    return RING((middle - last) / left)


def recurrence_values(alpha, beta, up_to):
    """The secondary polynomials by the Jacobi recurrence."""
    values = [RING(0)]
    if up_to >= 1:
        values.append(RING((alpha + beta + 2) / QQ(2)))
    for n in range(2, up_to + 1):
        values.append(jacobi_recurrence_next(alpha, beta, values[n - 2], values[n - 1], n))
    return values


def reversed_coefficients(polynomial, degree):
    """Coefficients of u^degree * polynomial(1/u)."""
    original = polynomial.list()
    return [
        original[degree - i] if degree - i < len(original) else QQ(0)
        for i in range(degree + 1)
    ]


def product_coefficient(left, right, index):
    total = QQ(0)
    for i, coefficient in enumerate(left):
        j = index - i
        if 0 <= j < len(right):
            total += coefficient * right[j]
    return total


def pade_property(alpha, beta, polynomial, secondary, n):
    """Whether q_n/P_n matches the Cauchy-transform series through u^(2n)."""
    n = int(n)
    if n == 0:
        return secondary == 0
    denominator = reversed_coefficients(polynomial, n)
    numerator = reversed_coefficients(secondary, n)
    cauchy = [QQ(0)] + [moment(alpha, beta, i) for i in range(2 * n)]
    for exponent in range(2 * n + 1):
        left = product_coefficient(denominator, cauchy, exponent)
        right = numerator[exponent] if exponent < len(numerator) else QQ(0)
        if left != right:
            return False
    return True


def quadrature_moment_identity(alpha, beta, polynomial, secondary, n):
    """Check sum q(r) r^m / P'(r) = m_m using the quotient-ring residue formula."""
    n = int(n)
    if n == 0:
        return True
    leading = polynomial.leading_coefficient()
    for exponent in range(2 * n):
        remainder = RING((secondary * X ** exponent) % polynomial)
        if remainder.monomial_coefficient(X ** (n - 1)) / leading != moment(alpha, beta, exponent):
            return False
    return True


def integer_weight_moment(alpha, beta, index):
    """Moment from direct integration when alpha and beta are nonnegative integers."""
    alpha = int(alpha)
    beta = int(beta)
    index = int(index)
    weight = RING((1 - X) ** alpha * (1 + X) ** beta)
    mass = QQ(0)
    total = QQ(0)
    for degree, coefficient in enumerate(weight.list()):
        integral = QQ(0) if degree % 2 else QQ(2) / QQ(degree + 1)
        mass += coefficient * integral
        shifted = degree + index
        total += coefficient * (QQ(0) if shifted % 2 else QQ(2) / QQ(shifted + 1))
    return total / mass


def secondary_from_integer_weight(alpha, beta, n):
    """The defining integral with the weight expanded as a polynomial."""
    polynomial = jacobi_polynomial(alpha, beta, n)
    secondary = RING(0)
    for degree, coefficient in enumerate(polynomial.list()):
        if coefficient == 0:
            continue
        for i in range(degree):
            secondary += (
                coefficient
                * integer_weight_moment(alpha, beta, i)
                * X ** (degree - 1 - i)
            )
    return RING(secondary)


def legendre_secondary(up_to):
    """The Legendre secondary polynomials in the T133 density-1 convention."""
    values = [RING(0)]
    if up_to >= 1:
        values.append(RING(2))
    for n in range(2, up_to + 1):
        values.append(RING(((QQ(2) * n - 1) * X * values[n - 1] - (n - 1) * values[n - 2]) / QQ(n)))
    return values


def _fq(value):
    value = QQ(value)
    return Fraction(int(value.numerator()), int(value.denominator()))


def _trim(poly):
    while len(poly) > 1 and poly[-1] == 0:
        poly.pop()
    return poly


def _add(left, right):
    size = max(len(left), len(right))
    return _trim([
        (left[i] if i < len(left) else Fraction(0))
        + (right[i] if i < len(right) else Fraction(0))
        for i in range(size)
    ])


def _scale(poly, scalar):
    return _trim([scalar * coefficient for coefficient in poly])


def _mul(left, right):
    out = [Fraction(0) for _ in range(len(left) + len(right) - 1)]
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i + j] += a * b
    return _trim(out)


def _pow_linear(constant, linear, exponent):
    out = [Fraction(1)]
    factor = [constant, linear]
    for _ in range(exponent):
        out = _mul(out, factor)
    return out


def _binom_fraction(argument, count):
    value = Fraction(1)
    for offset in range(count):
        value *= argument - offset
    for divisor in range(1, count + 1):
        value /= divisor
    return value


def _rising_fraction(argument, count):
    value = Fraction(1)
    for offset in range(count):
        value *= argument + offset
    return value


def fraction_jacobi(alpha, beta, n):
    """A plain-Python Fraction implementation of the binomial formula."""
    alpha = _fq(alpha)
    beta = _fq(beta)
    total = [Fraction(0)]
    for s in range(n + 1):
        coefficient = _binom_fraction(n + alpha, s) * _binom_fraction(n + beta, n - s)
        left = _pow_linear(Fraction(-1, 2), Fraction(1, 2), n - s)
        right = _pow_linear(Fraction(1, 2), Fraction(1, 2), s)
        total = _add(total, _scale(_mul(left, right), coefficient))
    return total


def fraction_moment(alpha, beta, index):
    alpha = _fq(alpha)
    beta = _fq(beta)
    total = Fraction(0)
    for k in range(index + 1):
        total += (
            Fraction(int(ZZ(index).binomial(k)))
            * Fraction(2) ** k
            * Fraction(-1) ** (index - k)
            * _rising_fraction(beta + 1, k)
            / _rising_fraction(alpha + beta + 2, k)
        )
    return total


def fraction_secondary(alpha, beta, n):
    polynomial = fraction_jacobi(alpha, beta, n)
    out = [Fraction(0) for _ in range(max(1, n))]
    for degree, coefficient in enumerate(polynomial):
        if coefficient == 0:
            continue
        for i in range(degree):
            out[degree - 1 - i] += coefficient * fraction_moment(alpha, beta, i)
    return _trim(out)


def _from_fraction_poly(poly):
    total = RING(0)
    for degree, coefficient in enumerate(poly):
        total += QQ(coefficient.numerator) / QQ(coefficient.denominator) * X ** degree
    return RING(total)


_RECURRENCES = {
    (alpha, beta): recurrence_values(alpha, beta, UP_TO)
    for i, alpha in enumerate(PARAMETER_VALUES)
    for beta in PARAMETER_VALUES[i + 1 :]
}
_LEGENDRE = legendre_secondary(UP_TO)


def checked(alpha, beta, n):
    """q_n, after the exact construction and independent checks have agreed."""
    alpha = _as_qq(alpha)
    beta = _as_qq(beta)
    n = int(n)
    if alpha >= beta:
        raise ValueError("this draft stores alpha < beta, not alpha=%s, beta=%s" % (alpha, beta))
    if n < 0:
        raise ValueError("n must be nonnegative, not %s" % n)
    if n > UP_TO:
        raise ValueError("this draft covers n <= %d" % UP_TO)

    polynomial = jacobi_polynomial(alpha, beta, n)
    secondary = secondary_from_definition(alpha, beta, n)

    if secondary != _RECURRENCES[(alpha, beta)][n]:
        raise ArithmeticError(
            "alpha=%s beta=%s n=%d: definition and recurrence disagree"
            % (alpha, beta, n)
        )

    if secondary != _from_fraction_poly(fraction_secondary(alpha, beta, n)):
        raise ArithmeticError(
            "alpha=%s beta=%s n=%d: Sage and Fraction implementations disagree"
            % (alpha, beta, n)
        )

    if alpha in ZZ and beta in ZZ and alpha >= 0 and beta >= 0:
        if secondary != secondary_from_integer_weight(alpha, beta, n):
            raise ArithmeticError(
                "alpha=%s beta=%s n=%d: beta moments and direct integration disagree"
                % (alpha, beta, n)
            )

    if not pade_property(alpha, beta, polynomial, secondary, n):
        raise ArithmeticError(
            "alpha=%s beta=%s n=%d: the Pade property failed" % (alpha, beta, n)
        )

    if not quadrature_moment_identity(alpha, beta, polynomial, secondary, n):
        raise ArithmeticError(
            "alpha=%s beta=%s n=%d: the quadrature moment identity failed"
            % (alpha, beta, n)
        )

    if QQ(2) * secondary_from_definition(QQ(0), QQ(0), n) != _LEGENDRE[n]:
        raise ArithmeticError("n=%d: the Legendre relation to T133 failed" % n)

    if n == 0:
        if secondary != 0:
            raise ArithmeticError("q_0 is not 0")
        return secondary
    if secondary.degree() != n - 1:
        raise ArithmeticError(
            "alpha=%s beta=%s n=%d: degree %d, not %d"
            % (alpha, beta, n, secondary.degree(), n - 1)
        )
    if secondary.leading_coefficient() != polynomial.leading_coefficient():
        raise ArithmeticError(
            "alpha=%s beta=%s n=%d: leading coefficient does not match P_n"
            % (alpha, beta, n)
        )
    return secondary


def run_integrity_checks():
    count = 0
    longest = (0, None)
    for i, alpha in enumerate(PARAMETER_VALUES):
        for beta in PARAMETER_VALUES[i + 1 :]:
            for n in range(UP_TO + 1):
                value = checked(alpha, beta, n)
                count += 1
                length = len(str(value))
                if length > longest[0]:
                    longest = (length, "alpha=%s beta=%s n=%d" % (alpha, beta, n))
    print("integrity checks passed for %d Jacobi secondary polynomials" % count)
    print("matched the Jacobi recurrence, Pade property and quadrature moment identity")
    print("matched the Fraction implementation and integer-weight controls")
    print("matched 2 q_n^(0,0) with the Legendre secondary convention of T133")
    print("longest polynomial has %d characters at %s" % longest)


class JacobiSecondary(numberdb.Generator):

    table = TABLE
    parameters = ("alpha", "beta", "n")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for i, alpha in enumerate(PARAMETER_VALUES):
            for beta in PARAMETER_VALUES[i + 1 :]:
                for n in range(up_to + 1):
                    yield {"alpha": str(alpha), "beta": str(beta), "n": str(n)}

    def value(self, params, digits):
        return checked(QQ(params["alpha"]), QQ(params["beta"]), int(params["n"]))


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
    generator = JacobiSecondary()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(
            fill_draft_once(
                generator,
                message=(
                    "fill secondary polynomials of Jacobi polynomials from "
                    "exact probability-normalised moments"
                ),
            )
        )
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
