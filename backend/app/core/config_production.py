"""
Production configuration for Lucky Gas Simplified Backend
Optimized for Google Cloud Run deployment
"""
import os
from pydantic_settings import BaseSettings


class ProductionSettings(BaseSettings):
    """
    Production settings with strict security and proper CORS
    """
    # Application
    APP_NAME: str = "Lucky Gas Delivery System"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # Database - Must be set via environment variable
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Security - Must be set via environment variable
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    
    # CORS - Allow specific origins only
    BACKEND_CORS_ORIGINS: list = [
        "https://storage.googleapis.com",
        "https://luckygas-frontend-production.storage.googleapis.com",
        "https://luckygas-frontend-staging-2025.storage.googleapis.com",
        "https://app.luckygas.tw",
        "https://www.luckygas.tw",
        "https://luckygas.tw"
    ]
    
    # Admin user (for initial setup)
    FIRST_SUPERUSER: str = os.getenv("FIRST_SUPERUSER", "admin@luckygas.com")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "")
    
    # API
    API_V1_STR: str = "/api/v1"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100
    
    # Cache
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    
    # File upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".pdf"}
    
    # Timezone
    TIMEZONE: str = "Asia/Taipei"
    
    # Google Cloud Run specific
    PORT: int = int(os.getenv("PORT", "8080"))
    
    class Config:
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables

    def validate_production_config(self):
        """Validate required production settings"""
        errors = []
        
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL environment variable is required")
        
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be set and at least 32 characters long")
        
        if not self.FIRST_SUPERUSER_PASSWORD:
            errors.append("FIRST_SUPERUSER_PASSWORD environment variable is required")
        
        if errors:
            raise ValueError(f"Production configuration errors: {', '.join(errors)}")
        
        return True


# Create global settings instance
settings = ProductionSettings()

# Validate in production
if settings.ENVIRONMENT == "production":
    settings.validate_production_config()