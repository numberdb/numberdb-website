"""NumberDB for SageMath: the same calls, with Sage objects coming back.

    sage: import numberdb.sage as numberdb
    sage: numberdb.search('pi')[0].value
    3.141592653589794?

One import line, and every call site below reads exactly as it would in plain
Python -- there is no mode to set and nothing to pass at each call.

Why a submodule rather than a setting or an extra:

* An extra (``pip install numberdb[sage]``) could not do it anyway: extras
  install dependencies, and the installed code is identical either way. There
  deliberately is no such extra, because it would be typed by the people it can
  hurt -- inside a full SageMath it would install passagemath over the top,
  overwriting 349 files including compiled extensions, with no conflict
  reported. This module needs nothing installed; it uses the Sage you have.
* A setting would work but has to be remembered, and code that omits it behaves
  differently from code that does not.
* Detecting whether Sage happens to be importable would make the same program
  behave differently in different environments, which is worse than either.

The import line states which world you are in, once, where a reader can see it.

Every function is written out below rather than generated in a loop. The loop
kept the two modules from drifting but made them invisible to tooling: a
checker reported "Module has no attribute search_integer", and an editor
offered no completion -- for exactly the audience this module exists to serve.
A test asserts this list stays complete, which buys the same guarantee at no
cost to the reader.
"""

import importlib.util
from typing import Any, Optional, Union

from ._convert import Scalar
from . import (KINDS, Client, ComplexInterval, NumberDBError, PAdic,
               Polynomial,
               RateLimitError, RealInterval, Result, Searchable,
               SearchResults, Table, Tag, TransportError, UnauthorizedError,
               UnsupportedNumberError, __version__, configure, table, tag)
#Writing needs no Sage flavour of its own -- values go *in*, and a Sage
#object is already understood wherever one is accepted -- but it has to be
#reachable, or `import numberdb.sage as numberdb` is a drop-in replacement
#that silently is not one. A Sage session is where generators get written.
from . import (ConflictError, DisagreementError, Generator,
               PublishOutcome, TooBigError, VerifyReport, bits)
from . import search as _search
from . import search_many as _search_many
from . import search_by_expression as _search_by_expression
from . import search_complex_ball as _search_complex_ball
from . import search_complex_interval as _search_complex_interval
from . import search_integer as _search_integer
from . import search_p_adic as _search_p_adic
from . import search_polynomial as _search_polynomial
from . import search_rational as _search_rational
from . import search_real_ball as _search_real_ball
from . import search_real_interval as _search_real_interval
from . import search_text as _search_text

__all__ = ['search', 'search_many', 'search_text',
           'search_by_expression',
           'search_integer', 'search_rational',
           'search_real_interval', 'search_real_ball',
           'search_complex_interval', 'search_complex_ball',
           'search_p_adic', 'search_polynomial',
           'table', 'tag', 'configure', 'Client',
           'Result', 'Table', 'SearchResults',
           'Tag',
           'RealInterval', 'ComplexInterval', 'PAdic', 'Polynomial', 'KINDS',
           'NumberDBError', 'TransportError', 'RateLimitError', 'UnauthorizedError',
           'UnsupportedNumberError', 'ConflictError', 'TooBigError', 'DisagreementError',
           'Generator', 'PublishOutcome', 'VerifyReport', 'bits',
           'assume_accurate', 'agreeing',
           '__version__']

#Checked by specification rather than by importing: Sage takes seconds to load,
#and the point of failing here is to say plainly that this module needs it, not
#to pay that cost before the caller has asked for anything.
if importlib.util.find_spec('sage') is None:
    raise ImportError(
        'numberdb.sage needs SageMath, which does not appear to be installed. '
        'Use "import numberdb" instead: it returns plain Python values and '
        'needs nothing extra. If you want Sage objects without a full '
        'SageMath, install passagemath into a fresh environment -- never into '
        'an existing Sage, where it would overwrite the installation.')

from ._wire import _prime_sage

#Initialise Sage as this module loads, so that a caller can import Sage's own
#rings directly afterwards.
#
#`from sage.rings.rational_field import QQ` raises "cannot import name QQ" on a
#modular passagemath until something else has brought Sage up -- and there is
#no `sage.all` there to do it. So a generator either opened with `from sage.all
#import ...`, which only exists in a full SageMath, or carried a line importing
#a module it never used. Importing this module is now enough, and it costs
#nothing that was not already being paid: `numberdb.sage` needs Sage to do
#anything at all.
_prime_sage()

#Not a client of its own. One was made here at import time, with no key, and
#every search through this module used it -- so `numberdb.configure(api_key=
#...)` had no effect on the Sage wrappers and an authenticated run read the
#corpus anonymously, at sixty requests an hour. Three separate runs met that
#as a mysterious throttle; one of them could not walk the corpus at all,
#which the skill asks it to do.
#
#`for_sage()` is asked of whatever client the caller has, so configuring the
#package configures this too.

_SAGE_NOTE = """

    Results carry Sage objects. The conversion is a faithful container, not a
    byte-identical round trip: a ball comes back as an interval, and an
    endpoint Sage cannot represent exactly is widened to one it can. It always
    contains the stored number.
    """


def _flavoured(client: Optional[Client]) -> Client:
    """The caller's client, or the package's, returning Sage objects either way.

    The package's, not one of this module's own: `numberdb.configure()`
    replaces `numberdb._default_client`, and a module holding its own client
    would keep reading with whatever key existed at import time -- which was
    none.
    """
    import numberdb

    return (client or numberdb._default_client).for_sage()


def search(value: Searchable,
           client: Optional[Client] = None) -> SearchResults:
    return _search(value, client=_flavoured(client))


def search_many(values, client: Optional[Client] = None):
    return _search_many(values, client=_flavoured(client))


def search_text(text: str, client: Optional[Client] = None) -> SearchResults:
    return _search_text(text, client=_flavoured(client))


def search_by_expression(expression: str,
                         client: Optional[Client] = None) -> SearchResults:
    return _search_by_expression(expression, client=_flavoured(client))


def search_integer(value: Scalar,
                   client: Optional[Client] = None) -> SearchResults:
    return _search_integer(value, client=_flavoured(client))


def search_rational(numerator: Scalar, denominator: Scalar = 1,
                    client: Optional[Client] = None) -> SearchResults:
    return _search_rational(numerator, denominator, client=_flavoured(client))


def search_real_interval(lower: Any, upper: Optional[Scalar] = None,
                         client: Optional[Client] = None) -> SearchResults:
    #The signature mirrors the plain one deliberately. Narrowing it here --
    #`upper` required, forwarded positionally -- meant the Sage layer refused
    #a whole RIF element while the plain package accepted it, which is exactly
    #backwards: in Sage the interval is what you are holding. Reported from
    #outside, against the examples in this package's own README.
    return _search_real_interval(lower, upper, client=_flavoured(client))


def search_real_ball(center: Scalar, radius: Scalar,
                     client: Optional[Client] = None) -> SearchResults:
    return _search_real_ball(center, radius, client=_flavoured(client))


def search_complex_interval(re_lower: Any,
                            re_upper: Optional[Scalar] = None,
                            im_lower: Optional[Scalar] = None,
                            im_upper: Optional[Scalar] = None,
                            client: Optional[Client] = None) -> SearchResults:
    return _search_complex_interval(re_lower, re_upper, im_lower, im_upper,
                                    client=_flavoured(client))


def search_complex_ball(re_center: Scalar, im_center: Scalar, radius: Scalar,
                        client: Optional[Client] = None) -> SearchResults:
    return _search_complex_ball(re_center, im_center, radius,
                                client=_flavoured(client))


def search_p_adic(prime: Any, order: Optional[int] = None,
                  unit: Optional[int] = None,
                  absolute_precision: Optional[int] = None,
                  relative_precision: Optional[int] = None,
                  client: Optional[Client] = None) -> SearchResults:
    return _search_p_adic(prime, order, unit,
                          absolute_precision=absolute_precision,
                          relative_precision=relative_precision,
                          client=_flavoured(client))


def search_polynomial(polynomial: Union[str, Polynomial],
                      client: Optional[Client] = None) -> SearchResults:
    return _search_polynomial(polynomial, client=_flavoured(client))


#The plain module's documentation, plus a note about the flavour. Copied rather
#than rewritten so the two modules cannot come to say different things about
#the same call.
for _name in __all__:
    if _name.startswith('search'):
        _original = globals()['_' + _name]
        globals()[_name].__doc__ = (_original.__doc__ or '') + _SAGE_NOTE
del _name, _original


def _ball_and_interval_fields():
    """``RealBallField, RealIntervalField``, without going through `sage.all`.

    `sage.all` imports the whole library. That is free in a full SageMath, and
    it is not free with passagemath, which ships Sage as separate pip
    distributions so that a person can install the parts they need into an
    ordinary virtual environment. Asking for `sage.all` there either drags in
    far more than this package uses or fails outright on a narrow install.

    The specific modules are tried first for that reason, and `sage.all` is
    kept as the fallback because importing a submodule before anything has
    initialised Sage can raise "partially initialized module" -- the same
    circular-import problem `_wire.py` documents, with the order reversed
    because these two modules are safe to reach directly.
    """
    try:
        from sage.rings.real_arb import RealBallField
        from sage.rings.real_mpfi import RealIntervalField
        return RealBallField, RealIntervalField
    except ImportError:
        pass
    try:
        from sage.all import RealBallField, RealIntervalField
        return RealBallField, RealIntervalField
    except ImportError:
        raise ImportError(
            'SageMath is required here. Install SageMath, or passagemath: '
            '`pip install passagemath-symbolics`.')


def assume_accurate(value, ulps, because):
    """A ball around ``value``, of radius ``ulps`` units in its last place.

    For a number computed in fixed-precision arithmetic that you have a reason
    to believe is accurate to within a stated number of ulps. It turns that
    belief into a radius **once**, at the point where the belief is made, so
    that every operation afterwards is interval arithmetic and the error
    propagates instead of vanishing at the first multiplication.

        zero = numberdb.sage.assume_accurate(
            pari_result, ulps=2,
            because='PARI ellL1 at 38 digits; agrees with the Dokchitser '
                    'implementation to 30 digits on this curve')

    Two things it deliberately does not do.

    **It has no default for ``ulps``.** A helper that supplies the bound
    supplies the judgement, and the judgement is the whole content of it. There
    is no general answer: PARI's documentation, checked, mentions "ulp" in one
    of its 1271 documented functions, and mpmath's `airyaizero` and
    `besseljzero` say nothing about accuracy at all. *"It was PARI"* is not a
    reason; *"PARI's documentation for this function states X"* is one.

    **It requires ``because``**, which is stored with the run. An assumption
    nobody wrote down is indistinguishable, a year later, from an assumption
    nobody made.

    The generator using this should declare ``rigour = 'assumed-bound'``: the
    arithmetic downstream is rigorous, and it rests on something asserted here
    rather than proven.

    **The argument counts too.** A documented bound on a routine bounds
    ``f(x̃)``, where ``x̃`` is the argument as the routine received it. If ``x``
    is not exactly representable at the working precision then ``x̃`` is not
    ``x``, and there is a second error of size ``|f'| · |x - x̃|`` that no claim
    about ``f`` covers -- and bounding *that* needs the derivative over an
    interval, since a derivative at a point is itself a heuristic. So ``ulps``
    here should account for the argument as well as the routine, and
    ``because`` should say so. Where the argument is exactly representable --
    an integer, a half -- there is nothing to add, and where the whole
    computation is interval arithmetic the question does not arise, which is
    the strongest practical case for `proven`.
    """
    RealBallField, RealIntervalField = _ball_and_interval_fields()

    if not because or not str(because).strip():
        raise ValueError(
            'assume_accurate() needs a reason: what makes this value accurate '
            'to %r ulps? It is stored with the numbers, because an assumption '
            'nobody wrote down cannot be checked later.' % (ulps,))
    if ulps is None or ulps <= 0:
        raise ValueError('ulps must be positive: an accuracy of zero ulps is '
                         'a claim of exactness, which is what an exact value '
                         'is for.')

    parent = getattr(value, 'parent', None)
    field = parent() if parent is not None else None
    precision = getattr(field, 'precision', None)
    bits_of = precision() if precision is not None else 53

    #The last place of a value of this precision, then that many of them.
    ball = RealBallField(bits_of)(value)
    return ball.add_error(ball.abs() * RealBallField(bits_of)(2) ** (-bits_of)
                          * ulps)


def agreeing(compute, at):
    """Compute a value at several precisions and keep the digits they agree on.

    For a number that cannot be computed rigorously. `mpmath.airyaizero` and
    its kind return a fixed-precision float with no error bound, and printing
    one to a hundred digits gives a hundred digits -- the last sixty of them
    the decimal expansion of a binary approximation. Nothing downstream can
    tell: a point wrapped in an interval field has width zero, which says the
    value is exact.

    Computing twice and keeping what agrees turns that into something
    measurable::

        def value(self, params, digits):
            return numberdb.agreeing(
                lambda working: self._zero(params['n'], working),
                at=(150, 200))

    ``compute`` is called once per entry in ``at`` with that number of working
    **decimal digits**, and should return whatever it computed -- a string
    carrying that many digits is the usual thing, since a string crossing from
    another library into Sage keeps the digits rather than a binary
    approximation of them.

    The result is the union of the values as intervals, so it has real width,
    only the digits every computation supports are written, and `publish`'s
    precision check has something to measure. A generator using this should
    declare ``rigour = 'heuristic (agreement-checked)'``.

    ``at`` is stated explicitly rather than derived from ``digits``, and there
    is no escalation on failure: the file attached to a table is meant to be
    how those numbers were made, and a run that silently raised its own
    precision would not be. If the agreement is too short, raise the numbers
    here and run it again.

    **This is not a proof.** It bounds the error from working precision and
    nothing else. Two runs of a wrong algorithm agree perfectly, and so do two
    runs of a library function with a bug.
    """
    _, RealIntervalField = _ball_and_interval_fields()

    from ._write import bits

    working = [int(w) for w in at]
    if len(working) < 2:
        raise ValueError(
            'agreeing() needs at least two precisions to compare; one '
            'computation cannot check itself, which is the whole point of it.')
    if len(set(working)) != len(working):
        raise ValueError(
            'agreeing() was given the same precision twice: %r. Two identical '
            'computations agree completely and say nothing.' % (at,))

    field = RealIntervalField(bits(max(working)))
    values = [field(compute(w)) for w in working]
    result = values[0]
    for value in values[1:]:
        result = result.union(value)
    return result
