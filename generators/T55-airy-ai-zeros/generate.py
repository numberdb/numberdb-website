"""Zeros of the Airy function Ai -- numberdb.org/T55

The n-th negative zero of Ai(x), for n = 1..1000.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

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


#: The two working precisions, in decimal digits. The first is what the
#: original script used for a hundred written digits; the second is enough more
#: to disagree if the first were wrong.
#:
#: One computation cannot check itself. `mpmath.nstr(z, 100)` prints a hundred
#: digits of a value computed to thirty, and the last seventy are the decimal
#: expansion of a binary approximation -- deterministic, reproducible and
#: wrong. Measured on n = 1: computing at 30 digits and at 300 gives answers
#: that diverge at the 40th, so 61 of the 100 digits would have been published
#: without anything noticing.
WORKING = (150, 200)


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
        # `agreeing` was written here by hand first, and lifted into the
        # package before the seven generators that followed copied it.
        return numberdb.agreeing(
            lambda working: self._zero(params['n'], working), at=WORKING)

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
