"""
Google OR-Tools VRP (Vehicle Routing Problem) optimizer for Lucky Gas deliveries
"""
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)


@dataclass
class VRPStop:
    """Represents a delivery stop"""
    order_id: int
    customer_id: int
    customer_name: str
    address: str
    latitude: float
    longitude: float
    demand: Dict[str, int]  # {"50kg": 2, "20kg": 1}
    time_window: Tuple[int, int]  # (start, end) in minutes from start
    service_time: int  # minutes


@dataclass
class VRPVehicle:
    """Represents a delivery vehicle"""
    driver_id: int
    driver_name: str
    capacity: Dict[str, int]  # {"50kg": 10, "20kg": 20}
    start_location: Tuple[float, float]
    end_location: Optional[Tuple[float, float]] = None
    max_travel_time: int = 480  # 8 hours in minutes


class ORToolsOptimizer:
    """
    Vehicle Routing Problem optimizer using Google OR-Tools
    Optimizes multiple routes considering:
    - Vehicle capacities for different gas cylinder sizes
    - Customer time windows
    - Service time at each stop
    - Maximum driver working hours
    """
    
    def __init__(self, depot_location: Tuple[float, float]):
        self.depot_location = depot_location
        
    def create_data_model(
        self,
        stops: List[VRPStop],
        vehicles: List[VRPVehicle]
    ) -> Dict:
        """Create data model for VRP"""
        
        # Calculate distance matrix
        locations = [self.depot_location]  # Depot is index 0
        for stop in stops:
            locations.append((stop.latitude, stop.longitude))
        
        distance_matrix = self._calculate_distance_matrix(locations)
        
        # Create time matrix (distance in km * 2 for average speed 30km/h in city)
        time_matrix = [[int(dist * 2) for dist in row] for row in distance_matrix]
        
        # Extract demands for each product type
        product_types = ["50kg", "20kg", "16kg", "10kg", "4kg"]
        demands = {}
        for product in product_types:
            demands[product] = [0]  # Depot has 0 demand
            for stop in stops:
                demands[product].append(stop.demand.get(product, 0))
        
        # Vehicle capacities
        vehicle_capacities = {}
        for product in product_types:
            vehicle_capacities[product] = [
                vehicle.capacity.get(product, 0) for vehicle in vehicles
            ]
        
        # Time windows
        time_windows = [(0, 480)]  # Depot open all day
        for stop in stops:
            time_windows.append(stop.time_window)
        
        data = {
            'distance_matrix': distance_matrix,
            'time_matrix': time_matrix,
            'demands': demands,
            'vehicle_capacities': vehicle_capacities,
            'num_vehicles': len(vehicles),
            'depot': 0,
            'time_windows': time_windows,
            'service_time': [0] + [stop.service_time for stop in stops],
            'vehicle_max_time': [v.max_travel_time for v in vehicles]
        }
        
        return data
    
    def optimize(
        self,
        stops: List[VRPStop],
        vehicles: List[VRPVehicle]
    ) -> Dict[int, List[VRPStop]]:
        """
        Optimize routes for multiple vehicles
        Returns: Dict mapping vehicle index to list of stops
        """
        
        if not stops:
            return {i: [] for i in range(len(vehicles))}
        
        # Create data model
        data = self.create_data_model(stops, vehicles)
        
        # Create routing index manager
        manager = pywrapcp.RoutingIndexManager(
            len(data['distance_matrix']),
            data['num_vehicles'],
            data['depot']
        )
        
        # Create routing model
        routing = pywrapcp.RoutingModel(manager)
        
        # Distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add capacity constraints for each product type
        for product, demands in data['demands'].items():
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return demands[from_node]
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # null capacity slack
                data['vehicle_capacities'][product],
                True,  # start cumul to zero
                f'{product}_capacity'
            )
        
        # Add time dimension
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel_time = data['time_matrix'][from_node][to_node]
            service_time = data['service_time'][from_node]
            return travel_time + service_time
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        
        routing.AddDimension(
            time_callback_index,
            30,  # allow waiting time
            data['vehicle_max_time'],  # maximum time per vehicle
            False,  # Don't force start cumul to zero
            'Time'
        )
        
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # Add time window constraints
        for location_idx, time_window in enumerate(data['time_windows']):
            if location_idx == data['depot']:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        
        # Instantiate route start and end times
        for vehicle_id in range(data['num_vehicles']):
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.Start(vehicle_id))
            )
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.End(vehicle_id))
            )
        
        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(30)
        
        # Solve
        logger.info(f"Optimizing routes for {len(stops)} stops and {len(vehicles)} vehicles")
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            logger.info("OR-Tools found optimal solution")
            return self._extract_solution(
                manager, routing, solution, stops, vehicles, data
            )
        else:
            logger.warning("OR-Tools could not find solution, using fallback")
            return self._fallback_assignment(stops, vehicles)
    
    def _extract_solution(
        self,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        solution: pywrapcp.Assignment,
        stops: List[VRPStop],
        vehicles: List[VRPVehicle],
        data: Dict
    ) -> Dict[int, List[VRPStop]]:
        """Extract solution routes"""
        
        routes = {}
        time_dimension = routing.GetDimensionOrDie('Time')
        total_distance = 0
        total_time = 0
        
        for vehicle_id in range(len(vehicles)):
            route_stops = []
            route_distance = 0
            index = routing.Start(vehicle_id)
            plan_output = f"Route for vehicle {vehicle_id} ({vehicles[vehicle_id].driver_name}):\n"
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                
                if node_index != 0:  # Skip depot
                    stop = stops[node_index - 1]  # Adjust for depot at index 0
                    
                    # Add arrival time
                    time_var = time_dimension.CumulVar(index)
                    stop.estimated_arrival = solution.Min(time_var)
                    
                    route_stops.append(stop)
                    plan_output += f"  Stop {len(route_stops)}: {stop.customer_name} - {stop.address}\n"
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            
            routes[vehicle_id] = route_stops
            
            # Log route info
            if route_stops:
                route_time = solution.Min(time_dimension.CumulVar(routing.End(vehicle_id)))
                plan_output += f"  Distance: {route_distance}m\n"
                plan_output += f"  Duration: {route_time} minutes\n"
                plan_output += f"  Load: {self._calculate_route_load(route_stops)}\n"
                logger.info(plan_output)
                
                total_distance += route_distance
                total_time += route_time
        
        # Log summary
        logger.info(f"Total distance: {total_distance/1000:.1f} km")
        logger.info(f"Total time: {total_time} minutes")
        logger.info(f"Average stops per vehicle: {len(stops) / len(vehicles):.1f}")
        
        return routes
    
    def _calculate_distance_matrix(
        self,
        locations: List[Tuple[float, float]]
    ) -> List[List[float]]:
        """Calculate distance matrix using Haversine formula"""
        n = len(locations)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Return distance in meters for OR-Tools
                    matrix[i][j] = int(self._haversine_distance(
                        locations[i][0], locations[i][1],
                        locations[j][0], locations[j][1]
                    ) * 1000)
        
        return matrix
    
    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _calculate_route_load(self, stops: List[VRPStop]) -> str:
        """Calculate total load for a route"""
        total_demand = {}
        for stop in stops:
            for product, qty in stop.demand.items():
                total_demand[product] = total_demand.get(product, 0) + qty
        
        return ", ".join([f"{qty} x {product}" for product, qty in total_demand.items() if qty > 0])
    
    def _fallback_assignment(
        self,
        stops: List[VRPStop],
        vehicles: List[VRPVehicle]
    ) -> Dict[int, List[VRPStop]]:
        """Simple fallback assignment when OR-Tools fails"""
        logger.warning("Using fallback assignment strategy")
        
        # Sort stops by geographic area (simple clustering by latitude)
        sorted_stops = sorted(stops, key=lambda s: (s.latitude, s.longitude))
        
        # Distribute stops evenly
        stops_per_vehicle = len(stops) // len(vehicles)
        routes = {}
        
        for i in range(len(vehicles)):
            start = i * stops_per_vehicle
            end = start + stops_per_vehicle if i < len(vehicles) - 1 else len(stops)
            routes[i] = sorted_stops[start:end]
            
            # Add simple estimated arrival times
            current_time = 8 * 60  # Start at 8 AM
            for j, stop in enumerate(routes[i]):
                stop.estimated_arrival = current_time + (j * 30)  # 30 minutes per stop
        
        return routes


# Singleton instance with default Taipei depot location
ortools_optimizer = ORToolsOptimizer(
    depot_location=(25.0330, 121.5654)  # Taipei
)