"""Values of the Barnes G-function at rational numbers -- numberdb.org/T93

    G(z+1) = Gamma(z) G(z),   G(1) = 1

so that G(n) = 0! 1! 2! ... (n-2)! at positive integers.

Run it with SageMath:

    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Converted from the original `generate.sage`, which called `mpmath.barnesg` at
100*2 decimal digits and wrote the result through
`real_interval_to_sage_string` without ever forming an interval. mpmath's
documentation states no accuracy for `barnesg`, and mpmath's numbers carry no
error term, so the file recorded no reason for the digits it wrote.

`arb` computes the Barnes G-function in ball arithmetic (`acb_barnes_g`), and
the width of the resulting ball bounds the error. The integer arguments are
returned exactly, as products of factorials, rather than as a hundred digits
of an integer -- which is both stronger and shorter.

The table's range is inherited unchanged: reduced fractions a/b with
1 <= b <= 30 and |a| <= 30. The negative half is included and is where the
function is interesting -- G has zeros at the non-positive integers and
oscillates in sign between them -- but a <= 0 with b = 1 is excluded, because
G vanishes there and a zero is not a value this table means to list.
"""

import sys

import numberdb.sage as numberdb
from sage.all import QQ, ZZ, ComplexBallField, factorial, prod


#: Bits of working precision beyond what the written digits need.
#:
#: G grows and shrinks fast, and the negative arguments come through the
#: reflection formula with cancellation. Measured over the whole table: at the
#: default guard the worst entry (s = -29/3) retains 105.5 digits, and at 64 it
#: retains 119.9 -- the worst entry is the same one either way, so the cost is
#: the argument's, not the guard's.
WORKING_GUARD = 64


class BarnesG(numberdb.Generator):

    table = 'T93'
    parameters = ('s',)
    type = 'R'
    digits = 100

    #Ball arithmetic, and exact integers where the value is one.
    rigour = 'proven'

    def enumerate(self, bound=30):
        for b in range(1, bound + 1):
            for a in range(-bound, bound + 1):
                s = QQ(a) / QQ(b)
                if s.denominator() != b:
                    continue
                # G(s) = 0 for s a non-positive integer.
                if b == 1 and a <= 0:
                    continue
                yield {'s': str(s)}

    def value(self, params, digits):
        s = QQ(params['s'])

        # At a positive integer the value is a product of factorials, which is
        # an integer: G(5) is 12, not 12.000... to a hundred places. Returning
        # it exactly means the entry claims `exact` rather than a hundred
        # correct digits, which is a different and better claim.
        if s.denominator() == 1:
            return ZZ(prod(factorial(k) for k in range(0, ZZ(s) - 1)))

        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        value = field(s).barnes_g()

        # G is real on the real line; arb returns a complex ball.
        assert value.imag().contains_zero(), (
            'G(%s) came back with a non-real imaginary part: %s'
            % (params['s'], value.imag()))
        return value.real()


if __name__ == '__main__':
    generator = BarnesG()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='recomputed in ball arithmetic; the digits are now proven')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
