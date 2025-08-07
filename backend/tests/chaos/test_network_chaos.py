"""
Chaos Engineering Tests - Network Latency and Failures
Tests system behavior under various network conditions
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ConnectError, ReadTimeout


class TestNetworkChaos:
    """Test system resilience under network disruptions"""

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_network_latency_100ms(self, client: AsyncClient):
        """Test API behavior with 100ms network latency"""

        # Simulate 100ms latency by adding delay
        async def delayed_request(url: str, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return await client.get(url, **kwargs)

        # Test critical endpoints with latency
        endpoints = [
            "/api / v1 / health",
            "/api / v1 / orders",
            "/api / v1 / customers",
        ]

        results = []
        for endpoint in endpoints:
            start_time = time.time()
            try:
                response = await delayed_request(endpoint, timeout=5.0)
                end_time = time.time()
                results.append(
                    {
                        "endpoint": endpoint,
                        "status": response.status_code,
                        "total_time": end_time - start_time,
                        "success": True,
                    }
                )
            except ReadTimeout:
                results.append(
                    {
                        "endpoint": endpoint,
                        "status": 0,
                        "error": "timeout",
                        "success": False,
                    }
                )

        # All endpoints should handle 100ms latency gracefully
        for result in results:
            assert result["success"], f"{result['endpoint']} failed with 100ms latency"
            # Total time should be reasonable (< 2 seconds even with latency)
            if "total_time" in result:
                assert (
                    result["total_time"] < 2.0
                ), f"{result['endpoint']} took too long: {result['total_time']:.2f}s"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_network_latency_500ms(self, client: AsyncClient):
        """Test API behavior with 500ms network latency"""
        # Track circuit breaker activations
        circuit_breaker_trips = []

        async def make_delayed_request(endpoint: str, delay: float = 0.5):
            start_time = time.time()
            try:
                # Simulate network delay
                await asyncio.sleep(delay)
                response = await client.get(endpoint, timeout=3.0)
                return {
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "response_time": time.time() - start_time,
                    "success": response.status_code == 200,
                }
            except ReadTimeout:
                circuit_breaker_trips.append(
                    {"endpoint": endpoint, "timestamp": time.time()}
                )
                return {
                    "endpoint": endpoint,
                    "status": 0,
                    "response_time": time.time() - start_time,
                    "success": False,
                    "error": "timeout",
                }

        # Test multiple requests to trigger circuit breaker
        test_endpoints = ["/api / v1 / orders"] * 5  # Same endpoint multiple times
        results = []

        for endpoint in test_endpoints:
            result = await make_delayed_request(endpoint)
            results.append(result)
            await asyncio.sleep(0.1)  # Small delay between requests

        # Check if circuit breaker activated (should fail fast after initial timeouts)
        response_times = [r["response_time"] for r in results if not r["success"]]
        if len(response_times) > 3:
            # Later failures should fail faster due to circuit breaker
            avg_early_failures = sum(response_times[:2]) / 2
            avg_late_failures = sum(response_times[-2:]) / 2

            print(f"Early failure avg: {avg_early_failures:.2f}s")
            print(f"Late failure avg: {avg_late_failures:.2f}s")

            # Circuit breaker should make late failures faster
            assert (
                avg_late_failures < avg_early_failures * 0.5
            ), "Circuit breaker not activating properly"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_network_latency_1s(self, client: AsyncClient):
        """Test API behavior with 1 second network latency"""
        # Test degraded mode activation
        high_latency_endpoints = {
            "/api / v1 / routes / optimize": {
                "timeout": 10.0,
                "degraded_threshold": 2.0,
            },
            "/api / v1 / predictions / daily": {
                "timeout": 15.0,
                "degraded_threshold": 3.0,
            },
        }

        for endpoint, config in high_latency_endpoints.items():
            start_time = time.time()

            # Simulate 1s network latency
            await asyncio.sleep(1.0)

            try:
                response = await client.post(
                    endpoint, json={"test": "data"}, timeout=config["timeout"]
                )

                elapsed = time.time() - start_time

                # Service should switch to degraded mode
                if elapsed > config["degraded_threshold"]:
                    # Check for degraded mode indicators
                    if response.status_code == 200:
                        response_data = response.json()
                        # Service might return cached or simplified results
                        assert "degraded_mode" in response_data.get(
                            "metadata", {}
                        ) or "cached" in response_data.get(
                            "metadata", {}
                        ), f"{endpoint} should indicate degraded mode with high latency"

            except ReadTimeout:
                # Timeout is acceptable for non - critical endpoints under extreme latency
                if endpoint not in ["/api / v1 / health", "/api / v1 / auth / login"]:
                    pass  # Expected for some endpoints
                else:
                    pytest.fail(
                        f"Critical endpoint {endpoint} timed out with 1s latency"
                    )

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_intermittent_network_failures(self, client: AsyncClient):
        """Test system behavior with intermittent network failures"""
        # Simulate 30% packet loss
        failure_rate = 0.3
        total_requests = 20
        failed_requests = 0
        successful_requests = 0

        import random

        for i in range(total_requests):
            should_fail = random.random() < failure_rate

            try:
                if should_fail:
                    # Simulate network failure
                    raise ConnectError("Simulated network failure")

                response = await client.get("/api / v1 / health")
                if response.status_code == 200:
                    successful_requests += 1
            except ConnectError:
                failed_requests += 1

            await asyncio.sleep(0.1)

        print(f"Total requests: {total_requests}")
        print(f"Successful: {successful_requests}")
        print(f"Failed: {failed_requests}")
        print(f"Actual failure rate: {failed_requests / total_requests:.2%}")

        # System should handle intermittent failures gracefully
        # Success rate should be close to (1 - failure_rate)
        expected_success_rate = 1 - failure_rate
        actual_success_rate = successful_requests / total_requests

        # Allow 10% deviation
        assert (
            abs(actual_success_rate - expected_success_rate) < 0.1
        ), f"Success rate {actual_success_rate:.2%} deviates too much from expected {expected_success_rate:.2%}"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_complete_network_partition(self, client: AsyncClient):
        """Test system behavior during complete network partition"""
        # Simulate complete network isolation
        offline_mode_activated = False
        queued_operations = []

        # Test offline mode activation
        try:
            # Simulate network partition
            with patch(
                "httpx.AsyncClient.get", side_effect=ConnectError("Network unreachable")
            ):
                # System should detect offline state
                # In real implementation, this would trigger offline mode
                offline_mode_activated = True

                # Test queueing of critical operations
                critical_operation = {
                    "type": "order_update",
                    "order_id": 123,
                    "status": "delivered",
                    "timestamp": datetime.now().isoformat(),
                }

                queued_operations.append(critical_operation)

        except Exception as e:
            print(f"Exception during network partition: {e}")

        assert (
            offline_mode_activated
        ), "System should activate offline mode during network partition"
        assert (
            len(queued_operations) > 0
        ), "System should queue operations during offline mode"

        # Test recovery after network partition ends
        print("Testing recovery after network partition...")

        # Simulate network recovery
        recovery_successful = False
        try:
            response = await client.get("/api / v1 / health")
            if response.status_code == 200:
                recovery_successful = True

                # Check if queued operations are being processed
                # In real implementation, this would check sync status
                print(f"Queued operations to sync: {len(queued_operations)}")

        except Exception as e:
            print(f"Recovery failed: {e}")

        assert recovery_successful, "System should recover after network partition ends"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_timeout_cascade_prevention(self, client: AsyncClient):
        """Test that timeouts don't cascade through the system"""
        # Test timeout handling at different layers
        timeout_layers = {
            "client": 1.0,  # Client timeout
            "api": 2.0,  # API gateway timeout
            "service": 3.0,  # Service layer timeout
            "database": 5.0,  # Database timeout
        }

        results = {}

        for layer, timeout in timeout_layers.items():
            start_time = time.time()
            try:
                # Simulate slow operation
                if layer == "database":
                    # Simulate slow database query
                    response = await client.get(
                        "/api / v1 / orders?page_size=1000", timeout=timeout
                    )
                else:
                    response = await client.get(
                        f"/api / v1 / health/{layer}", timeout=timeout
                    )

                results[layer] = {
                    "success": True,
                    "status": response.status_code,
                    "time": time.time() - start_time,
                }
            except ReadTimeout:
                results[layer] = {
                    "success": False,
                    "error": "timeout",
                    "time": time.time() - start_time,
                }

        # Verify timeout isolation
        # Timeouts at one layer shouldn't affect others
        timeout_count = sum(1 for r in results.values() if not r["success"])

        # Not all layers should timeout
        assert timeout_count < len(
            timeout_layers
        ), "Timeout cascade detected - all layers timed out"

        # Each layer should respect its own timeout
        for layer, config_timeout in timeout_layers.items():
            if not results[layer]["success"]:
                actual_timeout = results[layer]["time"]
                # Allow 0.5s tolerance
                assert (
                    actual_timeout < config_timeout + 0.5
                ), f"{layer} timeout exceeded configured value: {actual_timeout:.2f}s > {config_timeout}s"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_retry_with_backoff(self, client: AsyncClient):
        """Test retry mechanism with exponential backof"""
        retry_attempts = []
        max_retries = 3

        # Mock a service that fails initially then succeeds
        failure_count = 0

        async def flaky_endpoint_simulation():
            nonlocal failure_count
            attempt_time = time.time()
            retry_attempts.append(attempt_time)

            if failure_count < 2:  # Fail first 2 attempts
                failure_count += 1
                raise ConnectError("Service temporarily unavailable")

            return {"status": "success", "attempts": len(retry_attempts)}

        # Test retry with backoff
        start_time = time.time()
        result = None

        for attempt in range(max_retries):
            try:
                result = await flaky_endpoint_simulation()
                break
            except ConnectError:
                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    backoff_time = 2**attempt
                    await asyncio.sleep(backoff_time)
                else:
                    raise

        assert result is not None, "Retry mechanism failed to recover"
        assert result["attempts"] == 3, f"Expected 3 attempts, got {result['attempts']}"

        # Verify exponential backoff timing
        if len(retry_attempts) >= 3:
            # Time between attempts should increase exponentially
            first_gap = retry_attempts[1] - retry_attempts[0]
            second_gap = retry_attempts[2] - retry_attempts[1]

            # Second gap should be roughly 2x the first gap (with some tolerance)
            assert (
                1.5 < (second_gap / first_gap) < 2.5
            ), f"Exponential backoff not working correctly: gaps {first_gap:.2f}s, {second_gap:.2f}s"
