"""
Mock Google Routes API Server for Testing

This module provides a mock implementation of Google Routes API endpoints
for testing without incurring API costs or requiring internet connectivity.
"""

from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import json
import random
import math
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, Response
import asyncio
import logging

logger = logging.getLogger(__name__)

# Create FastAPI app for mock server
mock_app = FastAPI(title="Mock Google Routes API", version="1.0.0")

# Mock API key for testing
MOCK_API_KEY = "mock_AIzaSyC-1234567890abcdefghijklmnop"

# Taiwan-specific mock data
TAIWAN_AREAS = ["信義區", "大安區", "中山區", "內湖區", "士林區", "北投區"]
TRAFFIC_CONDITIONS = ["NORMAL", "SLOW", "CONGESTION"]


class MockRoutesServer:
    """Mock Google Routes API server implementation"""

    def __init__(self):
        self.request_count = 0
        self.rate_limit_per_second = 10
        self.last_request_time = datetime.now()
        self.mock_delays = True  # Simulate network delays

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        return api_key == MOCK_API_KEY

    def calculate_haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in km

        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def generate_polyline(self, points: List[Tuple[float, float]]) -> str:
        """Generate a mock encoded polyline"""
        # Simple mock polyline - in production, this would be properly encoded
        return "ipkcFfichVnP@j@kBiD{FqCcBuBqAsAqE_DmGyIoB}C" + "".join(
            random.choice(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            )
            for _ in range(20)
        )

    async def compute_routes(self, request_data: Dict) -> Dict:
        """Mock implementation of computeRoutes endpoint"""
        if self.mock_delays:
            await asyncio.sleep(random.uniform(0.1, 0.3))  # Simulate network delay

        origin = request_data["origin"]["location"]["latLng"]
        destination = request_data["destination"]["location"]["latLng"]
        intermediates = request_data.get("intermediates", [])
        optimize_order = request_data.get("optimizeWaypointOrder", False)

        # Calculate base distance and duration
        total_distance = 0
        total_duration = 0
        legs = []

        # Create waypoints list
        waypoints = [(origin["latitude"], origin["longitude"])]
        for intermediate in intermediates:
            loc = intermediate["location"]["latLng"]
            waypoints.append((loc["latitude"], loc["longitude"]))
        waypoints.append((destination["latitude"], destination["longitude"]))

        # Optimize order if requested
        if optimize_order and len(intermediates) > 1:
            # Simple optimization: sort by distance from depot
            intermediate_points = waypoints[1:-1]
            depot = waypoints[0]
            sorted_points = sorted(
                intermediate_points,
                key=lambda p: self.calculate_haversine_distance(
                    depot[0], depot[1], p[0], p[1]
                ),
            )
            waypoints = [depot] + sorted_points + [waypoints[-1]]

            # Generate optimized indices
            optimized_indices = []
            original_intermediates = [
                (
                    i["location"]["latLng"]["latitude"],
                    i["location"]["latLng"]["longitude"],
                )
                for i in intermediates
            ]
            for point in sorted_points:
                optimized_indices.append(original_intermediates.index(point))
        else:
            optimized_indices = list(range(len(intermediates)))

        # Calculate legs
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]

            distance = self.calculate_haversine_distance(
                start[0], start[1], end[0], end[1]
            )
            # Assume average speed of 30 km/h in city
            duration = (distance / 30) * 3600  # Convert to seconds

            # Add random traffic delay
            traffic_factor = random.uniform(1.1, 1.5) if random.random() > 0.7 else 1.0
            duration *= traffic_factor

            leg = {
                "distanceMeters": int(distance * 1000),
                "duration": f"{int(duration)}s",
                "staticDuration": f"{int(duration / traffic_factor)}s",
                "polyline": {"encodedPolyline": self.generate_polyline([start, end])},
                "startLocation": {
                    "latLng": {"latitude": start[0], "longitude": start[1]}
                },
                "endLocation": {"latLng": {"latitude": end[0], "longitude": end[1]}},
            }

            legs.append(leg)
            total_distance += distance * 1000
            total_duration += duration

        # Build response
        route = {
            "legs": legs,
            "distanceMeters": int(total_distance),
            "duration": f"{int(total_duration)}s",
            "staticDuration": f"{int(total_duration * 0.8)}s",
            "polyline": {"encodedPolyline": self.generate_polyline(waypoints)},
        }

        # Add optimization info if applicable
        if optimize_order and len(intermediates) > 1:
            route["optimizedIntermediateWaypointIndex"] = optimized_indices

        # Add extra computations if requested
        if "FUEL_CONSUMPTION" in request_data.get("extraComputations", []):
            # Estimate fuel consumption (liters per 100km * distance in km / 100)
            fuel_consumption = 8.5 * (total_distance / 1000) / 100
            route["fuelConsumptionMicroliters"] = int(fuel_consumption * 1_000_000)

        if "TOLLS" in request_data.get("extraComputations", []):
            # Mock toll data for Taiwan
            route["tolls"] = {
                "estimatedPrice": [
                    {
                        "currencyCode": "TWD",
                        "units": "0",  # Taiwan highways are mostly toll-free
                        "nanos": 0,
                    }
                ]
            }

        response = {"routes": [route]}

        # Add fuel-efficient route if requested
        if "FUEL_EFFICIENT" in request_data.get("requestedReferenceRoutes", []):
            fuel_efficient_route = {
                **route,
                "distanceMeters": int(total_distance * 1.1),  # Slightly longer
                "duration": f"{int(total_duration * 0.95)}s",  # Slightly faster
                "fuelConsumptionMicroliters": int(
                    fuel_consumption * 0.9 * 1_000_000
                ),  # Less fuel
                "routeLabels": ["FUEL_EFFICIENT"],
            }
            response["routes"].append(fuel_efficient_route)

        return response

    async def compute_route_matrix(self, request_data: Dict) -> List[Dict]:
        """Mock implementation of computeRouteMatrix endpoint"""
        if self.mock_delays:
            await asyncio.sleep(random.uniform(0.1, 0.3))

        origins = request_data.get("origins", [])
        destinations = request_data.get("destinations", [])

        matrix_elements = []

        for origin in origins:
            for destination in destinations:
                origin_loc = origin["waypoint"]["location"]["latLng"]
                dest_loc = destination["waypoint"]["location"]["latLng"]

                distance = self.calculate_haversine_distance(
                    origin_loc["latitude"],
                    origin_loc["longitude"],
                    dest_loc["latitude"],
                    dest_loc["longitude"],
                )

                # Calculate duration with traffic
                base_duration = (distance / 30) * 3600  # 30 km/h average
                traffic_factor = random.uniform(1.0, 1.3)
                duration = base_duration * traffic_factor

                element = {
                    "originIndex": origins.index(origin),
                    "destinationIndex": destinations.index(destination),
                    "status": "OK",
                    "distanceMeters": int(distance * 1000),
                    "duration": f"{int(duration)}s",
                    "staticDuration": f"{int(base_duration)}s",
                    "condition": random.choice(["ROUTE_EXISTS", "ROUTE_EXISTS"]),
                }

                matrix_elements.append(element)

        return matrix_elements

    def check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded"""
        current_time = datetime.now()
        time_diff = (current_time - self.last_request_time).total_seconds()

        if time_diff < 1.0:
            self.request_count += 1
            if self.request_count > self.rate_limit_per_second:
                return False
        else:
            self.request_count = 1
            self.last_request_time = current_time

        return True


# Create mock server instance
mock_server = MockRoutesServer()


@mock_app.middleware("http")
async def validate_api_key_middleware(request: Request, call_next):
    """Validate API key for all requests"""
    if request.url.path == "/docs" or request.url.path == "/openapi.json":
        return await call_next(request)

    api_key = request.headers.get("X-Goog-Api-Key")
    if not api_key or not await mock_server.validate_api_key(api_key):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": 401,
                    "message": "Invalid API key",
                    "status": "UNAUTHENTICATED",
                }
            },
        )

    # Check rate limit
    if not mock_server.check_rate_limit():
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": 429,
                    "message": "Rate limit exceeded",
                    "status": "RESOURCE_EXHAUSTED",
                }
            },
        )

    response = await call_next(request)
    return response


@mock_app.post("/directions/v2:computeRoutes")
async def compute_routes(request: Request):
    """Mock Google Routes API computeRoutes endpoint"""
    try:
        request_data = await request.json()
        result = await mock_server.compute_routes(request_data)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in mock computeRoutes: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": 500, "message": str(e), "status": "INTERNAL"}},
        )


@mock_app.post("/distanceMatrix/v2:computeRouteMatrix")
async def compute_route_matrix(request: Request):
    """Mock Google Routes API computeRouteMatrix endpoint"""
    try:
        request_data = await request.json()
        result = await mock_server.compute_route_matrix(request_data)
        # Return as newline-delimited JSON (streaming format)
        response_content = "\n".join(json.dumps(element) for element in result)
        return Response(content=response_content, media_type="application/json")
    except Exception as e:
        logger.error(f"Error in mock computeRouteMatrix: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": 500, "message": str(e), "status": "INTERNAL"}},
        )


@mock_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Mock Google Routes API",
        "timestamp": datetime.now().isoformat(),
        "request_count": mock_server.request_count,
    }


# Configuration for running the mock server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(mock_app, host="127.0.0.1", port=8888, log_level="info")
