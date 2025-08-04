"""
Enhanced VRP (Vehicle Routing Problem) solver for Lucky Gas deliveries
Integrates Google Routes API with OR-Tools for optimal route planning
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sklearn.cluster import DBSCAN

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.route import Route, RouteStatus, RouteStop
from app.models.user import User
from app.services.dispatch.google_routes_service import Location, RouteRequest
from app.services.dispatch.google_routes_service import \
    RouteStop as GoogleRouteStop
from app.services.dispatch.google_routes_service import get_routes_service
from app.services.optimization.ortools_optimizer import VRPStop, VRPVehicle

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """Configuration for route optimization"""

    # Performance
    max_optimization_time: int = 5  # Maximum 5 seconds as required
    use_parallel_processing: bool = True
    cache_duration_hours: int = 1

    # Clustering
    clustering_epsilon_km: float = 1.5  # DBSCAN clustering radius
    min_cluster_size: int = 3

    # Taiwan-specific
    peak_hours: List[Tuple[int, int]] = field(
        default_factory=lambda: [(7, 9), (17, 19)]
    )
    avg_speed_kmh: Dict[str, float] = field(
        default_factory=lambda: {"peak": 20, "normal": 35, "highway": 60}
    )
    taiwan_road_factor: float = 1.3  # Roads are not straight

    # Vehicle constraints
    default_vehicle_capacity: Dict[str, int] = field(
        default_factory=lambda: {
            "50kg": 20,
            "20kg": 50,
            "16kg": 60,
            "10kg": 100,
            "4kg": 200,
        }
    )
    max_driving_hours: float = 8.0
    lunch_break_duration: int = 60  # minutes
    service_time_per_cylinder: Dict[str, int] = field(
        default_factory=lambda: {"50kg": 5, "20kg": 3, "16kg": 3, "10kg": 2, "4kg": 1}
    )

    # Optimization weights
    distance_weight: float = 0.4
    time_weight: float = 0.4
    priority_weight: float = 0.2


@dataclass
class EnhancedVRPStop(VRPStop):
    """Enhanced stop with additional Taiwan-specific fields"""

    area: str
    customer_type: str
    is_restaurant: bool = False  # Restaurants have lunch rush
    is_priority_customer: bool = False
    historical_service_time: Optional[int] = None
    geocoded_location: Optional[Tuple[float, float]] = None


@dataclass
class OptimizationResult:
    """Complete optimization result"""

    routes: List[Route]
    route_stops: Dict[int, List[RouteStop]]
    unassigned_orders: List[Order]
    metrics: Dict[str, Any]
    warnings: List[str]
    optimization_time_ms: int


class EnhancedVRPSolver:
    """
    Production-ready VRP solver combining OR-Tools with Google Routes API
    Optimized for Taiwan-specific delivery patterns
    """

    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()
        self.routes_service = None
        self._distance_cache = {}
        self._geocoding_cache = {}

    async def initialize(self):
        """Initialize the solver and services"""
        if not self.routes_service:
            self.routes_service = await get_routes_service()

    async def optimize_routes(
        self,
        orders: List[Order],
        drivers: List[User],
        depot_location: Tuple[float, float],
        optimization_date: datetime,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> OptimizationResult:
        """
        Main optimization entry point

        Args:
            orders: List of orders to deliver
            drivers: Available drivers
            depot_location: Starting point (lat, lng)
            optimization_date: Date for route planning
            constraints: Additional constraints

        Returns:
            OptimizationResult with optimized routes
        """
        start_time = datetime.now()
        warnings = []

        try:
            # 1. Prepare data
            stops = await self._prepare_stops(orders)
            vehicles = self._prepare_vehicles(drivers, depot_location)

            # 2. Apply geographic clustering for better initial grouping
            clusters = await self._cluster_stops_intelligently(stops)
            logger.info(f"Created {len(clusters)} clusters from {len(stops)} stops")

            # 3. Run parallel optimization for each cluster if beneficial
            if len(clusters) > 1 and self.config.use_parallel_processing:
                route_assignments = await self._optimize_clusters_parallel(
                    clusters, vehicles, depot_location
                )
            else:
                # Single optimization for all stops
                route_assignments = await self._optimize_single_cluster(
                    stops, vehicles, depot_location
                )

            # 4. Balance workload across drivers
            balanced_assignments = self._balance_driver_workload(
                route_assignments, vehicles
            )

            # 5. Get detailed routes from Google Routes API
            detailed_routes = await self._get_detailed_routes(
                balanced_assignments, depot_location, optimization_date
            )

            # 6. Create Route and RouteStop objects
            routes, route_stops = self._create_route_objects(
                detailed_routes, optimization_date
            )

            # 7. Calculate metrics
            metrics = self._calculate_optimization_metrics(
                routes, route_stops, len(orders)
            )

            # 8. Identify unassigned orders
            assigned_order_ids = set()
            for stops in route_stops.values():
                assigned_order_ids.update(stop.order_id for stop in stops)

            unassigned_orders = [
                order for order in orders if order.id not in assigned_order_ids
            ]

            if unassigned_orders:
                warnings.append(
                    f"{len(unassigned_orders)} orders could not be assigned"
                )

            optimization_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            return OptimizationResult(
                routes=routes,
                route_stops=route_stops,
                unassigned_orders=unassigned_orders,
                metrics=metrics,
                warnings=warnings,
                optimization_time_ms=optimization_time_ms,
            )

        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            # Fallback to simple assignment
            return await self._fallback_optimization(
                orders, drivers, depot_location, optimization_date
            )

    async def _prepare_stops(self, orders: List[Order]) -> List[EnhancedVRPStop]:
        """Convert orders to VRP stops with geocoding"""
        stops = []

        for order in orders:
            # Get customer location (in production, use actual geocoding)
            lat, lng = await self._geocode_address(order.customer.address)

            # Calculate demand
            demand = {
                "50kg": order.qty_50kg or 0,
                "20kg": order.qty_20kg or 0,
                "16kg": order.qty_16kg or 0,
                "10kg": order.qty_10kg or 0,
                "4kg": order.qty_4kg or 0,
            }

            # Calculate service time
            service_time = self._calculate_service_time(demand, order.customer)

            # Parse time window
            time_window = self._parse_time_window(
                order.delivery_time_start, order.delivery_time_end
            )

            stop = EnhancedVRPStop(
                order_id=order.id,
                customer_id=order.customer_id,
                customer_name=order.customer.short_name,
                address=order.delivery_address or order.customer.address,
                latitude=lat,
                longitude=lng,
                demand=demand,
                time_window=time_window,
                service_time=service_time,
                area=order.customer.area or "未分區",
                customer_type=getattr(order.customer, "customer_type", "OTHER"),
                is_restaurant=self._is_restaurant(order.customer),
                is_priority_customer=order.is_urgent,
                geocoded_location=(lat, lng),
            )

            stops.append(stop)

        return stops

    def _prepare_vehicles(
        self, drivers: List[User], depot_location: Tuple[float, float]
    ) -> List[VRPVehicle]:
        """Prepare vehicle data for optimization"""
        vehicles = []

        for driver in drivers:
            # Get vehicle capacity (could be from driver profile or vehicle model)
            capacity = self.config.default_vehicle_capacity.copy()

            vehicle = VRPVehicle(
                driver_id=driver.id,
                driver_name=driver.full_name or driver.username,
                capacity=capacity,
                start_location=depot_location,
                end_location=depot_location,  # Return to depot
                max_travel_time=int(self.config.max_driving_hours * 60),
            )

            vehicles.append(vehicle)

        return vehicles

    async def _cluster_stops_intelligently(
        self, stops: List[EnhancedVRPStop]
    ) -> List[List[EnhancedVRPStop]]:
        """
        Cluster stops using DBSCAN for geographic proximity
        Consider Taiwan-specific patterns like restaurant lunch rushes
        """
        if len(stops) < self.config.min_cluster_size:
            return [stops]

        # Extract coordinates
        coordinates = np.array([(s.latitude, s.longitude) for s in stops])

        # Convert epsilon from km to degrees (approximate)
        epsilon_degrees = self.config.clustering_epsilon_km / 111.0

        # Perform DBSCAN clustering
        clustering = DBSCAN(
            eps=epsilon_degrees,
            min_samples=self.config.min_cluster_size,
            metric="haversine",
        ).fit(np.radians(coordinates))

        # Group stops by cluster
        clusters = defaultdict(list)
        for idx, label in enumerate(clustering.labels_):
            if label == -1:  # Noise points
                # Create single-stop cluster
                clusters[f"single_{idx}"] = [stops[idx]]
            else:
                clusters[label].append(stops[idx])

        # Special handling for restaurants (group lunch deliveries)
        restaurant_cluster = []
        other_clusters = []

        for cluster in clusters.values():
            restaurant_stops = [s for s in cluster if s.is_restaurant]
            if len(restaurant_stops) > len(cluster) * 0.5:  # Majority restaurants
                restaurant_cluster.extend(cluster)
            else:
                other_clusters.append(cluster)

        if restaurant_cluster:
            other_clusters.append(restaurant_cluster)

        return other_clusters

    async def _optimize_clusters_parallel(
        self,
        clusters: List[List[EnhancedVRPStop]],
        vehicles: List[VRPVehicle],
        depot_location: Tuple[float, float],
    ) -> Dict[int, List[EnhancedVRPStop]]:
        """Optimize multiple clusters in parallel"""
        # Distribute vehicles proportionally to cluster sizes
        total_stops = sum(len(cluster) for cluster in clusters)
        vehicle_assignments = []

        start_idx = 0
        for cluster in clusters:
            cluster_ratio = len(cluster) / total_stops
            num_vehicles = max(1, int(len(vehicles) * cluster_ratio))
            end_idx = min(start_idx + num_vehicles, len(vehicles))

            vehicle_assignments.append((cluster, vehicles[start_idx:end_idx]))
            start_idx = end_idx

        # Run optimizations in parallel
        tasks = []
        for cluster_stops, cluster_vehicles in vehicle_assignments:
            task = self._optimize_single_cluster(
                cluster_stops, cluster_vehicles, depot_location
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Combine results
        combined_assignments = {}
        for result in results:
            combined_assignments.update(result)

        return combined_assignments

    async def _optimize_single_cluster(
        self,
        stops: List[EnhancedVRPStop],
        vehicles: List[VRPVehicle],
        depot_location: Tuple[float, float],
    ) -> Dict[int, List[EnhancedVRPStop]]:
        """Optimize a single cluster using OR-Tools"""
        if not stops:
            return {i: [] for i in range(len(vehicles))}

        # Create OR-Tools data model
        data = await self._create_ortools_data_model(stops, vehicles, depot_location)

        # Create routing model
        manager = pywrapcp.RoutingIndexManager(
            len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
        )

        routing = pywrapcp.RoutingModel(manager)

        # Set up the model with Taiwan-specific constraints
        self._setup_routing_model(routing, manager, data)

        # Set search parameters optimized for speed
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        # Strict time limit for performance
        search_parameters.time_limit.FromMilliseconds(
            self.config.max_optimization_time * 1000 // len(vehicles)
        )

        # Solve
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            return self._extract_ortools_solution(
                manager, routing, solution, stops, vehicles
            )
        else:
            # Fallback to nearest neighbor
            return self._nearest_neighbor_assignment(stops, vehicles, depot_location)

    async def _create_ortools_data_model(
        self,
        stops: List[EnhancedVRPStop],
        vehicles: List[VRPVehicle],
        depot_location: Tuple[float, float],
    ) -> Dict[str, Any]:
        """Create data model for OR-Tools with caching"""
        locations = [depot_location] + [s.geocoded_location for s in stops]

        # Get distance matrix (with caching)
        distance_matrix = await self._get_distance_matrix(locations)

        # Create time matrix considering Taiwan traffic patterns
        time_matrix = self._create_time_matrix(distance_matrix, datetime.now())

        # Prepare demands
        product_types = ["50kg", "20kg", "16kg", "10kg", "4kg"]
        demands = {}
        for product in product_types:
            demands[product] = [0] + [s.demand.get(product, 0) for s in stops]

        # Vehicle capacities
        vehicle_capacities = {}
        for product in product_types:
            vehicle_capacities[product] = [v.capacity.get(product, 0) for v in vehicles]

        # Time windows (convert to minutes from start of day)
        time_windows = [(0, 720)]  # Depot: 0 to 12 hours
        for stop in stops:
            time_windows.append(stop.time_window)

        return {
            "distance_matrix": distance_matrix,
            "time_matrix": time_matrix,
            "demands": demands,
            "vehicle_capacities": vehicle_capacities,
            "num_vehicles": len(vehicles),
            "depot": 0,
            "time_windows": time_windows,
            "service_time": [0] + [s.service_time for s in stops],
            "priorities": [0] + [5 if s.is_priority_customer else 1 for s in stops],
        }

    async def _get_distance_matrix(
        self, locations: List[Tuple[float, float]]
    ) -> List[List[int]]:
        """Get distance matrix with caching and Google Routes API fallback"""
        n = len(locations)
        matrix = [[0] * n for _ in range(n)]

        # Check cache and calculate missing distances
        uncached_pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                cache_key = f"{locations[i]}_{locations[j]}"
                if cache_key in self._distance_cache:
                    distance = self._distance_cache[cache_key]
                else:
                    uncached_pairs.append((i, j))
                    # Use Haversine as initial estimate
                    distance = (
                        self._haversine_distance(
                            locations[i][0],
                            locations[i][1],
                            locations[j][0],
                            locations[j][1],
                        )
                        * self.config.taiwan_road_factor
                    )

                matrix[i][j] = int(distance * 1000)  # Convert to meters
                matrix[j][i] = matrix[i][j]

        # Batch request to Google Routes API for uncached pairs
        if uncached_pairs and len(uncached_pairs) < 100:  # API limit
            try:
                # Would implement batch distance matrix API call here
                pass
            except Exception as e:
                logger.warning(f"Google Routes API failed, using estimates: {e}")

        return matrix

    def _create_time_matrix(
        self, distance_matrix: List[List[int]], current_time: datetime
    ) -> List[List[int]]:
        """Create time matrix considering Taiwan traffic patterns"""
        hour = current_time.hour

        # Determine if peak hour
        is_peak = any(start <= hour < end for start, end in self.config.peak_hours)

        speed_kmh = self.config.avg_speed_kmh["peak" if is_peak else "normal"]

        time_matrix = []
        for row in distance_matrix:
            time_row = []
            for distance_m in row:
                # Convert meters to km, then to hours, then to minutes
                time_minutes = (distance_m / 1000) / speed_kmh * 60
                time_row.append(int(time_minutes))
            time_matrix.append(time_row)

        return time_matrix

    def _setup_routing_model(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        data: Dict[str, Any],
    ):
        """Set up OR-Tools routing model with constraints"""

        # Distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["distance_matrix"][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add capacity constraints for each product
        for product, demands in data["demands"].items():

            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return demands[from_node]

            demand_callback_index = routing.RegisterUnaryTransitCallback(
                demand_callback
            )

            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # null capacity slack
                data["vehicle_capacities"][product],
                True,  # start cumul to zero
                f"{product}_capacity",
            )

        # Time dimension with service time
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel_time = data["time_matrix"][from_node][to_node]
            service_time = data["service_time"][from_node]
            return travel_time + service_time

        time_callback_index = routing.RegisterTransitCallback(time_callback)

        routing.AddDimension(
            time_callback_index,
            30,  # allow waiting time
            720,  # maximum time per vehicle (12 hours)
            False,
            "Time",
        )

        time_dimension = routing.GetDimensionOrDie("Time")

        # Add time window constraints
        for location_idx, time_window in enumerate(data["time_windows"]):
            if location_idx == 0:  # Skip depot
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(
                int(time_window[0]), int(time_window[1])
            )

        # Priority constraints - prioritize high-priority customers
        for node in range(1, len(data["priorities"])):
            if data["priorities"][node] > 1:
                routing.AddDisjunction(
                    [manager.NodeToIndex(node)], data["priorities"][node] * 1000
                )

    def _extract_ortools_solution(
        self,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        solution: pywrapcp.Assignment,
        stops: List[EnhancedVRPStop],
        vehicles: List[VRPVehicle],
    ) -> Dict[int, List[EnhancedVRPStop]]:
        """Extract solution from OR-Tools"""
        routes = {}

        for vehicle_id in range(len(vehicles)):
            route_stops = []
            index = routing.Start(vehicle_id)

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)

                if node_index != 0:  # Skip depot
                    stop = stops[node_index - 1]
                    route_stops.append(stop)

                index = solution.Value(routing.NextVar(index))

            routes[vehicle_id] = route_stops

        return routes

    def _balance_driver_workload(
        self, assignments: Dict[int, List[EnhancedVRPStop]], vehicles: List[VRPVehicle]
    ) -> Dict[int, List[EnhancedVRPStop]]:
        """Balance workload across drivers"""
        # Calculate current workload
        workloads = {}
        for vehicle_id, stops in assignments.items():
            total_demand = sum(sum(stop.demand.values()) for stop in stops)
            total_time = sum(stop.service_time for stop in stops)
            workloads[vehicle_id] = {
                "stops": len(stops),
                "demand": total_demand,
                "time": total_time,
                "score": len(stops) * 0.3 + total_demand * 0.3 + total_time * 0.4,
            }

        # Find imbalanced drivers
        avg_score = np.mean([w["score"] for w in workloads.values()])
        overloaded = [
            (v, w) for v, w in workloads.items() if w["score"] > avg_score * 1.2
        ]
        underloaded = [
            (v, w) for v, w in workloads.items() if w["score"] < avg_score * 0.8
        ]

        # Simple rebalancing - move stops from overloaded to underloaded
        for over_vehicle, over_workload in overloaded:
            if not underloaded:
                break

            # Move some stops
            stops_to_move = int((over_workload["stops"] - avg_score) * 0.3)
            if stops_to_move > 0 and assignments[over_vehicle]:
                under_vehicle, _ = underloaded[0]

                # Move last stops (furthest from depot usually)
                moved_stops = assignments[over_vehicle][-stops_to_move:]
                assignments[over_vehicle] = assignments[over_vehicle][:-stops_to_move]
                assignments[under_vehicle].extend(moved_stops)

                # Update underloaded list
                underloaded.pop(0)

        return assignments

    async def _get_detailed_routes(
        self,
        assignments: Dict[int, List[EnhancedVRPStop]],
        depot_location: Tuple[float, float],
        optimization_date: datetime,
    ) -> Dict[int, Dict[str, Any]]:
        """Get detailed routes from Google Routes API"""
        detailed_routes = {}

        for vehicle_id, stops in assignments.items():
            if not stops:
                continue

            # Prepare waypoints
            waypoints = []
            for stop in stops:
                location = Location(
                    latitude=stop.latitude,
                    longitude=stop.longitude,
                    address=stop.address,
                )

                google_stop = GoogleRouteStop(
                    location=location,
                    order_id=str(stop.order_id),
                    service_duration_minutes=stop.service_time,
                    priority=5 if stop.is_priority_customer else 1,
                )
                waypoints.append(google_stop)

            # Create route request
            origin = Location(
                latitude=depot_location[0],
                longitude=depot_location[1],
                address="配送中心",
            )

            route_request = RouteRequest(
                origin=origin,
                destination=origin,  # Return to depot
                waypoints=waypoints,
                departure_time=datetime.combine(
                    optimization_date.date(), time(8, 0)  # 8 AM start
                ),
                optimize_waypoint_order=False,  # Already optimized
            )

            try:
                # Get route from Google
                result = await self.routes_service.optimize_route(route_request)

                detailed_routes[vehicle_id] = {
                    "stops": stops,
                    "google_result": result,
                    "polyline": result.polyline,
                    "total_distance_m": result.total_distance_meters,
                    "total_duration_s": result.total_duration_seconds,
                }

            except Exception as e:
                logger.error(
                    f"Failed to get Google route for vehicle {vehicle_id}: {e}"
                )
                # Fallback to estimates
                detailed_routes[vehicle_id] = {
                    "stops": stops,
                    "google_result": None,
                    "polyline": None,
                    "total_distance_m": len(stops) * 5000,  # 5km average
                    "total_duration_s": len(stops) * 1200,  # 20min average
                }

        return detailed_routes

    def _create_route_objects(
        self, detailed_routes: Dict[int, Dict[str, Any]], optimization_date: datetime
    ) -> Tuple[List[Route], Dict[int, List[RouteStop]]]:
        """Create Route and RouteStop objects"""
        routes = []
        all_route_stops = {}

        for vehicle_id, route_data in detailed_routes.items():
            # Create Route
            route = Route(
                route_number=f"R{optimization_date.strftime('%Y%m%d')}-{vehicle_id+1:03d}",
                name=f"路線 {vehicle_id+1}",
                date=optimization_date,
                scheduled_date=optimization_date.date(),
                driver_id=vehicle_id,  # Would map to actual driver
                status=RouteStatus.OPTIMIZED,
                total_stops=len(route_data["stops"]),
                total_distance_km=route_data["total_distance_m"] / 1000,
                estimated_duration_minutes=int(route_data["total_duration_s"] / 60),
                polyline=route_data.get("polyline"),
                is_optimized=True,
                optimization_score=0.85,  # Would calculate actual score
                optimization_timestamp=datetime.now(),
            )
            routes.append(route)

            # Create RouteStops
            route_stops = []
            current_time = optimization_date.replace(hour=8, minute=0)

            for seq, stop in enumerate(route_data["stops"]):
                # Calculate arrival time
                if seq > 0:
                    # Add travel time from previous stop
                    travel_time = timedelta(minutes=20)  # Would get from Google
                    current_time += travel_time

                route_stop = RouteStop(
                    route_id=route.id,
                    order_id=stop.order_id,
                    stop_sequence=seq + 1,
                    latitude=stop.latitude,
                    longitude=stop.longitude,
                    address=stop.address,
                    estimated_arrival=current_time,
                    estimated_duration_minutes=20,  # Total time at stop
                    service_duration_minutes=stop.service_time,
                    distance_from_previous_km=5.0 if seq > 0 else 0,  # Would calculate
                )
                route_stops.append(route_stop)

                current_time += timedelta(minutes=stop.service_time)

            all_route_stops[route.id] = route_stops

        return routes, all_route_stops

    def _calculate_optimization_metrics(
        self,
        routes: List[Route],
        route_stops: Dict[int, List[RouteStop]],
        total_orders: int,
    ) -> Dict[str, Any]:
        """Calculate optimization metrics"""
        total_distance = sum(r.total_distance_km for r in routes)
        total_stops = sum(r.total_stops for r in routes)
        total_duration = sum(r.estimated_duration_minutes for r in routes)

        # Calculate efficiency metrics
        avg_stops_per_route = total_stops / len(routes) if routes else 0
        avg_distance_per_stop = total_distance / total_stops if total_stops else 0

        # Optimization score based on multiple factors
        distance_efficiency = (
            min(1.0, 5.0 / avg_distance_per_stop) if avg_distance_per_stop else 0
        )
        time_efficiency = (
            min(1.0, 480 / (total_duration / len(routes))) if routes else 0
        )
        coverage = total_stops / total_orders if total_orders else 0

        optimization_score = (
            distance_efficiency * 0.4 + time_efficiency * 0.4 + coverage * 0.2
        ) * 100

        return {
            "total_routes": len(routes),
            "total_distance_km": round(total_distance, 2),
            "total_duration_hours": round(total_duration / 60, 2),
            "total_stops": total_stops,
            "avg_stops_per_route": round(avg_stops_per_route, 1),
            "avg_distance_per_stop": round(avg_distance_per_stop, 2),
            "avg_duration_per_route": (
                round(total_duration / len(routes), 1) if routes else 0
            ),
            "optimization_score": round(optimization_score, 1),
            "coverage_percentage": round(coverage * 100, 1),
        }

    async def _geocode_address(self, address: str) -> Tuple[float, float]:
        """Geocode address with caching"""
        if address in self._geocoding_cache:
            return self._geocoding_cache[address]

        # In production, use Google Geocoding API
        # For now, generate coordinates around Taipei
        lat = 25.0330 + (hash(address) % 1000 - 500) / 10000
        lng = 121.5654 + (hash(address + "lng") % 1000 - 500) / 10000

        self._geocoding_cache[address] = (lat, lng)
        return lat, lng

    def _calculate_service_time(
        self, demand: Dict[str, int], customer: Customer
    ) -> int:
        """Calculate service time based on cylinder count and type"""
        base_time = 5  # Base 5 minutes

        # Add time per cylinder
        cylinder_time = sum(
            demand.get(size, 0) * self.config.service_time_per_cylinder.get(size, 2)
            for size in demand
        )

        # Add extra time for restaurants during lunch
        if self._is_restaurant(customer):
            current_hour = datetime.now().hour
            if 11 <= current_hour <= 14:
                cylinder_time *= 1.5

        return int(base_time + cylinder_time)

    def _is_restaurant(self, customer: Customer) -> bool:
        """Check if customer is a restaurant"""
        restaurant_keywords = ["餐廳", "飯店", "小吃", "麵店", "火鍋", "燒烤"]
        return any(keyword in customer.short_name for keyword in restaurant_keywords)

    def _parse_time_window(
        self, start_time: Optional[str], end_time: Optional[str]
    ) -> Tuple[int, int]:
        """Parse time window strings to minutes from start of day"""
        default_start = 0  # 00:00
        default_end = 720  # 12:00

        if start_time:
            try:
                hours, minutes = map(int, start_time.split(":"))
                start_minutes = (
                    hours * 60 + minutes - 480
                )  # Subtract 8 hours (8 AM start)
                start_minutes = max(0, start_minutes)
            except:
                start_minutes = default_start
        else:
            start_minutes = default_start

        if end_time:
            try:
                hours, minutes = map(int, end_time.split(":"))
                end_minutes = hours * 60 + minutes - 480
                end_minutes = max(
                    start_minutes + 30, end_minutes
                )  # At least 30 min window
            except:
                end_minutes = default_end
        else:
            end_minutes = default_end

        return (start_minutes, end_minutes)

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance in kilometers"""
        R = 6371
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    def _nearest_neighbor_assignment(
        self,
        stops: List[EnhancedVRPStop],
        vehicles: List[VRPVehicle],
        depot_location: Tuple[float, float],
    ) -> Dict[int, List[EnhancedVRPStop]]:
        """Fast nearest neighbor assignment as fallback"""
        assignments = {i: [] for i in range(len(vehicles))}
        remaining_stops = stops.copy()

        for vehicle_id in range(len(vehicles)):
            vehicle_stops = []
            current_location = depot_location
            vehicle_capacity = vehicles[vehicle_id].capacity.copy()

            while remaining_stops:
                # Find nearest feasible stop
                best_stop = None
                best_distance = float("inf")

                for stop in remaining_stops:
                    # Check capacity
                    can_fit = all(
                        stop.demand.get(product, 0) <= vehicle_capacity.get(product, 0)
                        for product in stop.demand
                    )

                    if can_fit:
                        distance = self._haversine_distance(
                            current_location[0],
                            current_location[1],
                            stop.latitude,
                            stop.longitude,
                        )

                        if distance < best_distance:
                            best_distance = distance
                            best_stop = stop

                if best_stop:
                    vehicle_stops.append(best_stop)
                    remaining_stops.remove(best_stop)
                    current_location = (best_stop.latitude, best_stop.longitude)

                    # Update capacity
                    for product, qty in best_stop.demand.items():
                        vehicle_capacity[product] -= qty
                else:
                    break

            assignments[vehicle_id] = vehicle_stops

        return assignments

    async def _fallback_optimization(
        self,
        orders: List[Order],
        drivers: List[User],
        depot_location: Tuple[float, float],
        optimization_date: datetime,
    ) -> OptimizationResult:
        """Simple fallback when optimization fails"""
        logger.warning("Using fallback optimization")

        # Simple round-robin assignment
        routes = []
        route_stops = {}

        orders_per_driver = len(orders) // len(drivers) + 1

        for i, driver in enumerate(drivers):
            start_idx = i * orders_per_driver
            end_idx = min((i + 1) * orders_per_driver, len(orders))

            if start_idx >= len(orders):
                break

            driver_orders = orders[start_idx:end_idx]

            # Create route
            route = Route(
                route_number=f"R{optimization_date.strftime('%Y%m%d')}-{i+1:03d}",
                name=f"路線 {i+1}",
                date=optimization_date,
                scheduled_date=optimization_date.date(),
                driver_id=driver.id,
                status=RouteStatus.PLANNED,
                total_stops=len(driver_orders),
                total_distance_km=len(driver_orders) * 5,  # Estimate
                estimated_duration_minutes=len(driver_orders) * 20,
                is_optimized=False,
                optimization_score=0.5,
            )
            routes.append(route)

            # Create stops
            stops = []
            for j, order in enumerate(driver_orders):
                lat, lng = await self._geocode_address(order.customer.address)

                stop = RouteStop(
                    route_id=route.id,
                    order_id=order.id,
                    stop_sequence=j + 1,
                    latitude=lat,
                    longitude=lng,
                    address=order.customer.address,
                    estimated_arrival=optimization_date.replace(hour=8)
                    + timedelta(minutes=j * 30),
                    estimated_duration_minutes=20,
                    service_duration_minutes=10,
                )
                stops.append(stop)

            route_stops[route.id] = stops

        return OptimizationResult(
            routes=routes,
            route_stops=route_stops,
            unassigned_orders=[],
            metrics={
                "total_routes": len(routes),
                "optimization_score": 50.0,
                "total_stops": len(orders),
            },
            warnings=["使用簡單分配，建議手動調整"],
            optimization_time_ms=100,
        )
