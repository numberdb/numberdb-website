"""Abel polynomials -- numberdb.org/Abel_polynomials

    A_0 = 1,  A_n(x;a) = x (x - a n)^(n-1)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Polynomials in two variables, x and a. The rings are named rather than taken
from `sage.all`, so this runs on a modular passagemath as well as on a full
SageMath.

Answers numberdb-data#90.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs. Measured: A_20 is 551 characters written out.
UP_TO = 20

_R = PolynomialRing(ZZ, ['x', 'a'])
_x, _a = _R.gens()


class AbelPolynomials(numberdb.Generator):

    table = 'T123'
    parameters = ('n',)
    type = 'Z[]'

    #Exact: integer coefficients, and nothing here divides.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {'n': str(n)}

    def value(self, params, digits):
        n = int(params['n'])
        if n == 0:
            return _R.one()
        return _x * (_x - _a * n) ** (n - 1)


if __name__ == '__main__':
    generator = AbelPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(message='the Abel polynomials, in x and a'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
