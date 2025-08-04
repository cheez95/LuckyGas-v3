"""
Environment Variable Validation
Ensures all required configuration is present at startup
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates environment variables on application startup"""

    # Required variables by environment
    REQUIRED_VARS = {
        "common": [
            "DATABASE_URL",
            "SECRET_KEY",
            "REDIS_URL",
        ],
        "production": [
            "GOOGLE_API_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GCP_PROJECT_ID",
        ],
        "development": [
            # No additional required vars for development
        ],
    }

    # Optional variables with descriptions
    OPTIONAL_VARS = {
        "GOOGLE_API_KEY": "Required for Google Routes API in production",
        "GOOGLE_APPLICATION_CREDENTIALS": "Required for Vertex AI in production",
        "GCP_PROJECT_ID": "Required for Google Cloud services",
        "DEVELOPMENT_MODE": "Controls mock service usage (auto/production/development/offline)",
        "DAILY_COST_WARNING": "Cost threshold for warnings (default: 50.00)",
        "DAILY_COST_CRITICAL": "Cost threshold for blocking (default: 100.00)",
        "ROUTES_RATE_LIMIT_PER_SECOND": "Override routes API rate limit",
        "SENTRY_DSN": "Error tracking integration",
        "LOG_LEVEL": "Logging verbosity (DEBUG/INFO/WARNING/ERROR)",
    }

    # URL validation patterns
    URL_VARS = ["DATABASE_URL", "REDIS_URL", "SENTRY_DSN"]

    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """
        Validate all environment variables
        Returns: (success, list_of_errors)
        """
        errors = []
        warnings = []
        environment = os.getenv("ENVIRONMENT", "development").lower()

        # Check common required variables
        for var in cls.REQUIRED_VARS["common"]:
            if not os.getenv(var):
                errors.append(f"Missing required variable: {var}")

        # Check environment-specific required variables
        if environment in cls.REQUIRED_VARS:
            for var in cls.REQUIRED_VARS[environment]:
                if not os.getenv(var):
                    errors.append(f"Missing required variable for {environment}: {var}")

        # Validate URL formats
        for var in cls.URL_VARS:
            value = os.getenv(var)
            if value:
                if not cls._validate_url(value):
                    errors.append(f"Invalid URL format for {var}: {value}")

        # Check optional variables and provide warnings
        for var, description in cls.OPTIONAL_VARS.items():
            if not os.getenv(var):
                # Only warn about production-critical vars in production
                if environment == "production" and var in [
                    "GOOGLE_API_KEY",
                    "GOOGLE_APPLICATION_CREDENTIALS",
                ]:
                    errors.append(
                        f"Missing critical variable for production: {var} - {description}"
                    )
                else:
                    warnings.append(f"Optional variable not set: {var} - {description}")

        # Validate specific variable formats
        cls._validate_specific_formats(errors)

        # Log results
        if errors:
            logger.error("Environment validation failed:")
            for error in errors:
                logger.error(f"  - {error}")

        if warnings:
            logger.warning("Environment validation warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")

        if not errors:
            logger.info(f"Environment validation passed for {environment} environment")

        return len(errors) == 0, errors

    @staticmethod
    def _validate_url(url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @classmethod
    def _validate_specific_formats(cls, errors: List[str]):
        """Validate specific environment variable formats"""
        # Validate LOG_LEVEL
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append(
                f"Invalid LOG_LEVEL: {log_level}. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )

        # Validate ENVIRONMENT
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment not in ["development", "staging", "production", "test"]:
            errors.append(
                f"Invalid ENVIRONMENT: {environment}. Must be one of: development, staging, production, test"
            )

        # Validate DEVELOPMENT_MODE
        dev_mode = os.getenv("DEVELOPMENT_MODE", "auto").lower()
        if dev_mode not in ["auto", "production", "development", "offline"]:
            errors.append(
                f"Invalid DEVELOPMENT_MODE: {dev_mode}. Must be one of: auto, production, development, offline"
            )

        # Validate numeric thresholds
        for var in [
            "DAILY_COST_WARNING",
            "DAILY_COST_CRITICAL",
            "ROUTES_RATE_LIMIT_PER_SECOND",
        ]:
            value = os.getenv(var)
            if value:
                try:
                    float(value)
                except ValueError:
                    errors.append(f"Invalid numeric value for {var}: {value}")

    @classmethod
    def check_google_api_readiness(cls) -> Dict[str, bool]:
        """Check if Google APIs are properly configured"""
        return {
            "routes_api": bool(os.getenv("GOOGLE_API_KEY")),
            "vertex_ai": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
            "gcp_project": bool(os.getenv("GCP_PROJECT_ID")),
            "redis": bool(os.getenv("REDIS_URL")),
        }

    @classmethod
    def get_config_summary(cls) -> Dict[str, any]:
        """Get a summary of current configuration"""
        environment = os.getenv("ENVIRONMENT", "development")
        dev_mode = os.getenv("DEVELOPMENT_MODE", "auto")

        return {
            "environment": environment,
            "development_mode": dev_mode,
            "google_apis_ready": cls.check_google_api_readiness(),
            "redis_configured": bool(os.getenv("REDIS_URL")),
            "cost_thresholds": {
                "warning": os.getenv("DAILY_COST_WARNING", "50.00"),
                "critical": os.getenv("DAILY_COST_CRITICAL", "100.00"),
            },
            "rate_limits": {
                "routes_per_second": os.getenv("ROUTES_RATE_LIMIT_PER_SECOND", "10"),
            },
        }


def validate_environment():
    """
    Validate environment on startup
    Exits if critical errors are found
    """
    success, errors = EnvironmentValidator.validate()

    if not success:
        print("\n" + "=" * 60)
        print("ENVIRONMENT VALIDATION FAILED")
        print("=" * 60)
        for error in errors:
            print(f"❌ {error}")
        print("=" * 60)
        print("\nPlease set the required environment variables and try again.")
        print("For development, you can use the .env.example file as a template.")
        sys.exit(1)

    # Print configuration summary
    config = EnvironmentValidator.get_config_summary()
    print("\n" + "=" * 60)
    print("ENVIRONMENT CONFIGURATION")
    print("=" * 60)
    print(f"Environment: {config['environment']}")
    print(f"Development Mode: {config['development_mode']}")
    print("\nGoogle APIs Ready:")
    for api, ready in config["google_apis_ready"].items():
        status = "✅" if ready else "❌"
        print(f"  {status} {api}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Test validation
    validate_environment()
