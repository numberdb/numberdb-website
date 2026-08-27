"""Bernoulli polynomials of the second kind -- numberdb.org

    t/log(1+t) * (1+t)^x = sum_n psi_n(x) t^n / n!

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Computed by coefficient arithmetic rather than in a power series ring: series
`.log()` and `.inverse()` reach for Sage's symbolic machinery, which the named
imports below do not initialise. Everything here is multiplication and
addition of rationals, which is also what keeps it exact -- see the note on
`_factorial`. Checked against the power series version, and against the Cauchy
numbers of the first kind.

Answers numberdb-data#83.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: How far the table runs. Measured: psi_25 is 636 characters written out.
UP_TO = 25

_R = PolynomialRing(QQ, 'x')
_x = _R.gen()


def _factorial(n):
    """n! as a Sage integer.

    Written out rather than imported: `sage.arith.misc.factorial` pulls in
    symbolic machinery here, and in a plain `sage -python` the builtin returns
    a Python int, whose division is float division and silently wrong past
    2^53.
    """
    out = ZZ(1)
    for i in range(2, n + 1):
        out *= i
    return out


def _all_up_to(upto):
    """psi_0 ... psi_upto, by multiplying two series coefficient by coefficient."""
    #log(1+t)/t = sum_k (-1)^k t^k/(k+1), whose constant term is 1.
    quotient = [QQ((-1) ** k) / QQ(k + 1) for k in range(upto + 1)]
    #Its reciprocal, by the usual recurrence for a series with constant term 1.
    reciprocal = [QQ(1)]
    for n in range(1, upto + 1):
        reciprocal.append(-sum(quotient[k] * reciprocal[n - k]
                               for k in range(1, n + 1)))
    #(1+t)^x = sum_k binomial(x, k) t^k, with binomial(x, k) a polynomial.
    binomials = []
    for k in range(upto + 1):
        term = _R.one()
        for i in range(k):
            term *= (_x - i)
        binomials.append(term / QQ(_factorial(k)))
    return [sum(reciprocal[k] * binomials[n - k] for k in range(n + 1))
            * _factorial(n) for n in range(upto + 1)]


class BernoulliPolynomialsSecondKind(numberdb.Generator):

    table = 'T124'
    parameters = ('n',)
    type = 'Q[]'

    #Exact: rational coefficients throughout, every division between Sage
    #rationals.
    rigour = 'exact'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._values = None

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {'n': str(n)}

    def value(self, params, digits):
        if self._values is None:
            self._values = _all_up_to(UP_TO)
        return self._values[int(params['n'])]


if __name__ == '__main__':
    generator = BernoulliPolynomialsSecondKind()

    if '--publish' in sys.argv:
        print(generator.publish(
            message='the Bernoulli polynomials of the second kind'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
