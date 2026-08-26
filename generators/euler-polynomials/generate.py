"""Euler polynomials -- numberdb.org/Euler_polynomials

    2 e^(xt) / (e^t + 1) = sum_n E_n(x) t^n / n!

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.

Answers numberdb-data#82.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import bernoulli, binomial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: How far the table runs. Measured: E_50 is 835 characters written out and
#: the whole block is 16 KB, against a soft limit of 320 KB.
UP_TO = 50

_R = PolynomialRing(QQ, 'x')
_x = _R.gen()


def _bernoulli_polynomial(n):
    if n == 0:
        return _R.one()
    return sum(QQ(binomial(n, k)) * QQ(bernoulli(n - k)) * _x ** k
               for k in range(n + 1))


class EulerPolynomials(numberdb.Generator):

    table = 'T115'
    parameters = ('n',)
    type = 'Q[]'

    #Exact: rational coefficients throughout. Every division is between Sage
    #rationals -- `QQ(a) / QQ(b)` -- because in this environment a plain
    #`int / int` is float division and silently wrong past 2^53.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {'n': str(n)}

    def value(self, params, digits):
        n = int(params['n'])
        higher = _bernoulli_polynomial(n + 1)
        halved = higher.subs(x=_x / QQ(2))
        return QQ(2) / QQ(n + 1) * (higher - QQ(2) ** (n + 1) * halved)


if __name__ == '__main__':
    generator = EulerPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(message='the Euler polynomials'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
