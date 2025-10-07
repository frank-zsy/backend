"""Management command to promote a user to admin."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Set an existing user as an administrator."""

    help = (
        "Promote an existing user to admin by UID or username. "
        "At least one identifier must be provided."
    )

    def add_arguments(self, parser):
        """Register command arguments."""
        parser.add_argument(
            "--uid",
            type=int,
            help="Numeric primary key of the user to promote.",
        )
        parser.add_argument(
            "--username",
            type=str,
            help="Username of the user to promote.",
        )

    def handle(self, *args, **options):
        """Execute the command promoting the user."""
        uid = options.get("uid")
        username = options.get("username")

        user = self._get_user(uid=uid, username=username)

        if user.is_staff and user.is_superuser:
            self.stdout.write(self.style.WARNING("User is already an admin."))
            return

        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])

        self.stdout.write(
            self.style.SUCCESS(f"User '{user.username}' promoted to admin.")
        )

    def _get_user(self, *, uid=None, username=None):
        """Fetch the user using UID or username."""
        if not uid and not username:
            message = "Provide either --uid or --username."
            raise CommandError(message)

        if uid and username:
            message = "Provide only one of --uid or --username."
            raise CommandError(message)

        user_model = get_user_model()

        lookup = {"pk": uid} if uid else {"username": username}

        try:
            return user_model.objects.get(**lookup)
        except user_model.DoesNotExist as exc:
            identifier = f"uid={uid}" if uid else f"username='{username}'"
            message = f"User with {identifier} does not exist."
            raise CommandError(message) from exc
