"""Lagrange basis polynomials on the nodes 0..d for equally spaced nodes -- numberdb.org

    l_(d,i)(x) = prod_{j != i} (x - j)/(i - j),   0 <= i <= j <= d

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.

Answers the second half of numberdb-data#121. The first half -- general point
sets -- is not a table: the nodes would be a parameter with infinitely many
values and no canonical order. The formula for that case is in the table
instead.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: How far the table runs.
#:
#: Measured: at d <= 20 the table holds 231 polynomials, the longest written
#: out is 610 characters and the whole block is 73 KB, against a soft limit of
#: 320 KB. At d <= 25 it would be 168 KB, past the half-limit this project
#: aims at so that the next person can extend a table without breaching it.
UP_TO = 20

_R = PolynomialRing(QQ, 'x')
_x = _R.gen()


class LagrangeBasisPolynomials(numberdb.Generator):

    table = 'T112'
    parameters = ('d', 'i')
    type = 'Q[]'

    #Exact: rational coefficients, no precision to choose.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for d in range(up_to + 1):
            for i in range(d + 1):
                yield {'d': str(d), 'i': str(i)}

    def value(self, params, digits):
        d, i = int(params['d']), int(params['i'])
        #Built in the ring rather than multiplied out of fractions: at d = 0
        #the product is empty and would otherwise come back as the integer 1.
        polynomial = _R.one()
        for j in range(d + 1):
            if j != i:
                polynomial *= (_x - j) / QQ(i - j)
        return polynomial


if __name__ == '__main__':
    generator = LagrangeBasisPolynomials()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='the Lagrange basis polynomials for equally spaced nodes')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
