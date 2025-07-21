"""
Test OR-Tools integration with routes service
"""
import asyncio
from datetime import datetime
from app.services.google_cloud.routes_service import google_routes_service
from app.models.order import Order
from app.models.customer import Customer


async def test_ortools_integration():
    """Test the OR-Tools VRP integration"""
    
    # Create test customers
    customers = [
        Customer(
            id=1,
            customer_code="C001",
            short_name="客戶A",
            address="台北市中正區重慶南路一段122號",
            latitude=25.0330,
            longitude=121.5654,
            delivery_time_start="09:00",
            delivery_time_end="12:00"
        ),
        Customer(
            id=2,
            customer_code="C002",
            short_name="客戶B",
            address="台北市大安區忠孝東路四段1號",
            latitude=25.0408,
            longitude=121.5438,
            delivery_time_start="14:00",
            delivery_time_end="17:00"
        ),
        Customer(
            id=3,
            customer_code="C003",
            short_name="客戶C",
            address="台北市信義區市府路1號",
            latitude=25.0375,
            longitude=121.5637,
            delivery_time_start="10:00",
            delivery_time_end="15:00"
        )
    ]
    
    # Create test orders
    orders = []
    for i, customer in enumerate(customers):
        order = Order(
            id=i+1,
            customer_id=customer.id,
            customer=customer,
            delivery_address=customer.address,
            priority=1,
            quantity_20kg=2,
            quantity_16kg=1,
            quantity_10kg=0,
            quantity_4kg=1,
            quantity_50kg=0
        )
        orders.append(order)
    
    # Create test drivers
    drivers = [
        {"id": 1, "name": "司機A"},
        {"id": 2, "name": "司機B"}
    ]
    
    # Test optimization
    print("Testing OR-Tools VRP optimization...")
    try:
        routes = await google_routes_service.optimize_multiple_routes(
            orders=orders,
            drivers=drivers,
            date=datetime.now()
        )
        
        print(f"\nOptimization completed! Generated {len(routes)} routes:")
        for route in routes:
            print(f"\nRoute {route['route_number']}:")
            print(f"  Driver: {route['driver_id']}")
            print(f"  Total stops: {route['total_stops']}")
            print(f"  Distance: {route['total_distance_km']:.2f} km")
            print(f"  Duration: {route['estimated_duration_minutes']} minutes")
            print(f"  Optimization method: {route['optimization_method']}")
            
            print("  Stops:")
            for stop in route['stops']:
                print(f"    {stop['stop_sequence']}. {stop['customer_name']} - {stop['address']}")
                print(f"       Products: {stop['products']}")
                print(f"       ETA: {stop['estimated_arrival']}")
        
        print("\n✅ OR-Tools integration test passed!")
        
    except Exception as e:
        print(f"\n❌ OR-Tools integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ortools_integration())