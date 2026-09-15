"""Ehrhart polynomials of hypersimplices -- numberdb.org/T234

For 4 <= n <= 20 and 2 <= k <= floor(n/2), this stores the Ehrhart
polynomial L_{Delta(k,n)}(t) of the hypersimplex
Delta(k,n) = {x in [0,1]^n : sum x_i = k}.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The Ehrhart polynomial is computed by exact inclusion-exclusion:

    L(t) = sum_i (-1)^i binomial(n, i) binomial((k-i)t - i + n - 1, n - 1).
"""

import numberdb.sage as numberdb

import os
import sys
from math import comb, factorial

from sage.rings.rational_field import QQ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


T234 = "T234"
UP_TO_N = 20

_T = PolynomialRing(QQ, "t")
_t = _T.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def binomial_polynomial(argument, degree):
    value = _T.one()
    for j in range(degree):
        value *= argument - QQ(j)
    return value / QQ(factorial(degree))


def ehrhart_polynomial(n, k):
    degree = n - 1
    value = _T.zero()
    for i in range(k):
        value += (
            QQ((-1) ** i * comb(n, i))
            * binomial_polynomial((k - i) * _t - i + n - 1, degree)
        )
    return value


class HypersimplexEhrhartPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", T234)
    parameters = ("n", "k")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to_n=UP_TO_N):
        for n in range(4, up_to_n + 1):
            for k in range(2, n // 2 + 1):
                yield {"n": str(n), "k": str(k)}

    def value(self, params, digits):
        n = int(params["n"])
        k = int(params["k"])
        #No `param-latex` here. It overrides the label of the
        #entry's own parameter group, so naming the polynomial put
        #`$L_{\Delta(2,4)}(t)$` in the column that should read `2`
        #-- the column header already says which polynomial this
        #table holds.
        return {
            "number": ehrhart_polynomial(n, k),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = HypersimplexEhrhartPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="hypersimplex Ehrhart polynomials",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
