"""NumberDB — look a number up and find out whether it is already known.

    >>> import numberdb
    >>> for result in numberdb.search('pi'):
    ...     print(result.exact_text, '--', result.table.title)

Works in plain Python. Inside SageMath, ``result.sage()`` gives the number as a
Sage object; nothing else requires Sage, and it is not imported until asked
for.

Anonymous use is rate limited. Set an API key to raise the limit:

    >>> numberdb.api_key = '...'          # or export NUMBERDB_API_KEY

Why a package rather than a file to copy: the response has to be turned into
numbers, and doing that by hand is how the old example client ended up calling
``loads()`` on server-supplied bytes -- which runs whatever those bytes say.
Here decoding is a fixed table (see ``_wire``), and it is versioned, so a
change to the format is a version bump rather than a KeyError in your session.
"""

from ._http import NumberDBError, RateLimited, Unauthorized, request
from ._wire import (Box, Interval, PAdic, Polynomial, UnsupportedNumber,
                    KINDS, decode, to_sage)

__all__ = ['search', 'table', 'tag', 'Result', 'Table', 'SearchResults',
           'Interval', 'Box', 'PAdic', 'Polynomial',
           'NumberDBError', 'RateLimited', 'Unauthorized', 'UnsupportedNumber',
           'api_key', '__version__']

__version__ = '0.1.0'

#: Set to raise the anonymous rate limit. Falls back to $NUMBERDB_API_KEY.
api_key = None


class Table:
    """The table a number was found in."""

    __slots__ = ('tid', 'title', 'url')

    def __init__(self, record):
        record = record or {}
        self.tid = record.get('tid')
        self.title = record.get('title')
        self.url = record.get('url')

    def __repr__(self):
        return 'Table(%r, %r)' % (self.tid, self.title)


class Result:
    """One number, and where it lives.

    ``value`` is the number in plain Python: ``int``, ``Fraction``,
    ``Interval``, ``Box``, ``PAdic`` or ``Polynomial``. ``exact_text`` is how
    the database writes it, which is the form to quote in a paper or paste back
    into a search.
    """

    __slots__ = ('value', 'exact_text', 'str_short', 'param', 'table', 'kind')

    def __init__(self, record):
        number = record.get('number') or {}
        wire = number.get('number')
        self.kind = (wire or {}).get('kind')
        self.value = decode(wire) if wire else None
        self.exact_text = number.get('exact_text') or ''
        self.str_short = number.get('str_short') or ''
        self.param = number.get('param') or ''
        self.table = Table(record.get('table'))

    def sage(self):
        """The number as a Sage object. Requires SageMath."""
        return to_sage(self.value)

    def url(self):
        """Where to read about it on the site."""
        if not self.table.url:
            return None
        page = '%s%s' % (_http_base(), self.table.url)
        return '%s#%s' % (page, self.param) if self.param else page

    def __repr__(self):
        return 'Result(%r, table=%r)' % (self.exact_text or self.str_short,
                                         self.table.title)


class SearchResults(list):
    """The results, plus anything the server wanted to say about the search.

    A list, so it can simply be iterated. ``messages`` is kept rather than
    printed: a search that was truncated or partly rejected should be able to
    say so without deciding for the caller how to report it.
    """

    def __init__(self, results, messages):
        super().__init__(results)
        self.messages = messages

    @property
    def warnings(self):
        return [message.get('text', '') for message in self.messages]


def _http_base():
    from ._http import base_url
    return base_url()


def search(expression, urlopen=None):
    """Search for numbers matching ``expression``.

    The expression is evaluated by the server, in the language documented at
    https://numberdb.org/advanced-search -- for example ``'pi'``,
    ``'{n: pi^n for n in [1..5]}'``.
    """
    payload = _request('api/search', {'expression': expression}, urlopen)
    records = payload.get('results') or []
    return SearchResults([Result(record) for record in records],
                         payload.get('messages') or [])


def table(table_id, urlopen=None):
    """A whole table, as stored. ``table_id`` may be 12 or 'T12'."""
    payload = _request('api/table', {'id': table_id}, urlopen)
    if 'error' in payload:
        raise NumberDBError(payload['error'])
    return payload


def tag(name, urlopen=None):
    """The tables carrying a tag."""
    payload = _request('api/tag', {'url': name}, urlopen)
    if 'error' in payload:
        raise NumberDBError(payload['error'])
    return payload


def _request(path, parameters, urlopen):
    if urlopen is None:
        return request(path, parameters)
    return request(path, parameters, urlopen=urlopen)
