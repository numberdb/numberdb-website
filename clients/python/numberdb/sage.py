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

from . import (Client, NumberDBError, RateLimited, Result, SearchResults,
               Table, TransportError, Unauthorized, UnsupportedNumber,
               __version__, configure, table, tag)
from . import search as _search

__all__ = ['search', 'table', 'tag', 'configure', 'Client',
           'Result', 'Table', 'SearchResults',
           'NumberDBError', 'TransportError', 'RateLimited', 'Unauthorized',
           'UnsupportedNumber', '__version__']

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


def search(expression, client=None):
    """Search for numbers matching ``expression``, as Sage objects.

    Identical to ``numberdb.search`` except that ``result.value`` is a Sage
    object rather than a plain Python one.

    The conversion is a faithful container, not a byte-identical round trip: a
    ball comes back as an interval, and an endpoint Sage cannot represent
    exactly is widened to one it can. It always contains the stored number.
    """
    return _search(expression, client=client, as_sage=True)
