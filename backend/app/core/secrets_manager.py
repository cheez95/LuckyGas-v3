"""
Google Secret Manager integration for secure secrets management.

This module provides a centralized way to manage secrets using Google Secret Manager,
with fallback to environment variables for local development.
"""

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional, Union

from google.api_core import exceptions as gcp_exceptions
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manages application secrets using Google Secret Manager with environment fallback."""

    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize the secrets manager.

        Args:
            project_id: GCP project ID. If not provided, attempts to get from environment.
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self._client: Optional[secretmanager.SecretManagerServiceClient] = None
        self._use_secret_manager = bool(
            self.project_id and os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )

        if self._use_secret_manager:
            try:
                self._client = secretmanager.SecretManagerServiceClient()
                logger.info(
                    f"Initialized Secret Manager for project: {self.project_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Secret Manager: {e}. Falling back to environment variables."
                )
                self._use_secret_manager = False
        else:
            logger.info(
                "Using environment variables for secrets (Secret Manager not configured)"
            )

    @lru_cache(maxsize=128)
    def get_secret(self, secret_id: str, version: str = "latest") -> Optional[str]:
        """
        Retrieve a secret value from Secret Manager or environment.

        Args:
            secret_id: The ID of the secret to retrieve
            version: The version of the secret (default: "latest")

        Returns:
            The secret value as a string, or None if not found
        """
        # First, try environment variable
        env_value = os.getenv(secret_id.upper())
        if env_value:
            logger.debug(f"Using environment variable for secret: {secret_id}")
            return env_value

        # If Secret Manager is available, try to fetch from there
        if self._use_secret_manager and self._client:
            try:
                name = (
                    f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
                )
                response = self._client.access_secret_version(request={"name": name})
                secret_value = response.payload.data.decode("UTF-8")
                logger.debug(f"Retrieved secret from Secret Manager: {secret_id}")
                return secret_value
            except gcp_exceptions.NotFound:
                logger.warning(f"Secret not found in Secret Manager: {secret_id}")
            except Exception as e:
                logger.error(f"Error accessing secret {secret_id}: {e}")

        return None

    def get_secret_json(
        self, secret_id: str, version: str = "latest"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a JSON secret and parse it.

        Args:
            secret_id: The ID of the secret to retrieve
            version: The version of the secret

        Returns:
            The parsed JSON as a dictionary, or None if not found or invalid
        """
        secret_value = self.get_secret(secret_id, version)
        if secret_value:
            try:
                return json.loads(secret_value)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON secret {secret_id}: {e}")
        return None

    def create_secret(self, secret_id: str, secret_value: Union[str, Dict]) -> bool:
        """
        Create a new secret in Secret Manager.

        Args:
            secret_id: The ID for the new secret
            secret_value: The secret value (string or dict to be JSON-encoded)

        Returns:
            True if successful, False otherwise
        """
        if not self._use_secret_manager or not self._client:
            logger.warning("Secret Manager not available for creating secrets")
            return False

        try:
            # Create the secret
            parent = f"projects/{self.project_id}"
            secret = self._client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )

            # Add the secret version
            if isinstance(secret_value, dict):
                secret_data = json.dumps(secret_value).encode("UTF-8")
            else:
                secret_data = str(secret_value).encode("UTF-8")

            self._client.add_secret_version(
                request={"parent": secret.name, "payload": {"data": secret_data}}
            )

            logger.info(f"Created secret: {secret_id}")
            return True

        except gcp_exceptions.AlreadyExists:
            logger.warning(f"Secret already exists: {secret_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to create secret {secret_id}: {e}")
            return False

    def update_secret(self, secret_id: str, secret_value: Union[str, Dict]) -> bool:
        """
        Update an existing secret by adding a new version.

        Args:
            secret_id: The ID of the secret to update
            secret_value: The new secret value

        Returns:
            True if successful, False otherwise
        """
        if not self._use_secret_manager or not self._client:
            logger.warning("Secret Manager not available for updating secrets")
            return False

        try:
            parent = f"projects/{self.project_id}/secrets/{secret_id}"

            if isinstance(secret_value, dict):
                secret_data = json.dumps(secret_value).encode("UTF-8")
            else:
                secret_data = str(secret_value).encode("UTF-8")

            self._client.add_secret_version(
                request={"parent": parent, "payload": {"data": secret_data}}
            )

            # Clear cache for this secret
            self.get_secret.cache_clear()

            logger.info(f"Updated secret: {secret_id}")
            return True

        except gcp_exceptions.NotFound:
            logger.error(f"Secret not found for update: {secret_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update secret {secret_id}: {e}")
            return False

    def list_secrets(self) -> list:
        """
        List all secrets in the project.

        Returns:
            List of secret IDs
        """
        if not self._use_secret_manager or not self._client:
            logger.warning("Secret Manager not available for listing secrets")
            return []

        try:
            parent = f"projects/{self.project_id}"
            secrets = []

            for secret in self._client.list_secrets(request={"parent": parent}):
                secret_id = secret.name.split("/")[-1]
                secrets.append(secret_id)

            return secrets

        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []

    def delete_secret(self, secret_id: str) -> bool:
        """
        Delete a secret from Secret Manager.

        Args:
            secret_id: The ID of the secret to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._use_secret_manager or not self._client:
            logger.warning("Secret Manager not available for deleting secrets")
            return False

        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}"
            self._client.delete_secret(request={"name": name})

            # Clear cache
            self.get_secret.cache_clear()

            logger.info(f"Deleted secret: {secret_id}")
            return True

        except gcp_exceptions.NotFound:
            logger.warning(f"Secret not found for deletion: {secret_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_id}: {e}")
            return False


# Global instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


# Convenience functions
def get_secret(secret_id: str, version: str = "latest") -> Optional[str]:
    """Get a secret value."""
    return get_secrets_manager().get_secret(secret_id, version)


def get_secret_json(
    secret_id: str, version: str = "latest"
) -> Optional[Dict[str, Any]]:
    """Get a JSON secret value."""
    return get_secrets_manager().get_secret_json(secret_id, version)


def create_secret(secret_id: str, secret_value: Union[str, Dict]) -> bool:
    """Create a new secret."""
    return get_secrets_manager().create_secret(secret_id, secret_value)


def update_secret(secret_id: str, secret_value: Union[str, Dict]) -> bool:
    """Update an existing secret."""
    return get_secrets_manager().update_secret(secret_id, secret_value)
