"""Helper utilities shared by the accounts API (legacy template views removed)."""

import secrets

from django.conf import settings
from django.utils import timezone
from social_django.models import UserSocialAuth

from messages import services as inbox_services
from messages.models import Message as InboxMessage
from shop.models import Redemption

from .models import AccountMergeRequest


def _build_asset_snapshot(user):
    """Gather key asset counts for auditing and messaging."""
    providers = list(
        UserSocialAuth.objects.filter(user=user).values_list("provider", flat=True)
    )
    return {
        "redemption_count": Redemption.objects.filter(user_profile=user).count(),
        "organization_count": user.organizations.count(),
        "social_providers": providers,
    }


def _generate_unique_token():
    """Generate a unique approval token for merge links."""
    while True:
        token = secrets.token_urlsafe(32)
        if not AccountMergeRequest.objects.filter(approve_token=token).exists():
            return token


def _frontend_merge_url(token, action=""):
    """Build a frontend SPA URL for the given merge-request token."""
    base = (settings.FRONTEND_APP_URL or "").rstrip("/")
    suffix = f"/{action}" if action else ""
    return f"{base}/account/merge/{token}{suffix}"


def _send_merge_request_message(merge_request, request):
    """Send inbox notification to the target user with action links."""
    source = merge_request.source_user
    target = merge_request.target_user

    review_url = _frontend_merge_url(merge_request.approve_token)
    agree_url = _frontend_merge_url(merge_request.approve_token, "agree")
    reject_url = _frontend_merge_url(merge_request.approve_token, "reject")

    snapshot = merge_request.asset_snapshot or {}
    providers = snapshot.get("social_providers") or []
    content_lines = [
        f"来自 **{source.username}** ({source.email or '未留邮箱'}) 的账号合并申请。",
        "",
        "资产快照：",
        f"- 兑换记录：{snapshot.get('redemption_count', 0)}",
        f"- 组织成员关系：{snapshot.get('organization_count', 0)}",
        f"- 社交绑定：{', '.join(providers) if providers else '无'}",
        "",
        f"有效期：{merge_request.expires_at:%Y-%m-%d %H:%M}",
        "",
        f"[同意合并]({agree_url})  |  [拒绝]({reject_url})",
        f"查看详情：{review_url}",
    ]

    message = inbox_services.send_message(
        title="账号合并申请",
        content="\n".join(content_lines),
        message_type=InboxMessage.MessageType.SECURITY,
        recipients=[target],
    )
    merge_request.message = message
    merge_request.save(update_fields=["message"])


def _notify_merge_result(merge_request, *, accepted, request, reason=None):
    """Send result notifications to both source and target users."""
    source = merge_request.source_user
    target = merge_request.target_user
    status_text = "合并已完成" if accepted else (reason or "合并已被拒绝")
    processed_at = merge_request.processed_at or timezone.now()
    content = "\n".join(
        [
            f"账号合并申请结果：{status_text}",
            "",
            f"源账号：{source.username} ({source.email or '未留邮箱'})",
            f"目标账号：{target.username} ({target.email or '未留邮箱'})",
            f"处理时间：{timezone.localtime(processed_at):%Y-%m-%d %H:%M}",
        ]
    )
    inbox_services.send_message(
        title="账号合并结果通知",
        content=content,
        message_type=InboxMessage.MessageType.SECURITY,
        recipients=[source, target],
    )


def _expire_request_if_needed(merge_request, actor, request):
    """Mark request expired and notify when token is stale."""
    if (
        merge_request.status != AccountMergeRequest.Status.PENDING
        or not merge_request.is_expired
    ):
        return False

    merge_request.status = AccountMergeRequest.Status.EXPIRED
    merge_request.processed_at = timezone.now()
    merge_request.processed_by = actor
    merge_request.save(update_fields=["status", "processed_at", "processed_by"])
    _notify_merge_result(
        merge_request,
        accepted=False,
        request=request,
        reason="申请已过期，未做任何变更",
    )
    return True
