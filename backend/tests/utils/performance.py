"""
Performance testing utilities
"""
import time
import asyncio
import psutil
import gc
from typing import Callable, Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
import statistics


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    memory_before_mb: float = 0
    memory_after_mb: float = 0
    memory_delta_mb: float = 0
    cpu_percent: float = 0
    iterations: int = 1
    errors: int = 0
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    avg_duration_ms: Optional[float] = None
    p95_duration_ms: Optional[float] = None
    p99_duration_ms: Optional[float] = None
    
    def calculate_percentiles(self, durations: List[float]):
        """Calculate percentile metrics"""
        if not durations:
            return
        
        sorted_durations = sorted(durations)
        self.min_duration_ms = sorted_durations[0]
        self.max_duration_ms = sorted_durations[-1]
        self.avg_duration_ms = statistics.mean(sorted_durations)
        
        if len(sorted_durations) >= 20:
            p95_index = int(len(sorted_durations) * 0.95)
            p99_index = int(len(sorted_durations) * 0.99)
            self.p95_duration_ms = sorted_durations[p95_index]
            self.p99_duration_ms = sorted_durations[p99_index]


class PerformanceMonitor:
    """Monitor performance metrics during tests"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.process = psutil.Process()
    
    @asynccontextmanager
    async def measure(self, operation: str):
        """Measure performance of an operation"""
        # Force garbage collection before measurement
        gc.collect()
        
        # Get initial metrics
        memory_before = self.process.memory_info().rss / 1024 / 1024  # MB
        cpu_before = self.process.cpu_percent(interval=0.1)
        
        metric = PerformanceMetrics(
            operation=operation,
            start_time=datetime.now(),
            memory_before_mb=memory_before
        )
        
        start_time = time.perf_counter()
        
        try:
            yield metric
        finally:
            # Calculate duration
            end_time = time.perf_counter()
            metric.end_time = datetime.now()
            metric.duration_ms = (end_time - start_time) * 1000
            
            # Get final metrics
            memory_after = self.process.memory_info().rss / 1024 / 1024  # MB
            cpu_after = self.process.cpu_percent(interval=0.1)
            
            metric.memory_after_mb = memory_after
            metric.memory_delta_mb = memory_after - memory_before
            metric.cpu_percent = (cpu_before + cpu_after) / 2
            
            self.metrics.append(metric)
    
    async def measure_concurrent(
        self, 
        operation: str,
        func: Callable,
        concurrency: int,
        iterations: int = 100,
        *args,
        **kwargs
    ) -> PerformanceMetrics:
        """Measure performance of concurrent operations"""
        durations = []
        errors = 0
        
        async def run_single():
            start = time.perf_counter()
            try:
                await func(*args, **kwargs)
                return (time.perf_counter() - start) * 1000
            except Exception:
                return None
        
        # Run iterations in batches
        for i in range(0, iterations, concurrency):
            batch_size = min(concurrency, iterations - i)
            tasks = [run_single() for _ in range(batch_size)]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                if result is None:
                    errors += 1
                else:
                    durations.append(result)
        
        metric = PerformanceMetrics(
            operation=f"{operation} (concurrent={concurrency})",
            start_time=datetime.now(),
            end_time=datetime.now(),
            iterations=iterations,
            errors=errors
        )
        
        if durations:
            metric.calculate_percentiles(durations)
            metric.duration_ms = metric.avg_duration_ms
        
        self.metrics.append(metric)
        return metric
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        if not self.metrics:
            return {"message": "No metrics collected"}
        
        total_duration = sum(m.duration_ms or 0 for m in self.metrics)
        total_memory = sum(m.memory_delta_mb for m in self.metrics)
        
        return {
            "total_operations": len(self.metrics),
            "total_duration_ms": round(total_duration, 2),
            "total_memory_delta_mb": round(total_memory, 2),
            "operations": [
                {
                    "name": m.operation,
                    "duration_ms": round(m.duration_ms or 0, 2),
                    "memory_delta_mb": round(m.memory_delta_mb, 2),
                    "cpu_percent": round(m.cpu_percent, 2),
                    "iterations": m.iterations,
                    "errors": m.errors,
                    "percentiles": {
                        "min": round(m.min_duration_ms, 2) if m.min_duration_ms else None,
                        "avg": round(m.avg_duration_ms, 2) if m.avg_duration_ms else None,
                        "p95": round(m.p95_duration_ms, 2) if m.p95_duration_ms else None,
                        "p99": round(m.p99_duration_ms, 2) if m.p99_duration_ms else None,
                        "max": round(m.max_duration_ms, 2) if m.max_duration_ms else None
                    }
                }
                for m in self.metrics
            ]
        }
    
    def assert_performance(
        self,
        operation: str,
        max_duration_ms: float = None,
        max_memory_mb: float = None,
        max_cpu_percent: float = None
    ):
        """Assert performance requirements are met"""
        metric = next((m for m in self.metrics if m.operation == operation), None)
        if not metric:
            raise AssertionError(f"No metrics found for operation: {operation}")
        
        if max_duration_ms and metric.duration_ms:
            assert metric.duration_ms <= max_duration_ms, \
                f"{operation} took {metric.duration_ms:.2f}ms, expected <= {max_duration_ms}ms"
        
        if max_memory_mb:
            assert abs(metric.memory_delta_mb) <= max_memory_mb, \
                f"{operation} used {metric.memory_delta_mb:.2f}MB, expected <= {max_memory_mb}MB"
        
        if max_cpu_percent:
            assert metric.cpu_percent <= max_cpu_percent, \
                f"{operation} used {metric.cpu_percent:.2f}% CPU, expected <= {max_cpu_percent}%"


class LoadTester:
    """Simple load testing utility"""
    
    def __init__(self):
        self.results = []
    
    async def run_load_test(
        self,
        func: Callable,
        duration_seconds: int = 60,
        rps: int = 10,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Run a load test with specified RPS"""
        interval = 1.0 / rps
        end_time = time.time() + duration_seconds
        
        successful = 0
        failed = 0
        durations = []
        
        while time.time() < end_time:
            start = time.perf_counter()
            
            try:
                await func(*args, **kwargs)
                successful += 1
                duration = (time.perf_counter() - start) * 1000
                durations.append(duration)
            except Exception as e:
                failed += 1
                print(f"Request failed: {e}")
            
            # Wait for next request
            elapsed = time.perf_counter() - start
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
        
        # Calculate statistics
        if durations:
            return {
                "duration_seconds": duration_seconds,
                "target_rps": rps,
                "actual_rps": (successful + failed) / duration_seconds,
                "successful_requests": successful,
                "failed_requests": failed,
                "error_rate": failed / (successful + failed) if (successful + failed) > 0 else 0,
                "latency": {
                    "min_ms": round(min(durations), 2),
                    "avg_ms": round(statistics.mean(durations), 2),
                    "median_ms": round(statistics.median(durations), 2),
                    "p95_ms": round(sorted(durations)[int(len(durations) * 0.95)], 2) if len(durations) > 20 else None,
                    "p99_ms": round(sorted(durations)[int(len(durations) * 0.99)], 2) if len(durations) > 100 else None,
                    "max_ms": round(max(durations), 2)
                }
            }
        else:
            return {
                "duration_seconds": duration_seconds,
                "target_rps": rps,
                "actual_rps": 0,
                "successful_requests": 0,
                "failed_requests": failed,
                "error_rate": 1.0,
                "latency": {}
            }


def benchmark(iterations: int = 100):
    """Decorator for benchmarking async functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            durations = []
            
            for _ in range(iterations):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                durations.append(duration)
            
            print(f"\nBenchmark results for {func.__name__}:")
            print(f"  Iterations: {iterations}")
            print(f"  Min: {min(durations):.2f}ms")
            print(f"  Avg: {statistics.mean(durations):.2f}ms")
            print(f"  Max: {max(durations):.2f}ms")
            if len(durations) >= 20:
                print(f"  P95: {sorted(durations)[int(len(durations) * 0.95)]:.2f}ms")
            
            return result
        
        return wrapper
    return decorator


async def stress_test_database(session, operation: Callable, records: int = 1000):
    """Stress test database operations"""
    monitor = PerformanceMonitor()
    
    async with monitor.measure(f"Create {records} records"):
        tasks = []
        for i in range(records):
            if i % 100 == 0:
                # Commit in batches
                await asyncio.gather(*tasks)
                tasks = []
            tasks.append(operation(session, i))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    return monitor.get_summary()