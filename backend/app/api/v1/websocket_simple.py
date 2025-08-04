"""
Simple WebSocket endpoint for real-time communication
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional

from app.api import deps
from app.services.simple_websocket import websocket_manager
from app.core.auth import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time updates.
    
    Connect with: ws://localhost:8000/api/v1/websocket/ws?token=YOUR_JWT_TOKEN
    """
    connection_id = None
    
    try:
        # Validate token (optional for now)
        user_id = "anonymous"
        if token:
            try:
                payload = decode_token(token)
                user_id = str(payload.get("sub", "anonymous"))
            except Exception as e:
                logger.warning(f"Invalid token in WebSocket connection: {e}")
                await websocket.close(code=1008, reason="Invalid token")
                return
        
        # Accept connection
        connection_id = await websocket_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Handle messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                # Handle the message
                await websocket_manager.handle_message(connection_id, data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                # Continue handling other messages
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Clean up connection
        if connection_id:
            await websocket_manager.disconnect(connection_id)


@router.post("/broadcast")
async def broadcast_message(
    event_type: str,
    data: dict,
    current_user = Depends(deps.get_current_user)
):
    """
    Broadcast a message to all connected WebSocket clients.
    
    Requires authentication.
    """
    # Only allow staff to broadcast
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        return {"error": "Unauthorized"}
    
    await websocket_manager.broadcast_event(event_type, data)
    
    return {
        "success": True,
        "event_type": event_type,
        "connections": len(websocket_manager.connections)
    }


@router.get("/connections")
async def get_connections(
    current_user = Depends(deps.get_current_user)
):
    """
    Get current WebSocket connections (for monitoring).
    
    Requires admin authentication.
    """
    if current_user.role not in ["super_admin", "manager"]:
        return {"error": "Unauthorized"}
    
    return {
        "total_connections": len(websocket_manager.connections),
        "connection_ids": list(websocket_manager.connections.keys()),
        "redis_connected": websocket_manager.redis_client is not None
    }