"""A generator that needs more of its file than its class body.

Fixture for the test that `publish` attaches the *file*. The value comes from
a function defined outside the class, so an attachment holding the class alone
would not contain the code that computed the number -- which is exactly the
thing an attached source is for.

Not named test_* so pytest does not collect it.
"""

from fractions import Fraction

import numberdb

SCALE = 3


def scaled(n):
    """Module-level, and the class cannot be read without it."""
    return Fraction(1, n * SCALE)


class Sample(numberdb.Generator):
    parameters = ('n',)
    type = 'Q'
    table = 'T7'

    def enumerate(self, limit=2):
        for n in range(1, limit + 1):
            yield {'n': n}

    def value(self, params, digits):
        return scaled(int(params['n']))
