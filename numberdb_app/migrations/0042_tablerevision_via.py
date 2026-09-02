from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0041_userprofile_operated_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='tablerevision',
            name='via',
            field=models.CharField(
                blank=True,
                choices=[('web', 'the site'), ('api', 'the API directly'),
                         ('package', 'the numberdb package'),
                         ('import', 'an importer')],
                default='web',
                max_length=16,
            ),
        ),
    ]
