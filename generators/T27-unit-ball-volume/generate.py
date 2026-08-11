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
    hoped. `numberdb.bits()` converts digits to bits with a margin, and the
    package then *measures* what each value actually pins down and refuses the
    run if any entry falls short of what it claims. The hoping is gone.

  * The old script stripped Sage's `?` from the written form by hand. Nothing
    here writes one: the package holds the database's convention, in which
    `3.14` already means (3.13, 3.15).

The entry for d = 2 carries `equals: HREF{Pi}` in the table, which is prose and
belongs to whoever wrote it. A generator cannot send prose and cannot remove
it, so it survives this untouched.
"""

import sys

import numberdb.sage as numberdb
from sage.all import QQ, RealIntervalField, gamma, pi


class UnitBallVolume(numberdb.Generator):

    table = 'T27'
    parameters = ('d',)
    type = 'R'
    digits = 100

    def enumerate(self, up_to=500):
        # 0 is a real entry, not an edge case: the 0-dimensional ball is a
        # point and its volume is 1, which is what the table says.
        for d in range(0, up_to + 1):
            yield {'d': d}

    def value(self, params, digits):
        # QQ(d)/2 rather than d/2: this is a plain .py file, not a Sage
        # worksheet, so `/` on two Python ints is floating point and the
        # exponent would arrive already rounded.
        half = QQ(params['d']) / 2
        field = RealIntervalField(numberdb.bits(digits))
        return field(pi ** half / gamma(half + 1))


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
