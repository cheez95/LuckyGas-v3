"""
Mock SMS Gateway Service for Testing
Simulates SMS sending functionality
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock SMS Gateway", version="1.0.0")

# Store sent messages for testing
sent_messages: List[dict] = []


class SMSRequest(BaseModel):
    to: str
    message: str
    from_number: Optional[str] = "+886900000000"
    callback_url: Optional[str] = None


class SMSResponse(BaseModel):
    message_id: str
    status: str
    to: str
    from_number: str
    message: str
    timestamp: str
    cost: float


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "mock-sms",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/sms/send", response_model=SMSResponse)
async def send_sms(request: SMSRequest, authorization: Optional[str] = Header(None)):
    """Mock SMS send endpoint"""
    logger.info(f"SMS send request to: {request.to}")

    # Simulate authentication
    if authorization != "Bearer test_token":
        logger.warning("Invalid authorization token")
        # Allow for testing without auth in test environment
        pass

    # Validate phone number (Taiwan format)
    if not (request.to.startswith("09") or request.to.startswith("+8869")):
        raise HTTPException(
            status_code=400, detail="Invalid Taiwan phone number format"
        )

    # Simulate random failures (5% failure rate)
    if random.random() < 0.05:
        raise HTTPException(
            status_code=500, detail="SMS gateway temporarily unavailable"
        )

    # Create mock response
    message_id = f"sms_{uuid.uuid4().hex[:12]}"
    response = SMSResponse(
        message_id=message_id,
        status="sent",
        to=request.to,
        from_number=request.from_number,
        message=request.message,
        timestamp=datetime.now().isoformat(),
        cost=0.85,  # Mock cost in TWD
    )

    # Store message for testing
    sent_messages.append(
        {
            "message_id": message_id,
            "to": request.to,
            "from": request.from_number,
            "message": request.message,
            "timestamp": response.timestamp,
            "status": "sent",
            "callback_url": request.callback_url,
        }
    )

    logger.info(f"SMS sent successfully: {message_id}")

    # Simulate webhook callback if provided
    if request.callback_url:
        # In real implementation, this would be async
        logger.info(f"Would send webhook to: {request.callback_url}")

    return response


@app.get("/api/sms/status/{message_id}")
async def get_sms_status(message_id: str):
    """Get SMS delivery status"""
    logger.info(f"Status request for message: {message_id}")

    # Find message
    message = next((m for m in sent_messages if m["message_id"] == message_id), None)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Simulate status progression
    time_diff = (datetime.now() - datetime.fromisoformat(message["timestamp"])).seconds

    if time_diff < 10:
        status = "sent"
    elif time_diff < 30:
        status = "delivered"
    else:
        status = "delivered" if random.random() > 0.1 else "failed"

    message["status"] = status

    return {
        "message_id": message_id,
        "status": status,
        "to": message["to"],
        "timestamp": message["timestamp"],
        "delivery_timestamp": (
            datetime.now().isoformat() if status == "delivered" else None
        ),
    }


@app.post("/api/sms/bulk")
async def send_bulk_sms(messages: List[SMSRequest]):
    """Send multiple SMS messages"""
    logger.info(f"Bulk SMS request for {len(messages)} messages")

    results = []
    for msg in messages:
        try:
            result = await send_sms(msg)
            results.append(
                {"success": True, "message_id": result.message_id, "to": result.to}
            )
        except Exception as e:
            results.append({"success": False, "to": msg.to, "error": str(e)})

    return {
        "total": len(messages),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results,
    }


@app.get("/api/sms/sent")
async def get_sent_messages(limit: int = 100):
    """Get list of sent messages for testing"""
    return {"total": len(sent_messages), "messages": sent_messages[-limit:]}


@app.delete("/api/sms/clear")
async def clear_messages():
    """Clear sent messages (for testing)"""
    sent_messages.clear()
    return {"message": "All messages cleared"}


# Mock webhook endpoint for testing callbacks
@app.post("/mock-webhook")
async def mock_webhook(data: dict):
    """Mock webhook receiver for testing SMS callbacks"""
    logger.info(f"Webhook received: {data}")
    return {"status": "received"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
