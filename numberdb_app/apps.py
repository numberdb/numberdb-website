from django.apps import AppConfig


class NumberdbAppConfig(AppConfig):
    name = 'numberdb_app'
    # Historical app label used throughout migrations and model relations.
    label = 'db'
