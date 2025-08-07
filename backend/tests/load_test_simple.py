#!/usr / bin / env python3
"""Simple load test for production readiness validation."""
import asyncio
import statistics
import sys
import time
from typing import List

import aiohttp


async def make_request(session: aiohttp.ClientSession, url: str) -> tuple[float, int]:
    """Make a single request and return latency and status code."""
    start = time.time()
    try:
        async with session.get(url) as response:
            await response.text()
            return time.time() - start, response.status
    except Exception as e:
        print(f"Request failed: {e}")
        return time.time() - start, 500


async def run_load_test(
    url: str, concurrent_users: int = 100, requests_per_user: int = 10
):
    """Run load test with specified concurrent users."""
    print(
        f"Starting load test: {concurrent_users} concurrent users, {requests_per_user} requests each"
    )

    latencies: List[float] = []
    errors = 0

    async with aiohttp.ClientSession() as session:
        # Warmup
        print("Warming up...")
        await make_request(session, url)

        # Load test
        print("Running load test...")
        start_time = time.time()

        tasks = []
        for _ in range(concurrent_users):
            for _ in range(requests_per_user):
                tasks.append(make_request(session, url))

        results = await asyncio.gather(*tasks)

        for latency, status in results:
            latencies.append(latency)
            if status >= 400:
                errors += 1

        total_time = time.time() - start_time

    # Calculate metrics
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.5)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print("\n=== Load Test Results ===")
    print(f"Total requests: {len(latencies)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Requests / sec: {len(latencies) / total_time:.2f}")
    print(f"Errors: {errors} ({errors / len(latencies) * 100:.2f}%)")
    print("\nLatency metrics:")
    print(f"  p50: {p50 * 1000:.2f}ms")
    print(f"  p95: {p95 * 1000:.2f}ms")
    print(f"  p99: {p99 * 1000:.2f}ms")
    print(f"  avg: {statistics.mean(latencies) * 1000:.2f}ms")

    # Check if p95 < 200ms
    if p95 * 1000 < 200:
        print("\n✅ PASS: p95 latency < 200ms")
    else:
        print("\n❌ FAIL: p95 latency >= 200ms")

    return p95 * 1000 < 200, errors / len(latencies) < 0.01


if __name__ == "__main__":
    url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "http://localhost:8000 / api / v1 / health"
    )
    asyncio.run(run_load_test(url))
