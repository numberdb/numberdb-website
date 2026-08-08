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

Prose is not here. A table's definition, comments, references and tags are
written by a person on the site, and a program cannot reach them from this
module -- which is why a generator can no longer delete them by accident.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

#Nothing here is public. A program's one way in is `numberdb.publish`, and
#these are the pieces it is built from: turning a value into the string the
#database stores, collecting values under their parameters, and sending them.
#
#What is deliberately absent is as important as what is here. There is no way
#from a program to write a whole document, and so no way for a generator to
#delete a table's definition, comments or references by assembling a document
#out of what it happens to know. That is not a discipline anybody has to
#remember: the function does not exist.
__all__ = ['Entries', 'to_text', 'submit_entries', 'check_writable', 'attach',
           'bits']

#: How many digits a value is written to when nothing says otherwise. The
#: house style, and the reason for it is not storage: digits that are cheap to
#: compute carry no information, since anybody who wants the thousandth digit
#: of a value that evaluates in a second can have it. A hundred is far more
#: than enough to identify a number, which is what the database is for. More
#: digits earn their place when they were expensive to obtain, and a table that
#: writes more is expected to say why.
DIGITS = 100


def bits(digits: int, losing: int = 16) -> int:
    """Working precision, in bits, for ``digits`` correct decimal digits.

    Sage's interval and ball fields are built in **bits**, and this database
    counts **decimal digits**, because that is how a number is written down and
    quoted. One is not the other: a hundred digits needs 333 bits, and
    ``RealIntervalField(100)`` gives about thirty digits, not a hundred.

        def value(self, params, digits):
            return RealIntervalField(numberdb.bits(digits))(zeta(params['n']))

    ``losing`` is the guard: arithmetic loses low bits, so a field built at
    exactly the width of the answer will not produce an answer that wide.
    Sixteen covers the ordinary case. A computation that loses more -- a long
    sum, a badly conditioned series -- should ask for more rather than tune
    this: ``numberdb.bits(2 * digits)`` is the honest way to say "this one is
    expensive to get right".

    Nothing depends on getting it right, which is the point of it being a
    guess: `publish` measures what each value actually pins down and refuses to
    store a table of thirty-digit numbers that was meant to hold a hundred.
    """
    import math

    if digits <= 0:
        raise ValueError('digits must be positive')
    return int(math.ceil(digits * math.log2(10))) + max(0, int(losing))


def to_text(value: Any, digits: int = DIGITS) -> str:
    """A value as the string the database stores.

    Exact things keep their exact form: an integer, a fraction and a polynomial
    are written out in full, because writing fewer digits of an exact value
    does not round it, it makes it a different number.

    An approximation is written to ``digits`` significant figures in **one**
    form, whatever it was computed in::

        3.14159?

    The digits written are known and the last is uncertain by one, so that
    value is the interval (3.14158, 3.14160). Intervals and balls, real and
    complex, Sage's and this package's own, all arrive as that -- a table
    holding four spellings of the same convention would make every reader work
    out which one each row was written under.

    The precision travels inside the value, which is why a string is a sound
    way to carry a number here and a bare float is not.
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

    #A ball first, because it is written differently and must not be truncated
    #as text: `[1.20205690 +/- 2.8e-25]` cut to twenty significant characters
    #keeps the centre and mangles the radius into `+/- 0.00000`, which claims
    #an uncertainty a hundred million times too wide. Converting to an interval
    #gives the same number in the one form this database writes.
    #
    #Matched case-insensitively because Sage does not name these consistently:
    #`Real Interval Field with 53 bits of precision` but `Real ball field with
    #53 bits of precision`. Testing for 'Ball' refused every ball there is.
    if 'ball' in name.lower():
        value = _as_interval(value)
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


def _as_interval(ball):
    """A Sage ball as the interval that holds it, at the same precision.

    Sage is imported here and nowhere else in this module: reaching this line
    means the caller already handed us a Sage object, so Sage is loaded and
    the import costs nothing.
    """
    precision = ball.parent().precision()
    if 'complex' in str(ball.parent()).lower():
        from sage.rings.complex_interval_field import ComplexIntervalField

        return ComplexIntervalField(precision)(ball)
    from sage.rings.real_mpfi import RealIntervalField

    return RealIntervalField(precision)(ball)


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


def _as_yaml(tree):
    try:
        import yaml
    except ImportError:
        #JSON is a subset of YAML 1.2 and the server reads either, so a caller
        #without PyYAML is not blocked from writing.
        import json
        return json.dumps(tree, ensure_ascii=False, sort_keys=False)
    return yaml.dump(tree, sort_keys=False, allow_unicode=True,
                     default_flow_style=False)


def submit_entries(tid: str, entries: Union[Entries, Sequence[Mapping[str, Any]]],
                   message: str = '', produced_by: str = '',
                   upsert: bool = False, run: str = '',
                   client: Any = None) -> Dict[str, Any]:
    """Replace only the entries of table ``tid``. Internal; use `publish`.

    Entries and nothing else, which is the boundary the old arrangement had by
    accident: a script wrote its own `numbers.yaml` and could not reach the
    prose. Sending a whole document is not possible from this package at all,
    so a generator cannot delete a definition, the comments, the references or
    the tags by assembling a document out of what it happens to know.

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
    would: `UnauthorizedError` without a usable key, `NumberDBError` for an unknown
    table.
    """
    return submit_entries(tid, [], upsert=True, client=client,
                          message='checking that this table can be written to')


def attach(tid: str, name: str, content: Any, run: str = '',
           message: str = '', client: Any = None) -> Dict[str, Any]:
    """Put a file on a table, in the same revision as the run's entries.

    The code that produced a set of numbers belongs with them. Until now a
    program could send its results but not itself, so `generate.sage` was put
    in the repository by hand and drifted from whatever had actually run.

    Carrying the same ``run`` as the entries puts the file on the same
    revision, so somebody looking at where a number came from finds the code
    that made it rather than the code that happens to be there now.
    """
    from . import _default_client

    client = client or _default_client
    headers = {}
    if run:
        headers['X-Run-Id'] = run
    if message:
        headers['X-Edit-Message'] = message
    body = content if isinstance(content, str) else content.decode('utf8')
    return client.submit('/api/table/%s/file/%s'
                         % (str(tid).lstrip('tT'), name), body, headers)
