from typing import List
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
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
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
        return f"postgresql+psycopg2://{values.data.get('POSTGRES_USER')}:{values.data.get('POSTGRES_PASSWORD')}@{values.data.get('POSTGRES_SERVER')}/{values.data.get('POSTGRES_DB')}"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]
    
    # Google Cloud
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "asia-east1"  # Taiwan region
    VERTEX_MODEL_ID: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    
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