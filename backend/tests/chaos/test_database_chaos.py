"""
Chaos Engineering Tests - Database Connection Pool and Failures
Tests system behavior under database stress and failures
"""

import asyncio
import os
import time
from unittest.mock import MagicMock, patch

import psutil
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool


class TestDatabaseChaos:
    """Test system resilience under database disruptions"""

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, client: AsyncClient, test_settings):
        """Test behavior when database connection pool is exhausted"""
        # Create engine with small pool for testing
        test_engine = create_async_engine(
            test_settings.DATABASE_URL,
            pool_size=2,  # Very small pool
            max_overflow=1,  # Limited overflow
            pool_timeout=1,  # Quick timeout
            pool_pre_ping=True,
        )

        # Track metrics
        connection_attempts = []
        pool_exhaustion_errors = 0
        successful_connections = 0

        # Simulate many concurrent database operations
        async def acquire_connection(conn_id: int):
            start_time = time.time()
            try:
                async with test_engine.connect() as conn:
                    # Hold connection for a bit to simulate work
                    await asyncio.sleep(0.5)
                    await conn.execute("SELECT 1")
                    successful_connections_count = 1
                    return {
                        "conn_id": conn_id,
                        "success": True,
                        "acquisition_time": time.time() - start_time,
                    }
            except (TimeoutError, SQLTimeoutError) as e:
                return {
                    "conn_id": conn_id,
                    "success": False,
                    "error": "pool_timeout",
                    "acquisition_time": time.time() - start_time,
                }
            except Exception as e:
                return {
                    "conn_id": conn_id,
                    "success": False,
                    "error": str(type(e).__name__),
                    "acquisition_time": time.time() - start_time,
                }

        # Launch concurrent connections exceeding pool size
        concurrent_count = 10  # Much larger than pool size
        tasks = []

        for i in range(concurrent_count):
            task = asyncio.create_task(acquire_connection(i))
            tasks.append(task)
            # Small delay to spread out requests
            await asyncio.sleep(0.05)

        # Wait for all tasks
        results = await asyncio.gather(*tasks)

        # Analyze results
        successful_connections = sum(1 for r in results if r["success"])
        pool_timeouts = sum(1 for r in results if r.get("error") == "pool_timeout")

        print(f"Connection attempts: {concurrent_count}")
        print(f"Successful: {successful_connections}")
        print(f"Pool timeouts: {pool_timeouts}")

        # Verify connection pool behavior
        assert pool_timeouts > 0, "Should have some pool timeouts with exhausted pool"
        assert (
            successful_connections >= 2
        ), "At least pool_size connections should succeed"

        # Check queue behavior - connections should be queued and eventually succeed
        avg_wait_time = sum(r["acquisition_time"] for r in results) / len(results)
        assert avg_wait_time < 3.0, f"Average wait time too high: {avg_wait_time:.2f}s"

        # Cleanup
        await test_engine.dispose()

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_database_connection_failure_recovery(self, client: AsyncClient):
        """Test system recovery when database becomes unavailable"""
        # Track health check results
        health_checks = []

        # Baseline health check
        response = await client.get("/api/v1/health/db")
        baseline_healthy = response.status_code == 200

        # Simulate database becoming unavailable
        with patch(
            "asyncpg.connect",
            side_effect=OperationalError("Database unavailable", "", ""),
        ):
            # Test health check during outage
            for i in range(5):
                try:
                    response = await client.get("/api/v1/health/db")
                    health_checks.append(
                        {
                            "attempt": i,
                            "status": response.status_code,
                            "healthy": response.status_code == 200,
                        }
                    )
                except Exception as e:
                    health_checks.append(
                        {"attempt": i, "status": 0, "healthy": False, "error": str(e)}
                    )
                await asyncio.sleep(0.5)

        # Database should be marked unhealthy during outage
        outage_health = [h["healthy"] for h in health_checks]
        assert not any(
            outage_health
        ), "Database incorrectly reported as healthy during outage"

        # Test recovery after database comes back
        recovery_checks = []
        for i in range(5):
            response = await client.get("/api/v1/health/db")
            recovery_checks.append(
                {
                    "attempt": i,
                    "status": response.status_code,
                    "healthy": response.status_code == 200,
                }
            )
            if response.status_code == 200:
                break
            await asyncio.sleep(1)

        # Should recover within 5 attempts
        assert any(
            r["healthy"] for r in recovery_checks
        ), "Database did not recover after connection restored"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_slow_query_handling(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test system behavior with slow database queries"""
        # Create many test records to slow down queries
        from app.models.customer import Customer

        # Insert test customers
        customers = []
        for i in range(100):
            customer = Customer(
                customer_code=f"CHAOS{i:04d}",
                short_name=f"Chaos Test Customer {i}",
                address=f"Test Address {i}",
                phone1=f"09{i:08d}",
                area="測試區",
            )
            customers.append(customer)

        db_session.add_all(customers)
        await db_session.commit()

        # Test slow query handling
        slow_query_params = {
            "search": "Chaos",  # Will match all test customers
            "page_size": 100,  # Large page size
            "include_orders": True,  # Join operation
        }

        start_time = time.time()
        response = await client.get(
            "/api/v1/customers",
            params=slow_query_params,
            headers={"Authorization": "Bearer test-token"},
            timeout=10.0,  # Generous timeout
        )
        query_time = time.time() - start_time

        # Should complete even with slow query
        assert response.status_code in [
            200,
            401,
        ], f"Slow query failed with status {response.status_code}"

        # Should not take too long (circuit breaker or timeout)
        assert query_time < 5.0, f"Query took too long: {query_time:.2f}s"

        # Check if response indicates degraded performance
        if response.status_code == 200:
            data = response.json()
            # System might limit results or switch to simplified query
            if "metadata" in data:
                print(f"Query metadata: {data['metadata']}")

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_transaction_rollback_integrity(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test data integrity during transaction failures"""
        # Create a complex transaction that might fail
        order_data = {
            "customer_id": 1,
            "scheduled_date": "2024-12-25T10:00:00",
            "qty_50kg": 5,
            "qty_20kg": 3,
            "payment_method": "cash",
            "delivery_address": "Transaction Test Address",
        }

        # Track order count before transaction
        from app.models.order import Order

        initial_count = await db_session.execute("SELECT COUNT(*) FROM orders")
        initial_order_count = initial_count.scalar()

        # Simulate transaction failure midway
        with patch(
            "app.services.order_service.OrderService.calculate_totals",
            side_effect=Exception("Simulated calculation error"),
        ):
            try:
                response = await client.post(
                    "/api/v1/orders",
                    json=order_data,
                    headers={"Authorization": "Bearer test-token"},
                )
            except Exception:
                pass  # Expected to fail

        # Verify no partial data was committed
        final_count = await db_session.execute("SELECT COUNT(*) FROM orders")
        final_order_count = final_count.scalar()

        assert (
            final_order_count == initial_order_count
        ), "Transaction not properly rolled back - data integrity compromised"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_connection_leak_prevention(self, client: AsyncClient):
        """Test that system prevents database connection leaks"""
        # Monitor system resources
        process = psutil.Process(os.getpid())
        initial_connections = len(process.connections(kind="tcp"))

        # Make many requests that could leak connections
        leak_test_iterations = 50

        for i in range(leak_test_iterations):
            try:
                # Various operations that use database
                tasks = [
                    client.get("/api/v1/customers"),
                    client.get("/api/v1/orders"),
                    client.get("/api/v1/health/db"),
                ]

                # Don't wait for all to complete (simulating interrupted requests)
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=0.5
                )
            except asyncio.TimeoutError:
                # Some requests will timeout - potential for leaks
                pass

            # Small delay between iterations
            await asyncio.sleep(0.1)

        # Allow cleanup time
        await asyncio.sleep(2)

        # Check for connection leaks
        final_connections = len(process.connections(kind="tcp"))
        connection_increase = final_connections - initial_connections

        print(f"Initial connections: {initial_connections}")
        print(f"Final connections: {final_connections}")
        print(f"Increase: {connection_increase}")

        # Should not have significant connection leak
        assert (
            connection_increase < 10
        ), f"Possible connection leak detected: {connection_increase} new connections"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_deadlock_detection_and_recovery(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test system behavior during database deadlocks"""
        # Create scenario that could cause deadlock
        # Two concurrent transactions updating same resources in different order

        async def transaction_a(session: AsyncSession):
            """Update customers then orders"""
            try:
                await session.execute(
                    "UPDATE customers SET updated_at = NOW() WHERE id = 1"
                )
                await asyncio.sleep(0.1)  # Increase chance of deadlock
                await session.execute(
                    "UPDATE orders SET updated_at = NOW() WHERE customer_id = 1"
                )
                await session.commit()
                return {"success": True}
            except Exception as e:
                await session.rollback()
                return {"success": False, "error": str(e)}

        async def transaction_b(session: AsyncSession):
            """Update orders then customers - opposite order"""
            try:
                await session.execute(
                    "UPDATE orders SET updated_at = NOW() WHERE customer_id = 1"
                )
                await asyncio.sleep(0.1)  # Increase chance of deadlock
                await session.execute(
                    "UPDATE customers SET updated_at = NOW() WHERE id = 1"
                )
                await session.commit()
                return {"success": True}
            except Exception as e:
                await session.rollback()
                return {"success": False, "error": str(e)}

        # Run transactions concurrently
        from app.core.database import get_async_session

        results = await asyncio.gather(
            transaction_a(db_session), transaction_b(db_session), return_exceptions=True
        )

        # At least one should succeed (deadlock detection and retry)
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))

        print(f"Deadlock test results: {results}")

        # System should handle deadlock gracefully
        assert (
            successful >= 1
        ), "Both transactions failed - deadlock not handled properly"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_database_failover(self, client: AsyncClient):
        """Test system behavior during database failover"""
        # Track service availability during failover
        failover_duration = 10  # seconds
        check_interval = 0.5
        availability_timeline = []

        start_time = time.time()

        # Simulate primary database failure and failover
        with patch("app.core.database.get_async_session") as mock_session:
            # First 3 seconds: primary fails
            # Next 2 seconds: failover in progress
            # Remaining time: replica promoted

            while (time.time() - start_time) < failover_duration:
                elapsed = time.time() - start_time

                if elapsed < 3:
                    # Primary database failure
                    mock_session.side_effect = OperationalError(
                        "Primary database down", "", ""
                    )
                elif elapsed < 5:
                    # Failover in progress - intermittent failures
                    if int(elapsed * 10) % 2 == 0:
                        mock_session.side_effect = OperationalError(
                            "Failover in progress", "", ""
                        )
                    else:
                        mock_session.side_effect = None
                else:
                    # Replica promoted - service restored
                    mock_session.side_effect = None

                try:
                    response = await client.get("/api/v1/health")
                    availability_timeline.append(
                        {
                            "time": elapsed,
                            "available": response.status_code == 200,
                            "status": response.status_code,
                        }
                    )
                except Exception:
                    availability_timeline.append(
                        {"time": elapsed, "available": False, "status": 0}
                    )

                await asyncio.sleep(check_interval)

        # Analyze failover performance
        total_checks = len(availability_timeline)
        available_checks = sum(
            1 for check in availability_timeline if check["available"]
        )
        availability_percentage = (available_checks / total_checks) * 100

        print(f"Availability during failover: {availability_percentage:.2f}%")

        # Should maintain reasonable availability even during failover
        assert (
            availability_percentage >= 50
        ), f"Availability too low during failover: {availability_percentage:.2f}%"

        # Recovery should happen within reasonable time
        recovery_time = None
        for i in range(len(availability_timeline) - 1, -1, -1):
            if availability_timeline[i]["available"]:
                recovery_time = availability_timeline[i]["time"]
                break

        assert recovery_time is not None, "Service did not recover after failover"
        assert recovery_time < 8, f"Recovery took too long: {recovery_time:.2f}s"
