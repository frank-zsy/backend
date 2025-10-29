"""消息视图."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .models import Message, UserMessage
from .services import (
    delete_messages,
    get_message_stats,
    get_user_messages,
    mark_as_read,
    mark_as_unread,
)


@login_required
def message_list(request):
    """消息列表视图."""
    # 获取过滤参数
    message_type = request.GET.get("type")
    status = request.GET.get("status")  # all, unread, read

    # 获取用户消息
    messages = get_user_messages(request.user, include_deleted=False)

    # 按类型过滤
    if message_type:
        messages = messages.filter(message__message_type=message_type)

    # 按状态过滤
    if status == "unread":
        messages = messages.filter(is_read=False)
    elif status == "read":
        messages = messages.filter(is_read=True)

    # 分页
    paginator = Paginator(messages, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 获取统计信息
    stats = get_message_stats(request.user)

    # 获取消息类型列表
    message_types = Message.MessageType.choices

    context = {
        "page_obj": page_obj,
        "stats": stats,
        "message_types": message_types,
        "current_type": message_type,
        "current_status": status or "all",
    }

    return render(request, "messages/message_list.html", context)


@login_required
def message_detail(request, pk):
    """消息详情视图."""
    user_message = get_object_or_404(
        UserMessage.objects.select_related("message", "message__sender"),
        message_id=pk,
        user=request.user,
        is_deleted=False,
    )

    # 自动标记为已读
    if not user_message.is_read:
        user_message.mark_as_read()

    context = {
        "user_message": user_message,
    }

    return render(request, "messages/message_detail.html", context)


@login_required
@require_POST
def mark_read(request):
    """标记消息为已读视图."""
    message_ids = request.POST.getlist("message_ids[]")

    if not message_ids:
        # 标记所有未读消息
        count = mark_as_read(request.user)
    else:
        # 标记指定消息
        count = mark_as_read(request.user, [int(mid) for mid in message_ids])

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True, "count": count})

    return redirect("messages:list")


@login_required
@require_POST
def mark_unread(request):
    """标记消息为未读视图."""
    message_ids = request.POST.getlist("message_ids[]")

    if not message_ids:
        return JsonResponse({"success": False, "error": "未指定消息"}, status=400)

    count = mark_as_unread(request.user, [int(mid) for mid in message_ids])

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True, "count": count})

    return redirect("messages:list")


@login_required
@require_POST
def delete_message(request):
    """删除消息 (软删除) 视图."""
    message_ids = request.POST.getlist("message_ids[]")

    if not message_ids:
        return JsonResponse({"success": False, "error": "未指定消息"}, status=400)

    count = delete_messages(request.user, [int(mid) for mid in message_ids])

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True, "count": count})

    return redirect("messages:list")


@login_required
@require_http_methods(["GET"])
def unread_count(request):
    """获取未读消息数量 (API) 视图."""
    message_type = request.GET.get("type")

    from .services import get_unread_count

    count = get_unread_count(request.user, message_type=message_type)

    return JsonResponse({"count": count})
