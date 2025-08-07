"""Unit tests for SMS Gateway functionality."""

import pytest

from app.models.notification import NotificationStatus, SMSProvider
from app.services.sms_gateway import SMSGateway
from app.services.sms_providers.chunghwa import ChunghwaProvider
from app.services.sms_providers.twilio import TwilioProvider
from unittest.mock import patch
from unittest.mock import AsyncMock


@pytest.fixture
def sms_gateway():
    """Create SMS gateway instance for testing"""
    gateway = SMSGateway()
    return gateway


@pytest.fixture
def mock_twilio_provider():
    """Create mock Twilio provider"""
    provider = AsyncMock(spec=TwilioProvider)
    provider.send_sms = AsyncMock(
        return_value={
            "success": True,
            "message_id": "SM12345",
            "segments": 1,
            "cost": 0.50,
        }
    )
    provider.check_status = AsyncMock(
        return_value={"success": True, "status": NotificationStatus.DELIVERED}
    )
    provider.health_check = AsyncMock(
        return_value={"healthy": True, "success_rate": 0.99}
    )
    return provider


@pytest.fixture
def mock_chunghwa_provider():
    """Create mock Chunghwa provider"""
    provider = AsyncMock(spec=ChunghwaProvider)
    provider.send_sms = AsyncMock(
        return_value={
            "success": True,
            "message_id": "CHT12345",
            "segments": 1,
            "cost": 0.70,
        }
    )
    provider.check_status = AsyncMock(
        return_value={"success": True, "status": NotificationStatus.DELIVERED}
    )
    provider.health_check = AsyncMock(return_value={"healthy": True, "balance": 1000})
    return provider


class TestSMSGateway:
    """Test SMS Gateway functionality"""

    @pytest.mark.asyncio
    async def test_initialize_gateway(self, sms_gateway):
        """Test gateway initialization"""
        with patch("app.core.config.settings.SMS_TWILIO_ENABLED", True):
            with patch("app.core.config.settings.SMS_CHUNGHWA_ENABLED", True):
                await sms_gateway.initialize()

                assert SMSProvider.TWILIO in sms_gateway._providers
                assert SMSProvider.CHUNGHWA in sms_gateway._providers

    @pytest.mark.asyncio
    async def test_send_sms_primary_provider(self, sms_gateway, mock_twilio_provider):
        """Test sending SMS with primary provider"""
        sms_gateway._providers = {SMSProvider.TWILIO: mock_twilio_provider}
        sms_gateway._primary_provider = SMSProvider.TWILIO

        result = await sms_gateway.send_sms(phone="0912345678", message="測試簡訊")

        assert result["success"] is True
        assert result["message_id"] == "SM12345"
        assert result["provider"] == SMSProvider.TWILIO
        mock_twilio_provider.send_sms.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_sms_fallback_provider(
        self, sms_gateway, mock_twilio_provider, mock_chunghwa_provider
    ):
        """Test fallback to secondary provider when primary fails"""
        # Make Twilio fail
        mock_twilio_provider.send_sms.return_value = {
            "success": False,
            "error": "Network error",
        }

        sms_gateway._providers = {
            SMSProvider.TWILIO: mock_twilio_provider,
            SMSProvider.CHUNGHWA: mock_chunghwa_provider,
        }
        sms_gateway._primary_provider = SMSProvider.TWILIO
        sms_gateway._fallback_providers = [SMSProvider.CHUNGHWA]

        result = await sms_gateway.send_sms(phone="0912345678", message="測試簡訊")

        assert result["success"] is True
        assert result["provider"] == SMSProvider.CHUNGHWA
        mock_twilio_provider.send_sms.assert_called_once()
        mock_chunghwa_provider.send_sms.assert_called_once()

    @pytest.mark.asyncio
    async def test_phone_number_formatting(self, sms_gateway):
        """Test Taiwan phone number formatting"""
        test_cases = [
            ("0912345678", "886912345678"),
            ("886912345678", "886912345678"),
            ("912345678", "886912345678"),
            ("+886912345678", "+886912345678"),
        ]

        for input_phone, expected in test_cases:
            formatted = sms_gateway._format_phone_number(input_phone)
            assert formatted == expected.replace("+", "")

    @pytest.mark.asyncio
    async def test_rate_limiting(self, sms_gateway):
        """Test rate limiting functionality"""
        # Test initial state
        assert await sms_gateway._check_rate_limit(SMSProvider.TWILIO, "normal") is True

        # Update rate limit
        await sms_gateway._update_rate_limit(SMSProvider.TWILIO)

        # Should still allow within limit
        assert await sms_gateway._check_rate_limit(SMSProvider.TWILIO, "normal") is True

        # Test priority boost
        assert await sms_gateway._check_rate_limit(SMSProvider.TWILIO, "high") is True

    @pytest.mark.asyncio
    async def test_template_rendering(self, sms_gateway):
        """Test message template rendering"""
        template_id = "order_confirmation"
        variables = {"order_id": "ORD123", "delivery_time": "14:30"}

        message = await sms_gateway._render_template(template_id, variables)

        assert "ORD123" in message
        assert "14:30" in message
        assert "幸福氣" in message

    @pytest.mark.asyncio
    async def test_health_checks(
        self, sms_gateway, mock_twilio_provider, mock_chunghwa_provider
    ):
        """Test provider health checks"""
        sms_gateway._providers = {
            SMSProvider.TWILIO: mock_twilio_provider,
            SMSProvider.CHUNGHWA: mock_chunghwa_provider,
        }

        health_results = await sms_gateway.perform_health_checks()

        assert health_results[SMSProvider.TWILIO]["healthy"] is True
        assert health_results[SMSProvider.CHUNGHWA]["healthy"] is True
        mock_twilio_provider.health_check.assert_called_once()
        mock_chunghwa_provider.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_providers_fail(
        self, sms_gateway, mock_twilio_provider, mock_chunghwa_provider
    ):
        """Test when all providers fail"""
        # Make both providers fail
        mock_twilio_provider.send_sms.return_value = {
            "success": False,
            "error": "Authentication failed",
        }
        mock_chunghwa_provider.send_sms.return_value = {
            "success": False,
            "error": "Insufficient balance",
        }

        sms_gateway._providers = {
            SMSProvider.TWILIO: mock_twilio_provider,
            SMSProvider.CHUNGHWA: mock_chunghwa_provider,
        }
        sms_gateway._primary_provider = SMSProvider.TWILIO
        sms_gateway._fallback_providers = [SMSProvider.CHUNGHWA]

        result = await sms_gateway.send_sms(phone="0912345678", message="測試簡訊")

        assert result["success"] is False
        assert "All SMS providers failed" in result["error"]
        assert result["providers_tried"] == [SMSProvider.TWILIO, SMSProvider.CHUNGHWA]


class TestTwilioProvider:
    """Test Twilio provider functionality"""

    @pytest.mark.asyncio
    async def test_calculate_segments_unicode(self):
        """Test segment calculation for Chinese text"""
        provider = TwilioProvider()

        # Single segment (70 chars)
        message = "測試" * 35  # 70 Chinese characters
        assert provider._calculate_segments(message) == 1

        # Multiple segments
        message = "測試" * 40  # 80 Chinese characters
        assert provider._calculate_segments(message) == 2

    @pytest.mark.asyncio
    async def test_calculate_segments_ascii(self):
        """Test segment calculation for ASCII text"""
        provider = TwilioProvider()

        # Single segment (160 chars)
        message = "a" * 160
        assert provider._calculate_segments(message) == 1

        # Multiple segments
        message = "a" * 200
        assert provider._calculate_segments(message) == 2


class TestChunghwaProvider:
    """Test Chunghwa provider functionality"""

    def test_create_signature(self):
        """Test signature creation"""
        provider = ChunghwaProvider()
        provider.account_id = "test_account"
        provider.password = "test_password"

        timestamp = 1234567890
        signature = provider._create_signature(timestamp)

        # Should be MD5 hash
        assert len(signature) == 32
        assert all(c in "0123456789abcde" for c in signature)

    def test_error_message_mapping(self):
        """Test error message mapping"""
        provider = ChunghwaProvider()

        assert "認證失敗" in provider._get_error_message("1")
        assert "餘額不足" in provider._get_error_message("4")
        assert "未知錯誤" in provider._get_error_message("999")
