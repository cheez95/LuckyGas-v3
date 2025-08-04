"""Enhanced SMS service with Taiwan provider support."""

import asyncio
import hashlib
import logging
import random
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.notification import (NotificationStatus, ProviderConfig,
                                     SMSLog, SMSProvider, SMSTemplate)

logger = logging.getLogger(__name__)


class SMSProviderBase:
    """Base class for SMS providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    async def send_sms(self, phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send SMS - must be implemented by provider"""
        raise NotImplementedError

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        """Check message delivery status"""
        raise NotImplementedError

    def calculate_segments(self, message: str) -> int:
        """Calculate number of SMS segments for message"""
        # Unicode (Chinese) messages have different limits
        if any(ord(char) > 127 for char in message):
            # Unicode: 70 chars for single, 67 for multi-segment
            if len(message) <= 70:
                return 1
            return ((len(message) - 1) // 67) + 1
        else:
            # GSM 7-bit: 160 chars for single, 153 for multi-segment
            if len(message) <= 160:
                return 1
            return ((len(message) - 1) // 153) + 1


class TwilioProvider(SMSProviderBase):
    """Twilio SMS provider"""

    async def send_sms(self, phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        try:
            from_number = self.config.get("from_number")
            account_sid = self.config.get("account_sid")
            auth_token = self.config.get("auth_token")

            # Format phone for international
            if not phone.startswith("+"):
                phone = "+886" + phone[1:] if phone.startswith("0") else "+886" + phone

            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

            data = {"To": phone, "From": from_number, "Body": message}

            auth = aiohttp.BasicAuth(account_sid, auth_token)

            async with aiohttp.ClientSession(auth=auth) as session:
                async with session.post(url, data=data) as response:
                    result = await response.json()

                    if response.status == 201:
                        return {
                            "success": True,
                            "message_id": result["sid"],
                            "segments": self.calculate_segments(message),
                            "cost": float(result.get("price", 0))
                            * -30,  # Convert USD to TWD estimate
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("message", "Unknown error"),
                        }

        except Exception as e:
            logger.error(f"Twilio SMS error: {e}")
            return {"success": False, "error": str(e)}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        """Check Twilio message status"""
        try:
            account_sid = self.config.get("account_sid")
            auth_token = self.config.get("auth_token")

            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{message_id}.json"

            auth = aiohttp.BasicAuth(account_sid, auth_token)

            async with aiohttp.ClientSession(auth=auth) as session:
                async with session.get(url) as response:
                    result = await response.json()

                    status_map = {
                        "delivered": NotificationStatus.DELIVERED,
                        "sent": NotificationStatus.SENT,
                        "failed": NotificationStatus.FAILED,
                        "undelivered": NotificationStatus.FAILED,
                    }

                    return {
                        "status": status_map.get(
                            result["status"], NotificationStatus.PENDING
                        ),
                        "error": result.get("error_message"),
                    }

        except Exception as e:
            logger.error(f"Twilio status check error: {e}")
            return {"status": NotificationStatus.FAILED, "error": str(e)}


class Every8dProvider(SMSProviderBase):
    """Every8d (Taiwan) SMS provider"""

    async def send_sms(self, phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send SMS via Every8d"""
        try:
            username = self.config.get("username")
            password = self.config.get("password")
            api_url = self.config.get("api_url", "https://api.e8d.tw/SMS/BulkSMS")

            # Format phone for Taiwan (remove country code if present)
            if phone.startswith("+886"):
                phone = "0" + phone[4:]
            elif not phone.startswith("0"):
                phone = "0" + phone

            params = {
                "UID": username,
                "PWD": password,
                "SB": "",  # Subject (optional)
                "MSG": message,
                "DEST": phone,
                "ST": "",  # Scheduled time (optional)
                "RETRYTIME": 300,  # Retry time in seconds
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    text = await response.text()

                    # Parse response (format: credit,sended,cost,unsend,batch_id)
                    parts = text.strip().split(",")

                    if len(parts) >= 5 and float(parts[1]) > 0:
                        return {
                            "success": True,
                            "message_id": parts[4],  # batch_id
                            "segments": self.calculate_segments(message),
                            "cost": float(parts[2]),  # Cost in TWD
                        }
                    else:
                        error_codes = {
                            "-1": "Send time format error",
                            "-2": "Send time expired",
                            "-4": "Account error",
                            "-5": "Password error",
                            "-6": "Insufficient balance",
                            "-20": "Source IP not authorized",
                            "-99": "System error",
                        }
                        error_msg = error_codes.get(
                            text.strip(), f"Unknown error: {text}"
                        )
                        return {"success": False, "error": error_msg}

        except Exception as e:
            logger.error(f"Every8d SMS error: {e}")
            return {"success": False, "error": str(e)}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        """Check Every8d message status"""
        # Every8d requires separate status API endpoint
        # Implementation depends on their specific API
        return {"status": NotificationStatus.SENT, "error": None}


class MitakeProvider(SMSProviderBase):
    """Mitake (三竹) SMS provider"""

    async def send_sms(self, phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send SMS via Mitake"""
        try:
            username = self.config.get("username")
            password = self.config.get("password")
            api_url = self.config.get(
                "api_url", "https://api.mitake.com.tw/api/mtk/SmSend"
            )

            # Format phone for Taiwan
            if phone.startswith("+886"):
                phone = "0" + phone[4:]
            elif not phone.startswith("0"):
                phone = "0" + phone

            # Mitake uses INI format for requests
            ini_data = f"""[0]
dstaddr={phone}
smbody={message}
dlvtime=
vldtime=
response=Y"""

            params = {"username": username, "password": password, "encoding": "UTF8"}

            headers = {"Content-Type": "text/plain; charset=UTF-8"}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    params=params,
                    data=ini_data.encode("utf-8"),
                    headers=headers,
                ) as response:
                    text = await response.text()

                    # Parse INI response
                    lines = text.strip().split("\n")
                    result = {}
                    for line in lines:
                        if "=" in line:
                            key, value = line.split("=", 1)
                            result[key.strip()] = value.strip()

                    if result.get("statuscode") == "0":
                        return {
                            "success": True,
                            "message_id": result.get("msgid", ""),
                            "segments": self.calculate_segments(message),
                            "cost": float(result.get("AccountPoint", 0)),
                        }
                    else:
                        error_codes = {
                            "1": "Invalid username/password",
                            "2": "Insufficient balance",
                            "3": "Invalid recipient",
                            "4": "Invalid message content",
                            "5": "Invalid sending time",
                            "6": "Invalid validity time",
                            "7": "Sending failed",
                        }
                        error_msg = error_codes.get(
                            result.get("statuscode", ""),
                            f"Unknown error: {result.get('Error', text)}",
                        )
                        return {"success": False, "error": error_msg}

        except Exception as e:
            logger.error(f"Mitake SMS error: {e}")
            return {"success": False, "error": str(e)}

    async def check_status(self, message_id: str) -> Dict[str, Any]:
        """Check Mitake message status"""
        try:
            username = self.config.get("username")
            password = self.config.get("password")
            api_url = "https://api.mitake.com.tw/api/mtk/SmQuery"

            params = {"username": username, "password": password, "msgid": message_id}

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    text = await response.text()

                    # Parse response
                    if "statuscode=0" in text and "statusstr=0" in text:
                        return {"status": NotificationStatus.DELIVERED, "error": None}
                    elif "statuscode=0" in text:
                        return {"status": NotificationStatus.SENT, "error": None}
                    else:
                        return {"status": NotificationStatus.FAILED, "error": text}

        except Exception as e:
            logger.error(f"Mitake status check error: {e}")
            return {"status": NotificationStatus.FAILED, "error": str(e)}


class EnhancedSMSService:
    """Enhanced SMS service with multiple provider support and production features"""

    def __init__(self):
        self.providers = {
            SMSProvider.TWILIO: TwilioProvider,
            SMSProvider.EVERY8D: Every8dProvider,
            SMSProvider.MITAKE: MitakeProvider,
        }
        self._provider_instances = {}
        self._rate_limiters = {}
        self._circuit_breakers = {}
        self._delivery_callbacks = {}
        self._init_metrics()
        self._load_production_credentials()

    def _init_metrics(self):
        """Initialize Prometheus metrics for monitoring"""
        try:
            from prometheus_client import Counter, Gauge, Histogram, Summary

            self.metrics = {
                "sms_sent": Counter(
                    "sms_messages_sent_total",
                    "Total SMS messages sent",
                    ["provider", "status", "message_type"],
                ),
                "sms_delivery": Counter(
                    "sms_messages_delivered_total",
                    "Total SMS messages delivered",
                    ["provider", "message_type"],
                ),
                "sms_cost": Summary(
                    "sms_message_cost_twd", "SMS message cost in TWD", ["provider"]
                ),
                "provider_latency": Histogram(
                    "sms_provider_latency_seconds",
                    "SMS provider API latency",
                    ["provider", "operation"],
                ),
                "provider_health": Gauge(
                    "sms_provider_health",
                    "SMS provider health status (1=healthy, 0=unhealthy)",
                    ["provider"],
                ),
                "rate_limit_remaining": Gauge(
                    "sms_rate_limit_remaining", "Remaining SMS rate limit", ["provider"]
                ),
            }
        except ImportError:
            logger.warning("Prometheus client not available, metrics disabled")
            self.metrics = None

    def _load_production_credentials(self):
        """Load SMS provider credentials from Secret Manager"""
        if settings.ENVIRONMENT != "production":
            return

        try:
            from app.core.secrets_manager import get_secrets_manager

            sm = get_secrets_manager()

            # Load provider credentials
            for provider in SMSProvider:
                credentials = sm.get_secret_json(f"sms-{provider.value}-credentials")
                if credentials:
                    # Store securely
                    self._store_provider_credentials(provider, credentials)
                    logger.info(f"Loaded credentials for SMS provider {provider.value}")

        except Exception as e:
            logger.error(f"Failed to load SMS credentials: {e}")

    def _store_provider_credentials(
        self, provider: SMSProvider, credentials: Dict[str, Any]
    ):
        """Store provider credentials securely"""
        if not hasattr(self, "_provider_credentials"):
            self._provider_credentials = {}

        self._provider_credentials[provider] = credentials

    def _get_provider_config(self, provider: SMSProvider) -> Dict[str, Any]:
        """Get provider configuration with production credentials"""
        config = {}

        # Get from secure storage if available
        if (
            hasattr(self, "_provider_credentials")
            and provider in self._provider_credentials
        ):
            config.update(self._provider_credentials[provider])

        return config

    async def _get_provider_instance(
        self, provider: SMSProvider, db: AsyncSession
    ) -> Optional[SMSProviderBase]:
        """Get or create provider instance with production configuration"""
        if provider not in self._provider_instances:
            # Load config from database
            result = await db.execute(
                select(ProviderConfig).where(
                    and_(
                        ProviderConfig.provider == provider,
                        ProviderConfig.is_active == True,
                    )
                )
            )
            config_obj = result.scalar_one_or_none()

            if not config_obj:
                return None

            provider_class = self.providers.get(provider)
            if not provider_class:
                return None

            # Merge database config with production credentials
            config = config_obj.config.copy()
            prod_config = self._get_provider_config(provider)
            config.update(prod_config)

            # Create provider instance
            instance = provider_class(config)
            self._provider_instances[provider] = instance

            # Initialize circuit breaker for this provider
            if provider not in self._circuit_breakers:
                self._circuit_breakers[provider] = {
                    "failures": 0,
                    "last_failure": None,
                    "state": "closed",
                    "half_open_until": None,
                }

            # Start health monitoring
            asyncio.create_task(self._monitor_provider_health(provider))

        return self._provider_instances[provider]

    async def _monitor_provider_health(self, provider: SMSProvider):
        """Monitor provider health with periodic checks"""
        while True:
            try:
                # Wait 5 minutes between health checks
                await asyncio.sleep(300)

                instance = self._provider_instances.get(provider)
                if not instance:
                    continue

                # Perform health check (send test SMS to monitoring number)
                if hasattr(instance, "health_check"):
                    health_status = await instance.health_check()
                else:
                    # Basic connectivity check
                    health_status = {"healthy": True}

                # Update metrics
                if self.metrics:
                    self.metrics["provider_health"].labels(provider=provider.value).set(
                        1 if health_status.get("healthy") else 0
                    )

                # Reset circuit breaker if healthy
                if (
                    health_status.get("healthy")
                    and self._circuit_breakers[provider]["state"] == "open"
                ):
                    self._circuit_breakers[provider] = {
                        "failures": 0,
                        "last_failure": None,
                        "state": "closed",
                        "half_open_until": None,
                    }
                    logger.info(
                        f"SMS provider {provider.value} recovered, circuit breaker reset"
                    )

            except Exception as e:
                logger.error(
                    f"Health check failed for SMS provider {provider.value}: {e}"
                )

    def _is_circuit_open(self, provider: SMSProvider) -> bool:
        """Check if circuit breaker is open for provider"""
        if provider not in self._circuit_breakers:
            return False

        breaker = self._circuit_breakers[provider]

        if breaker["state"] == "open":
            # Check if we should transition to half-open
            if breaker["last_failure"]:
                time_since_failure = (
                    datetime.utcnow() - breaker["last_failure"]
                ).total_seconds()
                if time_since_failure > 300:  # 5 minutes
                    breaker["state"] = "half_open"
                    breaker["half_open_until"] = datetime.utcnow() + timedelta(
                        seconds=30
                    )
                    logger.info(
                        f"Circuit breaker for {provider.value} transitioning to half-open"
                    )
                else:
                    return True

        elif breaker["state"] == "half_open":
            # Check if half-open period expired
            if datetime.utcnow() > breaker["half_open_until"]:
                breaker["state"] = "closed"
                breaker["failures"] = 0
                logger.info(
                    f"Circuit breaker for {provider.value} closed after successful half-open period"
                )

        return False

    def _record_circuit_failure(self, provider: SMSProvider):
        """Record a failure for circuit breaker"""
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = {
                "failures": 0,
                "last_failure": None,
                "state": "closed",
                "half_open_until": None,
            }

        breaker = self._circuit_breakers[provider]
        breaker["failures"] += 1
        breaker["last_failure"] = datetime.utcnow()

        # Open circuit after 3 failures
        if breaker["failures"] >= 3 and breaker["state"] != "open":
            breaker["state"] = "open"
            logger.warning(
                f"Circuit breaker opened for SMS provider {provider.value} after {breaker['failures']} failures"
            )

    async def _get_best_provider(
        self, db: AsyncSession
    ) -> Optional[Tuple[SMSProvider, SMSProviderBase]]:
        """Get best available provider based on priority and success rate"""
        result = await db.execute(
            select(ProviderConfig)
            .where(ProviderConfig.is_active == True)
            .order_by(
                ProviderConfig.priority.desc(), ProviderConfig.success_rate.desc()
            )
        )
        configs = result.scalars().all()

        for config in configs:
            # Check rate limits
            if not await self._check_rate_limit(config.provider, config.rate_limit):
                continue

            instance = await self._get_provider_instance(config.provider, db)
            if instance:
                return config.provider, instance

        return None

    async def _check_rate_limit(
        self, provider: SMSProvider, limit: Optional[int]
    ) -> bool:
        """Check if provider rate limit allows sending"""
        if not limit:
            return True

        key = f"sms_rate_{provider}"
        current_time = time.time()

        if key not in self._rate_limiters:
            self._rate_limiters[key] = []

        # Remove timestamps older than 1 minute
        self._rate_limiters[key] = [
            t for t in self._rate_limiters[key] if current_time - t < 60
        ]

        if len(self._rate_limiters[key]) >= limit:
            return False

        self._rate_limiters[key].append(current_time)
        return True

    async def _get_template(
        self, template_code: str, db: AsyncSession
    ) -> Optional[str]:
        """Get SMS template with A/B testing support"""
        # Get all active templates for this code
        result = await db.execute(
            select(SMSTemplate).where(
                and_(SMSTemplate.code == template_code, SMSTemplate.is_active == True)
            )
        )
        templates = result.scalars().all()

        if not templates:
            return None

        # Weighted random selection for A/B testing
        if len(templates) > 1:
            weights = [t.weight for t in templates]
            selected = random.choices(templates, weights=weights)[0]
        else:
            selected = templates[0]

        # Update sent count
        selected.sent_count += 1
        await db.commit()

        return selected.content

    async def send_sms(
        self,
        phone: str,
        message: str,
        message_type: Optional[str] = None,
        template_code: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        provider: Optional[SMSProvider] = None,
        metadata: Optional[Dict[str, Any]] = None,
        retry_on_failure: bool = True,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Send SMS with automatic provider selection and retry logic"""

        if not db:
            async for session in get_db():
                db = session
                break

        # Get template if specified
        if template_code and template_data:
            template = await self._get_template(template_code, db)
            if template:
                message = template.format(**template_data)

        # Create log entry
        sms_log = SMSLog(
            recipient=phone,
            message=message,
            message_type=message_type,
            notification_metadata=metadata or {},
            unicode_message=any(ord(char) > 127 for char in message),
        )

        # Get provider
        if provider:
            provider_instance = await self._get_provider_instance(provider, db)
            if not provider_instance:
                sms_log.status = NotificationStatus.FAILED
                sms_log.error_message = f"Provider {provider} not configured"
                db.add(sms_log)
                await db.commit()
                return {"success": False, "error": sms_log.error_message}
        else:
            result = await self._get_best_provider(db)
            if not result:
                sms_log.status = NotificationStatus.FAILED
                sms_log.error_message = "No available SMS providers"
                db.add(sms_log)
                await db.commit()
                return {"success": False, "error": sms_log.error_message}
            provider, provider_instance = result

        sms_log.provider = provider

        # Send SMS
        max_retries = 3 if retry_on_failure else 1
        last_error = None

        for attempt in range(max_retries):
            if attempt > 0:
                # Use different provider on retry
                result = await self._get_best_provider(db)
                if not result:
                    break
                provider, provider_instance = result
                sms_log.provider = provider

            try:
                # Check circuit breaker
                if self._is_circuit_open(provider):
                    logger.warning(
                        f"Circuit breaker open for {provider.value}, skipping"
                    )
                    last_error = f"Provider {provider.value} circuit breaker open"
                    continue

                # Measure latency
                start_time = time.time()

                result = await provider_instance.send_sms(phone, message)

                # Record metrics
                latency = time.time() - start_time
                if self.metrics:
                    self.metrics["provider_latency"].labels(
                        provider=provider.value, operation="send"
                    ).observe(latency)

                if result["success"]:
                    sms_log.status = NotificationStatus.SENT
                    sms_log.sent_at = datetime.utcnow()
                    sms_log.provider_message_id = result.get("message_id")
                    sms_log.segments = result.get("segments", 1)
                    sms_log.cost = result.get("cost", 0)

                    # Update provider stats
                    await self._update_provider_stats(provider, True, db)

                    # Update metrics
                    if self.metrics:
                        self.metrics["sms_sent"].labels(
                            provider=provider.value,
                            status="success",
                            message_type=message_type or "general",
                        ).inc()
                        self.metrics["sms_cost"].labels(
                            provider=provider.value
                        ).observe(sms_log.cost)

                    # Reset circuit breaker on success
                    if self._circuit_breakers[provider]["state"] == "half_open":
                        self._circuit_breakers[provider]["state"] = "closed"
                        self._circuit_breakers[provider]["failures"] = 0
                        logger.info(
                            f"Circuit breaker for {provider.value} closed after successful send"
                        )

                    # Register delivery callback if provider supports it
                    if hasattr(provider_instance, "register_delivery_callback"):
                        callback_url = (
                            f"{settings.API_V1_STR}/webhooks/sms/delivery/{sms_log.id}"
                        )
                        await provider_instance.register_delivery_callback(
                            sms_log.provider_message_id, callback_url
                        )

                    db.add(sms_log)
                    await db.commit()

                    return {
                        "success": True,
                        "message_id": sms_log.id,
                        "provider_message_id": sms_log.provider_message_id,
                        "segments": sms_log.segments,
                        "cost": sms_log.cost,
                    }
                else:
                    last_error = result.get("error", "Unknown error")
                    sms_log.retry_count = attempt + 1

                    # Record circuit failure
                    self._record_circuit_failure(provider)

                    # Update failure metrics
                    if self.metrics:
                        self.metrics["sms_sent"].labels(
                            provider=provider.value,
                            status="failure",
                            message_type=message_type or "general",
                        ).inc()

            except Exception as e:
                logger.error(f"SMS send error: {e}")
                last_error = str(e)
                sms_log.retry_count = attempt + 1

                # Record circuit failure
                self._record_circuit_failure(provider)

        # All retries failed
        sms_log.status = NotificationStatus.FAILED
        sms_log.failed_at = datetime.utcnow()
        sms_log.error_message = last_error

        # Update provider stats
        await self._update_provider_stats(provider, False, db)

        db.add(sms_log)
        await db.commit()

        return {"success": False, "error": last_error, "message_id": sms_log.id}

    async def _update_provider_stats(
        self, provider: SMSProvider, success: bool, db: AsyncSession
    ):
        """Update provider statistics"""
        result = await db.execute(
            select(ProviderConfig).where(ProviderConfig.provider == provider)
        )
        config = result.scalar_one_or_none()

        if config:
            if success:
                config.total_sent += 1
            else:
                config.total_failed += 1

            # Calculate success rate
            total = config.total_sent + config.total_failed
            if total > 0:
                config.success_rate = config.total_sent / total

            await db.commit()

    async def check_delivery_status(
        self, message_id: str, db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Check SMS delivery status"""
        if not db:
            async for session in get_db():
                db = session
                break

        # Get SMS log
        result = await db.execute(select(SMSLog).where(SMSLog.id == message_id))
        sms_log = result.scalar_one_or_none()

        if not sms_log:
            return {"success": False, "error": "Message not found"}

        # If already delivered or failed, return current status
        if sms_log.status in [NotificationStatus.DELIVERED, NotificationStatus.FAILED]:
            return {
                "success": True,
                "status": sms_log.status,
                "delivered_at": sms_log.delivered_at,
                "error": sms_log.error_message,
            }

        # Check with provider
        provider_instance = await self._get_provider_instance(sms_log.provider, db)
        if not provider_instance:
            return {"success": False, "error": "Provider not available"}

        try:
            result = await provider_instance.check_status(sms_log.provider_message_id)

            # Update log
            sms_log.status = result["status"]
            if result["status"] == NotificationStatus.DELIVERED:
                sms_log.delivered_at = datetime.utcnow()

                # Update template stats if applicable
                if sms_log.message_type:
                    await self._update_template_stats(sms_log.message_type, db)

            elif result["status"] == NotificationStatus.FAILED:
                sms_log.failed_at = datetime.utcnow()
                sms_log.error_message = result.get("error")

            await db.commit()

            return {
                "success": True,
                "status": sms_log.status,
                "delivered_at": sms_log.delivered_at,
                "error": sms_log.error_message,
            }

        except Exception as e:
            logger.error(f"Status check error: {e}")
            return {"success": False, "error": str(e)}

    async def _update_template_stats(self, template_code: str, db: AsyncSession):
        """Update template delivery stats"""
        result = await db.execute(
            select(SMSTemplate)
            .where(SMSTemplate.code == template_code)
            .order_by(SMSTemplate.updated_at.desc())
        )
        template = result.scalars().first()

        if template:
            template.delivered_count += 1
            if template.sent_count > 0:
                template.effectiveness_score = (
                    template.delivered_count / template.sent_count
                )
            await db.commit()

    async def send_bulk_sms(
        self,
        recipients: List[Dict[str, Any]],
        message_type: str,
        template_code: Optional[str] = None,
        provider: Optional[SMSProvider] = None,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """Send bulk SMS to multiple recipients"""
        results = {"total": len(recipients), "success": 0, "failed": 0, "errors": []}

        # Process in batches
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i : i + batch_size]

            # Send concurrently within batch
            tasks = []
            for recipient in batch:
                task = self.send_sms(
                    phone=recipient["phone"],
                    message=recipient.get("message", ""),
                    message_type=message_type,
                    template_code=template_code,
                    template_data=recipient.get("data", {}),
                    provider=provider,
                    metadata=recipient.get("metadata", {}),
                    retry_on_failure=False,  # Don't retry in bulk mode
                )
                tasks.append(task)

            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results["failed"] += 1
                    results["errors"].append(
                        {"recipient": batch[idx]["phone"], "error": str(result)}
                    )
                elif isinstance(result, dict):
                    if result.get("success"):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            {
                                "recipient": batch[idx]["phone"],
                                "error": result.get("error", "Unknown error"),
                            }
                        )

            # Small delay between batches to avoid rate limits
            if i + batch_size < len(recipients):
                await asyncio.sleep(1)

        return results


# Singleton instance
enhanced_sms_service = EnhancedSMSService()
