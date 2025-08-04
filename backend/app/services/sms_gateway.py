"""SMS Gateway abstraction layer for production SMS services."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol


from app.core.config import settings

logger = logging.getLogger(__name__)


class SMSProviderInterface(Protocol):
    """Interface for SMS providers"""

    async def send_sms(self, phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send SMS message"""
        ...

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        """Check message delivery status"""
        ...

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        ...

    async def register_delivery_callback(
        self, message_id: str, callback_url: str
    ) -> bool:
        """Register webhook for delivery updates"""
        ...


class SMSGateway:
    """SMS Gateway with provider abstraction and production features"""

    def __init__(self):
        self._providers: Dict[SMSProvider, SMSProviderInterface] = {}
        self._primary_provider: Optional[SMSProvider] = None
        self._fallback_providers: List[SMSProvider] = []
        self._connection_pools: Dict[SMSProvider, Any] = {}
        self._rate_limiters: Dict[SMSProvider, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize SMS gateway with configured providers"""
        # Load provider configuration from settings
        if settings.SMS_TWILIO_ENABLED:
            from app.services.sms_providers.twilio import TwilioProvider

            self._providers[SMSProvider.TWILIO] = TwilioProvider()
            await self._providers[SMSProvider.TWILIO].initialize()

        if settings.SMS_CHUNGHWA_ENABLED:
            from app.services.sms_providers.chunghwa import ChunghwaProvider

            self._providers[SMSProvider.CHUNGHWA] = ChunghwaProvider()
            await self._providers[SMSProvider.CHUNGHWA].initialize()

        # Set primary and fallback providers
        self._primary_provider = (
            SMSProvider(settings.SMS_PRIMARY_PROVIDER)
            if settings.SMS_PRIMARY_PROVIDER
            else None
        )
        self._fallback_providers = [
            SMSProvider(p) for p in settings.SMS_FALLBACK_PROVIDERS if p
        ]

        logger.info(
            f"SMS Gateway initialized with providers: {list(self._providers.keys())}"
        )

    async def send_sms(
        self,
        phone: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """
        Send SMS with automatic provider selection and failover

        Args:
            phone: Recipient phone number
            message: Message content (used if template_id not provided)
            template_id: Template ID for message
            variables: Variables for template substitution
            metadata: Additional metadata for tracking
            priority: Message priority (high, normal, low)

        Returns:
            Dict with send result including message_id, provider, cost
        """
        # Format phone number for Taiwan
        phone = self._format_phone_number(phone)

        # Get message from template if provided
        if template_id and variables:
            message = await self._render_template(template_id, variables)

        # Try primary provider first
        if self._primary_provider and self._primary_provider in self._providers:
            if await self._check_rate_limit(self._primary_provider, priority):
                result = await self._send_with_provider(
                    self._primary_provider, phone, message, metadata
                )
                if result["success"]:
                    return result

        # Try fallback providers
        for provider in self._fallback_providers:
            if provider in self._providers and await self._check_rate_limit(
                provider, priority
            ):
                result = await self._send_with_provider(
                    provider, phone, message, metadata
                )
                if result["success"]:
                    return result

        # All providers failed
        return {
            "success": False,
            "error": "All SMS providers failed",
            "providers_tried": [self._primary_provider] + self._fallback_providers,
        }

    async def _send_with_provider(
        self,
        provider: SMSProvider,
        phone: str,
        message: str,
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send SMS using specific provider"""
        try:
            provider_instance = self._providers[provider]

            # Send message
            result = await provider_instance.send_sms(
                phone=phone, message=message, metadata=metadata
            )

            if result["success"]:
                # Update rate limiter
                await self._update_rate_limit(provider)

                # Add provider info to result
                result["provider"] = provider

            return result

        except Exception as e:
            logger.error(f"Error sending SMS with {provider}: {e}")
            return {"success": False, "error": str(e), "provider": provider}

    async def _check_rate_limit(self, provider: SMSProvider, priority: str) -> bool:
        """Check if provider rate limit allows sending"""
        if provider not in self._rate_limiters:
            self._rate_limiters[provider] = {
                "tokens": settings.SMS_RATE_LIMIT_PER_MINUTE,
                "last_refill": datetime.utcnow(),
                "priority_boost": {"high": 2.0, "normal": 1.0, "low": 0.5},
            }

        limiter = self._rate_limiters[provider]
        now = datetime.utcnow()

        # Refill tokens
        time_passed = (now - limiter["last_refill"]).total_seconds()
        if time_passed >= 60:
            limiter["tokens"] = settings.SMS_RATE_LIMIT_PER_MINUTE
            limiter["last_refill"] = now

        # Check tokens with priority boost
        required_tokens = 1 / limiter["priority_boost"].get(priority, 1.0)

        if limiter["tokens"] >= required_tokens:
            return True

        return False

    async def _update_rate_limit(self, provider: SMSProvider):
        """Update rate limit after sending"""
        if provider in self._rate_limiters:
            self._rate_limiters[provider]["tokens"] -= 1

    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for Taiwan"""
        # Remove any non-numeric characters
        phone = "".join(filter(str.isdigit, phone))

        # Handle Taiwan mobile numbers
        if phone.startswith("886"):
            return phone  # Already has country code
        elif phone.startswith("09") and len(phone) == 10:
            return "886" + phone[1:]  # Convert to international format
        elif phone.startswith("9") and len(phone) == 9:
            return "886" + phone  # Missing leading 0

        # Return as-is if format unknown
        return phone

    async def _render_template(
        self, template_id: str, variables: Dict[str, Any]
    ) -> str:
        """Render message template with variables"""
        # This would be implemented to fetch template from database
        # and render with variables
        # For now, return a placeholder
        templates = {
            "order_confirmation": "【幸福氣】訂單確認：您的訂單 {order_id} 已確認，預計送達時間 {delivery_time}",
            "out_for_delivery": "【幸福氣】配送通知：您的訂單 {order_id} 正在配送中，司機 {driver_name} 將在 {eta} 分鐘內送達",
            "delivery_completed": "【幸福氣】配送完成：您的訂單 {order_id} 已送達，感謝您的訂購！",
            "payment_reminder": "【幸福氣】付款提醒：您有待付款訂單 {order_id}，金額 NT${amount}，請儘快完成付款",
        }

        template = templates.get(template_id, "")
        if template:
            return template.format(**variables)

        return ""

    async def check_delivery_status(
        self, message_id: str, provider: SMSProvider
    ) -> Dict[str, Any]:
        """Check SMS delivery status from provider"""
        if provider not in self._providers:
            return {"success": False, "error": f"Provider {provider} not configured"}

        try:
            provider_instance = self._providers[provider]
            return await provider_instance.check_status(message_id)
        except Exception as e:
            logger.error(f"Error checking status with {provider}: {e}")
            return {"success": False, "error": str(e)}

    async def perform_health_checks(self) -> Dict[SMSProvider, Dict[str, Any]]:
        """Perform health checks on all providers"""
        results = {}

        for provider, instance in self._providers.items():
            try:
                health_result = await instance.health_check()
                results[provider] = health_result
            except Exception as e:
                logger.error(f"Health check failed for {provider}: {e}")
                results[provider] = {"healthy": False, "error": str(e)}

        return results

    async def close(self):
        """Close all provider connections"""
        for provider, instance in self._providers.items():
            try:
                if hasattr(instance, "close"):
                    await instance.close()
            except Exception as e:
                logger.error(f"Error closing {provider}: {e}")


# Global SMS gateway instance
sms_gateway = SMSGateway()


async def get_sms_gateway() -> SMSGateway:
    """Get SMS gateway instance"""
    if not sms_gateway._providers:
        await sms_gateway.initialize()
    return sms_gateway
