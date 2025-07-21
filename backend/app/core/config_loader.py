"""
Advanced configuration loader with environment-specific settings
"""
from typing import Dict, Any, Optional
import json
import yaml
from pathlib import Path
from pydantic import BaseModel, Field
import logging

from app.core.config import Settings, Environment

logger = logging.getLogger(__name__)


class ConfigurationLoader:
    """
    Load configuration from multiple sources with precedence:
    1. Environment variables (highest priority)
    2. Environment-specific config files
    3. Default config file
    4. Default values in Settings class (lowest priority)
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config")
        self.env_mapping = {
            Environment.DEVELOPMENT: "development",
            Environment.STAGING: "staging",
            Environment.PRODUCTION: "production",
            Environment.TEST: "test"
        }
    
    def load_config(self, environment: Optional[str] = None) -> Settings:
        """Load configuration based on environment"""
        # Determine environment
        env = environment or Settings().ENVIRONMENT
        
        # Load base configuration
        base_config = self._load_file("default")
        
        # Load environment-specific configuration
        env_config = self._load_file(self.env_mapping.get(env, "development"))
        
        # Merge configurations
        merged_config = self._merge_configs(base_config, env_config)
        
        # Create Settings instance with merged config
        return Settings(**merged_config)
    
    def _load_file(self, env_name: str) -> Dict[str, Any]:
        """Load configuration from file"""
        config = {}
        
        # Try YAML first
        yaml_file = self.config_dir / f"{env_name}.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                config = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {yaml_file}")
                return config
        
        # Try JSON
        json_file = self.config_dir / f"{env_name}.json"
        if json_file.exists():
            with open(json_file) as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from {json_file}")
                return config
        
        return config
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result


class ConfigValidator:
    """Validate configuration for specific environments"""
    
    @staticmethod
    def validate_production(settings: Settings) -> None:
        """Validate production configuration"""
        errors = []
        
        # Security checks
        if len(settings.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters for production")
        
        if settings.ALGORITHM != "HS256":
            errors.append("Only HS256 algorithm is approved for production")
        
        # Database checks
        if "localhost" in settings.DATABASE_URL:
            errors.append("Database must not be on localhost for production")
        
        # Google Cloud checks
        if not settings.GCP_PROJECT_ID:
            errors.append("GCP_PROJECT_ID is required for production")
        
        if not settings.GOOGLE_APPLICATION_CREDENTIALS:
            errors.append("Service account credentials required for production")
        
        # CORS checks
        if not settings.BACKEND_CORS_ORIGINS:
            errors.append("CORS origins must be explicitly set for production")
        
        if errors:
            raise ValueError(f"Production configuration errors: {', '.join(errors)}")
    
    @staticmethod
    def validate_security_config(settings: Settings) -> None:
        """Validate security configuration"""
        security = settings.security
        
        if security.password_min_length < 8:
            raise ValueError("Password minimum length must be at least 8")
        
        if security.session_timeout_minutes > 1440:  # 24 hours
            logger.warning("Session timeout exceeds 24 hours")
        
        if security.max_login_attempts < 3:
            raise ValueError("Maximum login attempts must be at least 3")


# Configuration presets for different deployment scenarios
class DeploymentPresets:
    """Pre-configured settings for common deployment scenarios"""
    
    @staticmethod
    def local_development() -> Dict[str, Any]:
        """Local development preset"""
        return {
            "ENVIRONMENT": "development",
            "LOG_LEVEL": "DEBUG",
            "RATE_LIMIT_ENABLED": False,
            "POSTGRES_SERVER": "localhost",
            "REDIS_URL": "redis://localhost:6379",
            "business": {
                "delivery_start_hour": 8,
                "delivery_end_hour": 18,
                "driver_cost_per_hour": 500.0
            }
        }
    
    @staticmethod
    def docker_compose() -> Dict[str, Any]:
        """Docker Compose preset"""
        return {
            "ENVIRONMENT": "development",
            "POSTGRES_SERVER": "db",
            "REDIS_URL": "redis://redis:6379",
            "BACKEND_CORS_ORIGINS": ["http://frontend:3000"]
        }
    
    @staticmethod
    def cloud_run() -> Dict[str, Any]:
        """Google Cloud Run preset"""
        return {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "INFO",
            "RATE_LIMIT_ENABLED": True,
            # Cloud Run provides PORT env var
            # Database connection via Cloud SQL proxy
            "business": {
                "max_stops_per_route": 100,
                "max_route_duration_hours": 10
            }
        }
    
    @staticmethod
    def kubernetes() -> Dict[str, Any]:
        """Kubernetes preset"""
        return {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "INFO",
            "RATE_LIMIT_ENABLED": True,
            # Use service names for internal communication
            "POSTGRES_SERVER": "postgres-service",
            "REDIS_URL": "redis://redis-service:6379"
        }


# Helper functions
def get_settings_for_environment(env: str) -> Settings:
    """Get settings for a specific environment"""
    loader = ConfigurationLoader()
    settings = loader.load_config(env)
    
    # Validate if production
    if settings.ENVIRONMENT == Environment.PRODUCTION:
        ConfigValidator.validate_production(settings)
    
    # Always validate security
    ConfigValidator.validate_security_config(settings)
    
    return settings


def create_config_files():
    """Create example configuration files"""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Default configuration
    default_config = {
        "PROJECT_NAME": "Lucky Gas Delivery Management System",
        "API_V1_STR": "/api/v1",
        "TIMEZONE": "Asia/Taipei",
        "business": {
            "cylinder_sizes": [50, 20, 16, 10, 4],
            "invoice_tax_rate": 0.05,
            "weekend_surcharge": 1.2
        },
        "security": {
            "password_min_length": 8,
            "password_require_uppercase": True,
            "password_require_lowercase": True,
            "password_require_digit": True,
            "password_require_special": True
        }
    }
    
    # Development configuration
    dev_config = {
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "DEBUG",
        "RATE_LIMIT_ENABLED": False,
        "SECRET_KEY": "development-secret-key-not-for-production"
    }
    
    # Production configuration
    prod_config = {
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "INFO",
        "RATE_LIMIT_ENABLED": True,
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
        "business": {
            "max_stops_per_route": 100,
            "max_route_duration_hours": 10
        }
    }
    
    # Write configuration files
    with open(config_dir / "default.yaml", "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    
    with open(config_dir / "development.yaml", "w") as f:
        yaml.dump(dev_config, f, default_flow_style=False)
    
    with open(config_dir / "production.yaml", "w") as f:
        yaml.dump(prod_config, f, default_flow_style=False)
    
    logger.info("Created example configuration files in config/")


if __name__ == "__main__":
    # Example usage
    create_config_files()
    
    # Load development settings
    dev_settings = get_settings_for_environment("development")
    print(f"Development settings loaded: {dev_settings.ENVIRONMENT}")
    
    # Load production settings (will fail validation without proper config)
    try:
        prod_settings = get_settings_for_environment("production")
        print(f"Production settings loaded: {prod_settings.ENVIRONMENT}")
    except ValueError as e:
        print(f"Production validation failed: {e}")