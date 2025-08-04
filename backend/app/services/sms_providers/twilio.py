"""Twilio SMS provider implementation for production use."""

import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
import base64
from urllib.parse import urlencode

from app.core.config import settings
from app.models.notification import NotificationStatus

logger = logging.getLogger(__name__)


class TwilioProvider:
    """Production-ready Twilio SMS provider with connection pooling"""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER
        self.webhook_url = settings.TWILIO_WEBHOOK_URL
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

        # Connection pool
        self._session: Optional[aiohttp.ClientSession] = None

        # Performance metrics
        self.total_sent = 0
        self.total_failed = 0
        self.last_error = None

    async def initialize(self):
        """Initialize provider with connection pool"""
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache timeout
        )

        # Create session with authentication
        auth_str = f"{self.account_sid}:{self.auth_token}"
        auth_bytes = auth_str.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        self._session = aiohttp.ClientSession(
            connector=connector,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )

        logger.info("Twilio provider initialized with connection pooling")

    async def send_sms(
        self, phone: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS via Twilio

        Args:
            phone: Recipient phone number (should be formatted for international)
            message: Message content
            metadata: Additional tracking data

        Returns:
            Dict with success status, message_id, cost, segments
        """
        if not self._session:
            await self.initialize()

        try:
            # Format phone for international if needed
            if not phone.startswith("+"):
                if phone.startswith("886"):
                    phone = "+" + phone
                elif phone.startswith("0"):
                    phone = "+886" + phone[1:]
                else:
                    phone = "+886" + phone

            # Calculate segments before sending
            segments = self._calculate_segments(message)

            # Prepare request data
            data = {"To": phone, "From": self.from_number, "Body": message}

            # Add status callback if configured
            if self.webhook_url:
                data["StatusCallback"] = f"{self.webhook_url}/webhooks/sms/twilio"

            # Add custom parameters for tracking
            if metadata:
                if "order_id" in metadata:
                    data["ProvideFeedback"] = "true"
                    data["Tag"] = f"order_{metadata['order_id']}"

            # Send request
            url = f"{self.base_url}/Messages.json"

            async with self._session.post(url, data=urlencode(data)) as response:
                result = await response.json()

                if response.status == 201:
                    self.total_sent += 1

                    # Calculate cost in TWD (Twilio returns in USD)
                    cost_usd = (
                        float(result.get("price", 0)) * -1
                    )  # Twilio returns negative
                    cost_twd = cost_usd * 30  # Approximate USD to TWD conversion

                    return {
                        "success": True,
                        "message_id": result["sid"],
                        "segments": segments,
                        "cost": cost_twd,
                        "provider_response": {
                            "status": result.get("status"),
                            "date_created": result.get("date_created"),
                            "direction": result.get("direction"),
                        },
                    }
                else:
                    self.total_failed += 1
                    self.last_error = result.get("message", "Unknown error")

                    error_details = {
                        "code": result.get("code"),
                        "message": result.get("message"),
                        "more_info": result.get("more_info"),
                    }

                    logger.error(f"Twilio API error: {error_details}")

                    return {
                        "success": False,
                        "error": self.last_error,
                        "error_details": error_details,
                    }

        except aiohttp.ClientError as e:
            self.total_failed += 1
            self.last_error = f"Network error: {str(e)}"
            logger.error(f"Twilio network error: {e}")

            return {"success": False, "error": self.last_error}

        except Exception as e:
            self.total_failed += 1
            self.last_error = str(e)
            logger.error(f"Twilio unexpected error: {e}")

            return {"success": False, "error": self.last_error}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        """Check message delivery status"""
        if not self._session:
            await self.initialize()

        try:
            url = f"{self.base_url}/Messages/{message_id}.json"

            async with self._session.get(url) as response:
                if response.status == 200:
                    result = await response.json()

                    # Map Twilio status to our status enum
                    status_map = {
                        "queued": NotificationStatus.PENDING,
                        "sending": NotificationStatus.SENT,
                        "sent": NotificationStatus.SENT,
                        "delivered": NotificationStatus.DELIVERED,
                        "undelivered": NotificationStatus.FAILED,
                        "failed": NotificationStatus.FAILED,
                    }

                    twilio_status = result.get("status", "").lower()
                    our_status = status_map.get(
                        twilio_status, NotificationStatus.PENDING
                    )

                    return {
                        "success": True,
                        "status": our_status,
                        "provider_status": twilio_status,
                        "error_code": result.get("error_code"),
                        "error_message": result.get("error_message"),
                        "date_sent": result.get("date_sent"),
                        "date_updated": result.get("date_updated"),
                    }
                else:
                    error = await response.json()
                    return {
                        "success": False,
                        "error": error.get("message", "Failed to check status"),
                    }

        except Exception as e:
            logger.error(f"Error checking Twilio message status: {e}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check by checking account status"""
        if not self._session:
            await self.initialize()

        try:
            # Check account details as health check
            url = f"{self.base_url}.json"

            async with self._session.get(url) as response:
                if response.status == 200:
                    account = await response.json()

                    return {
                        "healthy": account.get("status") == "active",
                        "account_status": account.get("status"),
                        "account_name": account.get("friendly_name"),
                        "success_rate": (
                            self.total_sent / (self.total_sent + self.total_failed)
                            if (self.total_sent + self.total_failed) > 0
                            else 1.0
                        ),
                        "last_error": self.last_error,
                    }
                else:
                    return {
                        "healthy": False,
                        "error": f"HTTP {response.status}",
                        "last_error": self.last_error,
                    }

        except Exception as e:
            logger.error(f"Twilio health check failed: {e}")
            return {"healthy": False, "error": str(e), "last_error": self.last_error}

    async def register_delivery_callback(
        self, message_id: str, callback_url: str
    ) -> bool:
        """
        Register webhook for delivery updates
        Note: Twilio supports setting callback URL during send, not after
        """
        # Twilio doesn't support updating callback URL after sending
        # This is handled during send_sms with StatusCallback parameter
        logger.info(
            f"Twilio uses StatusCallback during send, cannot update for {message_id}"
        )
        return False

    def _calculate_segments(self, message: str) -> int:
        """Calculate number of SMS segments for message"""
        # Check if message contains Unicode (Chinese characters)
        is_unicode = any(ord(char) > 127 for char in message)

        if is_unicode:
            # Unicode: 70 chars for single segment, 67 for multi-segment
            if len(message) <= 70:
                return 1
            else:
                return ((len(message) - 1) // 67) + 1
        else:
            # GSM 7-bit: 160 chars for single segment, 153 for multi-segment
            if len(message) <= 160:
                return 1
            else:
                return ((len(message) - 1) // 153) + 1

    async def close(self):
        """Close connection pool"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Twilio provider connection pool closed")
