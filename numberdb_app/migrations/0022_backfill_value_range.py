"""Fill value_range from the bounds already stored.

The range is a repackaging of ``lower`` and ``upper``, not new information, so
it can be derived in place. Rebuilding the corpus would produce byte-identical
values and costs an hour of Sage on a 1 GB machine, which is how the site was
taken down once already.

Done in Python rather than as one UPDATE. ``double precision::numeric`` in
Postgres converts through the shortest text that round-trips, so 0.1 becomes
exactly 0.1 rather than the 0.1000000000000000055511151231257827 the double
actually holds. That moves an upper bound *inward* by a fraction of an ulp,
which is unsound in exactly the direction that matters -- a stored value could
stop matching a query it belongs to. ``Decimal(float)`` is the exact binary
value, so the range never claims more than the float did.
"""

import math
from decimal import Decimal

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
    #Inclusive bounds: Postgres reads [x, x) as empty, and every exactly-known
    #value has lower == upper, so the default would exclude them all.
    for row in Number.objects.all().only('id', 'lower', 'upper').iterator(
            chunk_size=BATCH):
        row.value_range = NumericRange(_bound(row.lower), _bound(row.upper), '[]')
        pending.append(row)
        if len(pending) >= BATCH:
            Number.objects.bulk_update(pending, ['value_range'])
            pending = []
    if pending:
        Number.objects.bulk_update(pending, ['value_range'])


def clear(apps, schema_editor):
    Number = apps.get_model('db', 'Number')
    Number.objects.update(value_range=None)


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0021_number_value_range'),
    ]

    operations = [
        migrations.RunPython(backfill, clear),
    ]
