"""Views for the homepage app."""

import json
from contextlib import suppress

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.models import UserProfile

MAX_SEARCH_RESULTS = 150
PAGE_SIZE = 12


def index(request):
    """Render the homepage index page."""
    return render(request, "homepage/index.html")


def user_search(request):
    """Search for users by keyword and render results with filters."""
    query = request.GET.get("q", "").strip()
    if not query:
        messages.info(request, "请输入要搜索的关键词。")
        return redirect("homepage:index")

    User = get_user_model()

    # Redirect immediately on exact username match (case-insensitive).
    exact_match = User.objects.filter(username__iexact=query).first()
    if exact_match:
        return redirect("public_profile", username=exact_match.username)

    users_qs = (
        User.objects.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__company__icontains=query)
            | Q(profile__location__icontains=query)
        )
        .select_related("profile")
        .annotate(points_sum=Coalesce(Sum("point_sources__remaining_points"), 0))
        .distinct()
    )

    # Filters
    location = request.GET.get("location", "").strip()
    company = request.GET.get("company", "").strip()
    min_points_raw = request.GET.get("min_points", "").strip()
    sort = request.GET.get("sort", "relevance")

    if location:
        users_qs = users_qs.filter(profile__location__icontains=location)

    if company:
        users_qs = users_qs.filter(profile__company__icontains=company)

    invalid_min_points = False
    min_points_value = None
    if min_points_raw:
        try:
            min_points_value = int(min_points_raw)
        except ValueError:
            invalid_min_points = True
            messages.error(request, "最低积分需要是整数。")
        else:
            if min_points_value > 0:
                users_qs = users_qs.filter(points_sum__gte=min_points_value)

    sort_map = {
        "relevance": ["-points_sum", "username"],
        "points_desc": ["-points_sum", "username"],
        "points_asc": ["points_sum", "username"],
        "username": ["username"],
    }
    order_by = sort_map.get(sort, sort_map["relevance"])
    users_qs = users_qs.order_by(*order_by)

    total_matches = users_qs.count()

    # Prepare filter options based on current result set (before limiting).
    available_locations = (
        users_qs.exclude(profile__location__isnull=True)
        .exclude(profile__location__exact="")
        .values_list("profile__location", flat=True)
        .distinct()
        .order_by("profile__location")
    )
    available_companies = (
        users_qs.exclude(profile__company__isnull=True)
        .exclude(profile__company__exact="")
        .values_list("profile__company", flat=True)
        .distinct()
        .order_by("profile__company")
    )

    results = []
    for user in users_qs[:MAX_SEARCH_RESULTS]:
        profile = None
        with suppress(UserProfile.DoesNotExist):
            profile = user.profile

        bio = profile.bio if profile and profile.bio else ""
        company_display = profile.company if profile and profile.company else ""
        location_display = profile.location if profile and profile.location else ""
        total_points = getattr(user, "points_sum", 0)

        results.append(
            {
                "username": user.username,
                "display_name": (user.get_full_name() or user.username),
                "bio": bio,
                "company": company_display,
                "location": location_display,
                "total_points": total_points,
                "profile_url": reverse("public_profile", args=[user.username]),
                "avatar_url": f"https://ui-avatars.com/api/?name={user.username}&background=random",
            }
        )

    context = {
        "query": query,
        "results": results,
        "results_json": json.dumps(results, ensure_ascii=False),
        "results_count": total_matches,
        "max_results": MAX_SEARCH_RESULTS,
        "filters": {
            "location": location,
            "company": company,
            "min_points": min_points_raw,
            "sort": sort,
        },
        "available_locations": list(available_locations),
        "available_companies": list(available_companies),
        "page_size": PAGE_SIZE,
        "invalid_min_points": invalid_min_points,
    }

    return render(request, "homepage/search_results.html", context)
