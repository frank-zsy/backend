"""Tests for homepage user search view."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from points.models import PointSource


class HomepageUserSearchTests(TestCase):
    """Test suite for the homepage user search experience."""

    def setUp(self):
        """Create reusable users and related data."""
        self.User = get_user_model()
        self.search_url = reverse("homepage:search")

        self.alice = self.User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="pass1234",
            first_name="Alice",
            last_name="Wonder",
        )
        UserProfile.objects.create(
            user=self.alice,
            bio="Core contributor",
            company="OpenShare",
            location="上海",
        )
        PointSource.objects.create(
            user_profile=self.alice,
            initial_points=250,
            remaining_points=250,
        )

        self.bob = self.User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="pass1234",
            first_name="Bob",
            last_name="Builder",
        )
        UserProfile.objects.create(
            user=self.bob,
            bio="Community maintainer",
            company="自由职业者",
            location="北京",
        )
        PointSource.objects.create(
            user_profile=self.bob,
            initial_points=60,
            remaining_points=60,
        )

    def test_redirects_on_exact_username_match(self):
        """Exact matches should redirect to the public profile page."""
        response = self.client.get(self.search_url, {"q": "Alice"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("public_profile", args=["alice"]))

    def test_partial_search_returns_results_page(self):
        """Partial matches render the results template with data."""
        response = self.client.get(self.search_url, {"q": "example"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "homepage/search_results.html")
        self.assertIn("results", response.context)
        usernames = {item["username"] for item in response.context["results"]}
        self.assertIn("alice", usernames)
        self.assertIn("bob", usernames)
        self.assertContains(response, "search-results-data")

    def test_location_filter_limits_results(self):
        """Location filter narrows the result set to the selected city."""
        response = self.client.get(
            self.search_url,
            {"q": "example", "location": "上海"},
        )

        self.assertEqual(response.status_code, 200)
        results = response.context["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["username"], "alice")
        self.assertEqual(results[0]["location"], "上海")

    def test_company_filter_limits_results(self):
        """Company filter narrows the result set to the selected organisation."""
        response = self.client.get(
            self.search_url,
            {"q": "example", "company": "OpenShare"},
        )

        self.assertEqual(response.status_code, 200)
        results = response.context["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["username"], "alice")
        self.assertEqual(results[0]["company"], "OpenShare")

    def test_min_points_filter(self):
        """Minimum points filter keeps users above the threshold."""
        response = self.client.get(
            self.search_url,
            {"q": "example", "min_points": "100"},
        )

        results = response.context["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["username"], "alice")

    def test_invalid_min_points_shows_message(self):
        """Non-numeric points filter triggers a validation message."""
        response = self.client.get(
            self.search_url,
            {"q": "example", "min_points": "abc"},
            follow=True,
        )

        messages = list(response.context["messages"])
        self.assertTrue(
            any("最低积分需要是整数" in str(message) for message in messages)
        )

    def test_empty_query_redirects_home(self):
        """Empty queries should redirect back to the homepage."""
        response = self.client.get(self.search_url, {"q": ""})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("homepage:index"))

    def test_results_context_limits_total_matches(self):
        """Context contains metadata for the filter summary."""
        response = self.client.get(self.search_url, {"q": "example"})

        self.assertGreaterEqual(response.context["results_count"], 2)
        self.assertEqual(response.context["filters"]["sort"], "relevance")
