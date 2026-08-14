"""Zeros of Bessel functions of the second kind -- numberdb.org/T21

The n-th positive zero of Y_alpha(x), for alpha in halves and n = 1..50.

Run it with SageMath:

    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are not proven**, and the file says so in `rigour` below.

mpmath computes the zeros of Y at a working precision and returns a float with no
error bound. Its documentation says nothing about the accuracy of these
functions; its interval mode, `mpmath.iv`, does not implement them; and Sage's
RealBallField, which would be rigorous, does not expose Bessel at all. So
there is no way to make this rigorous with what is installed.

What can be done, and is: compute at two precisions and keep only the digits
they agree on. The original script computed once at 1.5x the digits it wrote
and trusted the margin -- and `mpmath.nstr(z, 100)` will happily print a
hundred digits of a value computed to thirty, the last seventy being the
decimal expansion of a binary approximation. Measured on the first Airy zero,
30 digits against 300 diverge at the 40th.
"""

import sys

import mpmath
import numberdb.sage as numberdb


#: The two working precisions, in decimal digits, written down rather than
#: derived. The first is what the original script used for a hundred written
#: digits; the second is enough more to disagree if the first were wrong.
#:
#: Stated here because the file attached to a table is meant to be how those
#: numbers were made. Nothing escalates on failure: if the agreement is ever
#: too short, raise these and run it again.
WORKING = (150, 200)


class BesselYZeros(numberdb.Generator):

    table = 'T21'
    parameters = ('alpha', 'n')
    type = 'R'
    digits = 100
    rigour = 'heuristic (agreement-checked)'

    def enumerate(self, orders=20, up_to=50):
        # alpha runs over halves, as the table holds them: 0, 1/2, 1, ...
        from sage.all import QQ

        for a in range(0, orders + 1):
            for n in range(1, up_to + 1):
                yield {'alpha': QQ(a) / 2, 'n': n}

    def value(self, params, digits):
        alpha, n = params['alpha'], params['n']
        return numberdb.agreeing(
            lambda working: self._zero(alpha, n, working), at=WORKING)

    @staticmethod
    def _zero(alpha, n, working_digits):
        """The n-th the zeros of Y of order alpha, as a string of that many digits.

        A string rather than an mpmath float: the value crosses into Sage here,
        and a string carries the digits that were computed rather than a binary
        approximation of them.
        """
        mpmath.mp.dps = working_digits
        order = mpmath.mpf(alpha.numerator()) / int(alpha.denominator())
        return mpmath.nstr(mpmath.mp.besselyzero(order, n, derivative=0), working_digits,
                           strip_zeros=False)


if __name__ == '__main__':
    generator = BesselYZeros()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='recomputed with the numberdb package; digits now '
                    'agreement-checked at two precisions rather than assumed'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
