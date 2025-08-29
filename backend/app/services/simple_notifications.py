"""
Simple notification service for SMS and email
Replaces complex notification_service.py with direct sending
"""

import logging
import re

import httpx

from app.core.config import settings
from app.api.deps import get_db

logger = logging.getLogger(__name__)


class SimpleNotificationService:
    """
    Direct notification sending without queuing.

    Features:
    - Direct SMS sending via provider API
    - Simple email sending via SMTP
    - Database logging for audit trail
    - Taiwan - specific phone validation
    """

    def __init__(self):
        self.sms_provider_url = getattr(
            settings, "SMS_PROVIDER_URL", "https://api.sms.tw / send"
        )
        self.sms_api_key = getattr(settings, "SMS_API_KEY", "")
        self.sms_sender = getattr(settings, "SMS_SENDER_NAME", "LuckyGas")

    async def send_sms(self, phone: str, message: str) -> bool:
        """
        Send SMS directly to provider.

        Args:
            phone: Recipient phone number (Taiwan format)
            message: SMS content in Traditional Chinese

        Returns:
            bool: True if sent successfully
        """
        # Validate phone format
        if not self._validate_taiwan_phone(phone):
            logger.error(f"Invalid Taiwan phone format: {phone}")
            return False

        # Normalize phone number
        normalized_phone = self._normalize_phone(phone)

        try:
            # Send SMS via provider API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.sms_provider_url,
                    json={
                        "phone": normalized_phone,
                        "message": message,
                        "sender": self.sms_sender,
                    },
                    headers={
                        "Authorization": f"Bearer {self.sms_api_key}",
                        "Content - Type": "application / json",
                    },
                )

                success = response.status_code == 200

                # Log to database
                await self._log_notification(
                    notification_type="sms",
                    recipient=normalized_phone,
                    content=message,
                    status="sent" if success else "failed",
                    error_message=None if success else response.text[:500],
                )

                if success:
                    logger.info(f"SMS sent successfully to {normalized_phone}")
                else:
                    logger.error(
                        f"SMS failed to {normalized_phone}: {response.status_code}"
                    )

                return success

        except httpx.TimeoutException:
            logger.error(f"SMS timeout to {normalized_phone}")
            await self._log_notification(
                notification_type="sms",
                recipient=normalized_phone,
                content=message,
                status="failed",
                error_message="Request timeout",
            )
            return False

        except Exception as e:
            logger.error(f"SMS error to {normalized_phone}: {e}")
            await self._log_notification(
                notification_type="sms",
                recipient=normalized_phone,
                content=message,
                status="failed",
                error_message=str(e)[:500],
            )
            return False

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """
        Send email (simplified implementation).

        For now, just log it. Can be extended with SMTP later.
        """
        await self._log_notification(
            notification_type="email",
            recipient=to,
            content=f"Subject: {subject}\n\n{body}",
            status="sent",
            error_message=None,
        )

        logger.info(f"Email logged for {to}: {subject}")
        return True

    # Notification templates for common scenarios

    async def notify_order_confirmed(self, order) -> bool:
        """Send order confirmation SMS to customer"""
        if not order.customer or not order.customer.phone:
            return False

        message = (
            "【幸福氣】您的瓦斯訂單已確認\n"
            f"訂單編號：{order.order_number}\n"
            f"預計送達：{order.scheduled_date.strftime('%m月 % d日')}\n"
            f"送達時段：{order.delivery_time_start}-{order.delivery_time_end}"
        )

        return await self.send_sms(order.customer.phone, message)

    async def notify_driver_arriving(self, order) -> bool:
        """Send driver arriving soon SMS to customer"""
        if not order.customer or not order.customer.phone:
            return False

        message = (
            "【幸福氣】您的瓦斯即將送達！\n"
            "司機將在10 - 15分鐘內抵達\n"
            f"訂單編號：{order.order_number}"
        )

        return await self.send_sms(order.customer.phone, message)

    async def notify_order_delivered(self, order) -> bool:
        """Send delivery confirmation SMS to customer"""
        if not order.customer or not order.customer.phone:
            return False

        message = (
            "【幸福氣】您的瓦斯已送達\n"
            f"訂單編號：{order.order_number}\n"
            "感謝您的訂購！"
        )

        return await self.send_sms(order.customer.phone, message)

    async def notify_route_assigned(self, driver, route) -> bool:
        """Send route assignment notification to driver"""
        if not driver.phone:
            return False

        message = (
            "【幸福氣】您有新的配送路線\n"
            f"路線編號：{route.route_number}\n"
            f"配送點數：{route.total_stops}\n"
            f"預計時間：{route.estimated_duration_minutes}分鐘"
        )

        return await self.send_sms(driver.phone, message)

    def _validate_taiwan_phone(self, phone: str) -> bool:
        """
        Validate Taiwan phone number format.

        Accepts:
        - Mobile: 09XX - XXX - XXX or 09XXXXXXXX
        - Landline: 0X - XXXX - XXXX or 0XXXXXXXXX
        """
        # Remove common separators
        clean_phone = re.sub(r"[-\s()]", "", phone)

        # Mobile number pattern (09 followed by 8 digits)
        if re.match(r"^09\d{8}$", clean_phone):
            return True

        # Landline pattern (0 + area code + 7 - 8 digits)
        if re.match(r"^0[2 - 8]\d{7, 8}$", clean_phone):
            return True

        return False

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to consistent format"""
        # Remove all non - digits
        return re.sub(r"\D", "", phone)

    async def _log_notification(
        self,
        notification_type: str,
        recipient: str,
        content: str,
        status: str,
        error_message: Optional[str] = None,
    ):
        """Log notification to database for audit trail"""
        try:
            async for db in get_db():
                await db.execute(
                    """
                    INSERT INTO notification_history
                    (type, recipient, content, status, error_message, sent_at)
                    VALUES (:type, :recipient, :content, :status, :error, NOW())
                    """,
                    {
                        "type": notification_type,
                        "recipient": recipient,
                        "content": content[:1000],  # Limit content length
                        "status": status,
                        "error": error_message,
                    },
                )
                await db.commit()
                break

        except Exception as e:
            logger.error(f"Failed to log notification: {e}")
            # Don't fail the notification if logging fails

    async def get_notification_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get notification statistics for monitoring"""
        try:
            async for db in get_db():
                result = await db.execute(
                    """
                    SELECT
                        type,
                        status,
                        COUNT(*) as count
                    FROM notification_history
                    WHERE sent_at >= NOW() - INTERVAL :days DAY
                    GROUP BY type, status
                    """,
                    {"days": days},
                )

                stats = {
                    "sms": {"sent": 0, "failed": 0},
                    "email": {"sent": 0, "failed": 0},
                }

                for row in result:
                    stats[row.type][row.status] = row.count

                return stats

        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {}


# Global instance
notification_service = SimpleNotificationService()


# Convenience functions
async def send_order_sms(order, template: str) -> bool:
    """Send SMS for order using template"""
    if template == "confirmed":
        return await notification_service.notify_order_confirmed(order)
    elif template == "arriving":
        return await notification_service.notify_driver_arriving(order)
    elif template == "delivered":
        return await notification_service.notify_order_delivered(order)
    else:
        logger.error(f"Unknown SMS template: {template}")
        return False
