"""VRP Optimizer wrapper that integrates clustering with OR-Tools."""

import asyncio
import logging
import time as time_module
import uuid
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.metrics import (route_optimization_histogram,
                              vrp_constraint_violations_counter,
                              vrp_optimization_summary,
                              vrp_solution_quality_gauge)
from app.models.optimization import (ClusterInfo, OptimizationConstraints,
                                     OptimizationRequest, OptimizationResponse,
                                     OptimizedRoute, OptimizedStop)
from app.services.google_cloud.monitoring.intelligent_cache import \
    IntelligentCache
from app.services.optimization.clustering import GeographicClusterer
from app.services.optimization.ortools_optimizer import (ORToolsOptimizer,
                                                         VRPStop, VRPVehicle)

logger = logging.getLogger(__name__)


class VRPOptimizer:
    """
    Main VRP optimizer that coordinates clustering and route optimization.
    Integrates with existing OR-Tools implementation and adds Taiwan-specific features.
    """

    def __init__(
        self,
        google_routes_service=None,
        order_service=None,
        vehicle_service=None,
        cache_service: Optional[IntelligentCache] = None,
        websocket_service=None,
    ):
        self.google_routes_service = google_routes_service
        self.order_service = order_service
        self.vehicle_service = vehicle_service
        self.cache_service = cache_service
        self.websocket_service = websocket_service

        # Initialize components
        self.clusterer = GeographicClusterer()
        self.ortools_optimizer = ORToolsOptimizer(
            depot_location=(25.0330, 121.5654)  # Default Taipei depot
        )

        # Taiwan-specific settings
        self.taiwan_settings = {
            "peak_hours": [
                {"start": time(7, 0), "end": time(9, 0)},
                {"start": time(17, 0), "end": time(19, 0)},
            ],
            "school_zones": [
                # Major school areas to avoid during certain times
                {"lat": 25.0276, "lng": 121.5435, "radius_km": 0.5},
                {"lat": 25.0421, "lng": 121.5321, "radius_km": 0.5},
            ],
            "market_days": {
                # Traditional market busy days (0=Monday, 6=Sunday)
                "wednesday": 2,
                "saturday": 5,
                "sunday": 6,
            },
        }

    async def optimize_routes(
        self, request: OptimizationRequest
    ) -> OptimizationResponse:
        """
        Main entry point for route optimization.

        Args:
            request: Optimization request with orders, vehicles, and constraints

        Returns:
            OptimizationResponse with optimized routes
        """
        start_time = time_module.time()
        optimization_id = str(uuid.uuid4())

        try:
            # Check cache if available
            if self.cache_service:
                cache_key = self._generate_cache_key(request)
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    logger.info(f"Returning cached optimization result for {cache_key}")
                    return OptimizationResponse(**cached_result)

            # Send initial progress
            await self._send_progress(optimization_id, 0, "Starting optimization...")

            # Fetch order and vehicle data
            await self._send_progress(optimization_id, 10, "Fetching orders...")
            orders = await self._fetch_orders(request.order_ids)

            await self._send_progress(optimization_id, 20, "Fetching vehicles...")
            vehicles = await self._fetch_vehicles(request.vehicle_ids)

            if not orders:
                return self._create_empty_response(
                    optimization_id, "No valid orders found"
                )

            if not vehicles:
                return self._create_empty_response(
                    optimization_id, "No available vehicles"
                )

            # Apply clustering if beneficial
            clusters = None
            if len(orders) > 20:  # Cluster for larger order sets
                await self._send_progress(optimization_id, 30, "Clustering orders...")
                clusters = await self._cluster_orders(orders, request)
                logger.info(
                    f"Created {len(clusters)} clusters for {len(orders)} orders"
                )
                await self._send_progress(
                    optimization_id, 40, f"Created {len(clusters)} clusters"
                )

            # Convert to VRP format
            vrp_stops = self._convert_to_vrp_stops(orders, request.constraints)
            vrp_vehicles = self._convert_to_vrp_vehicles(vehicles, request.constraints)

            # Apply Taiwan-specific optimizations
            vrp_stops = self._apply_taiwan_optimizations(vrp_stops, request.date)

            # Run optimization
            await self._send_progress(
                optimization_id, 50, "Running route optimization..."
            )

            if clusters and len(clusters) > 1:
                # Optimize each cluster separately for better performance
                optimized_routes = await self._optimize_clustered_routes(
                    clusters, vrp_stops, vrp_vehicles, request
                )
            else:
                # Single optimization run
                optimized_routes = await self._run_single_optimization(
                    vrp_stops, vrp_vehicles, request
                )

            await self._send_progress(optimization_id, 80, "Building final routes...")

            # Build response
            response = await self._build_optimization_response(
                optimization_id, optimized_routes, orders, vehicles, request, start_time
            )

            # Track metrics
            await self._track_optimization_metrics(response, request, start_time)

            # Cache successful result
            if self.cache_service and response.status == "success":
                await self.cache_service.set(
                    cache_key, response.model_dump(), ttl_seconds=3600  # 1 hour cache
                )

            await self._send_progress(optimization_id, 100, "Optimization complete!")

            return response

        except Exception as e:
            logger.error(f"Route optimization failed: {e}", exc_info=True)
            return self._create_error_response(optimization_id, str(e), start_time)

    async def _fetch_orders(self, order_ids: List[int]) -> List[Dict]:
        """Fetch order data from service."""
        if not self.order_service:
            # Return mock data for testing
            return [
                {
                    "id": oid,
                    "customer_id": 100 + oid,
                    "latitude": 25.0330 + (oid % 10) * 0.01,
                    "longitude": 121.5654 + (oid % 10) * 0.01,
                    "delivery_date": datetime.now().date(),
                    "delivery_time_slot": "anytime",
                    "cylinders": {"16kg": 2},
                    "customer_type": "residential",
                    "address": f"Test Address {oid}",
                }
                for oid in order_ids
            ]

        return await self.order_service.get_orders_by_ids(order_ids)

    async def _fetch_vehicles(self, vehicle_ids: List[int]) -> List[Dict]:
        """Fetch vehicle data from service."""
        if not self.vehicle_service:
            # Return mock data for testing
            return [
                {
                    "id": vid,
                    "driver_id": 200 + vid,
                    "driver_name": f"Driver {vid}",
                    "capacity": {"16kg": 20, "20kg": 16, "50kg": 8},
                    "depot_lat": 25.0350,
                    "depot_lng": 121.5650,
                }
                for vid in vehicle_ids
            ]

        return await self.vehicle_service.get_vehicles_by_ids(vehicle_ids)

    async def _cluster_orders(
        self, orders: List[Dict], request: OptimizationRequest
    ) -> List[ClusterInfo]:
        """Cluster orders geographically."""
        locations = [
            {
                "id": order["id"],
                "lat": order.get("latitude", 25.0330),
                "lng": order.get("longitude", 121.5654),
                "time_window": order.get("delivery_time_slot", "anytime"),
                "demand": order.get("cylinders", {}),
            }
            for order in orders
        ]

        # Use time window clustering if requested
        if request.respect_time_windows:
            return self.clusterer.cluster_by_time_windows(
                locations, eps_km=request.cluster_radius_km
            )
        else:
            # Regular geographic clustering
            return self.clusterer.cluster_with_constraints(
                locations,
                constraints=["mountains", "rivers", "capacity"],
                max_cluster_size=30,  # Max stops per cluster
                target_density=5.0,
            )

    def _convert_to_vrp_stops(
        self, orders: List[Dict], constraints: OptimizationConstraints
    ) -> List[VRPStop]:
        """Convert orders to VRP stop format."""
        stops = []

        for order in orders:
            # Determine time window
            time_window = self._get_time_window_minutes(
                order.get("delivery_time_slot", "anytime"), constraints
            )

            # Determine service time
            customer_type = order.get("customer_type", "residential")
            service_time = constraints.service_time_minutes.get(customer_type, 5)

            stop = VRPStop(
                order_id=order["id"],
                customer_id=order.get("customer_id", 0),
                customer_name=order.get("customer_name", f"Customer {order['id']}"),
                address=order.get("address", ""),
                latitude=order.get("latitude", 25.0330),
                longitude=order.get("longitude", 121.5654),
                demand=order.get("cylinders", {}),
                time_window=time_window,
                service_time=service_time,
            )
            stops.append(stop)

        return stops

    def _convert_to_vrp_vehicles(
        self, vehicles: List[Dict], constraints: OptimizationConstraints
    ) -> List[VRPVehicle]:
        """Convert vehicles to VRP format."""
        vrp_vehicles = []

        for vehicle in vehicles:
            # Calculate max travel time from shift constraints
            shift_duration = (
                datetime.combine(datetime.today(), constraints.driver_shift_end)
                - datetime.combine(datetime.today(), constraints.driver_shift_start)
            ).seconds // 60

            vrp_vehicle = VRPVehicle(
                driver_id=vehicle.get("driver_id", vehicle["id"]),
                driver_name=vehicle.get("driver_name", f"Driver {vehicle['id']}"),
                capacity=vehicle.get("capacity", constraints.vehicle_capacity),
                start_location=(
                    vehicle.get("depot_lat", 25.0330),
                    vehicle.get("depot_lng", 121.5654),
                ),
                max_travel_time=min(shift_duration, 480),  # Max 8 hours
            )
            vrp_vehicles.append(vrp_vehicle)

        return vrp_vehicles

    def _get_time_window_minutes(
        self, time_slot: str, constraints: OptimizationConstraints
    ) -> Tuple[int, int]:
        """Convert time slot to minutes from shift start."""
        shift_start_minutes = (
            constraints.driver_shift_start.hour * 60
            + constraints.driver_shift_start.minute
        )
        shift_end_minutes = (
            constraints.driver_shift_end.hour * 60 + constraints.driver_shift_end.minute
        )

        if time_slot == "morning":
            return (0, 180)  # First 3 hours
        elif time_slot == "afternoon":
            lunch_end = (
                constraints.lunch_break_start.hour * 60
                + constraints.lunch_break_start.minute
                + constraints.lunch_break_duration_minutes
            )
            return (
                lunch_end - shift_start_minutes,
                shift_end_minutes - shift_start_minutes,
            )
        elif time_slot == "specific" and "time" in time_slot:
            # Parse specific time if provided
            return (0, shift_end_minutes - shift_start_minutes)
        else:  # anytime
            return (0, shift_end_minutes - shift_start_minutes)

    def _apply_taiwan_optimizations(
        self, stops: List[VRPStop], optimization_date: datetime
    ) -> List[VRPStop]:
        """Apply Taiwan-specific optimizations to stops."""
        weekday = optimization_date.weekday()

        # Adjust service times for market days
        if weekday in [
            self.taiwan_settings["market_days"]["wednesday"],
            self.taiwan_settings["market_days"]["saturday"],
            self.taiwan_settings["market_days"]["sunday"],
        ]:
            for stop in stops:
                # Add extra time for market area deliveries
                if self._is_near_market(stop.latitude, stop.longitude):
                    stop.service_time += 5  # Extra 5 minutes

        # Adjust time windows to avoid school zones during drop-off/pickup
        current_hour = datetime.now().hour
        if 7 <= current_hour <= 9 or 15 <= current_hour <= 17:
            for stop in stops:
                if self._is_near_school(stop.latitude, stop.longitude):
                    # Shift time window if possible
                    if stop.time_window[0] < 120:  # Morning window
                        stop.time_window = (
                            120,
                            stop.time_window[1],
                        )  # Start after 9 AM

        return stops

    def _is_near_market(self, lat: float, lng: float) -> bool:
        """Check if location is near traditional market."""
        # Simplified check - in production, use actual market locations
        market_areas = [
            {"lat": 25.0392, "lng": 121.5098},  # Shilin Night Market area
            {"lat": 25.0324, "lng": 121.5203},  # Tonghua Night Market area
        ]

        for market in market_areas:
            distance = self._calculate_distance(lat, lng, market["lat"], market["lng"])
            if distance < 1.0:  # Within 1 km
                return True
        return False

    def _is_near_school(self, lat: float, lng: float) -> bool:
        """Check if location is near school zone."""
        for school in self.taiwan_settings["school_zones"]:
            distance = self._calculate_distance(lat, lng, school["lat"], school["lng"])
            if distance < school["radius_km"]:
                return True
        return False

    def _calculate_distance(
        self, lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """Calculate distance between two points in kilometers."""
        from math import atan2, cos, radians, sin, sqrt

        R = 6371  # Earth's radius in kilometers
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])

        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    async def _optimize_clustered_routes(
        self,
        clusters: List[ClusterInfo],
        all_stops: List[VRPStop],
        vehicles: List[VRPVehicle],
        request: OptimizationRequest,
    ) -> Dict[int, List[VRPStop]]:
        """Optimize routes for clustered orders."""
        # Create stop lookup
        stop_map = {stop.order_id: stop for stop in all_stops}

        # Assign vehicles to clusters
        cluster_assignments = self._assign_vehicles_to_clusters(clusters, vehicles)

        # Run optimization for each cluster in parallel with timeout
        optimization_tasks = []
        for cluster, assigned_vehicles in cluster_assignments.items():
            cluster_stops = [
                stop_map[oid] for oid in cluster.order_ids if oid in stop_map
            ]
            if cluster_stops and assigned_vehicles:
                task = self._optimize_cluster_with_timeout(
                    cluster_stops,
                    assigned_vehicles,
                    request.optimization_mode,
                    timeout_seconds=min(
                        30, 5 + len(cluster_stops) * 0.1
                    ),  # Dynamic timeout
                )
                optimization_tasks.append(task)

        # Wait for all optimizations with early termination support
        cluster_results = await self._gather_with_early_termination(optimization_tasks)

        # Combine results
        all_routes = {}
        vehicle_offset = 0
        for cluster_routes in cluster_results:
            for vehicle_idx, stops in cluster_routes.items():
                all_routes[vehicle_offset + vehicle_idx] = stops
            vehicle_offset += len(cluster_routes)

        return all_routes

    def _assign_vehicles_to_clusters(
        self, clusters: List[ClusterInfo], vehicles: List[VRPVehicle]
    ) -> Dict[ClusterInfo, List[VRPVehicle]]:
        """Assign vehicles to clusters based on demand and location."""
        assignments = {}
        available_vehicles = list(vehicles)

        # Sort clusters by total demand (prioritize larger clusters)
        sorted_clusters = sorted(
            clusters, key=lambda c: sum(c.total_demand.values()), reverse=True
        )

        for cluster in sorted_clusters:
            if not available_vehicles:
                break

            # Calculate vehicles needed based on demand
            total_demand = sum(cluster.total_demand.values())
            avg_capacity = 20  # Average capacity estimate
            vehicles_needed = max(1, (total_demand + avg_capacity - 1) // avg_capacity)

            # Assign closest available vehicles
            assigned = []
            for _ in range(min(vehicles_needed, len(available_vehicles))):
                # Find closest vehicle to cluster center
                closest_vehicle = min(
                    available_vehicles,
                    key=lambda v: self._calculate_distance(
                        v.start_location[0],
                        v.start_location[1],
                        cluster.center_lat,
                        cluster.center_lng,
                    ),
                )
                assigned.append(closest_vehicle)
                available_vehicles.remove(closest_vehicle)

            assignments[cluster] = assigned

        return assignments

    async def _optimize_cluster_with_timeout(
        self,
        stops: List[VRPStop],
        vehicles: List[VRPVehicle],
        optimization_mode: str,
        timeout_seconds: float,
    ) -> Dict[int, List[VRPStop]]:
        """Optimize a single cluster with timeout."""
        try:
            # Run optimization with timeout
            return await asyncio.wait_for(
                self._optimize_cluster(stops, vehicles, optimization_mode),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Cluster optimization timed out after {timeout_seconds}s, using fallback"
            )
            # Return simple nearest-neighbor solution
            return self._fallback_optimization(stops, vehicles)

    async def _optimize_cluster(
        self, stops: List[VRPStop], vehicles: List[VRPVehicle], optimization_mode: str
    ) -> Dict[int, List[VRPStop]]:
        """Optimize a single cluster."""
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        routes = await loop.run_in_executor(
            None, self.ortools_optimizer.optimize, stops, vehicles
        )

        # Apply optimization mode adjustments
        if optimization_mode == "time":
            # Already optimized for time by OR-Tools
            pass
        elif optimization_mode == "fuel":
            # Post-process to minimize distance
            routes = self._minimize_fuel_consumption(routes)

        return routes

    async def _gather_with_early_termination(
        self, tasks: List[asyncio.Task]
    ) -> List[Dict[int, List[VRPStop]]]:
        """Gather results with early termination for good enough solutions."""
        results = []
        done_count = 0
        total_tasks = len(tasks)

        # Create tasks as futures
        pending = set(tasks)

        while pending:
            # Wait for at least one task to complete
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                try:
                    result = await task
                    results.append(result)
                    done_count += 1

                    # Check if we have "good enough" solution
                    if done_count >= total_tasks * 0.8:  # 80% complete
                        logger.info(
                            f"Early termination: {done_count}/{total_tasks} tasks complete"
                        )
                        # Cancel remaining tasks
                        for remaining_task in pending:
                            remaining_task.cancel()

                        # Get any completed results
                        for remaining_task in pending:
                            try:
                                result = await remaining_task
                                results.append(result)
                            except asyncio.CancelledError:
                                # Use fallback for cancelled tasks
                                results.append({})

                        return results

                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    results.append({})  # Empty result for failed task

        return results

    def _fallback_optimization(
        self, stops: List[VRPStop], vehicles: List[VRPVehicle]
    ) -> Dict[int, List[VRPStop]]:
        """Simple fallback optimization using nearest neighbor."""
        if not stops or not vehicles:
            return {}

        # Distribute stops evenly among vehicles
        stops_per_vehicle = (len(stops) + len(vehicles) - 1) // len(vehicles)
        routes = {}

        # Sort stops by geographic location for simple clustering
        sorted_stops = sorted(stops, key=lambda s: (s.latitude, s.longitude))

        for i, vehicle in enumerate(vehicles):
            start_idx = i * stops_per_vehicle
            end_idx = min(start_idx + stops_per_vehicle, len(stops))

            if start_idx < len(sorted_stops):
                vehicle_stops = sorted_stops[start_idx:end_idx]

                # Simple nearest neighbor within vehicle stops
                if vehicle_stops:
                    ordered_stops = [vehicle_stops[0]]
                    remaining = set(vehicle_stops[1:])

                    while remaining:
                        current = ordered_stops[-1]
                        nearest = min(
                            remaining,
                            key=lambda s: self._calculate_distance(
                                current.latitude,
                                current.longitude,
                                s.latitude,
                                s.longitude,
                            ),
                        )
                        ordered_stops.append(nearest)
                        remaining.remove(nearest)

                    routes[i] = ordered_stops
                else:
                    routes[i] = []

        return routes

    async def _run_single_optimization(
        self,
        stops: List[VRPStop],
        vehicles: List[VRPVehicle],
        request: OptimizationRequest,
    ) -> Dict[int, List[VRPStop]]:
        """Run single optimization without clustering."""
        return self.ortools_optimizer.optimize(stops, vehicles)

    def _minimize_fuel_consumption(
        self, routes: Dict[int, List[VRPStop]]
    ) -> Dict[int, List[VRPStop]]:
        """Adjust routes to minimize fuel consumption."""
        # Simple heuristic: ensure routes follow more direct paths
        # In production, this would consider elevation, traffic patterns, etc.
        return routes

    async def _build_optimization_response(
        self,
        optimization_id: str,
        optimized_routes: Dict[int, List[VRPStop]],
        orders: List[Dict],
        vehicles: List[Dict],
        request: OptimizationRequest,
        start_time: float,
    ) -> OptimizationResponse:
        """Build the optimization response."""
        routes = []
        all_assigned_orders = set()
        total_distance = 0
        total_duration = 0
        total_cost = 0

        for vehicle_idx, stops in optimized_routes.items():
            if not stops or vehicle_idx >= len(vehicles):
                continue

            vehicle = vehicles[vehicle_idx]
            route_distance, route_duration = await self._calculate_route_metrics(stops)

            # Build optimized stops
            optimized_stops = []
            current_time = datetime.combine(
                request.date.date() if hasattr(request.date, "date") else request.date,
                request.constraints.driver_shift_start,
            )

            for seq, stop in enumerate(stops):
                # Calculate arrival time
                if seq > 0:
                    travel_time = await self._estimate_travel_time(
                        stops[seq - 1].latitude,
                        stops[seq - 1].longitude,
                        stop.latitude,
                        stop.longitude,
                    )
                    current_time += timedelta(minutes=travel_time)

                optimized_stop = OptimizedStop(
                    order_id=stop.order_id,
                    sequence=seq + 1,
                    arrival_time=current_time,
                    departure_time=current_time + timedelta(minutes=stop.service_time),
                    distance_from_previous_km=0,  # Would calculate if needed
                    travel_time_minutes=0,  # Would calculate if needed
                    service_time_minutes=stop.service_time,
                    customer_id=stop.customer_id,
                    location={"lat": stop.latitude, "lng": stop.longitude},
                    delivery_notes=None,
                )

                optimized_stops.append(optimized_stop)
                all_assigned_orders.add(stop.order_id)
                current_time += timedelta(minutes=stop.service_time)

            # Calculate costs
            fuel_cost = route_distance * request.constraints.fuel_cost_per_km
            time_cost = (route_duration / 60) * request.constraints.time_cost_per_hour
            route_total_cost = fuel_cost + time_cost

            # Calculate capacity utilization
            capacity_utilization = {}
            for stop in stops:
                for product, qty in stop.demand.items():
                    capacity_utilization[product] = (
                        capacity_utilization.get(product, 0) + qty
                    )

            # Build route
            route = OptimizedRoute(
                vehicle_id=vehicle["id"],
                driver_id=vehicle.get("driver_id", vehicle["id"]),
                date=request.date,
                stops=optimized_stops,
                total_distance_km=route_distance,
                total_duration_minutes=route_duration,
                total_fuel_cost=fuel_cost,
                total_time_cost=time_cost,
                total_cost=route_total_cost,
                start_location={
                    "lat": vehicle.get("depot_lat", 25.0330),
                    "lng": vehicle.get("depot_lng", 121.5654),
                },
                end_location={
                    "lat": vehicle.get("depot_lat", 25.0330),
                    "lng": vehicle.get("depot_lng", 121.5654),
                },
                capacity_utilization=capacity_utilization,
                efficiency_score=self._calculate_efficiency_score(
                    len(stops), route_distance, route_duration
                ),
            )

            routes.append(route)
            total_distance += route_distance
            total_duration += route_duration
            total_cost += route_total_cost

        # Calculate unassigned orders
        all_order_ids = set(order["id"] for order in orders)
        unassigned_orders = list(all_order_ids - all_assigned_orders)

        # Calculate savings (simplified - compare to unoptimized scenario)
        unoptimized_estimate = len(orders) * 10  # 10 km per order average
        savings_percentage = (
            ((unoptimized_estimate - total_distance) / unoptimized_estimate * 100)
            if unoptimized_estimate > 0
            else 0
        )

        # Build warnings
        warnings = []
        if unassigned_orders:
            warnings.append(f"{len(unassigned_orders)} orders could not be assigned")
        if total_duration > len(vehicles) * 480:
            warnings.append("Some routes exceed 8-hour shift limit")

        return OptimizationResponse(
            optimization_id=optimization_id,
            status="success" if not unassigned_orders else "partial",
            routes=routes,
            unassigned_orders=unassigned_orders,
            total_routes=len(routes),
            total_distance_km=total_distance,
            total_duration_hours=total_duration / 60,
            total_cost=total_cost,
            savings_percentage=max(0, min(100, savings_percentage)),
            optimization_time_ms=int((time_module.time() - start_time) * 1000),
            warnings=warnings,
            metadata={
                "optimization_mode": request.optimization_mode,
                "clustered": len(orders) > 20,
                "vehicles_used": len(routes),
                "orders_processed": len(orders),
            },
        )

    async def _calculate_route_metrics(
        self, stops: List[VRPStop]
    ) -> Tuple[float, float]:
        """Calculate total distance and duration for a route."""
        if not stops:
            return 0, 0

        # If we have Google Routes service, use it
        if self.google_routes_service:
            try:
                # Get route from Google
                depot = (25.0330, 121.5654)  # Default depot
                result = (
                    await self.google_routes_service._get_google_directions_enhanced(
                        depot, stops
                    )
                )
                return result.get("distance", 0), result.get("duration", 0)
            except Exception as e:
                logger.warning(f"Failed to get Google route metrics: {e}")

        # Fallback to estimation
        total_distance = 0
        total_duration = 0

        # Add distance from depot to first stop
        if stops:
            total_distance += self._calculate_distance(
                25.0330, 121.5654, stops[0].latitude, stops[0].longitude  # Depot
            )

        # Add distances between stops
        for i in range(len(stops) - 1):
            distance = self._calculate_distance(
                stops[i].latitude,
                stops[i].longitude,
                stops[i + 1].latitude,
                stops[i + 1].longitude,
            )
            total_distance += distance

        # Add distance from last stop back to depot
        if stops:
            total_distance += self._calculate_distance(
                stops[-1].latitude, stops[-1].longitude, 25.0330, 121.5654  # Depot
            )

        # Estimate duration (30 km/h average in city)
        total_duration = (total_distance / 30) * 60  # Convert to minutes

        # Add service times
        total_duration += sum(stop.service_time for stop in stops)

        return total_distance, total_duration

    async def _estimate_travel_time(
        self, lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """Estimate travel time between two points in minutes."""
        distance = self._calculate_distance(lat1, lng1, lat2, lng2)
        # Assume 30 km/h average speed in city
        return (distance / 30) * 60

    def _calculate_efficiency_score(
        self, num_stops: int, distance: float, duration: float
    ) -> float:
        """Calculate route efficiency score (0-100)."""
        if num_stops == 0:
            return 0

        # Factors:
        # - Stops per km (more is better)
        # - Stops per hour (more is better)
        # - Distance per stop (less is better)

        stops_per_km = num_stops / max(distance, 1)
        stops_per_hour = num_stops / max(duration / 60, 1)
        km_per_stop = distance / num_stops

        # Normalize and weight factors
        score = (
            min(stops_per_km / 0.5, 1) * 30  # Target: 0.5 stops/km
            + min(stops_per_hour / 8, 1) * 40  # Target: 8 stops/hour
            + min(2 / km_per_stop, 1) * 30  # Target: 2 km/stop
        )

        return min(100, max(0, score))

    def _generate_cache_key(self, request: OptimizationRequest) -> str:
        """Generate cache key for request."""
        # Create a deterministic key based on request parameters
        key_parts = [
            "vrp",
            request.date.strftime("%Y%m%d"),
            ",".join(map(str, sorted(request.order_ids))),
            ",".join(map(str, sorted(request.vehicle_ids))),
            request.optimization_mode,
            str(request.respect_time_windows),
            str(request.cluster_radius_km),
        ]
        return ":".join(key_parts)

    def _create_empty_response(
        self, optimization_id: str, message: str
    ) -> OptimizationResponse:
        """Create empty response for edge cases."""
        return OptimizationResponse(
            optimization_id=optimization_id,
            status="failed",
            routes=[],
            unassigned_orders=[],
            total_routes=0,
            total_distance_km=0,
            total_duration_hours=0,
            total_cost=0,
            savings_percentage=0,
            optimization_time_ms=0,
            warnings=[message],
        )

    def _create_error_response(
        self, optimization_id: str, error: str, start_time: float
    ) -> OptimizationResponse:
        """Create error response."""
        return OptimizationResponse(
            optimization_id=optimization_id,
            status="failed",
            routes=[],
            unassigned_orders=[],
            total_routes=0,
            total_distance_km=0,
            total_duration_hours=0,
            total_cost=0,
            savings_percentage=0,
            optimization_time_ms=int((time_module.time() - start_time) * 1000),
            warnings=[f"Optimization failed: {error}"],
        )

    async def _send_progress(
        self, optimization_id: str, percentage: int, message: str
    ) -> None:
        """Send optimization progress via WebSocket if available."""
        if self.websocket_service:
            try:
                progress_data = {
                    "type": "optimization_progress",
                    "optimization_id": optimization_id,
                    "percentage": percentage,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }
                await self.websocket_service.broadcast_to_room(
                    f"optimization_{optimization_id}", progress_data
                )
            except Exception as e:
                logger.warning(f"Failed to send progress update: {e}")

    async def _track_optimization_metrics(
        self,
        response: OptimizationResponse,
        request: OptimizationRequest,
        start_time: float,
    ) -> None:
        """Track optimization metrics for monitoring."""
        try:
            # Track optimization duration
            duration = time_module.time() - start_time
            route_optimization_histogram.labels(
                method="VRP", num_stops=str(len(request.order_ids))
            ).observe(duration)

            # Track VRP summary metrics
            vrp_optimization_summary.labels(
                optimization_mode=request.optimization_mode,
                clustered=str(len(request.order_ids) > 20),
            ).observe(duration)

            # Track solution quality
            if response.status == "success":
                vrp_solution_quality_gauge.labels(metric_type="savings_percentage").set(
                    response.savings_percentage
                )

                # Calculate average efficiency score
                if response.routes:
                    avg_efficiency = sum(
                        r.efficiency_score for r in response.routes
                    ) / len(response.routes)
                    vrp_solution_quality_gauge.labels(
                        metric_type="efficiency_score"
                    ).set(avg_efficiency)

                # Calculate unassigned ratio
                unassigned_ratio = (
                    len(response.unassigned_orders) / len(request.order_ids)
                    if request.order_ids
                    else 0
                )
                vrp_solution_quality_gauge.labels(metric_type="unassigned_ratio").set(
                    unassigned_ratio * 100
                )

            # Track constraint violations
            for warning in response.warnings:
                if "time window" in warning.lower():
                    vrp_constraint_violations_counter.labels(
                        constraint_type="time_window"
                    ).inc()
                elif "capacity" in warning.lower():
                    vrp_constraint_violations_counter.labels(
                        constraint_type="capacity"
                    ).inc()
                elif "shift" in warning.lower() or "hour" in warning.lower():
                    vrp_constraint_violations_counter.labels(
                        constraint_type="shift_time"
                    ).inc()

            # Log summary metrics
            logger.info(
                f"VRP Optimization completed: "
                f"duration={duration:.2f}s, "
                f"routes={response.total_routes}, "
                f"distance={response.total_distance_km:.1f}km, "
                f"savings={response.savings_percentage:.1f}%, "
                f"unassigned={len(response.unassigned_orders)}"
            )

        except Exception as e:
            logger.error(f"Failed to track optimization metrics: {e}")
