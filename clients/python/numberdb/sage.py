"""NumberDB for SageMath: the same calls, with Sage objects coming back.

    sage: import numberdb.sage as numberdb
    sage: numberdb.search('pi')[0].value
    3.141592653589794?

One import line and every call site below reads exactly as it would in plain
Python -- there is no mode to set and nothing to pass at each call.

Why a submodule rather than a setting or an extra:

* An extra (``pip install numberdb[sage]``) could not do it anyway: extras
  install dependencies, and the installed code is identical either way. There
  deliberately is no such extra, because it would be typed by the people it
  can hurt -- inside a full SageMath it would install passagemath over the
  top, overwriting 349 files including compiled extensions, with no conflict
  reported. This module needs nothing installed; it uses the Sage you have.
* A setting would work but has to be remembered, and code that omits it behaves
  differently from code that does not.
* Detecting whether Sage happens to be importable would make the same program
  behave differently in different environments, which is worse than either.

The import line states which world you are in, once, where a reader can see it.

Everything not concerned with numbers -- ``table``, ``tag``, ``Client``, the
exceptions -- is re-exported unchanged, so this module can stand in for the
package wholesale.
"""

import importlib.util

import functools
from typing import Any

from . import (Client, ComplexInterval, NumberDBError, PAdic, Polynomial,
               RateLimited, RealInterval, Result, SearchResults, Table,
               TransportError, Unauthorized, UnsupportedNumber, __version__,
               configure, table, tag)
from . import __all__ as _plain_names

__all__ = list(_plain_names)

#Checked by specification rather than by importing: Sage takes seconds to load,
#and the point of failing here is to say plainly that this module needs it,
#not to pay that cost before the caller has asked for anything.
if importlib.util.find_spec('sage') is None:
    raise ImportError(
        'numberdb.sage needs SageMath, which does not appear to be installed. '
        'Use "import numberdb" instead: it returns plain Python values and '
        'needs nothing extra. If you want Sage objects without a full '
        'SageMath, install passagemath into a fresh environment -- never into '
        'an existing Sage, where it would overwrite the installation.')


def _flavoured(function: Any) -> Any:
    """The same call, with results carrying Sage objects.

    Wrapped rather than reimplemented, so the two modules cannot drift: adding
    a search function to the package adds it here with no further work.
    """
    @functools.wraps(function)
    def call(*args: Any, **keywords: Any) -> Any:
        keywords.setdefault('as_sage', True)
        return function(*args, **keywords)

    call.__doc__ = (function.__doc__ or '') + (
        '\n\n    Results carry Sage objects. The conversion is a faithful\n'
        '    container, not a byte-identical round trip: a ball comes back as\n'
        '    an interval, and an endpoint Sage cannot represent exactly is\n'
        '    widened to one it can. It always contains the stored number.\n')
    return call


#Every search function, in Sage flavour. Anything else -- table, tag, Client,
#the exceptions -- is re-exported unchanged above.
_plain = __import__('numberdb', fromlist=['*'])
for _name in _plain_names:
    if _name.startswith('search'):
        globals()[_name] = _flavoured(getattr(_plain, _name))
del _name
