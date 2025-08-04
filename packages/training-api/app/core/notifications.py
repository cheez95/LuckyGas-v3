import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import json
import aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.training import Achievement, UserAchievement, Course, Module
from app.core.config import settings
from app.core.websocket import manager
from app.services.email_service import EmailService
from app.services.sms_service import SMSService

class NotificationService:
    """Service for handling all types of notifications."""
    
    def __init__(self):
        self.redis = None
        self.email_service = EmailService()
        self.sms_service = SMSService()
    
    async def initialize(self):
        """Initialize Redis connection for pub/sub."""
        self.redis = await aioredis.create_redis_pool(settings.REDIS_URL)
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
    
    async def send_achievement_notification(
        self,
        user: User,
        achievement: Achievement,
        user_achievement: UserAchievement
    ):
        """Send notification when user earns an achievement."""
        notification = {
            "type": "achievement",
            "user_id": str(user.id),
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "achievement_id": str(achievement.achievement_id),
                "name": achievement.name_zh,
                "description": achievement.description_zh,
                "icon": achievement.icon,
                "points": achievement.points_value,
                "rarity": achievement.rarity,
                "earned_at": user_achievement.earned_at.isoformat()
            }
        }
        
        # Send real-time notification via WebSocket
        await self._send_websocket_notification(user.id, notification)
        
        # Store in notification history
        await self._store_notification(user.id, notification)
        
        # Send push notification if enabled
        if user.push_notifications_enabled:
            await self._send_push_notification(
                user,
                f"🎉 恭喜獲得成就：{achievement.name_zh}",
                achievement.description_zh
            )
        
        # Send email if it's a rare achievement
        if achievement.rarity in ["epic", "legendary"] and user.email_notifications_enabled:
            await self._send_achievement_email(user, achievement)
    
    async def send_course_reminder(
        self,
        user: User,
        course: Course,
        reminder_type: str = "deadline"
    ):
        """Send course reminder notification."""
        notification = {
            "type": "course_reminder",
            "user_id": str(user.id),
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "course_id": str(course.course_id),
                "title": course.title_zh,
                "reminder_type": reminder_type,
                "message": self._get_reminder_message(reminder_type, course)
            }
        }
        
        # Send real-time notification
        await self._send_websocket_notification(user.id, notification)
        
        # Store notification
        await self._store_notification(user.id, notification)
        
        # Send SMS for important reminders
        if reminder_type in ["deadline", "overdue"] and user.sms_notifications_enabled:
            await self._send_reminder_sms(user, course, reminder_type)
    
    async def send_module_completion_notification(
        self,
        user: User,
        module: Module,
        course: Course,
        points_earned: int
    ):
        """Send notification when user completes a module."""
        notification = {
            "type": "module_completion",
            "user_id": str(user.id),
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "module_id": str(module.module_id),
                "module_title": module.title_zh,
                "course_id": str(course.course_id),
                "course_title": course.title_zh,
                "points_earned": points_earned
            }
        }
        
        # Send real-time notification
        await self._send_websocket_notification(user.id, notification)
        
        # Store notification
        await self._store_notification(user.id, notification)
    
    async def send_leaderboard_update(
        self,
        user: User,
        old_rank: int,
        new_rank: int,
        leaderboard_type: str = "overall"
    ):
        """Send notification when user's leaderboard position changes."""
        if new_rank >= old_rank:  # Only notify on rank improvement
            return
        
        notification = {
            "type": "leaderboard_update",
            "user_id": str(user.id),
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "old_rank": old_rank,
                "new_rank": new_rank,
                "leaderboard_type": leaderboard_type,
                "message": f"恭喜！您的{self._get_leaderboard_name(leaderboard_type)}排名上升到第 {new_rank} 名！"
            }
        }
        
        # Send real-time notification
        await self._send_websocket_notification(user.id, notification)
        
        # Store notification
        await self._store_notification(user.id, notification)
    
    async def broadcast_announcement(
        self,
        title: str,
        message: str,
        target_departments: Optional[List[str]] = None,
        priority: str = "normal"
    ):
        """Broadcast announcement to multiple users."""
        announcement = {
            "type": "announcement",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "title": title,
                "message": message,
                "priority": priority
            }
        }
        
        # Broadcast via WebSocket to all connected users
        if target_departments:
            await manager.broadcast_to_departments(announcement, target_departments)
        else:
            await manager.broadcast(announcement)
        
        # Also publish to Redis for users not currently connected
        if self.redis:
            channel = "announcements:all" if not target_departments else f"announcements:{':'.join(target_departments)}"
            await self.redis.publish(channel, json.dumps(announcement))
    
    async def _send_websocket_notification(self, user_id: str, notification: dict):
        """Send notification via WebSocket to specific user."""
        await manager.send_personal_message(notification, user_id)
    
    async def _store_notification(self, user_id: str, notification: dict):
        """Store notification in Redis for history."""
        if self.redis:
            key = f"notifications:{user_id}"
            # Store notification with expiry (30 days)
            await self.redis.lpush(key, json.dumps(notification))
            await self.redis.ltrim(key, 0, 99)  # Keep last 100 notifications
            await self.redis.expire(key, 30 * 24 * 60 * 60)  # 30 days
    
    async def _send_push_notification(self, user: User, title: str, body: str):
        """Send push notification to user's devices."""
        # This would integrate with Firebase Cloud Messaging or similar
        # For now, just log it
        print(f"Push notification to {user.name}: {title} - {body}")
    
    async def _send_achievement_email(self, user: User, achievement: Achievement):
        """Send email notification for achievement."""
        subject = f"🎉 恭喜獲得成就：{achievement.name_zh}"
        
        html_content = f"""
        <h2>恭喜您獲得新成就！</h2>
        <div style="text-align: center; padding: 20px;">
            <div style="font-size: 48px;">{achievement.icon}</div>
            <h3>{achievement.name_zh}</h3>
            <p>{achievement.description_zh}</p>
            <p><strong>獲得點數：{achievement.points_value} 點</strong></p>
        </div>
        <p>繼續努力，解鎖更多成就！</p>
        """
        
        await self.email_service.send_email(
            to=user.email,
            subject=subject,
            html_content=html_content
        )
    
    async def _send_reminder_sms(self, user: User, course: Course, reminder_type: str):
        """Send SMS reminder for course."""
        message = self._get_reminder_message(reminder_type, course)
        await self.sms_service.send_sms(user.phone, message)
    
    def _get_reminder_message(self, reminder_type: str, course: Course) -> str:
        """Get reminder message based on type."""
        messages = {
            "deadline": f"提醒：課程「{course.title_zh}」即將到期，請盡快完成學習。",
            "overdue": f"重要：課程「{course.title_zh}」已逾期，請立即完成學習。",
            "new_module": f"新模組已開放：{course.title_zh}，快來學習吧！",
            "incomplete": f"您還有未完成的課程「{course.title_zh}」，繼續加油！"
        }
        return messages.get(reminder_type, f"課程提醒：{course.title_zh}")
    
    def _get_leaderboard_name(self, leaderboard_type: str) -> str:
        """Get leaderboard display name."""
        names = {
            "overall": "總排行榜",
            "monthly": "月排行榜",
            "weekly": "週排行榜",
            "department": "部門排行榜"
        }
        return names.get(leaderboard_type, "排行榜")
    
    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[dict]:
        """Get user's notification history."""
        if not self.redis:
            return []
        
        key = f"notifications:{user_id}"
        notifications = await self.redis.lrange(key, offset, offset + limit - 1)
        
        return [json.loads(n) for n in notifications]
    
    async def mark_notifications_read(self, user_id: str, notification_ids: List[str]):
        """Mark notifications as read."""
        # This would update the notification status in the database
        # For now, we're using Redis which doesn't track read status
        pass


# Global notification service instance
notification_service = NotificationService()


# Helper functions for common notifications
async def send_achievement_notification(user: User, achievement: Achievement, user_achievement: UserAchievement):
    """Helper function to send achievement notification."""
    await notification_service.send_achievement_notification(user, achievement, user_achievement)


async def send_course_reminder(user: User, course: Course, reminder_type: str = "deadline"):
    """Helper function to send course reminder."""
    await notification_service.send_course_reminder(user, course, reminder_type)


async def broadcast_announcement(title: str, message: str, target_departments: Optional[List[str]] = None, priority: str = "normal"):
    """Helper function to broadcast announcement."""
    await notification_service.broadcast_announcement(title, message, target_departments, priority)