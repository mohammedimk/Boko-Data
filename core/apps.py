from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'VTU Core Platform'

    def ready(self):
        # Import signal handlers so they are registered when the app starts.
        import core.signals  # noqa: F401
