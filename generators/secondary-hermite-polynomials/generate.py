"""Secondary polynomials of the Hermite polynomials q_n -- numberdb.org/T373.

For the physicists' Hermite polynomial H_n, this table stores

    q_n(x) = pi^(-1/2) integral_{-infinity}^{infinity}
             (H_n(t) - H_n(x)) / (t - x) exp(-t^2) dt.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are exact rational polynomials. The integrity checks compare the
recurrence with the defining moment formula, with a plain Python fractions
implementation of the same formula, with the shifted monic associated-Hermite
recurrence, and with the Gauss-Hermite quadrature identity
q_n(x_k)/H_n'(x_k) = w_k/sqrt(pi) at the roots of H_n, checked exactly as a
polynomial congruence modulo H_n. They also check the Pade property of
q_n/H_n for the Stieltjes transform of the probability Hermite weight.
"""

import os
import sys
from fractions import Fraction

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T373")
UP_TO = 50

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
        numberdb.configure(api_key=token)


def hermite_values(up_to=UP_TO):
    values = [R.one()]
    if up_to == 0:
        return values
    values.append(ZZ(2) * x)
    for n in range(1, up_to):
        values.append(ZZ(2) * x * values[n] - ZZ(2 * n) * values[n - 1])
    return values


HERMITE = hermite_values(UP_TO)


def secondary_values(up_to=UP_TO):
    values = [R.zero()]
    if up_to == 0:
        return values
    values.append(R(2))
    for n in range(1, up_to):
        values.append(ZZ(2) * x * values[n] - ZZ(2 * n) * values[n - 1])
    return values


SECONDARY = secondary_values(UP_TO)


def moment(power):
    power = int(power)
    if power % 2:
        return QQ(0)
    k = power // 2
    return QQ(factorial(2 * k)) / (QQ(4) ** k * QQ(factorial(k)))


def secondary_from_moments(n):
    total = R.zero()
    polynomial = HERMITE[int(n)]
    for degree, coefficient in enumerate(polynomial.list()):
        for i in range(degree):
            total += coefficient * moment(i) * x ** (degree - 1 - i)
    return R(total)


def fraction_moment(power):
    power = int(power)
    if power % 2:
        return Fraction(0)
    k = power // 2
    return Fraction(int(factorial(2 * k)), (4 ** k) * int(factorial(k)))


def fraction_poly_add(one, other):
    length = max(len(one), len(other))
    out = [Fraction(0) for _ in range(length)]
    for i, coefficient in enumerate(one):
        out[i] += coefficient
    for i, coefficient in enumerate(other):
        out[i] += coefficient
    return out


def fraction_poly_mul_x(poly):
    return [Fraction(0)] + list(poly)


def fraction_poly_scalar(poly, scalar):
    return [scalar * coefficient for coefficient in poly]


def fraction_hermite_values(up_to=UP_TO):
    values = [[Fraction(1)]]
    if up_to == 0:
        return values
    values.append([Fraction(0), Fraction(2)])
    for n in range(1, up_to):
        values.append(fraction_poly_add(
            fraction_poly_scalar(fraction_poly_mul_x(values[n]), Fraction(2)),
            fraction_poly_scalar(values[n - 1], Fraction(-2 * n)),
        ))
    return values


FRACTION_HERMITE = fraction_hermite_values(UP_TO)


def fraction_secondary_from_moments(n):
    out = [Fraction(0) for _ in range(int(n))]
    for degree, coefficient in enumerate(FRACTION_HERMITE[int(n)]):
        for i in range(degree):
            out[degree - 1 - i] += coefficient * fraction_moment(i)
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out


def sage_poly_from_fractions(coefficients):
    total = R.zero()
    for degree, coefficient in enumerate(coefficients):
        total += QQ(coefficient.numerator) / QQ(coefficient.denominator) * x ** degree
    return total


def check_identities():
    for n in range(UP_TO + 1):
        value = SECONDARY[n]
        if value != secondary_from_moments(n):
            raise ArithmeticError("moment formula failed at n=%d" % n)
        if value != sage_poly_from_fractions(fraction_secondary_from_moments(n)):
            raise ArithmeticError("plain Python fraction check failed at n=%d" % n)
        if n == 0:
            if value != 0:
                raise ArithmeticError("q_0 is not zero")
            continue
        if value.degree() != n - 1:
            raise ArithmeticError("degree failed at n=%d" % n)
        if value.leading_coefficient() != QQ(2) ** n:
            raise ArithmeticError("leading coefficient failed at n=%d" % n)
        if value(-x) != (-1) ** (n - 1) * value:
            raise ArithmeticError("parity failed at n=%d" % n)

    for n in range(0, UP_TO):
        associated = SECONDARY[n + 1] / (QQ(2) ** (n + 1))
        if associated.leading_coefficient() != 1:
            raise ArithmeticError("associated polynomial is not monic at n=%d" % n)
        if n == 0 and associated != 1:
            raise ArithmeticError("associated initial value failed")
        if n == 1 and associated != x:
            raise ArithmeticError("associated first-degree value failed")
        if n >= 1:
            previous = SECONDARY[n] / (QQ(2) ** n)
            before_previous = SECONDARY[n - 1] / (QQ(2) ** (n - 1))
            expected = x * previous - QQ(n) / QQ(2) * before_previous
            if associated != expected:
                raise ArithmeticError("associated recurrence failed at n=%d" % n)

    for n in range(1, UP_TO + 1):
        congruence = (SECONDARY[n] * HERMITE[n].derivative()) % HERMITE[n]
        expected = R(QQ(2) ** (n + 1) * QQ(factorial(n)))
        if congruence != expected:
            raise ArithmeticError("Gauss-Hermite congruence failed at n=%d" % n)

    for n in range(1, UP_TO + 1):
        coefficients = HERMITE[n].list()
        for exponent in range(n):
            coefficient = sum(
                coefficients[degree] * moment(degree + exponent)
                for degree in range(len(coefficients))
            )
            if coefficient != 0:
                raise ArithmeticError(
                    "Pade remainder coefficient %d failed at n=%d"
                    % (exponent, n)
                )
        first_remainder = sum(
            coefficients[degree] * moment(degree + n)
            for degree in range(len(coefficients))
        )
        if first_remainder == 0:
            raise ArithmeticError("first Pade remainder vanished at n=%d" % n)

    longest = max((len(str(SECONDARY[n])), n) for n in range(UP_TO + 1))
    print("integrity checks passed for q_0 through q_%d" % UP_TO)
    print("moment formula and plain Python fraction checks passed")
    print("associated-Hermite recurrence and Gauss-Hermite congruence passed")
    print("Stieltjes-transform Pade check passed")
    print("longest polynomial has %d characters at n=%d" % (longest[0], longest[1]))


class SecondaryHermitePolynomials(numberdb.Generator):
    """Generator for T373, secondary polynomials of physicists' Hermite H_n."""

    table = TABLE
    parameters = ("n",)
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return SECONDARY[int(params["n"])]


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
    check_identities()
    generator = SecondaryHermitePolynomials()
    if "--publish" in sys.argv or bool(int(os.environ.get("NUMBERDB_PUBLISH", "0"))):
        print(fill_draft_once(
            generator,
            message="exact Hermite secondary polynomials from recurrence"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
