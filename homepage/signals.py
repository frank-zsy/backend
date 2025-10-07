"""Signal handlers to keep homepage caches consistent."""

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import bump_search_cache_version

User = get_user_model()
UserProfile = apps.get_model("accounts", "UserProfile")
PointSource = apps.get_model("points", "PointSource")
PointTransaction = apps.get_model("points", "PointTransaction")


def _invalidate_search_cache(*_, **__):
    bump_search_cache_version()


@receiver(post_save, sender=User)
@receiver(post_delete, sender=User)
@receiver(post_save, sender=UserProfile)
@receiver(post_delete, sender=UserProfile)
def invalidate_cache_on_user_updates(sender, **kwargs):
    """Reset cached search results when user identity data changes."""
    _invalidate_search_cache(sender, **kwargs)


@receiver(post_save, sender=PointSource)
@receiver(post_delete, sender=PointSource)
@receiver(post_save, sender=PointTransaction)
@receiver(post_delete, sender=PointTransaction)
def invalidate_cache_on_points_updates(sender, **kwargs):
    """Reset cached search results when user point data changes."""
    _invalidate_search_cache(sender, **kwargs)
