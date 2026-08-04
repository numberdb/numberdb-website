"""NumberDB: look a number up and find out whether it is already known.

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

import json
from fractions import Fraction
from typing import Any, Dict, List, Optional, Union

from ._convert import Scalar, SupportsParent, to_exact
from ._limits import (MAX_BATCH, SIGNIFICANT_DIGITS, bound_interval,
                      p_adic_digits)
from ._errors import (Conflict, NumberDBError, RateLimited, TooBig,
                      TransportError,
                      Unauthorized, UnsupportedNumber)
from ._http import Client
#After Client, since the write helpers reach for the default client at
#call time rather than at import time.
from ._write import Entries, create, document, submit, to_text
from ._wire import (KINDS, ComplexInterval, PAdic, Polynomial, RealInterval,
                    decode, to_sage)

__all__ = ['search', 'search_many', 'search_text',
           'search_by_expression',
           'search_integer', 'search_rational',
           'search_real_interval', 'search_real_ball',
           'search_complex_interval', 'search_complex_ball',
           'search_p_adic', 'search_polynomial',
           'table', 'tag', 'configure', 'Client',
           'Result', 'Table', 'Tag', 'SearchResults',
           'RealInterval', 'ComplexInterval', 'PAdic', 'Polynomial', 'KINDS',
           'NumberDBError', 'TransportError', 'RateLimited', 'Unauthorized',
           'UnsupportedNumber', 'Conflict', 'TooBig',
           'Entries', 'document', 'to_text', 'submit', 'create',
           '__version__']

try:
    from importlib.metadata import PackageNotFoundError, version
    #Single source of truth: the installed metadata, which comes from
    #pyproject.toml. Declaring the version in two places guarantees they drift.
    __version__ = version('numberdb')
except Exception:  # pragma: no cover - running from a source tree
    __version__ = '0.0.0+unknown'

#: Polynomials longer than this are looked up by a digest of their canonical
#: key rather than sent whole. Comfortably under the 8k a URL survives.
_HASH_ABOVE = 1500

_default_client = Client()


def configure(api_key: Optional[str] = None,
              base_url: Optional[str] = None,
              timeout: Optional[float] = None) -> Client:
    """Set what the module-level functions use.

    For a single key in a single process. Anything more -- two servers, two
    keys, threads with different credentials -- wants ``Client`` instead.
    """
    global _default_client
    _default_client = Client(api_key=api_key, base_url=base_url,
                             timeout=timeout)
    return _default_client


class Table:
    """The table a number was found in, or that a word matched."""

    __slots__ = ('tid', 'title', 'url', 'number_count')

    def __init__(self, record: Optional[Dict[str, Any]]) -> None:
        record = record or {}
        self.tid = record.get('tid')
        self.title = record.get('title')
        self.url = record.get('url')
        #Present when the table was found by a text search, absent when it
        #arrived as the home of a number.
        self.number_count = record.get('number_count')

    def __repr__(self):
        return 'Table(%r, %r)' % (self.tid, self.title)


class Tag:
    """A subject heading that a search term matched.

    A signpost rather than contents: ``numberdb.tag(tag.url)`` fetches the
    tables under it.
    """

    __slots__ = ('name', 'url', 'table_count', 'number_count')

    def __init__(self, record: Optional[Dict[str, Any]]) -> None:
        record = record or {}
        self.name = record.get('name')
        self.url = record.get('url')
        self.table_count = record.get('table_count')
        self.number_count = record.get('number_count')

    def __repr__(self):
        return 'Tag(%r)' % (self.name,)


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
                 '_wire', '_value', '_decoded', '_as_sage')

    def __init__(self, record: Dict[str, Any],
                 as_sage: bool = False) -> None:
        number = record.get('number') or {}
        self._wire = number.get('number')
        self._value = None
        self._decoded = False
        #Set by numberdb.sage, so that a Sage session gets Sage objects without
        #a flag at every call site.
        self._as_sage = as_sage
        self.kind = (self._wire or {}).get('kind')
        self.exact_text = number.get('exact_text') or ''
        self.str_short = number.get('str_short') or ''
        self.param = number.get('param') or ''
        self.table = Table(record.get('table'))

    @property
    def value(self) -> Any:
        """The number. Raises ``UnsupportedNumber`` if this version cannot
        read its kind -- ``exact_text`` still holds it either way."""
        if not self._decoded:
            value = decode(self._wire) if self._wire else None
            self._value = to_sage(value) if (self._as_sage and value is not None) else value
            self._decoded = True
        return self._value

    @property
    def is_readable(self) -> bool:
        """Whether ``value`` will decode, without having to try it."""
        return self.kind in KINDS

    def sage(self) -> Any:
        """The number as a Sage object. Requires SageMath.

        A conversion, not the stored value: a ball comes back as an interval,
        and an endpoint Sage cannot represent exactly is widened to one it can.
        It always contains the stored number -- verified across the database --
        but it is a faithful container, not a byte-identical round trip.
        """
        if self._as_sage:
            return self.value
        return to_sage(self.value)

    def url(self) -> Optional[str]:
        """Where to read about this value on the site.

        Carries the entry twice on purpose. `?entry=` is seen by the server, so
        following the link confirms the value is still there and says so if it
        is not; `#` is seen only by the browser, and scrolls to it. A link with
        the fragment alone -- which is what this returned before -- fails
        silently when an entry has been renumbered: the page loads, nothing
        scrolls, and the reader has no way to tell a stale citation from a
        value they simply cannot see.
        """
        if not self.table.url:
            return None
        import urllib.parse
        page = urllib.parse.urljoin(_default_client.base_url, self.table.url)
        if not self.param:
            return page
        return '%s?entry=%s#%s' % (
            page, urllib.parse.quote(self.param, safe=''), self.param)

    def __repr__(self):
        return 'Result(%r, table=%r)' % (self.exact_text or self.str_short,
                                         self.table.title)


class SearchResults(list):
    """The results, plus anything the server said about the search.

    A list, so it can simply be iterated. ``messages`` holds notes -- that the
    results were capped, that part of the expression was rejected -- as plain
    strings, kept rather than printed: the caller decides how to report them.

    ``tables`` and ``tags`` are what the term matched as *words* rather than as
    a number, and are filled in by :func:`search_text` alone. They stay
    separate from the list itself because they are not numbers: iterating a
    search must not hand back a table where a value was expected.
    """

    def __init__(self, results: List['Result'],
                 messages: List[str],
                 tables: Optional[List['Table']] = None,
                 tags: Optional[List['Tag']] = None) -> None:
        super().__init__(results)
        self.messages = messages
        self.tables = tables if tables is not None else []
        self.tags = tags if tags is not None else []

    @property
    def unreadable(self) -> List['Result']:
        """Results this version cannot decode, if the server is newer."""
        return [result for result in self if not result.is_readable]

    @property
    def total(self) -> int:
        """Everything the term matched: numbers, tables and tags together.

        ``len()`` counts the numbers alone, because this is a list of numbers
        and a list must not lie about its length. That makes the obvious
        ``if not results:`` wrong for a text search, which can match a table
        while matching no number -- 'matrix multiplication' finds the table and
        nothing numeric. ``if not results.total:`` is the question that was
        meant.

        Overriding ``__bool__`` instead would have made a sequence of length
        zero come out true, which no reader of Python expects.
        """
        return len(self) + len(self.tables) + len(self.tags)


def table(table_id: Union[int, str],
          client: Optional[Client] = None) -> Dict[str, Any]:
    """A whole table, as stored. ``table_id`` may be 12 or ``'T12'``.

    Returned as the server sends it, a plain dict. Deliberately not wrapped in
    classes: a table's shape is the data format's business, and mirroring it
    here would mean this package needed a release every time a table gained a
    field.
    """
    return (client or _default_client).request('api/table', {'id': table_id})


def tag(name: str, client: Optional[Client] = None) -> Dict[str, Any]:
    """The tables carrying a tag. A plain dict, as for ``table``."""
    return (client or _default_client).request('api/tag', {'url': name})


def _lookup(parameters: Dict[str, Any],
            client: Optional[Client]) -> 'SearchResults':
    used = client or _default_client
    payload = used.request('api/lookup', parameters)
    records = payload.get('results') or []
    messages = [message.get('text', '') for message in
                (payload.get('messages') or []) if isinstance(message, dict)]
    #Absent from every response an older server sends, and from the number
    #searches on any server, so the default is an empty list rather than an
    #error.
    tables = [Table(record) for record in (payload.get('tables') or [])]
    tags = [Tag(record) for record in (payload.get('tags') or [])]
    return SearchResults([Result(record, used.as_sage)
                          for record in records], messages, tables, tags)


def _by_number(record: Dict[str, Any],
               client: Optional[Client]) -> 'SearchResults':
    return _lookup({'number': json.dumps(record)}, client)


def _overlaps(value, low, high) -> bool:
    """Whether a returned value could still be the number originally asked for.

    A widened query is sound -- it cannot miss -- but it can bring back numbers
    that only matched the widening. The check is filter-and-refine: the coarse
    interval goes to the server, and the exact one is applied here, where the
    original bounds are still known.

    A value this version cannot decode is kept. It might be the answer, and
    dropping something unexamined is worse than showing it.
    """
    if isinstance(value, RealInterval):
        return value.lower <= high and value.upper >= low
    if isinstance(value, (int, Fraction)):
        return low <= Fraction(value) <= high
    return True


def _refine(results: 'SearchResults', low, high) -> 'SearchResults':
    """Drop results that only matched the widened query."""
    kept = []
    for result in results:
        if not result.is_readable:
            kept.append(result)
            continue
        try:
            if _overlaps(result.value, low, high):
                kept.append(result)
        except UnsupportedNumber:
            kept.append(result)
    return SearchResults(kept, results.messages)


def search_integer(value: Scalar, client: Optional[Client] = None) -> 'SearchResults':
    """Search for an exact integer.

    The server searches an exact value as a point interval on the real line, so
    the result is what search_real_interval(n, n) would give. This exists to
    say what you mean, and to refuse a value that is not an integer, rather
    than because it asks a mechanically different question.
    """
    exact = to_exact(value, 'value')
    if exact.denominator != 1:
        raise ValueError('%s is not an integer; use search_rational' % (exact,))
    if len(str(abs(exact.numerator))) > SIGNIFICANT_DIGITS:
        #Too long to send exactly, so sent as the range it lies in. The server
        #searches an exact value as a point interval anyway, so this loses
        #nothing that was being used.
        return search_real_interval(exact, exact, client=client)
    return _by_number({'kind': 'ZZ', 'value': str(exact.numerator)},
                      client)


def search_rational(numerator: Scalar, denominator: Scalar = 1,
                    client: Optional[Client] = None) -> 'SearchResults':
    """Search for an exact rational ``numerator / denominator``.

    The denominator defaults to 1, so a Fraction can be passed on its own.
    """
    exact = to_exact(numerator, 'numerator') / to_exact(denominator,
                                                        'denominator')
    if len(str(exact)) > 2 * SIGNIFICANT_DIGITS:
        return search_real_interval(exact, exact, client=client)
    return _by_number({'kind': 'QQ', 'value': str(exact)}, client)


def search_real_interval(lower: Scalar, upper: Scalar,
                         client: Optional[Client] = None) -> 'SearchResults':
    """Search for a real known to lie between ``lower`` and ``upper``.

    Endpoints are converted exactly before anything else touches them, so the
    interval searched is the interval given -- never a rounding of it.
    """
    exact_low, exact_high = to_exact(lower, 'lower'), to_exact(upper, 'upper')
    if exact_low > exact_high:
        exact_low, exact_high = exact_high, exact_low

    #Trimmed outward, so the interval sent contains the one meant. Trimming
    #inward would hide the number the caller is looking for.
    low, high = bound_interval(exact_low, exact_high)

    found = _by_number({'kind': 'RIF', 'lower': str(low), 'upper': str(high)},
                       client)
    if (low, high) == (exact_low, exact_high):
        return found
    #Widened, so some of what came back may only have matched the widening.
    return _refine(found, exact_low, exact_high)


def search_real_ball(center: Scalar, radius: Scalar,
                     client: Optional[Client] = None) -> 'SearchResults':
    """Search for a real known as ``center`` give or take ``radius``.

    The form to use for an experimental value: state the uncertainty you
    actually have, rather than letting the digits of a float imply one.
    """
    middle, spread = to_exact(center, 'center'), abs(to_exact(radius, 'radius'))
    return search_real_interval(middle - spread, middle + spread,
                                client=client)


def search_complex_interval(re_lower: Scalar, re_upper: Scalar,
                            im_lower: Scalar, im_upper: Scalar,
                            client: Optional[Client] = None) -> 'SearchResults':
    """Search for a complex number known to lie in a rectangle."""
    #Each coordinate bounded on its own, so a large real part cannot cost the
    #imaginary one its precision.
    real = list(bound_interval(to_exact(re_lower, 're_lower'),
                               to_exact(re_upper, 're_upper')))
    imaginary = list(bound_interval(to_exact(im_lower, 'im_lower'),
                                    to_exact(im_upper, 'im_upper')))
    return _by_number({'kind': 'CIF',
                       're_lower': str(real[0]), 're_upper': str(real[1]),
                       'im_lower': str(imaginary[0]),
                       'im_upper': str(imaginary[1])}, client)


def search_complex_ball(re_center: Scalar, im_center: Scalar, radius: Scalar,
                        client: Optional[Client] = None) -> 'SearchResults':
    """Search for a complex number known to within ``radius`` of a centre.

    The disc is widened to the square that contains it: the database stores
    rectangles, and widening is the direction that cannot lose a match.
    """
    spread = abs(to_exact(radius, 'radius'))
    real = to_exact(re_center, 're_center')
    imaginary = to_exact(im_center, 'im_center')
    return search_complex_interval(real - spread, real + spread,
                                   imaginary - spread, imaginary + spread,
                                   client=client)


def search_p_adic(prime: int, order: int, unit: int,
                  absolute_precision: Optional[int] = None,
                  relative_precision: Optional[int] = None,
                  client: Optional[Client] = None) -> 'SearchResults':
    """Search for ``prime**order * unit``, known to the given precision.

    ``unit`` must be coprime to ``prime``. Exactly one precision must be
    given, and it must be named: absolute and relative coincide at order zero
    and diverge silently elsewhere, so a bare number would have to be
    remembered rather than read.
    """
    if (absolute_precision is None) == (relative_precision is None):
        raise TypeError('give exactly one of absolute_precision or '
                        'relative_precision')
    if absolute_precision is None:
        #Narrowed for the reader as much as the checker: exactly one of the two
        #is given, so relative_precision is not None on this branch.
        assert relative_precision is not None
        absolute_precision = int(relative_precision) + int(order)
    #Counted in p-adic digits: a hundred decimal digits is worth
    #100*log(10)/log(p) of them, 333 for p=2 and two for a very large prime.
    allowed = p_adic_digits(int(prime))
    if absolute_precision - int(order) > allowed:
        absolute_precision = int(order) + allowed

    #Constructed rather than assembled by hand, so the coprimality check and
    #the reduction of the unit happen here too.
    value = PAdic(prime, order, unit, absolute_precision)
    return _by_number({'kind': 'Qp', 'prime': value.prime,
                       'valuation': value.valuation, 'unit': str(value.unit),
                       'precision': value.precision_absolute},
                      client)


def search_polynomial(polynomial: Union[str, Polynomial],
                      client: Optional[Client] = None) -> 'SearchResults':
    """Search for a polynomial over the rationals, written as text.

    Variable names do not matter: the database canonicalises under renaming, so
    'x^2-2' and 'y^2-2' find each other.

    Not the same as passing the text to search_text. A search term might be a
    title or a tag, and because variables are canonicalised away, a single-term
    polynomial would match any word -- so the search bar ignores those. Saying
    "this is a polynomial" removes the ambiguity, and 'x' is searched here
    where it would not be there.
    """
    text = polynomial.text if isinstance(polynomial, Polynomial) \
        else str(polynomial)

    #Sent as a digest of the canonical key when the polynomial is long. The
    #longest stored one is 58866 characters and a URL is rejected past 8k, so
    #the largest entries could not be asked about at all. Sound because one
    #canonicalisation defines the key and this package carries a byte-identical
    #copy of it; a test asserts the two files never diverge.
    if len(text) > _HASH_ABOVE:
        try:
            from ._polynomial import parse_polynomial as _parse
            return _lookup({'polynomial_hash': _parse(
                text.replace(' ', '')).canonical_hash()}, client)
        except Exception:
            #Unreadable here but perhaps readable by the server, which has the
            #richer parser. Falling back costs a long request, not an answer.
            pass
    #Its own parameter, not text=. Search terms are ambiguous -- a word might
    #be a title or a tag -- and polynomials are canonicalised under renaming of
    #variables, so a single-term polynomial would match any word at all. The
    #search bar ignores those on purpose. Here the caller has said this is a
    #polynomial, so single terms are searched too. Parsing still happens on the
    #server, so this package does not grow a second polynomial parser.
    return _lookup({'polynomial': text}, client)


def search_text(text: str, client: Optional[Client] = None) -> 'SearchResults':
    """Search exactly as the box on the website does.

    The term is read two ways, because a term is often two questions.

    As a *number*, in the documented human formats: '3.14159' for a real,
    '1415' for a fractional part, 'Q5:1010' or '1 + O(5^20)' for a p-adic,
    '1/2 + i*0.866' for a complex number, 'x^2-2' for a polynomial. These are
    the results in the list itself. A string states its own precision --
    '3.14' means the last digit is uncertain -- which is why text is a sound
    way to search and a bare float is not.

    As *words*, against the table titles and tag names. Those matches arrive
    as ``.tables`` and ``.tags`` rather than in the list, since they are
    signposts and not numbers::

        >>> found = numberdb.search_text('matrix multiplication')
        >>> [table.title for table in found.tables]
        ['Exponent of matrix multiplication complexity']

    A term that is plainly machinery -- one containing ':' or '^' -- is not
    offered to the word search, which would only cost a query.
    """
    return _lookup({'text': text}, client)


def search_by_expression(expression: str, client: Optional[Client] = None) -> 'SearchResults':
    """Have the server evaluate a Sage expression, and search for the results.

    The only call that runs code on the server: it forks a sandboxed Sage
    process, so it is much the most expensive, and the rate limit it consumes
    is there because of it. Use it when you want the server to *compute*
    something -- '{n: pi^n for n in [1..5]}' -- not to look up a number you
    already have.
    """
    return _expression(expression, client)


def _expression(expression: str,
                client: Optional[Client]) -> 'SearchResults':
    used = client or _default_client
    payload = used.request('api/search', {'expression': expression})
    records = payload.get('results') or []
    messages = [message.get('text', '') for message in
                (payload.get('messages') or []) if isinstance(message, dict)]
    return SearchResults([Result(record, used.as_sage)
                          for record in records], messages)


#: Anything search() accepts. Sage values are matched structurally, by
#: having a parent -- never by the attributes they expose, since Sage
#: polynomials and p-adics both answer numerator().
Searchable = Union[int, Fraction, str, RealInterval, ComplexInterval,
                   PAdic, Polynomial, SupportsParent]


def _sage_parent_kind(value: Any) -> Optional[str]:
    """What a Sage value is, judged by its parent.

    Never by the attributes it exposes: Sage polynomials and p-adics both carry
    numerator() and denominator(), returning objects of their own type, so
    anything sniffing for those would take them for rationals -- and Python's
    Fraction does not raise on a Sage rational, it stores the bound methods.

    Textual, because the alternative is importing Sage to compare classes, and
    this package must work without it.
    """
    parent = getattr(value, 'parent', None)
    if not callable(parent):
        return None
    try:
        described = str(parent())
    except Exception:
        return None
    lowered = described.lower()
    if 'adic' in lowered:
        return 'p-adic'
    if 'polynomial ring' in lowered:
        return 'polynomial'
    if 'complex interval' in lowered or 'complex ball' in lowered:
        return 'complex interval'
    if 'real interval' in lowered or 'real ball' in lowered:
        return 'real interval'
    if described == 'Rational Field':
        return 'rational'
    if described == 'Integer Ring':
        return 'integer'
    return described


def search(value: 'Searchable', client: Optional[Client] = None) -> 'SearchResults':
    """Search for a number you already have.

    Accepts a Python ``int`` or ``Fraction``, one of this package's own types
    (``RealInterval``, ``ComplexInterval``, ``PAdic``, ``Polynomial``), or a
    Sage number. For raw components, the ``search_*`` functions take them
    directly and need no object built first.

    A bare ``float`` is refused. A float states no precision -- its decimal
    digits are an artefact of binary, not a claim about a measurement -- so
    searching for one would silently invent an uncertainty. Say what you know:
    ``search_real_ball(3.14159266, 1e-8)``, or a string, which does state its
    own precision.
    """
    if isinstance(value, bool):
        raise TypeError('a bool is not a number')

    if isinstance(value, RealInterval):
        return search_real_interval(value.lower, value.upper,
                                    client=client)
    if isinstance(value, ComplexInterval):
        return search_complex_interval(
            value.real.lower, value.real.upper,
            value.imag.lower, value.imag.upper, client=client)
    if isinstance(value, PAdic):
        return search_p_adic(value.prime, value.valuation, value.unit,
                             absolute_precision=value.precision_absolute,
                             client=client)
    if isinstance(value, Polynomial):
        return search_polynomial(value, client=client)

    if isinstance(value, int):
        return search_integer(value, client=client)
    if isinstance(value, Fraction):
        return search_rational(value, client=client)
    if isinstance(value, str):
        return search_text(value, client=client)

    if isinstance(value, float):
        raise TypeError(
            'a float states no precision, so searching for one would invent an '
            'uncertainty it does not have. Use search_real_ball(centre, '
            'radius) to say what you know, or pass a string, which states its '
            'own precision.')

    kind = _sage_parent_kind(value)
    #Classified by parent, so from here it is a Sage object whose interface
    #the type system cannot see. Named as Any rather than pretended about.
    sage_value: Any = value
    if kind == 'integer':
        return search_integer(sage_value, client=client)
    if kind == 'rational':
        return search_rational(sage_value, client=client)
    if kind == 'real interval':
        return search_real_interval(sage_value.lower(), sage_value.upper(),
                                    client=client)
    if kind == 'complex interval':
        return search_complex_interval(
            sage_value.real().lower(), sage_value.real().upper(),
            sage_value.imag().lower(), sage_value.imag().upper(),
            client=client)
    if kind == 'p-adic':
        if sage_value == 0:
            absolute = int(sage_value.precision_absolute())
            return search_p_adic(int(sage_value.parent().prime()), absolute, 0,
                                 absolute_precision=absolute,
                                 client=client)
        return search_p_adic(int(sage_value.parent().prime()),
                             int(sage_value.valuation()),
                             int(sage_value.unit_part().lift()),
                             absolute_precision=int(
                                 sage_value.precision_absolute()),
                             client=client)
    if kind == 'polynomial':
        return search_polynomial(str(sage_value).replace(' ', ''),
                                 client=client)

    raise TypeError(
        'no search for %s. Give an int, a Fraction, a string, one of this '
        "package's types, or a Sage number." % (kind or type(value).__name__,))


def _record_for(value) -> Dict[str, Any]:
    """The wire record for a value, as the typed functions would send it."""
    if isinstance(value, RealInterval):
        low, high = bound_interval(value.lower, value.upper)
        return {'kind': 'RIF', 'lower': str(low), 'upper': str(high)}
    if isinstance(value, ComplexInterval):
        real = bound_interval(value.real.lower, value.real.upper)
        imaginary = bound_interval(value.imag.lower, value.imag.upper)
        return {'kind': 'CIF', 're_lower': str(real[0]),
                're_upper': str(real[1]), 'im_lower': str(imaginary[0]),
                'im_upper': str(imaginary[1])}
    if isinstance(value, PAdic):
        return {'kind': 'Qp', 'prime': value.prime,
                'valuation': value.valuation, 'unit': str(value.unit),
                'precision': value.precision_absolute}
    if isinstance(value, bool):
        raise TypeError('a bool is not a number')
    if isinstance(value, int):
        return {'kind': 'ZZ', 'value': str(value)}
    if isinstance(value, Fraction):
        return {'kind': 'QQ', 'value': str(value)}
    raise TypeError('cannot batch %s; batches carry numbers, not text or '
                    'expressions' % (type(value).__name__,))


def search_many(values, client: Optional[Client] = None
                ) -> Dict[int, 'SearchResults']:
    """Look up many numbers in one request.

    One round trip instead of many, which matters more than it sounds: a TLS
    handshake costs about twice what an answered request does, and the rate
    limit counts requests. A batch is priced at one unit plus half per number,
    so a hundred numbers cost fifty-one units rather than a hundred.

    Returns a dict from position in ``values`` to the results for that number,
    so a caller can tell which answer belongs to which question. Every position
    is present: one that matched nothing maps to an empty ``SearchResults``,
    not to a missing key. Absence would be indistinguishable from a number the
    server dropped, and would make the obvious ``results[i]`` raise on the one
    case a caller most wants to see -- that their number is not known. Numbers
    the server could not read appear in the messages of every group rather than
    silently vanishing.

    At most ``MAX_BATCH`` numbers, because one caller should not be able to
    make the server do unbounded work in a single round trip.
    """
    values = list(values)
    if len(values) > MAX_BATCH:
        raise ValueError('at most %d numbers in one batch; %d given. Split it.'
                         % (MAX_BATCH, len(values)))

    records = [_record_for(value) for value in values]
    payload = (client or _default_client).request(
        'api/lookup', {'numbers': json.dumps(records)})
    messages = [message.get('text', '') for message in
                (payload.get('messages') or []) if isinstance(message, dict)]

    used = client or _default_client
    #Seeded with every position asked about, so the caller's indices and the
    #dict's keys agree whatever the server sent back.
    grouped = {index: SearchResults([], messages)
               for index in range(len(values))}  # type: Dict[int, SearchResults]
    for record in payload.get('results') or []:
        try:
            index = int(record.get('index', -1))
        except (TypeError, ValueError):
            continue
        #setdefault rather than indexing: an index outside the range asked
        #about should not be dropped on the floor, it should be visible.
        grouped.setdefault(index, SearchResults([], messages)).append(
            Result(record, used.as_sage))
    return grouped
