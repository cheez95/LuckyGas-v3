"""
Simple WebSocket manager for real-time updates
Replaces complex websocket_service.py with message queuing
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional

import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings

logger = logging.getLogger(__name__)


class SimpleWebSocketManager:
    """
    Minimal WebSocket manager for real-time updates.

    Features:
    - Direct WebSocket connections without complex routing
    - Optional Redis pub/sub for multi-instance support
    - Simple event broadcasting
    - No message queuing or priorities
    """

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.redis_client: Optional[redis.Redis] = None
        self._pubsub_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize Redis for cross-instance communication"""
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()

            # Subscribe to events channel
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("events")

            # Start listener in background
            self._pubsub_task = asyncio.create_task(self._redis_listener(pubsub))

            logger.info("WebSocket manager initialized with Redis pub/sub")

        except Exception as e:
            logger.warning(f"Redis not available, running in single-instance mode: {e}")
            self.redis_client = None

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """Accept WebSocket connection"""
        await websocket.accept()

        # Generate unique connection ID
        connection_id = f"{user_id}_{datetime.now().timestamp()}"
        self.connections[connection_id] = websocket

        # Send welcome message
        await websocket.send_json(
            {
                "type": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(f"WebSocket connected: {connection_id}")
        return connection_id

    async def disconnect(self, connection_id: str):
        """Remove connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")

    async def broadcast_event(self, event_type: str, data: dict):
        """
        Broadcast event to all connected clients.

        Args:
            event_type: Type of event (e.g., 'order_updated', 'driver_location')
            data: Event data to broadcast
        """
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        # Local broadcast to connected clients
        disconnected = []
        for conn_id, websocket in self.connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to {conn_id}: {e}")
                disconnected.append(conn_id)

        # Clean up disconnected clients
        for conn_id in disconnected:
            await self.disconnect(conn_id)

        # Publish to Redis for other instances
        if self.redis_client:
            try:
                await self.redis_client.publish("events", json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}")

    async def send_to_user(self, user_id: str, event_type: str, data: dict):
        """
        Send event to specific user's connections.

        Args:
            user_id: User ID to send to
            event_type: Type of event
            data: Event data
        """
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        # Find connections for this user
        user_connections = [
            (conn_id, ws)
            for conn_id, ws in self.connections.items()
            if conn_id.startswith(f"{user_id}_")
        ]

        # Send to user's connections
        for conn_id, websocket in user_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to {conn_id}: {e}")
                await self.disconnect(conn_id)

    async def _redis_listener(self, pubsub):
        """Listen for Redis pub/sub events"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Parse message
                        event_data = json.loads(message["data"])

                        # Broadcast to local connections
                        disconnected = []
                        for conn_id, websocket in self.connections.items():
                            try:
                                await websocket.send_json(event_data)
                            except:
                                disconnected.append(conn_id)

                        # Clean up disconnected
                        for conn_id in disconnected:
                            await self.disconnect(conn_id)

                    except json.JSONDecodeError:
                        logger.error(
                            f"Invalid JSON in Redis message: {message['data']}"
                        )
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")

        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
        finally:
            await pubsub.close()

    async def handle_message(self, connection_id: str, data: dict):
        """
        Handle incoming message from client.

        Args:
            connection_id: Connection that sent the message
            data: Message data
        """
        message_type = data.get("type")

        # Handle different message types
        if message_type == "ping":
            # Respond to ping
            if connection_id in self.connections:
                await self.connections[connection_id].send_json(
                    {"type": "pong", "timestamp": datetime.now().isoformat()}
                )

        elif message_type == "driver_location":
            # Broadcast driver location update
            await self.broadcast_event(
                "driver_location",
                {
                    "driver_id": data.get("driver_id"),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                    "heading": data.get("heading", 0),
                    "speed": data.get("speed", 0),
                },
            )

        else:
            logger.debug(f"Unknown message type: {message_type}")

    async def close(self):
        """Clean up resources"""
        # Close all connections
        for conn_id in list(self.connections.keys()):
            await self.disconnect(conn_id)

        # Cancel Redis listener
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()

        logger.info("WebSocket manager closed")


# Global instance
websocket_manager = SimpleWebSocketManager()


# Helper functions for common events
async def notify_order_updated(order_id: int, status: str, details: dict = None):
    """Notify about order status change"""
    await websocket_manager.broadcast_event(
        "order_updated",
        {"order_id": order_id, "status": status, "details": details or {}},
    )


async def notify_route_assigned(route_id: int, driver_id: int, details: dict = None):
    """Notify about route assignment"""
    await websocket_manager.broadcast_event(
        "route_assigned",
        {"route_id": route_id, "driver_id": driver_id, "details": details or {}},
    )


async def notify_driver_location(driver_id: int, lat: float, lng: float, **kwargs):
    """Notify about driver location update"""
    await websocket_manager.broadcast_event(
        "driver_location",
        {"driver_id": driver_id, "latitude": lat, "longitude": lng, **kwargs},
    )
