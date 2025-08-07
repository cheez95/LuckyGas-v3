"""Tests for enhanced SMS service."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.notification import (
    NotificationStatus,
    ProviderConfig,
    SMSLog,
    SMSProvider,
    SMSTemplate,
)
from app.services.sms_service import (
    EnhancedSMSService,
    Every8dProvider,
    MitakeProvider,
    SMSProviderBase,
    TwilioProvider,
)


class TestSMSProviderBase:
    """Test base SMS provider functionality"""

    def test_calculate_segments_unicode(self):
        """Test segment calculation for Unicode (Chinese) messages"""
        provider = SMSProviderBase({})

        # Single segment Unicode (≤70 chars)
        assert provider.calculate_segments("測試簡訊" * 10) == 1  # 40 chars
        assert provider.calculate_segments("測" * 70) == 1

        # Multi - segment Unicode (>70 chars, 67 per segment)
        assert provider.calculate_segments("測" * 71) == 2
        assert provider.calculate_segments("測" * 134) == 2
        assert provider.calculate_segments("測" * 135) == 3

    def test_calculate_segments_gsm(self):
        """Test segment calculation for GSM 7 - bit messages"""
        provider = SMSProviderBase({})

        # Single segment GSM (≤160 chars)
        assert provider.calculate_segments("Hello World" * 10) == 1  # 110 chars
        assert provider.calculate_segments("a" * 160) == 1

        # Multi - segment GSM (>160 chars, 153 per segment)
        assert provider.calculate_segments("a" * 161) == 2
        assert provider.calculate_segments("a" * 306) == 2
        assert provider.calculate_segments("a" * 307) == 3


class TestTwilioProvider:
    """Test Twilio SMS provider"""

    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test successful SMS send via Twilio"""
        config = {
            "account_sid": "test_sid",
            "auth_token": "test_token",
            "from_number": "+886912345678",
        }
        provider = TwilioProvider(config)

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(
            return_value={"sid": "SM123456", "price": "-0.08"}  # USD
        )

        with patch("aiohttp.ClientSession.post", return_value=mock_response):
            result = await provider.send_sms("0912345678", "測試訊息")

        assert result["success"] is True
        assert result["message_id"] == "SM123456"
        assert result["segments"] == 1
        assert result["cost"] == 2.4  # 0.08 * 30

    @pytest.mark.asyncio
    async def test_send_sms_failure(self):
        """Test SMS send failure via Twilio"""
        config = {
            "account_sid": "test_sid",
            "auth_token": "test_token",
            "from_number": "+886912345678",
        }
        provider = TwilioProvider(config)

        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"message": "Invalid phone number"})

        with patch("aiohttp.ClientSession.post", return_value=mock_response):
            result = await provider.send_sms("invalid", "測試訊息")

        assert result["success"] is False
        assert "Invalid phone number" in result["error"]

    @pytest.mark.asyncio
    async def test_check_status(self):
        """Test message status check"""
        config = {"account_sid": "test_sid", "auth_token": "test_token"}
        provider = TwilioProvider(config)

        # Mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"status": "delivered"})

        with patch("aiohttp.ClientSession.get", return_value=mock_response):
            result = await provider.check_status("SM123456")

        assert result["status"] == NotificationStatus.DELIVERED
        assert result["error"] is None


class TestEvery8dProvider:
    """Test Every8d SMS provider"""

    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test successful SMS send via Every8d"""
        config = {
            "username": "test_user",
            "password": "test_pass",
            "api_url": "https://api.e8d.tw / SMS / BulkSMS",
        }
        provider = Every8dProvider(config)

        # Mock response (format: credit, sended, cost, unsend, batch_id)
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="100.0, 1, 1.5, 0, BATCH123")

        with patch("aiohttp.ClientSession.get", return_value=mock_response):
            result = await provider.send_sms("0912345678", "測試訊息")

        assert result["success"] is True
        assert result["message_id"] == "BATCH123"
        assert result["cost"] == 1.5

    @pytest.mark.asyncio
    async def test_send_sms_insufficient_balance(self):
        """Test SMS send with insufficient balance"""
        config = {"username": "test_user", "password": "test_pass"}
        provider = Every8dProvider(config)

        # Mock error response
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="-6")

        with patch("aiohttp.ClientSession.get", return_value=mock_response):
            result = await provider.send_sms("0912345678", "測試訊息")

        assert result["success"] is False
        assert "Insufficient balance" in result["error"]

    @pytest.mark.asyncio
    async def test_phone_formatting(self):
        """Test phone number formatting for Taiwan"""
        config = {"username": "test", "password": "test"}
        provider = Every8dProvider(config)

        # Test various phone formats
        test_cases = [
            ("+886912345678", "0912345678"),
            ("886912345678", "0912345678"),
            ("0912345678", "0912345678"),
            ("912345678", "0912345678"),
        ]

        for input_phone, expected in test_cases:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value="100, 1, 1.5, 0, BATCH123")

            with patch(
                "aiohttp.ClientSession.get", return_value=mock_response
            ) as mock_get:
                await provider.send_sms(input_phone, "test")

                # Check that the formatted phone was used
                call_args = mock_get.call_args
                params = call_args[1]["params"]
                assert params["DEST"] == expected


class TestMitakeProvider:
    """Test Mitake SMS provider"""

    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test successful SMS send via Mitake"""
        config = {
            "username": "test_user",
            "password": "test_pass",
            "api_url": "https://api.mitake.com.tw / api / mtk / SmSend",
        }
        provider = MitakeProvider(config)

        # Mock INI response
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(
            return_value="""[0]
msgid=1234567890
statuscode=0
AccountPoint=98.5"""
        )

        with patch("aiohttp.ClientSession.post", return_value=mock_response):
            result = await provider.send_sms("0912345678", "測試訊息")

        assert result["success"] is True
        assert result["message_id"] == "1234567890"
        assert result["cost"] == 98.5

    @pytest.mark.asyncio
    async def test_send_sms_invalid_recipient(self):
        """Test SMS send with invalid recipient"""
        config = {"username": "test_user", "password": "test_pass"}
        provider = MitakeProvider(config)

        # Mock error response
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(
            return_value="""[0]
statuscode=3
Error=Invalid recipient"""
        )

        with patch("aiohttp.ClientSession.post", return_value=mock_response):
            result = await provider.send_sms("invalid", "測試訊息")

        assert result["success"] is False
        assert "Invalid recipient" in result["error"]

    @pytest.mark.asyncio
    async def test_check_status_delivered(self):
        """Test status check for delivered message"""
        config = {"username": "test_user", "password": "test_pass"}
        provider = MitakeProvider(config)

        # Mock status response
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="statuscode=0\nstatusstr=0")

        with patch("aiohttp.ClientSession.get", return_value=mock_response):
            result = await provider.check_status("1234567890")

        assert result["status"] == NotificationStatus.DELIVERED
        assert result["error"] is None


class TestEnhancedSMSService:
    """Test enhanced SMS service"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def mock_provider_config(self):
        """Create mock provider configuration"""
        config = MagicMock(spec=ProviderConfig)
        config.provider = SMSProvider.TWILIO
        config.config = {
            "account_sid": "test_sid",
            "auth_token": "test_token",
            "from_number": "+886912345678",
        }
        config.is_active = True
        config.priority = 10
        config.rate_limit = 100
        config.success_rate = 0.95
        return config

    @pytest.mark.asyncio
    async def test_send_sms_success(self, mock_db, mock_provider_config):
        """Test successful SMS send"""
        service = EnhancedSMSService()

        # Mock provider config query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_provider_config
        mock_result.scalars().all.return_value = [mock_provider_config]
        mock_db.execute.return_value = mock_result

        # Mock provider send
        with patch.object(
            TwilioProvider,
            "send_sms",
            return_value={
                "success": True,
                "message_id": "SM123456",
                "segments": 1,
                "cost": 1.5,
            },
        ):
            result = await service.send_sms(
                phone="0912345678",
                message="測試訊息",
                message_type="test",
                metadata={"test": "data"},
                db=mock_db,
            )

        assert result["success"] is True
        assert "message_id" in result
        assert result["segments"] == 1
        assert result["cost"] == 1.5

        # Verify SMS log was created
        assert mock_db.add.called
        sms_log = mock_db.add.call_args[0][0]
        assert isinstance(sms_log, SMSLog)
        assert sms_log.recipient == "0912345678"
        assert sms_log.message == "測試訊息"
        assert sms_log.status == NotificationStatus.SENT

    @pytest.mark.asyncio
    async def test_send_sms_with_template(self, mock_db, mock_provider_config):
        """Test SMS send with template"""
        service = EnhancedSMSService()

        # Mock template
        mock_template = MagicMock(spec=SMSTemplate)
        mock_template.content = "訂單 {order_id} 已確認"
        mock_template.weight = 100
        mock_template.sent_count = 0

        # Mock queries
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_provider_config
        mock_result.scalars().all.side_effect = [
            [mock_template],  # Template query
            [mock_provider_config],  # Provider query
        ]
        mock_db.execute.return_value = mock_result

        # Mock provider send
        with patch.object(
            TwilioProvider,
            "send_sms",
            return_value={
                "success": True,
                "message_id": "SM123456",
                "segments": 1,
                "cost": 1.5,
            },
        ) as mock_send:
            result = await service.send_sms(
                phone="0912345678",
                message="",  # Empty message
                template_code="order_confirmation",
                template_data={"order_id": "ORD - 123"},
                db=mock_db,
            )

        # Verify template was used
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert args[1] == "訂單 ORD - 123 已確認"

        # Verify template count was incremented
        assert mock_template.sent_count == 1

    @pytest.mark.asyncio
    async def test_send_sms_retry_on_failure(self, mock_db, mock_provider_config):
        """Test SMS retry on failure"""
        service = EnhancedSMSService()

        # Mock multiple provider configs
        mock_provider_config2 = MagicMock(spec=ProviderConfig)
        mock_provider_config2.provider = SMSProvider.EVERY8D
        mock_provider_config2.config = {"username": "test", "password": "test"}
        mock_provider_config2.is_active = True
        mock_provider_config2.priority = 5
        mock_provider_config2.rate_limit = None
        mock_provider_config2.success_rate = 0.90

        # Mock queries
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [
            mock_provider_config,
            mock_provider_config2,
        ]
        mock_result.scalars().all.side_effect = [
            [mock_provider_config, mock_provider_config2],  # First best provider
            [mock_provider_config2],  # Second best provider after first fails
        ]
        mock_db.execute.return_value = mock_result

        # Mock first provider fails, second succeeds
        with patch.object(
            TwilioProvider,
            "send_sms",
            return_value={"success": False, "error": "Network error"},
        ):
            with patch.object(
                Every8dProvider,
                "send_sms",
                return_value={
                    "success": True,
                    "message_id": "BATCH123",
                    "segments": 1,
                    "cost": 1.5,
                },
            ):
                result = await service.send_sms(
                    phone="0912345678",
                    message="測試訊息",
                    retry_on_failure=True,
                    db=mock_db,
                )

        assert result["success"] is True
        assert result["message_id"] is not None

        # Verify retry count
        sms_log = mock_db.add.call_args[0][0]
        assert sms_log.retry_count == 1
        assert sms_log.provider == SMSProvider.EVERY8D

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_db, mock_provider_config):
        """Test rate limiting"""
        service = EnhancedSMSService()

        # Set low rate limit
        mock_provider_config.rate_limit = 2  # 2 per minute

        # Mock queries
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_provider_config
        mock_result.scalars().all.return_value = [mock_provider_config]
        mock_db.execute.return_value = mock_result

        # Send messages up to rate limit
        with patch.object(
            TwilioProvider,
            "send_sms",
            return_value={
                "success": True,
                "message_id": "SM123456",
                "segments": 1,
                "cost": 1.5,
            },
        ):
            # First two should succeed
            for i in range(2):
                result = await service.send_sms(
                    phone="0912345678", message=f"Message {i}", db=mock_db
                )
                assert result["success"] is True

            # Third should fail due to rate limit
            mock_result.scalars().all.return_value = []  # No available providers
            result = await service.send_sms(
                phone="0912345678", message="Message 3", db=mock_db
            )
            assert result["success"] is False
            assert "No available SMS providers" in result["error"]

    @pytest.mark.asyncio
    async def test_check_delivery_status(self, mock_db):
        """Test delivery status check"""
        service = EnhancedSMSService()

        # Mock SMS log
        mock_sms_log = MagicMock(spec=SMSLog)
        mock_sms_log.id = uuid4()
        mock_sms_log.status = NotificationStatus.SENT
        mock_sms_log.provider = SMSProvider.TWILIO
        mock_sms_log.provider_message_id = "SM123456"
        mock_sms_log.delivered_at = None
        mock_sms_log.error_message = None

        # Mock provider config
        mock_provider_config = MagicMock(spec=ProviderConfig)
        mock_provider_config.provider = SMSProvider.TWILIO
        mock_provider_config.config = {
            "account_sid": "test_sid",
            "auth_token": "test_token",
        }
        mock_provider_config.is_active = True

        # Mock queries
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [
            mock_sms_log,  # SMS log query
            mock_provider_config,  # Provider config query
        ]
        mock_db.execute.return_value = mock_result

        # Mock provider status check
        with patch.object(
            TwilioProvider,
            "check_status",
            return_value={"status": NotificationStatus.DELIVERED, "error": None},
        ):
            result = await service.check_delivery_status(
                str(mock_sms_log.id), db=mock_db
            )

        assert result["success"] is True
        assert result["status"] == NotificationStatus.DELIVERED

        # Verify status was updated
        assert mock_sms_log.status == NotificationStatus.DELIVERED
        assert mock_sms_log.delivered_at is not None

    @pytest.mark.asyncio
    async def test_send_bulk_sms(self, mock_db, mock_provider_config):
        """Test bulk SMS sending"""
        service = EnhancedSMSService()

        # Mock queries
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_provider_config
        mock_result.scalars().all.return_value = [mock_provider_config]
        mock_db.execute.return_value = mock_result

        # Prepare recipients
        recipients = [
            {"phone": "0912345678", "data": {"name": "張三"}},
            {"phone": "0923456789", "data": {"name": "李四"}},
            {"phone": "0934567890", "data": {"name": "王五"}},
        ]

        # Mock provider send
        send_count = 0

        async def mock_send(phone, message):
            nonlocal send_count
            send_count += 1
            if send_count == 2:
                # Make second one fail
                return {"success": False, "error": "Test error"}
            return {
                "success": True,
                "message_id": f"SM{send_count}",
                "segments": 1,
                "cost": 1.5,
            }

        with patch.object(TwilioProvider, "send_sms", side_effect=mock_send):
            result = await service.send_bulk_sms(
                recipients=recipients, message_type="marketing", batch_size=2
            )

        assert result["total"] == 3
        assert result["success"] == 2
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["recipient"] == "0923456789"


@pytest.mark.asyncio
async def test_taiwanese_phone_validation():
    """Test Taiwan phone number validation in schema"""
    from app.schemas.notification import SMSSendRequest

    # Valid mobile numbers
    valid_mobiles = ["0912345678", "0912 - 345 - 678", "0912 345 678", "+886912345678"]

    for phone in valid_mobiles:
        request = SMSSendRequest(phone=phone, message="test")
        assert request.phone.replace("-", "").replace(" ", "") in [
            "0912345678",
            "+886912345678",
        ]

    # Valid landline numbers
    valid_landlines = [
        "022345678",  # Taipei
        "02 - 2345 - 6789",
        "073456789",  # Kaohsiung
        "+886223456789",
    ]

    for phone in valid_landlines:
        request = SMSSendRequest(phone=phone, message="test")
        # Should not raise validation error

    # Invalid numbers
    invalid_numbers = [
        "12345",  # Too short
        "0812345678",  # Invalid prefix
        "091234567",  # Too short mobile
        "09123456789",  # Too long mobile
    ]

    for phone in invalid_numbers:
        with pytest.raises(ValueError, match="Invalid Taiwan phone number"):
            SMSSendRequest(phone=phone, message="test")
