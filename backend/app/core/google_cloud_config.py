import asyncio
import logging
from functools import lru_cache
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleCloudConfig:
    """Google Cloud Platform configuration management"""

    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = settings.GCP_LOCATION
        self.vertex_model_id = settings.VERTEX_MODEL_ID
        self.vertex_endpoint_id = settings.VERTEX_ENDPOINT_ID
        # Don't store API key directly - use get_maps_api_key() method
        self._maps_api_key = None
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.media_prefix = settings.GCS_MEDIA_PREFIX
        self.credentials_path = settings.GOOGLE_APPLICATION_CREDENTIALS

    async def get_maps_api_key(self) -> str:
        """Get Maps API key using the secure API Key Manager"""
        if self._maps_api_key is None:
            try:
                from app.core.api_key_manager import get_api_key_manager

                api_key_manager = await get_api_key_manager()
                self._maps_api_key = await api_key_manager.get_key(
                    "GOOGLE_MAPS_API_KEY"
                )
                if not self._maps_api_key:
                    # Fallback to settings if not in secure storage yet
                    self._maps_api_key = settings.GOOGLE_MAPS_API_KEY
                    if self._maps_api_key:
                        # Store it securely for next time
                        await api_key_manager.set_key(
                            "GOOGLE_MAPS_API_KEY", self._maps_api_key
                        )
                        logger.info("Migrated Google Maps API key to secure storage")
            except Exception as e:
                logger.error(f"Error accessing API Key Manager: {e}")
                # Fallback to settings
                self._maps_api_key = settings.GOOGLE_MAPS_API_KEY
        return self._maps_api_key

    @property
    def maps_api_key(self) -> str:
        """Legacy property - logs warning to use async method"""
        logger.warning(
            "Direct access to maps_api_key is deprecated. Use await get_maps_api_key() instead"
        )
        return settings.GOOGLE_MAPS_API_KEY

    def is_configured(self) -> bool:
        """Check if Google Cloud is properly configured"""
        # Check project_id and if API key exists in settings (not retrieving it)
        return bool(
            self.project_id and (self._maps_api_key or settings.GOOGLE_MAPS_API_KEY)
        )

    def is_vertex_ai_configured(self) -> bool:
        """Check if Vertex AI is configured"""
        return bool(self.project_id and self.vertex_model_id)

    def is_storage_configured(self) -> bool:
        """Check if Cloud Storage is configured"""
        return bool(self.project_id and self.bucket_name)

    def get_missing_configs(self) -> list[str]:
        """Get list of missing configurations"""
        missing = []
        if not self.project_id:
            missing.append("GCP_PROJECT_ID")
        if not (self._maps_api_key or settings.GOOGLE_MAPS_API_KEY):
            missing.append("GOOGLE_MAPS_API_KEY")
        if not self.vertex_model_id:
            missing.append("VERTEX_MODEL_ID")
        return missing


@lru_cache()
def get_gcp_config() -> GoogleCloudConfig:
    """Get cached Google Cloud configuration"""
    return GoogleCloudConfig()
