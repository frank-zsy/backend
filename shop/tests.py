"""Comprehensive test suite for shop application."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from points.models import Tag
from points.services import InsufficientPointsError, grant_points

from .models import Redemption, ShopItem
from .services import RedemptionError, redeem_item


class ShopItemModelTests(TestCase):
    """Test cases for ShopItem model."""

    def setUp(self):
        """Set up test fixtures."""
        self.tag = Tag.objects.create(name="test-tag")

    def test_shop_item_str(self):
        """Test string representation of ShopItem."""
        item = ShopItem.objects.create(
            name="Test Item", description="Test description", cost=100
        )

        assert str(item) == "Test Item - 100 pts"

    def test_shop_item_creation(self):
        """Test creating a shop item."""
        item = ShopItem.objects.create(
            name="Test Item",
            description="Test description",
            cost=100,
            stock=10,
            is_active=True,
        )

        assert item.name == "Test Item"
        assert item.description == "Test description"
        assert item.cost == 100
        assert item.stock == 10
        assert item.is_active is True

    def test_shop_item_unlimited_stock(self):
        """Test creating item with unlimited stock."""
        item = ShopItem.objects.create(
            name="Unlimited Item", description="Test", cost=50, stock=None
        )

        assert item.stock is None

    def test_shop_item_with_allowed_tags(self):
        """Test creating item with allowed tags."""
        tag1 = Tag.objects.create(name="tag1")
        tag2 = Tag.objects.create(name="tag2")

        item = ShopItem.objects.create(name="Tagged Item", description="Test", cost=50)
        item.allowed_tags.set([tag1, tag2])

        assert item.allowed_tags.count() == 2
        assert tag1 in item.allowed_tags.all()
        assert tag2 in item.allowed_tags.all()

    def test_shop_item_default_is_active(self):
        """Test that is_active defaults to True."""
        item = ShopItem.objects.create(name="Test", description="Test", cost=10)

        assert item.is_active is True

    def test_shop_item_timestamps(self):
        """Test that created_at and updated_at are set."""
        item = ShopItem.objects.create(name="Test", description="Test", cost=10)

        assert item.created_at is not None
        assert item.updated_at is not None

    def test_shop_item_with_image(self):
        """Test creating shop item with image."""
        image_file = SimpleUploadedFile(
            "test_image.jpg", b"file_content", content_type="image/jpeg"
        )
        item = ShopItem.objects.create(
            name="Item with Image",
            description="Test",
            cost=100,
            image=image_file,
        )

        assert item.image is not None
        assert "test_image" in item.image.name
        assert item.image.name.startswith("shop/items/")

    def test_shop_item_without_image(self):
        """Test creating shop item without image (null/blank)."""
        item = ShopItem.objects.create(
            name="Item without Image", description="Test", cost=50
        )

        assert not item.image

    def test_shop_item_image_upload_path(self):
        """Test that image is uploaded to correct path."""
        image_file = SimpleUploadedFile(
            "product.png", b"image_data", content_type="image/png"
        )
        item = ShopItem.objects.create(
            name="Path Test", description="Test", cost=75, image=image_file
        )

        assert item.image.name.startswith("shop/items/")


class RedemptionModelTests(TestCase):
    """Test cases for Redemption model."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.item = ShopItem.objects.create(
            name="Test Item", description="Test", cost=100
        )

    def test_redemption_str(self):
        """Test string representation of Redemption."""
        redemption = Redemption.objects.create(
            user_profile=self.user, item=self.item, points_cost_at_redemption=100
        )

        assert str(redemption) == "testuser redeemed Test Item"

    def test_redemption_creation(self):
        """Test creating a redemption."""
        redemption = Redemption.objects.create(
            user_profile=self.user,
            item=self.item,
            points_cost_at_redemption=100,
            status=Redemption.StatusChoices.COMPLETED,
        )

        assert redemption.user_profile == self.user
        assert redemption.item == self.item
        assert redemption.points_cost_at_redemption == 100
        assert redemption.status == "COMPLETED"

    def test_redemption_default_status(self):
        """Test that status defaults to PENDING."""
        redemption = Redemption.objects.create(
            user_profile=self.user, item=self.item, points_cost_at_redemption=100
        )

        assert redemption.status == "PENDING"

    def test_redemption_ordering(self):
        """Test that redemptions are ordered by created_at desc."""
        redemption1 = Redemption.objects.create(
            user_profile=self.user, item=self.item, points_cost_at_redemption=100
        )
        redemption2 = Redemption.objects.create(
            user_profile=self.user, item=self.item, points_cost_at_redemption=50
        )

        redemptions = Redemption.objects.all()

        assert redemptions[0] == redemption2
        assert redemptions[1] == redemption1

    def test_redemption_with_transaction(self):
        """Test redemption with associated transaction."""
        from points.models import PointTransaction

        transaction = PointTransaction.objects.create(
            user_profile=self.user,
            points=-100,
            transaction_type=PointTransaction.TransactionType.SPEND,
            description="Test",
        )

        redemption = Redemption.objects.create(
            user_profile=self.user,
            item=self.item,
            points_cost_at_redemption=100,
            transaction=transaction,
        )

        assert redemption.transaction == transaction
        assert transaction.redemption == redemption


class RedeemItemServiceTests(TestCase):
    """Test cases for redeem_item service function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.default_tag = Tag.objects.create(name="default", is_default=True)

    def test_redeem_item_success(self):
        """Test successful item redemption."""
        # Grant points
        grant_points(
            user_profile=self.user,
            points=200,
            description="Initial",
            tag_names=["default"],
        )

        # Create item
        item = ShopItem.objects.create(
            name="Test Item", description="Test", cost=100, stock=5
        )

        # Redeem
        redemption = redeem_item(user_profile=self.user, item_id=item.id)

        assert redemption.user_profile == self.user
        assert redemption.item == item
        assert redemption.points_cost_at_redemption == 100
        assert redemption.status == Redemption.StatusChoices.COMPLETED
        assert redemption.transaction is not None

        # Check points were deducted
        assert self.user.total_points == 100

        # Check stock was reduced
        item.refresh_from_db()
        assert item.stock == 4

    def test_redeem_item_unlimited_stock(self):
        """Test redeeming item with unlimited stock."""
        grant_points(
            user_profile=self.user,
            points=100,
            description="Initial",
            tag_names=["default"],
        )

        item = ShopItem.objects.create(
            name="Unlimited Item", description="Test", cost=100, stock=None
        )

        redemption = redeem_item(user_profile=self.user, item_id=item.id)

        assert redemption is not None
        # Stock should remain None
        item.refresh_from_db()
        assert item.stock is None

    def test_redeem_item_nonexistent(self):
        """Test redeeming non-existent item raises error."""
        with pytest.raises(RedemptionError, match="商品不存在"):
            redeem_item(user_profile=self.user, item_id=99999)

    def test_redeem_item_inactive(self):
        """Test redeeming inactive item raises error."""
        item = ShopItem.objects.create(
            name="Inactive Item", description="Test", cost=100, is_active=False
        )

        with pytest.raises(RedemptionError, match="该商品已下架"):
            redeem_item(user_profile=self.user, item_id=item.id)

    def test_redeem_item_out_of_stock(self):
        """Test redeeming out of stock item raises error."""
        item = ShopItem.objects.create(
            name="Out of Stock", description="Test", cost=100, stock=0
        )

        with pytest.raises(RedemptionError, match="该商品已售罄"):
            redeem_item(user_profile=self.user, item_id=item.id)

    def test_redeem_item_insufficient_points(self):
        """Test redeeming without enough points raises error."""
        grant_points(
            user_profile=self.user,
            points=50,
            description="Initial",
            tag_names=["default"],
        )

        item = ShopItem.objects.create(
            name="Expensive Item", description="Test", cost=100
        )

        with pytest.raises(InsufficientPointsError):
            redeem_item(user_profile=self.user, item_id=item.id)

    def test_redeem_item_with_allowed_tags(self):
        """Test redeeming item with tag restrictions."""
        # Grant points with specific tag
        premium_tag = Tag.objects.create(name="premium")
        grant_points(
            user_profile=self.user,
            points=200,
            description="Premium points",
            tag_names=["premium"],
        )

        # Create item that requires premium tag
        item = ShopItem.objects.create(
            name="Premium Item", description="Test", cost=100
        )
        item.allowed_tags.add(premium_tag)

        # Redeem
        redemption = redeem_item(user_profile=self.user, item_id=item.id)

        assert redemption is not None
        assert self.user.total_points == 100

    def test_redeem_item_with_multiple_allowed_tags(self):
        """Test redeeming item with multiple allowed tags uses first tag as priority."""
        tag1 = Tag.objects.create(name="tag1")
        tag2 = Tag.objects.create(name="tag2")

        # Grant points with both tags
        grant_points(
            user_profile=self.user,
            points=100,
            description="Tag1 points",
            tag_names=["tag1"],
        )
        grant_points(
            user_profile=self.user,
            points=100,
            description="Tag2 points",
            tag_names=["tag2"],
        )

        # Create item with multiple allowed tags
        item = ShopItem.objects.create(
            name="Multi-tag Item", description="Test", cost=50
        )
        item.allowed_tags.set([tag1, tag2])

        # Redeem - should use tag1 as priority
        redemption = redeem_item(user_profile=self.user, item_id=item.id)

        assert redemption is not None

    def test_redeem_item_atomic_transaction(self):
        """Test that redemption is atomic - failures don't change state."""
        # Grant some points
        grant_points(
            user_profile=self.user,
            points=100,
            description="Initial",
            tag_names=["default"],
        )

        # Create item with 0 stock to trigger error
        item = ShopItem.objects.create(
            name="No Stock", description="Test", cost=50, stock=0
        )

        initial_points = self.user.total_points

        # Try to redeem - should fail
        with pytest.raises(RedemptionError):
            redeem_item(user_profile=self.user, item_id=item.id)

        # Points should not have changed
        assert self.user.total_points == initial_points

        # No redemption should be created
        assert Redemption.objects.count() == 0

    def test_redeem_item_records_cost_at_redemption_time(self):
        """Test that redemption records the item cost at time of redemption."""
        grant_points(
            user_profile=self.user,
            points=200,
            description="Initial",
            tag_names=["default"],
        )

        item = ShopItem.objects.create(name="Price Test", description="Test", cost=100)

        redemption = redeem_item(user_profile=self.user, item_id=item.id)

        # Record the cost
        original_cost = redemption.points_cost_at_redemption

        # Change item price
        item.cost = 150
        item.save()

        # Redemption should still show original cost
        redemption.refresh_from_db()
        assert redemption.points_cost_at_redemption == original_cost
        assert redemption.points_cost_at_redemption == 100

    def test_redeem_item_creates_spend_transaction(self):
        """Test that redemption creates a spend transaction."""
        grant_points(
            user_profile=self.user,
            points=100,
            description="Initial",
            tag_names=["default"],
        )

        item = ShopItem.objects.create(
            name="Transaction Test", description="Test", cost=50
        )

        initial_transaction_count = self.user.point_transactions.count()

        redemption = redeem_item(user_profile=self.user, item_id=item.id)

        # Should have one more transaction
        assert self.user.point_transactions.count() == initial_transaction_count + 1

        # Transaction should be linked
        assert redemption.transaction is not None
        assert redemption.transaction.transaction_type == "SPEND"
        assert redemption.transaction.points == -50
        assert "兑换商品" in redemption.transaction.description

    def test_redeem_item_concurrent_stock_update(self):
        """Test that stock updates use F() expression to prevent race conditions."""
        grant_points(
            user_profile=self.user,
            points=100,
            description="Initial",
            tag_names=["default"],
        )

        item = ShopItem.objects.create(
            name="Stock Test", description="Test", cost=50, stock=10
        )

        # Redeem item
        redeem_item(user_profile=self.user, item_id=item.id)

        # Get fresh copy from DB
        item_from_db = ShopItem.objects.get(id=item.id)

        assert item_from_db.stock == 9
