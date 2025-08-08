"""
WebSocketManager Class for connection management and message handling.
Eliminates ~300 lines of duplicate WebSocket code.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any, Callable, TypedDict
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""
    # System messages
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    
    # Business messages
    ORDER_UPDATE = "order_update"
    ROUTE_UPDATE = "route_update"
    DELIVERY_UPDATE = "delivery_update"
    DRIVER_LOCATION = "driver_location"
    NOTIFICATION = "notification"
    ANALYTICS_UPDATE = "analytics_update"
    CHAT_MESSAGE = "chat_message"


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


@dataclass
class WebSocketMessage:
    """Standardized WebSocket message structure."""
    type: str
    data: Any
    timestamp: str = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class ConnectionInfo:
    """Information about a WebSocket connection."""
    
    def __init__(
        self,
        websocket: WebSocket,
        user_id: str,
        client_id: str,
        roles: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.websocket = websocket
        self.user_id = user_id
        self.client_id = client_id
        self.roles = roles or []
        self.metadata = metadata or {}
        self.state = ConnectionState.CONNECTING
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.last_pong = datetime.utcnow()
        self.message_count = 0
        self.error_count = 0
        self.subscriptions: Set[str] = set()
    
    @property
    def is_alive(self) -> bool:
        """Check if connection is still alive."""
        return (
            self.state == ConnectionState.CONNECTED and
            self.websocket.client_state == WebSocketState.CONNECTED
        )
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_ping = datetime.utcnow()


class WebSocketManager:
    """
    Centralized WebSocket connection manager.
    Handles connection lifecycle, message routing, and error recovery.
    """
    
    def __init__(
        self,
        ping_interval: int = 30,
        pong_timeout: int = 10,
        max_connections_per_user: int = 5,
        enable_message_history: bool = True,
        history_size: int = 100
    ):
        self.connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.room_connections: Dict[str, Set[str]] = {}
        self.ping_interval = ping_interval
        self.pong_timeout = pong_timeout
        self.max_connections_per_user = max_connections_per_user
        self.enable_message_history = enable_message_history
        self.history_size = history_size
        self.message_history: List[WebSocketMessage] = []
        self.message_handlers: Dict[str, List[Callable]] = {}
        self._ping_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        client_id: str,
        roles: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> ConnectionInfo:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            user_id: User identifier
            client_id: Unique client identifier
            roles: User roles for authorization
            metadata: Additional connection metadata
        
        Returns:
            ConnectionInfo object
        
        Raises:
            ConnectionError: If connection limit exceeded
        """
        async with self._lock:
            # Check connection limit
            if user_id in self.user_connections:
                if len(self.user_connections[user_id]) >= self.max_connections_per_user:
                    # Disconnect oldest connection
                    oldest_client_id = min(self.user_connections[user_id])
                    await self.disconnect(oldest_client_id, "Connection limit exceeded")
            
            # Accept WebSocket connection
            await websocket.accept()
            
            # Create connection info
            connection = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                client_id=client_id,
                roles=roles,
                metadata=metadata
            )
            connection.state = ConnectionState.CONNECTED
            
            # Register connection
            self.connections[client_id] = connection
            
            # Track user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(client_id)
            
            # Send connection confirmation
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.CONNECT,
                    data={"status": "connected", "client_id": client_id}
                )
            )
            
            # Start ping task if not running
            if not self._ping_task or self._ping_task.done():
                self._ping_task = asyncio.create_task(self._ping_loop())
            
            logger.info(f"WebSocket connected: user={user_id}, client={client_id}")
            return connection
    
    async def disconnect(
        self,
        client_id: str,
        reason: str = "Normal disconnect"
    ):
        """
        Disconnect and unregister a WebSocket connection.
        
        Args:
            client_id: Client identifier
            reason: Disconnect reason
        """
        async with self._lock:
            if client_id not in self.connections:
                return
            
            connection = self.connections[client_id]
            connection.state = ConnectionState.DISCONNECTING
            
            try:
                # Send disconnect message
                await self.send_to_client(
                    client_id,
                    WebSocketMessage(
                        type=MessageType.DISCONNECT,
                        data={"reason": reason}
                    )
                )
                
                # Close WebSocket
                if connection.websocket.client_state == WebSocketState.CONNECTED:
                    await connection.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            
            # Remove from tracking
            del self.connections[client_id]
            
            # Remove from user connections
            if connection.user_id in self.user_connections:
                self.user_connections[connection.user_id].discard(client_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]
            
            # Remove from rooms
            for room_id in list(self.room_connections.keys()):
                self.room_connections[room_id].discard(client_id)
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]
            
            connection.state = ConnectionState.DISCONNECTED
            logger.info(f"WebSocket disconnected: client={client_id}, reason={reason}")
    
    async def send_to_client(
        self,
        client_id: str,
        message: WebSocketMessage
    ) -> bool:
        """
        Send message to specific client.
        
        Args:
            client_id: Client identifier
            message: Message to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        if client_id not in self.connections:
            logger.warning(f"Client {client_id} not found")
            return False
        
        connection = self.connections[client_id]
        
        try:
            if connection.is_alive:
                await connection.websocket.send_text(message.to_json())
                connection.message_count += 1
                
                # Store in history
                if self.enable_message_history:
                    self._add_to_history(message)
                
                return True
            else:
                logger.warning(f"Client {client_id} connection not alive")
                await self.disconnect(client_id, "Connection not alive")
                return False
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            connection.error_count += 1
            
            # Disconnect if too many errors
            if connection.error_count > 5:
                await self.disconnect(client_id, "Too many errors")
            
            return False
    
    async def send_to_user(
        self,
        user_id: str,
        message: WebSocketMessage
    ) -> int:
        """
        Send message to all connections of a user.
        
        Args:
            user_id: User identifier
            message: Message to send
        
        Returns:
            Number of successful sends
        """
        if user_id not in self.user_connections:
            return 0
        
        success_count = 0
        for client_id in list(self.user_connections[user_id]):
            if await self.send_to_client(client_id, message):
                success_count += 1
        
        return success_count
    
    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude: Set[str] = None
    ) -> int:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message to broadcast
            exclude: Set of client IDs to exclude
        
        Returns:
            Number of successful sends
        """
        exclude = exclude or set()
        success_count = 0
        
        for client_id in list(self.connections.keys()):
            if client_id not in exclude:
                if await self.send_to_client(client_id, message):
                    success_count += 1
        
        return success_count
    
    async def send_to_room(
        self,
        room_id: str,
        message: WebSocketMessage,
        exclude: Set[str] = None
    ) -> int:
        """
        Send message to all clients in a room.
        
        Args:
            room_id: Room identifier
            message: Message to send
            exclude: Set of client IDs to exclude
        
        Returns:
            Number of successful sends
        """
        if room_id not in self.room_connections:
            return 0
        
        exclude = exclude or set()
        success_count = 0
        
        for client_id in list(self.room_connections[room_id]):
            if client_id not in exclude:
                if await self.send_to_client(client_id, message):
                    success_count += 1
        
        return success_count
    
    async def join_room(self, client_id: str, room_id: str):
        """
        Add client to a room.
        
        Args:
            client_id: Client identifier
            room_id: Room identifier
        """
        if client_id not in self.connections:
            return
        
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        
        self.room_connections[room_id].add(client_id)
        self.connections[client_id].subscriptions.add(room_id)
        
        logger.info(f"Client {client_id} joined room {room_id}")
    
    async def leave_room(self, client_id: str, room_id: str):
        """
        Remove client from a room.
        
        Args:
            client_id: Client identifier
            room_id: Room identifier
        """
        if room_id in self.room_connections:
            self.room_connections[room_id].discard(client_id)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]
        
        if client_id in self.connections:
            self.connections[client_id].subscriptions.discard(room_id)
        
        logger.info(f"Client {client_id} left room {room_id}")
    
    async def handle_message(
        self,
        client_id: str,
        message: str
    ):
        """
        Handle incoming message from client.
        
        Args:
            client_id: Client identifier
            message: Raw message string
        """
        try:
            # Parse message
            msg = WebSocketMessage.from_json(message)
            
            # Update activity
            if client_id in self.connections:
                self.connections[client_id].update_activity()
            
            # Handle system messages
            if msg.type == MessageType.PING:
                await self.send_to_client(
                    client_id,
                    WebSocketMessage(type=MessageType.PONG, data={})
                )
                return
            
            # Call registered handlers
            if msg.type in self.message_handlers:
                for handler in self.message_handlers[msg.type]:
                    try:
                        await handler(client_id, msg)
                    except Exception as e:
                        logger.error(f"Handler error for {msg.type}: {e}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from client {client_id}: {e}")
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.ERROR,
                    data={"error": "Invalid message format"}
                )
            )
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
    
    def register_handler(
        self,
        message_type: str,
        handler: Callable
    ):
        """
        Register a message handler.
        
        Args:
            message_type: Message type to handle
            handler: Async function to handle message
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
    
    async def listen(self, websocket: WebSocket, client_id: str):
        """
        Listen for messages from a client.
        
        Args:
            websocket: WebSocket connection
            client_id: Client identifier
        """
        try:
            while True:
                message = await websocket.receive_text()
                await self.handle_message(client_id, message)
        except WebSocketDisconnect:
            await self.disconnect(client_id, "Client disconnected")
        except Exception as e:
            logger.error(f"Error in listen loop for {client_id}: {e}")
            await self.disconnect(client_id, f"Error: {str(e)}")
    
    async def _ping_loop(self):
        """
        Send periodic ping messages to check connection health.
        """
        while self.connections:
            try:
                await asyncio.sleep(self.ping_interval)
                
                # Check all connections
                for client_id in list(self.connections.keys()):
                    connection = self.connections.get(client_id)
                    if not connection:
                        continue
                    
                    # Check if pong timeout exceeded
                    time_since_pong = (
                        datetime.utcnow() - connection.last_pong
                    ).total_seconds()
                    
                    if time_since_pong > self.ping_interval + self.pong_timeout:
                        logger.warning(f"Ping timeout for client {client_id}")
                        await self.disconnect(client_id, "Ping timeout")
                    else:
                        # Send ping
                        await self.send_to_client(
                            client_id,
                            WebSocketMessage(type=MessageType.PING, data={})
                        )
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")
    
    def _add_to_history(self, message: WebSocketMessage):
        """Add message to history with size limit."""
        self.message_history.append(message)
        if len(self.message_history) > self.history_size:
            self.message_history.pop(0)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.connections),
            "total_users": len(self.user_connections),
            "total_rooms": len(self.room_connections),
            "connections_by_state": {
                state.value: sum(
                    1 for c in self.connections.values()
                    if c.state == state
                )
                for state in ConnectionState
            },
            "message_history_size": len(self.message_history),
        }
    
    async def cleanup(self):
        """Clean up all connections and resources."""
        # Cancel ping task
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        
        # Disconnect all clients
        for client_id in list(self.connections.keys()):
            await self.disconnect(client_id, "Server shutdown")
        
        # Clear all data
        self.connections.clear()
        self.user_connections.clear()
        self.room_connections.clear()
        self.message_history.clear()
        
        logger.info("WebSocketManager cleanup completed")


# Global instance for singleton pattern
_manager_instance: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = WebSocketManager()
    return _manager_instance