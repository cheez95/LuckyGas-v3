"""
Simplified configuration for Lucky Gas
No overcomplicated settings - just what we need!
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings - simple and direct
    """
    # Application
    APP_NAME: str = "Lucky Gas Delivery System"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://luckygas:password@localhost/luckygas"
    )
    
    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "development-secret-key-change-in-production-must-be-32-chars"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:3000", 
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://vast-tributary-466619-m8.web.app",
        "https://luckygas-frontend-staging-2025.web.app",
        "https://luckygas-frontend-production-2025.web.app"
    ]
    
    # Admin user (for initial setup)
    FIRST_SUPERUSER: str = os.getenv("FIRST_SUPERUSER", "admin@luckygas.com")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "admin-password-2025")
    
    # API
    API_V1_STR: str = "/api/v1"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100
    
    # Cache
    CACHE_TTL_SECONDS: int = 300  # 5 minutes default
    
    # File upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".pdf"}
    
    # Timezone
    TIMEZONE: str = "Asia/Taipei"
    
    # External Services
    GOOGLE_MAPS_API_KEY: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY", None)
    
    class Config:
        env_file = ".env.local" if os.path.exists(".env.local") else ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env


# Create global settings instance
settings = Settings()