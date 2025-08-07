"""
WebSocket connection manager for real-time features.
"""
from typing import Dict, List, Set, Optional, Any
import json
import asyncio
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.connection_users: Dict[str, str] = {}  # connection_id -> user_id
        self.redis: Optional[Redis] = None
        self.pubsub_task: Optional[asyncio.Task] = None
        
    async def initialize(self, redis: Redis):
        """Initialize the connection manager with Redis."""
        self.redis = redis
        # Start Redis pubsub listener
        self.pubsub_task = asyncio.create_task(self._pubsub_listener())
        logger.info("WebSocket connection manager initialized")
        
    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        self.connection_users[connection_id] = user_id
        
        # Notify user joined
        await self._broadcast_user_status(user_id, "online")
        
        # Send connection acknowledgment
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"User {user_id} connected with connection {connection_id}")
        
    async def disconnect(self, user_id: str, connection_id: str):
        """Handle WebSocket disconnection."""
        if user_id in self.active_connections:
            # Remove the specific WebSocket connection
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id]
                if id(ws) != int(connection_id.split("-")[-1])
            ]
            
            # Clean up if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                await self._broadcast_user_status(user_id, "offline")
        
        # Clean up connection tracking
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        if connection_id in self.connection_users:
            del self.connection_users[connection_id]
            
        logger.info(f"User {user_id} disconnected (connection {connection_id})")
        
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.append(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.active_connections[user_id].remove(ws)
                
    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """Broadcast a message to all connected users."""
        disconnected_users = []
        
        for user_id, connections in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue
                
            disconnected = []
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.append(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                connections.remove(ws)
                
            if not connections:
                disconnected_users.append(user_id)
        
        # Clean up users with no connections
        for user_id in disconnected_users:
            del self.active_connections[user_id]
            
    async def broadcast_to_role(self, message: dict, role: str):
        """Broadcast a message to all users with a specific role."""
        # This would need integration with the user service to get users by role
        # For now, we'll use Redis to track user roles
        if self.redis:
            role_users = await self.redis.smembers(f"role:{role}:users")
            for user_id in role_users:
                await self.send_personal_message(message, user_id.decode())
                
    async def broadcast_to_group(self, message: dict, group_id: str):
        """Broadcast a message to all users in a specific group."""
        if self.redis:
            group_users = await self.redis.smembers(f"group:{group_id}:users")
            for user_id in group_users:
                await self.send_personal_message(message, user_id.decode())
                
    async def _broadcast_user_status(self, user_id: str, status: str):
        """Broadcast user online/offline status."""
        message = {
            "type": "user_status",
            "user_id": user_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message, exclude_user=user_id)
        
    async def _pubsub_listener(self):
        """Listen for Redis pub/sub messages."""
        if not self.redis:
            return
            
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("websocket:broadcast")
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self.broadcast(data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in pubsub message: {message['data']}")
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            await pubsub.unsubscribe("websocket:broadcast")
            await pubsub.close()
            
    async def publish_message(self, channel: str, message: dict):
        """Publish a message to Redis for cross-instance broadcasting."""
        if self.redis:
            await self.redis.publish(channel, json.dumps(message))
            
    async def shutdown(self):
        """Shutdown the connection manager."""
        # Cancel pubsub listener
        if self.pubsub_task:
            self.pubsub_task.cancel()
            
        # Close all connections
        for user_id, connections in self.active_connections.items():
            for websocket in connections:
                try:
                    await websocket.close()
                except:
                    pass
        
        self.active_connections.clear()
        self.user_connections.clear()
        self.connection_users.clear()
        
        logger.info("WebSocket connection manager shutdown complete")


# Global instance
manager = ConnectionManager()


class WebSocketMessageHandler:
    """Handles different types of WebSocket messages."""
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.handlers = {
            "ping": self._handle_ping,
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "message": self._handle_message,
            "location_update": self._handle_location_update,
            "order_update": self._handle_order_update,
        }
        
    async def handle_message(self, websocket: WebSocket, user_id: str, data: dict):
        """Route message to appropriate handler."""
        message_type = data.get("type")
        
        if message_type in self.handlers:
            await self.handlers[message_type](websocket, user_id, data)
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    async def _handle_ping(self, websocket: WebSocket, user_id: str, data: dict):
        """Handle ping message."""
        await websocket.send_json({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def _handle_subscribe(self, websocket: WebSocket, user_id: str, data: dict):
        """Handle subscription to a channel."""
        channel = data.get("channel")
        if channel:
            # Add user to Redis channel set
            if self.manager.redis:
                await self.manager.redis.sadd(f"channel:{channel}:users", user_id)
                
            await websocket.send_json({
                "type": "subscribed",
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat()
            })
            
    async def _handle_unsubscribe(self, websocket: WebSocket, user_id: str, data: dict):
        """Handle unsubscription from a channel."""
        channel = data.get("channel")
        if channel:
            # Remove user from Redis channel set
            if self.manager.redis:
                await self.manager.redis.srem(f"channel:{channel}:users", user_id)
                
            await websocket.send_json({
                "type": "unsubscribed",
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat()
            })
            
    async def _handle_message(self, websocket: WebSocket, user_id: str, data: dict):
        """Handle general message."""
        # This could be used for chat or other messaging features
        recipient = data.get("recipient")
        content = data.get("content")
        
        if recipient and content:
            message = {
                "type": "message",
                "from": user_id,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.manager.send_personal_message(message, recipient)
            
    async def _handle_location_update(self, websocket: WebSocket, user_id: str, data: dict):
        """Handle driver location update."""
        location = data.get("location")
        if location:
            # Store location in Redis
            if self.manager.redis:
                await self.manager.redis.setex(
                    f"driver:{user_id}:location",
                    300,  # 5 minute expiry
                    json.dumps(location)
                )
                
            # Broadcast to relevant users (e.g., customers tracking delivery)
            message = {
                "type": "driver_location",
                "driver_id": user_id,
                "location": location,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get customers tracking this driver
            if self.manager.redis:
                tracking_customers = await self.manager.redis.smembers(f"driver:{user_id}:trackers")
                for customer_id in tracking_customers:
                    await self.manager.send_personal_message(message, customer_id.decode())
                    
    async def _handle_order_update(self, websocket: WebSocket, user_id: str, data: dict):
        """Handle order status update."""
        order_id = data.get("order_id")
        status = data.get("status")
        
        if order_id and status:
            message = {
                "type": "order_status",
                "order_id": order_id,
                "status": status,
                "updated_by": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Notify relevant users
            if self.manager.redis:
                # Get order details to find customer
                order_data = await self.manager.redis.get(f"order:{order_id}")
                if order_data:
                    order = json.loads(order_data)
                    customer_id = order.get("customer_id")
                    if customer_id:
                        await self.manager.send_personal_message(message, customer_id)
                        
                # Notify office staff
                await self.manager.broadcast_to_role(message, "OFFICE_STAFF")