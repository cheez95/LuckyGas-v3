"""
Environment-Specific Configuration Manager

Provides secure configuration management with:
- Environment-specific settings (dev/staging/prod)
- Configuration validation
- Secret placeholder replacement
- Configuration templates
- Setup scripts for each environment
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
from pydantic import BaseModel, Field, validator
from enum import Enum
import logging
from app.core.enhanced_secrets_manager import get_secret_secure

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Supported environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str
    port: int = 5432
    database: str
    username: str
    password: str = Field(exclude=True)  # Exclude from logs
    ssl_mode: str = "require"
    pool_size: int = 20
    max_overflow: int = 40
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    @validator('password')
    def validate_password(cls, v):
        if v.startswith('${') and v.endswith('}'):
            # This is a placeholder, will be replaced
            return v
        if len(v) < 8:
            raise ValueError("Database password too short")
        return v


class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str
    port: int = 6379
    password: Optional[str] = Field(None, exclude=True)
    db: int = 0
    ssl: bool = False
    connection_pool_size: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


class GoogleCloudConfig(BaseModel):
    """Google Cloud configuration."""
    project_id: str
    region: str = "asia-east1"
    credentials_path: Optional[str] = None
    
    # Service-specific settings
    storage_bucket: str
    storage_location: str = "ASIA"
    
    # API restrictions
    maps_api_restrictions: Dict[str, Any] = {
        "allowed_ips": [],
        "allowed_domains": [],
        "quota_per_day": 25000,
        "quota_per_minute": 300
    }
    
    # Vertex AI settings
    vertex_ai_endpoint: Optional[str] = None
    vertex_ai_model: str = "text-bison@001"


class SecurityConfig(BaseModel):
    """Security configuration."""
    jwt_secret_key: str = Field(exclude=True)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Password policy
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10
    
    # CORS settings
    cors_origins: List[str] = []
    cors_allow_credentials: bool = True
    
    # Security headers
    security_headers: Dict[str, str] = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }


class BankingConfig(BaseModel):
    """Banking configuration."""
    enabled_banks: List[str] = []
    
    # Transaction limits
    daily_transaction_limit: float = 10000000  # TWD
    single_transaction_limit: float = 1000000  # TWD
    
    # Batch processing
    batch_size: int = 100
    batch_timeout: int = 300  # seconds
    
    # SFTP settings
    sftp_timeout: int = 30
    sftp_retry_attempts: int = 3
    sftp_retry_delay: int = 5
    
    # Security
    transaction_signing_required: bool = True
    dual_approval_threshold: float = 500000  # TWD


class NotificationConfig(BaseModel):
    """Notification configuration."""
    # Email settings
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = Field(None, exclude=True)
    smtp_use_tls: bool = True
    email_from: str = "noreply@luckygas.com.tw"
    
    # SMS settings
    sms_provider: str = "twilio"  # twilio or cht
    sms_from_number: Optional[str] = None
    
    # Push notification settings
    fcm_server_key: Optional[str] = Field(None, exclude=True)
    
    # Webhook settings
    webhook_timeout: int = 10
    webhook_retry_attempts: int = 3


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9090
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_to_file: bool = True
    log_file_path: str = "/var/log/luckygas/app.log"
    log_rotation: str = "daily"
    log_retention_days: int = 30
    
    # Health checks
    health_check_interval: int = 60
    health_check_timeout: int = 10
    
    # Alerting
    alert_email_recipients: List[str] = []
    alert_sms_recipients: List[str] = []


class ApplicationConfig(BaseModel):
    """Complete application configuration."""
    environment: Environment
    debug: bool = False
    
    # Component configurations
    database: DatabaseConfig
    redis: RedisConfig
    google_cloud: GoogleCloudConfig
    security: SecurityConfig
    banking: BankingConfig
    notifications: NotificationConfig
    monitoring: MonitoringConfig
    
    # Feature flags
    features: Dict[str, bool] = {
        "ai_predictions": True,
        "route_optimization": True,
        "mobile_app": True,
        "banking_integration": True,
        "sms_notifications": True,
        "email_invoices": True
    }
    
    # API settings
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    docs_enabled: bool = True
    
    @validator('debug')
    def validate_debug(cls, v, values):
        """Ensure debug is off in production."""
        if 'environment' in values and values['environment'] == Environment.PRODUCTION:
            if v:
                raise ValueError("Debug must be disabled in production")
        return v


class ConfigurationManager:
    """Manages environment-specific configurations."""
    
    def __init__(self):
        self._configs: Dict[Environment, ApplicationConfig] = {}
        self._current_env: Optional[Environment] = None
        self._config_dir = Path(__file__).parent.parent.parent / "configs"
        self._templates_dir = self._config_dir / "templates"
        self._load_configurations()
    
    def _load_configurations(self):
        """Load all environment configurations."""
        # Ensure config directories exist
        self._config_dir.mkdir(exist_ok=True)
        self._templates_dir.mkdir(exist_ok=True)
        
        # Load configurations for each environment
        for env in Environment:
            config_file = self._config_dir / f"{env.value}.yaml"
            if config_file.exists():
                try:
                    config = self._load_config_file(config_file, env)
                    self._configs[env] = config
                    logger.info(f"Loaded configuration for {env.value}")
                except Exception as e:
                    logger.error(f"Failed to load config for {env.value}: {e}")
    
    def _load_config_file(self, file_path: Path, env: Environment) -> ApplicationConfig:
        """Load and validate configuration file."""
        with open(file_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Replace placeholders with actual secrets
        processed_config = self._process_placeholders(raw_config, env)
        
        # Validate and create config object
        config = ApplicationConfig(**processed_config)
        
        # Additional environment-specific validation
        self._validate_environment_config(config, env)
        
        return config
    
    def _process_placeholders(self, config: Dict[str, Any], env: Environment) -> Dict[str, Any]:
        """Replace ${SECRET_NAME} placeholders with actual values."""
        def replace_in_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for key, value in d.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract secret name
                    secret_name = value[2:-1]
                    # Get from secrets manager
                    secret_value = get_secret_secure(
                        secret_name,
                        user_id=0,  # System user
                        purpose=f"config_loading_{env.value}"
                    )
                    if secret_value:
                        result[key] = secret_value
                    else:
                        logger.warning(f"Secret {secret_name} not found, keeping placeholder")
                        result[key] = value
                elif isinstance(value, dict):
                    result[key] = replace_in_dict(value)
                elif isinstance(value, list):
                    result[key] = [
                        replace_in_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    result[key] = value
            return result
        
        return replace_in_dict(config)
    
    def _validate_environment_config(self, config: ApplicationConfig, env: Environment):
        """Validate environment-specific configuration rules."""
        if env == Environment.PRODUCTION:
            # Production-specific validations
            if not config.database.ssl_mode == "require":
                raise ValueError("SSL must be required for production database")
            
            if not config.redis.ssl:
                raise ValueError("Redis SSL must be enabled in production")
            
            if config.security.rate_limit_enabled is False:
                raise ValueError("Rate limiting must be enabled in production")
            
            if not config.security.cors_origins:
                raise ValueError("CORS origins must be specified in production")
            
            if not config.banking.transaction_signing_required:
                raise ValueError("Transaction signing must be required in production")
        
        elif env == Environment.DEVELOPMENT:
            # Development-specific validations
            if config.security.jwt_secret_key == "changeme":
                logger.warning("Using default JWT secret in development")
    
    def get_config(self, env: Optional[Environment] = None) -> ApplicationConfig:
        """Get configuration for specified environment."""
        if env is None:
            env = self._current_env or self._detect_environment()
        
        if env not in self._configs:
            raise ValueError(f"No configuration found for environment: {env.value}")
        
        return self._configs[env]
    
    def _detect_environment(self) -> Environment:
        """Detect current environment from system."""
        env_value = os.getenv("ENVIRONMENT", "development").lower()
        
        try:
            return Environment(env_value)
        except ValueError:
            logger.warning(f"Unknown environment: {env_value}, defaulting to development")
            return Environment.DEVELOPMENT
    
    def create_template(self, env: Environment):
        """Create configuration template for an environment."""
        template_file = self._templates_dir / f"{env.value}.template.yaml"
        
        template_config = {
            "environment": env.value,
            "debug": env != Environment.PRODUCTION,
            "database": {
                "host": "${DB_HOST}",
                "port": 5432,
                "database": "${DB_NAME}",
                "username": "${DB_USER}",
                "password": "${DB_PASSWORD}",
                "ssl_mode": "require" if env == Environment.PRODUCTION else "prefer"
            },
            "redis": {
                "host": "${REDIS_HOST}",
                "port": 6379,
                "password": "${REDIS_PASSWORD}",
                "ssl": env == Environment.PRODUCTION
            },
            "google_cloud": {
                "project_id": "${GCP_PROJECT_ID}",
                "storage_bucket": "${GCS_BUCKET}",
                "maps_api_restrictions": {
                    "allowed_domains": ["luckygas.com.tw"] if env == Environment.PRODUCTION else ["localhost"]
                }
            },
            "security": {
                "jwt_secret_key": "${JWT_SECRET_KEY}",
                "cors_origins": self._get_default_cors_origins(env)
            },
            "banking": {
                "enabled_banks": ["mega", "ctbc", "esun"],
                "transaction_signing_required": env == Environment.PRODUCTION
            },
            "notifications": {
                "smtp_host": "${SMTP_HOST}",
                "smtp_username": "${SMTP_USERNAME}",
                "smtp_password": "${SMTP_PASSWORD}"
            },
            "monitoring": {
                "log_level": "DEBUG" if env == Environment.DEVELOPMENT else "INFO",
                "alert_email_recipients": ["ops@luckygas.com.tw"] if env == Environment.PRODUCTION else []
            }
        }
        
        with open(template_file, 'w') as f:
            yaml.dump(template_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created configuration template: {template_file}")
    
    def _get_default_cors_origins(self, env: Environment) -> List[str]:
        """Get default CORS origins for environment."""
        if env == Environment.PRODUCTION:
            return [
                "https://luckygas.com.tw",
                "https://www.luckygas.com.tw",
                "https://app.luckygas.com.tw"
            ]
        elif env == Environment.STAGING:
            return [
                "https://staging.luckygas.com.tw",
                "https://staging-app.luckygas.com.tw"
            ]
        else:
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173"
            ]
    
    def validate_all_configs(self) -> Dict[Environment, List[str]]:
        """Validate all environment configurations."""
        results = {}
        
        for env in Environment:
            errors = []
            
            try:
                config = self.get_config(env)
                
                # Check for placeholder values
                config_dict = config.dict()
                placeholders = self._find_placeholders(config_dict)
                if placeholders:
                    errors.append(f"Found unresolved placeholders: {', '.join(placeholders)}")
                
                # Environment-specific checks
                self._validate_environment_config(config, env)
                
            except Exception as e:
                errors.append(str(e))
            
            results[env] = errors
        
        return results
    
    def _find_placeholders(self, config: Dict[str, Any], path: str = "") -> List[str]:
        """Find any remaining placeholder values."""
        placeholders = []
        
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                placeholders.append(f"{current_path}={value}")
            elif isinstance(value, dict):
                placeholders.extend(self._find_placeholders(value, current_path))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        placeholders.extend(self._find_placeholders(item, f"{current_path}[{i}]"))
        
        return placeholders
    
    def export_config(self, env: Environment, include_secrets: bool = False) -> str:
        """Export configuration as YAML string."""
        config = self.get_config(env)
        config_dict = config.dict(exclude=None if include_secrets else {"password", "secret", "key"})
        return yaml.dump(config_dict, default_flow_style=False, sort_keys=False)


# Global instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get or create configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def get_current_config() -> ApplicationConfig:
    """Get configuration for current environment."""
    return get_config_manager().get_config()