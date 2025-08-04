"""
Unit tests for Development Mode Manager
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.google_cloud.development_mode import (
    DevelopmentMode,
    DevelopmentModeManager,
)


class TestDevelopmentModeManager:
    """Test cases for DevelopmentModeManager"""

    # Don't create fixture - we need to test initialization with different env vars

    @pytest.fixture
    def reset_env(self):
        """Reset environment variables after test"""
        original_env = os.environ.copy()
        yield
        os.environ.clear()
        os.environ.update(original_env)

    def test_auto_mode_with_api_keys(self, reset_env):
        """Test AUTO mode with API keys present"""
        # Mock environment
        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_MODE": "auto",
                "GOOGLE_API_KEY": "test_key_123",
                "TESTING": "false",
            },
            clear=False,
        ):
            # Create manager - mode is determined on init
            manager = DevelopmentModeManager()

            # Should be PRODUCTION when keys exist
            assert manager.mode == DevelopmentMode.PRODUCTION

    def test_auto_mode_without_api_keys(self, reset_env):
        """Test AUTO mode without API keys"""
        # Mock environment - remove API keys
        with patch.dict(
            os.environ, {"GOOGLE_API_MODE": "auto", "TESTING": "false"}, clear=True
        ):
            # Create manager - mode is determined on init
            manager = DevelopmentModeManager()

            # Should be DEVELOPMENT when no keys
            assert manager.mode == DevelopmentMode.DEVELOPMENT

    def test_forced_production_mode(self, reset_env):
        """Test forced PRODUCTION mode"""
        # Mock environment
        with patch.dict(
            os.environ,
            {"GOOGLE_API_MODE": "production", "TESTING": "false"},
            clear=True,
        ):
            # Create manager - mode is determined on init
            manager = DevelopmentModeManager()

            # Should be PRODUCTION (forced)
            assert manager.mode == DevelopmentMode.PRODUCTION

    def test_forced_development_mode(self, reset_env):
        """Test forced DEVELOPMENT mode"""
        # Mock environment
        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_MODE": "development",
                "GOOGLE_API_KEY": "test_key_123",  # Even with keys
                "TESTING": "false",
            },
            clear=True,
        ):
            # Create manager - mode is determined on init
            manager = DevelopmentModeManager()

            # Should be DEVELOPMENT (forced)
            assert manager.mode == DevelopmentMode.DEVELOPMENT

    def test_offline_mode(self, reset_env):
        """Test OFFLINE mode"""
        # Mock environment
        with patch.dict(
            os.environ, {"GOOGLE_API_MODE": "offline", "TESTING": "false"}, clear=True
        ):
            # Create manager - mode is determined on init
            manager = DevelopmentModeManager()

            # Should be OFFLINE
            assert manager.mode == DevelopmentMode.OFFLINE

    def test_is_production_mode(self, reset_env):
        """Test is_production method"""
        # Test production mode
        with patch.dict(
            os.environ,
            {"GOOGLE_API_MODE": "production", "TESTING": "false"},
            clear=True,
        ):
            manager = DevelopmentModeManager()
            assert manager.is_production() is True

        # Test development mode
        with patch.dict(
            os.environ,
            {"GOOGLE_API_MODE": "development", "TESTING": "false"},
            clear=True,
        ):
            manager = DevelopmentModeManager()
            assert manager.is_production() is False

    def test_is_development_mode(self, reset_env):
        """Test is_development method"""
        # Test development mode
        with patch.dict(
            os.environ,
            {"GOOGLE_API_MODE": "development", "TESTING": "false"},
            clear=True,
        ):
            manager = DevelopmentModeManager()
            assert manager.is_development() is True

        # Test production mode
        with patch.dict(
            os.environ,
            {"GOOGLE_API_MODE": "production", "TESTING": "false"},
            clear=True,
        ):
            manager = DevelopmentModeManager()
            assert manager.is_development() is False

    def test_is_offline_mode(self, reset_env):
        """Test is_offline method"""
        # Test offline mode
        with patch.dict(
            os.environ, {"GOOGLE_API_MODE": "offline", "TESTING": "false"}, clear=True
        ):
            manager = DevelopmentModeManager()
            assert manager.is_offline() is True

        # Test non-offline modes
        with patch.dict(
            os.environ,
            {"GOOGLE_API_MODE": "production", "TESTING": "false"},
            clear=True,
        ):
            manager = DevelopmentModeManager()
            assert manager.is_offline() is False

    def test_get_service_info(self, reset_env):
        """Test getting service information"""
        # Test in production mode
        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_MODE": "production",
                "GOOGLE_API_KEY": "test_key",
                "TESTING": "false",
            },
            clear=True,
        ):
            manager = DevelopmentModeManager()
            info = manager.get_service_info()

            assert info["mode"] == "production"
            assert info["is_production"] is True
            assert info["is_development"] is False
            assert info["is_offline"] is False

    def test_default_mode(self, reset_env):
        """Test default mode when GOOGLE_API_MODE is not set"""
        # Clear GOOGLE_API_MODE from environment, but not in test mode
        with patch.dict(os.environ, {"TESTING": "false"}, clear=True):
            # Create manager - should default to AUTO mode
            manager = DevelopmentModeManager()

            # With no keys, AUTO should be DEVELOPMENT
            assert manager.mode == DevelopmentMode.DEVELOPMENT

    def test_invalid_mode_string(self, reset_env):
        """Test handling of invalid mode string"""
        # Set invalid mode
        with patch.dict(
            os.environ,
            {"GOOGLE_API_MODE": "invalid_mode", "TESTING": "false"},
            clear=True,
        ):
            # Create manager - should default to AUTO behavior
            manager = DevelopmentModeManager()

            # With no keys, should be DEVELOPMENT
            assert manager.mode == DevelopmentMode.DEVELOPMENT

    def test_partial_api_keys(self, reset_env):
        """Test AUTO mode with partial API keys"""
        # Mock environment with only Google API key
        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_MODE": "auto",
                "GOOGLE_API_KEY": "test_key",
                "TESTING": "false",
                # No GOOGLE_APPLICATION_CREDENTIALS
            },
            clear=True,
        ):
            # Create manager
            manager = DevelopmentModeManager()

            # Should still be PRODUCTION if any key exists
            assert manager.mode == DevelopmentMode.PRODUCTION

    def test_set_mode(self, reset_env):
        """Test setting mode dynamically"""
        with patch.dict(os.environ, {"TESTING": "false"}, clear=True):
            manager = DevelopmentModeManager()
            # Default should be development (no keys)
            assert manager.mode == DevelopmentMode.DEVELOPMENT

            # Set to production
            manager.set_mode(DevelopmentMode.PRODUCTION)
            assert manager.get_mode() == DevelopmentMode.PRODUCTION
            assert manager.is_production() is True

    def test_environment_variable_case_insensitive(self, reset_env):
        """Test that mode detection is case-insensitive"""
        test_cases = [
            ("PRODUCTION", DevelopmentMode.PRODUCTION),
            ("production", DevelopmentMode.PRODUCTION),
            ("Production", DevelopmentMode.PRODUCTION),
            ("DEVELOPMENT", DevelopmentMode.DEVELOPMENT),
            ("development", DevelopmentMode.DEVELOPMENT),
            ("OFFLINE", DevelopmentMode.OFFLINE),
            ("offline", DevelopmentMode.OFFLINE),
        ]

        for env_value, expected_mode in test_cases:
            with patch.dict(
                os.environ,
                {"GOOGLE_API_MODE": env_value, "TESTING": "false"},
                clear=True,
            ):
                manager = DevelopmentModeManager()
                assert manager.mode == expected_mode, f"Failed for {env_value}"
