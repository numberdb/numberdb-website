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
    """
    lengths = {key: len(str(value)) for key, value in _pairs(values)}
    if not lengths:
        return {'entries': 0, 'longest': 0, 'block_kb': 0.0, 'longest_at': None}
    longest_at = max(lengths, key=lambda k: lengths[k])
    return {
        'entries': len(lengths),
        'longest': lengths[longest_at],
        'longest_at': longest_at,
        'block_kb': sum(n + 24 for n in lengths.values()) / 1024.0,
    }


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
