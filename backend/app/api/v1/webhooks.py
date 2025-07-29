"""Webhook handlers for external services."""
from fastapi import APIRouter, Request, HTTPException, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hmac
import hashlib
import logging
import time
import base64
from typing import Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.api.deps import get_db
from app.core.config import settings
from app.core.secrets_manager import get_secret
from app.models.notification import SMSLog, NotificationStatus, SMSProvider
from app.core.monitoring import track_webhook_event

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
        
    # Calculate signature using SHA1 and base64
    mac = hmac.new(
        auth_token.encode('utf-8'),
        s.encode('utf-8'),
        hashlib.sha1
    )
    calculated = base64.b64encode(mac.digest()).decode('utf-8')
    
    return hmac.compare_digest(calculated, signature)


def verify_every8d_signature(
    params: dict,
    signature: str,
    secret: str
) -> bool:
    """Verify Every8d webhook signature"""
    # Every8d uses MD5(BatchID + RM + STATUS + ST + secret)
    batch_id = params.get("BatchID", "")
    phone = params.get("RM", "")
    status = params.get("STATUS", "")
    status_time = params.get("ST", "")
    
    data_string = f"{batch_id}{phone}{status}{status_time}{secret}"
    calculated = hashlib.md5(data_string.encode('utf-8')).hexdigest().upper()
    
    return hmac.compare_digest(calculated, signature.upper())


@router.post("/sms/twilio")
async def twilio_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_twilio_signature: Optional[str] = Header(None)
):
    """Handle Twilio SMS delivery status webhooks"""
    webhook_received_at = datetime.utcnow()
    
    try:
        # Get form data
        form_data = await request.form()
        data = dict(form_data)
        
        # Verify signature
        if settings.ENVIRONMENT != "development":
            if not x_twilio_signature:
                await track_webhook_event(
                    provider="twilio",
                    event_type="missing_signature",
                    status="rejected",
                    metadata={"reason": "No signature header"}
                )
                raise HTTPException(status_code=401, detail="Missing signature")
            
            # Get auth token from secure storage
            auth_token = await get_secret("TWILIO_AUTH_TOKEN")
            if not auth_token:
                logger.error("Twilio auth token not configured")
                raise HTTPException(status_code=500, detail="Configuration error")
            
            # Verify the signature
            request_url = str(request.url)
            if not verify_twilio_signature(request_url, data, x_twilio_signature, auth_token):
                await track_webhook_event(
                    provider="twilio",
                    event_type="invalid_signature",
                    status="rejected",
                    metadata={"signature": x_twilio_signature[:10] + "..."}
                )
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Check timestamp to prevent replay attacks (5 minute window)
        if "Timestamp" in data:
            try:
                webhook_timestamp = datetime.fromisoformat(data["Timestamp"])
                if abs((webhook_received_at - webhook_timestamp).total_seconds()) > 300:
                    await track_webhook_event(
                        provider="twilio",
                        event_type="replay_attack",
                        status="rejected",
                        metadata={"timestamp_diff": abs((webhook_received_at - webhook_timestamp).total_seconds())}
                    )
                    raise HTTPException(status_code=401, detail="Request too old")
            except Exception as e:
                logger.warning(f"Failed to parse webhook timestamp: {e}")
        
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
        
        # Track successful webhook
        await track_webhook_event(
            provider="twilio",
            event_type="status_update",
            status="success",
            metadata={
                "message_sid": message_sid,
                "status": status,
                "processed_in_ms": int((datetime.utcnow() - webhook_received_at).total_seconds() * 1000)
            }
        )
        
        logger.info(f"Updated SMS {message_sid} status to {status}")
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {e}")
        await track_webhook_event(
            provider="twilio",
            event_type="processing_error",
            status="failed",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sms/every8d")
async def every8d_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    signature: Optional[str] = Query(None, alias="sign")
):
    """Handle Every8d SMS delivery status webhooks"""
    webhook_received_at = datetime.utcnow()
    
    try:
        # Get form data
        form_data = await request.form()
        data = dict(form_data)
        
        # Verify signature
        if settings.ENVIRONMENT != "development":
            if not signature:
                await track_webhook_event(
                    provider="every8d",
                    event_type="missing_signature",
                    status="rejected",
                    metadata={"reason": "No signature parameter"}
                )
                raise HTTPException(status_code=401, detail="Missing signature")
            
            # Get secret from secure storage
            secret = await get_secret("EVERY8D_WEBHOOK_SECRET")
            if not secret:
                logger.error("Every8d webhook secret not configured")
                raise HTTPException(status_code=500, detail="Configuration error")
            
            # Verify the signature
            if not verify_every8d_signature(data, signature, secret):
                await track_webhook_event(
                    provider="every8d",
                    event_type="invalid_signature",
                    status="rejected",
                    metadata={"signature": signature[:10] + "..."}
                )
                raise HTTPException(status_code=401, detail="Invalid signature")
        
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
        
        # Track successful webhook
        await track_webhook_event(
            provider="every8d",
            event_type="status_update",
            status="success",
            metadata={
                "batch_id": batch_id,
                "status_code": status_code,
                "processed_in_ms": int((datetime.utcnow() - webhook_received_at).total_seconds() * 1000)
            }
        )
        
        logger.info(f"Updated SMS {batch_id} status to {sms_log.status}")
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Every8d webhook: {e}")
        await track_webhook_event(
            provider="every8d",
            event_type="processing_error",
            status="failed",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sms/mitake")
async def mitake_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    checksum: Optional[str] = Query(None)
):
    """Handle Mitake SMS delivery status webhooks"""
    webhook_received_at = datetime.utcnow()
    
    try:
        # Get query parameters or form data
        params = dict(request.query_params)
        if not params:
            form_data = await request.form()
            params = dict(form_data)
        
        # Verify checksum for Mitake
        if settings.ENVIRONMENT != "development":
            if not checksum:
                await track_webhook_event(
                    provider="mitake",
                    event_type="missing_checksum",
                    status="rejected",
                    metadata={"reason": "No checksum parameter"}
                )
                raise HTTPException(status_code=401, detail="Missing checksum")
            
            # Get secret from secure storage
            secret = await get_secret("MITAKE_WEBHOOK_SECRET")
            if not secret:
                logger.error("Mitake webhook secret not configured")
                raise HTTPException(status_code=500, detail="Configuration error")
            
            # Verify checksum (Mitake uses MD5 of sorted params + secret)
            sorted_params = sorted([(k, v) for k, v in params.items() if k != "checksum"])
            param_string = "".join([f"{k}{v}" for k, v in sorted_params])
            data_string = f"{param_string}{secret}"
            calculated_checksum = hashlib.md5(data_string.encode('utf-8')).hexdigest()
            
            if not hmac.compare_digest(calculated_checksum, checksum):
                await track_webhook_event(
                    provider="mitake",
                    event_type="invalid_checksum",
                    status="rejected",
                    metadata={"checksum": checksum[:10] + "..."}
                )
                raise HTTPException(status_code=401, detail="Invalid checksum")
            
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
        
        # Track successful webhook
        await track_webhook_event(
            provider="mitake",
            event_type="status_update",
            status="success",
            metadata={
                "msgid": msgid,
                "statuscode": statuscode,
                "statusstr": statusstr,
                "processed_in_ms": int((datetime.utcnow() - webhook_received_at).total_seconds() * 1000)
            }
        )
        
        logger.info(f"Updated SMS {msgid} status to {sms_log.status}")
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Mitake webhook: {e}")
        await track_webhook_event(
            provider="mitake",
            event_type="processing_error",
            status="failed",
            metadata={"error": str(e)}
        )
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