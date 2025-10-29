"""站内信 Admin 配置."""

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils.html import format_html

from .models import Message, UserMessage
from .services import send_message

User = get_user_model()


class MessageAdminForm(forms.ModelForm):
    """消息发送表单."""

    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=admin.widgets.FilteredSelectMultiple("用户", False),
        label="接收用户",
        help_text="广播消息时无需选择用户",
    )

    class Meta:
        """表单元数据."""

        model = Message
        fields = [
            "title",
            "content",
            "message_type",
            "sender",
            "is_broadcast",
            "recipients",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 10, "cols": 80}),
        }

    def clean(self):
        """验证表单数据."""
        cleaned_data = super().clean()
        is_broadcast = cleaned_data.get("is_broadcast")
        recipients = cleaned_data.get("recipients")

        if is_broadcast and recipients:
            msg = "广播消息不能同时指定接收用户"
            raise forms.ValidationError(msg)

        if not is_broadcast and not recipients:
            msg = "非广播消息必须指定接收用户"
            raise forms.ValidationError(msg)

        return cleaned_data


class UserMessageInline(admin.TabularInline):
    """用户消息内联显示."""

    model = UserMessage
    extra = 0
    can_delete = False
    fields = ["user", "is_read", "read_at", "is_deleted", "created_at"]
    readonly_fields = ["user", "read_at", "created_at"]

    def has_add_permission(self, request, obj=None):
        """禁止添加用户消息."""
        return False


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """消息管理."""

    form = MessageAdminForm
    list_display = [
        "title",
        "message_type_badge",
        "sender_display",
        "is_broadcast",
        "recipient_count",
        "unread_count",
        "created_at",
    ]
    list_filter = ["message_type", "is_broadcast", "created_at"]
    search_fields = ["title", "content", "sender__username"]
    readonly_fields = ["created_at", "updated_at", "recipient_count", "unread_count"]
    inlines = [UserMessageInline]
    date_hierarchy = "created_at"

    fieldsets = [
        (
            "基本信息",
            {
                "fields": ["title", "content", "message_type"],
            },
        ),
        (
            "发送设置",
            {
                "fields": ["sender", "is_broadcast", "recipients"],
            },
        ),
        (
            "统计信息",
            {
                "fields": [
                    "recipient_count",
                    "unread_count",
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_queryset(self, request):
        """获取查询集并添加统计注解."""
        qs = super().get_queryset(request)
        return qs.annotate(
            _recipient_count=Count("user_messages", distinct=True),
            _unread_count=Count(
                "user_messages", filter=Q(user_messages__is_read=False), distinct=True
            ),
        )

    @admin.display(description="消息类型", ordering="message_type")
    def message_type_badge(self, obj):
        """显示消息类型徽章."""
        colors = {
            "system": "info",
            "personal": "primary",
            "payment": "success",
            "shipping": "warning",
            "activity": "secondary",
            "announcement": "danger",
            "points": "success",
            "order": "info",
            "security": "danger",
            "withdrawal": "warning",
        }
        color = colors.get(obj.message_type, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>', color, obj.get_message_type_display()
        )

    @admin.display(description="发送者")
    def sender_display(self, obj):
        """显示发送者信息."""
        if obj.sender:
            return obj.sender.username
        return format_html('<span class="text-muted">系统</span>')

    @admin.display(description="接收人数", ordering="_recipient_count")
    def recipient_count(self, obj):
        """显示接收人数."""
        count = getattr(obj, "_recipient_count", obj.get_recipient_count())
        if obj.is_broadcast:
            return format_html('<span class="badge bg-primary">{} (广播)</span>', count)
        return count

    @admin.display(description="未读数量", ordering="_unread_count")
    def unread_count(self, obj):
        """显示未读数量."""
        count = getattr(
            obj, "_unread_count", obj.user_messages.filter(is_read=False).count()
        )
        if count > 0:
            return format_html('<span class="badge bg-warning">{}</span>', count)
        return count

    def save_model(self, request, obj, form, change):
        """保存消息并发送给用户."""
        if not change:  # 仅在新建时发送
            recipients = form.cleaned_data.get("recipients", [])
            message = send_message(
                title=obj.title,
                content=obj.content,
                message_type=obj.message_type,
                sender=obj.sender,
                recipients=list(recipients) if recipients else None,
                is_broadcast=obj.is_broadcast,
            )
            # 替换 obj 为实际创建的消息对象
            obj.pk = message.pk
        else:
            super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        """消息发送后不允许修改."""
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """允许删除消息."""
        return request.user.is_superuser


@admin.register(UserMessage)
class UserMessageAdmin(admin.ModelAdmin):
    """用户消息管理."""

    list_display = [
        "user",
        "message_title",
        "message_type",
        "is_read_badge",
        "is_deleted_badge",
        "created_at",
    ]
    list_filter = ["is_read", "is_deleted", "message__message_type", "created_at"]
    search_fields = ["user__username", "message__title", "message__content"]
    readonly_fields = ["user", "message", "read_at", "created_at"]
    date_hierarchy = "created_at"

    fieldsets = [
        (
            "基本信息",
            {
                "fields": ["user", "message"],
            },
        ),
        (
            "状态",
            {
                "fields": ["is_read", "read_at", "is_deleted"],
            },
        ),
        (
            "时间信息",
            {
                "fields": ["created_at"],
            },
        ),
    ]

    actions = ["mark_as_read", "mark_as_unread", "soft_delete", "restore"]

    @admin.display(description="消息标题")
    def message_title(self, obj):
        """显示消息标题."""
        return obj.message.title

    @admin.display(description="消息类型")
    def message_type(self, obj):
        """显示消息类型."""
        return obj.message.get_message_type_display()

    @admin.display(description="已读", boolean=True)
    def is_read_badge(self, obj):
        """显示已读状态."""
        return obj.is_read

    @admin.display(description="已删除", boolean=True)
    def is_deleted_badge(self, obj):
        """显示已删除状态."""
        return obj.is_deleted

    @admin.action(description="标记为已读")
    def mark_as_read(self, request, queryset):
        """批量标记为已读."""
        count = 0
        for user_message in queryset.filter(is_read=False):
            user_message.mark_as_read()
            count += 1
        self.message_user(request, f"成功标记 {count} 条消息为已读")

    @admin.action(description="标记为未读")
    def mark_as_unread(self, request, queryset):
        """批量标记为未读."""
        count = 0
        for user_message in queryset.filter(is_read=True):
            user_message.mark_as_unread()
            count += 1
        self.message_user(request, f"成功标记 {count} 条消息为未读")

    @admin.action(description="软删除")
    def soft_delete(self, request, queryset):
        """批量软删除消息."""
        count = 0
        for user_message in queryset.filter(is_deleted=False):
            user_message.soft_delete()
            count += 1
        self.message_user(request, f"成功删除 {count} 条消息")

    @admin.action(description="恢复删除")
    def restore(self, request, queryset):
        """批量恢复已删除的消息."""
        count = queryset.filter(is_deleted=True).update(is_deleted=False)
        self.message_user(request, f"成功恢复 {count} 条消息")

    def has_add_permission(self, request):
        """不允许直接添加用户消息."""
        return False

    def has_change_permission(self, request, obj=None):
        """仅允许修改状态字段."""
        return True
