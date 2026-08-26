"""Bernstein basis polynomials -- numberdb.org/Bernstein_basis_polynomials

    b_(v,n)(x) = C(n,v) x^v (1-x)^(n-v),   0 <= v <= n

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath. `numberdb.sage` is imported
first because it is what initialises Sage.

Answers numberdb-data#122.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs.
#:
#: Measured: at n <= 25 the table holds 351 polynomials, the longest written
#: out is 354 characters and the whole block is 50 KB, against a soft limit of
#: 320 KB. Every entry stays short because the coefficients are binomial
#: products rather than anything that grows; what grows is the count, since
#: degree n contributes n+1 of them.
UP_TO = 25

_R = PolynomialRing(ZZ, 'x')
_x = _R.gen()


class BernsteinBasisPolynomials(numberdb.Generator):

    table = 'T111'
    parameters = ('n', 'v')
    type = 'Z[]'

    #Exact: integer coefficients, no precision to choose.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            for v in range(n + 1):
                yield {'n': str(n), 'v': str(v)}

    def value(self, params, digits):
        n, v = int(params['n']), int(params['v'])
        #Expanded, which is what makes two polynomials comparable here.
        return _R(binomial(n, v) * _x ** v * (1 - _x) ** (n - v))


if __name__ == '__main__':
    generator = BernsteinBasisPolynomials()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='the Bernstein basis polynomials, expanded')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
