import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import redis.asyncio as redis
from enum import Enum
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


class QueuePriority(str, Enum):
    """Message queue priority levels"""
    HIGH = "high"       # Critical messages (e.g., emergency alerts)
    NORMAL = "normal"   # Regular messages (e.g., status updates)
    LOW = "low"        # Non-critical messages (e.g., analytics)


class MessageStatus(str, Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


class Message:
    """Represents a queued message"""
    def __init__(
        self,
        message_id: str,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        priority: QueuePriority = QueuePriority.NORMAL,
        max_retries: int = 3,
        ttl_seconds: int = 3600,  # 1 hour default
        target_user_id: Optional[str] = None,
        target_role: Optional[str] = None
    ):
        self.message_id = message_id
        self.channel = channel
        self.event_type = event_type
        self.data = data
        self.priority = priority
        self.max_retries = max_retries
        self.ttl_seconds = ttl_seconds
        self.target_user_id = target_user_id
        self.target_role = target_role
        self.created_at = datetime.now()
        self.retry_count = 0
        self.status = MessageStatus.PENDING
        self.last_attempt_at: Optional[datetime] = None
        self.delivered_at: Optional[datetime] = None
        
    def is_expired(self) -> bool:
        """Check if message has exceeded TTL"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def can_retry(self) -> bool:
        """Check if message can be retried"""
        return self.retry_count < self.max_retries and not self.is_expired()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for Redis storage"""
        return {
            "message_id": self.message_id,
            "channel": self.channel,
            "event_type": self.event_type,
            "data": self.data,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "ttl_seconds": self.ttl_seconds,
            "target_user_id": self.target_user_id,
            "target_role": self.target_role,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
            "status": self.status,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary"""
        msg = cls(
            message_id=data["message_id"],
            channel=data["channel"],
            event_type=data["event_type"],
            data=data["data"],
            priority=data["priority"],
            max_retries=data["max_retries"],
            ttl_seconds=data["ttl_seconds"],
            target_user_id=data.get("target_user_id"),
            target_role=data.get("target_role")
        )
        msg.created_at = datetime.fromisoformat(data["created_at"])
        msg.retry_count = data["retry_count"]
        msg.status = data["status"]
        if data.get("last_attempt_at"):
            msg.last_attempt_at = datetime.fromisoformat(data["last_attempt_at"])
        if data.get("delivered_at"):
            msg.delivered_at = datetime.fromisoformat(data["delivered_at"])
        return msg


class MessageQueueService:
    """Service for reliable message delivery with retry logic"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.delivery_callback: Optional[Callable] = None
        self._background_tasks = set()
        self._retry_intervals = [5, 15, 60]  # Retry after 5s, 15s, 60s
        self._processing = False
        
    async def initialize(self, delivery_callback: Callable):
        """Initialize the message queue service"""
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            self.delivery_callback = delivery_callback
            
            # Start background processors
            await self._start_processors()
            
            logger.info("Message queue service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize message queue: {e}")
            raise
    
    async def _start_processors(self):
        """Start background message processors"""
        # Start processor for each priority level
        for priority in QueuePriority:
            task = asyncio.create_task(self._process_queue(priority))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        
        # Start retry processor
        retry_task = asyncio.create_task(self._process_retries())
        self._background_tasks.add(retry_task)
        retry_task.add_done_callback(self._background_tasks.discard)
        
        # Start cleanup processor
        cleanup_task = asyncio.create_task(self._cleanup_expired())
        self._background_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self._background_tasks.discard)
    
    async def enqueue(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        priority: QueuePriority = QueuePriority.NORMAL,
        max_retries: int = 3,
        ttl_seconds: int = 3600,
        target_user_id: Optional[str] = None,
        target_role: Optional[str] = None
    ) -> str:
        """Add message to queue"""
        message_id = str(uuid.uuid4())
        
        message = Message(
            message_id=message_id,
            channel=channel,
            event_type=event_type,
            data=data,
            priority=priority,
            max_retries=max_retries,
            ttl_seconds=ttl_seconds,
            target_user_id=target_user_id,
            target_role=target_role
        )
        
        # Store message in Redis
        queue_key = f"message_queue:{priority}"
        message_key = f"message:{message_id}"
        
        await self.redis_client.setex(
            message_key,
            ttl_seconds,
            json.dumps(message.to_dict())
        )
        
        # Add to priority queue
        await self.redis_client.rpush(queue_key, message_id)
        
        logger.info(f"Enqueued message {message_id} with priority {priority}")
        
        return message_id
    
    async def _process_queue(self, priority: QueuePriority):
        """Process messages from a specific priority queue"""
        queue_key = f"message_queue:{priority}"
        
        while True:
            try:
                # Get message from queue (blocking pop with 1 second timeout)
                result = await self.redis_client.blpop(queue_key, timeout=1)
                
                if result:
                    _, message_id = result
                    await self._process_message(message_id)
                
            except Exception as e:
                logger.error(f"Error processing {priority} queue: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_message(self, message_id: str):
        """Process a single message"""
        try:
            # Get message from Redis
            message_key = f"message:{message_id}"
            message_data = await self.redis_client.get(message_key)
            
            if not message_data:
                logger.warning(f"Message {message_id} not found")
                return
            
            message = Message.from_dict(json.loads(message_data))
            
            # Check if expired
            if message.is_expired():
                message.status = MessageStatus.EXPIRED
                await self._update_message(message)
                logger.warning(f"Message {message_id} expired")
                return
            
            # Attempt delivery
            message.last_attempt_at = datetime.now()
            message.status = MessageStatus.RETRYING
            
            try:
                # Call delivery callback
                await self.delivery_callback(
                    channel=message.channel,
                    event_type=message.event_type,
                    data=message.data,
                    target_user_id=message.target_user_id,
                    target_role=message.target_role
                )
                
                # Mark as delivered
                message.status = MessageStatus.DELIVERED
                message.delivered_at = datetime.now()
                await self._update_message(message)
                
                logger.info(f"Message {message_id} delivered successfully")
                
            except Exception as e:
                logger.error(f"Failed to deliver message {message_id}: {e}")
                
                # Handle retry
                message.retry_count += 1
                
                if message.can_retry():
                    # Schedule retry
                    retry_delay = self._retry_intervals[
                        min(message.retry_count - 1, len(self._retry_intervals) - 1)
                    ]
                    
                    retry_key = f"message_retry:{message_id}"
                    await self.redis_client.setex(
                        retry_key,
                        retry_delay,
                        message_id
                    )
                    
                    message.status = MessageStatus.RETRYING
                    logger.info(f"Message {message_id} scheduled for retry #{message.retry_count} in {retry_delay}s")
                    
                else:
                    # Max retries exceeded or expired
                    message.status = MessageStatus.FAILED
                    logger.error(f"Message {message_id} failed after {message.retry_count} retries")
                
                await self._update_message(message)
                
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
    
    async def _process_retries(self):
        """Process messages scheduled for retry"""
        while True:
            try:
                # Scan for retry keys
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor,
                        match="message_retry:*",
                        count=100
                    )
                    
                    for key in keys:
                        # Check if retry delay has passed
                        ttl = await self.redis_client.ttl(key)
                        if ttl <= 0:
                            # Get message ID and requeue
                            message_id = key.split(":")[-1]
                            
                            # Get message details
                            message_key = f"message:{message_id}"
                            message_data = await self.redis_client.get(message_key)
                            
                            if message_data:
                                message = Message.from_dict(json.loads(message_data))
                                
                                # Re-add to appropriate queue
                                queue_key = f"message_queue:{message.priority}"
                                await self.redis_client.rpush(queue_key, message_id)
                                
                                # Remove retry key
                                await self.redis_client.delete(key)
                                
                                logger.info(f"Message {message_id} requeued for retry")
                    
                    if cursor == 0:
                        break
                
                # Wait before next scan
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing retries: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_expired(self):
        """Clean up expired messages"""
        while True:
            try:
                # Run cleanup every minute
                await asyncio.sleep(60)
                
                # Scan for message keys
                cursor = 0
                cleaned = 0
                
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor,
                        match="message:*",
                        count=100
                    )
                    
                    for key in keys:
                        message_data = await self.redis_client.get(key)
                        if message_data:
                            message = Message.from_dict(json.loads(message_data))
                            
                            if message.is_expired() and message.status != MessageStatus.DELIVERED:
                                await self.redis_client.delete(key)
                                cleaned += 1
                    
                    if cursor == 0:
                        break
                
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} expired messages")
                    
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    async def _update_message(self, message: Message):
        """Update message in Redis"""
        message_key = f"message:{message.message_id}"
        await self.redis_client.setex(
            message_key,
            message.ttl_seconds,
            json.dumps(message.to_dict())
        )
    
    async def get_message_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific message"""
        message_key = f"message:{message_id}"
        message_data = await self.redis_client.get(message_key)
        
        if message_data:
            return json.loads(message_data)
        return None
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = {
            "queues": {},
            "total_pending": 0,
            "total_delivered": 0,
            "total_failed": 0
        }
        
        # Get queue lengths
        for priority in QueuePriority:
            queue_key = f"message_queue:{priority}"
            length = await self.redis_client.llen(queue_key)
            stats["queues"][priority] = length
            stats["total_pending"] += length
        
        # Get message counts by status
        # This is a simplified version - in production, you'd want to maintain counters
        
        return stats
    
    async def shutdown(self):
        """Shutdown the message queue service"""
        self._processing = False
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Message queue service shut down")


# Singleton instance
message_queue = MessageQueueService()