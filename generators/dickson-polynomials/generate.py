"""Dickson polynomials of the first kind -- numberdb.org/Dickson_polynomials

    D_0 = 2, D_1 = x, D_n(x,a) = x D_(n-1)(x,a) - a D_(n-2)(x,a)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Polynomials in two variables, x and a. The rings are named rather than taken
from `sage.all`, so this runs on a modular passagemath as well as on a full
SageMath.

Answers numberdb-data#98.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs. Measured: D_40 is 363 characters written out and
#: the whole block is 7 KB, against a soft limit of 320 KB. Short entries,
#: because the coefficients are binomial-sized rather than factorial-sized.
UP_TO = 40

_R = PolynomialRing(ZZ, ['x', 'a'])
_x, _a = _R.gens()


class DicksonPolynomials(numberdb.Generator):

    table = 'T117'
    parameters = ('n',)
    type = 'Z[]'

    #Exact: integer coefficients, and the recurrence only multiplies and
    #subtracts.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {'n': str(n)}

    def value(self, params, digits):
        previous, current = _R(2), _x
        for _ in range(int(params['n'])):
            previous, current = current, _x * current - _a * previous
        return previous


if __name__ == '__main__':
    generator = DicksonPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(message='the Dickson polynomials of the first '
                                        'kind, in x and a'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
