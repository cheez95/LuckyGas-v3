"""
E2E tests for WebSocket and real-time features (Sprint 2)
"""
import pytest
import asyncio
from typing import Dict, List
from httpx import AsyncClient
import socketio
from unittest.mock import AsyncMock, patch

from app.models.order import OrderStatus
from app.models.user import User
from app.models.customer import Customer


@pytest.mark.asyncio
class TestWebSocketRealtime:
    """Test real-time WebSocket functionality"""
    
    async def test_websocket_connection(self, authenticated_client: AsyncClient):
        """Test WebSocket connection establishment"""
        # Create a Socket.IO client
        sio = socketio.AsyncClient()
        
        # Connect to WebSocket server
        connected = False
        
        @sio.event
        async def connect():
            nonlocal connected
            connected = True
            
        try:
            await sio.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': authenticated_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            
            # Wait for connection
            await asyncio.sleep(0.5)
            assert connected, "WebSocket connection should be established"
            
        finally:
            await sio.disconnect()
    
    async def test_order_status_broadcast(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer,
        sample_order_data: Dict
    ):
        """Test real-time order status updates"""
        # Create an order
        sample_order_data['customer_id'] = test_customer.id
        response = await authenticated_client.post(
            "/api/v1/orders",
            json=sample_order_data
        )
        assert response.status_code == 201
        order = response.json()
        order_id = order['id']
        
        # Set up WebSocket listener
        sio = socketio.AsyncClient()
        received_updates = []
        
        @sio.event
        async def order_status_update(data):
            received_updates.append(data)
        
        try:
            # Connect to WebSocket
            await sio.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': authenticated_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            
            # Join order room
            await sio.emit('join_order', {'order_id': order_id})
            await asyncio.sleep(0.1)
            
            # Update order status
            response = await authenticated_client.put(
                f"/api/v1/orders/{order_id}/status",
                json={"status": OrderStatus.CONFIRMED.value}
            )
            assert response.status_code == 200
            
            # Wait for broadcast
            await asyncio.sleep(0.5)
            
            # Check if update was received
            assert len(received_updates) > 0, "Should receive order status update"
            update = received_updates[0]
            assert update['order_id'] == order_id
            assert update['status'] == OrderStatus.CONFIRMED.value
            
        finally:
            await sio.disconnect()
    
    async def test_driver_location_tracking(
        self,
        driver_client: AsyncClient,
        authenticated_client: AsyncClient
    ):
        """Test real-time driver location updates"""
        sio_driver = socketio.AsyncClient()
        sio_office = socketio.AsyncClient()
        location_updates = []
        
        @sio_office.event
        async def driver_location_update(data):
            location_updates.append(data)
        
        try:
            # Connect both clients
            await sio_driver.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': driver_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            
            await sio_office.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': authenticated_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            
            # Office joins driver tracking room
            await sio_office.emit('track_driver', {'driver_id': 1})
            await asyncio.sleep(0.1)
            
            # Driver sends location update
            location_data = {
                'latitude': 25.0330,
                'longitude': 121.5654,
                'heading': 45,
                'speed': 30
            }
            await sio_driver.emit('update_location', location_data)
            
            # Wait for broadcast
            await asyncio.sleep(0.5)
            
            # Verify location update received
            assert len(location_updates) > 0, "Should receive driver location update"
            update = location_updates[0]
            assert update['latitude'] == location_data['latitude']
            assert update['longitude'] == location_data['longitude']
            
        finally:
            await sio_driver.disconnect()
            await sio_office.disconnect()
    
    async def test_notification_system(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer
    ):
        """Test real-time notification delivery"""
        sio = socketio.AsyncClient()
        notifications = []
        
        @sio.event
        async def notification(data):
            notifications.append(data)
        
        try:
            # Connect to WebSocket
            await sio.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': authenticated_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            
            # Trigger a notification (e.g., urgent order)
            order_data = {
                'customer_id': test_customer.id,
                'scheduled_date': '2025-08-01T10:00:00',
                'qty_50kg': 2,
                'delivery_address': '台北市信義區測試路123號',
                'is_urgent': True,
                'payment_method': '現金'
            }
            
            response = await authenticated_client.post(
                "/api/v1/orders",
                json=order_data
            )
            assert response.status_code == 201
            
            # Wait for notification
            await asyncio.sleep(0.5)
            
            # Check notification received
            assert len(notifications) > 0, "Should receive urgent order notification"
            notification = notifications[0]
            assert notification['type'] == 'urgent_order'
            assert notification['priority'] == 'high'
            
        finally:
            await sio.disconnect()
    
    async def test_websocket_reconnection(self, authenticated_client: AsyncClient):
        """Test WebSocket auto-reconnection logic"""
        sio = socketio.AsyncClient()
        connection_count = 0
        
        @sio.event
        async def connect():
            nonlocal connection_count
            connection_count += 1
        
        try:
            # Initial connection
            await sio.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': authenticated_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            await asyncio.sleep(0.1)
            assert connection_count == 1
            
            # Simulate disconnect
            await sio.disconnect()
            await asyncio.sleep(0.1)
            
            # Reconnect
            await sio.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': authenticated_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            await asyncio.sleep(0.1)
            assert connection_count == 2, "Should reconnect successfully"
            
        finally:
            await sio.disconnect()
    
    async def test_message_queuing(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer
    ):
        """Test message queuing for offline clients"""
        # This test would verify that messages are queued when client is offline
        # and delivered when they reconnect
        
        sio = socketio.AsyncClient()
        received_messages = []
        
        @sio.event
        async def queued_message(data):
            received_messages.append(data)
        
        try:
            # Connect and immediately disconnect to simulate going offline
            await sio.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': authenticated_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            user_id = 1  # Would get from token in real scenario
            await sio.emit('register_user', {'user_id': user_id})
            await asyncio.sleep(0.1)
            await sio.disconnect()
            
            # Create order while offline (this should queue a notification)
            order_data = {
                'customer_id': test_customer.id,
                'scheduled_date': '2025-08-01T10:00:00',
                'qty_20kg': 1,
                'delivery_address': '台北市大安區測試路456號',
                'payment_method': '現金'
            }
            
            response = await authenticated_client.post(
                "/api/v1/orders",
                json=order_data
            )
            assert response.status_code == 201
            
            # Reconnect and check for queued messages
            await sio.connect(
                'http://localhost:8001',
                transports=['websocket'],
                auth={'token': authenticated_client.headers.get('Authorization', '').replace('Bearer ', '')}
            )
            await sio.emit('get_queued_messages', {'user_id': user_id})
            
            # Wait for queued messages
            await asyncio.sleep(0.5)
            
            # Should receive the queued notification
            assert len(received_messages) > 0, "Should receive queued messages"
            
        finally:
            await sio.disconnect()