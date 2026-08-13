"""Volume of the d-dimensional unit ball -- numberdb.org/T27

    B_d = pi^(d/2) / Gamma(d/2 + 1)

Run it with SageMath:

    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Converted from the `generate.sage` that produced the table originally, which
wrote a numbers.yaml for a pull request against the data repository. That file
is still attached to the table; this is what replaces it.

Two things changed in the translation, both worth knowing:

  * The old script fixed its working precision at `100 * 3.4 * 2` bits and
    hoped. Here the guard is stated as a constant with the measurement behind
    it, and the package *measures* what each value actually pinned down and
    refuses the run if any entry falls short of what it claims. The choice is
    still a choice -- how much a computation loses cannot be known in advance
    -- but it is no longer invisible, and it is no longer unchecked.

  * The old script stripped Sage's `?` from the written form by hand. Nothing
    here writes one: the package holds the database's convention, in which
    `3.14` already means (3.13, 3.15).

The entry for d = 2 carries `equals: HREF{Pi}` in the table, which is prose and
belongs to whoever wrote it. A generator cannot send prose and cannot remove
it, so it survives this untouched.
"""

import sys

import numberdb.sage as numberdb
from sage.all import QQ, RealIntervalField


#: Bits of working precision beyond what the written digits need.
#:
#: `numberdb.bits(digits)` converts decimal digits to bits and adds sixteen,
#: which is a guard against rounding, not against a computation. This one loses
#: more as d grows -- pi to a large power divided by a large gamma -- and at
#: the default guard the widest entry pinned 102 digits where 100 are written.
#: Two digits of margin on a table somebody may extend is not a margin.
#:
#: Measured over d = 0..500: 16 bits leaves 102 digits, 64 leaves 116, 256
#: leaves 174, and the whole table computes in a fifth of a second either way.
#: Nothing here is worth being clever about.
WORKING_GUARD = 256


class UnitBallVolume(numberdb.Generator):

    table = 'T27'
    parameters = ('d',)
    type = 'R'
    digits = 100

    #Interval arithmetic end to end, so the written digits follow from the
    #width of the result rather than from a guard chosen by hope. The two
    #exact entries are returned as exact rationals, which is the other thing
    #`proven` accepts.
    rigour = 'proven'

    def enumerate(self, up_to=500):
        # 0 is a real entry, not an edge case: the 0-dimensional ball is a
        # point and its volume is 1, which is what the table says.
        for d in range(0, up_to + 1):
            yield {'d': d}

    def value(self, params, digits):
        # Every step below is interval arithmetic, so that whether the result
        # is a valid enclosure can be read off this function rather than
        # inferred from what Sage does to a symbolic expression.
        #
        #   F.pi()            MPFI's enclosure of pi, correct by construction
        #   x ** (p/q)        interval power with an exact rational exponent
        #   x.gamma()         MPFI's gamma, which returns an enclosure
        #
        # An enclosure divided by an enclosure encloses the quotient, so the
        # result encloses the true volume. The earlier version of this line
        # read `field(pi ** half / gamma(half + 1))`, which builds the whole
        # expression in the symbolic ring and only then coerces it: the same
        # answer here, to within half a digit, but you cannot tell from
        # looking at it whether the coercion was rigorous.
        #
        # QQ(d)/2 rather than d/2, because this is a plain .py file and `/` on
        # two Python ints is floating point -- the exponent would arrive
        # already rounded. Halves are dyadic, so F(half) is exact and widens
        # nothing.
        # The first two are exact and are returned as exact rationals. This is
        # not a shortcut: B_0 = 1 because the 0-dimensional ball is a point,
        # and B_1 = 2 because the 1-dimensional one is the interval [-1, 1].
        #
        # Worth stating rather than leaving to the arithmetic. B_1 comes out of
        # the formula as sqrt(pi)/Gamma(3/2), which is exactly 2 -- but as
        # intervals it is a quotient of two enclosures of irrational numbers,
        # so it arrives as a narrow interval around 2 and gets written
        # `2.000000...` to a hundred digits. That is true and it is not what
        # the number is. The symbolic version of this line simplified it away
        # by luck; here it is said out loud.
        d = params['d']
        if d in (0, 1):
            return QQ(d + 1)

        half = QQ(d) / 2
        field = RealIntervalField(numberdb.bits(digits, losing=WORKING_GUARD))
        return field.pi() ** half / (field(half) + 1).gamma()


if __name__ == '__main__':
    generator = UnitBallVolume()

    if '--publish' in sys.argv:
        outcome = generator.publish(message='recomputed with the numberdb package')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
