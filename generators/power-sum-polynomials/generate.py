"""Power sum symmetric polynomials -- numberdb.org/Power_sum_polynomials

    p_k(x_1, ..., x_n) = x_1^k + ... + x_n^k

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.

Answers numberdb-data#104.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: Six variables is the most this database searches, and here it costs
#: nothing: p_k has n terms whatever k is, so the longest entry in the table
#: is 39 characters. That is why this one runs to k = 12 where the others
#: stop much sooner -- the length that decides the rest never bites.
MOST_VARIABLES = 6
HIGHEST_POWER = 12


class PowerSumPolynomials(numberdb.Generator):

    table = 'T119'
    parameters = ('n', 'k')
    type = 'Z[]'

    #Exact: every coefficient is one.
    rigour = 'exact'

    def enumerate(self, most_variables=MOST_VARIABLES,
                  highest_power=HIGHEST_POWER):
        for n in range(1, most_variables + 1):
            for k in range(1, highest_power + 1):
                yield {'n': str(n), 'k': str(k)}

    def value(self, params, digits):
        n, k = int(params['n']), int(params['k'])
        ring = PolynomialRing(ZZ, ['x%d' % (i + 1) for i in range(n)])
        return sum(g ** k for g in ring.gens())


if __name__ == '__main__':
    generator = PowerSumPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(message='the power sum symmetric polynomials'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
