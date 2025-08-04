from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Lucky Gas Training API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8000
    
    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://training.luckygas.com.tw",
        "https://www.luckygas.com.tw"
    ]
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # AWS
    AWS_REGION: str = "ap-northeast-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "luckygas-training-content"
    CLOUDFRONT_DISTRIBUTION_ID: Optional[str] = None
    CLOUDFRONT_DOMAIN: Optional[str] = None
    
    # Moodle Integration
    MOODLE_URL: str = "https://moodle.luckygas.com.tw"
    MOODLE_TOKEN: Optional[str] = None
    MOODLE_SERVICE_NAME: str = "luckygas_integration"
    
    # Lucky Gas System Integration
    LUCKYGAS_API_URL: str = "https://api.luckygas.com.tw/v1"
    LUCKYGAS_API_KEY: Optional[str] = None
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "training@luckygas.com.tw"
    SMTP_FROM_NAME: str = "Lucky Gas Training"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENABLE_TELEMETRY: bool = True
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    
    # Practice Environment
    PRACTICE_ENV_IMAGE: str = "luckygas/practice-env:latest"
    PRACTICE_ENV_CPU_LIMIT: str = "1"
    PRACTICE_ENV_MEMORY_LIMIT: str = "1Gi"
    PRACTICE_ENV_TIMEOUT_MINUTES: int = 120
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [
        ".pdf", ".doc", ".docx", ".ppt", ".pptx",
        ".mp4", ".avi", ".mov", ".webm",
        ".jpg", ".jpeg", ".png", ".gif", ".svg"
    ]
    
    # Video Processing
    VIDEO_ENCODING_PRESET: str = "training-optimized"
    VIDEO_QUALITIES: List[str] = ["360p", "720p", "1080p"]
    VIDEO_MAX_DURATION_MINUTES: int = 60
    
    # Assessment
    ASSESSMENT_MAX_ATTEMPTS: int = 3
    ASSESSMENT_PASS_PERCENTAGE: int = 80
    CERTIFICATE_VALIDITY_DAYS: int = 365
    
    # Gamification
    POINTS_PER_MODULE: int = 10
    POINTS_PER_COURSE: int = 100
    POINTS_PER_PERFECT_SCORE: int = 50
    STREAK_BONUS_MULTIPLIER: float = 1.5
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Feature Flags
    ENABLE_PRACTICE_ENVIRONMENT: bool = True
    ENABLE_VIDEO_DOWNLOADS: bool = True
    ENABLE_SOCIAL_LEARNING: bool = False
    ENABLE_AI_RECOMMENDATIONS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()