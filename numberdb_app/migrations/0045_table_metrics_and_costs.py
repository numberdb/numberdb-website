import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """What an editor wants to know about a table, and what it cost to make."""

    dependencies = [
        ('db', '0044_rename_restates_repeats'),
    ]

    operations = [
        migrations.CreateModel(
            name='TableMetrics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_count', models.IntegerField(default=0)),
                ('edit_count', models.IntegerField(default=0)),
                ('data_type', models.CharField(blank=True, default='', max_length=32)),
                ('agent_cost_usd', models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('table', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to='db.table')),
            ],
            options={'verbose_name_plural': 'table metrics'},
        ),
        migrations.CreateModel(
            name='TableCost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', models.CharField(max_length=64)),
                ('role', models.CharField(max_length=16)),
                ('engine', models.CharField(blank=True, default='', max_length=16)),
                ('cost_usd', models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ('runs', models.IntegerField(default=0)),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='costs', to='db.table')),
            ],
        ),
        migrations.AddIndex(
            model_name='tablecost',
            index=models.Index(fields=['model'], name='db_tablecos_model_idx'),
        ),
        migrations.AddIndex(
            model_name='tablecost',
            index=models.Index(fields=['role'], name='db_tablecos_role_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='tablecost',
            unique_together={('table', 'model', 'role')},
        ),
    ]
