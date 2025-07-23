"""
Test OR-Tools VRP optimizer
"""
import pytest
from app.services.optimization import ortools_optimizer, VRPStop, VRPVehicle


def test_ortools_basic_optimization():
    """Test basic route optimization with OR-Tools"""
    
    # Create test stops with time windows relative to 8AM start
    stops = [
        VRPStop(
            order_id=1,
            customer_id=1,
            customer_name="客戶 A",
            address="台北市信義區信義路五段7號",
            latitude=25.0330,
            longitude=121.5600,
            demand={"50kg": 2, "20kg": 1},
            time_window=(0, 4 * 60),  # 8 AM to 12 PM (0-240 minutes from 8AM)
            service_time=15
        ),
        VRPStop(
            order_id=2,
            customer_id=2,
            customer_name="客戶 B",
            address="台北市大安區忠孝東路四段",
            latitude=25.0415,
            longitude=121.5435,
            demand={"20kg": 3, "10kg": 2},
            time_window=(1 * 60, 8 * 60),  # 9 AM to 4 PM (60-480 minutes from 8AM)
            service_time=20
        ),
        VRPStop(
            order_id=3,
            customer_id=3,
            customer_name="客戶 C",
            address="台北市中山區南京東路",
            latitude=25.0520,
            longitude=121.5425,
            demand={"50kg": 1, "4kg": 5},
            time_window=(2 * 60, 8 * 60),  # 10 AM to 4 PM (120-480 minutes from 8AM)
            service_time=10
        )
    ]
    
    # Create test vehicles
    vehicles = [
        VRPVehicle(
            driver_id=1,
            driver_name="司機 王",
            capacity={"50kg": 5, "20kg": 10, "16kg": 10, "10kg": 15, "4kg": 20},
            start_location=(25.0330, 121.5654),  # Depot
            max_travel_time=480  # 8 hours
        ),
        VRPVehicle(
            driver_id=2,
            driver_name="司機 李",
            capacity={"50kg": 5, "20kg": 10, "16kg": 10, "10kg": 15, "4kg": 20},
            start_location=(25.0330, 121.5654),  # Depot
            max_travel_time=480  # 8 hours
        )
    ]
    
    # Optimize routes
    routes = ortools_optimizer.optimize(stops, vehicles)
    
    # Verify results
    assert len(routes) == 2  # Two vehicles
    
    # All stops should be assigned
    assigned_stops = []
    for vehicle_id, route_stops in routes.items():
        assigned_stops.extend(route_stops)
    
    assert len(assigned_stops) == len(stops)
    
    # Check capacity constraints
    for vehicle_id, route_stops in routes.items():
        vehicle = vehicles[vehicle_id]
        total_demand = {}
        
        for stop in route_stops:
            for product, qty in stop.demand.items():
                total_demand[product] = total_demand.get(product, 0) + qty
        
        # Verify capacity not exceeded
        for product, qty in total_demand.items():
            assert qty <= vehicle.capacity.get(product, 0)
    
    print(f"Optimization successful: {len(stops)} stops assigned to {len(vehicles)} vehicles")


def test_ortools_with_time_windows():
    """Test route optimization with strict time windows"""
    
    # Create stops with tight but achievable time windows
    stops = [
        VRPStop(
            order_id=1,
            customer_id=1,
            customer_name="早晨客戶",
            address="台北市信義區",
            latitude=25.0330,
            longitude=121.5600,
            demand={"50kg": 1},
            time_window=(0, 2 * 60),  # 8-10 AM (0-120 minutes from 8AM start)
            service_time=15
        ),
        VRPStop(
            order_id=2,
            customer_id=2,
            customer_name="下午客戶",
            address="台北市大安區",
            latitude=25.0415,
            longitude=121.5435,
            demand={"20kg": 2},
            time_window=(3 * 60, 6 * 60),  # 11 AM-2 PM (180-360 minutes from 8AM start)
            service_time=20
        )
    ]
    
    vehicles = [
        VRPVehicle(
            driver_id=1,
            driver_name="司機",
            capacity={"50kg": 10, "20kg": 20},
            start_location=(25.0330, 121.5654),
            max_travel_time=480
        )
    ]
    
    routes = ortools_optimizer.optimize(stops, vehicles)
    
    # Verify time window constraints are respected
    assert len(routes[0]) == 2
    
    # Check arrival times
    for stop in routes[0]:
        assert hasattr(stop, 'estimated_arrival')
        # Arrival should be within time window
        assert stop.time_window[0] <= stop.estimated_arrival <= stop.time_window[1]


def test_ortools_empty_case():
    """Test optimization with no stops"""
    
    stops = []
    vehicles = [
        VRPVehicle(
            driver_id=1,
            driver_name="司機",
            capacity={"50kg": 10},
            start_location=(25.0330, 121.5654),
            max_travel_time=480
        )
    ]
    
    routes = ortools_optimizer.optimize(stops, vehicles)
    
    assert len(routes) == 1
    assert len(routes[0]) == 0


if __name__ == "__main__":
    test_ortools_basic_optimization()
    test_ortools_with_time_windows()
    test_ortools_empty_case()
    print("All OR-Tools tests passed!")