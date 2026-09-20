"""Secondary Hermite polynomials q_n, physicist's convention -- numberdb.org/T371

    q_n(x) = integral (H_n(t) - H_n(x))/(t - x) exp(-t^2)/sqrt(pi) dt.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The weight is normalised to a probability density, so q_0 = 0, q_1 = 2 and
q_(n+1) = 2*x*q_n - 2*n*q_(n-1).  The unnormalised Hermite weight would
multiply every entry by sqrt(pi), which is not a polynomial over ZZ or QQ.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


UP_TO = 50

RING = PolynomialRing(ZZ, "x")
X = RING.gen()

QRING = PolynomialRing(QQ, "x")
QX = QRING.gen()
TRING = PolynomialRing(QRING, "t")
T = TRING.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def factorial_zz(n):
    out = ZZ(1)
    for k in range(2, int(n) + 1):
        out *= ZZ(k)
    return out


def hermite_polynomials(up_to=UP_TO):
    values = [RING.one()]
    if up_to == 0:
        return values
    values.append(2 * X)
    for n in range(1, int(up_to)):
        values.append(2 * X * values[n] - 2 * ZZ(n) * values[n - 1])
    return values


def secondary_polynomials(up_to=UP_TO):
    values = [RING.zero()]
    if up_to == 0:
        return values
    values.append(RING(2))
    for n in range(1, int(up_to)):
        values.append(2 * X * values[n] - 2 * ZZ(n) * values[n - 1])
    return values


def gaussian_moments(up_to):
    """Moments of exp(-t^2)/sqrt(pi), through degree up_to."""
    moments = [QQ(0) for _ in range(int(up_to) + 1)]
    moments[0] = QQ(1)
    if up_to >= 1:
        moments[1] = QQ(0)
    for n in range(2, int(up_to) + 1):
        moments[n] = QQ(n - 1) * moments[n - 2] / QQ(2)
    return moments


def hermite_over_t(up_to):
    values = [TRING.one()]
    if up_to == 0:
        return values
    values.append(2 * T)
    for n in range(1, int(up_to)):
        values.append(2 * T * values[n] - 2 * QQ(n) * values[n - 1])
    return values


def hermite_over_x(up_to):
    values = [QRING.one()]
    if up_to == 0:
        return values
    values.append(2 * QX)
    for n in range(1, int(up_to)):
        values.append(2 * QX * values[n] - 2 * QQ(n) * values[n - 1])
    return values


def secondary_from_moments(n):
    moments = gaussian_moments(n)
    h_t = hermite_over_t(n)[n]
    h_x = TRING(hermite_over_x(n)[n])
    quotient, remainder = (h_t - h_x).quo_rem(T - TRING(QX))
    if remainder:
        raise AssertionError("division by t - x left remainder at n=%s" % n)

    value = QRING.zero()
    for degree in range(quotient.degree() + 1):
        value += quotient[degree] * moments[degree]
    return value


def as_integer_polynomial(polynomial):
    coefficients = polynomial.list()
    if any(coefficient not in ZZ for coefficient in coefficients):
        raise AssertionError("non-integral coefficient in %s" % polynomial)
    return RING([ZZ(coefficient) for coefficient in coefficients])


def check_identities(up_to=UP_TO):
    hermite = hermite_polynomials(up_to)
    secondary = secondary_polynomials(up_to)

    expected_start = [
        RING.zero(),
        RING(2),
        4 * X,
        8 * X**2 - 8,
        16 * X**3 - 40 * X,
    ]
    if secondary[:5] != expected_start:
        raise AssertionError("initial values changed")

    for n, q in enumerate(secondary):
        if q != as_integer_polynomial(secondary_from_moments(n)):
            raise AssertionError("moment integral disagrees at n=%s" % n)
        if n == 0:
            if q != 0:
                raise AssertionError("q_0 is not zero")
            continue
        if q.degree() != n - 1:
            raise AssertionError("degree failed at n=%s" % n)
        if q.leading_coefficient() != ZZ(2) ** n:
            raise AssertionError("leading coefficient failed at n=%s" % n)
        for exponent, coefficient in enumerate(q.list()):
            if coefficient and (exponent - (n - 1)) % 2:
                raise AssertionError("parity failed at n=%s" % n)

        weight_identity = (
            q * hermite[n].derivative() - ZZ(2) ** (n + 1) * factorial_zz(n)
        )
        if weight_identity % hermite[n] != 0:
            raise AssertionError("Gauss-Hermite weight identity failed at n=%s"
                                 % n)

    return secondary


VALUES = check_identities()


class SecondaryHermitePhysicistPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T371")
    parameters = ("n",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(int(up_to) + 1):
            yield {"n": n}

    def value(self, params, digits):
        return VALUES[int(params["n"])]


def main():
    _key_from_stdin()
    generator = SecondaryHermitePhysicistPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="secondary Hermite polynomials in probability normalisation"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
