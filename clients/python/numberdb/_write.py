"""Building a table and sending it.

Every generator that has ever filled a NumberDB table has repeated the same
three steps: turn a computed value into the string the database stores, collect
those values under their parameters, and write the result out. Until now that
machinery lived in the *website* repository and was imported by scripts in the
*data* repository, which is a dependency pointing the wrong way and a copy for
anybody outside either.

Putting it here makes it installable, versioned and testable, and gives one
answer to the question two generators must not answer differently: how many
digits, and in what form.

    entries = numberdb.Entries('n')
    for n in range(1, 100):
        entries.add(n=n, number=zeta(n))
    numberdb.submit('T42', numberdb.document(title='Zeta at integers',
                                             parameters={'n': {'type': 'Z'}},
                                             entries=entries))
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

__all__ = ['Entries', 'document', 'to_text', 'submit', 'submit_entries',
           'create', 'check_writable']

#: How many digits a value is written to when nothing says otherwise. The
#: house style, and the reason for it is not storage: digits that are cheap to
#: compute carry no information, since anybody who wants the thousandth digit
#: of a value that evaluates in a second can have it. A hundred is far more
#: than enough to identify a number, which is what the database is for. More
#: digits earn their place when they were expensive to obtain, and a table that
#: writes more is expected to say why.
DIGITS = 100


def to_text(value: Any, digits: int = DIGITS) -> str:
    """A value as the string the database stores.

    Exact things keep their exact form: an integer, a fraction and a polynomial
    are written out in full, because writing fewer digits of an exact value
    does not round it, it makes it a different number.

    An approximation is written to ``digits`` significant figures. Real
    intervals become the `3.14159?` form the site parses, which records the
    precision in the value itself -- the reason a string is a sound way to
    carry a number here and a bare float is not.
    """
    if isinstance(value, str):
        return value

    #Sage objects, when the caller has Sage. Recognised by behaviour rather
    #than by importing Sage, so this module stays importable without it.
    #
    #Errors are NOT swallowed here. They were, and it hid the fact that this
    #could not write a Sage real interval at all -- the commonest value in the
    #database, 65 of 107 tables -- behind a generic "cannot write that".
    if callable(getattr(value, 'parent', None)):
        return _sage_text(value, digits)

    if isinstance(value, bool):
        #Before int, which bool is a subclass of, and never a number here.
        raise TypeError('a boolean is not a number')
    if isinstance(value, int):
        return str(value)

    from fractions import Fraction
    if isinstance(value, Fraction):
        return (str(value.numerator) if value.denominator == 1
                else '%d/%d' % (value.numerator, value.denominator))

    #The package's own value types. It could read all of these back and not
    #write any of them, which made a round trip -- fetch a table, recompute,
    #resubmit -- impossible in the one library that ought to make it easy.
    from ._wire import ComplexInterval, PAdic, Polynomial, RealInterval

    if isinstance(value, RealInterval):
        return _interval_text(value, digits)
    if isinstance(value, ComplexInterval):
        return _complex_text(_interval_text(value.real, digits),
                             _interval_text(value.imag, digits))
    if isinstance(value, PAdic):
        return str(value)
    if isinstance(value, Polynomial):
        return str(value)

    if isinstance(value, float):
        raise TypeError(
            'a float does not say how precise it is, so it cannot be stored '
            'as it stands. Give a string, a Fraction, or a Sage real interval, '
            'or say the precision: to_text(value, digits=15)')

    raise TypeError('cannot write %s as a number' % (type(value).__name__,))


def _interval_text(interval, digits):
    """A real interval as the `3.14159?` form, or exactly when it is exact.

    An interval whose endpoints coincide is a rational that happens to have
    arrived as an interval; writing it with a `?` would claim an uncertainty
    that is not there.
    """
    from fractions import Fraction

    if interval.lower == interval.upper:
        return to_text(Fraction(interval.lower))

    #The digits the two endpoints agree on are the digits that are known; one
    #more would be asserting something the interval does not say.
    low, high = interval.lower, interval.upper
    for places in range(digits + 1):
        scale = Fraction(10) ** places
        if int(low * scale) != int(high * scale):
            places = max(places - 1, 0)
            break
    scale = Fraction(10) ** places
    truncated = Fraction(int(low * scale), 1) / scale
    text = ('%%.%df' % (places,)) % (float(truncated),) if places else str(
        int(truncated))
    return text + '?'


def _sage_text(value, digits):
    """The string form of a Sage object.

    Real and complex intervals become the `3.14159?` form the database stores,
    where the `?` says the last digit is uncertain. Sage prints every digit it
    holds, which is a property of the field the caller happened to build rather
    than a statement about the number, so the value is truncated to ``digits``
    the way the corpus has always been written.
    """
    name = str(value.parent())

    if 'Interval' in name or 'Ball' in name:
        if 'Complex' in name:
            return _complex_text(_truncate(str(value.real()), digits),
                                 _truncate(str(value.imag()), digits))
        return _truncate(str(value), digits)

    #Integers, rationals, polynomials and p-adics print exactly as they are
    #stored, and each is exact, so there is nothing to truncate: fewer digits
    #of an exact value is a different value.
    if any(mark in name for mark in _NUMERIC_PARENTS):
        return str(value)

    #Anything else is refused rather than stringified. Sage will happily give
    #a printable form for a group, a graph or a parent, and storing that would
    #put a sentence where a number belongs -- with nothing afterwards looking
    #wrong. A generator that returns the wrong object should hear about it.
    raise TypeError(
        'cannot write a value from %s as a number; return an integer, a '
        'rational, a real or complex interval, a p-adic or a polynomial'
        % (name,))


#: Substrings of the printed name of a parent whose elements are numbers this
#: database stores. Matched on the name because importing Sage to compare
#: types would make this module cost seconds to import for everybody.
_NUMERIC_PARENTS = ('Integer Ring', 'Rational Field', 'Real Field',
                    'Complex Field', 'Polynomial Ring',
                    #`2-adic Field ...`, so the prime is part of the name.
                    '-adic',
                    'Number Field', 'Algebraic')


def _complex_text(real, imag):
    """A complex value as NumberDB writes it: `a + i * b`.

    The `i` goes **before** the digits, and that is the substantive part of the
    convention rather than a matter of taste. An imaginary part can run to a
    hundred digits or more, so anywhere it is shown abbreviated -- a search
    result, a table cell, a truncated line -- a reader sees the beginning and
    not the end. With `i` in front, the beginning says which part this is.
    Written Sage's way, as `b*I`, the marker is the one character certain to be
    cut off, and a long real part and a long imaginary part look identical.

    Spaces around the `*` because that is how all 1847 complex values in the
    corpus are written; `i*b` appears in none of them.

    A negative imaginary part keeps its sign in `b` -- `2 + i * -1`, never
    `2 - i * 1` -- so the separator is always `+` and nothing has to be read
    twice to work out what is being subtracted.
    """
    return '%s + i * %s' % (real, imag)


def _truncate(text, digits):
    """Cut a Sage interval's printed form down to ``digits`` significant ones.

    The same rule the data repository has used since the corpus was built, so
    a value regenerated through this package is spelt as its neighbours are.
    A form without a `?` is exact and left alone.
    """
    if '?' not in text:
        return text
    mantissa, exponent = text.split('?', 1)
    if '.' not in mantissa:
        return text
    whole, fraction = mantissa.split('.', 1)
    room = digits - len(whole.lstrip('-'))
    if len(fraction) <= room:
        return text
    return '%s.%s?%s' % (whole, fraction[:max(room, 0)], exponent)


class Entries:
    """The entries of a table, as records with named parameters.

    Named rather than positional because an entry's identity is its parameter
    values, and every anchor, citation and search result is built from it. An
    identity that depends on the order the parameters happen to nest is only as
    stable as an ordering nobody promised to keep: reordered, `1,2` still
    exists and means something else, so the citation does not break, it
    resolves and points at a different number.

    ``Entries('N', 'c4', 'c6')`` fixes both the names and the order. The order
    is not decoration: it is the order the identities are built in, and it is
    fixed when the table is created.
    """

    def __init__(self, *names: str) -> None:
        if len(names) == 1 and isinstance(names[0], (list, tuple)):
            names = tuple(names[0])
        self.names = tuple(str(n) for n in names)
        self._records = []  # type: List[Dict[str, Any]]

    def add(self, number: Any = None, digits: int = DIGITS,
            **fields: Any) -> 'Entries':
        """Record one entry. Parameters are keyword arguments.

            entries.add(n=3, number=pi)
            entries.add(N=389, c4=112, c6=-856, number=x, comment='...')

        Anything that is not a declared parameter and not ``number`` is kept as
        an annotation on the entry -- `comment`, `proof`, `url` and the like --
        which is how the format has always been extended.
        """
        params = {}
        for name in self.names:
            if name not in fields:
                raise TypeError('entry is missing the parameter %r' % (name,))
            params[name] = _param_text(fields.pop(name))

        record = {'params': params}  # type: Dict[str, Any]
        if number is not None:
            record['number'] = (
                [to_text(v, digits) for v in number]
                if isinstance(number, (list, tuple))
                else to_text(number, digits))
        for key, value in fields.items():
            record[key] = value

        if 'number' not in record and 'equals' not in record:
            raise TypeError('entry has no number')
        self._records.append(record)
        return self

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    def as_list(self) -> List[Dict[str, Any]]:
        """The records, as the document carries them."""
        return list(self._records)


def _param_text(value: Any) -> str:
    """A parameter value as it appears in an identity.

    Always a string, and never reformatted: `1/2` and `0.5` are different
    identities, and a parameter that silently changed spelling would move every
    citation of that entry.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        raise TypeError('a boolean is not a parameter value')
    return str(value)


def document(title: str,
             entries: Union[Entries, Sequence[Mapping[str, Any]], None] = None,
             parameters: Optional[Mapping[str, Any]] = None,
             **sections: Any) -> Dict[str, Any]:
    """A table document, with its sections in the order the site writes them.

    Order matters: it is part of the document, so a generator that let its
    serialiser sort the keys would rewrite the whole table without having
    changed a value.

    The identifier is not a section. It belongs to the table rather than to the
    text, it is allocated when the table is created, and the server ignores it
    if sent.
    """
    if not title or not str(title).strip():
        raise ValueError('a table needs a title')

    out = {'Title': str(title)}  # type: Dict[str, Any]
    #Everything the caller gave, in the order they gave it, so a generator can
    #choose how its table reads.
    for key, value in sections.items():
        out[_section_name(key)] = value
    if parameters is not None:
        out['Parameters'] = dict(parameters)
    if entries is not None:
        out['Numbers'] = (entries.as_list() if isinstance(entries, Entries)
                          else [dict(r) for r in entries])
    return out


def _section_name(key: str) -> str:
    """`data_properties` -> `Data properties`, since sections are prose names."""
    if key.isupper() or ' ' in key:
        return key
    words = key.replace('_', ' ').strip()
    return words[:1].upper() + words[1:]


def _as_yaml(tree: Any) -> str:
    try:
        import yaml
    except ImportError:
        #JSON is a subset of YAML 1.2 and the server reads either, so a caller
        #without PyYAML is not blocked from writing.
        import json
        return json.dumps(tree, ensure_ascii=False, sort_keys=False)
    return yaml.dump(tree, sort_keys=False, allow_unicode=True,
                     default_flow_style=False)


def submit(tid: str, tree: Mapping[str, Any], message: str = '',
           produced_by: str = '', base: str = '',
           client: Any = None) -> Dict[str, Any]:
    """Replace table ``tid`` with ``tree``. Returns what the server recorded.

    The **whole** document, so anything ``tree`` omits is removed. A generator
    that computes values wants `submit_entries` instead; this is for a caller
    that holds the entire table and means to replace it.

    ``produced_by`` names the program. It defaults to something truthful rather
    than to nothing, because a reader is entitled to know that a revision came
    out of a script and a reviewer triages those differently.

    ``base`` is the revision the caller started from. Passing it turns a
    concurrent change from a silent overwrite into a refusal.
    """
    from . import _default_client

    client = client or _default_client
    headers = {'X-Produced-By': produced_by or 'numberdb-python'}
    if message:
        headers['X-Edit-Message'] = message
    if base:
        headers['X-Base-Revision'] = base
    return client.submit('/api/table/%s' % (str(tid).lstrip('tT'),),
                         _as_yaml(tree), headers)


def submit_entries(tid: str, entries: Union[Entries, Sequence[Mapping[str, Any]]],
                   message: str = '', produced_by: str = '',
                   upsert: bool = False, run: str = '',
                   client: Any = None) -> Dict[str, Any]:
    """Replace only the entries of table ``tid``. This is what a generator wants.

    `submit` replaces the whole document, so a generator that assembles one
    from what it knows -- a title, the parameters, the numbers it computed --
    deletes the definition, the comments, the references and the tags, and the
    result looks perfectly ordinary afterwards. That was impossible under the
    old arrangement, where a script wrote its own `numbers.yaml` and could not
    reach the prose. This restores that boundary: only entries are sent, and
    the server sets them into the current document.

        entries = numberdb.Entries('n')
        for n in range(1, 100):
            entries.add(n=n, number=zeta(n))
        numberdb.submit_entries('T42', entries, produced_by='zeta-generator')

    ``upsert`` sends *these* entries and leaves the rest of the table alone,
    which is what a generator computing expensive values needs: it can send
    each as it is found, so a crash at entry 900 costs one entry rather than
    900. Without it the entries are replaced, which is what a full
    regeneration means.

    ``run`` names one such run. Submissions carrying the same run grow one
    revision instead of adding one each, so a thousand values sent one at a
    time leave one entry in the history rather than a thousand -- and one
    stored document rather than a thousand copies of the whole table.
    """
    from . import _default_client

    client = client or _default_client
    headers = {'X-Produced-By': produced_by or 'numberdb-python'}
    if message:
        headers['X-Edit-Message'] = message
    if upsert:
        headers['X-Entries-Mode'] = 'upsert'
    if run:
        headers['X-Run-Id'] = run
    records = (entries.as_list() if isinstance(entries, Entries)
               else [dict(r) for r in entries])
    return client.submit('/api/table/%s/entries' % (str(tid).lstrip('tT'),),
                         _as_yaml(records), headers)


def create(tree: Mapping[str, Any], message: str = '', produced_by: str = '',
           client: Any = None) -> Dict[str, Any]:
    """Add a new table. Returns its allocated T-number and first revision."""
    from . import _default_client

    client = client or _default_client
    headers = {'X-Produced-By': produced_by or 'numberdb-python'}
    if message:
        headers['X-Edit-Message'] = message
    return client.submit('/api/tables', _as_yaml(tree), headers)


def check_writable(tid: str, client: Any = None) -> Dict[str, Any]:
    """Find out now whether this table can be written to.

    A generator may run for hours. Discovering at the end that no key was set,
    or that this account may not write yet, or that the table does not exist,
    costs whatever the computation cost -- and it is exactly the sort of thing
    that is known before any of it starts.

    Sends an empty upsert, which merges nothing and writes nothing, rather than
    asking a separate endpoint whether writing would work. A question answered
    by a different code path from the one that does the work is a question that
    can be answered wrongly; this exercises the key, the account's permission,
    the table's existence and the lock, and leaves the table untouched.

    Returns what the server said. Raises the same exceptions a real write
    would: `Unauthorized` without a usable key, `NumberDBError` for an unknown
    table.
    """
    return submit_entries(tid, [], upsert=True, client=client,
                          message='checking that this table can be written to')
