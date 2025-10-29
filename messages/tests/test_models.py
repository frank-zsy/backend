"""消息模型测试."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from messages.models import Message, UserMessage

User = get_user_model()


class MessageModelTests(TestCase):
    """消息模型测试."""

    def setUp(self):
        """设置测试数据."""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com"
        )

    def test_message_creation(self):
        """测试创建消息."""
        message = Message.objects.create(
            title="测试消息",
            content="这是一条测试消息",
            message_type=Message.MessageType.SYSTEM,
            is_broadcast=False,
        )

        self.assertEqual(message.title, "测试消息")
        self.assertEqual(message.content, "这是一条测试消息")
        self.assertEqual(message.message_type, Message.MessageType.SYSTEM)
        self.assertFalse(message.is_broadcast)
        self.assertIsNone(message.sender)
        self.assertIsNotNone(message.created_at)
        self.assertIsNotNone(message.updated_at)

    def test_message_with_sender(self):
        """测试创建带发送者的消息."""
        message = Message.objects.create(
            title="个人消息",
            content="这是一条个人消息",
            message_type=Message.MessageType.PERSONAL,
            sender=self.user1,
            is_broadcast=False,
        )

        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.message_type, Message.MessageType.PERSONAL)

    def test_message_str(self):
        """测试消息字符串表示."""
        message = Message.objects.create(
            title="测试消息", content="内容", message_type=Message.MessageType.SYSTEM
        )

        self.assertIn("系统消息", str(message))
        self.assertIn("测试消息", str(message))

    def test_message_get_recipient_count(self):
        """测试获取接收者数量."""
        message = Message.objects.create(
            title="测试", content="内容", message_type=Message.MessageType.SYSTEM
        )

        UserMessage.objects.create(user=self.user1, message=message)
        UserMessage.objects.create(user=self.user2, message=message)

        self.assertEqual(message.get_recipient_count(), 2)

    def test_broadcast_message(self):
        """测试广播消息."""
        message = Message.objects.create(
            title="广播消息",
            content="这是一条广播消息",
            message_type=Message.MessageType.ANNOUNCEMENT,
            is_broadcast=True,
        )

        self.assertTrue(message.is_broadcast)

    def test_message_types(self):
        """测试所有消息类型."""
        types = [
            Message.MessageType.SYSTEM,
            Message.MessageType.PERSONAL,
            Message.MessageType.PAYMENT,
            Message.MessageType.SHIPPING,
            Message.MessageType.ACTIVITY,
            Message.MessageType.ANNOUNCEMENT,
            Message.MessageType.POINTS,
            Message.MessageType.ORDER,
            Message.MessageType.SECURITY,
            Message.MessageType.WITHDRAWAL,
        ]

        for msg_type in types:
            message = Message.objects.create(
                title=f"测试{msg_type}", content="内容", message_type=msg_type
            )
            self.assertEqual(message.message_type, msg_type)


class UserMessageModelTests(TestCase):
    """用户消息模型测试."""

    def setUp(self):
        """设置测试数据."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )
        self.message = Message.objects.create(
            title="测试消息", content="内容", message_type=Message.MessageType.SYSTEM
        )

    def test_user_message_creation(self):
        """测试创建用户消息."""
        user_message = UserMessage.objects.create(user=self.user, message=self.message)

        self.assertEqual(user_message.user, self.user)
        self.assertEqual(user_message.message, self.message)
        self.assertFalse(user_message.is_read)
        self.assertIsNone(user_message.read_at)
        self.assertFalse(user_message.is_deleted)
        self.assertIsNotNone(user_message.created_at)

    def test_user_message_str(self):
        """测试用户消息字符串表示."""
        user_message = UserMessage.objects.create(user=self.user, message=self.message)

        self.assertIn(self.user.username, str(user_message))
        self.assertIn(self.message.title, str(user_message))

    def test_mark_as_read(self):
        """测试标记为已读."""
        user_message = UserMessage.objects.create(user=self.user, message=self.message)

        self.assertFalse(user_message.is_read)
        self.assertIsNone(user_message.read_at)

        user_message.mark_as_read()

        self.assertTrue(user_message.is_read)
        self.assertIsNotNone(user_message.read_at)

    def test_mark_as_read_idempotent(self):
        """测试重复标记为已读."""
        user_message = UserMessage.objects.create(user=self.user, message=self.message)
        user_message.mark_as_read()

        first_read_at = user_message.read_at

        user_message.mark_as_read()

        # 应该不会改变 read_at
        self.assertEqual(user_message.read_at, first_read_at)

    def test_mark_as_unread(self):
        """测试标记为未读."""
        user_message = UserMessage.objects.create(user=self.user, message=self.message)
        user_message.mark_as_read()

        self.assertTrue(user_message.is_read)

        user_message.mark_as_unread()

        self.assertFalse(user_message.is_read)
        self.assertIsNone(user_message.read_at)

    def test_mark_as_unread_idempotent(self):
        """测试重复标记为未读."""
        user_message = UserMessage.objects.create(user=self.user, message=self.message)

        user_message.mark_as_unread()

        self.assertFalse(user_message.is_read)

    def test_soft_delete(self):
        """测试软删除."""
        user_message = UserMessage.objects.create(user=self.user, message=self.message)

        self.assertFalse(user_message.is_deleted)

        user_message.soft_delete()

        self.assertTrue(user_message.is_deleted)

    def test_soft_delete_idempotent(self):
        """测试重复软删除."""
        user_message = UserMessage.objects.create(user=self.user, message=self.message)
        user_message.soft_delete()

        user_message.soft_delete()

        self.assertTrue(user_message.is_deleted)

    def test_unique_together_constraint(self):
        """测试唯一约束."""
        UserMessage.objects.create(user=self.user, message=self.message)

        # 尝试创建重复的用户消息应该失败
        with self.assertRaises(IntegrityError):
            UserMessage.objects.create(user=self.user, message=self.message)

    def test_multiple_users_same_message(self):
        """测试多个用户接收同一条消息."""
        user2 = User.objects.create_user(username="user2", email="user2@example.com")

        um1 = UserMessage.objects.create(user=self.user, message=self.message)
        um2 = UserMessage.objects.create(user=user2, message=self.message)

        self.assertEqual(um1.message, um2.message)
        self.assertNotEqual(um1.user, um2.user)

    def test_user_message_ordering(self):
        """测试用户消息排序."""
        message2 = Message.objects.create(
            title="消息2", content="内容2", message_type=Message.MessageType.SYSTEM
        )

        um1 = UserMessage.objects.create(user=self.user, message=self.message)
        um2 = UserMessage.objects.create(user=self.user, message=message2)

        messages = UserMessage.objects.filter(user=self.user)

        # 应该按创建时间倒序排列
        self.assertEqual(messages[0], um2)
        self.assertEqual(messages[1], um1)
