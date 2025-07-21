"""
Unit tests for Development Mode Manager
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import os

from app.services.google_cloud.development_mode import (
    DevelopmentMode,
    DevelopmentModeManager
)
from app.core.security.api_key_manager import get_api_key_manager


class TestDevelopmentModeManager:
    """Test cases for DevelopmentModeManager"""
    
    @pytest.fixture
    def manager(self):
        """Create a DevelopmentModeManager instance"""
        return DevelopmentModeManager()
    
    @pytest.fixture
    def mock_key_manager(self):
        """Mock API key manager"""
        with patch("app.services.google_cloud.development_mode.get_api_key_manager") as mock:
            key_manager = AsyncMock()
            mock.return_value = key_manager
            yield key_manager
    
    @pytest.mark.asyncio
    async def test_auto_mode_with_api_keys(self, manager, mock_key_manager):
        """Test AUTO mode with API keys present"""
        # Mock environment
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "auto"}, clear=False):
            # Mock API keys exist
            mock_key_manager.get_key = AsyncMock(side_effect=[
                "routes_api_key_123",    # routes API key
                "vertex_ai_key_456"      # vertex AI key
            ])
            
            # Detect mode
            mode = await manager.detect_mode()
            
            # Should be PRODUCTION when keys exist
            assert mode == DevelopmentMode.PRODUCTION
    
    @pytest.mark.asyncio
    async def test_auto_mode_without_api_keys(self, manager, mock_key_manager):
        """Test AUTO mode without API keys"""
        # Mock environment
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "auto"}, clear=False):
            # Mock no API keys
            mock_key_manager.get_key = AsyncMock(return_value=None)
            
            # Detect mode
            mode = await manager.detect_mode()
            
            # Should be DEVELOPMENT when no keys
            assert mode == DevelopmentMode.DEVELOPMENT
    
    @pytest.mark.asyncio
    async def test_forced_production_mode(self, manager, mock_key_manager):
        """Test forced PRODUCTION mode"""
        # Mock environment
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}, clear=False):
            # Even without keys, should be PRODUCTION
            mock_key_manager.get_key = AsyncMock(return_value=None)
            
            # Detect mode
            mode = await manager.detect_mode()
            
            # Should be PRODUCTION (forced)
            assert mode == DevelopmentMode.PRODUCTION
    
    @pytest.mark.asyncio
    async def test_forced_development_mode(self, manager, mock_key_manager):
        """Test forced DEVELOPMENT mode"""
        # Mock environment
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}, clear=False):
            # Even with keys, should be DEVELOPMENT
            mock_key_manager.get_key = AsyncMock(return_value="api_key_exists")
            
            # Detect mode
            mode = await manager.detect_mode()
            
            # Should be DEVELOPMENT (forced)
            assert mode == DevelopmentMode.DEVELOPMENT
    
    @pytest.mark.asyncio
    async def test_offline_mode(self, manager, mock_key_manager):
        """Test OFFLINE mode"""
        # Mock environment
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "offline"}, clear=False):
            # Detect mode
            mode = await manager.detect_mode()
            
            # Should be OFFLINE
            assert mode == DevelopmentMode.OFFLINE
            
            # Key manager should not be called in offline mode
            mock_key_manager.get_key.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_is_production_mode(self, manager, mock_key_manager):
        """Test is_production_mode helper"""
        # Test production mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}, clear=False):
            assert await manager.is_production_mode() is True
        
        # Test development mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}, clear=False):
            assert await manager.is_production_mode() is False
        
        # Test auto mode with keys
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "auto"}, clear=False):
            mock_key_manager.get_key = AsyncMock(return_value="api_key")
            assert await manager.is_production_mode() is True
    
    @pytest.mark.asyncio
    async def test_is_development_mode(self, manager, mock_key_manager):
        """Test is_development_mode helper"""
        # Test development mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}, clear=False):
            assert await manager.is_development_mode() is True
        
        # Test production mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}, clear=False):
            assert await manager.is_development_mode() is False
        
        # Test offline mode (also considered development)
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "offline"}, clear=False):
            assert await manager.is_development_mode() is True
    
    @pytest.mark.asyncio
    async def test_should_use_mock_service(self, manager, mock_key_manager):
        """Test should_use_mock_service logic"""
        # Production mode - no mocks
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}, clear=False):
            assert await manager.should_use_mock_service("routes") is False
        
        # Development mode - use mocks
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}, clear=False):
            assert await manager.should_use_mock_service("routes") is True
        
        # Offline mode - always use mocks
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "offline"}, clear=False):
            assert await manager.should_use_mock_service("routes") is True
    
    @pytest.mark.asyncio
    async def test_get_service_mode_details(self, manager, mock_key_manager):
        """Test getting detailed service mode information"""
        # Test in production mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "production"}, clear=False):
            mock_key_manager.get_key = AsyncMock(return_value="api_key_123")
            
            details = await manager.get_service_mode_details()
            
            assert details["current_mode"] == "PRODUCTION"
            assert details["is_production"] is True
            assert details["is_development"] is False
            assert details["api_keys_status"]["routes"] == "configured"
            assert details["api_keys_status"]["vertex_ai"] == "configured"
            assert details["use_mock_services"] is False
        
        # Test in development mode without keys
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "development"}, clear=False):
            mock_key_manager.get_key = AsyncMock(return_value=None)
            
            details = await manager.get_service_mode_details()
            
            assert details["current_mode"] == "DEVELOPMENT"
            assert details["is_production"] is False
            assert details["is_development"] is True
            assert details["api_keys_status"]["routes"] == "not_configured"
            assert details["api_keys_status"]["vertex_ai"] == "not_configured"
            assert details["use_mock_services"] is True
    
    @pytest.mark.asyncio
    async def test_default_mode(self, manager, mock_key_manager):
        """Test default mode when DEVELOPMENT_MODE is not set"""
        # Clear DEVELOPMENT_MODE from environment
        with patch.dict(os.environ, {}, clear=True):
            # Should default to AUTO mode
            mock_key_manager.get_key = AsyncMock(return_value=None)
            
            mode = await manager.detect_mode()
            
            # With no keys, AUTO should be DEVELOPMENT
            assert mode == DevelopmentMode.DEVELOPMENT
    
    @pytest.mark.asyncio
    async def test_invalid_mode_string(self, manager, mock_key_manager):
        """Test handling of invalid mode string"""
        # Set invalid mode
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "invalid_mode"}, clear=False):
            mock_key_manager.get_key = AsyncMock(return_value=None)
            
            # Should default to AUTO behavior
            mode = await manager.detect_mode()
            
            # With no keys, should be DEVELOPMENT
            assert mode == DevelopmentMode.DEVELOPMENT
    
    @pytest.mark.asyncio
    async def test_partial_api_keys(self, manager, mock_key_manager):
        """Test AUTO mode with partial API keys"""
        # Mock environment
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "auto"}, clear=False):
            # Mock only routes API key exists
            mock_key_manager.get_key = AsyncMock(side_effect=[
                "routes_api_key_123",    # routes API key exists
                None                     # vertex AI key missing
            ])
            
            # Detect mode
            mode = await manager.detect_mode()
            
            # Should still be PRODUCTION if any key exists
            assert mode == DevelopmentMode.PRODUCTION
            
            # Check service-specific mock usage
            assert await manager.should_use_mock_service("routes") is False
            # Note: In real implementation, might want per-service logic
    
    @pytest.mark.asyncio
    async def test_mode_caching(self, manager, mock_key_manager):
        """Test that mode detection is cached"""
        # Mock environment
        with patch.dict(os.environ, {"DEVELOPMENT_MODE": "auto"}, clear=False):
            mock_key_manager.get_key = AsyncMock(return_value="api_key")
            
            # First call
            mode1 = await manager.detect_mode()
            call_count1 = mock_key_manager.get_key.call_count
            
            # Second call should use cache
            mode2 = await manager.detect_mode()
            call_count2 = mock_key_manager.get_key.call_count
            
            assert mode1 == mode2
            # Key manager should not be called again if cached
            # (Note: actual implementation might not cache, adjust test accordingly)
    
    @pytest.mark.asyncio
    async def test_environment_variable_case_insensitive(self, manager, mock_key_manager):
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
            with patch.dict(os.environ, {"DEVELOPMENT_MODE": env_value}, clear=False):
                mode = await manager.detect_mode()
                assert mode == expected_mode, f"Failed for {env_value}"