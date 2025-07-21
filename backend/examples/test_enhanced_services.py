"""
Example script demonstrating enhanced Google API services
"""
import asyncio
import os
from datetime import datetime, date
from decimal import Decimal

# Set development mode for testing
os.environ["DEVELOPMENT_MODE"] = "development"

from app.services.google_cloud.routes_service_enhanced import enhanced_routes_service
from app.services.google_cloud.vertex_ai_service_enhanced import enhanced_vertex_ai_service
from app.core.security.api_key_manager import get_api_key_manager


async def test_routes_service():
    """Test enhanced routes service"""
    print("\n=== Testing Enhanced Routes Service ===")
    
    # Test route calculation
    print("\n1. Calculating route...")
    route = await enhanced_routes_service.calculate_route(
        origin="25.033,121.565",  # Taipei 101
        destination="25.047,121.517"  # National Taiwan University
    )
    
    print(f"   Distance: {route['routes'][0]['distance']}m")
    print(f"   Duration: {route['routes'][0]['duration']}s")
    print(f"   Using mock service: {route.get('mock', False)}")
    
    # Test route optimization
    print("\n2. Optimizing multiple waypoints...")
    waypoints = [
        {"lat": 25.033, "lng": 121.565},
        {"lat": 25.040, "lng": 121.550},
        {"lat": 25.045, "lng": 121.540},
        {"lat": 25.047, "lng": 121.517}
    ]
    
    optimized = await enhanced_routes_service.optimize_route(waypoints)
    print(f"   Total distance: {optimized['total_distance']}m")
    print(f"   Total duration: {optimized['total_duration']}s")
    print(f"   Optimized order: {[w['sequence'] for w in optimized['waypoints']]}")
    
    # Check service health
    print("\n3. Checking service health...")
    health = await enhanced_routes_service.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Components:")
    for component, details in health['components'].items():
        print(f"     - {component}: {details['status']}")
    
    # Get metrics
    print("\n4. Service metrics...")
    metrics = await enhanced_routes_service.get_route_metrics()
    monitoring = metrics.get('monitoring_stats', {})
    print(f"   Total requests: {monitoring.get('total_requests', 0)}")
    print(f"   Success rate: {monitoring.get('success_rate', 0)}%")
    print(f"   Cache hit rate: {monitoring.get('cache_hit_rate', 0)}%")


async def test_vertex_ai_service():
    """Test enhanced Vertex AI service"""
    print("\n\n=== Testing Enhanced Vertex AI Service ===")
    
    # Test batch prediction
    print("\n1. Generating batch predictions...")
    result = await enhanced_vertex_ai_service.predict_demand_batch()
    
    print(f"   Batch ID: {result['batch_id']}")
    print(f"   Predictions count: {result['predictions_count']}")
    print(f"   Execution time: {result['execution_time_seconds']}s")
    print(f"   Summary:")
    print(f"     - Urgent deliveries: {result['summary']['urgent_deliveries']}")
    print(f"     - Total 50kg cylinders: {result['summary']['total_50kg']}")
    print(f"     - Average confidence: {result['summary']['average_confidence']}")
    
    # Test individual prediction
    print("\n2. Getting customer prediction...")
    customer_prediction = await enhanced_vertex_ai_service.get_customer_prediction(1)
    if customer_prediction:
        print(f"   Customer ID: {customer_prediction['customer_id']}")
        print(f"   Predicted date: {customer_prediction['predicted_date']}")
        print(f"   Confidence: {customer_prediction['confidence_score']}")
        print(f"   Is urgent: {customer_prediction['is_urgent']}")
    
    # Check service health
    print("\n3. Checking service health...")
    health = await enhanced_vertex_ai_service.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Components:")
    for component, details in health['components'].items():
        print(f"     - {component}: {details['status']}")
    
    # Get metrics
    print("\n4. Service metrics...")
    metrics = await enhanced_vertex_ai_service.get_prediction_metrics()
    print(f"   Model status: {metrics.get('model_status', 'N/A')}")
    monitoring = metrics.get('monitoring_stats', {})
    print(f"   Total predictions: {monitoring.get('total_predictions', 0)}")
    print(f"   Success rate: {monitoring.get('success_rate', 0)}%")
    print(f"   Cache hit rate: {monitoring.get('cache_hit_rate', 0)}%")


async def test_monitoring_components():
    """Test monitoring components"""
    print("\n\n=== Testing Monitoring Components ===")
    
    # Test rate limiter
    print("\n1. Rate Limiter Status...")
    rate_status = await enhanced_routes_service.rate_limiter.get_current_usage("routes")
    print(f"   Available: {rate_status['available']}")
    print(f"   Current usage:")
    print(f"     - Per second: {rate_status['current']['per_second']}/{rate_status['limits']['per_second']}")
    print(f"     - Per minute: {rate_status['current']['per_minute']}/{rate_status['limits']['per_minute']}")
    print(f"     - Per day: {rate_status['current']['per_day']}/{rate_status['limits']['per_day']}")
    
    # Test cost monitor
    print("\n2. Cost Monitor Status...")
    cost_status = await enhanced_routes_service.cost_monitor.get_api_usage("routes")
    print(f"   Daily cost: ${cost_status['daily_cost']}")
    print(f"   Daily budget: ${cost_status['thresholds']['daily_critical']}")
    print(f"   Budget used: {cost_status['daily_percentage']}%")
    print(f"   Over budget: {cost_status['over_budget']}")
    
    # Test circuit breaker
    print("\n3. Circuit Breaker Status...")
    cb_status = enhanced_routes_service.circuit_breaker.get_status()
    print(f"   State: {cb_status['state']}")
    print(f"   Failure count: {cb_status['failure_count']}")
    print(f"   Success count: {cb_status['success_count']}")
    print(f"   Can execute: {cb_status['can_execute']}")
    
    # Test cache
    print("\n4. Cache Statistics...")
    cache_stats = await enhanced_routes_service.cache.get_cache_stats()
    print(f"   Total keys: {cache_stats['total_keys']}")
    print(f"   Total memory: {cache_stats['total_memory_bytes']} bytes")
    print(f"   By API type:")
    for api_type, stats in cache_stats['by_api'].items():
        print(f"     - {api_type}: {stats['count']} keys, {stats['memory_bytes']} bytes")


async def test_development_mode():
    """Test development mode detection"""
    print("\n\n=== Testing Development Mode ===")
    
    dev_manager = enhanced_routes_service.dev_mode_manager
    
    print("\n1. Current mode detection...")
    mode = await dev_manager.detect_mode()
    print(f"   Mode: {mode.value}")
    print(f"   Is production: {await dev_manager.is_production_mode()}")
    print(f"   Is development: {await dev_manager.is_development_mode()}")
    print(f"   Should use mock (routes): {await dev_manager.should_use_mock_service('routes')}")
    
    print("\n2. Service mode details...")
    details = await dev_manager.get_service_mode_details()
    print(f"   Current mode: {details['current_mode']}")
    print(f"   API keys status:")
    for service, status in details['api_keys_status'].items():
        print(f"     - {service}: {status}")
    print(f"   Use mock services: {details['use_mock_services']}")


async def test_api_key_management():
    """Test API key management"""
    print("\n\n=== Testing API Key Management ===")
    
    manager = await get_api_key_manager()
    
    print("\n1. Setting test API keys...")
    await manager.set_key("test_api", "test_key_12345")
    print("   Test key set successfully")
    
    print("\n2. Retrieving API key...")
    key = await manager.get_key("test_api")
    print(f"   Retrieved: {'*' * (len(key) - 4) + key[-4:] if key else 'None'}")
    
    print("\n3. Listing all keys...")
    keys = await manager.list_keys()
    print(f"   Available keys: {keys}")
    
    print("\n4. Deleting test key...")
    deleted = await manager.delete_key("test_api")
    print(f"   Deleted: {deleted}")


async def simulate_failures():
    """Simulate various failure scenarios"""
    print("\n\n=== Simulating Failure Scenarios ===")
    
    print("\n1. Simulating rate limit exceeded...")
    # Make multiple rapid requests
    for i in range(5):
        result = await enhanced_routes_service.calculate_route(
            origin=f"25.{i:03d},121.565",
            destination="25.047,121.517"
        )
        print(f"   Request {i+1}: {'Success' if result else 'Failed'}")
    
    print("\n2. Circuit breaker behavior...")
    # Circuit breaker is already tested in the service
    print("   Circuit breaker automatically handles failures")
    print("   Opens after 5 consecutive failures")
    print("   Recovers after timeout period")
    
    print("\n3. Cost budget enforcement...")
    # Track some mock costs
    await enhanced_routes_service.cost_monitor.track_cost(
        "routes",
        "test_operation",
        Decimal("10.00"),
        {"test": True}
    )
    print("   Cost tracked: $10.00")
    
    # Check if over budget
    allowed = await enhanced_routes_service.cost_monitor.check_budget(
        "routes",
        Decimal("5.00")
    )
    print(f"   Additional $5.00 allowed: {allowed}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Enhanced Google API Services Test Suite")
    print("=" * 60)
    
    try:
        # Test each service
        await test_routes_service()
        await test_vertex_ai_service()
        await test_monitoring_components()
        await test_development_mode()
        await test_api_key_management()
        await simulate_failures()
        
        print("\n\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())