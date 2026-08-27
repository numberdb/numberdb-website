"""Schur polynomials -- numberdb.org/Schur_polynomials

    s_lambda = det(h_(lambda_i - i + j))          (Jacobi-Trudi)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Computed by Jacobi-Trudi rather than through Sage's SymmetricFunctions, whose
`.expand()` needs more of Sage initialised than the named imports below
provide -- and rather than from the ratio of determinants in the definition,
which would divide. Checked against the library over the whole range of this
table.

Answers numberdb-data#103.
"""

import sys
from itertools import combinations_with_replacement, permutations

import numberdb.sage as numberdb
from sage.misc.misc_c import prod
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs: partitions of at most 4, in at most 4 variables,
#: where the longest entry is 387 characters. These grow faster than the
#: monomial polynomials they expand into, which is why this stops one
#: variable sooner than that table.
MOST_VARIABLES = 4
LARGEST_PARTITION = 4


def _partitions(total, longest=None):
    if longest is None:
        longest = total
    if total == 0:
        yield []
        return
    for part in range(min(total, longest), 0, -1):
        for rest in _partitions(total - part, part):
            yield [part] + rest


def _determinant(rows, ring):
    """The determinant, expanded over permutations.

    Written out rather than taken from `matrix(...).determinant()`, which
    reaches for a module the named imports above do not load and fails with
    "module 'sage.rings.polynomial' has no attribute
    'laurent_polynomial_ring'". A partition of at most four has at most four
    parts, so this is at most 24 terms.
    """
    size = len(rows)
    total = ring.zero()
    for order in permutations(range(size)):
        sign, seen = 1, list(order)
        #Parity by counting inversions, which is cheap at this size.
        for i in range(size):
            for j in range(i + 1, size):
                if seen[i] > seen[j]:
                    sign = -sign
        term = ring.one()
        for i, j in enumerate(order):
            term *= rows[i][j]
        total += sign * term
    return total


class SchurPolynomials(numberdb.Generator):

    table = 'T122'
    parameters = ('n', 'lambda')
    type = 'Z[]'

    #Exact: integer coefficients, and Jacobi-Trudi only multiplies, adds and
    #subtracts. The ratio of determinants in the definition would divide.
    rigour = 'exact'

    def enumerate(self, most_variables=MOST_VARIABLES,
                  largest=LARGEST_PARTITION):
        for n in range(1, most_variables + 1):
            for size in range(1, largest + 1):
                for partition in _partitions(size):
                    if len(partition) <= n:
                        yield {'n': str(n),
                               'lambda': ','.join(str(p) for p in partition)}

    def value(self, params, digits):
        n = int(params['n'])
        partition = [int(p) for p in params['lambda'].split(',')]
        ring = PolynomialRing(ZZ, ['x%d' % (i + 1) for i in range(n)])

        def homogeneous(degree):
            if degree < 0:
                return ring.zero()
            if degree == 0:
                return ring.one()
            return sum(prod(c) for c in
                       combinations_with_replacement(ring.gens(), degree))

        size = len(partition)
        rows = [[homogeneous(partition[i] - i + j) for j in range(size)]
                for i in range(size)]
        return _determinant(rows, ring)


if __name__ == '__main__':
    generator = SchurPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(message='the Schur polynomials, by Jacobi-Trudi'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
