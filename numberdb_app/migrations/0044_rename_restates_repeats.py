from django.db import migrations


class Migration(migrations.Migration):
    """`restating` already meant something else.

    The Python client's `publish(restating=True)` rewrites entries whose
    stored value says the same thing in different digits. That is published
    on PyPI and other people's generators pass it, so the field named a day
    earlier is the one that moves.
    """

    dependencies = [
        ('db', '0043_table_restates'),
    ]

    operations = [
        migrations.RenameField(
            model_name='table',
            old_name='restates',
            new_name='repeats',
        ),
    ]
