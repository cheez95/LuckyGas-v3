import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime
import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum

from app.core.config import settings
# from app.services.message_queue_service import message_queue, QueuePriority  # Removed during compaction

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types"""
    # Connection events
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    
    # Order events
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_ASSIGNED = "order.assigned"
    ORDER_DELIVERED = "order.delivered"
    ORDER_CANCELLED = "order.cancelled"
    
    # Route events
    ROUTE_CREATED = "route.created"
    ROUTE_UPDATED = "route.updated"
    ROUTE_ASSIGNED = "route.assigned"
    ROUTE_PUBLISHED = "route.published"
    ROUTE_STARTED = "route.started"
    ROUTE_COMPLETED = "route.completed"
    
    # Driver events
    DRIVER_LOCATION = "driver.location"
    DRIVER_STATUS = "driver.status"
    DRIVER_ARRIVED = "driver.arrived"
    
    # Customer events
    CUSTOMER_NOTIFICATION = "customer.notification"
    DELIVERY_UPDATE = "delivery.update"
    
    # System events
    PREDICTION_READY = "prediction.ready"
    MAINTENANCE_ALERT = "maintenance.alert"
    SYSTEM_NOTIFICATION = "system.notification"


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.connection_info: Dict[str, Dict[str, Any]] = {}  # connection_id -> info
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._background_tasks = set()
        
    async def initialize(self):
        """Initialize Redis connection for pub/sub"""
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            
            # Subscribe to all channels
            await self.pubsub.subscribe(
                "orders",
                "routes", 
                "drivers",
                "customers",
                "system"
            )
            
            # Start listening for messages
            task = asyncio.create_task(self._redis_listener())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            
            # Initialize message queue with delivery callback
            # Removed during compaction
            # await message_queue.initialize(self._deliver_queued_message)
            
            logger.info("WebSocket manager initialized with Redis pub/sub and message queue")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            # Continue without Redis (single instance mode)
    
    async def _redis_listener(self):
        """Listen for Redis pub/sub messages"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self._handle_redis_message(message)
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
    
    async def _handle_redis_message(self, message: Dict[str, Any]):
        """Handle message from Redis pub/sub"""
        try:
            channel = message["channel"]
            data = json.loads(message["data"])
            
            # Broadcast to relevant connections
            if "user_id" in data:
                await self.send_to_user(data["user_id"], data)
            elif "role" in data:
                await self.send_to_role(data["role"], data)
            else:
                await self.broadcast(data, channel)
                
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")
    
    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str,
        role: str
    ):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Store connection info
        self.connection_info[connection_id] = {
            "user_id": user_id,
            "role": role,
            "connected_at": datetime.now(),
            "websocket": websocket
        }
        
        # Add to active connections by role
        if role not in self.active_connections:
            self.active_connections[role] = set()
        self.active_connections[role].add(websocket)
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": EventType.CONNECT,
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Publish connection event
        await self.publish_event("system", {
            "type": EventType.CONNECT,
            "user_id": user_id,
            "role": role
        })
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_id}, role: {role})")
    
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""
        if connection_id not in self.connection_info:
            return
        
        info = self.connection_info[connection_id]
        websocket = info["websocket"]
        user_id = info["user_id"]
        role = info["role"]
        
        # Remove from active connections
        if role in self.active_connections:
            self.active_connections[role].discard(websocket)
        
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove connection info
        del self.connection_info[connection_id]
        
        # Publish disconnection event
        await self.publish_event("system", {
            "type": EventType.DISCONNECT,
            "user_id": user_id,
            "role": role
        })
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send message to a specific connection"""
        if connection_id not in self.connection_info:
            return
        
        websocket = self.connection_info[connection_id]["websocket"]
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to connection {connection_id}: {e}")
            await self.disconnect(connection_id)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to all connections of a specific user"""
        if user_id not in self.user_connections:
            return
        
        for connection_id in self.user_connections[user_id].copy():
            await self.send_to_connection(connection_id, message)
    
    async def send_to_role(self, role: str, message: Dict[str, Any]):
        """Send message to all connections with a specific role"""
        if role not in self.active_connections:
            return
        
        disconnected = []
        for websocket in self.active_connections[role].copy():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to role {role}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.active_connections[role].discard(websocket)
    
    async def broadcast(self, message: Dict[str, Any], channel: Optional[str] = None):
        """Broadcast message to all connections or specific channel"""
        if channel:
            # Send to specific role/channel
            await self.send_to_role(channel, message)
        else:
            # Send to all connections
            for role in self.active_connections:
                await self.send_to_role(role, message)
    
    async def publish_event(
        self, 
        channel: str, 
        event_data: Dict[str, Any],
        # priority parameter removed during compaction
        use_queue: bool = False,
        target_user_id: Optional[str] = None,
        target_role: Optional[str] = None
    ):
        """Publish event to Redis for cross-instance broadcasting"""
        event_data["timestamp"] = datetime.now().isoformat()
        
        # Removed message queue during compaction - use Redis directly
        if self.redis_client:
            try:
                await self.redis_client.publish(channel, json.dumps(event_data))
            except Exception as e:
                logger.error(f"Error publishing to Redis: {e}")
                # Fallback to direct broadcast on Redis failure
                await self.broadcast(event_data, channel)
        else:
            # Fallback to direct broadcast (single instance)
            await self.broadcast(event_data, channel)
    
    async def _deliver_queued_message(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        target_user_id: Optional[str] = None,
        target_role: Optional[str] = None
    ):
        """Delivery callback for message queue"""
        if target_user_id:
            # Deliver to specific user
            await self.send_to_user(target_user_id, data)
        elif target_role:
            # Deliver to specific role
            await self.send_to_role(target_role, data)
        else:
            # Broadcast to channel
            await self.broadcast(data, channel)
    
    async def handle_message(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        if connection_id not in self.connection_info:
            return
        
        info = self.connection_info[connection_id]
        message_type = message.get("type")
        
        # Handle heartbeat
        if message_type == EventType.HEARTBEAT:
            await self.send_to_connection(connection_id, {
                "type": EventType.HEARTBEAT,
                "timestamp": datetime.now().isoformat()
            })
            return
        
        # Handle driver location update
        if message_type == EventType.DRIVER_LOCATION and info["role"] == "driver":
            await self.handle_driver_location(info["user_id"], message)
        
        # Handle delivery confirmation
        elif message_type == "delivery.confirmed" and info["role"] == "driver":
            await self.handle_delivery_confirmation(info["user_id"], message)
        
        # Handle generic order updates
        elif message_type == "order_update":
            await self.notify_order_update(
                message.get("order_id"),
                message.get("status", "updated"),
                details=message.get("details", {})
            )
        
        # Handle route updates
        elif message_type == "route_update":
            await self.notify_route_update(
                message.get("route_id"),
                message.get("status", "updated"),
                details=message.get("details", {})
            )
        
        # Add more message handlers as needed
    
    async def handle_driver_location(self, driver_id: str, message: Dict[str, Any]):
        """Handle driver location update"""
        location_data = {
            "type": EventType.DRIVER_LOCATION,
            "driver_id": driver_id,
            "latitude": message.get("latitude"),
            "longitude": message.get("longitude"),
            "speed": message.get("speed", 0),
            "heading": message.get("heading", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in Redis for persistence
        if self.redis_client:
            await self.redis_client.setex(
                f"driver_location:{driver_id}",
                300,  # 5 minute TTL
                json.dumps(location_data)
            )
        
        # Broadcast to relevant users (office staff, customers with active orders)
        await self.publish_event("drivers", location_data)
    
    async def notify_order_update(self, order_id: str, status: str, **kwargs):
        """Send order update notification"""
        event_data = {
            "type": EventType.ORDER_UPDATED,
            "order_id": order_id,
            "status": status,
            **kwargs
        }
        # Use message queue for critical order updates
        use_queue = status in ["delivered", "cancelled", "assigned"]
        # priority removed during compaction
        
        await self.publish_event(
            "orders", 
            event_data,
            use_queue=use_queue
        )
    
    async def notify_route_update(self, route_id: str, status: str, **kwargs):
        """Send route update notification"""
        event_data = {
            "type": EventType.ROUTE_UPDATED,
            "route_id": route_id,
            "status": status,
            **kwargs
        }
        await self.publish_event("routes", event_data)
    
    async def notify_customer(self, customer_id: str, notification: Dict[str, Any]):
        """Send notification to customer"""
        event_data = {
            "type": EventType.CUSTOMER_NOTIFICATION,
            "user_id": customer_id,
            **notification
        }
        # Always use message queue for customer notifications to ensure delivery
        # priority removed during compaction
        
        await self.publish_event(
            "customers", 
            event_data,
            use_queue=True,
            target_user_id=customer_id
        )
    
    async def handle_delivery_confirmation(self, driver_id: str, message: Dict[str, Any]):
        """Handle delivery confirmation from QR code scan or manual entry"""
        confirmation_data = {
            "type": EventType.ORDER_DELIVERED,
            "driver_id": driver_id,
            "order_id": message.get("order_id"),
            "customer_id": message.get("customer_id"),
            "confirmed_at": message.get("confirmed_at"),
            "confirmation_type": message.get("confirmation_type", "unknown"),
            "cylinder_serial": message.get("cylinder_serial")
        }
        
        # Update order status in database (to be implemented)
        # For now, just broadcast the event
        
        # Notify office staff
        await self.send_to_role("office_staff", confirmation_data)
        await self.send_to_role("manager", confirmation_data)
        
        # Notify the specific customer
        if customer_id := message.get("customer_id"):
            await self.send_to_user(customer_id, {
                "type": EventType.DELIVERY_UPDATE,
                "status": "delivered",
                "order_id": message.get("order_id"),
                "message": "您的瓦斯已送達，感謝您的訂購！",
                "timestamp": datetime.now().isoformat()
            })
        
        # Broadcast to all relevant channels
        await self.publish_event("orders", confirmation_data)
        
        logger.info(f"Delivery confirmed for order {message.get('order_id')} by driver {driver_id}")
    
    async def close(self):
        """Close all connections and cleanup"""
        # Close all WebSocket connections
        for connection_id in list(self.connection_info.keys()):
            await self.disconnect(connection_id)
        
        # Shutdown message queue service
        # Removed during compaction
        # await message_queue.shutdown()
        
        # Close Redis connections
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()


# Global WebSocket manager instance
websocket_manager = WebSocketManager()