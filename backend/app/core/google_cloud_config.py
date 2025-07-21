from typing import Optional
from functools import lru_cache
from app.core.config import settings


class GoogleCloudConfig:
    """Google Cloud Platform configuration management"""
    
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = settings.GCP_LOCATION
        self.vertex_model_id = settings.VERTEX_MODEL_ID
        self.vertex_endpoint_id = settings.VERTEX_ENDPOINT_ID
        self.maps_api_key = settings.GOOGLE_MAPS_API_KEY
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.media_prefix = settings.GCS_MEDIA_PREFIX
        self.credentials_path = settings.GOOGLE_APPLICATION_CREDENTIALS
        
    def is_configured(self) -> bool:
        """Check if Google Cloud is properly configured"""
        return bool(self.project_id and self.maps_api_key)
    
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
        if not self.maps_api_key:
            missing.append("GOOGLE_MAPS_API_KEY")
        if not self.vertex_model_id:
            missing.append("VERTEX_MODEL_ID")
        return missing


@lru_cache()
def get_gcp_config() -> GoogleCloudConfig:
    """Get cached Google Cloud configuration"""
    return GoogleCloudConfig()