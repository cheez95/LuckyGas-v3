"""
Integration tests for WebSocket real-time updates
"""
import pytest
import asyncio
import json
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch

from app.services.websocket_service import websocket_manager
from app.models.order import OrderStatus
from app.models.user import UserRole


class TestWebSocketRealTimeUpdates:
    """Test WebSocket real-time functionality"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self):
        """Test WebSocket connection establishment and cleanup"""
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        # Test connection
        connection_id = "test-connection-1"
        user_id = 1
        role = UserRole.OFFICE_STAFF.value
        
        # Add connection
        await websocket_manager.connect(mock_websocket, connection_id, user_id, role)
        
        # Verify connection is tracked
        assert connection_id in websocket_manager.active_connections
        assert websocket_manager.user_connections[user_id] == {connection_id}
        assert role in websocket_manager.role_connections
        assert connection_id in websocket_manager.role_connections[role]
        
        # Test message sending
        test_message = {"type": "test", "data": {"message": "Hello"}}
        await websocket_manager.send_personal_message(
            json.dumps(test_message),
            connection_id
        )
        mock_websocket.send_text.assert_called_once()
        
        # Disconnect
        await websocket_manager.disconnect(connection_id)
        
        # Verify cleanup
        assert connection_id not in websocket_manager.active_connections
        assert connection_id not in websocket_manager.user_connections.get(user_id, set())
    
    @pytest.mark.asyncio
    async def test_role_based_broadcasting(self):
        """Test broadcasting messages to specific roles"""
        # Setup mock connections for different roles
        office_ws = AsyncMock()
        driver_ws = AsyncMock()
        manager_ws = AsyncMock()
        
        await websocket_manager.connect(office_ws, "office-1", 1, UserRole.OFFICE_STAFF.value)
        await websocket_manager.connect(driver_ws, "driver-1", 2, UserRole.DRIVER.value)
        await websocket_manager.connect(manager_ws, "manager-1", 3, UserRole.MANAGER.value)
        
        # Broadcast to drivers only
        driver_message = {
            "type": "route_update",
            "data": {"route_id": 1, "status": "updated"}
        }
        await websocket_manager.broadcast_to_role(
            json.dumps(driver_message),
            UserRole.DRIVER.value
        )
        
        # Verify only driver received message
        driver_ws.send_text.assert_called_once()
        office_ws.send_text.assert_not_called()
        manager_ws.send_text.assert_not_called()
        
        # Cleanup
        await websocket_manager.disconnect("office-1")
        await websocket_manager.disconnect("driver-1")
        await websocket_manager.disconnect("manager-1")
    
    @pytest.mark.asyncio
    async def test_order_status_update_broadcast(self, db_session, test_customer):
        """Test order status updates are broadcast correctly"""
        # Setup connections
        office_ws = AsyncMock()
        customer_ws = AsyncMock()
        
        await websocket_manager.connect(
            office_ws, "office-1", 1, UserRole.OFFICE_STAFF.value
        )
        await websocket_manager.connect(
            customer_ws, "customer-1", test_customer.id, UserRole.CUSTOMER.value
        )
        
        # Simulate order status update
        order_update = {
            "type": "order_status_update",
            "data": {
                "order_id": 123,
                "customer_id": test_customer.id,
                "old_status": OrderStatus.CONFIRMED.value,
                "new_status": OrderStatus.DISPATCHED.value,
                "updated_at": datetime.now().isoformat()
            }
        }
        
        # Broadcast to office and specific customer
        await websocket_manager.broadcast_to_role(
            json.dumps(order_update),
            UserRole.OFFICE_STAFF.value
        )
        await websocket_manager.send_to_user(
            json.dumps(order_update),
            test_customer.id
        )
        
        # Verify both received the update
        office_ws.send_text.assert_called_once()
        customer_ws.send_text.assert_called_once()
        
        # Cleanup
        await websocket_manager.disconnect("office-1")
        await websocket_manager.disconnect("customer-1")
    
    @pytest.mark.asyncio
    async def test_driver_location_updates(self):
        """Test real-time driver location broadcasting"""
        # Setup connections
        office_ws = AsyncMock()
        driver_ws = AsyncMock()
        
        driver_id = 10
        await websocket_manager.connect(
            office_ws, "office-1", 1, UserRole.OFFICE_STAFF.value
        )
        await websocket_manager.connect(
            driver_ws, "driver-1", driver_id, UserRole.DRIVER.value
        )
        
        # Driver sends location update
        location_update = {
            "type": "driver_location",
            "data": {
                "driver_id": driver_id,
                "latitude": 25.0330,
                "longitude": 121.5654,
                "timestamp": datetime.now().isoformat(),
                "speed": 45.5,
                "heading": 180
            }
        }
        
        # Broadcast to office staff and managers
        await websocket_manager.broadcast_to_role(
            json.dumps(location_update),
            UserRole.OFFICE_STAFF.value
        )
        await websocket_manager.broadcast_to_role(
            json.dumps(location_update),
            UserRole.MANAGER.value
        )
        
        # Verify office received update
        office_ws.send_text.assert_called_once()
        sent_data = json.loads(office_ws.send_text.call_args[0][0])
        assert sent_data["type"] == "driver_location"
        assert sent_data["data"]["driver_id"] == driver_id
        
        # Cleanup
        await websocket_manager.disconnect("office-1")
        await websocket_manager.disconnect("driver-1")
    
    @pytest.mark.asyncio
    async def test_delivery_confirmation_broadcast(self):
        """Test delivery confirmation real-time updates"""
        # Setup connections
        office_ws = AsyncMock()
        customer_ws = AsyncMock()
        
        customer_id = 100
        await websocket_manager.connect(
            office_ws, "office-1", 1, UserRole.OFFICE_STAFF.value
        )
        await websocket_manager.connect(
            customer_ws, "customer-1", customer_id, UserRole.CUSTOMER.value
        )
        
        # Delivery confirmation message
        confirmation = {
            "type": "delivery_confirmation",
            "data": {
                "order_id": 456,
                "customer_id": customer_id,
                "delivered_at": datetime.now().isoformat(),
                "signature": "base64_signature_data",
                "cylinders_delivered": {
                    "50kg": 2,
                    "20kg": 1
                },
                "cylinders_collected": {
                    "50kg": 2,
                    "20kg": 1
                }
            }
        }
        
        # Broadcast
        await websocket_manager.broadcast(json.dumps(confirmation))
        
        # Both should receive
        office_ws.send_text.assert_called_once()
        customer_ws.send_text.assert_called_once()
        
        # Cleanup
        await websocket_manager.disconnect("office-1")
        await websocket_manager.disconnect("customer-1")
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors"""
        # Create a websocket that will fail
        failing_ws = AsyncMock()
        failing_ws.send_text = AsyncMock(side_effect=Exception("Connection lost"))
        
        await websocket_manager.connect(
            failing_ws, "failing-1", 1, UserRole.OFFICE_STAFF.value
        )
        
        # Try to send message - should handle error gracefully
        try:
            await websocket_manager.send_personal_message(
                json.dumps({"type": "test"}),
                "failing-1"
            )
        except Exception:
            # Should not raise exception to caller
            pass
        
        # Connection should be removed after error
        assert "failing-1" not in websocket_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_batch_updates(self):
        """Test sending batch updates efficiently"""
        # Setup multiple connections
        connections = []
        for i in range(5):
            ws = AsyncMock()
            conn_id = f"office-{i}"
            await websocket_manager.connect(
                ws, conn_id, i, UserRole.OFFICE_STAFF.value
            )
            connections.append((conn_id, ws))
        
        # Send batch update
        batch_update = {
            "type": "batch_order_update",
            "data": {
                "orders": [
                    {"id": 1, "status": "confirmed"},
                    {"id": 2, "status": "dispatched"},
                    {"id": 3, "status": "delivered"}
                ],
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Broadcast to all office staff
        await websocket_manager.broadcast_to_role(
            json.dumps(batch_update),
            UserRole.OFFICE_STAFF.value
        )
        
        # Verify all received
        for conn_id, ws in connections:
            ws.send_text.assert_called_once()
            
        # Cleanup
        for conn_id, _ in connections:
            await websocket_manager.disconnect(conn_id)
    
    @pytest.mark.asyncio
    async def test_reconnection_handling(self):
        """Test handling of client reconnections"""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        user_id = 1
        
        # Initial connection
        await websocket_manager.connect(
            ws1, "conn-1", user_id, UserRole.OFFICE_STAFF.value
        )
        
        # Simulate disconnection
        await websocket_manager.disconnect("conn-1")
        
        # Reconnect with new connection ID
        await websocket_manager.connect(
            ws2, "conn-2", user_id, UserRole.OFFICE_STAFF.value
        )
        
        # Send message to user - should go to new connection
        await websocket_manager.send_to_user(
            json.dumps({"type": "welcome_back"}),
            user_id
        )
        
        ws1.send_text.assert_not_called()
        ws2.send_text.assert_called_once()
        
        # Cleanup
        await websocket_manager.disconnect("conn-2")