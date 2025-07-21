"""
Development Mode Manager for Google Cloud Services

Provides seamless switching between production and mock services
with automatic detection of API key availability.
"""
import os
import logging
from typing import Dict, Any, Optional, Type
from enum import Enum
from app.core.config import settings
from app.services.google_cloud.routes_service import GoogleRoutesService
from app.services.google_cloud.mock_routes_service import MockGoogleRoutesService
from app.services.google_cloud.vertex_ai_service import VertexAIDemandPredictionService
from app.services.google_cloud.mock_vertex_ai_service import MockVertexAIDemandPredictionService
from app.services.google_cloud.monitoring.error_handler import GoogleAPIError

logger = logging.getLogger(__name__)


class DevelopmentMode(Enum):
    """Development mode settings"""
    AUTO = "auto"          # Automatically detect based on API keys
    PRODUCTION = "production"  # Force production mode
    DEVELOPMENT = "development"  # Force development/mock mode
    OFFLINE = "offline"    # Force offline mode with cached data


class DevelopmentModeManager:
    """
    Manages development mode for Google Cloud services
    
    Features:
    - Automatic detection of API key availability
    - Seamless switching between mock and production services
    - Offline mode with cached responses
    - Configuration override support
    """
    
    def __init__(self):
        self.mode = self._determine_mode()
        self._service_cache: Dict[str, Any] = {}
        self._mock_warning_shown = False
        
        logger.info(f"Development Mode Manager initialized in {self.mode.value} mode")
    
    def _determine_mode(self) -> DevelopmentMode:
        """Determine the appropriate development mode"""
        # Check for explicit mode setting
        mode_setting = os.getenv("GOOGLE_API_MODE", "auto").lower()
        
        if mode_setting == "production":
            return DevelopmentMode.PRODUCTION
        elif mode_setting == "development":
            return DevelopmentMode.DEVELOPMENT
        elif mode_setting == "offline":
            return DevelopmentMode.OFFLINE
        
        # Auto mode: Check for API keys
        has_google_api_key = bool(os.getenv("GOOGLE_API_KEY"))
        has_vertex_ai_creds = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        
        # In test environment, always use development mode
        if os.getenv("TESTING", "").lower() == "true":
            logger.info("Test environment detected, using development mode")
            return DevelopmentMode.DEVELOPMENT
        
        # If we have API keys, use production mode
        if has_google_api_key or has_vertex_ai_creds:
            logger.info("API keys detected, using production mode")
            return DevelopmentMode.PRODUCTION
        
        # No API keys, use development mode
        logger.warning(
            "No Google API keys detected. Using development mode with mock services. "
            "Set GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS for production mode."
        )
        return DevelopmentMode.DEVELOPMENT
    
    def get_mode(self) -> DevelopmentMode:
        """Get current development mode"""
        return self.mode
    
    def set_mode(self, mode: DevelopmentMode):
        """Manually set development mode"""
        old_mode = self.mode
        self.mode = mode
        
        # Clear service cache when switching modes
        if old_mode != mode:
            self._service_cache.clear()
            logger.info(f"Switched from {old_mode.value} to {mode.value} mode")
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.mode == DevelopmentMode.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.mode == DevelopmentMode.DEVELOPMENT
    
    def is_offline(self) -> bool:
        """Check if running in offline mode"""
        return self.mode == DevelopmentMode.OFFLINE
    
    async def get_routes_service(self) -> GoogleRoutesService:
        """Get appropriate routes service based on mode"""
        service_key = "routes_service"
        
        # Return cached service if available
        if service_key in self._service_cache:
            return self._service_cache[service_key]
        
        try:
            if self.mode == DevelopmentMode.PRODUCTION:
                # Try to create production service
                service = GoogleRoutesService()
                self._service_cache[service_key] = service
                return service
            
            elif self.mode in [DevelopmentMode.DEVELOPMENT, DevelopmentMode.OFFLINE]:
                # Use mock service
                service = MockGoogleRoutesService()
                self._service_cache[service_key] = service
                
                # Show warning once
                if not self._mock_warning_shown:
                    logger.warning(
                        "Using mock Google Routes service. Results are simulated. "
                        "Set GOOGLE_API_KEY for real route optimization."
                    )
                    self._mock_warning_shown = True
                
                return service
            
            else:  # AUTO mode
                # Try production first, fall back to mock
                try:
                    service = GoogleRoutesService()
                    self._service_cache[service_key] = service
                    self.mode = DevelopmentMode.PRODUCTION
                    return service
                except Exception as e:
                    logger.warning(f"Failed to initialize production routes service: {e}")
                    logger.info("Falling back to mock routes service")
                    
                    service = MockGoogleRoutesService()
                    self._service_cache[service_key] = service
                    self.mode = DevelopmentMode.DEVELOPMENT
                    
                    if not self._mock_warning_shown:
                        logger.warning(
                            "Using mock Google Routes service. Results are simulated. "
                            "Set GOOGLE_API_KEY for real route optimization."
                        )
                        self._mock_warning_shown = True
                    
                    return service
                    
        except Exception as e:
            logger.error(f"Failed to create routes service: {e}")
            raise GoogleAPIError(
                message=f"Failed to initialize routes service: {str(e)}",
                status_code=500,
                api_type="routes",
                endpoint="initialization"
            )
    
    async def get_vertex_ai_service(self) -> VertexAIDemandPredictionService:
        """Get appropriate Vertex AI service based on mode"""
        service_key = "vertex_ai_service"
        
        # Return cached service if available
        if service_key in self._service_cache:
            return self._service_cache[service_key]
        
        try:
            if self.mode == DevelopmentMode.PRODUCTION:
                # Try to create production service
                service = VertexAIDemandPredictionService()
                self._service_cache[service_key] = service
                return service
            
            elif self.mode in [DevelopmentMode.DEVELOPMENT, DevelopmentMode.OFFLINE]:
                # Use mock service
                service = MockVertexAIDemandPredictionService()
                self._service_cache[service_key] = service
                
                # Show warning once
                if not self._mock_warning_shown:
                    logger.warning(
                        "Using mock Vertex AI service. Predictions are simulated. "
                        "Set GOOGLE_APPLICATION_CREDENTIALS for real predictions."
                    )
                    self._mock_warning_shown = True
                
                return service
            
            else:  # AUTO mode
                # Try production first, fall back to mock
                try:
                    service = VertexAIDemandPredictionService()
                    self._service_cache[service_key] = service
                    self.mode = DevelopmentMode.PRODUCTION
                    return service
                except Exception as e:
                    logger.warning(f"Failed to initialize production Vertex AI service: {e}")
                    logger.info("Falling back to mock Vertex AI service")
                    
                    service = MockVertexAIDemandPredictionService()
                    self._service_cache[service_key] = service
                    self.mode = DevelopmentMode.DEVELOPMENT
                    
                    if not self._mock_warning_shown:
                        logger.warning(
                            "Using mock Vertex AI service. Predictions are simulated. "
                            "Set GOOGLE_APPLICATION_CREDENTIALS for real predictions."
                        )
                        self._mock_warning_shown = True
                    
                    return service
                    
        except Exception as e:
            logger.error(f"Failed to create Vertex AI service: {e}")
            raise GoogleAPIError(
                message=f"Failed to initialize Vertex AI service: {str(e)}",
                status_code=500,
                api_type="vertex_ai",
                endpoint="initialization"
            )
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about current services"""
        info = {
            "mode": self.mode.value,
            "services": {},
            "warnings": []
        }
        
        # Check routes service
        if "routes_service" in self._service_cache:
            service = self._service_cache["routes_service"]
            info["services"]["routes"] = {
                "type": type(service).__name__,
                "is_mock": isinstance(service, MockGoogleRoutesService)
            }
        
        # Check vertex AI service
        if "vertex_ai_service" in self._service_cache:
            service = self._service_cache["vertex_ai_service"]
            info["services"]["vertex_ai"] = {
                "type": type(service).__name__,
                "is_mock": isinstance(service, MockVertexAIDemandPredictionService)
            }
        
        # Add warnings
        if self.mode == DevelopmentMode.DEVELOPMENT:
            info["warnings"].append(
                "Running in development mode with mock services. "
                "API responses are simulated."
            )
        elif self.mode == DevelopmentMode.OFFLINE:
            info["warnings"].append(
                "Running in offline mode. Only cached responses available."
            )
        
        # Check for missing services
        if not os.getenv("GOOGLE_API_KEY") and self.mode != DevelopmentMode.DEVELOPMENT:
            info["warnings"].append(
                "GOOGLE_API_KEY not set. Routes API will not work in production mode."
            )
        
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and self.mode != DevelopmentMode.DEVELOPMENT:
            info["warnings"].append(
                "GOOGLE_APPLICATION_CREDENTIALS not set. Vertex AI will not work in production mode."
            )
        
        return info
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all services"""
        health = {
            "mode": self.mode.value,
            "healthy": True,
            "services": {}
        }
        
        # Check routes service
        try:
            routes_service = await self.get_routes_service()
            # Simple health check - try to get service info
            health["services"]["routes"] = {
                "status": "healthy",
                "type": type(routes_service).__name__,
                "is_mock": isinstance(routes_service, MockGoogleRoutesService)
            }
        except Exception as e:
            health["healthy"] = False
            health["services"]["routes"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check vertex AI service
        try:
            if self.mode == DevelopmentMode.PRODUCTION:
                vertex_service = await self.get_vertex_ai_service()
                health["services"]["vertex_ai"] = {
                    "status": "healthy",
                    "type": type(vertex_service).__name__,
                    "is_mock": False
                }
        except NotImplementedError:
            # Expected in development mode
            health["services"]["vertex_ai"] = {
                "status": "not_available",
                "reason": "Service not available in current mode"
            }
        except Exception as e:
            health["healthy"] = False
            health["services"]["vertex_ai"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        return health


# Global instance
_dev_mode_manager: Optional[DevelopmentModeManager] = None


def get_development_mode_manager() -> DevelopmentModeManager:
    """Get or create the singleton development mode manager"""
    global _dev_mode_manager
    if _dev_mode_manager is None:
        _dev_mode_manager = DevelopmentModeManager()
    return _dev_mode_manager


# Convenience functions
async def get_routes_service() -> GoogleRoutesService:
    """Get the appropriate routes service for current mode"""
    manager = get_development_mode_manager()
    return await manager.get_routes_service()


async def get_vertex_ai_service() -> VertexAIDemandPredictionService:
    """Get the appropriate Vertex AI service for current mode"""
    manager = get_development_mode_manager()
    return await manager.get_vertex_ai_service()


def is_production_mode() -> bool:
    """Check if running in production mode"""
    manager = get_development_mode_manager()
    return manager.is_production()


def is_development_mode() -> bool:
    """Check if running in development mode"""
    manager = get_development_mode_manager()
    return manager.is_development()