"""Tests for the points app."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import PointSource, PointTransaction, Tag
from .services import InsufficientPointsError, grant_points, spend_points


class TagModelTests(TestCase):
    """Test cases for Tag model."""

    def test_tag_str(self):
        """Test string representation of Tag."""
        tag = Tag.objects.create(name="test-tag", description="Test description")

        assert str(tag) == "test-tag"

    def test_tag_unique_name(self):
        """Test that tag names must be unique."""
        Tag.objects.create(name="unique-tag")

        with pytest.raises(IntegrityError):
            Tag.objects.create(name="unique-tag")


class PointSourceModelTests(TestCase):
    """Test cases for PointSource model."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.tag = Tag.objects.create(name="test-tag")

    def test_point_source_creation(self):
        """Test creating a point source."""
        source = PointSource.objects.create(
            user_profile=self.user, initial_points=100, remaining_points=100
        )
        source.tags.add(self.tag)

        assert source.initial_points == 100
        assert source.remaining_points == 100
        assert source.tags.count() == 1

    def test_point_source_ordering(self):
        """Test that point sources are ordered by created_at."""
        source1 = PointSource.objects.create(
            user_profile=self.user, initial_points=100, remaining_points=100
        )
        source2 = PointSource.objects.create(
            user_profile=self.user, initial_points=50, remaining_points=50
        )

        sources = PointSource.objects.all()

        assert sources[0] == source1
        assert sources[1] == source2


class PointTransactionModelTests(TestCase):
    """Test cases for PointTransaction model."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )

    def test_transaction_creation(self):
        """Test creating a transaction."""
        transaction = PointTransaction.objects.create(
            user_profile=self.user,
            points=100,
            transaction_type=PointTransaction.TransactionType.EARN,
            description="Test earn",
        )

        assert transaction.points == 100
        assert transaction.transaction_type == "EARN"
        assert transaction.description == "Test earn"

    def test_transaction_ordering(self):
        """Test that transactions are ordered by created_at desc."""
        trans1 = PointTransaction.objects.create(
            user_profile=self.user,
            points=100,
            transaction_type=PointTransaction.TransactionType.EARN,
            description="First",
        )
        trans2 = PointTransaction.objects.create(
            user_profile=self.user,
            points=50,
            transaction_type=PointTransaction.TransactionType.EARN,
            description="Second",
        )

        transactions = PointTransaction.objects.all()

        assert transactions[0] == trans2
        assert transactions[1] == trans1


class GrantPointsTests(TestCase):
    """Test cases for grant_points service function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )

    def test_grant_points_success(self):
        """Test granting points creates source and transaction."""
        source = grant_points(
            user_profile=self.user,
            points=100,
            description="Test grant",
            tag_names=["tag1", "tag2"],
        )

        assert source.initial_points == 100
        assert source.remaining_points == 100
        assert source.tags.count() == 2

        assert self.user.point_transactions.count() == 1
        transaction = self.user.point_transactions.first()
        assert transaction.points == 100
        assert transaction.transaction_type == "EARN"

    def test_grant_points_invalid_amount(self):
        """Test granting negative or zero points raises ValueError."""
        with pytest.raises(ValueError, match="发放的积分必须是正整数"):
            grant_points(
                user_profile=self.user,
                points=0,
                description="Invalid",
                tag_names=["tag1"],
            )

        with pytest.raises(ValueError, match="发放的积分必须是正整数"):
            grant_points(
                user_profile=self.user,
                points=-10,
                description="Invalid",
                tag_names=["tag1"],
            )

    def test_grant_points_creates_tags(self):
        """Test granting points creates tags if they don't exist."""
        grant_points(
            user_profile=self.user,
            points=100,
            description="Test",
            tag_names=["new-tag"],
        )

        assert Tag.objects.filter(name="new-tag").exists()


class SpendPointsTests(TestCase):
    """Test cases for spend_points service function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )

    def test_spend_points_success(self):
        """Test spending points deducts from sources."""
        grant_points(
            user_profile=self.user,
            points=100,
            description="Initial",
            tag_names=["default"],
        )

        transaction = spend_points(
            user_profile=self.user, amount=30, description="Spend test"
        )

        assert transaction.points == -30
        assert transaction.transaction_type == "SPEND"
        assert self.user.total_points == 70

    def test_spend_points_insufficient(self):
        """Test spending more points than available raises error."""
        grant_points(
            user_profile=self.user,
            points=50,
            description="Initial",
            tag_names=["default"],
        )

        with pytest.raises(InsufficientPointsError):
            spend_points(user_profile=self.user, amount=100, description="Too much")

    def test_spend_points_invalid_amount(self):
        """Test spending negative or zero points raises ValueError."""
        with pytest.raises(ValueError, match="消费的积分必须是正整数"):
            spend_points(user_profile=self.user, amount=0, description="Invalid")

        with pytest.raises(ValueError, match="消费的积分必须是正整数"):
            spend_points(user_profile=self.user, amount=-10, description="Invalid")


class MyPointsViewTests(TestCase):
    """Test cases for my_points view."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.url = reverse("points:my_points")

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        response = self.client.get(self.url)

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_view_displays_points(self):
        """Test that view displays user's points correctly."""
        self.client.login(username="testuser", password="password123")

        grant_points(
            user_profile=self.user,
            points=100,
            description="Test",
            tag_names=["tag1"],
        )

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "total_points" in response.context
        assert response.context["total_points"] == 100
        assert "points_by_tag" in response.context
        assert len(response.context["points_by_tag"]) == 1

    def test_view_displays_transactions(self):
        """Test that view displays transaction history."""
        self.client.login(username="testuser", password="password123")

        grant_points(
            user_profile=self.user,
            points=100,
            description="Test grant",
            tag_names=["tag1"],
        )
        spend_points(user_profile=self.user, amount=30, description="Test spend")

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "page_obj" in response.context
        assert len(response.context["page_obj"]) == 2

    def test_view_pagination(self):
        """Test that view paginates transactions."""
        self.client.login(username="testuser", password="password123")

        # Create 25 transactions
        for i in range(25):
            grant_points(
                user_profile=self.user,
                points=10,
                description=f"Test {i}",
                tag_names=["tag1"],
            )

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert len(response.context["page_obj"]) == 20

        response = self.client.get(f"{self.url}?page=2")

        assert response.status_code == 200
        assert len(response.context["page_obj"]) == 5

    def test_view_with_no_points(self):
        """Test that view works when user has no points."""
        self.client.login(username="testuser", password="password123")

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert response.context["total_points"] == 0
        assert len(response.context["points_by_tag"]) == 0


class URLTests(TestCase):
    """Test URL configuration."""

    def test_my_points_url_resolves(self):
        """Test that my_points URL resolves correctly."""
        url = reverse("points:my_points")

        assert url == "/accounts/points/"
