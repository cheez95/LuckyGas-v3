"""
Communications API endpoints for SMS and notifications
"""

from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.core.security import verify_user_role
from app.services.notification_service import NotificationService, NotificationType
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
notification_service = NotificationService()


class SMSRequest(BaseModel):
    """SMS request model"""

    phone: str
    template: str  # Template type: arriving, delivered, etc.
    order_id: str
    custom_message: str = None


@router.post("/sms")
async def send_sms(
    sms_data: SMSRequest, current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Send SMS to customer"""
    verify_user_role(current_user, ["driver", "office_staff", "manager", "admin"])

    # Map template to message
    template_messages = {
        "arriving": f"您好，幸福氣配送員即將抵達，請準備接收瓦斯。訂單編號: {sms_data.order_id}",
        "delivered": f"您的幸福氣瓦斯已送達。訂單編號: {sms_data.order_id}。謝謝您的惠顧！",
        "delayed": f"抱歉，您的幸福氣配送因故延遲，我們會盡快為您送達。訂單編號: {sms_data.order_id}",
        "custom": sms_data.custom_message or "來自幸福氣的訊息",
    }

    message = template_messages.get(sms_data.template, template_messages["custom"])

    try:
        # Send SMS via notification service
        result = await notification_service._send_sms(
            phone=sms_data.phone, message=message
        )

        if result:
            logger.info(
                f"SMS sent successfully to {sms_data.phone} by {current_user.full_name}"
            )
            return {"status": "success", "message": "簡訊已發送"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="簡訊發送失敗"
            )

    except Exception as e:
        logger.error(f"Failed to send SMS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"簡訊發送失敗: {str(e)}",
        )
