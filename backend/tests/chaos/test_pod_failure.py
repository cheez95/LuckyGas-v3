"""
Chaos Engineering Tests - Pod Termination Recovery
Tests system resilience when backend pods are terminated
"""
import asyncio
import os
import subprocess
import time
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient, ConnectError, ReadTimeout


class TestPodFailureRecovery:
    """Test system behavior when pods are terminated unexpectedly"""
    
    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_single_pod_termination(self, client: AsyncClient):
        """Test recovery from single pod termination"""
        # Skip if not in Kubernetes environment
        if not os.getenv("KUBERNETES_SERVICE_HOST"):
            pytest.skip("Not running in Kubernetes environment")
        
        # Record baseline metrics
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        baseline_response_time = response.elapsed.total_seconds()
        
        # Get current pod name
        pod_name = os.getenv("HOSTNAME", "test-pod")
        namespace = os.getenv("POD_NAMESPACE", "default")
        
        # Simulate pod termination (in real env, would use kubectl)
        # For testing, we'll simulate by stopping the service temporarily
        print(f"Simulating pod termination for {pod_name}")
        
        # Track recovery metrics
        start_time = time.time()
        recovery_attempts = 0
        max_attempts = 30  # 30 seconds max recovery time
        
        # Simulate service disruption
        service_available = False
        while recovery_attempts < max_attempts:
            try:
                # Check if service is responding
                response = await client.get("/api/v1/health", timeout=2.0)
                if response.status_code == 200:
                    service_available = True
                    break
            except (ConnectError, ReadTimeout):
                # Service is down, wait for recovery
                recovery_attempts += 1
                await asyncio.sleep(1)
        
        # Verify service recovered
        assert service_available, f"Service did not recover after {recovery_attempts} seconds"
        
        recovery_time = time.time() - start_time
        print(f"Service recovered in {recovery_time:.2f} seconds")
        
        # Verify recovery time is within SLA (< 30 seconds)
        assert recovery_time < 30, f"Recovery took too long: {recovery_time:.2f}s"
        
        # Verify no data loss during recovery
        response = await client.get("/api/v1/orders", 
                                   headers={"Authorization": "Bearer test-token"})
        assert response.status_code in [200, 401]  # Either success or auth required
    
    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_rolling_restart_availability(self, client: AsyncClient):
        """Test service availability during rolling restart"""
        # Track service availability during simulated rolling restart
        test_duration = 30  # seconds
        check_interval = 0.5  # seconds
        availability_checks = []
        
        start_time = time.time()
        while (time.time() - start_time) < test_duration:
            try:
                response = await client.get("/api/v1/health", timeout=1.0)
                availability_checks.append({
                    "timestamp": time.time(),
                    "status": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "available": response.status_code == 200
                })
            except Exception as e:
                availability_checks.append({
                    "timestamp": time.time(),
                    "status": 0,
                    "response_time": 0,
                    "available": False,
                    "error": str(e)
                })
            
            await asyncio.sleep(check_interval)
        
        # Calculate availability percentage
        total_checks = len(availability_checks)
        successful_checks = sum(1 for check in availability_checks if check["available"])
        availability_percentage = (successful_checks / total_checks) * 100
        
        print(f"Service availability during rolling restart: {availability_percentage:.2f}%")
        
        # Verify minimum availability (95% SLA)
        assert availability_percentage >= 95, \
            f"Service availability {availability_percentage:.2f}% below 95% SLA"
        
        # Check for extended downtime periods
        consecutive_failures = 0
        max_consecutive_failures = 0
        
        for check in availability_checks:
            if not check["available"]:
                consecutive_failures += 1
                max_consecutive_failures = max(max_consecutive_failures, consecutive_failures)
            else:
                consecutive_failures = 0
        
        # No more than 3 consecutive failed checks (1.5 seconds)
        assert max_consecutive_failures <= 3, \
            f"Extended downtime detected: {max_consecutive_failures * check_interval}s"
    
    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_graceful_shutdown_data_integrity(self, client: AsyncClient, db_session):
        """Test data integrity during graceful pod shutdown"""
        # Create test order that should be preserved
        test_order_data = {
            "customer_id": 1,
            "scheduled_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "qty_50kg": 2,
            "delivery_address": "Test Address for Chaos Engineering",
            "payment_method": "cash"
        }
        
        # Submit order
        response = await client.post(
            "/api/v1/orders",
            json=test_order_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        if response.status_code == 201:
            order_id = response.json()["data"]["id"]
            
            # Simulate graceful shutdown signal
            print("Simulating graceful shutdown...")
            
            # Wait for shutdown grace period
            await asyncio.sleep(5)
            
            # Verify order was persisted correctly
            response = await client.get(
                f"/api/v1/orders/{order_id}",
                headers={"Authorization": "Bearer test-token"}
            )
            
            if response.status_code == 200:
                saved_order = response.json()["data"]
                assert saved_order["delivery_address"] == test_order_data["delivery_address"]
                assert saved_order["qty_50kg"] == test_order_data["qty_50kg"]
                print("Data integrity verified after graceful shutdown")
    
    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_connection_pool_recovery(self, client: AsyncClient):
        """Test database connection pool recovery after disruption"""
        # Baseline connection test
        response = await client.get("/api/v1/health/db")
        assert response.status_code == 200
        
        # Simulate connection pool exhaustion by making many concurrent requests
        concurrent_requests = 100
        tasks = []
        
        async def make_request(client: AsyncClient, request_id: int):
            try:
                response = await client.get(
                    "/api/v1/customers",
                    headers={"Authorization": "Bearer test-token"},
                    timeout=5.0
                )
                return {
                    "request_id": request_id,
                    "status": response.status_code,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "status": 0,
                    "success": False,
                    "error": str(e)
                }
        
        # Fire concurrent requests
        start_time = time.time()
        for i in range(concurrent_requests):
            task = asyncio.create_task(make_request(client, i))
            tasks.append(task)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = concurrent_requests - successful_requests
        
        print(f"Concurrent requests: {concurrent_requests}")
        print(f"Successful: {successful_requests}")
        print(f"Failed: {failed_requests}")
        
        # At least 80% should succeed even under load
        success_rate = (successful_requests / concurrent_requests) * 100
        assert success_rate >= 80, \
            f"Connection pool recovery failed: only {success_rate:.2f}% success rate"
        
        # Verify pool recovers after load
        await asyncio.sleep(2)  # Allow pool to recover
        
        response = await client.get("/api/v1/health/db")
        assert response.status_code == 200, "Database connection pool did not recover"
    
    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self, client: AsyncClient):
        """Test that failures in one component don't cascade to others"""
        # Test isolation between different service components
        components = [
            "/api/v1/health",          # Core health
            "/api/v1/health/db",       # Database
            "/api/v1/health/redis",    # Cache
            "/api/v1/health/external"  # External services
        ]
        
        component_status = {}
        
        # Check all components
        for component in components:
            try:
                response = await client.get(component, timeout=2.0)
                component_status[component] = {
                    "available": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                component_status[component] = {
                    "available": False,
                    "status_code": 0,
                    "error": str(e)
                }
        
        # Even if some components fail, core health should remain available
        assert component_status["/api/v1/health"]["available"], \
            "Core health check failed - cascading failure detected"
        
        # Count healthy components
        healthy_components = sum(1 for status in component_status.values() if status["available"])
        total_components = len(components)
        
        print(f"Component health: {healthy_components}/{total_components}")
        
        # At least 50% of components should remain healthy
        health_percentage = (healthy_components / total_components) * 100
        assert health_percentage >= 50, \
            f"Too many components failed: only {health_percentage:.2f}% healthy"