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
           'create']

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

    #Sage objects, when the caller has Sage. Tested by behaviour rather than by
    #importing Sage, so this module stays importable without it.
    parent = getattr(value, 'parent', None)
    if parent is not None:
        try:
            return _sage_text(value, digits)
        except Exception:
            pass

    if isinstance(value, bool):
        #Before int, which bool is a subclass of, and never a number here.
        raise TypeError('a boolean is not a number')
    if isinstance(value, int):
        return str(value)

    from fractions import Fraction
    if isinstance(value, Fraction):
        return (str(value.numerator) if value.denominator == 1
                else '%d/%d' % (value.numerator, value.denominator))

    if isinstance(value, float):
        raise TypeError(
            'a float does not say how precise it is, so it cannot be stored '
            'as it stands. Give a string, a Fraction, or a Sage real interval, '
            'or say the precision: to_text(value, digits=15)')

    raise TypeError('cannot write %s as a number' % (type(value).__name__,))


def _sage_text(value, digits):
    """The string form of a Sage object."""
    parent = value.parent()
    name = str(parent)

    if 'Interval' in name or 'Ball' in name:
        #`?` marks the last digit as uncertain, which is how the site records
        #that this is a ball rather than an exact decimal.
        text = value.str(digits=digits, style='question')
        return text.replace('?', '?') if '?' in text else text + '?'
    if 'Integer Ring' in name or 'Rational Field' in name:
        return str(value)
    if 'Polynomial' in name:
        return str(value)
    if 'p-adic' in name or name.startswith('Q_') or 'Qp' in name:
        return str(value)
    #A plain real or complex field: no interval, so the caller has chosen a
    #precision and the digits are what they are.
    return str(value)


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
    """
    from . import _default_client

    client = client or _default_client
    headers = {'X-Produced-By': produced_by or 'numberdb-python'}
    if message:
        headers['X-Edit-Message'] = message
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
