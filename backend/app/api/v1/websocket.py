from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, Set, List, Optional
from datetime import datetime
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import decode_access_token
from app.models.user import User

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        # Active connections by user_id
        self.active_connections: Dict[int, WebSocket] = {}
        # User roles for authorization
        self.user_roles: Dict[int, str] = {}
        # Topic subscriptions
        self.subscriptions: Dict[str, Set[int]] = {
            "orders": set(),
            "routes": set(),
            "predictions": set(),
            "drivers": set(),
            "notifications": set()
        }
    
    async def connect(self, websocket: WebSocket, user_id: int, role: str):
        """Connect a user to WebSocket"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_roles[user_id] = role
        
        # Auto-subscribe based on role
        if role in ["super_admin", "manager"]:
            # Managers see everything
            for topic in self.subscriptions:
                self.subscriptions[topic].add(user_id)
        elif role == "office_staff":
            # Office staff see orders, routes, predictions
            self.subscriptions["orders"].add(user_id)
            self.subscriptions["routes"].add(user_id)
            self.subscriptions["predictions"].add(user_id)
            self.subscriptions["notifications"].add(user_id)
        elif role == "driver":
            # Drivers see routes and driver updates
            self.subscriptions["routes"].add(user_id)
            self.subscriptions["drivers"].add(user_id)
            self.subscriptions["notifications"].add(user_id)
        
        # Send connection success message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "role": role,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def disconnect(self, user_id: int):
        """Disconnect a user"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            del self.user_roles[user_id]
            
            # Remove from all subscriptions
            for topic in self.subscriptions:
                self.subscriptions[topic].discard(user_id)
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                print(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast_to_topic(self, topic: str, message: dict):
        """Broadcast message to all subscribers of a topic"""
        if topic not in self.subscriptions:
            return
        
        disconnected_users = []
        for user_id in self.subscriptions[topic]:
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to user {user_id}: {e}")
                    disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)
    
    async def broadcast_to_role(self, role: str, message: dict):
        """Broadcast message to all users with specific role"""
        disconnected_users = []
        for user_id, user_role in self.user_roles.items():
            if user_role == role and user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to user {user_id}: {e}")
                    disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected users"""
        disconnected_users = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to user {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)


# Global connection manager instance
manager = ConnectionManager()


async def get_current_ws_user(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
) -> Optional[User]:
    """Authenticate WebSocket connection"""
    if not token:
        # Try to get token from query params
        token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    
    try:
        # Decode token
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        
        # Get user from database by username
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        
        return user
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_async_session)
):
    """Main WebSocket endpoint for real-time updates"""
    # Authenticate user
    user = await get_current_ws_user(websocket, db=db)
    if not user:
        return
    
    # Connect user
    await manager.connect(websocket, user.id, user.role)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "ping":
                # Respond to ping
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif message_type == "subscribe":
                # Subscribe to additional topics
                topic = data.get("topic")
                if topic in manager.subscriptions:
                    manager.subscriptions[topic].add(user.id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": topic,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif message_type == "unsubscribe":
                # Unsubscribe from topic
                topic = data.get("topic")
                if topic in manager.subscriptions:
                    manager.subscriptions[topic].discard(user.id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "topic": topic,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif message_type == "driver_location":
                # Driver location update
                if user.role == "driver":
                    location_data = {
                        "type": "driver_location_update",
                        "driver_id": user.id,
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    # Broadcast to routes topic
                    await manager.broadcast_to_topic("routes", location_data)
            
            elif message_type == "delivery_status":
                # Delivery status update
                if user.role in ["driver", "office_staff", "manager", "super_admin"]:
                    status_data = {
                        "type": "delivery_status_update",
                        "order_id": data.get("order_id"),
                        "status": data.get("status"),
                        "updated_by": user.id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    # Broadcast to orders topic
                    await manager.broadcast_to_topic("orders", status_data)
            
    except WebSocketDisconnect:
        manager.disconnect(user.id)
    except Exception as e:
        print(f"WebSocket error for user {user.id}: {e}")
        manager.disconnect(user.id)


# Utility functions for sending notifications from other parts of the application

async def notify_order_update(order_id: int, status: str, details: dict = None):
    """Notify about order status update"""
    message = {
        "type": "order_update",
        "order_id": order_id,
        "status": status,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_to_topic("orders", message)


async def notify_route_update(route_id: int, update_type: str, details: dict = None):
    """Notify about route updates"""
    message = {
        "type": "route_update",
        "route_id": route_id,
        "update_type": update_type,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_to_topic("routes", message)


async def notify_prediction_ready(batch_id: str, summary: dict):
    """Notify when predictions are ready"""
    message = {
        "type": "prediction_ready",
        "batch_id": batch_id,
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_to_topic("predictions", message)


async def notify_driver_assigned(driver_id: int, route_id: int, details: dict = None):
    """Notify driver about route assignment"""
    message = {
        "type": "route_assigned",
        "route_id": route_id,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_personal_message(message, driver_id)


async def send_notification(user_id: int, title: str, message: str, priority: str = "normal"):
    """Send general notification to specific user"""
    notification = {
        "type": "notification",
        "title": title,
        "message": message,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_personal_message(notification, user_id)


async def broadcast_system_message(message: str, priority: str = "normal"):
    """Broadcast system message to all users"""
    system_message = {
        "type": "system_message",
        "message": message,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_to_all(system_message)