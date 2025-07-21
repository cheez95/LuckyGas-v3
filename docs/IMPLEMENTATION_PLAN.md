# Lucky Gas Framework Replacement & OR-Tools Implementation Plan

## Executive Summary

This comprehensive plan combines framework modernization with Google OR-Tools integration to deliver a 40-60% performance improvement and 30% code reduction while implementing true Vehicle Routing Problem (VRP) optimization for Lucky Gas's delivery operations.

**Timeline**: 3 weeks  
**Impact**: High - Core system improvements affecting all operations  
**Risk**: Low - All changes are incremental and backward compatible  

## Week 1: High-Impact Quick Wins & OR-Tools Foundation

### Day 1-2: FastAPI Background Tasks & Bulk Operations

#### Morning: Background Tasks for Predictions
```python
# File: backend/app/api/v1/predictions.py
from fastapi import BackgroundTasks

@router.post("/batch", response_model=dict)
async def generate_batch_predictions(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Generate predictions asynchronously"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(403, "權限不足")
    
    # Create batch record
    batch = PredictionBatch(
        created_by=current_user.id,
        status="processing",
        created_at=datetime.utcnow()
    )
    session.add(batch)
    await session.commit()
    
    # Add to background
    background_tasks.add_task(
        process_batch_predictions,
        batch_id=batch.id,
        session_factory=async_session_maker
    )
    
    return {
        "batch_id": batch.id,
        "status": "processing",
        "message": "預測生成已開始，完成後將通知您"
    }

async def process_batch_predictions(batch_id: int, session_factory):
    """Background task for prediction processing"""
    async with session_factory() as session:
        try:
            # Get all active customers
            result = await session.execute(
                select(Customer).where(Customer.is_terminated == False)
            )
            customers = result.scalars().all()
            
            # Generate predictions using Vertex AI
            predictions = await vertex_ai_service.predict_demand_batch(customers)
            
            # Bulk insert predictions
            prediction_data = [
                {
                    "batch_id": batch_id,
                    "customer_id": pred["customer_id"],
                    "predicted_date": pred["date"],
                    "predicted_quantity": pred["quantity"],
                    "confidence_score": pred["confidence"]
                }
                for pred in predictions
            ]
            
            # Use bulk operations
            await session.execute(
                insert(DeliveryPrediction).values(prediction_data)
            )
            
            # Update batch status
            batch = await session.get(PredictionBatch, batch_id)
            batch.status = "completed"
            batch.completed_at = datetime.utcnow()
            
            await session.commit()
            
            # Send WebSocket notification
            await notify_prediction_ready(batch_id, len(predictions))
            
        except Exception as e:
            # Update batch with error
            batch = await session.get(PredictionBatch, batch_id)
            batch.status = "failed"
            batch.error_message = str(e)
            await session.commit()
```

#### Afternoon: SQLAlchemy Bulk Operations
```python
# File: backend/app/services/route_optimization.py
from sqlalchemy import insert, update

async def create_route_stops_bulk(
    route_id: int,
    stops_data: List[Dict],
    session: AsyncSession
):
    """Bulk create route stops"""
    # Prepare data with proper formatting
    stop_records = [
        {
            "route_id": route_id,
            "order_id": stop["order_id"],
            "stop_sequence": idx + 1,
            "address": stop["address"],
            "latitude": stop["lat"],
            "longitude": stop["lng"],
            "estimated_arrival": stop["estimated_arrival"],
            "service_duration_minutes": stop.get("service_time", 10)
        }
        for idx, stop in enumerate(stops_data)
    ]
    
    # Bulk insert
    await session.execute(
        insert(RouteStop).values(stop_records)
    )
    
    # Bulk update order statuses
    order_ids = [stop["order_id"] for stop in stops_data]
    await session.execute(
        update(Order)
        .where(Order.id.in_(order_ids))
        .values(
            status=OrderStatus.ASSIGNED,
            assigned_route_id=route_id
        )
    )
```

### Day 3-4: OR-Tools VRP Implementation

#### Morning: Install and Setup OR-Tools
```bash
# File: backend/requirements.txt
ortools==9.8.3296
numpy==1.24.3
```

#### Create VRP Optimizer Service
```python
# File: backend/app/services/optimization/ortools_optimizer.py
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

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
        
        # Create time matrix (distance in km * 2 for average speed 30km/h)
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
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            return self._extract_solution(
                manager, routing, solution, stops, vehicles
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
        vehicles: List[VRPVehicle]
    ) -> Dict[int, List[VRPStop]]:
        """Extract solution routes"""
        
        routes = {}
        time_dimension = routing.GetDimensionOrDie('Time')
        
        for vehicle_id in range(len(vehicles)):
            route_stops = []
            index = routing.Start(vehicle_id)
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                
                if node_index != 0:  # Skip depot
                    stop = stops[node_index - 1]  # Adjust for depot at index 0
                    
                    # Add arrival time
                    time_var = time_dimension.CumulVar(index)
                    stop.estimated_arrival = solution.Min(time_var)
                    
                    route_stops.append(stop)
                
                index = solution.Value(routing.NextVar(index))
            
            routes[vehicle_id] = route_stops
            
            # Log route info
            if route_stops:
                route_time = solution.Min(time_dimension.CumulVar(routing.End(vehicle_id)))
                logger.info(
                    f"Vehicle {vehicle_id}: {len(route_stops)} stops, "
                    f"duration: {route_time} minutes"
                )
        
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
                    matrix[i][j] = self._haversine_distance(
                        locations[i][0], locations[i][1],
                        locations[j][0], locations[j][1]
                    )
        
        return matrix
    
    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in kilometers"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _fallback_assignment(
        self,
        stops: List[VRPStop],
        vehicles: List[VRPVehicle]
    ) -> Dict[int, List[VRPStop]]:
        """Simple fallback assignment when OR-Tools fails"""
        # Distribute stops evenly
        stops_per_vehicle = len(stops) // len(vehicles)
        routes = {}
        
        for i in range(len(vehicles)):
            start = i * stops_per_vehicle
            end = start + stops_per_vehicle if i < len(vehicles) - 1 else len(stops)
            routes[i] = stops[start:end]
        
        return routes

# Singleton instance
ortools_optimizer = ORToolsOptimizer(
    depot_location=(settings.DEPOT_LAT, settings.DEPOT_LNG)
)
```

### Day 5: Cache Replacement & Middleware

#### Morning: Replace Custom Cache with FastAPI-Cache2
```bash
# Install
cd backend
uv pip install "fastapi-cache2[redis]"
```

```python
# File: backend/app/main.py
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi.middleware.gzip import GZipMiddleware
import aioredis
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_db_and_tables()
    
    # Initialize cache
    redis = aioredis.from_url(settings.REDIS_URL)
    FastAPICache.init(RedisBackend(redis), prefix="luckygas")
    
    yield
    
    # Shutdown
    await redis.close()

# Add middleware stack
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(f"{process_time:.3f}")
    return response

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "資料驗證失敗",
            "errors": exc.errors(),
            "body": exc.body
        }
    )
```

#### Update Customer Endpoints with New Cache
```python
# File: backend/app/api/v1/customers.py
from fastapi_cache.decorator import cache

@router.get("/", response_model=CustomerList)
@cache(expire=900)  # 15 minutes
async def get_customers(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
    area: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[str] = None
):
    # Existing code...
    pass

@router.post("/", response_model=Customer)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Create customer
    # ...
    
    # Invalidate cache
    await FastAPICache.clear(namespace="luckygas")
    
    return customer
```

## Week 2: Advanced Features & Integration

### Day 6-7: Integrate OR-Tools with Routes Service

```python
# File: backend/app/services/google_cloud/routes_service.py
from app.services.optimization.ortools_optimizer import (
    ortools_optimizer, VRPStop, VRPVehicle
)

class GoogleRoutesService:
    """
    Hybrid service using OR-Tools for optimization and Google Routes for navigation
    """
    
    async def optimize_multiple_routes(
        self,
        orders: List[Order],
        drivers: List[Dict],
        date: datetime
    ) -> List[Dict]:
        """
        Optimize routes using OR-Tools VRP solver
        """
        
        # Convert orders to VRPStop format
        stops = []
        for order in orders:
            if not order.customer:
                continue
                
            stop = VRPStop(
                order_id=order.id,
                customer_id=order.customer_id,
                customer_name=order.customer.short_name,
                address=order.delivery_address or order.customer.address,
                latitude=order.customer.latitude or self.depot_location[0],
                longitude=order.customer.longitude or self.depot_location[1],
                demand=self._extract_demand(order),
                time_window=self._get_time_window(order),
                service_time=self._estimate_service_time(order)
            )
            stops.append(stop)
        
        # Convert drivers to VRPVehicle format
        vehicles = []
        for driver in drivers:
            vehicle = VRPVehicle(
                driver_id=driver["id"],
                driver_name=driver["name"],
                capacity={
                    "50kg": 10,
                    "20kg": 20,
                    "16kg": 25,
                    "10kg": 40,
                    "4kg": 50
                },
                start_location=self.depot_location,
                max_travel_time=480  # 8 hours
            )
            vehicles.append(vehicle)
        
        # Optimize using OR-Tools
        optimized_routes = ortools_optimizer.optimize(stops, vehicles)
        
        # Get turn-by-turn directions from Google Routes API
        route_results = []
        for vehicle_idx, route_stops in optimized_routes.items():
            if not route_stops:
                continue
                
            # Get Google directions for visualization
            google_route = await self._get_google_directions(
                self.depot_location,
                route_stops
            )
            
            # Build route data
            route_data = {
                "route_number": f"R{date.strftime('%Y%m%d')}-{vehicle_idx+1:02d}",
                "driver_id": vehicles[vehicle_idx].driver_id,
                "vehicle_id": vehicle_idx,
                "date": date.isoformat(),
                "status": "optimized",
                "area": self._determine_area(route_stops),
                "stops": [
                    {
                        "order_id": stop.order_id,
                        "customer_id": stop.customer_id,
                        "customer_name": stop.customer_name,
                        "address": stop.address,
                        "lat": stop.latitude,
                        "lng": stop.longitude,
                        "stop_sequence": idx + 1,
                        "estimated_arrival": self._minutes_to_datetime(
                            date, stop.estimated_arrival
                        ),
                        "service_time": stop.service_time,
                        "products": stop.demand
                    }
                    for idx, stop in enumerate(route_stops)
                ],
                "total_stops": len(route_stops),
                "total_distance_km": google_route.get("distance", 0),
                "estimated_duration_minutes": google_route.get("duration", 0),
                "polyline": google_route.get("polyline", ""),
                "optimized": True,
                "optimization_method": "OR-Tools VRP"
            }
            route_results.append(route_data)
        
        return route_results
    
    def _extract_demand(self, order: Order) -> Dict[str, int]:
        """Extract product demands from order"""
        demand = {}
        for size in [50, 20, 16, 10, 4]:
            qty_field = f"quantity_{size}kg"
            if hasattr(order, qty_field):
                qty = getattr(order, qty_field, 0)
                if qty > 0:
                    demand[f"{size}kg"] = qty
        return demand
    
    def _get_time_window(self, order: Order) -> Tuple[int, int]:
        """Convert delivery time to minutes from day start"""
        if order.customer.delivery_time_start:
            start_hour = int(order.customer.delivery_time_start.split(":")[0])
            start_minutes = start_hour * 60
        else:
            start_minutes = 8 * 60  # Default 8 AM
            
        if order.customer.delivery_time_end:
            end_hour = int(order.customer.delivery_time_end.split(":")[0])
            end_minutes = end_hour * 60
        else:
            end_minutes = 18 * 60  # Default 6 PM
            
        return (start_minutes, end_minutes)
    
    async def _get_google_directions(
        self,
        depot: Tuple[float, float],
        stops: List[VRPStop]
    ) -> Dict:
        """Get turn-by-turn directions from Google Routes API"""
        # Implementation for getting actual navigation data
        # This provides the visual route for drivers
        pass
```

### Day 8-9: Pydantic Enhancements & Security

#### Secure Settings Management
```python
# File: backend/app/core/config.py
from pydantic import SecretStr, Field, computed_field
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Lucky Gas Delivery Management System"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Security - Fixed secret key
    SECRET_KEY: SecretStr = Field(
        default_factory=lambda: SecretStr(
            os.getenv("SECRET_KEY", "your-secret-key-here")
        )
    )
    
    # Database with SecretStr
    POSTGRES_PASSWORD: SecretStr = Field(..., env="POSTGRES_PASSWORD")
    
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD.get_secret_value()}@"
            f"{self.POSTGRES_SERVER}:5433/{self.POSTGRES_DB}"
        )
    
    # Google Cloud with SecretStr
    GOOGLE_MAPS_API_KEY: SecretStr = Field(default="", env="GOOGLE_MAPS_API_KEY")
    
    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
```

#### Enhanced Pydantic Models
```python
# File: backend/app/schemas/customer.py
from pydantic import BaseModel, Field, computed_field, field_validator
from typing import Dict

class CustomerBase(BaseModel):
    customer_code: str = Field(..., min_length=1, max_length=20)
    short_name: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=500)
    
    # Individual cylinder fields
    cylinders_50kg: int = Field(default=0, ge=0, le=100)
    cylinders_20kg: int = Field(default=0, ge=0, le=200)
    cylinders_16kg: int = Field(default=0, ge=0, le=200)
    cylinders_10kg: int = Field(default=0, ge=0, le=300)
    cylinders_4kg: int = Field(default=0, ge=0, le=500)
    
    @computed_field
    @property
    def total_cylinders(self) -> int:
        """Total number of cylinders"""
        return (
            self.cylinders_50kg + self.cylinders_20kg +
            self.cylinders_16kg + self.cylinders_10kg +
            self.cylinders_4kg
        )
    
    @computed_field
    @property
    def total_capacity_kg(self) -> float:
        """Total gas capacity in kg"""
        return (
            self.cylinders_50kg * 50 +
            self.cylinders_20kg * 20 +
            self.cylinders_16kg * 16 +
            self.cylinders_10kg * 10 +
            self.cylinders_4kg * 4
        )
    
    @computed_field
    @property
    def estimated_monthly_revenue(self) -> float:
        """Estimated monthly revenue in TWD"""
        # Rough calculation based on cylinder size
        revenue_per_kg = 15  # TWD per kg
        avg_refills_per_month = 2.5
        return self.total_capacity_kg * revenue_per_kg * avg_refills_per_month
    
    @field_validator('delivery_time_start', 'delivery_time_end')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        if v and not re.match(r'^\d{2}:\d{2}$', v):
            raise ValueError('時間格式必須為 HH:MM')
        return v
```

### Day 10: WebSocket Replacement with python-socketio

```bash
# Install
cd backend
uv pip install "python-socketio[asyncio]"
```

```python
# File: backend/app/api/v1/websocket_v2.py
import socketio
from app.core.security import decode_access_token

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.get_all_cors_origins(),
    logger=True,
    engineio_logger=True
)

# Socket.IO app
socket_app = socketio.ASGIApp(
    sio,
    socketio_path='/ws/socket.io'
)

@sio.event
async def connect(sid, environ, auth):
    """Handle connection with JWT authentication"""
    try:
        token = auth.get('token') if auth else None
        if not token:
            await sio.disconnect(sid)
            return False
        
        # Verify JWT
        payload = decode_access_token(token)
        username = payload.get("sub")
        role = payload.get("role")
        
        # Store session data
        await sio.save_session(sid, {
            'username': username,
            'role': role,
            'user_id': payload.get("user_id")
        })
        
        # Join role-based rooms
        if role in ["super_admin", "manager"]:
            await sio.enter_room(sid, "admin")
            await sio.enter_room(sid, "orders")
            await sio.enter_room(sid, "routes")
            await sio.enter_room(sid, "predictions")
        elif role == "office_staff":
            await sio.enter_room(sid, "orders")
            await sio.enter_room(sid, "routes")
        elif role == "driver":
            await sio.enter_room(sid, "routes")
            await sio.enter_room(sid, f"driver_{payload.get('user_id')}")
        
        # Send connection success
        await sio.emit('connected', {
            'message': '連接成功',
            'role': role
        }, to=sid)
        
        return True
        
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await sio.disconnect(sid)
        return False

@sio.event
async def disconnect(sid):
    """Handle disconnection"""
    session = await sio.get_session(sid)
    logger.info(f"User {session.get('username')} disconnected")

# Helper functions for broadcasting
async def notify_order_update(order_data: dict):
    """Notify about order updates"""
    await sio.emit('order_update', order_data, room='orders')

async def notify_route_update(route_data: dict):
    """Notify about route updates"""
    await sio.emit('route_update', route_data, room='routes')

async def notify_prediction_ready(batch_id: int, summary: dict):
    """Notify when predictions are ready"""
    await sio.emit('prediction_ready', {
        'batch_id': batch_id,
        'summary': summary
    }, room='predictions')

# Mount Socket.IO app
app.mount("/ws", socket_app)
```

## Week 3: Performance Optimization & Monitoring

### Day 11-12: Performance Optimization

#### SQLAlchemy Query Optimization
```python
# File: backend/app/models/customer.py
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Index

class Customer(Base):
    __tablename__ = "customers"
    
    # Existing fields...
    
    @hybrid_property
    def is_active(self):
        """Active if not terminated"""
        return not self.is_terminated
    
    @is_active.expression
    def is_active(cls):
        return ~cls.is_terminated
    
    @hybrid_property
    def total_gas_inventory(self):
        """Total gas in kg across all cylinders"""
        return (
            self.cylinders_50kg * 50 +
            self.cylinders_20kg * 20 +
            self.cylinders_16kg * 16 +
            self.cylinders_10kg * 10 +
            self.cylinders_4kg * 4
        )
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_customer_area_active', 'area', 'is_terminated'),
        Index('idx_customer_code', 'customer_code'),
        Index('idx_customer_search', 'short_name', 'invoice_title'),
    )
```

#### Dependency Injection Patterns
```python
# File: backend/app/api/deps.py
from functools import lru_cache
from typing import List

class PermissionChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="權限不足"
            )
        return current_user

# Create reusable permission dependencies
require_admin = PermissionChecker(["super_admin"])
require_manager = PermissionChecker(["super_admin", "manager"])
require_office = PermissionChecker(["super_admin", "manager", "office_staff"])
require_driver = PermissionChecker(["driver"])

# Use in endpoints
@router.post("/", response_model=Customer)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_office)
):
    # No need to check permissions here
    pass
```

### Day 13-14: Monitoring & Testing

#### Add Prometheus Monitoring
```bash
cd backend
uv pip install prometheus-fastapi-instrumentator
```

```python
# File: backend/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

# After creating app
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*", "/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="inprogress",
    inprogress_labels=True,
)

instrumentator.instrument(app).expose(app)

# Custom metrics
from prometheus_client import Counter, Histogram, Gauge

# Track predictions
prediction_counter = Counter(
    'lucky_gas_predictions_total',
    'Total number of predictions generated',
    ['customer_type', 'status']
)

# Track route optimization
route_optimization_histogram = Histogram(
    'lucky_gas_route_optimization_duration_seconds',
    'Time spent optimizing routes',
    ['method', 'num_stops']
)

# Active deliveries
active_deliveries_gauge = Gauge(
    'lucky_gas_active_deliveries',
    'Number of active deliveries',
    ['area', 'driver']
)
```

#### Testing Utilities
```python
# File: backend/tests/conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import get_async_session, Base
from app.core.security import create_access_token

@pytest.fixture
async def async_client():
    """Create test client with test database"""
    # Create test database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestingSessionLocal = async_sessionmaker(
        engine, expire_on_commit=False
    )
    
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_async_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    """Create auth headers for testing"""
    def _auth_headers(role: str = "super_admin", user_id: int = 1):
        token = create_access_token(
            data={"sub": f"test_{role}", "role": role, "user_id": user_id}
        )
        return {"Authorization": f"Bearer {token}"}
    return _auth_headers

# Example test
async def test_create_customer(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/customers",
        json={
            "customer_code": "C001",
            "short_name": "測試客戶",
            "address": "台北市信義區",
            "cylinders_50kg": 2
        },
        headers=auth_headers("office_staff")
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_cylinders"] == 2  # Computed field
    assert data["total_capacity_kg"] == 100
```

## Implementation Schedule

### Week 1 Summary
- **Days 1-2**: FastAPI Background Tasks, SQLAlchemy Bulk Operations
- **Days 3-4**: OR-Tools VRP Implementation
- **Day 5**: Cache Replacement, Middleware Stack

### Week 2 Summary
- **Days 6-7**: OR-Tools Integration with Routes Service
- **Days 8-9**: Pydantic Enhancements, Security Updates
- **Day 10**: WebSocket Replacement

### Week 3 Summary
- **Days 11-12**: Performance Optimization, Query Improvements
- **Days 13-14**: Monitoring Setup, Testing Utilities

## Validation Checkpoints

### After Week 1
- [ ] Background predictions working (check WebSocket notifications)
- [ ] Bulk operations reducing database time by >50%
- [ ] OR-Tools generating valid routes
- [ ] Cache hit rate >80%

### After Week 2
- [ ] OR-Tools routes 20-30% more efficient than TSP
- [ ] All sensitive data using SecretStr
- [ ] WebSocket connections stable
- [ ] Computed fields working in API responses

### After Week 3
- [ ] API response time <200ms (p95)
- [ ] Prometheus metrics accessible at /metrics
- [ ] All E2E tests passing
- [ ] Code coverage >80%

## Risk Mitigation

1. **OR-Tools Integration Issues**
   - Fallback: Keep existing Google Routes API as backup
   - Test with real Lucky Gas data early

2. **Cache Migration**
   - Run both cache systems in parallel initially
   - Migrate endpoint by endpoint

3. **WebSocket Compatibility**
   - Keep old WebSocket endpoint during transition
   - Update frontend gradually

## Success Metrics

- **Performance**: 40-60% faster bulk operations
- **Code Reduction**: ~2,000 lines removed
- **Route Efficiency**: 20-30% better optimization
- **API Cost**: 80% reduction in Google API calls
- **Test Coverage**: From 45.5% to >80%
- **Response Time**: <200ms p95

## Next Steps After Implementation

1. **Monitor Performance**
   - Track Prometheus metrics
   - Analyze route optimization quality
   - Monitor API costs

2. **User Training**
   - Document new background task behavior
   - Explain improved route optimization
   - Show real-time features

3. **Phase 4 Preparation**
   - Deploy to staging
   - Load testing
   - Production deployment plan