"""A GiST-indexed range, so real search can ask for overlap.

The float bounds are indexed as two separate btrees, which together answer
*containment* efficiently -- ``lower BETWEEN a AND b AND upper BETWEEN a AND b``
combines into a BitmapAnd in about 0.7 ms. That is fast, and it is the wrong
question: it finds stored intervals inside the query and misses a coarsely
stored value that contains it, which is a false negative on a number that may
well be the one being looked for.

Overlap cannot be served that way -- as two unbounded half-ranges it degrades
to a sequential scan of 6-24 ms -- so it needs a single indexable object.
Measured on the 45832 rows already stored:

    containment, BitmapAnd (present behaviour)   0.73 ms
    overlap, no index                            6-24 ms
    overlap, GiST on a stored range              0.63 ms

so the correct question is answered no slower than the incorrect one, once the
range is stored rather than recomputed per row.

Bounds are NULL where the float projection saturated. 310 values exceed what a
double can hold, and building a range index over them fails outright:

    ERROR: "17976931348623199...922.658044843204" is out of range
           for type double precision

An unbounded range is both the honest representation and one GiST indexes
natively, so those rows stay searchable instead of being excluded.
"""

from django.contrib.postgres.indexes import GistIndex
import django.contrib.postgres.fields.ranges
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0020_exact_text_hash_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='number',
            name='value_range',
            field=django.contrib.postgres.fields.ranges.DecimalRangeField(
                blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='number',
            index=GistIndex(fields=['value_range'], name='number_range_gist'),
        ),
    ]
