from typing import List, Union, Optional, Dict
from pydantic import field_validator, Field, model_validator, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets
import re
from enum import Enum


class Environment(str, Enum):
    """Application environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class BusinessConfig(BaseModel):
    """Business logic configuration"""
    # Delivery Time Windows
    delivery_start_hour: int = Field(8, ge=0, le=23, description="Earliest delivery hour")
    delivery_end_hour: int = Field(18, ge=0, le=23, description="Latest delivery hour")
    
    # Service Times (minutes)
    base_service_time: int = Field(5, ge=1, description="Base service time per stop")
    time_per_cylinder: int = Field(2, ge=1, description="Additional time per cylinder")
    
    # Capacity Constraints
    max_stops_per_route: int = Field(50, ge=1, description="Maximum stops per route")
    max_route_duration_hours: int = Field(8, ge=1, description="Maximum route duration")
    
    # Cost Factors
    driver_cost_per_hour: float = Field(500.0, gt=0, description="Driver cost per hour (TWD)")
    fuel_cost_per_km: float = Field(10.0, gt=0, description="Fuel cost per kilometer (TWD)")
    
    # Gas Cylinder Sizes (kg)
    cylinder_sizes: List[int] = Field(
        default=[50, 20, 16, 10, 4],
        description="Available gas cylinder sizes"
    )
    
    # Taiwan-specific
    invoice_tax_rate: float = Field(0.05, ge=0, le=1, description="Tax rate for invoices")
    weekend_surcharge: float = Field(1.2, ge=1, description="Weekend delivery surcharge multiplier")


class SecurityConfig(BaseModel):
    """Security configuration"""
    password_min_length: int = Field(8, ge=6, description="Minimum password length")
    password_require_uppercase: bool = Field(True, description="Require uppercase letter")
    password_require_lowercase: bool = Field(True, description="Require lowercase letter")
    password_require_digit: bool = Field(True, description="Require digit")
    password_require_special: bool = Field(True, description="Require special character")
    
    # Session settings
    session_timeout_minutes: int = Field(1440, ge=1, description="Session timeout (24 hours)")
    max_login_attempts: int = Field(5, ge=1, description="Maximum login attempts")
    lockout_duration_minutes: int = Field(30, ge=1, description="Account lockout duration")


class DatabaseConfig(BaseModel):
    """Database connection pool configuration"""
    # Pool settings
    pool_size: int = Field(20, ge=1, le=100, description="Number of connections to maintain")
    max_overflow: int = Field(10, ge=0, le=50, description="Maximum overflow connections")
    pool_timeout: int = Field(30, ge=1, description="Timeout waiting for connection")
    pool_recycle: int = Field(3600, ge=60, description="Recycle connections after seconds")
    pool_pre_ping: bool = Field(True, description="Test connections before using")
    
    # Performance settings
    statement_timeout: int = Field(60000, ge=1000, description="Statement timeout in milliseconds")
    command_timeout: int = Field(60, ge=1, description="Command timeout in seconds")
    
    # Connection settings
    keepalives: int = Field(1, ge=0, description="Enable TCP keepalives")
    keepalives_idle: int = Field(30, ge=1, description="Seconds before sending keepalive")
    keepalives_interval: int = Field(5, ge=1, description="Interval between keepalives")
    keepalives_count: int = Field(5, ge=1, description="Number of keepalives before closing")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Lucky Gas Delivery Management System"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT_ENABLED: bool = True
    
    @field_validator("ENVIRONMENT", mode="before")
    def validate_environment(cls, v: str) -> Environment:
        try:
            return Environment(v.lower())
        except ValueError:
            raise ValueError(f"Invalid environment: {v}. Must be one of: {', '.join([e.value for e in Environment])}")
    
    # Security
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for JWT encoding")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 2  # 2 hours (reduced from 8 days)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "luckygas"
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password")
    POSTGRES_DB: str = "luckygas"
    POSTGRES_PORT: int = Field(5433, ge=1024, le=65535, description="PostgreSQL port")
    DATABASE_URL: str = ""
    
    @field_validator("DATABASE_URL", mode="after")
    def assemble_db_connection(cls, v: str, values) -> str:
        if v:
            return v
        return f"postgresql+asyncpg://{values.data.get('POSTGRES_USER')}:{values.data.get('POSTGRES_PASSWORD')}@{values.data.get('POSTGRES_SERVER')}:{values.data.get('POSTGRES_PORT')}/{values.data.get('POSTGRES_DB')}"
    
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
        # Production domains
        "https://app.luckygas.tw",
        "https://www.luckygas.tw",
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
    GOOGLE_MAPS_API_KEY: str = Field("", pattern="^$|^AIza[0-9A-Za-z-_]{35}$", description="Google Maps API key (empty or valid format)")
    
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
    FIRST_SUPERUSER: str = Field("admin@luckygas.tw", description="Initial superuser email")
    FIRST_SUPERUSER_PASSWORD: str = Field(..., min_length=8, description="Initial superuser password")
    
    # Nested Configuration Objects
    business: BusinessConfig = Field(default_factory=BusinessConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    # Taiwan-specific Validators
    @field_validator("FIRST_SUPERUSER")
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError(f"Invalid email format: {v}")
        return v
    
    @staticmethod
    def validate_taiwan_phone(phone: str) -> bool:
        """
        Validate Taiwan phone number formats:
        - Mobile: 09XX-XXX-XXX or 09XXXXXXXX
        - Landline: 0X-XXXX-XXXX or 0XXXXXXXXX
        """
        # Remove any spaces or hyphens
        phone_clean = re.sub(r'[\s\-]', '', phone)
        
        # Mobile pattern: 09 followed by 8 digits
        mobile_pattern = r'^09\d{8}$'
        # Landline pattern: 0 + area code (1-2 digits) + 7-8 digits
        landline_pattern = r'^0[2-8]\d{7,8}$'
        
        return bool(re.match(mobile_pattern, phone_clean) or re.match(landline_pattern, phone_clean))
    
    @staticmethod
    def validate_taiwan_address(address: str) -> bool:
        """
        Validate Taiwan address format contains required components
        """
        # Check for common Taiwan address components
        required_patterns = [
            r'(縣|市)',  # County or City
            r'(區|鄉|鎮|市)',  # District
            r'(路|街|巷)',  # Road/Street
            r'號'  # Number
        ]
        
        return all(re.search(pattern, address) for pattern in required_patterns)
    
    @staticmethod
    def validate_tax_id(tax_id: str) -> bool:
        """
        Validate Taiwan tax ID (統一編號) - 8 digits with checksum
        """
        if not re.match(r'^\d{8}$', tax_id):
            return False
        
        # Taiwan tax ID checksum algorithm
        weights = [1, 2, 1, 2, 1, 2, 4, 1]
        checksum = 0
        
        for i, digit in enumerate(tax_id):
            product = int(digit) * weights[i]
            checksum += product // 10 + product % 10
        
        return checksum % 10 == 0
    
    @model_validator(mode="after")
    def validate_config(self) -> "Settings":
        """Validate configuration based on environment"""
        if self.ENVIRONMENT == Environment.PRODUCTION:
            # Production-specific validations
            if self.SECRET_KEY == secrets.token_urlsafe(32):
                raise ValueError("Must set a custom SECRET_KEY for production")
            if not self.GCP_PROJECT_ID:
                raise ValueError("GCP_PROJECT_ID is required for production")
            if self.LOG_LEVEL == "DEBUG":
                raise ValueError("DEBUG log level not recommended for production")
        
        # Validate business hours
        if self.business.delivery_start_hour >= self.business.delivery_end_hour:
            raise ValueError("Delivery start hour must be before end hour")
        
        return self
    
    def get_database_url(self, async_mode: bool = True) -> str:
        """Get database URL with option for sync/async"""
        driver = "postgresql+asyncpg" if async_mode else "postgresql"
        return f"{driver}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:5433/{self.POSTGRES_DB}"
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    def get_rate_limit(self) -> Dict[str, int]:
        """Get rate limit configuration based on environment"""
        if self.is_production():
            return {"calls": 100, "period": 60}  # 100 calls per minute
        else:
            return {"calls": 1000, "period": 60}  # 1000 calls per minute for dev


settings = Settings()