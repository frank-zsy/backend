"""Views for the points app."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render


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

    context = {
        "total_points": user.total_points,
        "points_by_tag": points_by_tag,
        "active_sources": active_sources,
        "page_obj": page_obj,
    }

    return render(request, "points/my_points.html", context)
