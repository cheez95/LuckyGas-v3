"""
Socket.IO implementation for real-time communication
Replaces WebSocket with more robust Socket.IO protocol
"""
import asyncio
from typing import Dict, Set, List, Optional, Any
from datetime import datetime
import socketio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.database import async_session_maker
from app.core.security import decode_access_token
from app.core.metrics import background_tasks_counter
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# Get CORS origins from settings
cors_origins = settings.get_all_cors_origins()
if settings.is_development():
    # Add wildcard for development convenience
    cors_origins.append("http://localhost:*")
    cors_origins.append("http://127.0.0.1:*")

# Create async Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=cors_origins,  # Use settings-based CORS
    logger=logger,
    engineio_logger=settings.is_development(),  # Enable debug logging in development
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6,  # 1MB max message size
    async_handlers=True,
    namespaces=['/']  # Default namespace
)

# Create ASGI app
socket_app = socketio.ASGIApp(
    sio,
    other_asgi_app=None,  # Will be attached to FastAPI
    socketio_path='/socket.io'
)


class ConnectionManager:
    """Enhanced connection manager with rooms and acknowledgments"""
    
    def __init__(self):
        # Active sessions by session_id
        self.sessions: Dict[str, Dict[str, Any]] = {}
        # User to session mapping
        self.user_sessions: Dict[int, Set[str]] = {}
        # Room subscriptions
        self.rooms = {
            "orders": "orders_room",
            "routes": "routes_room",
            "predictions": "predictions_room",
            "drivers": "drivers_room",
            "notifications": "notifications_room"
        }
    
    async def connect(self, sid: str, user_id: int, role: str, username: str):
        """Register a new connection"""
        self.sessions[sid] = {
            "user_id": user_id,
            "role": role,
            "username": username,
            "connected_at": datetime.utcnow()
        }
        
        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(sid)
        
        # Auto-join rooms based on role
        await self._auto_join_rooms(sid, role)
        
        # Log connection
        logger.info(f"User {username} (ID: {user_id}) connected with session {sid}")
        
        # Track metrics
        background_tasks_counter.labels(
            task_type="socketio_connection",
            status="connected"
        ).inc()
    
    async def _auto_join_rooms(self, sid: str, role: str):
        """Auto-join rooms based on user role"""
        if role in ["super_admin", "manager"]:
            # Join all rooms
            for room in self.rooms.values():
                await sio.enter_room(sid, room)
        elif role == "office_staff":
            # Join specific rooms
            await sio.enter_room(sid, self.rooms["orders"])
            await sio.enter_room(sid, self.rooms["routes"])
            await sio.enter_room(sid, self.rooms["predictions"])
            await sio.enter_room(sid, self.rooms["notifications"])
        elif role == "driver":
            # Driver specific rooms
            await sio.enter_room(sid, self.rooms["routes"])
            await sio.enter_room(sid, self.rooms["drivers"])
            await sio.enter_room(sid, self.rooms["notifications"])
        else:
            # Customer - notifications only
            await sio.enter_room(sid, self.rooms["notifications"])
    
    async def disconnect(self, sid: str):
        """Handle disconnection"""
        if sid not in self.sessions:
            return
        
        session = self.sessions[sid]
        user_id = session["user_id"]
        username = session["username"]
        
        # Remove session
        del self.sessions[sid]
        
        # Remove from user sessions
        if user_id in self.user_sessions:
            self.user_sessions[user_id].discard(sid)
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]
        
        # Leave all rooms (Socket.IO handles this automatically)
        
        # Log disconnection
        logger.info(f"User {username} (ID: {user_id}) disconnected session {sid}")
        
        # Track metrics
        background_tasks_counter.labels(
            task_type="socketio_connection",
            status="disconnected"
        ).inc()
    
    def get_user_sessions(self, user_id: int) -> List[str]:
        """Get all active sessions for a user"""
        return list(self.user_sessions.get(user_id, []))
    
    def get_session_info(self, sid: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        return self.sessions.get(sid)
    
    def is_user_online(self, user_id: int) -> bool:
        """Check if user has any active sessions"""
        return user_id in self.user_sessions and len(self.user_sessions[user_id]) > 0


# Global connection manager
connection_manager = ConnectionManager()


# Socket.IO event handlers

@sio.event
async def connect(sid, environ, auth):
    """Handle new connections"""
    try:
        # Extract token from auth or query params
        token = None
        if auth and isinstance(auth, dict):
            token = auth.get('token')
        
        if not token:
            # Try query params
            query_string = environ.get('QUERY_STRING', '')
            for param in query_string.split('&'):
                if param.startswith('token='):
                    token = param.split('=')[1]
                    break
        
        if not token:
            logger.warning(f"Connection attempt without token from {sid}")
            await sio.disconnect(sid)
            return False
        
        # Decode token and get user
        try:
            payload = decode_access_token(token)
            username = payload.get("sub")
            if not username:
                raise ValueError("Invalid token payload")
        except Exception as e:
            logger.warning(f"Invalid token from {sid}: {e}")
            await sio.disconnect(sid)
            return False
        
        # Get user from database
        async with async_session_maker() as db:
            result = await db.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                logger.warning(f"Invalid user {username} from {sid}")
                await sio.disconnect(sid)
                return False
        
        # Register connection
        await connection_manager.connect(sid, user.id, user.role, user.username)
        
        # Send connection success
        await sio.emit('connected', {
            'status': 'success',
            'user_id': user.id,
            'role': user.role,
            'timestamp': datetime.utcnow().isoformat()
        }, room=sid)
        
        return True
        
    except Exception as e:
        logger.error(f"Connection error for {sid}: {e}")
        await sio.disconnect(sid)
        return False


@sio.event
async def disconnect(sid):
    """Handle disconnections"""
    await connection_manager.disconnect(sid)


@sio.event
async def ping(sid):
    """Handle ping for connection keep-alive"""
    await sio.emit('pong', {
        'timestamp': datetime.utcnow().isoformat()
    }, room=sid)


@sio.event
async def subscribe(sid, data):
    """Subscribe to a topic/room"""
    session = connection_manager.get_session_info(sid)
    if not session:
        return {'status': 'error', 'message': 'Invalid session'}
    
    topic = data.get('topic')
    if topic not in connection_manager.rooms:
        return {'status': 'error', 'message': 'Invalid topic'}
    
    room = connection_manager.rooms[topic]
    await sio.enter_room(sid, room)
    
    logger.info(f"Session {sid} subscribed to {topic}")
    
    return {
        'status': 'success',
        'topic': topic,
        'timestamp': datetime.utcnow().isoformat()
    }


@sio.event
async def unsubscribe(sid, data):
    """Unsubscribe from a topic/room"""
    session = connection_manager.get_session_info(sid)
    if not session:
        return {'status': 'error', 'message': 'Invalid session'}
    
    topic = data.get('topic')
    if topic not in connection_manager.rooms:
        return {'status': 'error', 'message': 'Invalid topic'}
    
    room = connection_manager.rooms[topic]
    await sio.leave_room(sid, room)
    
    logger.info(f"Session {sid} unsubscribed from {topic}")
    
    return {
        'status': 'success',
        'topic': topic,
        'timestamp': datetime.utcnow().isoformat()
    }


@sio.event
async def driver_location(sid, data):
    """Handle driver location updates"""
    session = connection_manager.get_session_info(sid)
    if not session or session['role'] != 'driver':
        return {'status': 'error', 'message': 'Unauthorized'}
    
    location_data = {
        'type': 'driver_location_update',
        'driver_id': session['user_id'],
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude'),
        'accuracy': data.get('accuracy'),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Emit to routes room
    await sio.emit('location_update', location_data, 
                   room=connection_manager.rooms['routes'])
    
    # Store in cache for tracking
    # TODO: Implement Redis location tracking
    
    return {'status': 'success'}


@sio.event
async def delivery_status(sid, data):
    """Handle delivery status updates"""
    session = connection_manager.get_session_info(sid)
    if not session:
        return {'status': 'error', 'message': 'Invalid session'}
    
    # Check authorization
    allowed_roles = ['driver', 'office_staff', 'manager', 'super_admin']
    if session['role'] not in allowed_roles:
        return {'status': 'error', 'message': 'Unauthorized'}
    
    status_data = {
        'type': 'delivery_status_update',
        'order_id': data.get('order_id'),
        'status': data.get('status'),
        'notes': data.get('notes'),
        'updated_by': session['user_id'],
        'updated_by_name': session['username'],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Emit to orders room
    await sio.emit('order_update', status_data,
                   room=connection_manager.rooms['orders'])
    
    # TODO: Update database
    
    return {
        'status': 'success',
        'order_id': data.get('order_id')
    }


# Utility functions for sending notifications from other parts of the application

async def notify_order_update(order_id: int, status: str, details: dict = None):
    """Notify about order status update"""
    message = {
        'type': 'order_update',
        'order_id': order_id,
        'status': status,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    await sio.emit('order_update', message, 
                   room=connection_manager.rooms['orders'])


async def notify_route_update(route_id: int, update_type: str, details: dict = None):
    """Notify about route updates"""
    message = {
        'type': 'route_update',
        'route_id': route_id,
        'update_type': update_type,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    await sio.emit('route_update', message,
                   room=connection_manager.rooms['routes'])


async def notify_prediction_ready(batch_id: str, summary: dict):
    """Notify when predictions are ready"""
    message = {
        'type': 'prediction_ready',
        'batch_id': batch_id,
        'summary': summary,
        'timestamp': datetime.utcnow().isoformat()
    }
    await sio.emit('prediction_ready', message,
                   room=connection_manager.rooms['predictions'])


async def notify_driver_assigned(driver_id: int, route_id: int, details: dict = None):
    """Notify driver about route assignment"""
    message = {
        'type': 'route_assigned',
        'route_id': route_id,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Send to all driver's sessions
    sessions = connection_manager.get_user_sessions(driver_id)
    for sid in sessions:
        await sio.emit('route_assigned', message, room=sid)


async def send_notification(user_id: int, title: str, message: str, 
                          priority: str = 'normal', callback: bool = True):
    """Send notification to specific user with acknowledgment"""
    notification = {
        'type': 'notification',
        'title': title,
        'message': message,
        'priority': priority,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Send to all user's sessions
    sessions = connection_manager.get_user_sessions(user_id)
    
    if callback:
        # Send with callback to track delivery
        results = []
        for sid in sessions:
            try:
                result = await sio.call('notification', notification, 
                                      sid=sid, timeout=5)
                results.append({'sid': sid, 'acknowledged': True, 'result': result})
            except asyncio.TimeoutError:
                results.append({'sid': sid, 'acknowledged': False, 'error': 'timeout'})
        return results
    else:
        # Send without waiting for acknowledgment
        for sid in sessions:
            await sio.emit('notification', notification, room=sid)
        return len(sessions)


async def broadcast_system_message(message: str, priority: str = 'normal'):
    """Broadcast system message to all connected users"""
    system_message = {
        'type': 'system_message',
        'message': message,
        'priority': priority,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Emit to all connected clients
    await sio.emit('system_message', system_message)
    
    # Log broadcast
    logger.info(f"System message broadcasted: {message}")


async def get_online_users() -> List[Dict[str, Any]]:
    """Get list of currently online users"""
    online_users = []
    
    for user_id, sessions in connection_manager.user_sessions.items():
        if sessions:
            # Get first session info
            sid = next(iter(sessions))
            session_info = connection_manager.get_session_info(sid)
            if session_info:
                online_users.append({
                    'user_id': user_id,
                    'username': session_info['username'],
                    'role': session_info['role'],
                    'session_count': len(sessions),
                    'connected_at': session_info['connected_at'].isoformat()
                })
    
    return online_users


async def get_room_members(topic: str) -> List[str]:
    """Get all session IDs in a room"""
    if topic not in connection_manager.rooms:
        return []
    
    room = connection_manager.rooms[topic]
    return list(sio.rooms(room))


# Performance monitoring
@sio.on('*')
async def catch_all(event, sid, data):
    """Catch all events for monitoring"""
    # Log unknown events
    if event not in ['connect', 'disconnect', 'ping', 'subscribe', 
                     'unsubscribe', 'driver_location', 'delivery_status']:
        logger.warning(f"Unknown event '{event}' from {sid}: {data}")
    
    # Track metrics
    background_tasks_counter.labels(
        task_type=f"socketio_event_{event}",
        status="received"
    ).inc()