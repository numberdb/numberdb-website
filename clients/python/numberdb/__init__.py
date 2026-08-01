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

import json
from fractions import Fraction
from typing import Any, Dict, List, Optional

from ._convert import Scalar, to_exact
from ._errors import (NumberDBError, RateLimited, TransportError,
                      Unauthorized, UnsupportedNumber)
from ._http import Client
from ._wire import (KINDS, ComplexInterval, PAdic, Polynomial, RealInterval,
                    decode, to_sage)

__all__ = ['search', 'search_text', 'search_by_expression',
           'search_integer', 'search_rational',
           'search_real_interval', 'search_real_ball',
           'search_complex_interval', 'search_complex_ball',
           'search_p_adic', 'search_polynomial',
           'table', 'tag', 'configure', 'Client',
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
                 '_wire', '_value', '_decoded', '_as_sage')

    def __init__(self, record, as_sage=False):
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
    def value(self):
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

    def sage(self):
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


def table(table_id, client: Optional[Client] = None) -> Dict[str, Any]:
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


def _lookup(parameters, client, as_sage):
    payload = (client or _default_client).request('api/lookup', parameters)
    records = payload.get('results') or []
    messages = [message.get('text', '') for message in
                (payload.get('messages') or []) if isinstance(message, dict)]
    return SearchResults([Result(record, as_sage) for record in records],
                         messages)


def _by_number(record, client, as_sage):
    return _lookup({'number': json.dumps(record)}, client, as_sage)


def search_integer(value: Scalar, client: Optional[Client] = None,
                   as_sage: bool = False) -> 'SearchResults':
    """Search for an exact integer.

    Exact values are matched by equality on an indexed column, not by a range
    query, so this is a different question from search_real_interval and not
    merely a convenience over it.
    """
    exact = to_exact(value, 'value')
    if exact.denominator != 1:
        raise ValueError('%s is not an integer; use search_rational' % (exact,))
    return _by_number({'kind': 'ZZ', 'value': str(exact.numerator)},
                      client, as_sage)


def search_rational(numerator: Scalar, denominator: Scalar = 1,
                    client: Optional[Client] = None,
                    as_sage: bool = False) -> 'SearchResults':
    """Search for an exact rational ``numerator / denominator``.

    The denominator defaults to 1, so a Fraction can be passed on its own.
    """
    exact = to_exact(numerator, 'numerator') / to_exact(denominator,
                                                        'denominator')
    return _by_number({'kind': 'QQ', 'value': str(exact)}, client, as_sage)


def search_real_interval(lower: Scalar, upper: Scalar,
                         client: Optional[Client] = None,
                         as_sage: bool = False) -> 'SearchResults':
    """Search for a real known to lie between ``lower`` and ``upper``.

    Endpoints are converted exactly before anything else touches them, so the
    interval searched is the interval given -- never a rounding of it.
    """
    low, high = to_exact(lower, 'lower'), to_exact(upper, 'upper')
    if low > high:
        low, high = high, low
    return _by_number({'kind': 'RIF', 'lower': str(low), 'upper': str(high)},
                      client, as_sage)


def search_real_ball(center: Scalar, radius: Scalar,
                     client: Optional[Client] = None,
                     as_sage: bool = False) -> 'SearchResults':
    """Search for a real known as ``center`` give or take ``radius``.

    The form to use for an experimental value: state the uncertainty you
    actually have, rather than letting the digits of a float imply one.
    """
    middle, spread = to_exact(center, 'center'), abs(to_exact(radius, 'radius'))
    return search_real_interval(middle - spread, middle + spread,
                                client=client, as_sage=as_sage)


def search_complex_interval(re_lower: Scalar, re_upper: Scalar,
                            im_lower: Scalar, im_upper: Scalar,
                            client: Optional[Client] = None,
                            as_sage: bool = False) -> 'SearchResults':
    """Search for a complex number known to lie in a rectangle."""
    real = sorted([to_exact(re_lower, 're_lower'), to_exact(re_upper, 're_upper')])
    imaginary = sorted([to_exact(im_lower, 'im_lower'),
                        to_exact(im_upper, 'im_upper')])
    return _by_number({'kind': 'CIF',
                       're_lower': str(real[0]), 're_upper': str(real[1]),
                       'im_lower': str(imaginary[0]),
                       'im_upper': str(imaginary[1])}, client, as_sage)


def search_complex_ball(re_center: Scalar, im_center: Scalar, radius: Scalar,
                        client: Optional[Client] = None,
                        as_sage: bool = False) -> 'SearchResults':
    """Search for a complex number known to within ``radius`` of a centre.

    The disc is widened to the square that contains it: the database stores
    rectangles, and widening is the direction that cannot lose a match.
    """
    spread = abs(to_exact(radius, 'radius'))
    real = to_exact(re_center, 're_center')
    imaginary = to_exact(im_center, 'im_center')
    return search_complex_interval(real - spread, real + spread,
                                   imaginary - spread, imaginary + spread,
                                   client=client, as_sage=as_sage)


def search_p_adic(prime: int, order: int, unit: int,
                  absolute_precision: Optional[int] = None,
                  relative_precision: Optional[int] = None,
                  client: Optional[Client] = None,
                  as_sage: bool = False) -> 'SearchResults':
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
        absolute_precision = int(relative_precision) + int(order)
    #Constructed rather than assembled by hand, so the coprimality check and
    #the reduction of the unit happen here too.
    value = PAdic(prime, order, unit, absolute_precision)
    return _by_number({'kind': 'Qp', 'prime': value.prime,
                       'valuation': value.valuation, 'unit': str(value.unit),
                       'precision': value.precision_absolute},
                      client, as_sage)


def search_polynomial(polynomial, client: Optional[Client] = None,
                      as_sage: bool = False) -> 'SearchResults':
    """Search for a polynomial over the rationals, written as text.

    Variable names do not matter: the database canonicalises under renaming,
    so 'x^2-2' and 'y^2-2' find each other.
    """
    text = polynomial.text if isinstance(polynomial, Polynomial) \
        else str(polynomial)
    #Sent as text: the server parses it with the same grammar the website
    #uses, rather than this package growing a second polynomial parser.
    return _lookup({'text': text}, client, as_sage)


def search_text(text: str, client: Optional[Client] = None,
                as_sage: bool = False) -> 'SearchResults':
    """Search exactly as the box on the website does.

    The documented human formats: '3.14159' for a real, '1415' for a
    fractional part, 'Q5:1010' or '1 + O(5^20)' for a p-adic, '1/2 + i*0.866'
    for a complex number, 'x^2-2' for a polynomial.

    A string states its own precision -- '3.14' means the last digit is
    uncertain -- which is why text is a sound way to search and a bare float
    is not.
    """
    return _lookup({'text': text}, client, as_sage)


def search_by_expression(expression: str, client: Optional[Client] = None,
                         as_sage: bool = False) -> 'SearchResults':
    """Have the server evaluate a Sage expression, and search for the results.

    The only call that runs code on the server: it forks a sandboxed Sage
    process, so it is much the most expensive, and the rate limit it consumes
    is there because of it. Use it when you want the server to *compute*
    something -- '{n: pi^n for n in [1..5]}' -- not to look up a number you
    already have.
    """
    return _expression(expression, client, as_sage)


def _expression(expression, client, as_sage):
    payload = (client or _default_client).request(
        'api/search', {'expression': expression})
    records = payload.get('results') or []
    messages = [message.get('text', '') for message in
                (payload.get('messages') or []) if isinstance(message, dict)]
    return SearchResults([Result(record, as_sage) for record in records],
                         messages)


def _sage_parent_kind(value):
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


def search(value, client: Optional[Client] = None,
           as_sage: bool = False) -> 'SearchResults':
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
                                    client=client, as_sage=as_sage)
    if isinstance(value, ComplexInterval):
        return search_complex_interval(
            value.real.lower, value.real.upper,
            value.imag.lower, value.imag.upper, client=client, as_sage=as_sage)
    if isinstance(value, PAdic):
        return search_p_adic(value.prime, value.valuation, value.unit,
                             absolute_precision=value.precision_absolute,
                             client=client, as_sage=as_sage)
    if isinstance(value, Polynomial):
        return search_polynomial(value, client=client, as_sage=as_sage)

    if isinstance(value, int):
        return search_integer(value, client=client, as_sage=as_sage)
    if isinstance(value, Fraction):
        return search_rational(value, client=client, as_sage=as_sage)
    if isinstance(value, str):
        return search_text(value, client=client, as_sage=as_sage)

    if isinstance(value, float):
        raise TypeError(
            'a float states no precision, so searching for one would invent an '
            'uncertainty it does not have. Use search_real_ball(centre, '
            'radius) to say what you know, or pass a string, which states its '
            'own precision.')

    kind = _sage_parent_kind(value)
    if kind == 'integer':
        return search_integer(value, client=client, as_sage=as_sage)
    if kind == 'rational':
        return search_rational(value, client=client, as_sage=as_sage)
    if kind == 'real interval':
        return search_real_interval(value.lower(), value.upper(),
                                    client=client, as_sage=as_sage)
    if kind == 'complex interval':
        return search_complex_interval(
            value.real().lower(), value.real().upper(),
            value.imag().lower(), value.imag().upper(),
            client=client, as_sage=as_sage)
    if kind == 'p-adic':
        if value == 0:
            absolute = int(value.precision_absolute())
            return search_p_adic(int(value.parent().prime()), absolute, 0,
                                 absolute_precision=absolute,
                                 client=client, as_sage=as_sage)
        return search_p_adic(int(value.parent().prime()),
                             int(value.valuation()),
                             int(value.unit_part().lift()),
                             absolute_precision=int(value.precision_absolute()),
                             client=client, as_sage=as_sage)
    if kind == 'polynomial':
        return search_polynomial(str(value).replace(' ', ''),
                                 client=client, as_sage=as_sage)

    raise TypeError(
        'no search for %s. Give an int, a Fraction, a string, one of this '
        "package's types, or a Sage number." % (kind or type(value).__name__,))
