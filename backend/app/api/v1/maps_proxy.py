"""
Secure Google Maps API proxy endpoint.

This module provides a secure proxy for Google Maps API calls,
hiding API keys from the frontend and implementing rate limiting,
authentication, and usage monitoring.
"""
from typing import Optional

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from redis import Redis
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.monitoring import track_api_usage
from app.core.secrets_manager import get_secret
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_REQUESTS = {
    "geocoding": 50,  # per minute per user
    "directions": 30,
    "places": 40,
    "static_maps": 100,
    "distance_matrix": 20,
}

# Cache configuration
CACHE_TTL = {
    "geocoding": 86400,  # 24 hours
    "directions": 3600,  # 1 hour
    "places": 7200,  # 2 hours
    "static_maps": 86400,  # 24 hours
    "distance_matrix": 3600,  # 1 hour
}


class GoogleMapsProxy:
    """Secure proxy for Google Maps API calls."""

    def __init__(self):
        self._api_key = None
        self._redis_client = None
        self._http_client = None
        self._usage_tracker = {}
        self._pending_requests = {}  # For request deduplication
        self._request_lock = asyncio.Lock()

    @property
    def api_key(self) -> str:
        """Get Google Maps API key from secrets manager."""
        if not self._api_key:
            self._api_key = get_secret("GOOGLE_MAPS_API_KEY")
            if not self._api_key:
                raise ValueError("Google Maps API key not configured")
        return self._api_key

    @property
    def redis_client(self) -> Redis:
        """Get Redis client for caching and rate limiting."""
        if not self._redis_client:
            try:
                self._redis_client = Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True,
                )
                self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis not available: {e}")
                self._redis_client = None
        return self._redis_client

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for making API calls."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(
                timeout=30.0, headers={"User - Agent": "LuckyGas - Backend / 1.0"}
            )
        return self._http_client

    def _generate_cache_key(self, service: str, params: dict) -> str:
        """Generate cache key for request."""
        # Sort params for consistent hashing
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        hash_str = hashlib.sha256(f"{service}:{param_str}".encode()).hexdigest()
        return f"maps_cache:{service}:{hash_str}"

    def _generate_rate_limit_key(self, user_id: int, service: str) -> str:
        """Generate rate limit key for user and service."""
        return f"maps_rate_limit:{user_id}:{service}"

    async def check_rate_limit(self, user_id: int, service: str) -> bool:
        """Check if user has exceeded rate limit."""
        if not self.redis_client:
            return True  # Allow if Redis not available

        try:
            key = self._generate_rate_limit_key(user_id, service)
            current = self.redis_client.incr(key)

            if current == 1:
                self.redis_client.expire(key, RATE_LIMIT_WINDOW)

            limit = RATE_LIMIT_REQUESTS.get(service, 50)
            return current <= limit
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error

    async def get_cached_response(self, service: str, params: dict) -> Optional[dict]:
        """Get cached response if available."""
        if not self.redis_client:
            return None

        try:
            key = self._generate_cache_key(service, params)
            cached = self.redis_client.get(key)
            if cached:
                logger.debug(f"Cache hit for {service}")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache retrieval failed: {e}")

        return None

    async def cache_response(self, service: str, params: dict, response: dict):
        """Cache API response."""
        if not self.redis_client:
            return

        try:
            key = self._generate_cache_key(service, params)
            ttl = CACHE_TTL.get(service, 3600)
            self.redis_client.setex(key, ttl, json.dumps(response))
        except Exception as e:
            logger.error(f"Cache storage failed: {e}")

    async def log_usage(
        self,
        user_id: int,
        service: str,
        params: dict,
        response_time: float,
        cached: bool = False,
    ):
        """Log API usage for monitoring and billing."""
        try:
            # Track in database for persistent storage
            await track_api_usage(
                user_id=user_id,
                api_name="google_maps",
                endpoint=service,
                request_params=params,
                response_time=response_time,
                cached=cached,
            )

            # Track in memory for quick stats
            if service not in self._usage_tracker:
                self._usage_tracker[service] = {
                    "requests": 0,
                    "cached": 0,
                    "total_time": 0.0,
                }

            self._usage_tracker[service]["requests"] += 1
            if cached:
                self._usage_tracker[service]["cached"] += 1
            self._usage_tracker[service]["total_time"] += response_time

        except Exception as e:
            logger.error(f"Usage logging failed: {e}")

    async def make_api_call(self, service: str, endpoint: str, params: dict) -> dict:
        """Make actual API call to Google Maps with request deduplication."""
        # Generate request key for deduplication
        request_key = self._generate_cache_key(service, params)

        async with self._request_lock:
            # Check if request is already in progress
            if request_key in self._pending_requests:
                logger.debug(f"Request already in progress for {service}, waiting...")
                # Wait for the pending request to complete
                return await self._pending_requests[request_key]

            # Create a future for this request
            future = asyncio.create_task(
                self._execute_api_call(service, endpoint, params)
            )
            self._pending_requests[request_key] = future

        try:
            result = await future
            return result
        finally:
            # Remove from pending requests
            async with self._request_lock:
                self._pending_requests.pop(request_key, None)

    async def _execute_api_call(
        self, service: str, endpoint: str, params: dict
    ) -> dict:
        """Execute the actual API call to Google Maps."""
        # Add API key to params
        params["key"] = self.api_key

        # Build URL
        base_url = "https://maps.googleapis.com / maps / api"
        url = f"{base_url}/{service}/{endpoint}"

        try:
            start_time = time.time()
            response = await self.http_client.get(url, params=params)
            time.time() - start_time

            if response.status_code != 200:
                logger.error(
                    f"Google Maps API error: {response.status_code} - {response.text}"
                )
                raise HTTPException(status_code=502, detail="External API error")

            data = response.json()

            # Check for API errors
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                logger.error(
                    f"Google Maps API status: {data.get('status')} - {data.get('error_message')}"
                )
                raise HTTPException(
                    status_code=502,
                    detail=data.get("error_message", "External API error"),
                )

            return data

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(
                status_code=502, detail="Failed to connect to external service"
            )


# Initialize proxy
maps_proxy = GoogleMapsProxy()


@router.get("/geocode")
async def geocode(
    address: str = Query(..., description="Address to geocode"),
    language: str = Query("zh - TW", description="Response language"),
    region: str = Query("TW", description="Region bias"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Geocode an address to coordinates.

    This endpoint proxies requests to Google Maps Geocoding API
    with authentication, rate limiting, and caching.
    """
    service = "geocode"
    endpoint = "json"

    # Check rate limit
    if not await maps_proxy.check_rate_limit(current_user.id, service):
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please try again later."
        )

    # Prepare params
    params = {"address": address, "language": language, "region": region}

    # Check cache
    # Use "geocoding" as key for backward compatibility with existing cache
    cached_response = await maps_proxy.get_cached_response("geocoding", params)
    if cached_response:
        await maps_proxy.log_usage(
            current_user.id, "geocoding", params, 0.0, cached=True
        )
        return cached_response

    # Make API call
    start_time = time.time()
    try:
        response = await maps_proxy.make_api_call(service, endpoint, params)
        response_time = time.time() - start_time

        # Cache successful response
        await maps_proxy.cache_response("geocoding", params, response)

        # Log usage
        await maps_proxy.log_usage(current_user.id, "geocoding", params, response_time)

        return response

    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
        raise


@router.get("/directions")
async def directions(
    origin: str = Query(..., description="Origin location"),
    destination: str = Query(..., description="Destination location"),
    waypoints: Optional[str] = Query(None, description="Waypoints (pipe - separated)"),
    mode: str = Query("driving", description="Travel mode"),
    departure_time: Optional[str] = Query(None, description="Departure time"),
    avoid: Optional[str] = Query(None, description="Features to avoid"),
    language: str = Query("zh - TW", description="Response language"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get directions between locations.

    This endpoint proxies requests to Google Maps Directions API
    with authentication, rate limiting, and caching.
    """
    service = "directions"
    endpoint = "json"

    # Check rate limit
    if not await maps_proxy.check_rate_limit(current_user.id, service):
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please try again later."
        )

    # Prepare params
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "language": language,
        "region": "TW",
    }

    if waypoints:
        params["waypoints"] = waypoints
    if departure_time:
        params["departure_time"] = departure_time
    if avoid:
        params["avoid"] = avoid

    # Check cache
    cached_response = await maps_proxy.get_cached_response(service, params)
    if cached_response:
        await maps_proxy.log_usage(current_user.id, service, params, 0.0, cached=True)
        return cached_response

    # Make API call
    start_time = time.time()
    try:
        response = await maps_proxy.make_api_call(service, endpoint, params)
        response_time = time.time() - start_time

        # Cache successful response
        await maps_proxy.cache_response(service, params, response)

        # Log usage
        await maps_proxy.log_usage(current_user.id, service, params, response_time)

        return response

    except Exception as e:
        logger.error(f"Directions request failed: {e}")
        raise


@router.get("/places / nearby")
async def places_nearby(
    location: str = Query(..., description="Center location (lat, lng)"),
    radius: int = Query(1000, description="Search radius in meters"),
    type: Optional[str] = Query(None, description="Place type"),
    keyword: Optional[str] = Query(None, description="Search keyword"),
    language: str = Query("zh - TW", description="Response language"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search for places near a location.

    This endpoint proxies requests to Google Maps Places API
    with authentication, rate limiting, and caching.
    """
    service = "places"
    endpoint = "nearbysearch / json"

    # Check rate limit
    if not await maps_proxy.check_rate_limit(current_user.id, service):
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please try again later."
        )

    # Prepare params
    params = {"location": location, "radius": radius, "language": language}

    if type:
        params["type"] = type
    if keyword:
        params["keyword"] = keyword

    # Check cache
    cached_response = await maps_proxy.get_cached_response(service, params)
    if cached_response:
        await maps_proxy.log_usage(current_user.id, service, params, 0.0, cached=True)
        return cached_response

    # Make API call
    start_time = time.time()
    try:
        response = await maps_proxy.make_api_call(
            "place", endpoint, params  # Note: Places API uses 'place' not 'places'
        )
        response_time = time.time() - start_time

        # Cache successful response
        await maps_proxy.cache_response(service, params, response)

        # Log usage
        await maps_proxy.log_usage(current_user.id, service, params, response_time)

        return response

    except Exception as e:
        logger.error(f"Places search failed: {e}")
        raise


@router.get("/distance - matrix")
async def distance_matrix(
    origins: str = Query(..., description="Origin locations (pipe - separated)"),
    destinations: str = Query(
        ..., description="Destination locations (pipe - separated)"
    ),
    mode: str = Query("driving", description="Travel mode"),
    departure_time: Optional[str] = Query(None, description="Departure time"),
    language: str = Query("zh - TW", description="Response language"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calculate distance matrix between multiple origins and destinations.

    This endpoint proxies requests to Google Maps Distance Matrix API
    with authentication, rate limiting, and caching.
    """
    service = "distance_matrix"
    endpoint = "json"

    # Check rate limit
    if not await maps_proxy.check_rate_limit(current_user.id, service):
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please try again later."
        )

    # Prepare params
    params = {
        "origins": origins,
        "destinations": destinations,
        "mode": mode,
        "language": language,
        "region": "TW",
    }

    if departure_time:
        params["departure_time"] = departure_time

    # Check cache
    cached_response = await maps_proxy.get_cached_response(service, params)
    if cached_response:
        await maps_proxy.log_usage(current_user.id, service, params, 0.0, cached=True)
        return cached_response

    # Make API call
    start_time = time.time()
    try:
        response = await maps_proxy.make_api_call(
            "distancematrix", endpoint, params  # Note: API uses 'distancematrix'
        )
        response_time = time.time() - start_time

        # Cache successful response
        await maps_proxy.cache_response(service, params, response)

        # Log usage
        await maps_proxy.log_usage(current_user.id, service, params, response_time)

        return response

    except Exception as e:
        logger.error(f"Distance matrix request failed: {e}")
        raise


@router.get("/script - url")
async def get_maps_script_url(
    libraries: str = Query(
        "places, drawing, geometry", description="Libraries to load"
    ),
    language: str = Query("zh - TW", description="Language"),
    region: str = Query("TW", description="Region"),
    version: str = Query("weekly", description="API version"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get secure Google Maps JavaScript API URL.

    This endpoint generates a properly authenticated URL for loading
    the Google Maps JavaScript API, keeping the API key secure on the backend.
    """
    # Build the script URL with API key
    base_url = "https://maps.googleapis.com / maps / api / js"
    params = {
        "key": maps_proxy.api_key,
        "libraries": libraries,
        "language": language,
        "region": region,
        "v": version,
        "callback": "initMap",  # Global callback function
    }

    # Build query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    script_url = f"{base_url}?{query_string}"

    # Log the request
    await maps_proxy.log_usage(
        current_user.id,
        "script_loader",
        {"libraries": libraries, "language": language},
        0.0,
    )

    return {"url": script_url}


@router.get("/usage - stats")
async def get_usage_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get API usage statistics for the current user.

    Only available to admin users.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get in - memory stats
    stats = {
        "services": maps_proxy._usage_tracker,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Get rate limit status for all services
    if maps_proxy.redis_client:
        rate_limits = {}
        for service in RATE_LIMIT_REQUESTS:
            key = maps_proxy._generate_rate_limit_key(current_user.id, service)
            current = maps_proxy.redis_client.get(key) or 0
            rate_limits[service] = {
                "current": int(current),
                "limit": RATE_LIMIT_REQUESTS[service],
                "window_seconds": RATE_LIMIT_WINDOW,
            }
        stats["rate_limits"] = rate_limits

    return stats


# Cleanup on shutdown


@router.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    if maps_proxy._http_client:
        await maps_proxy._http_client.aclose()
    if maps_proxy._redis_client:
        maps_proxy._redis_client.close()
