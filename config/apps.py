"""Project-level Django app configurations."""

from django.contrib.admin.apps import AdminConfig


class GitHubAdminConfig(AdminConfig):
    """Replace the default admin site with the GitHub OAuth-backed one."""

    default_site = "config.admin_site.GitHubAdminSite"
