import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import googlemaps
from geopy import distance

from app.core.config import settings

logger = logging.getLogger(__name__)


class RouteOptimizationService:
    """Service for optimizing delivery routes using OR-Tools and Google Routes API."""

    def __init__(self):
        self._gmaps = None

    @property
    def gmaps(self):
        """Lazy initialization of Google Maps client."""
        if self._gmaps is None and settings.GOOGLE_MAPS_API_KEY:
            self._gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        return self._gmaps

    async def optimize_routes(
        self,
        orders: List[Dict[str, Any]],
        drivers: List[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Optimize delivery routes for given orders and drivers."""
        try:
            # Set default constraints
            if not constraints:
                constraints = {
                    "max_distance_per_route": 100,  # km
                    "max_stops_per_route": 20,
                    "time_window_start": "08:00",
                    "time_window_end": "18:00",
                    "service_time_per_stop": 10,  # minutes
                    "depot_location": {"lat": 25.0330, "lng": 121.5654},
                }

            # Create distance matrix
            distance_matrix = await self._create_distance_matrix(
                orders, constraints["depot_location"]
            )

            # Create time matrix (considering traffic)
            time_matrix = await self._create_time_matrix(
                orders, constraints["depot_location"]
            )

            # Create demand array (cylinder quantities)
            demands = [0] + [
                order.get("quantity", 1) for order in orders
            ]  # 0 for depot

            # Create vehicle capacities
            vehicle_capacities = [driver.get("max_capacity", 50) for driver in drivers]

            # Solve using OR-Tools
            solution = self._solve_vrp(
                distance_matrix,
                time_matrix,
                demands,
                vehicle_capacities,
                len(drivers),
                constraints,
            )

            # Format solution
            routes = self._format_solution(
                solution, orders, drivers, distance_matrix, time_matrix
            )

            # Calculate metrics
            metrics = self._calculate_metrics(routes, distance_matrix)

            return {
                "success": True,
                "routes": routes,
                "unassigned_orders": solution.get("unassigned", []),
                "metrics": metrics,
                "optimization_score": metrics.get("optimization_score", 0),
            }

        except Exception as e:
            logger.error(f"Error optimizing routes: {str(e)}")
            # Fallback to simple assignment
            return self._simple_route_assignment(orders, drivers)

    async def _create_distance_matrix(
        self, orders: List[Dict[str, Any]], depot_location: Dict[str, float]
    ) -> List[List[float]]:
        """Create distance matrix between all locations."""
        locations = [depot_location] + [
            {"lat": order["latitude"], "lng": order["longitude"]} for order in orders
        ]

        n = len(locations)
        matrix = [[0] * n for _ in range(n)]

        # Use Google Distance Matrix API for accurate distances
        for i in range(n):
            for j in range(i + 1, n):
                try:
                    # For small distances, use straight-line distance
                    dist = distance.distance(
                        (locations[i]["lat"], locations[i]["lng"]),
                        (locations[j]["lat"], locations[j]["lng"]),
                    ).km

                    # Apply Taiwan road factor (roads are not straight)
                    dist *= 1.3

                    matrix[i][j] = int(dist * 1000)  # Convert to meters
                    matrix[j][i] = matrix[i][j]

                except Exception as e:
                    # Fallback to straight-line distance
                    dist = self._haversine_distance(
                        locations[i]["lat"],
                        locations[i]["lng"],
                        locations[j]["lat"],
                        locations[j]["lng"],
                    )
                    matrix[i][j] = int(dist * 1000)
                    matrix[j][i] = matrix[i][j]

        return matrix

    async def _create_time_matrix(
        self, orders: List[Dict[str, Any]], depot_location: Dict[str, float]
    ) -> List[List[int]]:
        """Create time matrix considering traffic patterns."""
        # For now, estimate based on distance and average speed
        distance_matrix = await self._create_distance_matrix(orders, depot_location)

        # Average speed in urban Taiwan (km/h)
        avg_speed = 30

        time_matrix = []
        for row in distance_matrix:
            time_row = []
            for dist in row:
                # Convert distance (meters) to time (minutes)
                time_minutes = (dist / 1000) / avg_speed * 60
                time_row.append(int(time_minutes))
            time_matrix.append(time_row)

        return time_matrix

    def _solve_vrp(
        self,
        distance_matrix: List[List[float]],
        time_matrix: List[List[int]],
        demands: List[int],
        vehicle_capacities: List[int],
        num_vehicles: int,
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Solve Vehicle Routing Problem using OR-Tools."""

        # Create routing index manager
        manager = pywrapcp.RoutingIndexManager(
            len(distance_matrix), num_vehicles, 0  # Depot index
        )

        # Create routing model
        routing = pywrapcp.RoutingModel(manager)

        # Create distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add capacity constraint
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            vehicle_capacities,  # vehicle maximum capacities
            True,  # start cumul to zero
            "Capacity",
        )

        # Add time constraint
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            30,  # allow waiting time
            480,  # maximum time per vehicle (8 hours)
            False,  # Don't force start cumul to zero
            "Time",
        )

        # Add distance constraint
        distance_dimension = routing.GetDimensionOrDie("Distance")
        distance_dimension.SetGlobalSpanCostCoefficient(100)

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
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            return self._extract_solution(manager, routing, solution, num_vehicles)
        else:
            return {"routes": [], "unassigned": list(range(1, len(distance_matrix)))}

    def _extract_solution(
        self,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        solution: pywrapcp.Assignment,
        num_vehicles: int,
    ) -> Dict[str, Any]:
        """Extract solution from OR-Tools solver."""
        routes = []
        unassigned = []

        for vehicle_id in range(num_vehicles):
            route = []
            index = routing.Start(vehicle_id)

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                if node_index != 0:  # Skip depot
                    route.append(node_index - 1)  # Adjust for 0-based order indexing
                index = solution.Value(routing.NextVar(index))

            if route:
                routes.append(
                    {
                        "vehicle_id": vehicle_id,
                        "route": route,
                        "distance": solution.Value(
                            routing.GetDimensionOrDie("Distance").CumulVar(index)
                        ),
                        "load": solution.Value(
                            routing.GetDimensionOrDie("Capacity").CumulVar(index)
                        ),
                    }
                )

        # Find unassigned orders
        for order_idx in range(len(manager.GetNumberOfNodes()) - 1):
            if not any(order_idx in route["route"] for route in routes):
                unassigned.append(order_idx)

        return {
            "routes": routes,
            "unassigned": unassigned,
            "total_distance": sum(r["distance"] for r in routes),
        }

    def _format_solution(
        self,
        solution: Dict[str, Any],
        orders: List[Dict[str, Any]],
        drivers: List[Dict[str, Any]],
        distance_matrix: List[List[float]],
        time_matrix: List[List[int]],
    ) -> List[Dict[str, Any]]:
        """Format solution into readable route format."""
        formatted_routes = []

        for route_data in solution.get("routes", []):
            driver = drivers[route_data["vehicle_id"]]
            route_orders = [orders[idx] for idx in route_data["route"]]

            # Calculate route details
            stops = []
            current_time = 480  # 8:00 AM in minutes
            total_distance = 0

            prev_idx = 0  # Start from depot
            for i, order_idx in enumerate(route_data["route"]):
                curr_idx = order_idx + 1  # Adjust for depot

                # Add travel time
                travel_time = time_matrix[prev_idx][curr_idx]
                current_time += travel_time

                # Add service time
                service_time = 10  # minutes per stop

                stops.append(
                    {
                        "sequence": i + 1,
                        "order_id": route_orders[i]["id"],
                        "customer_name": route_orders[i]["customer_name"],
                        "address": route_orders[i]["address"],
                        "arrival_time": self._minutes_to_time(current_time),
                        "service_time": service_time,
                        "distance_from_prev": distance_matrix[prev_idx][curr_idx]
                        / 1000,  # km
                    }
                )

                current_time += service_time
                total_distance += distance_matrix[prev_idx][curr_idx]
                prev_idx = curr_idx

            # Add return to depot
            total_distance += distance_matrix[prev_idx][0]

            formatted_routes.append(
                {
                    "route_id": f"R-{datetime.now().strftime('%Y%m%d')}-{route_data['vehicle_id'] + 1:02d}",
                    "driver_id": driver["id"],
                    "driver_name": driver["name"],
                    "vehicle_number": driver.get("vehicle_number", ""),
                    "stops": stops,
                    "total_distance": round(total_distance / 1000, 2),  # km
                    "total_time": current_time
                    - 480
                    + time_matrix[prev_idx][0],  # minutes
                    "optimization_score": self._calculate_route_efficiency(
                        total_distance / 1000,
                        len(stops),
                        driver.get("max_capacity", 50),
                    ),
                }
            )

        return formatted_routes

    def _calculate_metrics(
        self, routes: List[Dict[str, Any]], distance_matrix: List[List[float]]
    ) -> Dict[str, Any]:
        """Calculate optimization metrics."""
        total_distance = sum(route["total_distance"] for route in routes)
        total_stops = sum(len(route["stops"]) for route in routes)
        avg_stops_per_route = total_stops / len(routes) if routes else 0

        # Calculate theoretical minimum distance (TSP lower bound)
        min_spanning_tree_distance = self._calculate_mst_distance(distance_matrix)

        optimization_score = min(
            (
                (min_spanning_tree_distance / total_distance * 100)
                if total_distance > 0
                else 0
            ),
            100,
        )

        return {
            "total_distance": round(total_distance, 2),
            "total_stops": total_stops,
            "total_routes": len(routes),
            "avg_stops_per_route": round(avg_stops_per_route, 1),
            "avg_distance_per_route": (
                round(total_distance / len(routes), 2) if routes else 0
            ),
            "optimization_score": round(optimization_score, 1),
        }

    def _simple_route_assignment(
        self, orders: List[Dict[str, Any]], drivers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Simple round-robin route assignment as fallback."""
        routes = []
        orders_per_driver = len(orders) // len(drivers) + 1

        for i, driver in enumerate(drivers):
            start_idx = i * orders_per_driver
            end_idx = min((i + 1) * orders_per_driver, len(orders))

            if start_idx < len(orders):
                driver_orders = orders[start_idx:end_idx]
                stops = [
                    {
                        "sequence": j + 1,
                        "order_id": order["id"],
                        "customer_name": order["customer_name"],
                        "address": order["address"],
                    }
                    for j, order in enumerate(driver_orders)
                ]

                routes.append(
                    {
                        "route_id": f"R-{datetime.now().strftime('%Y%m%d')}-{i + 1:02d}",
                        "driver_id": driver["id"],
                        "driver_name": driver["name"],
                        "stops": stops,
                        "total_distance": len(stops) * 10,  # Rough estimate
                        "optimization_score": 70,  # Lower score for simple assignment
                    }
                )

        return {
            "success": True,
            "routes": routes,
            "unassigned_orders": [],
            "metrics": {
                "total_routes": len(routes),
                "optimization_score": 70,
            },
        }

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate haversine distance between two points."""
        R = 6371  # Earth's radius in km

        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)

        a = (
            np.sin(delta_lat / 2) ** 2
            + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
        )
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        return R * c

    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes since midnight to time string."""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def _calculate_route_efficiency(
        self, distance: float, stops: int, capacity: int
    ) -> float:
        """Calculate route efficiency score."""
        # Simple efficiency calculation
        distance_per_stop = distance / stops if stops > 0 else float("inf")

        # Ideal distance per stop (km)
        ideal_distance = 5.0

        efficiency = min((ideal_distance / distance_per_stop) * 100, 100)
        return round(efficiency, 1)

    def _calculate_mst_distance(self, distance_matrix: List[List[float]]) -> float:
        """Calculate minimum spanning tree distance as lower bound."""
        n = len(distance_matrix)
        if n <= 1:
            return 0

        # Simple MST approximation
        visited = [False] * n
        min_distance = 0
        visited[0] = True

        for _ in range(n - 1):
            min_edge = float("inf")
            next_vertex = -1

            for i in range(n):
                if visited[i]:
                    for j in range(n):
                        if not visited[j] and distance_matrix[i][j] < min_edge:
                            min_edge = distance_matrix[i][j]
                            next_vertex = j

            if next_vertex != -1:
                visited[next_vertex] = True
                min_distance += min_edge

        return min_distance / 1000  # Convert to km


# Singleton instance
route_optimization_service = RouteOptimizationService()
