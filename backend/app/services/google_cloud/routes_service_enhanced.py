"""
Enhanced Google Routes API Service with monitoring and protection

This version integrates:
- Secure API key management
- Rate limiting
- Cost monitoring
- Error handling with retry logic
- Circuit breaker pattern
- Response caching
"""
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
from dataclasses import dataclass
import logging

from app.core.google_cloud_config import get_gcp_config
from app.core.metrics import route_optimization_histogram
from app.models.route import Route as DeliveryRoute, RouteStop
from app.models.order import Order
from app.models.customer import Customer
from app.core.config import settings
from app.services.optimization.ortools_optimizer import (
    ortools_optimizer, VRPStop, VRPVehicle
)

# Import monitoring and protection components
from app.core.security.api_key_manager import get_api_key_manager
from app.services.google_cloud.monitoring.rate_limiter import get_rate_limiter
from app.services.google_cloud.monitoring.cost_monitor import get_cost_monitor
from app.services.google_cloud.monitoring.error_handler import GoogleAPIErrorHandler, GoogleAPIError
from app.services.google_cloud.monitoring.circuit_breaker import circuit_manager
from app.services.google_cloud.monitoring.api_cache import get_api_cache
from app.services.google_cloud.routes_service import GoogleRoutesService, DeliveryLocation

logger = logging.getLogger(__name__)


class EnhancedGoogleRoutesService(GoogleRoutesService):
    """
    Enhanced Google Routes API Service with comprehensive monitoring and protection
    """
    
    def __init__(self):
        # Initialize without calling parent __init__ to avoid double initialization
        self.gcp_config = get_gcp_config()
        self.base_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        self.optimization_url = "https://routes.googleapis.com/v1/projects/{}/locations/{}/routeOptimization:optimizeTours"
        self.depot_location = (settings.DEPOT_LAT, settings.DEPOT_LNG)
        
        # Initialize monitoring components
        self._api_key_manager = None
        self._rate_limiter = None
        self._cost_monitor = None
        self._cache = None
        self._circuit_breaker = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure all components are initialized"""
        if self._initialized:
            return
        
        # Initialize all monitoring components
        self._api_key_manager = await get_api_key_manager()
        self._rate_limiter = await get_rate_limiter()
        self._cost_monitor = await get_cost_monitor()
        self._cache = await get_api_cache()
        self._circuit_breaker = await circuit_manager.get_breaker(
            api_type="routes",
            failure_threshold=5,
            success_threshold=2,
            timeout=60
        )
        
        self._initialized = True
        logger.info("Enhanced Google Routes Service initialized with all monitoring components")
    
    async def _get_api_key(self) -> str:
        """Get API key from secure storage"""
        await self._ensure_initialized()
        
        # Try to get from secure storage first
        api_key = await self._api_key_manager.get_key("google_maps_api_key")
        
        if not api_key:
            # Fallback to environment variable
            api_key = self.gcp_config.maps_api_key
            
            if api_key:
                # Store in secure storage for future use
                await self._api_key_manager.set_key("google_maps_api_key", api_key)
        
        return api_key
    
    async def optimize_route(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int = 100,
        time_windows: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Enhanced route optimization with monitoring and protection
        """
        await self._ensure_initialized()
        
        # Check if API key is available
        api_key = await self._get_api_key()
        if not api_key:
            logger.warning("Google Maps API key not configured, returning unoptimized route")
            return self._create_unoptimized_route(depot, stops)
        
        # Create cache key
        cache_params = {
            "depot": depot,
            "stops": stops,
            "vehicle_capacity": vehicle_capacity,
            "time_windows": time_windows
        }
        
        # Check cache first
        cached_result = await self._cache.get("routes", cache_params)
        if cached_result:
            logger.info("Route optimization result found in cache")
            return cached_result
        
        # Check rate limits
        if not await self._rate_limiter.check_rate_limit("routes"):
            raise GoogleAPIError(
                message="Rate limit exceeded for Routes API",
                status_code=429,
                api_type="routes",
                endpoint="optimize_route"
            )
        
        # Check cost budget
        if not await self._cost_monitor.enforce_budget_limit("routes"):
            raise GoogleAPIError(
                message="Cost budget exceeded for Routes API",
                status_code=429,
                api_type="routes",
                endpoint="optimize_route",
                details={"reason": "budget_exceeded"}
            )
        
        # Execute with circuit breaker
        try:
            result = await self._circuit_breaker.call(
                self._execute_route_optimization,
                api_key, depot, stops, vehicle_capacity, time_windows
            )
            
            # Cache successful result
            await self._cache.set("routes", cache_params, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Route optimization failed: {e}")
            # Return fallback unoptimized route
            return self._create_unoptimized_route(depot, stops)
    
    async def _execute_route_optimization(
        self,
        api_key: str,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int,
        time_windows: Optional[Dict]
    ) -> Dict[str, Any]:
        """Execute the actual API call with error handling"""
        
        # Build request
        request_body = self._build_optimization_request(
            depot, stops, vehicle_capacity, time_windows
        )
        
        # Track start time for metrics
        import time
        start_time = time.time()
        
        # Make API request with retry logic
        async def make_request():
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "routes.optimizedIntermediateWaypointIndex,routes.duration,routes.distanceMeters,routes.polyline"
                }
                
                async with session.post(
                    self.base_url,
                    json=request_body,
                    headers=headers
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        # Record successful API call
                        processing_time = time.time() - start_time
                        await self._cost_monitor.record_api_call(
                            api_type="routes",
                            endpoint="computeRoutes",
                            response_size=len(response_text),
                            processing_time=processing_time
                        )
                        
                        # Record metrics
                        route_optimization_histogram.labels(
                            method="Google Routes API",
                            num_stops=str(len(stops))
                        ).observe(processing_time)
                        
                        result = json.loads(response_text)
                        return self._process_route_response(result, stops)
                    else:
                        # Raise for error handling
                        response.raise_for_status()
        
        # Execute with error handler
        return await GoogleAPIErrorHandler.handle_with_retry(
            make_request,
            api_type="routes",
            endpoint="computeRoutes"
        )
    
    async def optimize_multiple_routes(
        self,
        orders: List[Order],
        drivers: List[Dict],
        date: datetime
    ) -> List[Dict]:
        """
        Enhanced multiple route optimization with monitoring
        """
        await self._ensure_initialized()
        
        # Check rate limits for batch operation
        expected_api_calls = len(drivers)  # One call per driver for directions
        if not await self._rate_limiter.check_rate_limit("routes", count=expected_api_calls):
            raise GoogleAPIError(
                message=f"Rate limit would be exceeded for {expected_api_calls} route optimizations",
                status_code=429,
                api_type="routes",
                endpoint="optimize_multiple_routes"
            )
        
        # Use parent class implementation with OR-Tools
        logger.info(f"Optimizing routes for {len(orders)} orders and {len(drivers)} drivers")
        
        # Convert orders to VRPStop format
        stops = []
        for order in orders:
            if not order.customer:
                continue
                
            stop = VRPStop(
                order_id=order.id,
                customer_id=order.customer_id,
                customer_name=order.customer.short_name,
                address=order.delivery_address or order.customer.address,
                latitude=order.customer.latitude or self.depot_location[0],
                longitude=order.customer.longitude or self.depot_location[1],
                demand=self._extract_demand(order),
                time_window=self._get_time_window(order),
                service_time=self._estimate_service_time(order)
            )
            stops.append(stop)
        
        # Convert drivers to VRPVehicle format
        vehicles = []
        for driver in drivers:
            vehicle = VRPVehicle(
                driver_id=driver["id"],
                driver_name=driver["name"],
                capacity={
                    "50kg": 10,
                    "20kg": 20,
                    "16kg": 25,
                    "10kg": 40,
                    "4kg": 50
                },
                start_location=self.depot_location,
                max_travel_time=480  # 8 hours
            )
            vehicles.append(vehicle)
        
        # Optimize using OR-Tools
        import time
        start_time = time.time()
        optimized_routes = ortools_optimizer.optimize(stops, vehicles)
        optimization_time = time.time() - start_time
        
        # Record metrics
        route_optimization_histogram.labels(
            method="OR-Tools VRP",
            num_stops=str(len(stops))
        ).observe(optimization_time)
        
        logger.info(f"Route optimization completed in {optimization_time:.2f} seconds")
        
        # Get turn-by-turn directions with caching
        route_results = []
        for vehicle_idx, route_stops in optimized_routes.items():
            if not route_stops:
                continue
            
            # Get Google directions with monitoring
            google_route = await self._get_google_directions_enhanced(
                self.depot_location,
                route_stops
            )
            
            # Build route data
            route_data = {
                "route_number": f"R{date.strftime('%Y%m%d')}-{vehicle_idx+1:02d}",
                "driver_id": vehicles[vehicle_idx].driver_id,
                "driver_name": vehicles[vehicle_idx].driver_name,
                "vehicle_id": vehicle_idx,
                "date": date.isoformat(),
                "status": "optimized",
                "area": self._determine_area(route_stops),
                "stops": [
                    {
                        "order_id": stop.order_id,
                        "customer_id": stop.customer_id,
                        "customer_name": stop.customer_name,
                        "address": stop.address,
                        "lat": stop.latitude,
                        "lng": stop.longitude,
                        "stop_sequence": idx + 1,
                        "estimated_arrival": self._minutes_to_datetime(
                            date, stop.estimated_arrival
                        ).isoformat(),
                        "service_time": stop.service_time,
                        "products": stop.demand
                    }
                    for idx, stop in enumerate(route_stops)
                ],
                "total_stops": len(route_stops),
                "total_distance_km": google_route.get("distance", 0),
                "estimated_duration_minutes": google_route.get("duration", 0),
                "polyline": google_route.get("polyline", ""),
                "optimized": True,
                "optimization_method": "OR-Tools VRP"
            }
            route_results.append(route_data)
        
        return route_results
    
    async def _get_google_directions_enhanced(
        self,
        depot: Tuple[float, float],
        stops: List[VRPStop]
    ) -> Dict:
        """Enhanced Google directions with monitoring and caching"""
        api_key = await self._get_api_key()
        if not api_key or not stops:
            return {"distance": 0, "duration": 0, "polyline": ""}
        
        # Create cache key
        cache_params = {
            "depot": depot,
            "stop_coords": [(s.latitude, s.longitude) for s in stops]
        }
        
        # Check cache
        cached_result = await self._cache.get("routes_matrix", cache_params)
        if cached_result:
            return cached_result
        
        # Check rate limit
        if not await self._rate_limiter.check_rate_limit("routes"):
            logger.warning("Rate limit reached, returning estimated directions")
            return self._estimate_directions(depot, stops)
        
        # Execute with circuit breaker
        try:
            result = await self._circuit_breaker.call(
                self._execute_google_directions,
                api_key, depot, stops
            )
            
            # Cache result
            await self._cache.set("routes_matrix", cache_params, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get Google directions: {e}")
            return self._estimate_directions(depot, stops)
    
    async def _execute_google_directions(
        self,
        api_key: str,
        depot: Tuple[float, float],
        stops: List[VRPStop]
    ) -> Dict:
        """Execute Google directions API call"""
        # Create waypoints
        waypoints = []
        for stop in stops:
            waypoints.append({
                "location": {
                    "latLng": {
                        "latitude": stop.latitude,
                        "longitude": stop.longitude
                    }
                }
            })
        
        request_body = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": depot[0],
                        "longitude": depot[1]
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": depot[0],
                        "longitude": depot[1]
                    }
                }
            },
            "intermediates": waypoints,
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "optimizeWaypointOrder": False,
            "languageCode": "zh-TW",
            "regionCode": "TW"
        }
        
        import time
        start_time = time.time()
        
        async def make_request():
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline"
                }
                
                async with session.post(
                    self.base_url,
                    json=request_body,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        # Record API call
                        processing_time = time.time() - start_time
                        await self._cost_monitor.record_api_call(
                            api_type="routes",
                            endpoint="computeRoutes_directions",
                            processing_time=processing_time
                        )
                        
                        result = await response.json()
                        if result.get("routes"):
                            route = result["routes"][0]
                            return {
                                "distance": route.get("distanceMeters", 0) / 1000,
                                "duration": self._parse_duration(route.get("duration", "0s")),
                                "polyline": route.get("polyline", {}).get("encodedPolyline", "")
                            }
                    else:
                        response.raise_for_status()
        
        return await GoogleAPIErrorHandler.handle_with_retry(
            make_request,
            api_type="routes",
            endpoint="computeRoutes_directions"
        )
    
    def _estimate_directions(self, depot: Tuple[float, float], stops: List[VRPStop]) -> Dict:
        """Estimate directions when API is unavailable"""
        total_distance = 0
        current_location = depot
        
        for stop in stops:
            distance = self._calculate_distance(
                current_location[0], current_location[1],
                stop.latitude, stop.longitude
            )
            total_distance += distance
            current_location = (stop.latitude, stop.longitude)
        
        # Return to depot
        total_distance += self._calculate_distance(
            current_location[0], current_location[1],
            depot[0], depot[1]
        )
        
        # Estimate duration (average 30 km/h in city)
        duration_minutes = int((total_distance / 30) * 60)
        
        return {
            "distance": total_distance,
            "duration": duration_minutes,
            "polyline": ""  # No polyline for estimates
        }
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of the routes service"""
        await self._ensure_initialized()
        
        health = {
            "service": "Google Routes API",
            "status": "healthy",
            "components": {}
        }
        
        # Check API key
        api_key = await self._get_api_key()
        health["components"]["api_key"] = {
            "status": "configured" if api_key else "missing",
            "secure_storage": await self._api_key_manager.get_key("google_maps_api_key") is not None
        }
        
        # Check rate limiter
        rate_limit_info = await self._rate_limiter.get_current_usage("routes")
        health["components"]["rate_limiter"] = rate_limit_info
        
        # Check cost monitor
        cost_report = await self._cost_monitor.get_cost_report("daily")
        health["components"]["cost_monitor"] = {
            "daily_cost": cost_report["total_cost"],
            "daily_calls": cost_report["total_calls"],
            "budget_percentage": cost_report["budget_percentage"]
        }
        
        # Check circuit breaker
        circuit_state = self._circuit_breaker.get_state()
        health["components"]["circuit_breaker"] = circuit_state
        
        # Check cache
        cache_stats = await self._cache.get_stats()
        health["components"]["cache"] = cache_stats
        
        # Overall health
        if not api_key:
            health["status"] = "degraded"
            health["message"] = "API key not configured"
        elif circuit_state["state"] == "open":
            health["status"] = "unhealthy"
            health["message"] = "Circuit breaker is open - API failures detected"
        elif cost_report["budget_percentage"] > 90:
            health["status"] = "degraded"
            health["message"] = "Approaching daily budget limit"
        
        return health


# Create a function to get the enhanced service
def get_enhanced_routes_service() -> EnhancedGoogleRoutesService:
    """Get or create the enhanced routes service instance"""
    return EnhancedGoogleRoutesService()