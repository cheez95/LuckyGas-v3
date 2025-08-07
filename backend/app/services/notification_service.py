import asyncio
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

# from app.services.message_queue_service import message_queue, QueuePriority  # Removed during compaction

logger = logging.getLogger(__name__)


class NotificationType:
    """Notification types"""

    ORDER_CONFIRMATION = "order_confirmation"
    DELIVERY_ON_WAY = "delivery_on_way"
    DELIVERY_ARRIVED = "delivery_arrived"
    DELIVERY_COMPLETED = "delivery_completed"
    ORDER_CANCELLED = "order_cancelled"
    PAYMENT_REMINDER = "payment_reminder"
    URGENT_NOTIFICATION = "urgent_notification"
    SYSTEM_ALERT = "system_alert"


class NotificationChannel:
    """Notification channels"""

    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationService:
    """Service for sending notifications via SMS, Email, and other channels"""

    def __init__(self):
        # Use default values for missing settings in development
        self.sms_provider_url = getattr(
            settings, "SMS_PROVIDER_URL", "http://localhost:8001 / mock - sms"
        )
        self.sms_api_key = getattr(settings, "SMS_API_KEY", "dev - sms - key")
        self.sms_sender_id = getattr(settings, "SMS_SENDER_ID", "LuckyGas")

        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM or "noreply@luckygas.com.tw"

        # Template engine for email
        self.template_env = Environment(
            loader=FileSystemLoader("app / templates / email"),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # SMS templates (Traditional Chinese)
        self.sms_templates = {
            NotificationType.ORDER_CONFIRMATION: "【幸福氣】您的訂單 {order_number} 已確認，預計配送時間：{delivery_time}",
            NotificationType.DELIVERY_ON_WAY: "【幸福氣】您的瓦斯正在配送中，司機 {driver_name} 預計 {eta} 分鐘後到達",
            NotificationType.DELIVERY_ARRIVED: "【幸福氣】配送員已到達您的地址，請準備接收瓦斯",
            NotificationType.DELIVERY_COMPLETED: "【幸福氣】您的訂單 {order_number} 已送達完成，感謝您的訂購！",
            NotificationType.ORDER_CANCELLED: "【幸福氣】您的訂單 {order_number} 已取消，如有疑問請聯繫客服",
            NotificationType.PAYMENT_REMINDER: "【幸福氣】提醒您，訂單 {order_number} 尚有 NT${amount} 待付款",
            NotificationType.URGENT_NOTIFICATION: "【幸福氣】緊急通知：{message}",
            NotificationType.SYSTEM_ALERT: "【幸福氣】系統通知：{message}",
        }

    async def send_notification(
        self,
        recipient: str,
        notification_type: str,
        channel: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send notification via specified channel"""

        
        # Direct send
        try:
            if channel == NotificationChannel.SMS:
                return await self._send_sms(recipient, notification_type, data)
            elif channel == NotificationChannel.EMAIL:
                return await self._send_email(recipient, notification_type, data)
            elif channel == NotificationChannel.PUSH:
                return await self._send_push_notification(
                    recipient, notification_type, data
                )
            elif channel == NotificationChannel.IN_APP:
                return await self._send_in_app_notification(
                    recipient, notification_type, data
                )
            else:
                raise ValueError(f"Unknown notification channel: {channel}")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

            # Direct send failed
            raise

            raise

    async def _send_sms(
        self, phone_number: str, notification_type: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send SMS notification using enhanced SMS service"""
        from app.services.sms_service import enhanced_sms_service

        # Get template and format message
        template = self.sms_templates.get(notification_type, "")
        message = template.format(**data)

        # Use enhanced SMS service
        result = await enhanced_sms_service.send_sms(
            phone=phone_number,
            message=message,
            message_type=notification_type,
            metadata={
                "notification_type": notification_type,
                "order_id": data.get("order_number"),
                "customer_id": data.get("customer_id"),
            },
        )

        if result["success"]:
            logger.info(f"SMS sent successfully to {phone_number}")
            return {
                "success": True,
                "message_id": result["message_id"],
                "channel": NotificationChannel.SMS,
                "segments": result.get("segments", 1),
                "cost": result.get("cost", 0),
            }
        else:
            logger.error(f"SMS send failed: {result.get('error')}")
            raise Exception(f"SMS send failed: {result.get('error')}")

    async def _send_email(
        self, email_address: str, notification_type: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email notification"""

        # Email subjects in Traditional Chinese
        subjects = {
            NotificationType.ORDER_CONFIRMATION: "幸福氣 - 訂單確認",
            NotificationType.DELIVERY_ON_WAY: "幸福氣 - 瓦斯配送中",
            NotificationType.DELIVERY_COMPLETED: "幸福氣 - 配送完成",
            NotificationType.ORDER_CANCELLED: "幸福氣 - 訂單取消通知",
            NotificationType.PAYMENT_REMINDER: "幸福氣 - 付款提醒",
            NotificationType.URGENT_NOTIFICATION: "幸福氣 - 緊急通知",
            NotificationType.SYSTEM_ALERT: "幸福氣 - 系統通知",
        }

        subject = subjects.get(notification_type, "幸福氣通知")

        # Load email template
        try:
            template = self.template_env.get_template(f"{notification_type}.html")
            html_content = template.render(**data)
        except Exception:
            logger.warning(
                f"Email template not found for {notification_type}, using default"
            )
            # Use default template
            html_content = """
            <html>
                <body style="font - family: Arial, sans - serif;">
                    <h2>{subject}</h2>
                    <p>{data.get('message', '您有一則新通知')}</p>
                    <hr>
                    <p style="color: #666; font - size: 12px;">
                        此為系統自動發送的郵件，請勿直接回覆。<br>
                        如有任何問題，請聯繫客服：0800 - 123 - 456
                    </p>
                </body>
            </html>
            """

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"幸福氣體 <{self.email_from}>"
        msg["To"] = email_address

        # Attach HTML content
        msg.attach(MIMEText(html_content, "html", "utf - 8"))

        # Send email
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._send_email_sync, msg, email_address
        )

        return result

    def _send_email_sync(self, msg: MIMEMultipart, recipient: str) -> Dict[str, Any]:
        """Synchronous email sending (for executor)"""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg)

            logger.info(f"Email sent successfully to {recipient}")
            return {"success": True, "channel": NotificationChannel.EMAIL}
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            raise

    async def _send_push_notification(
        self, user_id: str, notification_type: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send push notification (placeholder for future implementation)"""
        # TODO: Implement FCM / APNS push notifications
        logger.info(f"Push notification would be sent to user {user_id}")
        return {
            "success": True,
            "channel": NotificationChannel.PUSH,
            "placeholder": True,
        }

    async def _send_in_app_notification(
        self, user_id: str, notification_type: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send in - app notification via WebSocket"""
        from app.services.websocket_service import websocket_manager

        notification_data = {
            "type": "notification",
            "notification_type": notification_type,
            "title": data.get("title", "通知"),
            "message": data.get("message", ""),
            "priority": data.get("priority", "normal"),
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        await websocket_manager.send_to_user(user_id, notification_data)

        return {"success": True, "channel": NotificationChannel.IN_APP}

    async def send_order_notifications(self, order: Dict[str, Any], event_type: str):
        """Send notifications for order events"""
        customer_phone = order.get("customer_phone")
        customer_email = order.get("customer_email")
        customer_id = order.get("customer_id")

        notification_data = {
            "order_number": order.get("order_number"),
            "customer_name": order.get("customer_name"),
            "delivery_time": order.get("scheduled_delivery_time", "今天"),
            "driver_name": order.get("driver_name", ""),
            "eta": order.get("eta_minutes", 30),
            "amount": order.get("total_amount", 0),
        }

        # Send SMS if phone available
        if customer_phone:
            await self.send_notification(
                customer_phone,
                event_type,
                NotificationChannel.SMS,
                notification_data,
            )

        # Send email if available
        if customer_email:
            await self.send_notification(
                customer_email,
                event_type,
                NotificationChannel.EMAIL,
                notification_data,
            )

        # Send in - app notification
        if customer_id:
            await self.send_notification(
                customer_id,
                event_type,
                NotificationChannel.IN_APP,
                notification_data,
            )

    async def send_driver_notification(
        self, driver_id: str, notification_type: str, data: Dict[str, Any]
    ):
        """Send notification to driver"""
        # Send in - app notification to driver
        await self.send_notification(
            driver_id,
            notification_type,
            NotificationChannel.IN_APP,
            data
        )

    async def send_bulk_notifications(
        self,
        recipients: List[Dict[str, str]],
        notification_type: str,
        data: Dict[str, Any],
        channels: List[str] = None,
    ):
        """Send notifications to multiple recipients"""
        if channels is None:
            channels = [NotificationChannel.SMS, NotificationChannel.EMAIL]

        tasks = []
        for recipient in recipients:
            for channel in channels:
                if channel == NotificationChannel.SMS and recipient.get("phone"):
                    tasks.append(
                        self.send_notification(
                            recipient["phone"], notification_type, channel, data
                        )
                    )
                elif channel == NotificationChannel.EMAIL and recipient.get("email"):
                    tasks.append(
                        self.send_notification(
                            recipient["email"], notification_type, channel, data
                        )
                    )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in results if isinstance(r, dict) and r.get("success")
        )
        error_count = sum(1 for r in results if isinstance(r, Exception))

        return {"total": len(results), "success": success_count, "errors": error_count}


# Singleton instance
notification_service = NotificationService()
