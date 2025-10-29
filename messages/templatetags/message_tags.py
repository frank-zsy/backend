"""消息模板标签."""

from django import template

from messages.services import get_unread_count

register = template.Library()


@register.simple_tag(takes_context=True)
def unread_message_count(context):
    """获取当前用户的未读消息数量."""
    request = context.get("request")
    if request and request.user.is_authenticated:
        return get_unread_count(request.user)
    return 0
