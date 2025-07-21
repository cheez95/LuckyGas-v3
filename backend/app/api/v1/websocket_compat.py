"""
WebSocket to Socket.IO compatibility layer
Provides backward compatibility during migration
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Optional
import json
import logging
from datetime import datetime

from app.api.v1.socketio_handler import (
    notify_order_update,
    notify_route_update,
    notify_prediction_ready,
    notify_driver_assigned,
    send_notification,
    broadcast_system_message
)

logger = logging.getLogger(__name__)


class WebSocketToSocketIOAdapter:
    """
    Adapter to maintain WebSocket API while using Socket.IO backend
    This allows gradual migration of frontend clients
    """
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.connected = False
        
    async def accept(self):
        """Accept WebSocket connection"""
        await self.websocket.accept()
        self.connected = True
        
        # Send deprecation notice
        await self.websocket.send_json({
            "type": "deprecation_notice",
            "message": "WebSocket endpoint is deprecated. Please migrate to Socket.IO",
            "migration_guide": "https://docs.luckygas.tw/migration/socketio",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def receive_json(self):
        """Receive and parse JSON message"""
        if not self.connected:
            raise WebSocketDisconnect()
        return await self.websocket.receive_json()
    
    async def send_json(self, data: dict):
        """Send JSON message"""
        if not self.connected:
            raise WebSocketDisconnect()
        await self.websocket.send_json(data)
    
    async def close(self, code: int = 1000):
        """Close WebSocket connection"""
        if self.connected:
            await self.websocket.close(code=code)
            self.connected = False
    
    async def handle_message(self, message: dict):
        """
        Convert WebSocket messages to Socket.IO calls
        """
        msg_type = message.get("type")
        
        try:
            if msg_type == "ping":
                # Simple ping response
                await self.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif msg_type == "subscribe":
                # Subscription handled locally for this connection
                topic = message.get("topic")
                await self.send_json({
                    "type": "subscribed",
                    "topic": topic,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif msg_type == "driver_location":
                # Forward to Socket.IO system
                await notify_route_update(
                    route_id=0,  # Legacy support
                    update_type="driver_location",
                    details={
                        "driver_id": message.get("driver_id"),
                        "latitude": message.get("latitude"),
                        "longitude": message.get("longitude")
                    }
                )
            
            elif msg_type == "delivery_status":
                # Forward to Socket.IO system
                await notify_order_update(
                    order_id=message.get("order_id"),
                    status=message.get("status"),
                    details=message.get("details", {})
                )
            
            else:
                # Unknown message type
                await self.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_json({
                "type": "error",
                "message": "Internal server error",
                "timestamp": datetime.utcnow().isoformat()
            })


# Compatibility endpoint - can be removed after full migration
async def websocket_compat_endpoint(websocket: WebSocket, user_id: int, role: str):
    """
    Compatibility endpoint that translates WebSocket to Socket.IO
    """
    adapter = WebSocketToSocketIOAdapter(websocket)
    await adapter.accept()
    
    logger.warning(f"WebSocket compatibility connection from user {user_id}")
    
    try:
        while True:
            message = await adapter.receive_json()
            await adapter.handle_message(message)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket compatibility disconnection from user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket compatibility error: {e}")
        await adapter.close(code=1011)  # Internal error


# Migration helpers
def get_migration_instructions():
    """Get detailed migration instructions for frontend developers"""
    return {
        "overview": "Migrate from WebSocket to Socket.IO for better reliability",
        "benefits": [
            "Automatic reconnection",
            "Room-based messaging",
            "Acknowledgment callbacks",
            "Better error handling",
            "Binary data support"
        ],
        "steps": [
            {
                "step": 1,
                "action": "Install Socket.IO client",
                "code": "npm install socket.io-client"
            },
            {
                "step": 2,
                "action": "Replace WebSocket connection",
                "old_code": """
const ws = new WebSocket('ws://localhost:8000/ws?token=' + token);
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
};
""",
                "new_code": """
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000', {
    auth: { token: token },
    path: '/socket.io'
});

socket.on('connect', () => {
    console.log('Connected to Socket.IO');
});

socket.on('order_update', (data) => {
    handleOrderUpdate(data);
});
"""
            },
            {
                "step": 3,
                "action": "Update event handlers",
                "changes": [
                    "Replace ws.send() with socket.emit()",
                    "Use socket.on() for event listeners",
                    "Add acknowledgment callbacks where needed"
                ]
            },
            {
                "step": 4,
                "action": "Test thoroughly",
                "checklist": [
                    "Connection/disconnection",
                    "Auto-reconnection",
                    "All event types",
                    "Error scenarios"
                ]
            }
        ],
        "example_events": {
            "client_to_server": [
                "ping",
                "subscribe",
                "unsubscribe",
                "driver_location",
                "delivery_status"
            ],
            "server_to_client": [
                "connected",
                "pong",
                "order_update",
                "route_update",
                "prediction_ready",
                "notification",
                "system_message"
            ]
        },
        "deprecation_timeline": {
            "phase1": "Socket.IO available alongside WebSocket",
            "phase2": "WebSocket marked as deprecated with warnings",
            "phase3": "WebSocket endpoint removed"
        }
    }