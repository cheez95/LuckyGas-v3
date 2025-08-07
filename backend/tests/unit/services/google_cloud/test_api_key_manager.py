"""
Unit tests for API Key Manager
"""

import os
from unittest.mock import Mock, patch

import pytest

from app.core.api_key_manager import (
    GCPSecretManager,
    LocalEncryptedKeyManager,
    get_api_key_manager,
)


class TestLocalEncryptedKeyManager:
    """Test cases for LocalEncryptedKeyManager"""

    @pytest.fixture
    def temp_master_key_path(self, tmp_path):
        """Create a temporary master key path"""
        master_key_path = tmp_path / "master.key"
        return str(master_key_path)

    @pytest.fixture
    def manager(self, temp_master_key_path, tmp_path):
        """Create a LocalEncryptedKeyManager instance with proper path mocking"""
        manager = LocalEncryptedKeyManager(master_key_path=temp_master_key_path)
        # Override the keys_file path after instantiation
        manager.keys_file = tmp_path / "encrypted_keys.json"
        return manager

    @pytest.mark.asyncio
    async def test_set_and_get_key(self, manager):
        """Test setting and getting an API key"""
        # Set a key
        success = await manager.set_key("test_api", "secret_key_123")
        assert success is True

        # Get the key
        retrieved_key = await manager.get_key("test_api")
        assert retrieved_key == "secret_key_123"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, manager):
        """Test getting a key that doesn't exist"""
        key = await manager.get_key("nonexistent")
        assert key is None

    @pytest.mark.asyncio
    async def test_update_existing_key(self, manager):
        """Test updating an existing key"""
        # Set initial key
        await manager.set_key("test_api", "initial_key")

        # Update the key
        success = await manager.set_key("test_api", "updated_key")
        assert success is True

        # Verify update
        retrieved_key = await manager.get_key("test_api")
        assert retrieved_key == "updated_key"

    @pytest.mark.asyncio
    async def test_delete_key(self, manager):
        """Test deleting a key"""
        # Set a key
        await manager.set_key("test_api", "secret_key")

        # Delete the key
        success = await manager.delete_key("test_api")
        assert success is True

        # Verify deletion
        key = await manager.get_key("test_api")
        assert key is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, manager):
        """Test deleting a key that doesn't exist"""
        success = await manager.delete_key("nonexistent")
        # LocalEncryptedKeyManager returns True for non - existent keys (idempotent delete)
        assert success is True

    @pytest.mark.asyncio
    async def test_list_keys(self, manager):
        """Test listing all key names"""
        # Set multiple keys
        await manager.set_key("api1", "key1")
        await manager.set_key("api2", "key2")
        await manager.set_key("api3", "key3")

        # List keys
        keys = await manager.list_keys()
        assert set(keys) == {"api1", "api2", "api3"}

    @pytest.mark.asyncio
    async def test_encryption_key_generation(self, manager):
        """Test that encryption key is properly generated"""
        assert manager.fernet is not None
        assert isinstance(manager.fernet._signing_key, bytes)
        assert isinstance(manager.fernet._encryption_key, bytes)

    @pytest.mark.asyncio
    async def test_file_persistence(self, tmp_path):
        """Test that keys persist across manager instances"""
        # Create a master key path
        master_key_path = tmp_path / "master.key"

        # Create first manager and set keys
        manager1 = LocalEncryptedKeyManager(master_key_path=str(master_key_path))
        manager1.keys_file = tmp_path / "encrypted_keys.json"
        await manager1.set_key("persistent_api", "persistent_key")

        # Create second manager with same paths
        manager2 = LocalEncryptedKeyManager(master_key_path=str(master_key_path))
        manager2.keys_file = tmp_path / "encrypted_keys.json"

        # Verify key persists
        key = await manager2.get_key("persistent_api")
        assert key == "persistent_key"

    @pytest.mark.asyncio
    async def test_concurrent_access(self, manager):
        """Test concurrent access to keys"""
        import asyncio

        async def set_key(name, value):
            await manager.set_key(name, value)

        async def get_key(name):
            return await manager.get_key(name)

        # Concurrent operations
        await asyncio.gather(
            set_key("concurrent1", "value1"),
            set_key("concurrent2", "value2"),
            set_key("concurrent3", "value3"),
        )

        # Verify all keys
        results = await asyncio.gather(
            get_key("concurrent1"), get_key("concurrent2"), get_key("concurrent3")
        )

        assert results == ["value1", "value2", "value3"]


class TestGCPSecretManager:
    """Test cases for GCPSecretManager"""

    @pytest.fixture
    def mock_secret_client(self):
        """Mock Google Secret Manager client"""
        with patch(
            "app.core.api_key_manager.secretmanager.SecretManagerServiceClient"
        ) as mock:
            yield mock

    @pytest.fixture
    def manager(self, mock_secret_client):
        """Create a GCPSecretManager instance"""
        # Configure the mock before creating the manager
        mock_client_instance = Mock()
        mock_secret_client.return_value = mock_client_instance

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test - project"}):
            return GCPSecretManager(project_id="test - project")

    @pytest.mark.asyncio
    async def test_get_key_success(self, manager, mock_secret_client):
        """Test successfully getting a key from GCP"""
        # Get the mock client instance that was created during manager initialization
        mock_client_instance = manager.client

        # Mock the client response
        mock_response = Mock()
        mock_response.payload.data = b"secret_value_123"
        mock_client_instance.access_secret_version.return_value = mock_response

        # Get the key
        key = await manager.get_key("test_api")

        # Verify
        assert key == "secret_value_123"
        mock_client_instance.access_secret_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_key_not_found(self, manager, mock_secret_client):
        """Test getting a key that doesn't exist in GCP"""
        # Get the mock client instance that was created during manager initialization
        mock_client_instance = manager.client

        # Mock client to raise exception
        mock_client_instance.access_secret_version.side_effect = Exception(
            "Secret not found"
        )

        # Get the key
        key = await manager.get_key("nonexistent")

        # Verify
        assert key is None

    @pytest.mark.asyncio
    async def test_set_key_create_new(self, manager, mock_secret_client):
        """Test creating a new secret in GCP"""
        # Get the mock client instance that was created during manager initialization
        mock_client_instance = manager.client

        # Mock client responses
        mock_client_instance.create_secret.return_value = Mock(
            name="projects / test - project / secrets / test_api"
        )
        mock_client_instance.add_secret_version.return_value = Mock()

        # Set the key
        success = await manager.set_key("test_api", "new_secret_value")

        # Verify
        assert success is True
        mock_client_instance.create_secret.assert_called_once()
        mock_client_instance.add_secret_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_key_update_existing(self, manager, mock_secret_client):
        """Test updating an existing secret in GCP"""
        # Get the mock client instance that was created during manager initialization
        mock_client_instance = manager.client

        # Mock client to indicate secret already exists
        mock_client_instance.create_secret.side_effect = Exception(
            "Secret already exists"
        )
        mock_client_instance.add_secret_version.return_value = Mock()

        # Set the key
        success = await manager.set_key("test_api", "updated_value")

        # Verify
        assert success is True
        mock_client_instance.add_secret_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_key(self, manager, mock_secret_client):
        """Test deleting a secret from GCP"""
        # Get the mock client instance that was created during manager initialization
        mock_client_instance = manager.client

        # Mock client response
        mock_client_instance.destroy_secret_version.return_value = None

        # Delete the key
        success = await manager.delete_key("test_api")

        # Verify
        assert success is True
        mock_client_instance.destroy_secret_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_keys(self, manager, mock_secret_client):
        """Test listing all secrets from GCP"""
        # Get the mock client instance that was created during manager initialization
        mock_client_instance = manager.client

        # Mock secrets
        mock_secret1 = Mock()
        mock_secret1.name = "projects / test - project / secrets / api - key - 1"
        mock_secret2 = Mock()
        mock_secret2.name = "projects / test - project / secrets / api - key - 2"
        mock_secret3 = Mock()
        mock_secret3.name = "projects / test - project / secrets / other - secret"

        # Mock client response
        mock_client_instance.list_secrets.return_value = [
            mock_secret1,
            mock_secret2,
            mock_secret3,
        ]

        # List keys
        keys = await manager.list_keys()

        # Verify - only api - key- prefixed secrets
        assert set(keys) == {"1", "2"}


class TestGetAPIKeyManager:
    """Test cases for get_api_key_manager factory function"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the singleton instance before each test"""

        app.core.api_key_manager._api_key_manager_instance = None
        yield
        # Reset after test as well for cleanup
        app.core.api_key_manager._api_key_manager_instance = None

    @pytest.mark.asyncio
    async def test_get_local_manager_by_default(self):
        """Test that local manager is returned by default"""
        with patch.dict(os.environ, {}, clear=True):
            manager = await get_api_key_manager()
            assert isinstance(manager, LocalEncryptedKeyManager)

    @pytest.mark.asyncio
    async def test_get_gcp_manager_when_configured(self):
        """Test that GCP manager is returned when GCP is configured"""
        # Create a mock settings object with GCP_PROJECT_ID attribute
        mock_settings = Mock()
        mock_settings.GCP_PROJECT_ID = "test - project"

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with patch("app.core.config.settings", mock_settings):
                with patch(
                    "app.core.api_key_manager.secretmanager.SecretManagerServiceClient"
                ):
                    manager = await get_api_key_manager()
                    assert isinstance(manager, GCPSecretManager)

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that the same manager instance is returned"""
        with patch.dict(os.environ, {}, clear=True):
            manager1 = await get_api_key_manager()
            manager2 = await get_api_key_manager()
            assert manager1 is manager2
