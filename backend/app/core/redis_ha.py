"""High Availability Redis Configuration.

This module provides Redis connection management with support for:
- Redis Sentinel for automatic failover
- Connection pooling
- Health checking
- Circuit breaker pattern
- Performance monitoring
"""

import asyncio
import logging
import json
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio.sentinel import Sentinel
from redis.exceptions import RedisError, ConnectionError, TimeoutError
from functools import wraps
import hashlib

from .config import settings

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern for Redis operations."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
    
    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def can_attempt(self) -> bool:
        """Check if we can attempt an operation."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if time_since_failure > self.recovery_timeout:
                    self.state = "half-open"
                    logger.info("Circuit breaker moved to half-open state")
                    return True
            return False
        
        # half-open state
        return True


class RedisManager:
    """Manages Redis connections with high availability support."""
    
    def __init__(self):
        self.sentinel: Optional[Sentinel] = None
        self.direct_client: Optional[redis.Redis] = None
        self.read_clients: List[redis.Redis] = []
        self.circuit_breaker = CircuitBreaker()
        self._health_check_task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, Any] = {
            "operations": {"get": 0, "set": 0, "delete": 0, "other": 0},
            "errors": {"connection": 0, "timeout": 0, "other": 0},
            "latency": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "last_health_check": None
        }
    
    async def initialize(self):
        """Initialize Redis connections."""
        logger.info("Initializing Redis connections...")
        
        # Check if Sentinel is configured
        sentinel_hosts = self._get_sentinel_hosts()
        
        if sentinel_hosts:
            await self._init_sentinel(sentinel_hosts)
        else:
            await self._init_direct_connection()
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Redis initialization complete")
    
    def _get_sentinel_hosts(self) -> List[tuple]:
        """Get Sentinel hosts from configuration."""
        sentinel_urls = settings.get("REDIS_SENTINELS", "").split(",")
        if not sentinel_urls or sentinel_urls == ['']:
            return []
        
        hosts = []
        for url in sentinel_urls:
            if ':' in url:
                host, port = url.strip().split(':')
                hosts.append((host, int(port)))
            else:
                hosts.append((url.strip(), 26379))  # Default Sentinel port
        
        return hosts
    
    async def _init_sentinel(self, sentinel_hosts: List[tuple]):
        """Initialize Redis with Sentinel support."""
        try:
            # Configure Sentinel
            self.sentinel = Sentinel(
                sentinel_hosts,
                socket_connect_timeout=5,
                socket_timeout=5,
                password=settings.get("REDIS_PASSWORD"),
                sentinel_kwargs={
                    "password": settings.get("SENTINEL_PASSWORD"),
                } if settings.get("SENTINEL_PASSWORD") else {}
            )
            
            # Get master for writes
            master_name = settings.get("REDIS_MASTER_NAME", "luckygas-master")
            self.direct_client = await self.sentinel.master_for(
                master_name,
                decode_responses=True,
                health_check_interval=30,
                max_connections=50,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )
            
            # Get slaves for reads
            slaves = await self.sentinel.slave_for(
                master_name,
                decode_responses=True,
                health_check_interval=30,
                max_connections=25,
                retry_on_timeout=True
            )
            if slaves:
                self.read_clients = [slaves]
            
            # Test connection
            await self.direct_client.ping()
            logger.info("Redis Sentinel connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis Sentinel: {e}")
            # Fall back to direct connection
            await self._init_direct_connection()
    
    async def _init_direct_connection(self):
        """Initialize direct Redis connection."""
        try:
            redis_url = settings.REDIS_URL
            
            # Parse URL to add password if needed
            if settings.get("REDIS_PASSWORD") and "@" not in redis_url:
                # Insert password into URL
                redis_url = redis_url.replace("redis://", f"redis://:{settings.get('REDIS_PASSWORD')}@")
            
            self.direct_client = await redis.from_url(
                redis_url,
                decode_responses=True,
                health_check_interval=30,
                max_connections=50,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )
            
            # Test connection
            await self.direct_client.ping()
            logger.info("Direct Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize direct Redis connection: {e}")
            raise
    
    def _with_circuit_breaker(func):
        """Decorator to apply circuit breaker pattern."""
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not self.circuit_breaker.can_attempt():
                raise ConnectionError("Circuit breaker is open")
            
            try:
                result = await func(self, *args, **kwargs)
                self.circuit_breaker.record_success()
                return result
            except (ConnectionError, TimeoutError) as e:
                self.circuit_breaker.record_failure()
                self._metrics["errors"]["connection"] += 1
                raise
            except Exception as e:
                self.circuit_breaker.record_failure()
                self._metrics["errors"]["other"] += 1
                raise
        
        return wrapper
    
    def _track_metrics(operation: str):
        """Decorator to track operation metrics."""
        def decorator(func):
            @wraps(func)
            async def wrapper(self, *args, **kwargs):
                start_time = datetime.utcnow()
                try:
                    result = await func(self, *args, **kwargs)
                    
                    # Track latency
                    latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                    self._metrics["latency"].append(latency)
                    self._metrics["latency"] = self._metrics["latency"][-1000:]  # Keep last 1000
                    
                    # Track operation
                    if operation in self._metrics["operations"]:
                        self._metrics["operations"][operation] += 1
                    else:
                        self._metrics["operations"]["other"] += 1
                    
                    return result
                except Exception:
                    raise
            
            return wrapper
        return decorator
    
    @_with_circuit_breaker
    @_track_metrics("get")
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        client = self._get_read_client()
        value = await client.get(key)
        
        if value is None:
            self._metrics["cache_misses"] += 1
        else:
            self._metrics["cache_hits"] += 1
        
        return value
    
    @_with_circuit_breaker
    @_track_metrics("set")
    async def set(self, key: str, value: Union[str, dict, list], 
                  expire: Optional[int] = None) -> bool:
        """Set value in Redis."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        return await self.direct_client.set(key, value, ex=expire)
    
    @_with_circuit_breaker
    @_track_metrics("delete")
    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis."""
        return await self.direct_client.delete(*keys)
    
    @_with_circuit_breaker
    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        """Get multiple values."""
        client = self._get_read_client()
        return await client.mget(keys)
    
    @_with_circuit_breaker
    async def mset(self, mapping: Dict[str, Union[str, dict, list]]) -> bool:
        """Set multiple values."""
        processed_mapping = {}
        for key, value in mapping.items():
            if isinstance(value, (dict, list)):
                processed_mapping[key] = json.dumps(value)
            else:
                processed_mapping[key] = value
        
        return await self.direct_client.mset(processed_mapping)
    
    @_with_circuit_breaker
    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        client = self._get_read_client()
        return await client.exists(*keys)
    
    @_with_circuit_breaker
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        return await self.direct_client.expire(key, seconds)
    
    @_with_circuit_breaker
    async def ttl(self, key: str) -> int:
        """Get TTL of key."""
        client = self._get_read_client()
        return await client.ttl(key)
    
    # Hash operations
    @_with_circuit_breaker
    async def hset(self, name: str, key: str, value: Union[str, dict]) -> int:
        """Set hash field."""
        if isinstance(value, dict):
            value = json.dumps(value)
        return await self.direct_client.hset(name, key, value)
    
    @_with_circuit_breaker
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field."""
        client = self._get_read_client()
        return await client.hget(name, key)
    
    @_with_circuit_breaker
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        client = self._get_read_client()
        return await client.hgetall(name)
    
    # List operations
    @_with_circuit_breaker
    async def lpush(self, key: str, *values: Union[str, dict]) -> int:
        """Push values to list."""
        processed_values = []
        for value in values:
            if isinstance(value, dict):
                processed_values.append(json.dumps(value))
            else:
                processed_values.append(value)
        
        return await self.direct_client.lpush(key, *processed_values)
    
    @_with_circuit_breaker
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range from list."""
        client = self._get_read_client()
        return await client.lrange(key, start, end)
    
    # Set operations
    @_with_circuit_breaker
    async def sadd(self, key: str, *values: str) -> int:
        """Add values to set."""
        return await self.direct_client.sadd(key, *values)
    
    @_with_circuit_breaker
    async def smembers(self, key: str) -> set:
        """Get all set members."""
        client = self._get_read_client()
        return await client.smembers(key)
    
    # Pub/Sub operations
    async def publish(self, channel: str, message: Union[str, dict]) -> int:
        """Publish message to channel."""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        return await self.direct_client.publish(channel, message)
    
    async def subscribe(self, *channels: str):
        """Subscribe to channels."""
        pubsub = self.direct_client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub
    
    # Geo operations for delivery tracking
    @_with_circuit_breaker
    async def geoadd(self, key: str, longitude: float, latitude: float, 
                     member: str) -> int:
        """Add geo location."""
        return await self.direct_client.geoadd(key, (longitude, latitude, member))
    
    @_with_circuit_breaker
    async def georadius(self, key: str, longitude: float, latitude: float,
                       radius: float, unit: str = "km") -> List[str]:
        """Get members within radius."""
        client = self._get_read_client()
        return await client.georadius(key, longitude, latitude, radius, unit)
    
    def _get_read_client(self) -> redis.Redis:
        """Get client for read operations."""
        if self.read_clients:
            # Simple round-robin
            return self.read_clients[0]
        return self.direct_client
    
    async def _health_check_loop(self):
        """Periodically check Redis health."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _check_health(self):
        """Check Redis connection health."""
        self._metrics["last_health_check"] = datetime.utcnow()
        
        try:
            # Check primary
            start_time = datetime.utcnow()
            await self.direct_client.ping()
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Check memory usage
            info = await self.direct_client.info("memory")
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)
            
            if max_memory > 0:
                memory_usage_percent = (used_memory / max_memory) * 100
                if memory_usage_percent > 90:
                    logger.warning(f"Redis memory usage high: {memory_usage_percent:.1f}%")
            
            # Check replication if using Sentinel
            if self.sentinel:
                master_info = await self.direct_client.info("replication")
                connected_slaves = master_info.get("connected_slaves", 0)
                logger.debug(f"Redis master has {connected_slaves} connected slaves")
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            self._metrics["errors"]["connection"] += 1
    
    async def close(self):
        """Close Redis connections."""
        logger.info("Closing Redis connections...")
        
        # Cancel health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close connections
        if self.direct_client:
            await self.direct_client.close()
        
        for client in self.read_clients:
            await client.close()
        
        logger.info("Redis connections closed")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Redis metrics."""
        total_ops = sum(self._metrics["operations"].values())
        hit_rate = 0
        if self._metrics["cache_hits"] + self._metrics["cache_misses"] > 0:
            hit_rate = self._metrics["cache_hits"] / (
                self._metrics["cache_hits"] + self._metrics["cache_misses"]
            ) * 100
        
        avg_latency = 0
        if self._metrics["latency"]:
            avg_latency = sum(self._metrics["latency"]) / len(self._metrics["latency"])
        
        return {
            **self._metrics,
            "total_operations": total_ops,
            "cache_hit_rate": f"{hit_rate:.2f}%",
            "average_latency_ms": f"{avg_latency:.2f}",
            "circuit_breaker_state": self.circuit_breaker.state
        }
    
    # Cache helper methods
    async def cache_get(self, key: str, default=None):
        """Get cached value with default."""
        value = await self.get(key)
        if value is None:
            return default
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    async def cache_set(self, key: str, value: Any, expire: int = 3600):
        """Set cached value with expiration."""
        return await self.set(key, value, expire)
    
    async def cache_delete_pattern(self, pattern: str):
        """Delete all keys matching pattern."""
        cursor = 0
        deleted = 0
        
        while True:
            cursor, keys = await self.direct_client.scan(
                cursor, match=pattern, count=100
            )
            
            if keys:
                deleted += await self.delete(*keys)
            
            if cursor == 0:
                break
        
        return deleted
    
    def make_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        key_parts = ["luckygas"]
        for arg in args:
            if isinstance(arg, (dict, list)):
                # Hash complex objects
                key_parts.append(hashlib.md5(
                    json.dumps(arg, sort_keys=True).encode()
                ).hexdigest()[:8])
            else:
                key_parts.append(str(arg))
        
        return ":".join(key_parts)


# Global Redis manager instance
redis_manager = RedisManager()


# Dependency for FastAPI
async def get_redis() -> RedisManager:
    """FastAPI dependency for Redis."""
    return redis_manager