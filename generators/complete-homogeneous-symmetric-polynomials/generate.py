"""Complete homogeneous symmetric polynomials -- numberdb.org

    h_k(x_1, ..., x_n) = sum of every monomial of degree k

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Computed from the definition rather than through Sage's SymmetricFunctions:
`.expand()` needs more of Sage initialised than the named imports below
provide. Checked against it over the whole range of this table.

Answers numberdb-data#105.
"""

import sys
from itertools import combinations_with_replacement

import numberdb.sage as numberdb
from sage.misc.misc_c import prod
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs.
#:
#: These grow fastest of the five families: h_3 in six variables is 559
#: characters written out and h_6 would be 6969. The rule across the five is
#: the largest complete rectangle whose longest entry stays under about 600
#: characters -- a table of entries nobody can read is not a reference.
MOST_VARIABLES = 6
HIGHEST_DEGREE = 3


class CompleteHomogeneousSymmetricPolynomials(numberdb.Generator):

    table = 'T120'
    parameters = ('n', 'k')
    type = 'Z[]'

    #Exact: every coefficient is one.
    rigour = 'exact'

    def enumerate(self, most_variables=MOST_VARIABLES,
                  highest_degree=HIGHEST_DEGREE):
        for n in range(1, most_variables + 1):
            for k in range(1, highest_degree + 1):
                yield {'n': str(n), 'k': str(k)}

    def value(self, params, digits):
        n, k = int(params['n']), int(params['k'])
        ring = PolynomialRing(ZZ, ['x%d' % (i + 1) for i in range(n)])
        return sum(prod(c)
                   for c in combinations_with_replacement(ring.gens(), k))


if __name__ == '__main__':
    generator = CompleteHomogeneousSymmetricPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(
            message='the complete homogeneous symmetric polynomials'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
