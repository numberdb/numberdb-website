"""Checks a table-building run should not have to write again.

Each of these caught a real error, or would have. They are here rather than in
the prompt because prose asking an agent to "make sure the arithmetic is exact"
gets a confident answer; a function that inspects the coefficients does not.

    from check import exactness, measure, agrees_with, names_its_rings

Nothing here talks to the database. `stored` reads a table back so that the
values can be checked as published rather than as computed, which is the one
check `verify()` cannot do -- it compares a table with the generator that made
it and so cannot catch a generator wrong in the same way twice.
"""

import os
import re


def exactness(values):
    """Refuse anything that is not exactly what it claims to be.

    The trap this exists for: in `sage -python` there is no preparser, so
    `factorial(30)` is a Python int and `factorial(n) / k` is float division --
    exact to 2^53 and quietly wrong after it. A Bessel polynomial built that
    way was right to n = 15 and wrong from n = 16, in its last two digits.

    `c in ZZ` does not catch it, because that is true of a float that happens
    to be integral. This looks at the type.

    Returns a list of complaints; empty means every coefficient is a Sage
    integer or rational.
    """
    complaints = []
    for key, value in _pairs(values):
        for coefficient in _coefficients(value):
            name = type(coefficient).__name__
            if _is_integer_interval_text(coefficient):
                #The one string an exact table returns on purpose: `[43, 48]`
                #for a Ramsey number, `[40, 44]` for a kissing number -- an
                #integer known to lie between two integers. It is an
                #enclosure in the database's own spelling, and the client
                #writes a string verbatim, which is the only way to store it:
                #a RealInterval with those endpoints is written in decimal
                #form. The first version of this check reported it as
                #"unexpected type str", and the run that met that wrapped
                #the string in a subclass carrying its endpoints so that the
                #check would pass -- which the client's YAML writer then
                #serialised as a Python object, storing eighteen entries as
                #mappings. A check that refuses the right answer teaches
                #people to disguise it.
                continue
            if _is_ball_text(coefficient):
                #The other string a table returns on purpose: `0.7478008 +/-
                #2e-7`, a published estimate with the paper's uncertainty as
                #its radius, in the database's own spelling -- what the table
                #of the fine-structure constant stores and what a `measured`
                #table of percolation thresholds returns for each transcribed
                #row. The client writes it verbatim and reads the digits it
                #claims from the radius. Plain `str` and a positive radius,
                #for the same reasons as the integer interval above.
                continue
            if isinstance(coefficient, float) or 'float' in name.lower():
                complaints.append(
                    '%s: coefficient %r is a %s, not exact -- something '
                    'divided with / where both sides were Python ints'
                    % (key, coefficient, name))
                break
            if _is_enclosure(coefficient):
                #A ball or an interval is not a failure of exactness, it is
                #the strongest thing an inexact value can carry: the error
                #bound travels with the number. What must not pass is one
                #that encloses everything -- a nan ball compares true against
                #any interval, so letting one through turns every later
                #agreement check into a formality that cannot fail. A
                #polygamma generator produced exactly that, from arb taking a
                #negative base to a negative power, and a control "passed"
                #while establishing nothing.
                if not _is_finite(coefficient):
                    complaints.append(
                        '%s: value %r is not finite -- an enclosure this wide '
                        'contains every answer, so nothing compared against '
                        'it can fail' % (key, coefficient))
                    break
                continue
            if name not in ('Integer', 'Rational', 'int'):
                complaints.append('%s: coefficient of unexpected type %s'
                                  % (key, name))
                break
    return complaints


def _is_integer_interval_text(value):
    """Whether this is the string `[a, b]` with integers a < b: the interval
    an exact table stores for an integer that is only known to lie between
    two others. Must be a plain string -- a subclass is what the client
    serialises as an object -- and must have nonzero width, since `[2, 2]`
    is an integer pretending to be uncertain."""
    if type(value) is not str:
        return False
    found = re.fullmatch(r'\[(-?\d+), (-?\d+)\]', value)
    return bool(found) and int(found.group(1)) < int(found.group(2))


def _is_ball_text(value):
    """Whether this is the string `centre +/- radius` with a decimal centre
    and a positive radius: the form a measured value is stored in. Must be
    a plain string, and the radius must be positive, since `x +/- 0` is a
    point pretending to be an enclosure."""
    if type(value) is not str:
        return False
    found = re.fullmatch(
        r'(-?\d+(?:\.\d+)?(?:[eE]-?\d+)?) \+/- (\d+(?:\.\d+)?(?:[eE]-?\d+)?)', value)
    if not found:
        return False
    from decimal import Decimal, InvalidOperation
    try:
        return Decimal(found.group(2)) > 0
    except InvalidOperation:
        return False


def _is_enclosure(value):
    """Whether this carries its own error bound: a ball or an interval."""
    name = type(value).__name__
    return ('Ball' in name or 'IntervalFieldElement' in name
            or 'Interval' in name)


def _is_finite(value):
    """Whether an enclosure actually pins something down."""
    try:
        if hasattr(value, 'is_finite'):
            return bool(value.is_finite())
        if hasattr(value, 'is_NaN'):
            return not bool(value.is_NaN())
    except Exception:                                    # noqa: BLE001
        return False
    return True


def measure(values):
    """How long the entries get, so a range is chosen from data.

    Length is what decides these tables, not the stated size limits. The
    Fibonacci polynomials stop where the longest is 1107 characters; `h_6` in
    six variables would be 6969, which nobody reads.

    `longest` is the written value alone. `block_kb` is what the server
    measures against its limit: the YAML of the flat records, annotations
    included -- a comment on every entry is part of the block, and a table of
    607 hundred-digit values found that out by coming in at 166 KB rather
    than the 75 KB its numbers alone would make.
    """
    lengths = {key: len(str(_number_of(value))) for key, value in _pairs(values)}
    if not lengths:
        return {'entries': 0, 'longest': 0, 'block_kb': 0.0, 'longest_at': None}
    longest_at = max(lengths, key=lambda k: lengths[k])
    return {
        'entries': len(lengths),
        'longest': lengths[longest_at],
        'longest_at': longest_at,
        'block_kb': _block_bytes(values) / 1024.0,
    }


def _number_of(value):
    """The value inside an entry, whether it came bare or as a mapping.

    A generator may return ``{'number': x, 'comment': '...'}``, which the
    skill says it may; the first version of these checks reported that as
    "coefficient of unexpected type dict" and measured the comment's length
    as the value's.
    """
    if isinstance(value, dict) and 'number' in value:
        return value['number']
    return value


def _block_bytes(values):
    """The size of the entries block as the server serialises it.

    The same `yaml.dump` of the same flat records as `numberdb_app/limits.py`;
    without PyYAML, the old estimate of 24 bytes of overhead per entry.
    """
    records = []
    for key, value in _pairs(values):
        record = {'params': {'key': str(key)}}
        if isinstance(value, dict):
            record.update({k: (str(v) if k == 'number' else v)
                           for k, v in value.items()})
        else:
            record['number'] = str(value)
        records.append(record)
    try:
        import yaml
    except ImportError:
        return sum(len(str(_number_of(v))) + 24 for _, v in _pairs(values))
    return len(yaml.dump(records, default_flow_style=False,
                         allow_unicode=True).encode('utf8'))


def agrees_with(values, other):
    """Compare against a computation that shares no code with the generator.

    A generator checked against its own definition proves nothing. `other` is
    called with the same key and must return the same value.
    """
    disagreements = []
    for key, value in _pairs(values):
        try:
            expected = other(key)
        except Exception as trouble:                # noqa: BLE001
            disagreements.append('%s: the independent computation raised %s: %s'
                                 % (key, type(trouble).__name__, trouble))
            continue
        if expected != value:
            disagreements.append('%s: %s here, %s independently'
                                 % (key, str(value)[:60], str(expected)[:60]))
    return disagreements


def names_its_rings(path):
    """A generator should name the rings it uses rather than import sage.all.

    `sage.all` does not exist in a modular passagemath, and the same source
    then runs in both. Returns a list of complaints.
    """
    with open(path, encoding='utf8') as handle:
        source = handle.read()
    complaints = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith(('from sage.all import', 'import sage.all')):
            complaints.append('imports sage.all: %s' % stripped)
    if 'import numberdb.sage' not in source:
        complaints.append('does not import numberdb.sage, which is what '
                          'initialises Sage before a ring can be imported')
    return complaints


def stored(tid):
    """The table as published: {params tuple or string: written value}.

    Read back so the identities can be checked on what a reader will see.
    Needs the Django app; call it from `manage.py shell`.
    """
    from numberdb_app.editing import tree_of
    from numberdb_app.models import Table

    tree = tree_of(Table.objects.get(tid=tid).head_revision)
    out = {}
    for entry in tree.get('Numbers') or []:
        if not isinstance(entry, dict) or not entry.get('number'):
            continue
        params = entry.get('params') or {}
        key = tuple(sorted(params.items())) if len(params) > 1 \
            else (list(params.values()) or [None])[0]
        out[key] = entry['number']
    return out


def _pairs(values):
    if isinstance(values, dict):
        return list(values.items())
    return list(enumerate(values))


def _coefficients(value):
    """Every number inside a value, whatever shape it arrives in.

    A polynomial, a bare list of coefficients, a nested list, or a single
    number: the check is about the numbers, and the first version of it
    reported "unexpected type list" for a list of floats instead of reporting
    the floats -- which is a check stumbling on the shape rather than doing
    its job.
    """
    value = _number_of(value)
    getter = getattr(value, 'coefficients', None)
    if callable(getter):
        try:
            return _flatten(getter())
        except Exception:                            # noqa: BLE001
            pass
    return _flatten(value)


def _flatten(value):
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            out.extend(_flatten(item))
        return out
    return [value]
