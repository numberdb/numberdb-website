"""Complete elliptic integral of the third kind Pi(n, m) -- numberdb.org/T59

    Pi(n, m) = int_0^(pi/2) dt / ((1 - n sin^2 t) sqrt(1 - m sin^2 t))

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Converted from the original `generate.sage`, which computed
`elliptic_pi(n, pi/2, m)` -- the incomplete integral at amplitude pi/2 -- and
coerced the fixed-precision result into an interval field, which records no
error of its own. `arb` computes the complete integral directly and in ball
arithmetic (`acb_elliptic_pi`), so the bound is derived.

Two conventions to get right, both checked against the stored values rather
than assumed, because either would be silently wrong in every entry instead of
obviously wrong in one:

  * the second argument is the parameter m, not the modulus sqrt(m);
  * the order is `CBF(n).elliptic_pi(m)` -- the characteristic first. At
    n = 1/3, m = 1/2 that gives 2.3107949907542818..., which is what the table
    holds; the other order gives 2.4952460470776346..., which is Pi(1/2, 1/3)
    and belongs to a different entry of this same table.

The n = 0 entry carries no number. Pi(0, m) is K(m), and the table says so
with a link rather than by repeating 993 digits that live under T25. A
generator cannot write prose and does not try: `enumerate` skips n = 0, and
the entry stays as whoever wrote it left it.
"""

import sys

import numberdb.sage as numberdb
from sage.all import QQ, ComplexBallField


#: Bits of working precision beyond what the written digits need.
#:
#: Pi has a pole as n approaches 1, so the entries with the largest n cost the
#: most. Measured over the whole table: at the default guard the worst entry
#: (n = 9/10, m = 8/9) retains 108.4 digits; at 64 the worst (n = m = 9/10)
#: retains 122.9.
WORKING_GUARD = 64


class CompleteEllipticPi(numberdb.Generator):

    table = 'T59'
    parameters = ('n', 'm')
    type = 'R'
    digits = 100

    #Ball arithmetic from the arguments to the result.
    rigour = 'proven'

    def enumerate(self, denominator=10):
        # As the original: reduced fractions with denominator at most 10 in
        # both arguments, each in [0, 1). n = 0 is skipped -- see the note
        # above; it is the one entry here that is a statement rather than a
        # number.
        fractions = []
        for b in range(1, denominator + 1):
            for a in range(0, denominator + 1):
                q = QQ(a) / QQ(b)
                if q >= 1 or q.denominator() != b:
                    continue
                fractions.append(q)

        for n in fractions:
            if n == 0:
                continue
            for m in fractions:
                yield {'n': str(n), 'm': str(m)}

    def value(self, params, digits):
        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        value = field(QQ(params['n'])).elliptic_pi(field(QQ(params['m'])))

        # Real for n, m < 1. Beyond n = 1 the integrand has a pole inside the
        # range and the principal value is a different question; the assert
        # holds us to the region the table covers.
        assert value.imag().contains_zero(), (
            'Pi(%s, %s) came back with a non-real imaginary part: %s'
            % (params['n'], params['m'], value.imag()))
        return value.real()


if __name__ == '__main__':
    generator = CompleteEllipticPi()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='recomputed in ball arithmetic; the digits are now proven')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
