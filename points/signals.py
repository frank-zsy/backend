"""Signal handlers for points app to maintain cache consistency."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import PointSource, PointTransaction


@receiver(post_save, sender=PointSource)
@receiver(post_delete, sender=PointSource)
def clear_user_points_cache_on_source_change(sender, instance, **kwargs):
    """Clear user's cached total_points when PointSource is modified."""
    user = instance.user
    if user:
        user.clear_points_cache()


@receiver(post_save, sender=PointTransaction)
@receiver(post_delete, sender=PointTransaction)
def clear_user_points_cache_on_transaction_change(sender, instance, **kwargs):
    """Clear user's cached total_points when PointTransaction is modified."""
    user = instance.user
    if user:
        user.clear_points_cache()
