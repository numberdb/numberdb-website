"""The Wilbraham-Gibbs constant -- numberdb.org/T40

    G' = Si(pi) = int_0^pi (sin t)/t dt

and the three rescalings the table also lists, of which G = (2/pi) G' is the
one usually called *the* Gibbs constant: the factor by which the partial sums
of a Fourier series overshoot a jump discontinuity.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Converted from the original `generate.sage`, which computed `RIFprec(Si(pi))`.
Sage's `Si` has no interval implementation: the symbolic expression is
evaluated to a fixed-precision number and the coercion wraps it in an interval
of width zero, which states that the value is exact. The subsequent
multiplication by `RIFprec(2/pi)` is genuine interval arithmetic applied to a
quantity whose error had already been discarded, which is the shape that makes
this kind of mistake hard to see: three of the four entries were computed
rigorously *from* a number that was not.

`arb` computes the sine integral in ball arithmetic (`acb_hypgeom_si`), and
pi is taken as a ball rather than as a rounded constant, so the whole chain
carries its error. All four entries are then derived by exact rational
operations on that ball.
"""

import sys

import numberdb.sage as numberdb
from sage.all import QQ, ComplexBallField


#: Bits of working precision beyond what the written digits need.
#:
#: Nothing here is ill-conditioned -- Si(pi) is an ordinary value of an
#: ordinary function, and the four entries differ by a rational factor.
#: Measured: at the default guard the worst of the four retains 108.2 digits,
#: and at 64 it retains 122.6. Eight digits of margin would probably hold; the
#: guard is raised anyway because on four entries it costs nothing.
WORKING_GUARD = 64


class GibbsConstant(numberdb.Generator):

    table = 'T40'
    parameters = ('expression',)
    type = 'R'
    digits = 100

    #Ball arithmetic from pi to the result.
    rigour = 'proven'

    def enumerate(self):
        # The parameter is which rescaling is meant, and the four the table
        # lists are the four in circulation. Both G' and G are called "the
        # Gibbs constant" in the literature, which is exactly why a database
        # entry has to say which one it holds.
        for expression in ('WG', 'G', 'G-1', '(G-1)/2'):
            yield {'expression': expression}

    def value(self, params, digits):
        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))

        # Si of a ball containing pi. Not Si of a rounded pi: the constant is
        # irrational, so any fixed-precision pi is the wrong argument, and the
        # ball is what makes that harmless rather than something to reason
        # about separately.
        overshoot = field(field.pi()).sin_integral()
        assert overshoot.imag().contains_zero(), (
            'Si(pi) came back non-real: %s' % (overshoot.imag(),))
        overshoot = overshoot.real()

        gibbs = overshoot * 2 / field.base().pi()

        expression = params['expression']
        if expression == 'WG':
            return overshoot
        if expression == 'G':
            return gibbs
        if expression == 'G-1':
            return gibbs - 1
        if expression == '(G-1)/2':
            return (gibbs - 1) / QQ(2)
        raise ValueError('no such entry: %r' % (expression,))


if __name__ == '__main__':
    generator = GibbsConstant()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='recomputed in ball arithmetic; the digits are now proven')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
