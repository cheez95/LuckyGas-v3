"""Webhook handlers for external services."""
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hmac
import hashlib
import logging
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.notification import SMSLog, NotificationStatus, SMSProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_twilio_signature(
    request_url: str,
    params: dict,
    signature: str,
    auth_token: str
) -> bool:
    """Verify Twilio webhook signature"""
    # Sort parameters alphabetically
    sorted_params = sorted(params.items())
    
    # Build the string to sign
    s = request_url
    for k, v in sorted_params:
        s += f"{k}{v}"
        
    # Calculate signature
    mac = hmac.new(
        auth_token.encode('utf-8'),
        s.encode('utf-8'),
        hashlib.sha1
    )
    calculated = mac.hexdigest()
    
    return hmac.compare_digest(calculated, signature)


def verify_every8d_signature(
    data: str,
    signature: str,
    secret: str
) -> bool:
    """Verify Every8d webhook signature"""
    calculated = hashlib.md5(
        f"{data}{secret}".encode('utf-8')
    ).hexdigest()
    
    return calculated == signature


@router.post("/sms/twilio")
async def twilio_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_twilio_signature: Optional[str] = Header(None)
):
    """Handle Twilio SMS delivery status webhooks"""
    try:
        # Get form data
        form_data = await request.form()
        data = dict(form_data)
        
        # TODO: Verify signature in production
        # if x_twilio_signature:
        #     auth_token = "your_auth_token"  # Get from secure storage
        #     if not verify_twilio_signature(str(request.url), data, x_twilio_signature, auth_token):
        #         raise HTTPException(status_code=401, detail="Invalid signature")
        
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
            return {"status": "ok"}  # Return OK to prevent retries
            
        # Update status
        status_map = {
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
            elif new_status == NotificationStatus.FAILED:
                sms_log.failed_at = datetime.utcnow()
                sms_log.error_message = f"Error {error_code}: {error_message}" if error_code else error_message
                
        await db.commit()
        
        logger.info(f"Updated SMS {message_sid} status to {status}")
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sms/every8d")
async def every8d_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Every8d SMS delivery status webhooks"""
    try:
        # Get form data
        form_data = await request.form()
        data = dict(form_data)
        
        # Extract status info
        batch_id = data.get("BatchID")
        phone = data.get("RM")  # Recipient mobile
        status_code = data.get("STATUS")
        status_time = data.get("ST")  # Status time
        
        if not batch_id:
            raise HTTPException(status_code=400, detail="Missing BatchID")
            
        # Find SMS log
        result = await db.execute(
            select(SMSLog).where(
                SMSLog.provider_message_id == batch_id,
                SMSLog.recipient.like(f"%{phone[-8:]}") if phone else True
            )
        )
        sms_log = result.scalar_one_or_none()
        
        if not sms_log:
            logger.warning(f"SMS log not found for BatchID: {batch_id}")
            return {"status": "ok"}
            
        # Update status based on Every8d codes
        # 100: Delivered, 101: Waiting, 102: Sending, other: Failed
        if status_code == "100":
            sms_log.status = NotificationStatus.DELIVERED
            sms_log.delivered_at = datetime.utcnow()
        elif status_code in ["101", "102"]:
            sms_log.status = NotificationStatus.SENT
        else:
            sms_log.status = NotificationStatus.FAILED
            sms_log.failed_at = datetime.utcnow()
            sms_log.error_message = f"Status code: {status_code}"
            
        await db.commit()
        
        logger.info(f"Updated SMS {batch_id} status to {sms_log.status}")
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Every8d webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sms/mitake")
async def mitake_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Mitake SMS delivery status webhooks"""
    try:
        # Get query parameters or form data
        params = dict(request.query_params)
        if not params:
            form_data = await request.form()
            params = dict(form_data)
            
        # Extract status info
        msgid = params.get("msgid")
        dstaddr = params.get("dstaddr")  # Recipient phone
        dlvtime = params.get("dlvtime")  # Delivery time
        donetime = params.get("donetime")  # Done time
        statuscode = params.get("statuscode")
        statusstr = params.get("statusstr")
        
        if not msgid:
            raise HTTPException(status_code=400, detail="Missing msgid")
            
        # Find SMS log
        result = await db.execute(
            select(SMSLog).where(
                SMSLog.provider_message_id == msgid
            )
        )
        sms_log = result.scalar_one_or_none()
        
        if not sms_log:
            logger.warning(f"SMS log not found for msgid: {msgid}")
            return {"status": "ok"}
            
        # Update status
        # statuscode 0 = success, statusstr 0 = delivered
        if statuscode == "0":
            if statusstr == "0":
                sms_log.status = NotificationStatus.DELIVERED
                sms_log.delivered_at = datetime.utcnow()
            else:
                sms_log.status = NotificationStatus.SENT
        else:
            sms_log.status = NotificationStatus.FAILED
            sms_log.failed_at = datetime.utcnow()
            sms_log.error_message = f"Status: {statuscode}/{statusstr}"
            
        await db.commit()
        
        logger.info(f"Updated SMS {msgid} status to {sms_log.status}")
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Mitake webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sms/generic/{provider}")
async def generic_sms_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Generic webhook handler for other SMS providers"""
    try:
        # Log the webhook data for debugging
        body = await request.body()
        headers = dict(request.headers)
        
        logger.info(f"Received webhook from {provider}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Body: {body}")
        
        # Try to parse JSON
        try:
            import json
            data = json.loads(body)
        except:
            # Try form data
            form_data = await request.form()
            data = dict(form_data)
            
        # Log for future implementation
        logger.info(f"Webhook data from {provider}: {data}")
        
        return {"status": "ok", "message": f"Webhook received for {provider}"}
        
    except Exception as e:
        logger.error(f"Error processing {provider} webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")