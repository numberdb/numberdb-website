from django.apps import AppConfig


class NumberdbAppConfig(AppConfig):
    name = 'numberdb_app'
    # Historical app label used throughout migrations and model relations.
    label = 'db'

    def ready(self):
        # Registers the configuration checks. Imported here rather than at
        # module level because registering a check touches settings, which are
        # not necessarily loaded when this module first is.
        from . import checks  # noqa: F401
