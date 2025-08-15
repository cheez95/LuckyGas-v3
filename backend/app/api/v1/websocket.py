"""
Simplified WebSocket endpoints for Lucky Gas
Synchronous version for simplified backend
"""
import logging
import jwt
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Store active connections
active_connections: dict = {}


async def authenticate_websocket(token: Optional[str]) -> Optional[dict]:
    """Simple WebSocket authentication"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if user_id:
            return {
                "user_id": user_id,
                "email": payload.get("email", ""),
                "role": payload.get("role", "customer")
            }
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        return None
    
    return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """Main WebSocket endpoint"""
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    # Authenticate
    user = await authenticate_websocket(token)
    if not user:
        await websocket.send_json({
            "type": "error",
            "message": "Authentication failed"
        })
        await websocket.close(code=4001)
        return
    
    user_id = user["user_id"]
    active_connections[user_id] = websocket
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully",
            "user": user
        })
        
        # Keep connection alive
        while True:
            # Wait for messages
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": data.get("timestamp")
                })
            elif data.get("type") == "subscribe":
                # Handle subscription requests
                await websocket.send_json({
                    "type": "subscribed",
                    "channel": data.get("channel"),
                    "message": f"Subscribed to {data.get('channel')}"
                })
            else:
                # Echo back for now
                await websocket.send_json({
                    "type": "message",
                    "data": data
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
        if user_id in active_connections:
            del active_connections[user_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if user_id in active_connections:
            del active_connections[user_id]
        await websocket.close(code=1000)


@router.get("/test")
async def test_websocket():
    """Test endpoint to verify WebSocket module is loaded"""
    return {
        "status": "ok",
        "message": "WebSocket module is loaded",
        "active_connections": len(active_connections)
    }