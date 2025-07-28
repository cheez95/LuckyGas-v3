"""Enhanced SMS webhook handlers with security and monitoring."""
from fastapi import APIRouter, Request, HTTPException, Depends, Header, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import hmac
import hashlib
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from app.api.deps import get_db
from app.api.auth_deps import get_current_superuser
from app.core.config import settings
from app.models.notification import SMSLog, NotificationStatus, SMSProvider, SMSTemplate
from app.services.notification_service import notification_service
from app.core.api_monitoring import api_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sms", tags=["sms"])


def verify_webhook_signature(
    provider: SMSProvider,
    request_data: Dict[str, Any],
    signature: str,
    secret: str
) -> bool:
    """Verify webhook signature based on provider"""
    
    if provider == SMSProvider.TWILIO:
        # Twilio uses HMAC-SHA1
        # Build string to sign
        sorted_params = sorted(request_data.items())
        string_to_sign = ""
        for key, value in sorted_params:
            string_to_sign += f"{key}{value}"
            
        mac = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        )
        calculated = mac.hexdigest()
        return hmac.compare_digest(calculated, signature)
        
    elif provider == SMSProvider.CHUNGHWA:
        # Chunghwa uses MD5
        data_string = json.dumps(request_data, sort_keys=True)
        calculated = hashlib.md5(
            f"{data_string}{secret}".encode('utf-8')
        ).hexdigest()
        return calculated == signature
        
    return False


@router.post("/delivery/twilio")
async def twilio_delivery_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_twilio_signature: Optional[str] = Header(None)
):
    """
    Handle Twilio SMS delivery status webhooks
    
    Twilio sends status updates for:
    - queued, sending, sent, delivered, undelivered, failed
    """
    try:
        # Record webhook call
        await api_monitor.record_webhook_call("twilio_sms_delivery")
        
        # Get form data
        form_data = await request.form()
        data = dict(form_data)
        
        # Verify signature in production
        if settings.ENVIRONMENT == "production" and x_twilio_signature:
            auth_token = settings.TWILIO_AUTH_TOKEN
            request_url = str(request.url)
            
            if not verify_webhook_signature(
                SMSProvider.TWILIO,
                data,
                x_twilio_signature,
                auth_token
            ):
                logger.warning("Invalid Twilio webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
                
        # Extract status info
        message_sid = data.get("MessageSid")
        status = data.get("MessageStatus", "").lower()
        error_code = data.get("ErrorCode")
        error_message = data.get("ErrorMessage")
        
        if not message_sid:
            raise HTTPException(status_code=400, detail="Missing MessageSid")
            
        # Find SMS log
        result = await db.execute(
            select(SMSLog).where(
                SMSLog.provider_message_id == message_sid
            )
        )
        sms_log = result.scalar_one_or_none()
        
        if not sms_log:
            logger.warning(f"SMS log not found for MessageSid: {message_sid}")
            # Return OK to prevent Twilio from retrying
            return {"status": "ok", "message": "Log not found but acknowledged"}
            
        # Update status
        status_map = {
            "queued": NotificationStatus.PENDING,
            "sending": NotificationStatus.SENT,
            "sent": NotificationStatus.SENT,
            "delivered": NotificationStatus.DELIVERED,
            "undelivered": NotificationStatus.FAILED,
            "failed": NotificationStatus.FAILED
        }
        
        new_status = status_map.get(status)
        if new_status:
            sms_log.status = new_status
            
            if new_status == NotificationStatus.DELIVERED:
                sms_log.delivered_at = datetime.utcnow()
                
                # Update template effectiveness if using template
                if sms_log.message_type:
                    background_tasks.add_task(
                        update_template_effectiveness,
                        sms_log.message_type,
                        db
                    )
                    
                # Send delivery notification to websocket
                background_tasks.add_task(
                    notification_service.send_sms_delivery_notification,
                    sms_log.id,
                    sms_log.recipient,
                    "delivered"
                )
                
            elif new_status == NotificationStatus.FAILED:
                sms_log.failed_at = datetime.utcnow()
                sms_log.error_message = f"Error {error_code}: {error_message}" if error_code else error_message
                
                # Send failure notification
                background_tasks.add_task(
                    notification_service.send_sms_delivery_notification,
                    sms_log.id,
                    sms_log.recipient,
                    "failed",
                    sms_log.error_message
                )
                
        # Add delivery metadata
        if not sms_log.notification_metadata:
            sms_log.notification_metadata = {}
            
        sms_log.notification_metadata["twilio_status"] = status
        sms_log.notification_metadata["last_webhook_at"] = datetime.utcnow().isoformat()
        
        await db.commit()
        
        logger.info(f"Updated SMS {message_sid} status to {status}")
        
        # Record successful webhook processing
        await api_monitor.record_webhook_success("twilio_sms_delivery")
        
        return {"status": "ok", "message": f"Status updated to {status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {e}")
        await api_monitor.record_webhook_error("twilio_sms_delivery", str(e))
        # Return OK to prevent retries for processing errors
        return {"status": "ok", "message": "Error acknowledged"}


@router.post("/delivery/chunghwa")
async def chunghwa_delivery_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_cht_signature: Optional[str] = Header(None)
):
    """
    Handle Chunghwa Telecom SMS delivery status webhooks
    
    CHT sends XML status updates
    """
    try:
        # Record webhook call
        await api_monitor.record_webhook_call("chunghwa_sms_delivery")
        
        # Get request body
        body = await request.body()
        
        # Verify signature in production
        if settings.ENVIRONMENT == "production" and x_cht_signature:
            secret = settings.CHT_SMS_WEBHOOK_SECRET
            
            if not verify_webhook_signature(
                SMSProvider.CHUNGHWA,
                {"body": body.decode('utf-8')},
                x_cht_signature,
                secret
            ):
                logger.warning("Invalid Chunghwa webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
                
        # Parse XML response
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(body)
            
            msg_id = root.find("MessageId").text
            status_code = root.find("StatusCode").text
            status_text = root.find("StatusText").text
            delivery_time = root.find("DeliveryTime").text
            recipient = root.find("Recipient").text
            
        except Exception as e:
            logger.error(f"Failed to parse CHT XML: {e}")
            raise HTTPException(status_code=400, detail="Invalid XML format")
            
        if not msg_id:
            raise HTTPException(status_code=400, detail="Missing MessageId")
            
        # Find SMS log
        result = await db.execute(
            select(SMSLog).where(
                SMSLog.provider_message_id == msg_id
            )
        )
        sms_log = result.scalar_one_or_none()
        
        if not sms_log:
            logger.warning(f"SMS log not found for MessageId: {msg_id}")
            return {"status": "ok", "message": "Log not found but acknowledged"}
            
        # Update status based on CHT codes
        # 0: 已送達, 1: 發送中, 2: 等待中, 3: 發送失敗, 4: 無法送達
        status_map = {
            "0": NotificationStatus.DELIVERED,
            "1": NotificationStatus.SENT,
            "2": NotificationStatus.PENDING,
            "3": NotificationStatus.FAILED,
            "4": NotificationStatus.FAILED
        }
        
        new_status = status_map.get(status_code, NotificationStatus.PENDING)
        sms_log.status = new_status
        
        if new_status == NotificationStatus.DELIVERED:
            sms_log.delivered_at = datetime.fromisoformat(delivery_time) if delivery_time else datetime.utcnow()
            
            # Update template effectiveness
            if sms_log.message_type:
                background_tasks.add_task(
                    update_template_effectiveness,
                    sms_log.message_type,
                    db
                )
                
            # Send delivery notification
            background_tasks.add_task(
                notification_service.send_sms_delivery_notification,
                sms_log.id,
                sms_log.recipient,
                "delivered"
            )
            
        elif new_status == NotificationStatus.FAILED:
            sms_log.failed_at = datetime.utcnow()
            sms_log.error_message = f"CHT Status: {status_code} - {status_text}"
            
            # Send failure notification
            background_tasks.add_task(
                notification_service.send_sms_delivery_notification,
                sms_log.id,
                sms_log.recipient,
                "failed",
                sms_log.error_message
            )
            
        # Add delivery metadata
        if not sms_log.notification_metadata:
            sms_log.notification_metadata = {}
            
        sms_log.notification_metadata["cht_status_code"] = status_code
        sms_log.notification_metadata["cht_status_text"] = status_text
        sms_log.notification_metadata["last_webhook_at"] = datetime.utcnow().isoformat()
        
        await db.commit()
        
        logger.info(f"Updated SMS {msg_id} status to {new_status}")
        
        # Record successful webhook processing
        await api_monitor.record_webhook_success("chunghwa_sms_delivery")
        
        # Return XML response
        response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Status>0</Status>
    <Message>Success</Message>
</Response>"""
        
        return Response(content=response_xml, media_type="application/xml")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Chunghwa webhook: {e}")
        await api_monitor.record_webhook_error("chunghwa_sms_delivery", str(e))
        
        # Return error XML
        error_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Status>1</Status>
    <Message>Error acknowledged</Message>
</Response>"""
        
        return Response(content=error_xml, media_type="application/xml")


@router.post("/test-webhook/{provider}")
async def test_webhook(
    provider: str,
    request: Request,
    current_user=Depends(get_current_superuser)
):
    """Test webhook endpoint for development and debugging (superuser only)"""
    
    # Log request details
    body = await request.body()
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    
    logger.info(f"Test webhook received for {provider}")
    logger.info(f"Headers: {headers}")
    logger.info(f"Query params: {query_params}")
    logger.info(f"Body: {body}")
    
    # Try to parse body
    parsed_body = None
    try:
        # Try JSON
        parsed_body = json.loads(body)
        body_type = "json"
    except:
        try:
            # Try form data
            form_data = await request.form()
            parsed_body = dict(form_data)
            body_type = "form"
        except:
            # Try XML
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(body)
                parsed_body = {"xml": ET.tostring(root, encoding='unicode')}
                body_type = "xml"
            except:
                parsed_body = body.decode('utf-8')
                body_type = "raw"
                
    return {
        "provider": provider,
        "method": request.method,
        "headers": headers,
        "query_params": query_params,
        "body_type": body_type,
        "body": parsed_body,
        "timestamp": datetime.utcnow().isoformat()
    }


async def update_template_effectiveness(template_code: str, db: AsyncSession):
    """Update SMS template effectiveness score"""
    try:
        # Get template
        result = await db.execute(
            select(SMSTemplate).where(
                SMSTemplate.code == template_code,
                SMSTemplate.is_active == True
            )
        )
        template = result.scalar_one_or_none()
        
        if template:
            template.delivered_count += 1
            
            # Calculate effectiveness score
            if template.sent_count > 0:
                template.effectiveness_score = (
                    template.delivered_count / template.sent_count
                ) * 100
                
            await db.commit()
            logger.info(
                f"Updated template {template_code} effectiveness: "
                f"{template.effectiveness_score:.2f}%"
            )
            
    except Exception as e:
        logger.error(f"Error updating template effectiveness: {e}")


# Import Response for XML responses
from fastapi.responses import Response