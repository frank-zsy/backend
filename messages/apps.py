"""站内信应用配置."""

from django.apps import AppConfig


class SiteMessagesConfig(AppConfig):
    """站内信应用配置."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "messages"
    label = "site_messages"
    verbose_name = "站内信"
