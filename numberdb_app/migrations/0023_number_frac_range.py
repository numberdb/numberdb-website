"""The fractional part as a GiST-indexed range, so it can be searched by overlap.

Same change as 0021/0022, for the search that was left behind: fractional parts
were matched by containment, which cannot return a value known more coarsely
than the query. 39344 of 45832 stored fractional parts are interval-valued, so
this was not a rare case.

Derived from frac_lower/frac_upper in Python for the same reason as before --
``double precision::numeric`` converts through the shortest round-trip text,
which moves a bound inward by a fraction of an ulp and can drop a value out of
a query it belongs to.

There is no wrap-around to handle. Sage's frac() widens an interval straddling
an integer to [0,1] rather than splitting it in two, and no stored row has a
negative lower bound, so every fractional part is already a single interval
inside [0,1].
"""

import math
from decimal import Decimal

from django.contrib.postgres.indexes import GistIndex
import django.contrib.postgres.fields.ranges
from django.db import migrations
from django.db.backends.postgresql.psycopg_any import NumericRange

BATCH = 2000


def _bound(value):
    number = float(value)
    if math.isinf(number) or math.isnan(number):
        return None
    return Decimal(number)


def backfill(apps, schema_editor):
    Number = apps.get_model('db', 'Number')
    pending = []
    #Inclusive bounds: Postgres reads [x, x) as empty, and 6488 stored
    #fractional parts are exactly known, so the default would hide them all.
    for row in Number.objects.all().only(
            'id', 'frac_lower', 'frac_upper').iterator(chunk_size=BATCH):
        row.frac_range = NumericRange(
            _bound(row.frac_lower), _bound(row.frac_upper), '[]')
        pending.append(row)
        if len(pending) >= BATCH:
            Number.objects.bulk_update(pending, ['frac_range'])
            pending = []
    if pending:
        Number.objects.bulk_update(pending, ['frac_range'])


def clear(apps, schema_editor):
    Number = apps.get_model('db', 'Number')
    Number.objects.update(frac_range=None)


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0022_backfill_value_range'),
    ]

    operations = [
        migrations.AddField(
            model_name='number',
            name='frac_range',
            field=django.contrib.postgres.fields.ranges.DecimalRangeField(
                blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='number',
            index=GistIndex(fields=['frac_range'],
                            name='number_frac_range_gist'),
        ),
        migrations.RunPython(backfill, clear),
    ]
