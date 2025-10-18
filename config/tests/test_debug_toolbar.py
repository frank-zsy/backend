"""Tests covering debug toolbar configuration branches."""

import importlib
import sys
import types
from contextlib import contextmanager
from unittest import mock

from django.test import SimpleTestCase, override_settings


class DebugToolbarConfigurationTests(SimpleTestCase):
    """Ensure settings and URL routing handle debug toolbar conditionally."""

    def setUp(self):
        """Reload settings and URL modules while preserving `sys.argv`."""
        self.original_sys_argv = list(sys.argv)
        self.settings_module = importlib.import_module("config.settings")
        self.urls_module = importlib.import_module("config.urls")

        with mock.patch.object(sys, "argv", self.original_sys_argv):
            self.settings_module = importlib.reload(self.settings_module)
        self.urls_module = importlib.reload(self.urls_module)

    def tearDown(self):
        """Restore reloaded modules after each test run."""
        with mock.patch.object(sys, "argv", self.original_sys_argv):
            self.settings_module = importlib.reload(self.settings_module)
        self.urls_module = importlib.reload(self.urls_module)

    @staticmethod
    def _fake_debug_toolbar_modules():
        package = types.ModuleType("debug_toolbar")
        toolbar = types.ModuleType("debug_toolbar.toolbar")
        sentinel_pattern = object()

        def debug_toolbar_urls():
            return [sentinel_pattern]

        toolbar.debug_toolbar_urls = debug_toolbar_urls
        package.toolbar = toolbar
        return package, toolbar, sentinel_pattern

    @contextmanager
    def _mock_debug_toolbar(self):
        package, toolbar, sentinel = self._fake_debug_toolbar_modules()
        original_modules = {
            name: sys.modules.get(name)
            for name in ("debug_toolbar", "debug_toolbar.toolbar")
        }

        for name in original_modules:
            sys.modules.pop(name, None)

        try:
            with mock.patch.dict(
                sys.modules,
                {
                    "debug_toolbar": package,
                    "debug_toolbar.toolbar": toolbar,
                },
                clear=False,
            ):
                yield sentinel
        finally:
            for name, module in original_modules.items():
                if module is not None:
                    sys.modules[name] = module
                else:
                    sys.modules.pop(name, None)

    def test_settings_appends_debug_toolbar_when_not_testing(self):
        """Ensure debug toolbar hooks load when not in testing mode."""
        with self._mock_debug_toolbar():
            with mock.patch.object(sys, "argv", ["manage.py"]):
                self.settings_module = importlib.reload(self.settings_module)

                self.assertIn("debug_toolbar", self.settings_module.INSTALLED_APPS)
                self.assertIn(
                    "debug_toolbar.middleware.DebugToolbarMiddleware",
                    self.settings_module.MIDDLEWARE,
                )
                self.assertIn("127.0.0.1", self.settings_module.INTERNAL_IPS)

        with mock.patch.object(sys, "argv", self.original_sys_argv):
            self.settings_module = importlib.reload(self.settings_module)

        self.assertNotIn("debug_toolbar", self.settings_module.INSTALLED_APPS)

    def test_urls_include_debug_toolbar_patterns_when_not_testing(self):
        """Confirm URLconf gains toolbar routes only outside testing."""
        original_patterns = list(self.urls_module.urlpatterns)

        with self._mock_debug_toolbar() as sentinel:
            with override_settings(TESTING=False):
                self.urls_module = importlib.reload(self.urls_module)

                self.assertIn(sentinel, self.urls_module.urlpatterns)

        self.urls_module = importlib.reload(self.urls_module)

        self.assertNotIn(sentinel, self.urls_module.urlpatterns)
        self.assertEqual(len(self.urls_module.urlpatterns), len(original_patterns))
