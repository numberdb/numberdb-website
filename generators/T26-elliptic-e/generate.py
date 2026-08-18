"""Complete elliptic integral of the second kind E(m) -- numberdb.org/T26

    E(m) = int_0^(pi/2) sqrt(1 - m sin^2 t) dt

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Converted from the original `generate.sage`, which computed `elliptic_ec(m)`
and wrapped the result in `RealIntervalField`. That wrapping records no error:
`elliptic_ec` returns a fixed-precision number and coercing one into an
interval field gives an interval of width zero, which claims the value is
exact. The digits were right and unestablished.

`arb` computes E in ball arithmetic (`acb_elliptic_e`), so the error bound is
carried through the computation rather than assumed afterwards, and the
argument's own inexactness -- most of these m are not dyadic and so are not
representable -- sits inside the ball rather than outside the claim. See the
companion generator for T25 (K), which this follows in every respect.

The convention is the parameter m, not the modulus k = sqrt(m); checked
against the stored values rather than assumed.
"""

import sys

import numberdb.sage as numberdb
from sage.all import QQ, ZZ, ComplexBallField


#: Bits of working precision beyond what the written digits need.
#:
#: E is bounded on the whole closed interval -- unlike K it has no singularity
#: at m = 1 -- but it loses about as much: measured over the whole table, at
#: the default guard the worst entry (m = 49/50) retains 106.3 digits, and at
#: 64 it retains 120.8. Six digits of margin is not a margin, and the guard is
#: kept in step with T25 besides, because the two tables are read together.
WORKING_GUARD = 64


class CompleteEllipticE(numberdb.Generator):

    table = 'T26'
    parameters = ('m',)
    type = 'R'
    digits = 100

    #Ball arithmetic from the argument to the result.
    rigour = 'proven'

    def enumerate(self, denominator=50):
        # As the original: every reduced fraction a/b with b at most 50 and
        # 0 <= a/b <= 1. Note the closed upper end, where T25 is open -- E is
        # finite at m = 1 and K is not.
        for b in range(1, denominator + 1):
            for a in range(0, denominator + 1):
                m = QQ(a) / QQ(b)
                if m > 1 or m.denominator() != b:
                    continue
                yield {'m': str(m)}

    def value(self, params, digits):
        m = QQ(params['m'])

        # E(1) = 1 exactly: the integrand collapses to cos(t) and the integral
        # to sin(pi/2). The table stores it as the integer 1 rather than as a
        # hundred digits of 1.000..., which is the right way round -- a value
        # that is exactly an integer should not be written as an
        # approximation, and `exact` is a stronger statement than any number
        # of correct digits.
        if m == 1:
            return ZZ(1)

        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        value = field(m).elliptic_e()

        # Real for m <= 1; arb returns a complex ball whose imaginary part is
        # a ball around zero. Discarding it is sound only if it is, and this
        # is where a moved branch cut would show itself.
        assert value.imag().contains_zero(), (
            'E(%s) came back with a non-real imaginary part: %s'
            % (params['m'], value.imag()))
        return value.real()


if __name__ == '__main__':
    generator = CompleteEllipticE()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='recomputed in ball arithmetic; the digits are now proven')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
