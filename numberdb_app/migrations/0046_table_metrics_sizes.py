from django.db import migrations, models


class Migration(migrations.Migration):
    """How big a table's values are, not only how many there are."""

    dependencies = [
        ('db', '0045_table_metrics_and_costs'),
    ]

    operations = [
        migrations.AddField(
            model_name='tablemetrics',
            name='document_bytes',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='tablemetrics',
            name='value_chars_median',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tablemetrics',
            name='digits_median',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tablemetrics',
            name='degree_median',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tablemetrics',
            name='terms_median',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
