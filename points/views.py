"""Views for the points app."""

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from points.forms import WithdrawalRequestForm
from points.models import PointSource, Tag, WithdrawalRequest
from points.services import (
    PointSourceNotWithdrawableError,
    WithdrawalAmountError,
    WithdrawalData,
    WithdrawalError,
    cancel_withdrawal,
    create_withdrawal_request,
)

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


@login_required
def withdrawal_create(request, point_source_id):
    """
    Create a withdrawal request for a specific point source.

    Args:
        request: HTTP request
        point_source_id: ID of the point source to withdraw from

    """
    # Get the point source and verify it belongs to the user
    point_source = get_object_or_404(PointSource, id=point_source_id, user=request.user)

    # Check if the point source is withdrawable
    if not point_source.is_withdrawable:
        messages.error(request, "该积分来源不支持提现。")
        return redirect("points:my_points")

    # Check if there are remaining points
    if point_source.remaining_points <= 0:
        messages.error(request, "该积分来源没有可提现的积分。")
        return redirect("points:my_points")

    if request.method == "POST":
        form = WithdrawalRequestForm(request.POST, point_source=point_source)
        if form.is_valid():
            try:
                withdrawal_data = WithdrawalData(
                    real_name=form.cleaned_data["real_name"],
                    id_number=form.cleaned_data["id_number"],
                    phone_number=form.cleaned_data["phone_number"],
                    bank_name=form.cleaned_data["bank_name"],
                    bank_account=form.cleaned_data["bank_account"],
                )
                withdrawal_request = create_withdrawal_request(
                    user=request.user,
                    point_source_id=point_source.id,
                    points=form.cleaned_data["points"],
                    withdrawal_data=withdrawal_data,
                )
                messages.success(
                    request,
                    f"提现申请已提交！申请编号: #{withdrawal_request.id}，请等待审核。",
                )
                return redirect("points:withdrawal_list")
            except (
                PointSource.DoesNotExist,
                PointSourceNotWithdrawableError,
                WithdrawalAmountError,
            ) as e:
                messages.error(request, str(e))
    else:
        form = WithdrawalRequestForm(point_source=point_source)

    context = {
        "form": form,
        "point_source": point_source,
    }

    return render(request, "points/withdrawal_create.html", context)


@login_required
def withdrawal_list(request):
    """
    Display user's withdrawal requests.

    Shows all withdrawal requests with their status.

    """
    # Get user's withdrawal requests with pagination
    withdrawals = request.user.withdrawal_requests.select_related(
        "point_source", "processed_by"
    ).order_by("-created_at")

    paginator = Paginator(withdrawals, 20)  # 20 requests per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }

    return render(request, "points/withdrawal_list.html", context)


@login_required
def withdrawal_detail(request, withdrawal_id):
    """
    Display details of a specific withdrawal request.

    Args:
        request: HTTP request
        withdrawal_id: ID of the withdrawal request

    """
    withdrawal = get_object_or_404(
        WithdrawalRequest.objects.select_related("point_source", "processed_by"),
        id=withdrawal_id,
        user=request.user,
    )

    context = {
        "withdrawal": withdrawal,
    }

    return render(request, "points/withdrawal_detail.html", context)


@login_required
def withdrawal_cancel(request, withdrawal_id):
    """
    Cancel a pending withdrawal request.

    Args:
        request: HTTP request
        withdrawal_id: ID of the withdrawal request

    """
    withdrawal = get_object_or_404(
        WithdrawalRequest, id=withdrawal_id, user=request.user
    )

    if request.method == "POST":
        try:
            cancel_withdrawal(withdrawal)
            messages.success(request, "提现申请已取消。")
            return redirect("points:withdrawal_list")
        except WithdrawalError as e:
            messages.error(request, str(e))
            return redirect("points:withdrawal_detail", withdrawal_id=withdrawal_id)

    # If not POST, redirect to detail page
    return redirect("points:withdrawal_detail", withdrawal_id=withdrawal_id)
