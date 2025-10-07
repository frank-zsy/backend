"""Tests for accounts management commands."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase


class SetAdminCommandTests(TestCase):
    """Test suite for the setadmin management command."""

    databases = {"default"}

    def setUp(self):
        """Create a baseline user for tests."""
        self.user = get_user_model().objects.create_user(
            username="regular",
            email="regular@example.com",
            password="password123",
            is_staff=False,
            is_superuser=False,
        )

    def test_promote_user_by_username(self):
        """Promote a user using their username."""
        output = StringIO()

        call_command("setadmin", username=self.user.username, stdout=output)

        self.user.refresh_from_db()

        assert self.user.is_staff is True
        assert self.user.is_superuser is True
        assert "promoted to admin" in output.getvalue().lower()

    def test_promote_user_by_uid(self):
        """Promote a user using their primary key."""
        output = StringIO()

        call_command("setadmin", uid=self.user.pk, stdout=output)

        self.user.refresh_from_db()

        assert self.user.is_staff is True
        assert self.user.is_superuser is True
        assert "promoted to admin" in output.getvalue().lower()

    def test_command_requires_identifier(self):
        """Command must receive exactly one identifier."""
        with self.assertRaisesMessage(
            CommandError, "Provide either --uid or --username."
        ):
            call_command("setadmin")

        with self.assertRaisesMessage(
            CommandError, "Provide only one of --uid or --username."
        ):
            call_command("setadmin", uid=self.user.pk, username=self.user.username)

    def test_missing_user_raises_error(self):
        """Command raises an error when the user does not exist."""
        with self.assertRaisesMessage(
            CommandError, "User with uid=999 does not exist."
        ):
            call_command("setadmin", uid=999)

        with self.assertRaisesMessage(
            CommandError,
            "User with username='ghost' does not exist.",
        ):
            call_command("setadmin", username="ghost")

    def test_already_admin_outputs_warning(self):
        """Warn when the user is already an admin."""
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])

        output = StringIO()

        call_command("setadmin", username=self.user.username, stdout=output)

        assert "already an admin" in output.getvalue().lower()
