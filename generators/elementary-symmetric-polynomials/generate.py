"""Elementary symmetric polynomials -- numberdb.org/Elementary_symmetric_polynomials

    e_k(x_1, ..., x_n) = sum over i_1 < ... < i_k of x_(i_1) ... x_(i_k)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath. `numberdb.sage` is imported
first because it is what initialises Sage.

Answers numberdb-data#102.
"""

import sys

from itertools import combinations

import numberdb.sage as numberdb
from sage.misc.misc_c import prod
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: Most variables the table runs to.
#:
#: Six is the most this database can search: matching polynomials that differ
#: only in the names of their variables needs a key found by trying
#: permutations, and beyond six that is refused rather than attempted. Here it
#: is not the binding constraint anyway -- e_3 in six variables is 217
#: characters, and length is what usually decides these tables.
MOST_VARIABLES = 6


def _ring(n):
    return PolynomialRing(ZZ, ['x%d' % (i + 1) for i in range(n)])


class ElementarySymmetricPolynomials(numberdb.Generator):

    table = 'T118'
    parameters = ('n', 'k')
    type = 'Z[]'

    #Exact: every coefficient is one.
    rigour = 'exact'

    def enumerate(self, most_variables=MOST_VARIABLES):
        for n in range(1, most_variables + 1):
            for k in range(1, n + 1):
                yield {'n': str(n), 'k': str(k)}

    def value(self, params, digits):
        n, k = int(params['n']), int(params['k'])
        ring = _ring(n)
        #Straight from the definition, rather than through
        #`SymmetricFunctions(QQ).e()[k].expand(...)`: that call needs more of
        #Sage initialised than the named imports above provide, and fails
        #with "codomain could not be determined". Checked against it anyway,
        #over the whole range of this table.
        return sum(prod(c) for c in combinations(ring.gens(), k))


if __name__ == '__main__':
    generator = ElementarySymmetricPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(message='the elementary symmetric polynomials, '
                                        'expanded in n variables'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
