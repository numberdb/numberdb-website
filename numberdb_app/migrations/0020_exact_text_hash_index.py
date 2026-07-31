"""Index ``exact_text`` by hash rather than btree.

A btree index row is capped at about 2704 bytes. The Igusa polynomials render
to 2856, so building the btree index from 0019 fails outright during a rebuild:

    OperationalError: index row size 2856 exceeds btree version 4 maximum 2704
    HINT: Consider a function index of an MD5 hash of the value

``exact_text`` is looked up by equality -- "is this exact value already
stored?" -- so a hash index is the right structure anyway: it hashes the value,
has no length limit, and does not pay for an ordering nobody asks of it.
Ordering and range queries belong to the float projection.
"""

from django.contrib.postgres.indexes import HashIndex
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0019_add_exact_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='number',
            name='exact_text',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='numbercomplex',
            name='exact_text',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='numberpadic',
            name='exact_text',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='polynomial',
            name='exact_text',
            field=models.TextField(default=''),
        ),
        migrations.AddIndex(
            model_name='number',
            index=HashIndex(fields=['exact_text'], name='number_exact_hash'),
        ),
        migrations.AddIndex(
            model_name='numbercomplex',
            index=HashIndex(fields=['exact_text'], name='numbercomplex_exact_hash'),
        ),
        migrations.AddIndex(
            model_name='numberpadic',
            index=HashIndex(fields=['exact_text'], name='numberpadic_exact_hash'),
        ),
        migrations.AddIndex(
            model_name='polynomial',
            index=HashIndex(fields=['exact_text'], name='polynomial_exact_hash'),
        ),
    ]
