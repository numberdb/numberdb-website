"""Named rational Euler products over primes -- numberdb.org/T167.

This table stores a finite shelf of constants of the form product_p F(p),
where F is a rational function and F(p) = 1 + O(p^-2), together with three
zeta-quotient rows with closed forms.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The values are computed with PARI's prodeulerrat at guarded working precision.
PARI does not return a ball or an interval for this computation, so the digits
are not marked proven. The draft records the agreement checks against OEIS and
closed-form zeta values.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.libs.pari import pari


DIGITS = 100
PARI_PRECISION = DIGITS + 40


PRODUCTS = {
    'artin': {
        'expression': '1 - 1/(p*(p - 1))',
        'comment': (r"Artin's constant is the density factor in Artin's "
                    r'primitive-root conjecture CITE{OEISArtin} '
                    r'CITE{MathWorldArtin}.'),
    },
    'stephens': {
        'expression': '1 - p/(p^3 - 1)',
        'comment': (r"Stephens' constant is the density factor for primes "
                    r"dividing terms $a^k-b$ in Stephens' two-variable "
                    r'Artin problem CITE{OEISStephens} '
                    r'CITE{MathWorldStephens}.'),
    },
    'artin-rank-2': {
        'expression': '1 - 1/(p^2*(p - 1))',
        'comment': (r'The rank-$2$ Artin constant CITE{OEISRank2Artin} is also '
                    r'written $\prod_p(1-1/(p^3-p^2))$.'),
    },
    'feller-tornier-product': {
        'expression': '1 - 2/p^2',
        'comment': (r'This is the product part of the Feller-Tornier '
                    r'constant CITE{OEISFellerTornierProduct}.'),
    },
    'feller-tornier': {
        'expression': '(1 + prodeulerrat(1 - 2/p^2))/2',
        'comment': (r'The Feller-Tornier constant is '
                    r'$\frac12(1+\prod_p(1-2/p^2))$, the affine transform '
                    r'of the product part CITE{OEISFellerTornier} '
                    r'CITE{MathWorldFellerTornier}.'),
    },
    'heath-brown-moroz': {
        'expression': '(1 - 1/p)^7*(1 + (7*p + 1)/p^2)',
        'comment': (r'The Heath-Brown-Moroz constant is from '
                    r'the density of rational points on '
                    r'$X_0^3=X_1X_2X_3$ CITE{OEISHBM} '
                    r'CITE{MathWorldHBM}.'),
    },
    'taniguchi': {
        'expression': '1 - 3/p^3 + 2/p^4 + 1/p^5 - 1/p^6',
        'comment': (r"Taniguchi's constant is from a mean "
                    r'value theorem for class numbers and regulators of '
                    r'quadratic extensions CITE{OEISTaniguchi} '
                    r'CITE{MathWorldTaniguchi}.'),
    },
    'barban': {
        'expression': '1 + (3*p^2 - 1)/(p*(p + 1)*(p^2 - 1))',
        'comment': (r"Barban's constant CITE{OEISBarban} has local factors "
                    r'$29/18,61/48,397/360,\ldots$ '
                    r'CITE{MathWorldBarban}.'),
    },
    'sarnak': {
        'expression': '1 - (p + 2)/p^3',
        'start': 3,
        'comment': (r"Sarnak's constant is the product over the odd primes "
                    r'$p\geq3$ CITE{OEISSarnak} CITE{MathWorldSarnak}.'),
    },
    'squarefree-density': {
        'expression': '1 - 1/p^2',
        'comment': (r'This is the squarefree density '
                    r'$\prod_p(1-p^{-2})=1/\zeta(2)=6/\pi^2$ '
                    r'CITE{OEISSquarefreeDensity}.'),
    },
    'ramanujan': {
        'expression': '1 + 1/p^2',
        'comment': (r'$\prod_p(1+p^{-2})=15/\pi^2$, an identity of '
                    r'Ramanujan CITE{OEISRamanujan}.'),
    },
    'landau-totient': {
        'expression': '1 + 1/(p*(p - 1))',
        'comment': (r"Landau's totient constant is "
                    r'$\prod_p(1+1/(p(p-1)))=\zeta(2)\zeta(3)/\zeta(6)$ '
                    r'CITE{OEISLandauTotient}.'),
    },
}

ORDER = (
    'artin',
    'stephens',
    'artin-rank-2',
    'feller-tornier-product',
    'feller-tornier',
    'heath-brown-moroz',
    'taniguchi',
    'barban',
    'sarnak',
    'squarefree-density',
    'ramanujan',
    'landau-totient',
)


def pari_value(key):
    """The PARI real for a row."""
    data = PRODUCTS[key]
    pari('default(realprecision, %d)' % PARI_PRECISION)
    start = int(data.get('start', 1))
    expression = data['expression']
    if 'prodeulerrat' in expression:
        return pari(expression)
    return pari('prodeulerrat(%s, 1, %d)' % (expression, start))


def decimal(value, digits):
    """A PARI real as NumberDB's plain decimal text."""
    text = str(pari('Strprintf("%%.%dg", %s)' % (int(digits), value)))
    return text.replace('E', 'e')


class NamedEulerProducts(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T167')
    parameters = ('product',)
    type = 'R'
    digits = DIGITS
    rigour = 'heuristic (agreement-checked)'

    def enumerate(self):
        for key in ORDER:
            yield {'product': key}

    def value(self, params, digits):
        key = str(params['product'])
        return {
            'number': decimal(pari_value(key), digits),
            'comment': PRODUCTS[key]['comment'],
        }


if __name__ == '__main__':
    generator = NamedEulerProducts()
    if '--publish' in sys.argv or os.environ.get('NUMBERDB_PUBLISH') == '1':
        if os.environ.get('NUMBERDB_KEY_FROM_STDIN') == '1':
            os.environ['NUMBERDB_API_KEY'] = sys.stdin.read().strip()
        print(generator.publish(
            message='named rational Euler products over primes'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
