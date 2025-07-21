"""
Example Socket.IO client for Lucky Gas real-time communication
Demonstrates proper usage of the new Socket.IO implementation
"""
import socketio
import asyncio
import json
from datetime import datetime
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Socket.IO client
sio = socketio.AsyncClient(
    logger=logger,
    engineio_logger=False  # Set to True for debugging
)


class LuckyGasSocketClient:
    """Example Socket.IO client for Lucky Gas"""
    
    def __init__(self, server_url: str, token: str):
        self.server_url = server_url
        self.token = token
        self.connected = False
    
    async def connect(self):
        """Connect to Socket.IO server"""
        try:
            await sio.connect(
                self.server_url,
                auth={'token': self.token},
                socketio_path='/socket.io'
            )
            self.connected = True
            logger.info(f"Connected to {self.server_url}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.connected:
            await sio.disconnect()
            self.connected = False
            logger.info("Disconnected from server")
    
    async def subscribe_to_topics(self, topics: list):
        """Subscribe to topics"""
        for topic in topics:
            result = await sio.call('subscribe', {'topic': topic}, timeout=5)
            logger.info(f"Subscribed to {topic}: {result}")
    
    async def send_driver_location(self, lat: float, lng: float):
        """Send driver location update"""
        data = {
            'latitude': lat,
            'longitude': lng,
            'accuracy': 10.0
        }
        result = await sio.call('driver_location', data, timeout=5)
        logger.info(f"Location update sent: {result}")
    
    async def update_delivery_status(self, order_id: int, status: str, notes: str = ""):
        """Update delivery status"""
        data = {
            'order_id': order_id,
            'status': status,
            'notes': notes
        }
        result = await sio.call('delivery_status', data, timeout=5)
        logger.info(f"Delivery status updated: {result}")
    
    async def send_ping(self):
        """Send ping to keep connection alive"""
        await sio.emit('ping')
    
    def setup_event_handlers(self):
        """Setup event handlers for incoming messages"""
        
        @sio.on('connected')
        async def on_connected(data):
            logger.info(f"Connection confirmed: {data}")
        
        @sio.on('pong')
        async def on_pong(data):
            logger.info(f"Pong received: {data}")
        
        @sio.on('order_update')
        async def on_order_update(data):
            logger.info(f"Order update: {data}")
        
        @sio.on('route_update')
        async def on_route_update(data):
            logger.info(f"Route update: {data}")
        
        @sio.on('notification')
        async def on_notification(data):
            logger.info(f"Notification: {data}")
            # Send acknowledgment
            return {'received': True, 'timestamp': datetime.utcnow().isoformat()}
        
        @sio.on('system_message')
        async def on_system_message(data):
            logger.warning(f"System message: {data}")
        
        @sio.on('location_update')
        async def on_location_update(data):
            logger.info(f"Driver location update: {data}")
        
        @sio.on('route_assigned')
        async def on_route_assigned(data):
            logger.info(f"Route assigned: {data}")
        
        @sio.on('prediction_ready')
        async def on_prediction_ready(data):
            logger.info(f"Predictions ready: {data}")
        
        @sio.event
        async def connect():
            logger.info("Socket.IO connected event fired")
        
        @sio.event
        async def connect_error(data):
            logger.error(f"Connection error: {data}")
        
        @sio.event
        async def disconnect():
            logger.info("Socket.IO disconnected")


async def run_driver_simulation(client: LuckyGasSocketClient):
    """Simulate a driver's activities"""
    logger.info("Starting driver simulation...")
    
    # Subscribe to driver topics
    await client.subscribe_to_topics(['routes', 'drivers', 'notifications'])
    
    # Simulate route progress
    route_points = [
        (25.0330, 121.5654),  # Start
        (25.0340, 121.5664),  # Stop 1
        (25.0350, 121.5674),  # Stop 2
        (25.0360, 121.5684),  # Stop 3
    ]
    
    order_ids = [101, 102, 103]
    
    for i, (lat, lng) in enumerate(route_points):
        # Send location update
        await client.send_driver_location(lat, lng)
        await asyncio.sleep(2)
        
        # Update delivery status
        if i > 0 and i <= len(order_ids):
            order_id = order_ids[i-1]
            await client.update_delivery_status(
                order_id, 
                'delivered',
                f'Delivered to stop {i}'
            )
            await asyncio.sleep(1)
    
    logger.info("Driver simulation completed")


async def run_office_simulation(client: LuckyGasSocketClient):
    """Simulate office staff activities"""
    logger.info("Starting office simulation...")
    
    # Subscribe to office topics
    await client.subscribe_to_topics(['orders', 'routes', 'predictions', 'notifications'])
    
    # Just listen for updates
    logger.info("Listening for updates... (Press Ctrl+C to stop)")
    
    # Keep alive with periodic pings
    while True:
        await client.send_ping()
        await asyncio.sleep(30)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Lucky Gas Socket.IO Client Example')
    parser.add_argument('--server', default='http://localhost:8000', help='Server URL')
    parser.add_argument('--token', required=True, help='Authentication token')
    parser.add_argument('--role', choices=['driver', 'office'], default='office', 
                       help='Simulate driver or office staff')
    
    args = parser.parse_args()
    
    # Create client
    client = LuckyGasSocketClient(args.server, args.token)
    client.setup_event_handlers()
    
    try:
        # Connect
        await client.connect()
        
        # Run simulation based on role
        if args.role == 'driver':
            await run_driver_simulation(client)
        else:
            await run_office_simulation(client)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    # Run the client
    asyncio.run(main())


"""
Usage examples:

1. Run as office staff:
   python socketio_client.py --token YOUR_JWT_TOKEN --role office

2. Run as driver:
   python socketio_client.py --token YOUR_JWT_TOKEN --role driver

3. Connect to production:
   python socketio_client.py --server https://api.luckygas.tw --token YOUR_JWT_TOKEN

Note: You need to get a valid JWT token first by logging in through the API.
"""