"""Store the faithful value beside the search columns.

Each number gains ``exact_text``: its canonical spelling in a documented
format, produced by ``utils.numbers``. That text is the definition of the
value; the existing float bounds, digit strings and hashes become explicitly a
lossy projection used to find candidates.

No data migration. The canonical text lives in numberdb-data, so the index is
rebuilt from source rather than backfilled -- and the source is the only place
it could come from, since a float interval cannot regenerate the notation it
was derived from.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0018_alter_number_id_alter_numbercomplex_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='number',
            name='exact_text',
            field=models.TextField(db_index=True, default=''),
        ),
        migrations.AddField(
            model_name='numbercomplex',
            name='exact_text',
            field=models.TextField(db_index=True, default=''),
        ),
        migrations.AddField(
            model_name='numberpadic',
            name='exact_text',
            field=models.TextField(db_index=True, default=''),
        ),
        migrations.AddField(
            model_name='polynomial',
            name='exact_text',
            field=models.TextField(db_index=True, default=''),
        ),
    ]
