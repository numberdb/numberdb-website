"""Mott polynomials s_n(x) -- numberdb.org/T185.

    sum_{n >= 0} s_n(x) t^n/n! = exp(x*(sqrt(1 - t^2) - 1)/t)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: Measured before the draft was created: n = 0..45 gives 46 entries, s_45 is
#: 1147 characters written out, and the entries block is 19.4 KB.
UP_TO = 45

_R = PolynomialRing(QQ, "x")
_x = _R.gen()
_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _catalan(k):
    value = QQ(factorial(ZZ(2 * k)))
    value /= QQ(factorial(ZZ(k))) * QQ(factorial(ZZ(k + 1)))
    return value


def _integral_zero_constant(polynomial):
    out = _R.zero()
    for degree, coefficient in enumerate(polynomial.list()):
        out += coefficient * _x ** (degree + 1) / QQ(degree + 1)
    return out


def mott_polynomials(up_to=UP_TO):
    if up_to in _CACHE:
        return _CACHE[up_to]

    values = [_R.one()]
    for n in range(1, up_to + 1):
        derivative = _R.zero()
        for k in range((n - 1) // 2 + 1):
            j = n - 1 - 2 * k
            scale = QQ(factorial(ZZ(n)))
            scale /= QQ(factorial(ZZ(j))) * QQ(2 ** (2 * k + 1))
            derivative -= scale * _catalan(k) * values[j]
        values.append(_integral_zero_constant(derivative))

    _CACHE[up_to] = values
    return values


def mott_polynomial(n):
    return mott_polynomials(n)[n]


class MottPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T185")
    parameters = ("n",)
    type = "Q[]"

    # Exact: rational coefficients, no precision to choose.
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return mott_polynomial(int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = MottPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Mott polynomials in the sqrt(1 - t^2) convention, n = 0..%d"
                    % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
