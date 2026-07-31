"""How well each value is known, relative to its own size.

Search by number answers "I measured this, is it known?", so an entry earns a
place only if matching it says which number the asker has. A value that is
merely bounded cannot: the exponent of matrix multiplication lies somewhere in
[2, 2.3728596], and matching it reports that one wide range overlaps another.

Measured on the exact value, not the float projection. The two disagree in both
directions -- 101471818419863/165 is exact but projects to a span of 1.2e-4,
and the subnormal entries are known in full while their projection keeps about
one bit -- so the projection would exclude precisely the values search was just
fixed to find.

Stored rather than computed per query because it needs exact_text parsed, which
SQL cannot do. Kept as the measurement rather than a verdict, so the cutoff
stays a constant in search.py.

Across the corpus, 16 of 45832 rows are known to worse than 1e-5:

    rel 0.10 - 0.97   Ramsey numbers, matrix multiplication exponent (7)
    rel 1.3e-4        mass ratios, e.g. 0.88153(17)                  (9)
"""

from django.db import migrations, models

BATCH = 2000


def _relative_width(exact_text):
    if not exact_text:
        return None
    try:
        from utils.numbers import parse_real
        low, high = parse_real(exact_text).bounds()
    except Exception:
        return None
    if high == low:
        return 0.0
    magnitude = max(abs(low), abs(high))
    if magnitude == 0:
        return float('inf')
    return float((high - low) / magnitude)


def backfill(apps, schema_editor):
    Number = apps.get_model('db', 'Number')
    pending = []
    for row in Number.objects.all().only('id', 'exact_text').iterator(
            chunk_size=BATCH):
        row.exact_relative_width = _relative_width(row.exact_text)
        pending.append(row)
        if len(pending) >= BATCH:
            Number.objects.bulk_update(pending, ['exact_relative_width'])
            pending = []
    if pending:
        Number.objects.bulk_update(pending, ['exact_relative_width'])


def clear(apps, schema_editor):
    Number = apps.get_model('db', 'Number')
    Number.objects.update(exact_relative_width=None)


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0023_number_frac_range'),
    ]

    operations = [
        migrations.AddField(
            model_name='number',
            name='exact_relative_width',
            field=models.FloatField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(backfill, clear),
    ]
