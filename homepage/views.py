"""
Helper utilities shared by the homepage public API.

The legacy template-rendered views (index and user_search) were removed when the
SPA frontend took over rendering. The remaining helpers stay here because
``homepage.api_v1`` reuses them for the public user search endpoint.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from accounts.models import UserProfile

MAX_SEARCH_RESULTS = 150


@dataclass
class SearchFilters:
    """Filters extracted from the incoming request."""

    DEFAULT_SORT = "relevance"
    SUPPORTED_SORTS = (DEFAULT_SORT, "username")

    location: str = ""
    company: str = ""
    sort: str = DEFAULT_SORT

    def ordering(self) -> Iterable[str]:
        """Return database ordering for the chosen sort."""
        sort_map = {
            "relevance": ["username"],
            "username": ["username"],
        }
        return sort_map.get(self.sort, sort_map["relevance"])


def _apply_optional_filters(queryset, filters: SearchFilters):
    """Apply optional location and company filters."""
    lookups = {
        "profile__location__icontains": filters.location,
        "profile__company__icontains": filters.company,
    }
    criteria = {lookup: value for lookup, value in lookups.items() if value}
    if criteria:
        queryset = queryset.filter(**criteria)
    return queryset


def _collect_available_values(queryset, field: str) -> list[str]:
    """Return ordered distinct values for the requested profile field."""
    lookup = f"profile__{field}"
    return list(
        queryset.exclude(**{f"{lookup}__isnull": True})
        .exclude(**{f"{lookup}__exact": ""})
        .values_list(lookup, flat=True)
        .distinct()
        .order_by(lookup)
    )


def _resolve_profile(user):
    try:
        return user.profile
    except UserProfile.DoesNotExist:  # pragma: no cover - defensive
        return None


def _serialize_user(user):
    """
    Serialize a user for the public search API response.

    ``profile_url`` is emitted as a plain frontend-style path so the SPA can
    route to the public profile without the backend hosting that page itself.
    """
    profile = _resolve_profile(user)
    return {
        "username": user.username,
        "display_name": user.get_full_name() or user.username,
        "bio": getattr(profile, "bio", "") or "",
        "company": getattr(profile, "company", "") or "",
        "location": getattr(profile, "location", "") or "",
        "profile_url": f"/u/{user.username}",
        "avatar_url": f"https://ui-avatars.com/api/?name={user.username}&background=random",
    }
