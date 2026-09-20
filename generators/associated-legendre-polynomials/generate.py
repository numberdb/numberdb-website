r"""Associated Legendre polynomials -- numberdb.org/T360.

This draft stores the Condon-Shortley associated Legendre functions
P_l^m(x), with -l <= m <= l and l <= 25, as exact polynomials in x and y,
where y stands for sqrt(1 - x^2).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The coefficients are exact rationals. The generator computes ordinary
Legendre polynomials by Bonnet's recurrence, then applies Rodrigues' formula
for nonnegative order and the standard negative-order relation. Before any
value is written it checks the initial rows, the negative-order relation, the
three-term recurrence in l, exact orthogonality for each nonnegative m, and
the m = 0 match with the ordinary Legendre polynomials.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T360")

# Measured before filling the draft: l <= 25 gives 676 entries. The longest
# written value has 407 characters, and the entries block is 115.4 KB in the
# dry-run measurement.
UP_TO = 25

X_RING = PolynomialRing(QQ, "x")
x_single = X_RING.gen()

XY_RING = PolynomialRing(QQ, ("x", "y"))
x, y = XY_RING.gens()

U_RING = PolynomialRing(QQ, "u")
u = U_RING.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _legendre_polynomials(up_to):
    polynomials = [X_RING.one()]
    if up_to == 0:
        return polynomials
    polynomials.append(x_single)
    for degree in range(1, up_to):
        polynomials.append(
            X_RING(
                ((2 * degree + 1) * x_single * polynomials[degree]
                 - degree * polynomials[degree - 1])
                * (QQ(1) / QQ(degree + 1))
            )
        )
    return polynomials


LEGENDRE = _legendre_polynomials(UP_TO)


def _lift_x(polynomial):
    value = XY_RING.zero()
    for exponent, coefficient in X_RING(polynomial).dict().items():
        value += QQ(coefficient) * x ** int(exponent)
    return XY_RING(value)


def _differentiate(polynomial, times):
    value = X_RING(polynomial)
    for _ in range(times):
        value = value.derivative()
    return X_RING(value)


def associated_legendre(l, m):
    """The Condon-Shortley P_l^m(x), as a polynomial in x and y."""
    l = int(l)
    m = int(m)
    if l < 0 or abs(m) > l:
        raise ValueError("expected l >= 0 and |m| <= l")

    order = abs(m)
    positive_order = (
        QQ((-1) ** order)
        * y ** order
        * _lift_x(_differentiate(LEGENDRE[l], order))
    )
    if m >= 0:
        return XY_RING(positive_order)

    ratio = QQ((-1) ** order) * (
        QQ(factorial(l - order)) / QQ(factorial(l + order))
    )
    return XY_RING(ratio * positive_order)


def _m_values(l):
    yield 0
    for order in range(1, l + 1):
        yield order
        yield -order


class AssociatedLegendrePolynomials(numberdb.Generator):
    """Generator for T360, the associated Legendre polynomials P_l^m."""

    table = TABLE
    parameters = ("l", "m")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for l in range(up_to + 1):
            for m in _m_values(l):
                yield {"l": str(l), "m": str(m)}

    def value(self, params, digits):
        return associated_legendre(int(params["l"]), int(params["m"]))


def _computed_values():
    return {
        (l, m): associated_legendre(l, m)
        for l in range(UP_TO + 1)
        for m in _m_values(l)
    }


def _stored_or_zero(values, l, m):
    if l < 0 or abs(m) > l:
        return XY_RING.zero()
    return values[(l, m)]


def _check_initial_values(values):
    expected = {
        (0, 0): XY_RING(1),
        (1, 0): x,
        (1, 1): -y,
        (1, -1): QQ(1) / QQ(2) * y,
        (2, 0): QQ(3) / QQ(2) * x ** 2 - QQ(1) / QQ(2),
        (2, 1): -3 * x * y,
        (2, -1): QQ(1) / QQ(2) * x * y,
        (2, 2): 3 * y ** 2,
        (2, -2): QQ(1) / QQ(8) * y ** 2,
        (3, 0): QQ(5) / QQ(2) * x ** 3 - QQ(3) / QQ(2) * x,
        (3, 1): -QQ(3) / QQ(2) * (5 * x ** 2 - 1) * y,
        (3, 2): 15 * x * y ** 2,
        (3, 3): -15 * y ** 3,
    }
    for key, wanted in expected.items():
        if values[key] != XY_RING(wanted):
            raise ArithmeticError("initial value failed at l=%s, m=%s" % key)


def _check_negative_order(values):
    for l in range(UP_TO + 1):
        for order in range(1, l + 1):
            expected = (
                QQ((-1) ** order)
                * QQ(factorial(l - order))
                / QQ(factorial(l + order))
                * values[(l, order)]
            )
            if values[(l, -order)] != XY_RING(expected):
                raise ArithmeticError("negative-order relation failed at l=%d, m=%d"
                                      % (l, order))


def _check_l_recurrence(values):
    for m in range(-UP_TO, UP_TO + 1):
        for l in range(max(0, abs(m)), UP_TO):
            left = QQ(l - m + 1) * _stored_or_zero(values, l + 1, m)
            right = (
                QQ(2 * l + 1) * x * _stored_or_zero(values, l, m)
                - QQ(l + m) * _stored_or_zero(values, l - 1, m)
            )
            if XY_RING(left - right) != 0:
                raise ArithmeticError("l-recurrence failed at l=%d, m=%d"
                                      % (l, m))


def _to_univariate_after_y_squared(polynomial):
    """Substitute y^2 = 1 - u^2 into a polynomial with even y exponents."""
    value = U_RING.zero()
    for exponent, coefficient in XY_RING(polynomial).dict().items():
        x_degree, y_degree = (int(exponent[0]), int(exponent[1]))
        if y_degree % 2:
            raise ArithmeticError("odd y exponent in orthogonality check")
        value += QQ(coefficient) * u ** x_degree * (1 - u ** 2) ** (y_degree // 2)
    return U_RING(value)


def _integral_minus_one_to_one(polynomial):
    total = QQ(0)
    for exponent, coefficient in U_RING(polynomial).dict().items():
        exponent = int(exponent)
        if exponent % 2 == 0:
            total += QQ(2) * QQ(coefficient) / QQ(exponent + 1)
    return total


def _check_orthogonality(values):
    for m in range(UP_TO + 1):
        for l in range(m, UP_TO + 1):
            for k in range(m, UP_TO + 1):
                product = _to_univariate_after_y_squared(
                    values[(l, m)] * values[(k, m)]
                )
                actual = _integral_minus_one_to_one(product)
                if l == k:
                    expected = (
                        QQ(2)
                        * QQ(factorial(l + m))
                        / (QQ(2 * l + 1) * QQ(factorial(l - m)))
                    )
                else:
                    expected = QQ(0)
                if actual != expected:
                    raise ArithmeticError(
                        "orthogonality failed at m=%d, l=%d, k=%d"
                        % (m, l, k)
                    )


def _check_m_zero(values):
    for l in range(UP_TO + 1):
        if values[(l, 0)] != _lift_x(LEGENDRE[l]):
            raise ArithmeticError("m=0 row failed at l=%d" % (l,))


def run_integrity_checks():
    values = _computed_values()
    _check_initial_values(values)
    _check_negative_order(values)
    _check_l_recurrence(values)
    _check_orthogonality(values)
    _check_m_zero(values)


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
    generator = AssociatedLegendrePolynomials()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact associated Legendre polynomials with Condon-Shortley phase"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
