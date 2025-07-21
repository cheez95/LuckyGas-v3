from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Lucky Gas Delivery Management System"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT_ENABLED: bool = True
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "luckygas"
    POSTGRES_PASSWORD: str = "luckygas123"
    POSTGRES_DB: str = "luckygas"
    DATABASE_URL: str = ""
    
    @field_validator("DATABASE_URL", mode="after")
    def assemble_db_connection(cls, v: str, values) -> str:
        if v:
            return v
        return f"postgresql+asyncpg://{values.data.get('POSTGRES_USER')}:{values.data.get('POSTGRES_PASSWORD')}@{values.data.get('POSTGRES_SERVER')}:5433/{values.data.get('POSTGRES_DB')}"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS - Updated configuration
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if not v:
                return []
            if v.startswith("["):
                import json
                return json.loads(v)
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []
    
    # Default CORS origins for development
    DEFAULT_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:5174",  # Vite alternative port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]
    
    def get_all_cors_origins(self) -> List[str]:
        """Get all CORS origins including defaults"""
        all_origins = self.DEFAULT_CORS_ORIGINS.copy()
        if self.BACKEND_CORS_ORIGINS:
            all_origins.extend(self.BACKEND_CORS_ORIGINS)
        return list(set(all_origins))  # Remove duplicates
    
    # Google Cloud
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "asia-east1"  # Taiwan region
    VERTEX_MODEL_ID: str = ""
    VERTEX_ENDPOINT_ID: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    
    # Storage
    GCS_BUCKET_NAME: str = "lucky-gas-storage"
    GCS_MEDIA_PREFIX: str = "delivery-photos"
    
    # Service Account (optional)
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    
    # Business Logic
    DEPOT_LAT: float = 25.0330  # Taipei
    DEPOT_LNG: float = 121.5654
    DRIVER_COST_PER_HOUR: float = 500.0  # TWD
    
    # Timezone
    TIMEZONE: str = "Asia/Taipei"
    
    # Admin User
    FIRST_SUPERUSER: str = "admin@luckygas.tw"
    FIRST_SUPERUSER_PASSWORD: str = "admin123"


settings = Settings()