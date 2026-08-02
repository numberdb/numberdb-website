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
from typing import Optional, Union

from . import (Client, ComplexInterval, NumberDBError, PAdic, Polynomial,
               RateLimited, RealInterval, Result, Scalar, Searchable,
               SearchResults, Table, Tag, TransportError, Unauthorized,
               UnsupportedNumber, __version__, configure, table, tag)
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
           'RealInterval', 'ComplexInterval', 'PAdic', 'Polynomial',
           'NumberDBError', 'TransportError', 'RateLimited', 'Unauthorized',
           'UnsupportedNumber', '__version__']

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

_sage_client = Client(as_sage=True)

_SAGE_NOTE = """

    Results carry Sage objects. The conversion is a faithful container, not a
    byte-identical round trip: a ball comes back as an interval, and an
    endpoint Sage cannot represent exactly is widened to one it can. It always
    contains the stored number.
    """


def _flavoured(client: Optional[Client]) -> Client:
    """The caller's client, or ours, returning Sage objects either way."""
    return (client or _sage_client).for_sage()


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


def search_real_interval(lower: Scalar, upper: Scalar,
                         client: Optional[Client] = None) -> SearchResults:
    return _search_real_interval(lower, upper, client=_flavoured(client))


def search_real_ball(center: Scalar, radius: Scalar,
                     client: Optional[Client] = None) -> SearchResults:
    return _search_real_ball(center, radius, client=_flavoured(client))


def search_complex_interval(re_lower: Scalar, re_upper: Scalar,
                            im_lower: Scalar, im_upper: Scalar,
                            client: Optional[Client] = None) -> SearchResults:
    return _search_complex_interval(re_lower, re_upper, im_lower, im_upper,
                                    client=_flavoured(client))


def search_complex_ball(re_center: Scalar, im_center: Scalar, radius: Scalar,
                        client: Optional[Client] = None) -> SearchResults:
    return _search_complex_ball(re_center, im_center, radius,
                                client=_flavoured(client))


def search_p_adic(prime: int, order: int, unit: int,
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
