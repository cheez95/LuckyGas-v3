# Master AI Prompt for VRP Algorithm Implementation
## Story 3.2: Route Optimization Algorithm for Lucky Gas

### 🎯 High-Level Goal
Create a production-ready Vehicle Routing Problem (VRP) solver for Lucky Gas that optimizes delivery routes for 100+ stops in under 5 seconds, considering time windows, vehicle capacity, driver shifts, and Taiwan-specific traffic patterns. The solution must integrate with the existing GoogleRoutesService and achieve 25-30% fuel cost reduction.

### 📋 Detailed Step-by-Step Instructions

1. **Create VRP Optimizer Service** (`/backend/app/services/optimization/vrp_optimizer.py`)
   - Import OR-Tools for core VRP solving capabilities
   - Create `VRPOptimizer` class with async methods
   - Implement connection pooling for concurrent route calculations
   - Add comprehensive logging for performance monitoring

2. **Define Data Models** (`/backend/app/models/optimization.py`)
   - Create `OptimizationRequest` Pydantic model with:
     - List of delivery locations (lat/lng, time windows, demand)
     - Vehicle fleet specifications (capacity, shift times)
     - Optimization objectives (minimize time vs fuel)
   - Create `OptimizationResponse` model with:
     - Optimized routes per vehicle
     - Total distance/time/fuel estimates
     - Individual stop ETAs and sequence

3. **Implement Clustering Algorithm**
   - Use DBSCAN or K-means for initial geographic grouping
   - Consider delivery density and time windows
   - Create clusters of 15-20 stops for sub-problem solving
   - Account for Taiwan's geographic constraints (mountains, rivers)

4. **Build Core VRP Solver**
   ```python
   class VRPOptimizer:
       def __init__(self, google_routes_service: GoogleRoutesService):
           self.routes_service = google_routes_service
           self.manager = None
           self.routing = None
           
       async def optimize_routes(
           self,
           locations: List[DeliveryLocation],
           vehicles: List[Vehicle],
           constraints: OptimizationConstraints
       ) -> OptimizationResponse:
           # Step 1: Cluster locations
           clusters = self._cluster_locations(locations)
           
           # Step 2: Create distance matrix using GoogleRoutesService
           distance_matrix = await self._build_distance_matrix(locations)
           
           # Step 3: Setup OR-Tools routing model
           self._setup_routing_model(distance_matrix, vehicles, constraints)
           
           # Step 4: Solve with time limit
           solution = self._solve_vrp(time_limit_seconds=4)
           
           # Step 5: Post-process and validate
           return self._process_solution(solution, locations)
   ```

5. **Integrate Google Routes API**
   - Use batch distance matrix API for efficiency
   - Cache distance calculations aggressively
   - Implement fallback for API failures
   - Consider real-time traffic for time calculations

6. **Add Time Window Constraints**
   - Implement soft and hard time windows
   - Penalize late deliveries appropriately
   - Consider Taiwan business hours (9 AM - 6 PM typical)
   - Handle lunch break constraints (12 PM - 1 PM)

7. **Handle Vehicle Capacity**
   - Track cylinder count per vehicle (typical: 50-100)
   - Implement multi-trip support for high demand
   - Consider weight distribution for safety
   - Account for different cylinder sizes (10kg, 16kg, 20kg)

8. **Optimize for Taiwan-Specific Patterns**
   - Peak traffic hours: 7-9 AM, 5-7 PM
   - Avoid school zones during drop-off/pickup
   - Consider traditional market days (higher congestion)
   - Account for typhoon season adjustments

9. **Implement Performance Optimizations**
   - Use asyncio for parallel processing
   - Implement early termination for "good enough" solutions
   - Cache frequently used routes
   - Pre-compute common delivery patterns

10. **Add Monitoring and Metrics**
    - Track optimization time per request
    - Monitor solution quality (fuel savings %)
    - Log constraint violations
    - Export metrics to Cloud Monitoring

### 🔧 Code Examples, Data Structures & Constraints

**Required Dependencies:**
```python
# requirements.txt additions
ortools==9.8.3296
scikit-learn==1.3.2  # for clustering
numpy==1.24.3
asyncio-throttle==1.0.2
```

**Integration Points:**
```python
# Use existing GoogleRoutesService
from app.services.google_cloud.routes_service import GoogleRoutesService
from app.models.order import Order
from app.models.route import Route
from app.models.customer import Customer
```

**API Contract:**
```python
# POST /api/v1/routes/optimize
{
    "date": "2024-01-23",
    "orders": [
        {
            "id": 123,
            "customer_id": 456,
            "location": {"lat": 25.0330, "lng": 121.5654},
            "time_window": {"start": "09:00", "end": "17:00"},
            "cylinders_ordered": {"16kg": 2, "20kg": 1},
            "priority": "normal"
        }
    ],
    "vehicles": [
        {
            "id": "V001",
            "capacity": {"16kg": 30, "20kg": 20},
            "shift_start": "08:00",
            "shift_end": "18:00",
            "start_location": {"lat": 25.0478, "lng": 121.5319}
        }
    ],
    "optimization_profile": "balanced"  # balanced|time|fuel
}
```

**Constraints:**
- Maximum 100 stops per optimization request
- Solution must be found within 5 seconds
- Respect all hard time windows (no violations)
- Vehicle capacity cannot be exceeded
- Driver shift times are hard constraints
- Minimum 10-minute service time per stop

**DO NOT:**
- Use simple TSP algorithms (need full VRP with constraints)
- Ignore real-world traffic data
- Create routes longer than 10 hours
- Split orders for same customer across vehicles
- Use deprecated OR-Tools APIs

### 🎯 Strict Scope Definition

**Files to CREATE:**
- `/backend/app/services/optimization/vrp_optimizer.py` - Main VRP solver
- `/backend/app/services/optimization/clustering.py` - Geographic clustering
- `/backend/app/models/optimization.py` - Request/response models
- `/backend/app/api/v1/routes_optimization.py` - API endpoint
- `/backend/tests/test_vrp_optimizer.py` - Comprehensive tests

**Files to MODIFY:**
- `/backend/app/api/v1/__init__.py` - Register new endpoint
- `/backend/requirements.txt` - Add OR-Tools and dependencies

**Files to LEAVE UNTOUCHED:**
- `/backend/app/services/google_cloud/routes_service.py` - Only import and use
- Existing database models - Work with current structure
- Authentication/authorization - Use existing patterns

### 🚀 Performance Requirements

The implementation MUST:
- Handle 100 stops in <5 seconds (target: 3 seconds)
- Achieve 25-30% reduction in total distance vs naive routing
- Support concurrent optimization requests
- Provide progress updates via WebSocket
- Gracefully degrade with partial solutions if time limit reached

### 🧪 Testing Requirements

Include comprehensive tests for:
- Various cluster sizes (10, 50, 100 stops)
- Time window constraint satisfaction
- Capacity constraint validation
- Performance benchmarks
- Edge cases (all stops urgent, impossible constraints)
- Taiwan-specific scenarios (typhoon mode, holiday routing)

---

## 🎨 Agent Recommendations

This complex algorithmic implementation would best be handled by:

1. **Backend Agent** (Primary) - For core VRP implementation and API integration
2. **Architect Agent** (Supporting) - For system design and performance optimization
3. **Performance Agent** (Review) - For optimization and bottleneck analysis

The implementation requires deep algorithmic knowledge, performance optimization skills, and careful integration with existing systems - making it ideal for specialized backend development with architectural oversight.

**Note**: All generated code will require careful human review, testing, and refinement before production deployment. The VRP solver is a critical component that directly impacts business operations and costs.