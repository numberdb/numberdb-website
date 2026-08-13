"""Zeros of the Airy function Ai -- numberdb.org/T55

The n-th negative zero of Ai(x), for n = 1..1000.

**These digits are not proven.** That is the point of this file, and it is
worth reading before the code.

The original `generate.sage` computed each zero with mpmath at 1.5 times the
digits it wrote, wrapped the result in a wide RealIntervalField, and wrote a
hundred digits:

    mpmath.mp.dps = prec10 * 1.5
    RIFprec = RealIntervalField(prec10 * 3.4 * 2)
    number = mpmath.mp.airyaizero(n, derivative=0)
    real_interval_to_sage_string(RIFprec(number), max_digits=prec10)

`RIFprec(number)` of an mpmath float is an interval of **zero width**: the
error made in computing the zero is not in it, because nothing put it there.
The fifty per cent margin is the entire error control and nothing checks it.

That is not an oversight to be fixed here, because it cannot be fixed with what
is installed:

  * mpmath documents correct rounding for its low-level arithmetic, and says
    nothing at all about the accuracy of `airyaizero`.
  * mpmath ships a rigorous interval mode, `mpmath.iv`, which covers `pi`,
    `exp` and `gamma` -- and raises AttributeError for `airyaizero`, whose
    implementation calls context methods the interval context does not have.
  * Sage's RealBallField, which is arb and would be rigorous, does not expose
    Airy functions at all. (arb itself has `arb_hypgeom_airy_zero`; nothing
    wraps it here.)

So this generator reproduces the original method deliberately, and the honest
description of its output is *a hundred digits computed at a hundred and fifty,
believed and not proven*. When the package can record that -- see
docs/design/rigour.md -- this file should declare it rather than leave a reader
to infer it from a docstring.
"""

import sys

import mpmath
import numberdb.sage as numberdb
from sage.all import RealIntervalField


#: Digits computed beyond the digits written, as the original used: fifty guard
#: digits for a hundred written.
GUARD_RATIO = 1.5

#: ...and again at this much more, so the two can be compared.
#:
#: One computation cannot check itself. `mpmath.nstr(z, 100)` prints a hundred
#: digits of a value computed to thirty, and the last seventy are the decimal
#: expansion of a binary approximation -- deterministic, reproducible and
#: wrong. Measured on n = 1: computing at 30 digits and at 300 gives answers
#: that diverge at the 40th, so 61 of the 100 digits would have been published
#: without anything noticing.
SECOND_OPINION = 2.0


class AiryAiZeros(numberdb.Generator):

    table = 'T55'
    parameters = ('n',)
    type = 'R'
    digits = 100

    #Said out loud, and it is the honest word. mpmath's airyaizero carries no
    #error bound and documents no accuracy; two computations at different
    #precisions agreeing is evidence about rounding, not a proof about the
    #zero. The table will say so where a reader can see it.
    rigour = 'heuristic (agreement-checked)'

    def enumerate(self, up_to=1000):
        for n in range(1, up_to + 1):
            yield {'n': n}

    def value(self, params, digits):
        n = params['n']
        low = self._zero(n, int(digits * GUARD_RATIO))
        high = self._zero(n, int(digits * SECOND_OPINION))

        # The two answers as one interval. This is the whole idea: a value
        # computed twice at different precisions, kept only as far as the two
        # agree. The union has real width, so the package's writer emits only
        # the digits both support, and its precision check -- which measures
        # what a value pins down -- is no longer looking at a point that claims
        # everything.
        #
        # Not a proof, and it must not be read as one. Two runs of the same
        # algorithm can be wrong together, and this bounds the error from
        # working precision, nothing else. It is the difference between a
        # hundred digits believed because fifty extra were computed, and a
        # hundred digits that two computations agreed on.
        field = RealIntervalField(numberdb.bits(int(digits * SECOND_OPINION)))
        return field(low).union(field(high))

    @staticmethod
    def _zero(n, working_digits):
        """The n-th zero to ``working_digits``, as a string.

        A string rather than an mpmath float, because the value crosses into
        Sage here and a string carries the digits that were computed rather
        than a binary approximation of them.
        """
        # mpmath's precision is global state, set per call so that a run at a
        # different `digits` is not silently computed at the previous one.
        mpmath.mp.dps = working_digits
        return mpmath.nstr(mpmath.mp.airyaizero(n, derivative=0),
                           working_digits, strip_zeros=False)


if __name__ == '__main__':
    generator = AiryAiZeros()
    if '--publish' in sys.argv:
        print(generator.publish(message='recomputed with the numberdb package'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
