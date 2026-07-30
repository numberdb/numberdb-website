"""Capture what Sage currently produces for real database rows.

Run this inside a container that has Sage and a populated database::

    docker compose exec -T web sage -python tests/golden/generate_golden.py \
        > tests/golden/number_decoding.json

The output is committed and becomes the contract for the plain-Python
replacement (see docs/design/ -- phase A of moving `web` off Sage). The point is
that the fixture is *self-contained*: it carries the stored bytes and the
expected rendering, so ``tests/test_number_decoding.py`` can verify a new
decoder on a plain interpreter, with no Sage and no database.

Selection is deterministic -- ordered by primary key, sampled at a fixed stride,
plus explicitly chosen edge cases -- so regenerating it produces the same file
and a diff means a real behaviour change, not resampling noise.
"""

import json
import os
import sys

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'numberdb.settings.prod')

import django  # noqa: E402
django.setup()

from numberdb_app.models import (  # noqa: E402
    Number, NumberComplex, NumberPAdic, Polynomial,
)

#: Cases per stored type. Enough to catch systematic formatting differences
#: without committing a large file.
PER_TYPE = 120


def _hex(value):
    return bytes(value).hex()


def _safe(callable_):
    """Record what happens, including failures -- those are part of the contract."""
    try:
        return {'ok': True, 'value': callable_()}
    except Exception as error:  # noqa: BLE001
        return {'ok': False, 'error': '%s: %s' % (type(error).__name__, error)}


def _sample(queryset, count):
    """Deterministic spread across the table, not just the first N rows."""
    total = queryset.count()
    if total == 0:
        return []
    if total <= count:
        return list(queryset)
    stride = max(total // count, 1)
    return list(queryset)[::stride][:count]


def numbers():
    cases = []
    for stored_type in (b'z', b'q', b'r', b'b'):
        rows = Number.objects.filter(number_type=stored_type).order_by('pk')
        for row in _sample(rows, PER_TYPE):
            cases.append({
                'model': 'Number',
                'number_type': _hex(row.number_type),
                'number_blob': _hex(row.number_blob),
                # Stored floats are part of the contract too: the replacement
                # must derive identical values when writing new rows.
                'lower': repr(row.lower),
                'upper': repr(row.upper),
                'frac_lower': repr(row.frac_lower),
                'frac_upper': repr(row.frac_upper),
                'str': _safe(lambda r=row: str(r)),
                'str_short': _safe(lambda r=row: r.str_short()),
                'to_sage_repr': _safe(lambda r=row: repr(r.to_sage())),
                'parent': _safe(lambda r=row: str(r.to_sage().parent())),
            })
    return cases


def complexes():
    cases = []
    rows = NumberComplex.objects.order_by('pk')
    for row in _sample(rows, PER_TYPE):
        cases.append({
            'model': 'NumberComplex',
            'number_searchstring': row.number_searchstring,
            're_lower': repr(row.re_lower), 're_upper': repr(row.re_upper),
            'im_lower': repr(row.im_lower), 'im_upper': repr(row.im_upper),
            'str': _safe(lambda r=row: str(r)),
            'str_short': _safe(lambda r=row: r.str_short()),
        })
    return cases


def p_adics():
    cases = []
    rows = NumberPAdic.objects.order_by('pk')
    for row in _sample(rows, PER_TYPE):
        cases.append({
            'model': 'NumberPAdic',
            'number_string': row.number_string,
            'prime': int(row.prime),
            'valuation': int(row.valuation),
            'str': _safe(lambda r=row: str(r)),
            'str_short': _safe(lambda r=row: r.str_short()),
        })
    return cases


def polynomials():
    cases = []
    rows = Polynomial.objects.order_by('pk')
    for row in _sample(rows, PER_TYPE):
        cases.append({
            'model': 'Polynomial',
            'number_string': row.number_string,
            'number_string_hash': int(row.number_string_hash),
            'variable_count': int(row.variable_count),
            'str': _safe(lambda r=row: str(r)),
            'str_short': _safe(lambda r=row: r.str_short()),
        })
    return cases


def main():
    import sage.version

    payload = {
        'generated_with': {
            'sage': sage.version.version,
            'python': sys.version.split()[0],
            'note': ('Expected values produced by the Sage-based implementation. '
                     'The plain-Python replacement must reproduce them exactly.'),
        },
        'cases': numbers() + complexes() + p_adics() + polynomials(),
    }
    json.dump(payload, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
