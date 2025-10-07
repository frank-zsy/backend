"""Django app configuration for homepage."""

from django.apps import AppConfig


class HomepageConfig(AppConfig):
    """Configuration for the homepage app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "homepage"
    verbose_name = "首页"

    def ready(self):
        """Import signal handlers when app is ready."""
        super().ready()
        import homepage.signals  # noqa: F401
