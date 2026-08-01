"""NumberDB — look a number up and find out whether it is already known.

    >>> import numberdb
    >>> for result in numberdb.search('pi'):
    ...     print(result.exact_text, '--', result.table.title)

Works in plain Python. Inside SageMath, ``result.sage()`` gives the number as a
Sage object; nothing else needs Sage, and it is not imported until asked for.

Anonymous use is rate limited. A key raises the limit:

    $ export NUMBERDB_API_KEY=...

or, if you must set it in code, ``numberdb.configure(api_key='...')``. For more
than one server or key in a process, use ``Client`` directly.

Why a package rather than a file to copy: the response has to be turned into
numbers, and doing that by hand is how the previous example client came to call
``loads()`` on server-supplied bytes -- which runs whatever those bytes say.
Here decoding is a fixed table (see ``_wire``), and it is versioned, so a change
to the format is a version bump and a clear message rather than an exception in
the middle of your session.
"""

from ._errors import (NumberDBError, RateLimited, TransportError,
                      Unauthorized, UnsupportedNumber)
from ._http import Client
from ._wire import (KINDS, ComplexInterval, PAdic, Polynomial, RealInterval,
                    decode, to_sage)

__all__ = ['search', 'table', 'tag', 'configure', 'Client',
           'Result', 'Table', 'SearchResults',
           'RealInterval', 'ComplexInterval', 'PAdic', 'Polynomial', 'KINDS',
           'NumberDBError', 'TransportError', 'RateLimited', 'Unauthorized',
           'UnsupportedNumber', '__version__']

try:
    from importlib.metadata import PackageNotFoundError, version
    #Single source of truth: the installed metadata, which comes from
    #pyproject.toml. Declaring the version in two places guarantees they drift.
    __version__ = version('numberdb')
except Exception:  # pragma: no cover - running from a source tree
    __version__ = '0.0.0+unknown'

_default_client = Client()


def configure(api_key=None, base_url=None, timeout=None):
    """Set what the module-level functions use.

    For a single key in a single process. Anything more -- two servers, two
    keys, threads with different credentials -- wants ``Client`` instead.
    """
    global _default_client
    _default_client = Client(api_key=api_key, base_url=base_url,
                             timeout=timeout)
    return _default_client


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

    ``exact_text`` is how the database writes the number: the form to quote in
    a paper or paste back into a search. It is plain text and needs no decoding,
    so it is available whatever this version of the package understands.

    ``value`` is the number as a Python object -- ``int``, ``Fraction``,
    ``RealInterval``, ``ComplexInterval``, ``PAdic`` or ``Polynomial``. It is
    decoded when first asked for, not when the result arrives. That matters for
    longevity: when the server learns a new kind of number, an older package
    still returns every result, and only the one value it cannot read raises,
    at the point you ask for it. Decoding eagerly would let one unfamiliar
    number throw away an entire search.
    """

    __slots__ = ('exact_text', 'str_short', 'param', 'table', 'kind',
                 '_wire', '_value', '_decoded')

    def __init__(self, record):
        number = record.get('number') or {}
        self._wire = number.get('number')
        self._value = None
        self._decoded = False
        self.kind = (self._wire or {}).get('kind')
        self.exact_text = number.get('exact_text') or ''
        self.str_short = number.get('str_short') or ''
        self.param = number.get('param') or ''
        self.table = Table(record.get('table'))

    @property
    def value(self):
        """The number. Raises ``UnsupportedNumber`` if this version cannot
        read its kind -- ``exact_text`` still holds it either way."""
        if not self._decoded:
            self._value = decode(self._wire) if self._wire else None
            self._decoded = True
        return self._value

    @property
    def is_readable(self):
        """Whether ``value`` will decode, without having to try it."""
        return self.kind in KINDS

    def sage(self):
        """The number as a Sage object. Requires SageMath."""
        return to_sage(self.value)

    def url(self):
        """Where to read about it on the site."""
        if not self.table.url:
            return None
        import urllib.parse
        page = urllib.parse.urljoin(_default_client.base_url, self.table.url)
        return '%s#%s' % (page, self.param) if self.param else page

    def __repr__(self):
        return 'Result(%r, table=%r)' % (self.exact_text or self.str_short,
                                         self.table.title)


class SearchResults(list):
    """The results, plus anything the server said about the search.

    A list, so it can simply be iterated. ``messages`` holds notes -- that the
    results were capped, that part of the expression was rejected -- as plain
    strings, kept rather than printed: the caller decides how to report them.
    """

    def __init__(self, results, messages):
        super().__init__(results)
        self.messages = messages

    @property
    def unreadable(self):
        """Results this version cannot decode, if the server is newer."""
        return [result for result in self if not result.is_readable]


def search(expression, client=None):
    """Search for numbers matching ``expression``.

    The expression is evaluated by the server, in the language documented at
    https://numberdb.org/advanced-search -- for example ``'pi'`` or
    ``'{n: pi^n for n in [1..5]}'``.
    """
    payload = (client or _default_client).request(
        'api/search', {'expression': expression})
    records = payload.get('results') or []
    #Messages are flattened to text: their other field is a CSS class, which is
    #the website's business and has no place in a library's contract.
    messages = [message.get('text', '') for message in
                (payload.get('messages') or []) if isinstance(message, dict)]
    return SearchResults([Result(record) for record in records], messages)


def table(table_id, client=None):
    """A whole table, as stored. ``table_id`` may be 12 or ``'T12'``.

    Returned as the server sends it, a plain dict. Deliberately not wrapped in
    classes: a table's shape is the data format's business, and mirroring it
    here would mean this package needed a release every time a table gained a
    field.
    """
    return (client or _default_client).request('api/table', {'id': table_id})


def tag(name, client=None):
    """The tables carrying a tag. A plain dict, as for ``table``."""
    return (client or _default_client).request('api/tag', {'url': name})
