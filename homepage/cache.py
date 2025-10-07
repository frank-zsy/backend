"""Cache utilities for homepage features."""

from django.core.cache import cache
from django.utils.crypto import get_random_string

SEARCH_CACHE_VERSION_KEY = "homepage:user_search:version"
SEARCH_CACHE_VERSION_TIMEOUT = None


def _generate_version() -> str:
    return get_random_string(12)


def get_search_cache_version() -> str:
    """Return the current cache version for user search results."""
    version = cache.get(SEARCH_CACHE_VERSION_KEY)
    if version is None:
        version = _generate_version()
        cache.set(SEARCH_CACHE_VERSION_KEY, version, SEARCH_CACHE_VERSION_TIMEOUT)
    return version


def bump_search_cache_version() -> None:
    """Invalidate cached search results by rotating the version token."""
    cache.set(
        SEARCH_CACHE_VERSION_KEY, _generate_version(), SEARCH_CACHE_VERSION_TIMEOUT
    )
