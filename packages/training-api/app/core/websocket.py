from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    """Manages WebSocket connections for real-time features."""
    
    def __init__(self):
        # Active connections: {user_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # User metadata: {user_id: {department, role, etc}}
        self.user_metadata: Dict[str, dict] = {}
        # Room subscriptions: {room_name: Set[user_id]}
        self.rooms: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, metadata: dict = None):
        """Accept WebSocket connection and store it."""
        await websocket.accept()
        
        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Store user metadata
        if metadata:
            self.user_metadata[user_id] = metadata
        
        # Send connection confirmation
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat()
            },
            user_id
        )
        
        # Join default rooms based on metadata
        if metadata:
            if "department" in metadata:
                await self.join_room(user_id, f"dept:{metadata['department']}")
            if "role" in metadata:
                await self.join_room(user_id, f"role:{metadata['role']}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                # Clean up metadata and room subscriptions
                if user_id in self.user_metadata:
                    del self.user_metadata[user_id]
                # Remove from all rooms
                for room_users in self.rooms.values():
                    room_users.discard(user_id)
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user (all their connections)."""
        if user_id in self.active_connections:
            message_text = json.dumps(message, ensure_ascii=False)
            # Send to all connections of the user
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_text)
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected websockets
            for conn in disconnected:
                self.active_connections[user_id].remove(conn)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected users."""
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(message_text)
                except:
                    disconnected.append((user_id, connection))
        
        # Clean up disconnected websockets
        for user_id, conn in disconnected:
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(conn)
    
    async def broadcast_to_room(self, message: dict, room_name: str):
        """Broadcast message to all users in a specific room."""
        if room_name not in self.rooms:
            return
        
        for user_id in self.rooms[room_name]:
            await self.send_personal_message(message, user_id)
    
    async def broadcast_to_departments(self, message: dict, departments: List[str]):
        """Broadcast message to users in specific departments."""
        for dept in departments:
            await self.broadcast_to_room(message, f"dept:{dept}")
    
    async def broadcast_to_role(self, message: dict, role: str):
        """Broadcast message to users with specific role."""
        await self.broadcast_to_room(message, f"role:{role}")
    
    async def join_room(self, user_id: str, room_name: str):
        """Add user to a room."""
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(user_id)
        
        # Notify user
        await self.send_personal_message(
            {
                "type": "room_joined",
                "room": room_name,
                "timestamp": datetime.utcnow().isoformat()
            },
            user_id
        )
    
    async def leave_room(self, user_id: str, room_name: str):
        """Remove user from a room."""
        if room_name in self.rooms:
            self.rooms[room_name].discard(user_id)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
        
        # Notify user
        await self.send_personal_message(
            {
                "type": "room_left",
                "room": room_name,
                "timestamp": datetime.utcnow().isoformat()
            },
            user_id
        )
    
    async def send_training_update(self, user_id: str, update_type: str, data: dict):
        """Send training-specific updates to user."""
        message = {
            "type": "training_update",
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(message, user_id)
    
    async def send_progress_update(self, user_id: str, course_id: str, module_id: str, progress: float):
        """Send progress update to user."""
        await self.send_training_update(
            user_id,
            "progress",
            {
                "course_id": course_id,
                "module_id": module_id,
                "progress_percentage": progress
            }
        )
    
    async def send_achievement_unlocked(self, user_id: str, achievement: dict):
        """Send achievement unlocked notification."""
        await self.send_training_update(
            user_id,
            "achievement_unlocked",
            achievement
        )
    
    async def send_leaderboard_update(self, leaderboard_data: dict):
        """Broadcast leaderboard update to all users."""
        message = {
            "type": "leaderboard_update",
            "data": leaderboard_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message)
    
    def get_online_users(self) -> List[str]:
        """Get list of currently online users."""
        return list(self.active_connections.keys())
    
    def get_online_count(self) -> int:
        """Get count of online users."""
        return len(self.active_connections)
    
    def get_room_users(self, room_name: str) -> List[str]:
        """Get list of users in a specific room."""
        return list(self.rooms.get(room_name, set()))
    
    async def handle_heartbeat(self, websocket: WebSocket, user_id: str):
        """Handle heartbeat to keep connection alive."""
        try:
            # Send ping every 30 seconds
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})
        except:
            # Connection closed
            self.disconnect(websocket, user_id)


# Global connection manager instance
manager = ConnectionManager()


# WebSocket endpoint handler
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str):
    """WebSocket endpoint for real-time communication."""
    # TODO: Validate token and get user metadata
    metadata = {
        "department": "office",  # Get from user data
        "role": "staff"  # Get from user data
    }
    
    await manager.connect(websocket, user_id, metadata)
    
    # Start heartbeat task
    heartbeat_task = asyncio.create_task(manager.handle_heartbeat(websocket, user_id))
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "pong":
                # Client responded to ping
                continue
            
            elif message.get("type") == "join_room":
                room_name = message.get("room")
                if room_name:
                    await manager.join_room(user_id, room_name)
            
            elif message.get("type") == "leave_room":
                room_name = message.get("room")
                if room_name:
                    await manager.leave_room(user_id, room_name)
            
            elif message.get("type") == "progress_update":
                # Handle progress update from client
                # This would typically update the database and broadcast to relevant users
                pass
            
            else:
                # Echo back unknown message types
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Unknown message type",
                        "original": message
                    },
                    user_id
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        heartbeat_task.cancel()
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
        heartbeat_task.cancel()