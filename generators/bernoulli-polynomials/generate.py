"""Bernoulli polynomials -- numberdb.org/Bernoulli_polynomials

    t e^(xt) / (e^t - 1) = sum_n B_n(x) t^n / n!

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.

Answers numberdb-data#81.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import bernoulli
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: How far the table runs. Measured: B_50 is 737 characters written out and
#: the whole block is 14 KB, against a soft limit of 320 KB.
UP_TO = 50

_R = PolynomialRing(QQ, 'x')
_x = _R.gen()


class BernoulliPolynomials(numberdb.Generator):

    table = 'T114'
    parameters = ('n',)
    type = 'Q[]'

    #Exact: rational coefficients, no precision to choose.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {'n': str(n)}

    def value(self, params, digits):
        n = int(params['n'])
        #From the Bernoulli numbers rather than from Sage's polynomial
        #routine, so the arithmetic here is visibly exact: every term is a
        #rational times a binomial coefficient, and nothing is divided by a
        #Python int. `factorial(30) / k` in this environment is float
        #division, which is silently wrong past 2^53.
        from sage.arith.misc import binomial

        return sum(QQ(binomial(n, k)) * QQ(bernoulli(n - k)) * _x ** k
                   for k in range(n + 1)) if n else _R.one()


if __name__ == '__main__':
    generator = BernoulliPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(message='the Bernoulli polynomials'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
