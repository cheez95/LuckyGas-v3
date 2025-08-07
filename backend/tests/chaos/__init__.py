"""
Chaos Engineering Test Suite for Lucky Gas v3

This test suite simulates various failure scenarios to ensure system resilience:

1. Pod / Service Failures - Tests recovery from service crashes and restarts
2. Network Chaos - Tests behavior under latency, timeouts, and partitions
3. Database Chaos - Tests handling of connection pool exhaustion and failures
4. External API Failures - Tests resilience when third - party services fail
5. Resource Exhaustion - Tests behavior under memory, CPU, and disk pressure

These tests should be run in a controlled environment, not in production.

Usage:
    pytest tests / chaos -m chaos  # Run all chaos tests
    pytest tests / chaos / test_pod_failure.py  # Run specific chaos test
    pytest tests / chaos -k "network" -m chaos  # Run network - related chaos tests
"""

# Chaos test markers and configuration
CHAOS_TEST_MARKERS = {
    "chaos": "Chaos engineering tests that simulate failures",
    "pod_failure": "Tests for pod / service termination scenarios",
    "network_chaos": "Tests for network latency and failures",
    "database_chaos": "Tests for database connection issues",
    "external_api": "Tests for third - party service failures",
    "resource_exhaustion": "Tests for resource constraint scenarios",
}

# Chaos test configuration
CHAOS_CONFIG = {
    "pod_failure": {
        "max_recovery_time": 30,  # seconds
        "availability_sla": 95,  # percentage
    },
    "network": {
        "latency_thresholds": {
            "low": 100,  # ms
            "medium": 500,  # ms
            "high": 1000,  # ms
        },
        "timeout_thresholds": {
            "client": 1.0,  # seconds
            "api": 2.0,
            "service": 3.0,
            "database": 5.0,
        },
    },
    "database": {
        "pool_size": 10,
        "max_overflow": 5,
        "pool_timeout": 30,
        "query_timeout": 5,
    },
    "external_api": {
        "retry_attempts": 3,
        "backoff_factor": 2,
        "circuit_breaker_threshold": 5,
        "circuit_breaker_timeout": 60,
    },
    "resource": {
        "memory_limit_mb": 512,
        "cpu_threshold_percent": 80,
        "disk_threshold_percent": 90,
        "fd_soft_limit": 1024,
        "thread_limit": 100,
    },
}

# Export configuration
__all__ = ["CHAOS_TEST_MARKERS", "CHAOS_CONFIG"]
