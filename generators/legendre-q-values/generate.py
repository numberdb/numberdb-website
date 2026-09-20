"""Values of the Legendre functions of the second kind Q_nu(x) -- numberdb.org/T375

This table stores the real branch of Q_nu(x) for x > 1.  In Sage and mpmath
this is the type 3 branch of legendre_Q or legenq; type 2 differs by an
imaginary multiple of pi on the same interval.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py
"""

import os
import sys

import mpmath
import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


WORKING_GUARD = 96
MPMATH_DIGITS = 150

DEGREES = (
    [QQ(0), QQ(1) / QQ(3), QQ(1) / QQ(2), QQ(2) / QQ(3)]
    + [QQ(n) / QQ(2) for n in range(2, 31)]
)

ARGUMENTS = tuple(
    sorted({
        QQ(a) / QQ(b)
        for b in range(1, 5)
        for a in range(1, 5 * b + 1)
        if QQ(a) / QQ(b) > 1 and (QQ(a) / QQ(b)).denominator() == b
    })
)

PRING = PolynomialRing(QQ, "x")
X = PRING.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def field_for(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def rational(text):
    return QQ(str(text))


def q_value(nu, x, digits=100):
    field = field_for(digits)
    nu = field(nu)
    x = field(x)
    two = field(2)
    a = (nu + 2) / 2
    b = (nu + 1) / 2
    c = nu + field(QQ(3) / QQ(2))
    value = (
        field.pi().sqrt()
        * (nu + 1).gamma()
        * (1 / (x * x)).hypergeometric([a, b], [c])
    )
    value /= (two ** (nu + 1)) * c.gamma() * (x ** (nu + 1))
    for part in (value.real(), value.imag()):
        if hasattr(part, "is_finite") and not part.is_finite():
            raise ArithmeticError("non-finite value for nu=%s, x=%s"
                                  % (nu, x))
        if hasattr(part, "is_NaN") and part.is_NaN():
            raise ArithmeticError("NaN value for nu=%s, x=%s" % (nu, x))
    if not value.imag().contains_zero():
        raise ArithmeticError("non-real value for nu=%s, x=%s: %s"
                              % (nu, x, value))
    return value.real()


def legendre_polynomials(up_to):
    values = [PRING.one()]
    if up_to == 0:
        return values
    values.append(X)
    for n in range(1, up_to):
        values.append(((2 * n + 1) * X * values[n] - n * values[n - 1])
                      / QQ(n + 1))
    return values


def secondary_legendre_polynomials(up_to):
    values = [PRING.zero()]
    if up_to == 0:
        return values
    values.append(PRING(2))
    for n in range(1, up_to):
        values.append(((2 * n + 1) * X * values[n] - n * values[n - 1])
                      / QQ(n + 1))
    return values


def assert_overlaps(label, left, right):
    if not left.overlaps(right):
        raise AssertionError("%s: %s does not overlap %s" % (label, left, right))


def check_identities(digits=100):
    field = field_for(digits)
    values = {
        (nu, x): q_value(nu, x, digits)
        for nu in DEGREES
        for x in ARGUMENTS
    }

    mpmath.mp.dps = MPMATH_DIGITS
    for (nu, x), value in values.items():
        expected = mpmath.legenq(
            mpmath.mpf(str(nu)), 0, mpmath.mpf(str(x)), type=3)
        expected_ball = field(str(mpmath.re(expected)))
        assert_overlaps("mpmath nu=%s x=%s" % (nu, x),
                        field(value), expected_ball)
        imag = abs(mpmath.im(expected))
        if imag > mpmath.mpf("1e-140"):
            raise AssertionError("mpmath returned non-real value at nu=%s x=%s"
                                 % (nu, x))

    for x in ARGUMENTS:
        xb = field(x)
        q0 = values[(QQ(0), x)]
        q1 = values[(QQ(1), x)]
        initial0 = (xb + 1).log() - (xb - 1).log()
        initial0 *= QQ(1) / QQ(2)
        assert_overlaps("Q0 x=%s" % x, field(q0), initial0)
        assert_overlaps("Q1 x=%s" % x, field(q1), xb * field(q0) - 1)

    degree_set = set(DEGREES)
    for x in ARGUMENTS:
        xb = field(x)
        for nu in DEGREES:
            if nu + 1 not in degree_set or nu + 2 not in degree_set:
                continue
            recurrence = (
                field(nu + 2) * field(values[(nu + 2, x)])
                - field(2 * nu + 3) * xb * field(values[(nu + 1, x)])
                + field(nu + 1) * field(values[(nu, x)])
            )
            if not recurrence.contains_zero():
                raise AssertionError("recurrence failed at nu=%s x=%s: %s"
                                     % (nu, x, recurrence))

    legendre = legendre_polynomials(15)
    secondary = secondary_legendre_polynomials(15)
    for x in ARGUMENTS:
        xb = field(x)
        log_part = ((xb + 1).log() - (xb - 1).log()) / 2
        for n in range(16):
            rhs = field(legendre[n](x)) * log_part - field(secondary[n](x)) / 2
            assert_overlaps("integer relation n=%s x=%s" % (n, x),
                            field(values[(QQ(n), x)]), rhs)

    widest = max(values.items(), key=lambda item: item[1].rad())
    print("identity checks passed for %s values" % len(values))
    print("widest ball at nu=%s, x=%s has radius %s"
          % (widest[0][0], widest[0][1], widest[1].rad()))
    return values


class LegendreQValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T375")
    parameters = ("nu", "x")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for nu in DEGREES:
            for x in ARGUMENTS:
                yield {"nu": str(nu), "x": str(x)}

    def value(self, params, digits):
        return q_value(rational(params["nu"]), rational(params["x"]), digits)


def main():
    _key_from_stdin()
    check_identities()
    generator = LegendreQValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="computed Legendre Q values in ball arithmetic"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")


if __name__ == "__main__":
    main()
