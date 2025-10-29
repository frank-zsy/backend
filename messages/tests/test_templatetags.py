"""消息模板标签测试."""

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from messages.models import Message, UserMessage

User = get_user_model()


class MessageTagsTests(TestCase):
    """消息模板标签测试."""

    def setUp(self):
        """设置测试数据."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )
        self.factory = RequestFactory()

        # 创建消息
        for i in range(3):
            message = Message.objects.create(
                title=f"消息{i}",
                content=f"内容{i}",
                message_type=Message.MessageType.SYSTEM,
            )
            UserMessage.objects.create(user=self.user, message=message)

    def test_unread_message_count_authenticated(self):
        """测试已认证用户的未读消息数量."""
        request = self.factory.get("/")
        request.user = self.user

        template = Template("{% load message_tags %}{% unread_message_count %}")
        context = Context({"request": request})
        rendered = template.render(context)

        self.assertEqual(rendered.strip(), "3")

    def test_unread_message_count_unauthenticated(self):
        """测试未认证用户的未读消息数量."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/")
        request.user = AnonymousUser()

        template = Template("{% load message_tags %}{% unread_message_count %}")
        context = Context({"request": request})
        rendered = template.render(context)

        self.assertEqual(rendered.strip(), "0")

    def test_unread_message_count_after_reading(self):
        """测试阅读后的未读消息数量."""
        # 标记一条为已读
        um = UserMessage.objects.filter(user=self.user).first()
        um.mark_as_read()

        request = self.factory.get("/")
        request.user = self.user

        template = Template("{% load message_tags %}{% unread_message_count %}")
        context = Context({"request": request})
        rendered = template.render(context)

        self.assertEqual(rendered.strip(), "2")

    def test_unread_message_count_no_messages(self):
        """测试没有消息时的未读数量."""
        user2 = User.objects.create_user(username="user2", email="user2@example.com")

        request = self.factory.get("/")
        request.user = user2

        template = Template("{% load message_tags %}{% unread_message_count %}")
        context = Context({"request": request})
        rendered = template.render(context)

        self.assertEqual(rendered.strip(), "0")

    def test_unread_message_count_as_variable(self):
        """测试将未读数量存储为变量."""
        request = self.factory.get("/")
        request.user = self.user

        template = Template(
            "{% load message_tags %}{% unread_message_count as count %}You have {{ count }} unread messages"
        )
        context = Context({"request": request})
        rendered = template.render(context)

        self.assertIn("You have 3 unread messages", rendered)
