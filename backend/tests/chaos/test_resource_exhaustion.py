"""
Chaos Engineering Tests - Resource Exhaustion
Tests system behavior under resource constraints (memory, CPU, disk)
"""

import asyncio
import gc
import multiprocessing
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import psutil
import pytest
from httpx import AsyncClient


class TestResourceExhaustion:
    """Test system behavior under resource exhaustion scenarios"""

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_memory_exhaustion_handling(self, client: AsyncClient):
        """Test system behavior when memory is exhausted"""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Track memory allocations
        memory_blocks = []
        allocation_results = []

        try:
            # Gradually consume memory
            block_size = 10 * 1024 * 1024  # 10MB blocks
            max_blocks = 50  # Up to 500MB

            for i in range(max_blocks):
                try:
                    # Allocate memory block
                    block = bytearray(block_size)
                    memory_blocks.append(block)

                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = current_memory - initial_memory

                    # Test API response under memory pressure
                    start_time = time.time()
                    response = await client.get("/api/v1/health", timeout=5.0)
                    response_time = time.time() - start_time

                    allocation_results.append(
                        {
                            "block": i,
                            "memory_increase_mb": memory_increase,
                            "api_status": response.status_code,
                            "api_response_time": response_time,
                            "memory_percent": process.memory_percent(),
                        }
                    )

                    # Stop if system is under severe stress
                    if response_time > 2.0 or process.memory_percent() > 80:
                        print(
                            f"Stopping at block {i}, memory {memory_increase:.1f}MB, "
                            f"response time {response_time:.2f}s"
                        )
                        break

                except MemoryError:
                    print(f"MemoryError at block {i}")
                    break

                await asyncio.sleep(0.1)  # Small delay between allocations

            # Analyze system behavior under memory pressure
            if allocation_results:
                # Check response time degradation
                early_response_times = [
                    r["api_response_time"] for r in allocation_results[:5]
                ]
                late_response_times = [
                    r["api_response_time"] for r in allocation_results[-5:]
                ]

                avg_early = sum(early_response_times) / len(early_response_times)
                avg_late = (
                    sum(late_response_times) / len(late_response_times)
                    if late_response_times
                    else avg_early
                )

                print(f"Early avg response time: {avg_early:.3f}s")
                print(f"Late avg response time: {avg_late:.3f}s")

                # Response time should degrade gracefully, not catastrophically
                assert (
                    avg_late < avg_early * 10
                ), f"Response time degraded too severely: {avg_early:.3f}s -> {avg_late:.3f}s"

                # API should remain available
                failed_requests = [
                    r for r in allocation_results if r["api_status"] != 200
                ]
                failure_rate = len(failed_requests) / len(allocation_results)
                assert (
                    failure_rate < 0.2
                ), f"Too many failures under memory pressure: {failure_rate:.1%}"

        finally:
            # Clean up memory
            memory_blocks.clear()
            gc.collect()

            # Verify memory is released
            await asyncio.sleep(1)
            final_memory = process.memory_info().rss / 1024 / 1024
            print(f"Memory released: {initial_memory:.1f}MB -> {final_memory:.1f}MB")

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_cpu_throttling_behavior(self, client: AsyncClient):
        """Test system behavior under CPU constraints"""

        # Function to consume CPU
        def cpu_intensive_task(duration):
            """Consume CPU for specified duration"""
            end_time = time.time() + duration
            while time.time() < end_time:
                # Intensive computation
                _ = sum(i * i for i in range(1000))

        # Get CPU count for scaling
        cpu_count = multiprocessing.cpu_count()

        # Track API performance under CPU load
        performance_metrics = []

        # Baseline performance
        baseline_start = time.time()
        baseline_response = await client.get("/api/v1/health")
        baseline_time = time.time() - baseline_start

        # Start CPU intensive tasks in background
        with ThreadPoolExecutor(max_workers=cpu_count) as executor:
            # Submit CPU intensive tasks
            futures = []
            for i in range(cpu_count * 2):  # Oversubscribe CPUs
                future = executor.submit(cpu_intensive_task, 5)  # 5 seconds of CPU work
                futures.append(future)

            # Test API performance under CPU load
            test_duration = 3  # seconds
            start_time = time.time()
            request_count = 0

            while (time.time() - start_time) < test_duration:
                request_start = time.time()
                try:
                    response = await client.get("/api/v1/health", timeout=2.0)
                    request_time = time.time() - request_start

                    performance_metrics.append(
                        {
                            "request_id": request_count,
                            "response_time": request_time,
                            "status_code": response.status_code,
                            "cpu_percent": psutil.cpu_percent(interval=0.1),
                        }
                    )
                except Exception as e:
                    performance_metrics.append(
                        {
                            "request_id": request_count,
                            "response_time": time.time() - request_start,
                            "status_code": 0,
                            "error": str(e),
                            "cpu_percent": psutil.cpu_percent(interval=0.1),
                        }
                    )

                request_count += 1
                await asyncio.sleep(0.2)  # Small delay between requests

        # Analyze results
        successful_requests = [
            m for m in performance_metrics if m["status_code"] == 200
        ]
        success_rate = (
            len(successful_requests) / len(performance_metrics)
            if performance_metrics
            else 0
        )

        # Calculate average response time under load
        avg_response_time = (
            sum(m["response_time"] for m in successful_requests)
            / len(successful_requests)
            if successful_requests
            else 0
        )

        print(f"Baseline response time: {baseline_time:.3f}s")
        print(f"Average response time under CPU load: {avg_response_time:.3f}s")
        print(f"Success rate under CPU load: {success_rate:.1%}")
        print(
            f"Average CPU during test: {sum(m['cpu_percent'] for m in performance_metrics) / len(performance_metrics):.1f}%"
        )

        # System should maintain reasonable performance
        assert (
            success_rate >= 0.8
        ), f"Success rate too low under CPU load: {success_rate:.1%}"
        assert (
            avg_response_time < baseline_time * 5
        ), f"Response time degraded too much: {baseline_time:.3f}s -> {avg_response_time:.3f}s"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_disk_space_exhaustion(self, client: AsyncClient):
        """Test system behavior when disk space is limited"""
        # Create temporary directory with limited space
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file_path = os.path.join(temp_dir, "disk_exhaustion_test.dat")

            # Get disk usage
            disk_usage = psutil.disk_usage(temp_dir)
            free_space_mb = disk_usage.free / 1024 / 1024

            print(f"Free disk space: {free_space_mb:.1f}MB")

            # Track system behavior as disk fills
            disk_fill_results = []

            try:
                # Write large files to consume disk space
                chunk_size = 10 * 1024 * 1024  # 10MB chunks
                chunks_written = 0
                max_chunks = min(
                    int(free_space_mb / 10), 50
                )  # Limit to 500MB or available space

                with open(test_file_path, "wb") as f:
                    for i in range(max_chunks):
                        try:
                            # Write chunk
                            data = bytearray(chunk_size)
                            f.write(data)
                            f.flush()
                            os.fsync(f.fileno())  # Force write to disk

                            chunks_written += 1

                            # Check system behavior
                            disk_usage = psutil.disk_usage(temp_dir)
                            disk_percent = disk_usage.percent

                            # Test logging capability
                            log_response = await client.post(
                                "/api/v1/admin/logs",
                                json={"message": f"Disk test {i}", "level": "info"},
                                headers={"Authorization": "Bearer test-token"},
                            )

                            # Test file upload capability
                            upload_response = await client.post(
                                "/api/v1/upload/test",
                                files={
                                    "file": ("test.txt", b"test data", "text/plain")
                                },
                                headers={"Authorization": "Bearer test-token"},
                            )

                            disk_fill_results.append(
                                {
                                    "chunk": i,
                                    "disk_percent": disk_percent,
                                    "log_status": log_response.status_code,
                                    "upload_status": upload_response.status_code,
                                    "free_space_mb": disk_usage.free / 1024 / 1024,
                                }
                            )

                            # Stop if disk is getting full
                            if disk_percent > 90:
                                print(f"Stopping at {disk_percent:.1f}% disk usage")
                                break

                        except (IOError, OSError) as e:
                            print(f"Disk write error at chunk {i}: {e}")
                            break

                # Analyze system behavior
                if disk_fill_results:
                    # Check degradation pattern
                    early_results = (
                        disk_fill_results[:5]
                        if len(disk_fill_results) >= 5
                        else disk_fill_results
                    )
                    late_results = (
                        disk_fill_results[-5:]
                        if len(disk_fill_results) >= 5
                        else disk_fill_results
                    )

                    # Logging should degrade gracefully
                    early_log_success = sum(
                        1 for r in early_results if r["log_status"] in [200, 201]
                    ) / len(early_results)
                    late_log_success = sum(
                        1 for r in late_results if r["log_status"] in [200, 201]
                    ) / len(late_results)

                    print(f"Early log success rate: {early_log_success:.1%}")
                    print(f"Late log success rate: {late_log_success:.1%}")

                    # Some degradation is expected, but not complete failure
                    assert (
                        late_log_success >= 0.5 or late_results[-1]["disk_percent"] > 95
                    ), "Logging failed too early with available disk space"

                    # File uploads should fail gracefully when disk is full
                    if late_results[-1]["disk_percent"] > 90:
                        late_upload_failures = sum(
                            1 for r in late_results if r["upload_status"] >= 500
                        )
                        assert late_upload_failures < len(
                            late_results
                        ), "All uploads resulted in server errors - should fail gracefully"

            finally:
                # Clean up
                if os.path.exists(test_file_path):
                    os.remove(test_file_path)

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_file_descriptor_exhaustion(self, client: AsyncClient):
        """Test system behavior when file descriptors are exhausted"""
        # Track open file descriptors
        process = psutil.Process(os.getpid())
        initial_fds = len(process.open_files())

        # Store opened files
        opened_files = []
        fd_exhaustion_results = []

        try:
            # Open many files to exhaust file descriptors
            temp_dir = tempfile.mkdtemp()
            max_files = 1000  # Typical soft limit is 1024

            for i in range(max_files):
                try:
                    # Open file and keep it open
                    file_path = os.path.join(temp_dir, f"fd_test_{i}.txt")
                    f = open(file_path, "w")
                    opened_files.append(f)

                    # Test system behavior
                    if i % 100 == 0:  # Test every 100 files
                        current_fds = len(process.open_files())

                        # Test API functionality
                        response = await client.get("/api/v1/health")

                        # Test database query
                        db_response = await client.get(
                            "/api/v1/customers",
                            headers={"Authorization": "Bearer test-token"},
                        )

                        fd_exhaustion_results.append(
                            {
                                "files_opened": i,
                                "fd_count": current_fds,
                                "health_status": response.status_code,
                                "db_query_status": db_response.status_code,
                            }
                        )

                except OSError as e:
                    if "Too many open files" in str(e):
                        print(f"Hit file descriptor limit at {i} files")

                        # System should still respond to health checks
                        health_response = await client.get("/api/v1/health")
                        assert (
                            health_response.status_code == 200
                        ), "Health check should work even with FD exhaustion"
                        break
                    else:
                        raise

            # Analyze results
            if fd_exhaustion_results:
                # Check for graceful degradation
                failed_health_checks = sum(
                    1 for r in fd_exhaustion_results if r["health_status"] != 200
                )
                assert (
                    failed_health_checks == 0
                ), "Health checks should not fail due to FD exhaustion"

                # Database queries might fail, but should not crash
                db_errors = sum(
                    1 for r in fd_exhaustion_results if r["db_query_status"] >= 500
                )
                assert (
                    db_errors < len(fd_exhaustion_results) / 2
                ), "Too many database errors due to FD exhaustion"

        finally:
            # Clean up
            for f in opened_files:
                try:
                    f.close()
                except:
                    pass

            # Remove temp directory
            if "temp_dir" in locals():
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)

            # Verify FDs are released
            final_fds = len(process.open_files())
            print(f"FD count: {initial_fds} -> {final_fds}")

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_thread_exhaustion(self, client: AsyncClient):
        """Test system behavior when thread pool is exhausted"""
        # Track active threads
        initial_thread_count = threading.active_count()
        print(f"Initial thread count: {initial_thread_count}")

        # Create many threads
        threads = []
        thread_results = []

        def thread_worker(thread_id, duration=5):
            """Worker that holds thread for specified duration"""
            thread_results.append(
                {"thread_id": thread_id, "start_time": time.time(), "status": "started"}
            )
            time.sleep(duration)
            thread_results.append(
                {"thread_id": thread_id, "end_time": time.time(), "status": "completed"}
            )

        try:
            # Create many threads to exhaust thread pool
            max_threads = 100

            for i in range(max_threads):
                try:
                    thread = threading.Thread(target=thread_worker, args=(i, 2))
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)

                    # Test system responsiveness
                    if i % 20 == 0:
                        current_thread_count = threading.active_count()

                        # Make API requests
                        start_time = time.time()
                        response = await client.get("/api/v1/health")
                        response_time = time.time() - start_time

                        print(
                            f"Threads: {current_thread_count}, Response time: {response_time:.3f}s"
                        )

                        # System should remain responsive
                        assert (
                            response.status_code == 200
                        ), f"Health check failed with {current_thread_count} threads"
                        assert (
                            response_time < 2.0
                        ), f"Response too slow ({response_time:.3f}s) with {current_thread_count} threads"

                except Exception as e:
                    print(f"Thread creation failed at {i}: {e}")
                    break

                # Small delay to avoid overwhelming system
                await asyncio.sleep(0.05)

            # Wait a bit for threads to run
            await asyncio.sleep(1)

            # Test concurrent request handling under thread pressure
            concurrent_requests = 10
            request_tasks = []

            for i in range(concurrent_requests):
                task = client.get("/api/v1/health")
                request_tasks.append(task)

            # All requests should complete
            responses = await asyncio.gather(*request_tasks, return_exceptions=True)
            successful_responses = [
                r
                for r in responses
                if not isinstance(r, Exception) and r.status_code == 200
            ]

            success_rate = len(successful_responses) / concurrent_requests
            assert (
                success_rate >= 0.8
            ), f"Too many failures under thread pressure: {success_rate:.1%}"

        finally:
            # Wait for threads to complete
            max_wait = 5
            start_wait = time.time()

            while (
                threading.active_count() > initial_thread_count
                and (time.time() - start_wait) < max_wait
            ):
                await asyncio.sleep(0.5)

            final_thread_count = threading.active_count()
            print(f"Final thread count: {final_thread_count}")

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, client: AsyncClient):
        """Test behavior when connection pools (HTTP, DB, Redis) are exhausted"""
        # Test HTTP connection pool exhaustion
        connection_metrics = []

        # Make many concurrent requests
        concurrent_count = 50

        async def make_request(request_id):
            start_time = time.time()
            try:
                # Don't close connection immediately
                response = await client.get(
                    "/api/v1/customers",
                    headers={
                        "Authorization": "Bearer test-token",
                        "Connection": "keep-alive",
                    },
                )
                return {
                    "request_id": request_id,
                    "status": response.status_code,
                    "response_time": time.time() - start_time,
                    "success": True,
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "status": 0,
                    "response_time": time.time() - start_time,
                    "success": False,
                    "error": str(e),
                }

        # Launch all requests concurrently
        tasks = [make_request(i) for i in range(concurrent_count)]
        results = await asyncio.gather(*tasks)

        # Analyze results
        successful = sum(1 for r in results if r["success"])
        failed = concurrent_count - successful
        avg_response_time = sum(r["response_time"] for r in results) / len(results)

        print(f"Concurrent requests: {concurrent_count}")
        print(f"Successful: {successful}, Failed: {failed}")
        print(f"Average response time: {avg_response_time:.3f}s")

        # Most requests should succeed
        success_rate = successful / concurrent_count
        assert success_rate >= 0.7, f"Too many connection failures: {success_rate:.1%}"

        # Response times should be reasonable
        slow_requests = sum(1 for r in results if r["response_time"] > 5.0)
        assert (
            slow_requests < concurrent_count * 0.2
        ), f"Too many slow requests: {slow_requests}/{concurrent_count}"
