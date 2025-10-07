"""Views for the points app."""

import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from points.models import Tag

TREND_DAYS = 30


def _trend_date_range():
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=TREND_DAYS - 1)
    return start_date, end_date


def _build_trend_labels(start_date):
    return [
        (start_date + timedelta(days=offset)).strftime("%m/%d")
        for offset in range(TREND_DAYS)
    ]


def _user_tags(user):
    return Tag.objects.filter(point_sources__user=user).distinct().order_by("name")


def _collect_daily_changes(user, tag, start_date):
    changes: dict = {}

    earn_sources = (
        user.point_sources.filter(tags=tag, created_at__date__gte=start_date)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total_points=Sum("initial_points"))
        .order_by("date")
    )
    for item in earn_sources:
        changes[item["date"]] = changes.get(item["date"], 0) + item["total_points"]

    spend_transactions = (
        user.point_transactions.filter(
            created_at__date__gte=start_date,
            transaction_type="SPEND",
            consumed_sources__tags=tag,
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total_points=Sum("points"))
        .order_by("date")
    )
    for item in spend_transactions:
        changes[item["date"]] = changes.get(item["date"], 0) + item["total_points"]

    return changes


def _build_tag_trend(user, tag, start_date):
    daily_changes = _collect_daily_changes(user, tag, start_date)
    current_tag_points = sum(
        source.remaining_points for source in user.point_sources.filter(tags=tag)
    )
    total_change = sum(daily_changes.values())
    starting_points = current_tag_points - total_change

    trend_data = []
    cumulative = starting_points
    for offset in range(TREND_DAYS):
        current_date = start_date + timedelta(days=offset)
        cumulative += daily_changes.get(current_date, 0)
        trend_data.append(cumulative)

    if current_tag_points > 0 or total_change != 0:
        return {"label": tag.name, "data": trend_data}
    return None


@login_required
def my_points(request):
    """
    Display user's points information.

    Shows:
    - Total points
    - Points by tag
    - Point sources
    - Transaction history

    """
    user = request.user

    # Get points by tag
    points_by_tag = user.get_points_by_tag()

    # Get active point sources (with remaining points)
    active_sources = user.point_sources.filter(remaining_points__gt=0).order_by(
        "-created_at"
    )

    # Get transaction history with pagination
    transactions = user.point_transactions.select_related().order_by("-created_at")
    paginator = Paginator(transactions, 20)  # 20 transactions per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    start_date, _ = _trend_date_range()
    trend_labels = _build_trend_labels(start_date)
    trend_datasets = []
    for tag in _user_tags(user):
        dataset = _build_tag_trend(user, tag, start_date)
        if dataset:
            trend_datasets.append(dataset)

    context = {
        "total_points": user.total_points,
        "points_by_tag": points_by_tag,
        "active_sources": active_sources,
        "page_obj": page_obj,
        "trend_labels_json": json.dumps(trend_labels),
        "trend_datasets_json": json.dumps(trend_datasets),
    }

    return render(request, "points/my_points.html", context)
