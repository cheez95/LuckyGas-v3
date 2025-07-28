"""
Payment webhook handlers with HMAC validation.

This module handles payment notifications from various payment providers
with proper signature validation, idempotency, and security measures.
"""

import logging
import hmac
import hashlib
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.core.config import settings
from app.core.secrets_manager import get_secret
from app.models.invoice import Payment, PaymentStatus, PaymentMethod
from app.models.webhook import WebhookLog, WebhookStatus
from app.core.monitoring import track_webhook_event
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/payments", tags=["payment-webhooks"])


class PaymentWebhookValidator:
    """Validates payment webhook signatures from different providers."""
    
    @staticmethod
    async def verify_stripe_signature(
        payload: bytes,
        signature: str,
        webhook_secret: str,
        timestamp: Optional[int] = None
    ) -> bool:
        """Verify Stripe webhook signature."""
        if not timestamp:
            # Extract timestamp from signature header
            elements = signature.split(",")
            for element in elements:
                if element.startswith("t="):
                    timestamp = int(element.split("=")[1])
                    break
        
        if not timestamp:
            return False
        
        # Check timestamp is within 5 minutes
        current_time = int(time.time())
        if abs(current_time - timestamp) > 300:
            return False
        
        # Extract signature
        expected_sig = None
        for element in signature.split(","):
            if element.startswith("v1="):
                expected_sig = element.split("=")[1]
                break
        
        if not expected_sig:
            return False
        
        # Compute signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        computed_sig = hmac.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(computed_sig, expected_sig)
    
    @staticmethod
    async def verify_paypal_signature(
        headers: dict,
        payload: bytes,
        webhook_id: str,
        webhook_secret: str
    ) -> bool:
        """Verify PayPal webhook signature."""
        # PayPal signature components
        transmission_id = headers.get("paypal-transmission-id")
        transmission_time = headers.get("paypal-transmission-time")
        cert_url = headers.get("paypal-cert-url")
        actual_sig = headers.get("paypal-transmission-sig")
        
        if not all([transmission_id, transmission_time, cert_url, actual_sig]):
            return False
        
        # Build signature string
        crc32 = str(zlib.crc32(payload) & 0xffffffff)
        sig_string = f"{transmission_id}|{transmission_time}|{webhook_id}|{crc32}"
        
        # Verify with webhook secret (simplified - in production use PayPal SDK)
        expected_sig = hmac.new(
            webhook_secret.encode('utf-8'),
            sig_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, actual_sig)
    
    @staticmethod
    async def verify_generic_hmac(
        payload: bytes,
        signature: str,
        secret: str,
        algorithm: str = "sha256"
    ) -> bool:
        """Verify generic HMAC signature."""
        if algorithm == "sha256":
            hash_func = hashlib.sha256
        elif algorithm == "sha1":
            hash_func = hashlib.sha1
        elif algorithm == "md5":
            hash_func = hashlib.md5
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hash_func
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, signature)


validator = PaymentWebhookValidator()


async def check_idempotency(
    db: AsyncSession,
    provider: str,
    event_id: str
) -> bool:
    """Check if webhook event has already been processed."""
    result = await db.execute(
        select(WebhookLog).where(
            WebhookLog.provider == provider,
            WebhookLog.event_id == event_id,
            WebhookLog.status == WebhookStatus.PROCESSED
        )
    )
    return result.scalar_one_or_none() is not None


async def log_webhook_event(
    db: AsyncSession,
    provider: str,
    event_id: str,
    event_type: str,
    payload: dict,
    status: WebhookStatus,
    error_message: Optional[str] = None
):
    """Log webhook event for audit trail."""
    webhook_log = WebhookLog(
        provider=provider,
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        status=status,
        error_message=error_message,
        received_at=datetime.utcnow()
    )
    db.add(webhook_log)
    await db.commit()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(None)
):
    """Handle Stripe payment webhooks."""
    webhook_received_at = datetime.utcnow()
    
    try:
        # Get raw body
        body = await request.body()
        
        # Verify signature
        if settings.ENVIRONMENT != "development":
            if not stripe_signature:
                await track_webhook_event(
                    provider="stripe",
                    event_type="missing_signature",
                    status="rejected"
                )
                raise HTTPException(status_code=401, detail="Missing signature")
            
            webhook_secret = await get_secret("STRIPE_WEBHOOK_SECRET")
            if not webhook_secret:
                logger.error("Stripe webhook secret not configured")
                raise HTTPException(status_code=500, detail="Configuration error")
            
            if not await validator.verify_stripe_signature(
                body, stripe_signature, webhook_secret
            ):
                await track_webhook_event(
                    provider="stripe",
                    event_type="invalid_signature",
                    status="rejected"
                )
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        data = json.loads(body)
        event_id = data.get("id")
        event_type = data.get("type")
        
        # Check idempotency
        if await check_idempotency(db, "stripe", event_id):
            logger.info(f"Stripe event {event_id} already processed")
            return {"status": "ok", "message": "Event already processed"}
        
        # Process different event types
        if event_type == "payment_intent.succeeded":
            await process_stripe_payment_success(db, data)
        elif event_type == "payment_intent.payment_failed":
            await process_stripe_payment_failure(db, data)
        elif event_type == "charge.dispute.created":
            await process_stripe_dispute(db, data)
        
        # Log successful processing
        await log_webhook_event(
            db, "stripe", event_id, event_type, data,
            WebhookStatus.PROCESSED
        )
        
        await track_webhook_event(
            provider="stripe",
            event_type=event_type,
            status="success",
            metadata={
                "event_id": event_id,
                "processed_in_ms": int((datetime.utcnow() - webhook_received_at).total_seconds() * 1000)
            }
        )
        
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        if 'event_id' in locals():
            await log_webhook_event(
                db, "stripe", event_id, event_type or "unknown", 
                data if 'data' in locals() else {},
                WebhookStatus.FAILED,
                str(e)
            )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ecpay")
async def ecpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle ECPay (綠界) payment webhooks - Taiwan's popular payment gateway."""
    webhook_received_at = datetime.utcnow()
    
    try:
        # Get form data
        form_data = await request.form()
        data = dict(form_data)
        
        # Verify CheckMacValue
        if settings.ENVIRONMENT != "development":
            check_mac_value = data.get("CheckMacValue")
            if not check_mac_value:
                await track_webhook_event(
                    provider="ecpay",
                    event_type="missing_checksum",
                    status="rejected"
                )
                raise HTTPException(status_code=401, detail="Missing CheckMacValue")
            
            # Get merchant keys
            hash_key = await get_secret("ECPAY_HASH_KEY")
            hash_iv = await get_secret("ECPAY_HASH_IV")
            
            if not hash_key or not hash_iv:
                logger.error("ECPay keys not configured")
                raise HTTPException(status_code=500, detail="Configuration error")
            
            # Verify CheckMacValue (ECPay specific algorithm)
            if not verify_ecpay_checksum(data, check_mac_value, hash_key, hash_iv):
                await track_webhook_event(
                    provider="ecpay",
                    event_type="invalid_checksum",
                    status="rejected"
                )
                raise HTTPException(status_code=401, detail="Invalid CheckMacValue")
        
        # Extract payment info
        merchant_trade_no = data.get("MerchantTradeNo")
        rtn_code = data.get("RtnCode", "")
        payment_type = data.get("PaymentType")
        trade_amt = data.get("TradeAmt")
        
        # Check idempotency
        if await check_idempotency(db, "ecpay", merchant_trade_no):
            logger.info(f"ECPay trade {merchant_trade_no} already processed")
            return "1|OK"  # ECPay expects this response
        
        # Process payment
        if rtn_code == "1":  # Success
            await process_ecpay_payment_success(db, data)
        else:
            await process_ecpay_payment_failure(db, data)
        
        # Log webhook
        await log_webhook_event(
            db, "ecpay", merchant_trade_no, "payment_notification",
            data, WebhookStatus.PROCESSED
        )
        
        await track_webhook_event(
            provider="ecpay",
            event_type="payment_notification",
            status="success",
            metadata={
                "trade_no": merchant_trade_no,
                "rtn_code": rtn_code,
                "amount": trade_amt
            }
        )
        
        return "1|OK"  # ECPay expects this response format
        
    except HTTPException:
        return "0|Error"
    except Exception as e:
        logger.error(f"Error processing ECPay webhook: {e}")
        return "0|Error"


@router.post("/tappay")
async def tappay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_tappay_signature: str = Header(None)
):
    """Handle TapPay payment webhooks - Another Taiwan payment provider."""
    webhook_received_at = datetime.utcnow()
    
    try:
        # Get body
        body = await request.body()
        data = json.loads(body)
        
        # Verify signature
        if settings.ENVIRONMENT != "development":
            if not x_tappay_signature:
                raise HTTPException(status_code=401, detail="Missing signature")
            
            partner_key = await get_secret("TAPPAY_PARTNER_KEY")
            if not partner_key:
                logger.error("TapPay partner key not configured")
                raise HTTPException(status_code=500, detail="Configuration error")
            
            if not await validator.verify_generic_hmac(
                body, x_tappay_signature, partner_key
            ):
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Process webhook
        event_type = data.get("event")
        rec_trade_id = data.get("rec_trade_id")
        
        if event_type == "payment.success":
            await process_tappay_payment_success(db, data)
        elif event_type == "payment.failed":
            await process_tappay_payment_failure(db, data)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing TapPay webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def verify_ecpay_checksum(
    params: dict,
    checksum: str,
    hash_key: str,
    hash_iv: str
) -> bool:
    """Verify ECPay CheckMacValue."""
    # Remove CheckMacValue from params
    params_copy = {k: v for k, v in params.items() if k != "CheckMacValue"}
    
    # Sort by key
    sorted_params = sorted(params_copy.items())
    
    # Build check string
    param_string = "&".join([f"{k}={v}" for k, v in sorted_params])
    
    # Add HashKey and HashIV
    check_string = f"HashKey={hash_key}&{param_string}&HashIV={hash_iv}"
    
    # URL encode
    import urllib.parse
    check_string = urllib.parse.quote(check_string, safe='').lower()
    
    # Calculate SHA256
    calculated = hashlib.sha256(check_string.encode('utf-8')).hexdigest().upper()
    
    return calculated == checksum


async def process_stripe_payment_success(db: AsyncSession, data: dict):
    """Process successful Stripe payment."""
    payment_service = PaymentService(db)
    payment_intent = data.get("data", {}).get("object", {})
    
    # Extract payment details
    amount = payment_intent.get("amount", 0) / 100  # Convert from cents
    payment_id = payment_intent.get("metadata", {}).get("payment_id")
    
    if payment_id:
        await payment_service.confirm_payment(
            payment_id=payment_id,
            transaction_id=payment_intent.get("id"),
            amount=amount
        )


async def process_stripe_payment_failure(db: AsyncSession, data: dict):
    """Process failed Stripe payment."""
    payment_service = PaymentService(db)
    payment_intent = data.get("data", {}).get("object", {})
    
    payment_id = payment_intent.get("metadata", {}).get("payment_id")
    if payment_id:
        await payment_service.mark_payment_failed(
            payment_id=payment_id,
            reason=payment_intent.get("last_payment_error", {}).get("message")
        )


async def process_stripe_dispute(db: AsyncSession, data: dict):
    """Process Stripe dispute/chargeback."""
    # Log dispute for manual review
    dispute = data.get("data", {}).get("object", {})
    logger.warning(f"Stripe dispute created: {dispute.get('id')} for amount {dispute.get('amount')}")
    
    # TODO: Implement dispute handling workflow
    pass


async def process_ecpay_payment_success(db: AsyncSession, data: dict):
    """Process successful ECPay payment."""
    payment_service = PaymentService(db)
    
    # Extract payment ID from MerchantTradeNo
    merchant_trade_no = data.get("MerchantTradeNo", "")
    payment_id = merchant_trade_no.split("_")[1] if "_" in merchant_trade_no else None
    
    if payment_id:
        await payment_service.confirm_payment(
            payment_id=payment_id,
            transaction_id=data.get("TradeNo"),
            amount=float(data.get("TradeAmt", 0))
        )


async def process_ecpay_payment_failure(db: AsyncSession, data: dict):
    """Process failed ECPay payment."""
    payment_service = PaymentService(db)
    
    merchant_trade_no = data.get("MerchantTradeNo", "")
    payment_id = merchant_trade_no.split("_")[1] if "_" in merchant_trade_no else None
    
    if payment_id:
        await payment_service.mark_payment_failed(
            payment_id=payment_id,
            reason=f"ECPay RtnCode: {data.get('RtnCode')} - {data.get('RtnMsg')}"
        )


async def process_tappay_payment_success(db: AsyncSession, data: dict):
    """Process successful TapPay payment."""
    payment_service = PaymentService(db)
    
    payment_id = data.get("order_number")
    if payment_id:
        await payment_service.confirm_payment(
            payment_id=payment_id,
            transaction_id=data.get("rec_trade_id"),
            amount=float(data.get("amount", 0))
        )


async def process_tappay_payment_failure(db: AsyncSession, data: dict):
    """Process failed TapPay payment."""
    payment_service = PaymentService(db)
    
    payment_id = data.get("order_number")
    if payment_id:
        await payment_service.mark_payment_failed(
            payment_id=payment_id,
            reason=data.get("msg")
        )


# Import zlib for PayPal
try:
    import zlib
except ImportError:
    logger.warning("zlib not available, PayPal webhook validation will be limited")