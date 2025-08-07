"""
Mock Google Cloud Services for Testing
Provides mock implementations of Google Maps, Routes API, and Vertex AI
"""

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock GCP Services", version="1.0.0")


# Models
class LatLng(BaseModel):
    latitude: float
    longitude: float


class Location(BaseModel):
    latLng: LatLng


class Waypoint(BaseModel):
    location: Location
    
    
class RouteRequest(BaseModel):
    origin: Waypoint
    destination: Waypoint
    intermediates: Optional[List[Waypoint]] = []
    travelMode: str = "DRIVE"
    computeAlternativeRoutes: bool = False
    routePreference: str = "TRAFFIC_AWARE"
    departureTime: Optional[str] = None
    languageCode: str = "zh-TW"
    units: str = "METRIC"


class PredictionRequest(BaseModel):
    instances: List[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]] = {}


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "mock-gcp", "timestamp": datetime.now().isoformat()}


# Google Maps Geocoding API
@app.get("/maps/api/geocode/json")
async def geocode(address: str = Query(...), key: str = Query(...)):
    """Mock Google Maps Geocoding API"""
    logger.info(f"Geocoding request for address: {address}")
    
    # Generate mock coordinates for Taiwan addresses
    base_lat = 25.0330
    base_lng = 121.5654
    
    return {
        "results": [{
            "formatted_address": address,
            "geometry": {
                "location": {
                    "lat": base_lat + random.uniform(-0.1, 0.1),
                    "lng": base_lng + random.uniform(-0.1, 0.1)
                },
                "location_type": "ROOFTOP",
                "viewport": {
                    "northeast": {
                        "lat": base_lat + 0.01,
                        "lng": base_lng + 0.01
                    },
                    "southwest": {
                        "lat": base_lat - 0.01,
                        "lng": base_lng - 0.01
                    }
                }
            },
            "place_id": f"mock_place_id_{uuid.uuid4().hex[:8]}",
            "types": ["street_address"]
        }],
        "status": "OK"
    }


# Google Routes API
@app.post("/routes/v2:computeRoutes")
async def compute_routes(request: RouteRequest):
    """Mock Google Routes API"""
    logger.info(f"Route computation request from {request.origin} to {request.destination}")
    
    # Calculate mock distance and duration
    num_waypoints = len(request.intermediates) + 2
    base_distance = random.randint(5000, 20000)  # 5-20km
    base_duration = random.randint(600, 2400)  # 10-40 minutes
    
    # Add distance/time for each waypoint
    total_distance = base_distance * num_waypoints
    total_duration = base_duration + (num_waypoints * 300)  # 5 min per stop
    
    route = {
        "distanceMeters": total_distance,
        "duration": f"{total_duration}s",
        "polyline": {
            "encodedPolyline": "mock_polyline_" + uuid.uuid4().hex[:16]
        },
        "legs": []
    }
    
    # Create legs for each segment
    for i in range(num_waypoints - 1):
        leg_distance = total_distance // (num_waypoints - 1)
        leg_duration = total_duration // (num_waypoints - 1)
        
        route["legs"].append({
            "distanceMeters": leg_distance,
            "duration": f"{leg_duration}s",
            "staticDuration": f"{leg_duration}s",
            "polyline": {
                "encodedPolyline": f"mock_leg_{i}_" + uuid.uuid4().hex[:8]
            },
            "startLocation": {
                "latLng": {
                    "latitude": 25.0330 + random.uniform(-0.05, 0.05),
                    "longitude": 121.5654 + random.uniform(-0.05, 0.05)
                }
            },
            "endLocation": {
                "latLng": {
                    "latitude": 25.0330 + random.uniform(-0.05, 0.05),
                    "longitude": 121.5654 + random.uniform(-0.05, 0.05)
                }
            }
        })
    
    response = {
        "routes": [route]
    }
    
    if request.computeAlternativeRoutes:
        # Add an alternative route
        alt_route = {
            "distanceMeters": int(total_distance * 1.1),
            "duration": f"{int(total_duration * 1.15)}s",
            "polyline": {
                "encodedPolyline": "mock_alt_polyline_" + uuid.uuid4().hex[:16]
            }
        }
        response["routes"].append(alt_route)
    
    return response


# Google Distance Matrix API
@app.get("/maps/api/distancematrix/json")
async def distance_matrix(
    origins: str = Query(...),
    destinations: str = Query(...),
    key: str = Query(...),
    mode: str = Query("driving"),
    language: str = Query("zh-TW")
):
    """Mock Google Distance Matrix API"""
    logger.info(f"Distance matrix request: {origins} to {destinations}")
    
    origin_list = origins.split("|")
    dest_list = destinations.split("|")
    
    rows = []
    for origin in origin_list:
        elements = []
        for dest in dest_list:
            # Generate random distance and duration
            distance = random.randint(1000, 50000)  # 1-50km
            duration = random.randint(300, 3600)  # 5-60 minutes
            
            elements.append({
                "distance": {
                    "text": f"{distance/1000:.1f} 公里",
                    "value": distance
                },
                "duration": {
                    "text": f"{duration//60} 分鐘",
                    "value": duration
                },
                "status": "OK"
            })
        rows.append({"elements": elements})
    
    return {
        "destination_addresses": dest_list,
        "origin_addresses": origin_list,
        "rows": rows,
        "status": "OK"
    }


# Vertex AI Predictions
@app.post("/vertex-ai/v1/projects/{project}/locations/{location}/endpoints/{endpoint}:predict")
async def vertex_ai_predict(
    project: str,
    location: str,
    endpoint: str,
    request: PredictionRequest
):
    """Mock Vertex AI prediction endpoint"""
    logger.info(f"Vertex AI prediction request for endpoint: {endpoint}")
    
    predictions = []
    
    for instance in request.instances:
        # Generate mock predictions based on input
        if "customer_id" in instance:
            # Customer demand prediction
            prediction = {
                "predicted_demand": random.randint(1, 10),
                "confidence": random.uniform(0.7, 0.95),
                "next_order_days": random.randint(7, 30),
                "recommended_products": [
                    {"product_id": "GAS-20KG", "quantity": random.randint(1, 5)},
                    {"product_id": "GAS-16KG", "quantity": random.randint(1, 3)}
                ]
            }
        elif "route_id" in instance:
            # Route optimization prediction
            prediction = {
                "optimized_sequence": list(range(1, random.randint(5, 15))),
                "estimated_time_minutes": random.randint(120, 480),
                "estimated_distance_km": random.uniform(20, 100),
                "fuel_consumption_liters": random.uniform(5, 30)
            }
        else:
            # Generic prediction
            prediction = {
                "value": random.uniform(0, 100),
                "confidence": random.uniform(0.6, 0.99),
                "timestamp": datetime.now().isoformat()
            }
        
        predictions.append(prediction)
    
    return {
        "predictions": predictions,
        "deployedModelId": f"mock-model-{endpoint}",
        "model": f"projects/{project}/locations/{location}/models/mock-model",
        "modelDisplayName": "Mock Prediction Model",
        "modelVersionId": "1"
    }


# Places API Autocomplete
@app.get("/maps/api/place/autocomplete/json")
async def place_autocomplete(
    input: str = Query(...),
    key: str = Query(...),
    language: str = Query("zh-TW"),
    components: str = Query("country:tw")
):
    """Mock Google Places Autocomplete API"""
    logger.info(f"Place autocomplete request: {input}")
    
    # Generate mock predictions
    predictions = []
    base_addresses = [
        "台北市中正區",
        "新北市板橋區",
        "台中市西區",
        "高雄市前金區",
        "台南市中西區"
    ]
    
    for i, base in enumerate(base_addresses[:3]):
        if input.lower() in base.lower() or not input:
            predictions.append({
                "description": f"{base}{input}路{random.randint(1, 200)}號",
                "matched_substrings": [{"length": len(input), "offset": 0}],
                "place_id": f"mock_place_{uuid.uuid4().hex[:8]}",
                "structured_formatting": {
                    "main_text": f"{base}{input}路",
                    "secondary_text": "台灣"
                },
                "terms": [
                    {"offset": 0, "value": base},
                    {"offset": len(base), "value": f"{input}路"}
                ],
                "types": ["route", "geocode"]
            })
    
    return {
        "predictions": predictions,
        "status": "OK"
    }


# Mock credentials file endpoint
@app.get("/test-credentials.json")
async def get_test_credentials():
    """Return mock GCP credentials for testing"""
    return {
        "type": "service_account",
        "project_id": "test-lucky-gas",
        "private_key_id": "mock-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK-PRIVATE-KEY\n-----END PRIVATE KEY-----",
        "client_email": "test-service-account@test-lucky-gas.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test-service-account%40test-lucky-gas.iam.gserviceaccount.com"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)