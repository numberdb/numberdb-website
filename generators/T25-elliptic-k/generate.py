"""Complete elliptic integral of the first kind K(m) -- numberdb.org/T25

    K(m) = int_0^(pi/2) dt / sqrt(1 - m sin^2 t)

Run it with SageMath:

    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Converted from the `generate.sage` that produced the table originally, and the
conversion changed what the table may claim about itself.

The old script computed `elliptic_kc(m)` and wrote `RIFprec(number)`. That
looks like interval arithmetic and is not. `elliptic_kc` has no interval
implementation in Sage: it returns a fixed-precision number, and coercing one
of those into `RealIntervalField` produces an interval of width zero -- a
claim of infinite accuracy, made by the coercion rather than by anything that
computed the value. Measured here: `RIF(elliptic_kc(1/3))` has diameter 0.

The table said `proven` on the strength of that shape for a day. It said
`heuristic` after it was noticed, which was true and unsatisfying: the digits
were almost certainly right, and nothing in the file established it.

They are established now. `arb` implements the complete elliptic integrals in
ball arithmetic (`acb_elliptic_k`), which Sage exposes as
`ComplexBallField(prec)(m).elliptic_k()`, and a ball carries its own error
bound through every step. So the width of the returned ball is a bound on the
error, derived rather than asserted, and the digits written are the digits it
supports.

That also settles the question of evaluating at a point we cannot represent.
Half of these arguments -- 1/3, 7/9, 31/50 -- are not dyadic and so cannot be
a floating point number, and K is steep near m = 1: at m = 49/50 the
derivative is about 12, so an argument wrong in its last bit moves the answer
by more than that bit. `CBF(QQ(1)/3)` is not a rounded 1/3 but a ball
containing it, and `elliptic_k` of a ball encloses the image of everything in
that ball. The argument's own inexactness is inside the bound rather than
outside it, and nothing needs to be said about the derivative.

Convention, checked rather than assumed: `arb` takes the *parameter* m, as
Sage's `elliptic_kc` does, not the modulus k = sqrt(m). At m = 1/2 both give
1.8540746773013719..., while the modulus reading would give
1.6857503548125960... -- a difference that would have been silently wrong in
every entry rather than obviously wrong in one.
"""

import sys

import numberdb.sage as numberdb
from sage.all import QQ, ComplexBallField


#: Bits of working precision beyond what the written digits need.
#:
#: A ball computation does not need this to be right, only to be enough: if the
#: guard is too small the result comes back wider than the digits promised and
#: the package refuses the run, rather than writing digits that are not there.
#: Measured over the whole table -- K has a logarithmic singularity at m = 1,
#: so the entries with m near 1 cost the most: at the default guard the worst
#: entry (m = 27/28) retained 108.3 digits, and at 64 the worst (m = 29/30)
#: retains 122.7. Eight digits of margin on a table somebody may extend
#: towards m = 1 is not a margin.
WORKING_GUARD = 64


class CompleteEllipticK(numberdb.Generator):

    table = 'T25'
    parameters = ('m',)
    type = 'R'
    digits = 100

    #Ball arithmetic from the argument to the result.
    rigour = 'proven'

    def enumerate(self, denominator=50):
        # The original range, kept exactly: every reduced fraction a/b with
        # b at most 50 and 0 <= a/b < 1. m = 0 is included and is a real
        # entry -- K(0) = pi/2, the quarter period of a circle.
        for b in range(1, denominator + 1):
            for a in range(0, denominator + 1):
                m = QQ(a) / QQ(b)
                if m >= 1 or m.denominator() != b:
                    continue
                yield {'m': str(m)}

    def value(self, params, digits):
        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        value = field(QQ(params['m'])).elliptic_k()

        # K(m) is real for m < 1, but arb computes it as a complex ball and
        # the imaginary part comes back as a ball around zero rather than
        # zero. Discarding it is only sound if it *is* around zero: if a
        # convention or a branch cut ever moved under us, this is where it
        # would show, rather than in a hundred digits of a wrong real part.
        assert value.imag().contains_zero(), (
            'K(%s) came back with a non-real imaginary part: %s'
            % (params['m'], value.imag()))
        return value.real()


if __name__ == '__main__':
    generator = CompleteEllipticK()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='recomputed in ball arithmetic; the digits are now proven')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
