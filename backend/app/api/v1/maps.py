"""
Maps API endpoints for Lucky Gas system
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/script-url")
def get_maps_script_url(
    current_user = Depends(get_current_user)
):
    """
    Get Google Maps script URL for frontend
    In production, this would return a properly configured URL with API key
    """
    # For now, return a placeholder URL
    # In production, the API key should be stored securely and injected here
    # Using a placeholder that won't cause immediate errors
    return {
        "url": "https://maps.googleapis.com/maps/api/js?key=AIzaSyBNLrJhOMz6idD05pzfn5lhA-TAw-mAZCU&libraries=places,drawing,geometry&language=zh-TW&region=TW"
    }


@router.get("/config")
def get_maps_config(
    current_user = Depends(get_current_user)
):
    """
    Get maps configuration for the application
    """
    return {
        "center": {
            "lat": 25.0330,
            "lng": 121.5654
        },
        "zoom": 12,
        "mapTypeId": "roadmap",
        "language": "zh-TW",
        "region": "TW",
        "styles": []  # Custom map styles can be added here
    }


@router.post("/geocode")
def geocode_address(
    address: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Geocode an address to get coordinates
    In production, this would call Google Geocoding API
    """
    # Mock response for now
    return {
        "success": True,
        "result": {
            "formatted_address": address,
            "latitude": 25.0330,
            "longitude": 121.5654,
            "place_id": "mock_place_id",
            "location_type": "ROOFTOP"
        }
    }


@router.post("/reverse-geocode")
def reverse_geocode(
    lat: float,
    lng: float,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Reverse geocode coordinates to get address
    """
    # Mock response for now
    return {
        "success": True,
        "result": {
            "formatted_address": f"台北市信義區信義路五段7號",
            "latitude": lat,
            "longitude": lng,
            "place_id": "mock_place_id",
            "address_components": [
                {"long_name": "7", "short_name": "7", "types": ["street_number"]},
                {"long_name": "信義路五段", "short_name": "信義路五段", "types": ["route"]},
                {"long_name": "信義區", "short_name": "信義區", "types": ["administrative_area_level_3"]},
                {"long_name": "台北市", "short_name": "台北市", "types": ["administrative_area_level_1"]},
                {"long_name": "台灣", "short_name": "TW", "types": ["country"]},
                {"long_name": "110", "short_name": "110", "types": ["postal_code"]}
            ]
        }
    }