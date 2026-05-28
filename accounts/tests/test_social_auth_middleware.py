"""Tests for social-auth exception handling middleware."""

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.http import HttpRequest
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.middleware import EMAIL_CONFLICT_MESSAGE, SocialAuthExceptionMiddleware
from accounts.social_auth import (
    EMAIL_CONFLICT_ERROR_CODE,
    EmailConflictRequiresBinding,
    FrontendSocialCallbackNotConfigured,
    build_frontend_social_callback_url,
)


class SocialAuthExceptionMiddlewareTests(TestCase):
    """Verify known social-auth exceptions redirect to the right surface."""

    @staticmethod
    def _raise_email_conflict(backend, *args, **kwargs):
        """Raise the custom social-auth conflict exception."""
        raise EmailConflictRequiresBinding(backend)

    @override_settings(
        FRONTEND_APP_URL="https://frontend.example",
        FRONTEND_SOCIAL_CALLBACK_PATH="/auth/social/callback",
    )
    @patch("social_django.views.do_complete")
    def test_social_conflict_redirects_to_frontend_callback(
        self,
        do_complete_mock,
    ):
        """Social login conflicts should redirect to the SPA callback with error code."""
        do_complete_mock.side_effect = self._raise_email_conflict

        response = self.client.get(reverse("social:complete", args=["github"]))

        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlparse(response.url).query)
        self.assertEqual(query["provider"], ["github"])
        self.assertEqual(query["error"], [EMAIL_CONFLICT_ERROR_CODE])

    def test_middleware_falls_back_to_root_when_frontend_unconfigured(self):
        """Without FRONTEND_APP_URL the middleware should fall back to the SPA root."""
        middleware = SocialAuthExceptionMiddleware(lambda request: None)
        request = HttpRequest()
        exception = EmailConflictRequiresBinding(backend="github")
        request.backend = type("Backend", (), {"name": "github"})()

        with patch(
            "accounts.middleware.build_frontend_social_callback_url",
            side_effect=FrontendSocialCallbackNotConfigured,
        ):
            self.assertEqual(
                middleware.get_redirect_uri(request, exception),
                "/",
            )

    def test_middleware_direct_branches_for_fallbacks(self):
        """Direct middleware calls should cover custom and superclass fallback branches."""
        middleware = SocialAuthExceptionMiddleware(lambda request: None)
        request = HttpRequest()
        exception = EmailConflictRequiresBinding(backend="github")

        self.assertEqual(
            middleware.get_message(request, exception), EMAIL_CONFLICT_MESSAGE
        )

        generic_error = RuntimeError("generic")
        with patch.object(
            SocialAuthExceptionMiddleware.__mro__[1],
            "get_message",
            return_value="base message",
        ) as base_get_message:
            self.assertEqual(
                middleware.get_message(request, generic_error),
                "base message",
            )
        base_get_message.assert_called_once_with(request, generic_error)

        with patch.object(
            SocialAuthExceptionMiddleware.__mro__[1],
            "get_redirect_uri",
            return_value="/base/",
        ) as base_get_redirect:
            self.assertEqual(
                middleware.get_redirect_uri(request, generic_error),
                "/base/",
            )
        base_get_redirect.assert_called_once_with(request, generic_error)

    @override_settings(
        FRONTEND_APP_URL="https://frontend.example/",
        FRONTEND_SOCIAL_CALLBACK_PATH="/auth/social/callback",
    )
    def test_social_auth_helper_branches(self):
        """Social auth URL helpers should cover string and configured URL paths."""
        exception = EmailConflictRequiresBinding(backend="github")

        self.assertEqual(str(exception), EMAIL_CONFLICT_ERROR_CODE)
        self.assertEqual(
            build_frontend_social_callback_url("github", error="boom"),
            "https://frontend.example/auth/social/callback?provider=github&error=boom",
        )

    @override_settings(FRONTEND_APP_URL="")
    def test_frontend_callback_url_requires_frontend_app_url(self):
        """Missing frontend URL should raise a stable configuration error."""
        with self.assertRaises(FrontendSocialCallbackNotConfigured):
            build_frontend_social_callback_url("github")
