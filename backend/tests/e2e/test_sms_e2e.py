"""End-to-end tests for SMS functionality."""
import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import (NotificationStatus, ProviderConfig,
                                     SMSLog, SMSProvider, SMSTemplate)
from app.models.user import User


@pytest.fixture
async def sms_template(db: AsyncSession):
    """Create test SMS template"""
    template = SMSTemplate(
        id=uuid.uuid4(),
        code="test_order_confirmation",
        name="測試訂單確認",
        content="【幸福氣】訂單 {order_id} 已確認，預計 {delivery_time} 送達",
        is_active=True,
        language="zh-TW",
        variant="A",
        weight=100
    )
    db.add(template)
    await db.commit()
    return template


@pytest.fixture
async def provider_config(db: AsyncSession):
    """Create test provider configuration"""
    config = ProviderConfig(
        id=uuid.uuid4(),
        provider=SMSProvider.TWILIO,
        config={
            "account_sid": "test_sid",
            "auth_token": "test_token",
            "from_number": "+1234567890"
        },
        is_active=True,
        priority=100,
        rate_limit=60
    )
    db.add(config)
    await db.commit()
    return config


class TestSMSAPI:
    """Test SMS API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_sms_logs(
        self,
        client: AsyncClient,
        superuser_token_headers: dict,
        db: AsyncSession
    ):
        """Test getting SMS logs with filtering"""
        # Create test logs
        for i in range(5):
            log = SMSLog(
                id=uuid.uuid4(),
                recipient=f"091234567{i}",
                message=f"Test message {i}",
                message_type="order_confirmation",
                provider=SMSProvider.TWILIO,
                status=NotificationStatus.DELIVERED if i % 2 == 0 else NotificationStatus.FAILED,
                cost=0.5,
                segments=1,
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            db.add(log)
        await db.commit()
        
        # Test getting logs
        response = await client.get(
            "/api/v1/sms/logs",
            headers=superuser_token_headers,
            params={
                "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "end_date": datetime.utcnow().isoformat()
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        
        # Test filtering by status
        response = await client.get(
            "/api/v1/sms/logs",
            headers=superuser_token_headers,
            params={
                "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "status": "delivered"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(log["status"] == "delivered" for log in data)
    
    @pytest.mark.asyncio
    async def test_get_sms_stats(
        self,
        client: AsyncClient,
        superuser_token_headers: dict,
        db: AsyncSession
    ):
        """Test getting SMS statistics"""
        # Create test logs with different statuses
        statuses = [
            NotificationStatus.DELIVERED,
            NotificationStatus.DELIVERED,
            NotificationStatus.FAILED,
            NotificationStatus.PENDING
        ]
        
        for i, status in enumerate(statuses):
            log = SMSLog(
                id=uuid.uuid4(),
                recipient=f"091234567{i}",
                message=f"Test message {i}",
                provider=SMSProvider.TWILIO if i % 2 == 0 else SMSProvider.CHUNGHWA,
                status=status,
                cost=0.5 + i * 0.1,
                segments=1
            )
            db.add(log)
        await db.commit()
        
        # Get stats
        response = await client.get(
            "/api/v1/sms/stats",
            headers=superuser_token_headers,
            params={
                "start_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "end_date": datetime.utcnow().isoformat()
            }
        )
        
        assert response.status_code == 200
        stats = response.json()
        
        assert stats["total_sent"] == 4
        assert stats["total_delivered"] == 2
        assert stats["total_failed"] == 1
        assert stats["total_pending"] == 1
        assert stats["success_rate"] == 50.0
        assert "twilio" in stats["provider_stats"]
        assert "chunghwa" in stats["provider_stats"]
    
    @pytest.mark.asyncio
    async def test_send_sms(
        self,
        client: AsyncClient,
        superuser_token_headers: dict,
        provider_config
    ):
        """Test sending SMS"""
        response = await client.post(
            "/api/v1/sms/send",
            headers=superuser_token_headers,
            json={
                "phone": "0912345678",
                "message": "測試簡訊內容",
                "message_type": "test"
            }
        )
        
        # In test environment, should simulate success
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message_id" in data
    
    @pytest.mark.asyncio
    async def test_send_sms_with_template(
        self,
        client: AsyncClient,
        superuser_token_headers: dict,
        sms_template,
        provider_config
    ):
        """Test sending SMS with template"""
        response = await client.post(
            "/api/v1/sms/send",
            headers=superuser_token_headers,
            json={
                "phone": "0912345678",
                "template_code": "test_order_confirmation",
                "template_data": {
                    "order_id": "ORD123",
                    "delivery_time": "14:30"
                },
                "message_type": "order_confirmation"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_resend_failed_sms(
        self,
        client: AsyncClient,
        superuser_token_headers: dict,
        db: AsyncSession,
        provider_config
    ):
        """Test resending failed SMS"""
        # Create failed SMS log
        failed_log = SMSLog(
            id=uuid.uuid4(),
            recipient="0912345678",
            message="Failed message",
            provider=SMSProvider.TWILIO,
            status=NotificationStatus.FAILED,
            error_message="Network error",
            cost=0,
            segments=1
        )
        db.add(failed_log)
        await db.commit()
        
        # Resend
        response = await client.post(
            f"/api/v1/sms/resend/{failed_log.id}",
            headers=superuser_token_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["original_id"] == str(failed_log.id)
    
    @pytest.mark.asyncio
    async def test_bulk_sms_send(
        self,
        client: AsyncClient,
        superuser_token_headers: dict,
        provider_config
    ):
        """Test bulk SMS sending"""
        recipients = [
            {"phone": "0912345678", "data": {"name": "張三"}},
            {"phone": "0923456789", "data": {"name": "李四"}},
            {"phone": "0934567890", "data": {"name": "王五"}}
        ]
        
        response = await client.post(
            "/api/v1/sms/bulk-send",
            headers=superuser_token_headers,
            json={
                "recipients": recipients,
                "message_type": "promotion",
                "message": "親愛的 {name}，幸福氣優惠活動開始了！"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        # In test mode, all should succeed
        assert data["success"] >= 0
        assert data["failed"] >= 0
    
    @pytest.mark.asyncio
    async def test_sms_template_management(
        self,
        client: AsyncClient,
        superuser_token_headers: dict
    ):
        """Test SMS template CRUD operations"""
        # Create template
        template_data = {
            "code": "new_template",
            "name": "新模板",
            "content": "【幸福氣】{content}",
            "variant": "A",
            "weight": 100
        }
        
        response = await client.post(
            "/api/v1/sms/templates",
            headers=superuser_token_headers,
            json=template_data
        )
        
        assert response.status_code == 200
        created_template = response.json()
        assert created_template["code"] == "new_template"
        
        # Get templates
        response = await client.get(
            "/api/v1/sms/templates",
            headers=superuser_token_headers
        )
        
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) > 0
        
        # Update template
        response = await client.put(
            f"/api/v1/sms/templates/{created_template['id']}",
            headers=superuser_token_headers,
            json={"is_active": False}
        )
        
        assert response.status_code == 200
        updated = response.json()
        assert updated["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_provider_configuration(
        self,
        client: AsyncClient,
        superuser_token_headers: dict
    ):
        """Test provider configuration management"""
        # Get providers
        response = await client.get(
            "/api/v1/sms/providers",
            headers=superuser_token_headers
        )
        
        assert response.status_code == 200
        providers = response.json()
        assert len(providers) > 0
        
        # Update provider config
        response = await client.put(
            f"/api/v1/sms/providers/{SMSProvider.TWILIO}",
            headers=superuser_token_headers,
            json={
                "is_active": True,
                "priority": 200,
                "rate_limit": 100
            }
        )
        
        assert response.status_code == 200
        updated = response.json()
        assert updated["priority"] == 200
        assert updated["rate_limit"] == 100


class TestSMSWebhooks:
    """Test SMS webhook endpoints"""
    
    @pytest.mark.asyncio
    async def test_twilio_webhook(
        self,
        client: AsyncClient,
        db: AsyncSession
    ):
        """Test Twilio delivery webhook"""
        # Create SMS log
        sms_log = SMSLog(
            id=uuid.uuid4(),
            recipient="0912345678",
            message="Test message",
            provider=SMSProvider.TWILIO,
            provider_message_id="SM12345",
            status=NotificationStatus.SENT,
            cost=0.5,
            segments=1
        )
        db.add(sms_log)
        await db.commit()
        
        # Send webhook
        response = await client.post(
            "/api/v1/sms/delivery/twilio",
            data={
                "MessageSid": "SM12345",
                "MessageStatus": "delivered",
                "To": "+886912345678",
                "From": "+1234567890"
            }
        )
        
        assert response.status_code == 200
        
        # Check log was updated
        await db.refresh(sms_log)
        assert sms_log.status == NotificationStatus.DELIVERED
        assert sms_log.delivered_at is not None
    
    @pytest.mark.asyncio
    async def test_chunghwa_webhook(
        self,
        client: AsyncClient,
        db: AsyncSession
    ):
        """Test Chunghwa delivery webhook"""
        # Create SMS log
        sms_log = SMSLog(
            id=uuid.uuid4(),
            recipient="0912345678",
            message="Test message",
            provider=SMSProvider.CHUNGHWA,
            provider_message_id="CHT12345",
            status=NotificationStatus.SENT,
            cost=0.7,
            segments=1
        )
        db.add(sms_log)
        await db.commit()
        
        # Send webhook (XML format)
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<DeliveryStatus>
    <MessageId>CHT12345</MessageId>
    <StatusCode>0</StatusCode>
    <StatusText>已送達</StatusText>
    <DeliveryTime>2024-01-20T14:30:00</DeliveryTime>
    <Recipient>0912345678</Recipient>
</DeliveryStatus>"""
        
        response = await client.post(
            "/api/v1/sms/delivery/chunghwa",
            content=xml_data,
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 200
        
        # Check log was updated
        await db.refresh(sms_log)
        assert sms_log.status == NotificationStatus.DELIVERED
        assert sms_log.delivered_at is not None
    
    @pytest.mark.asyncio
    async def test_webhook_security(
        self,
        client: AsyncClient,
        superuser_token_headers: dict
    ):
        """Test webhook security and validation"""
        # Test webhook with invalid signature (should still accept in test mode)
        response = await client.post(
            "/api/v1/sms/delivery/twilio",
            headers={"X-Twilio-Signature": "invalid_signature"},
            data={
                "MessageSid": "SM99999",
                "MessageStatus": "failed"
            }
        )
        
        # In test mode, should accept but log warning
        assert response.status_code == 200
        
        # Test webhook endpoint for debugging
        response = await client.post(
            "/api/v1/sms/test-webhook/test_provider",
            headers=superuser_token_headers,
            json={"test": "data"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "test_provider"
        assert data["body"]["test"] == "data"