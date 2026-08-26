"""Bessel polynomials -- numberdb.org/Bessel_polynomials

    y_0 = 1, y_1 = x + 1, y_n = (2n-1) x y_(n-1) + y_(n-2)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Built from the recurrence rather than from the closed form

    y_n(x) = sum_k (n+k)! / ((n-k)! k! 2^k) x^k

because that form divides, and in this environment `factorial(n)` is a Python
int, so `/` is float division: from n = 16 the coefficients silently lose
precision and come out wrong in their last digits. The recurrence uses only
multiplication and addition of exact integers. Checked: the two agree for
n <= 30 once the closed form is evaluated over the rationals.

Answers numberdb-data#80.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs. Measured: y_30 is 1025 characters written out and
#: the whole block is 12 KB, against a soft limit of 320 KB.
UP_TO = 30

_R = PolynomialRing(ZZ, 'x')
_x = _R.gen()


class BesselPolynomials(numberdb.Generator):

    table = 'T116'
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
        previous, current = _R.one(), _x + 1
        for i in range(2, n + 1):
            previous, current = current, (2 * i - 1) * _x * current + previous
        return current


if __name__ == '__main__':
    generator = BesselPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(message='the Bessel polynomials, from the '
                                        'recurrence so that nothing divides'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
