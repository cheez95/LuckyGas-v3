"""Tests for notification API endpoints."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.notification import NotificationChannel, NotificationStatus, SMSProvider


class TestSMSEndpoints:
    """Test SMS notification endpoints"""

    @pytest.mark.asyncio
    async def test_send_sms_success(self, async_client, test_token_headers_manager):
        """Test successful SMS send"""
        with patch(
            "app.services.sms_service.enhanced_sms_service.send_sms"
        ) as mock_send:
            mock_send.return_value = {
                "success": True,
                "message_id": str(uuid4()),
                "provider_message_id": "SM123456",
                "segments": 1,
                "cost": 1.5,
            }

            response = await async_client.post(
                "/api/v1/notifications/send-sms",
                headers=test_token_headers_manager,
                json={
                    "phone": "0912345678",
                    "message": "測試簡訊",
                    "message_type": "test",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message_id" in data
        assert data["segments"] == 1
        assert data["cost"] == 1.5

    @pytest.mark.asyncio
    async def test_send_sms_with_template(
        self, async_client, test_token_headers_manager
    ):
        """Test SMS send with template"""
        with patch(
            "app.services.sms_service.enhanced_sms_service.send_sms"
        ) as mock_send:
            mock_send.return_value = {
                "success": True,
                "message_id": str(uuid4()),
                "segments": 1,
                "cost": 1.5,
            }

            response = await async_client.post(
                "/api/v1/notifications/send-sms",
                headers=test_token_headers_manager,
                json={
                    "phone": "0912345678",
                    "template_code": "order_confirmation",
                    "template_data": {
                        "order_number": "ORD-123",
                        "delivery_time": "今天下午2點",
                    },
                },
            )

        assert response.status_code == 200

        # Verify template data was passed
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.kwargs["template_code"] == "order_confirmation"
        assert call_args.kwargs["template_data"]["order_number"] == "ORD-123"

    @pytest.mark.asyncio
    async def test_send_sms_invalid_phone(
        self, async_client, test_token_headers_manager
    ):
        """Test SMS send with invalid phone number"""
        response = await async_client.post(
            "/api/v1/notifications/send-sms",
            headers=test_token_headers_manager,
            json={"phone": "123456", "message": "測試簡訊"},  # Invalid
        )

        assert response.status_code == 422
        assert "Invalid Taiwan phone number" in str(response.json())

    @pytest.mark.asyncio
    async def test_send_sms_permission_denied(
        self, async_client, test_token_headers_driver
    ):
        """Test SMS send permission for driver role"""
        response = await async_client.post(
            "/api/v1/notifications/send-sms",
            headers=test_token_headers_driver,
            json={"phone": "0912345678", "message": "測試簡訊"},
        )

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_sms_status(self, async_client, test_token_headers_manager):
        """Test SMS status check"""
        message_id = uuid4()

        with patch(
            "app.services.sms_service.enhanced_sms_service.check_delivery_status"
        ) as mock_check:
            mock_check.return_value = {
                "success": True,
                "status": NotificationStatus.DELIVERED,
                "delivered_at": datetime.utcnow(),
                "error": None,
            }

            response = await async_client.get(
                f"/api/v1/notifications/sms-status/{message_id}",
                headers=test_token_headers_manager,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "delivered"
        assert data["delivered_at"] is not None

    @pytest.mark.asyncio
    async def test_send_bulk_sms(self, async_client, test_token_headers_manager):
        """Test bulk SMS send"""
        with patch(
            "app.services.sms_service.enhanced_sms_service.send_bulk_sms"
        ) as mock_bulk:
            mock_bulk.return_value = {
                "total": 3,
                "success": 2,
                "failed": 1,
                "errors": [{"recipient": "0934567890", "error": "Invalid number"}],
            }

            response = await async_client.post(
                "/api/v1/notifications/send-bulk-sms",
                headers=test_token_headers_manager,
                json={
                    "recipients": [
                        {"phone": "0912345678", "template_data": {"name": "張三"}},
                        {"phone": "0923456789", "template_data": {"name": "李四"}},
                        {"phone": "0934567890", "template_data": {"name": "王五"}},
                    ],
                    "message_type": "marketing",
                    "default_message": "優惠訊息",
                    "batch_name": "2025年1月促銷",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success"] == 2
        assert data["failed"] == 1
        assert len(data["errors"]) == 1


class TestSMSTemplateEndpoints:
    """Test SMS template management endpoints"""

    @pytest.mark.asyncio
    async def test_create_template(
        self, async_client, test_token_headers_manager, test_db
    ):
        """Test create SMS template"""
        response = await async_client.post(
            "/api/v1/notifications/sms-templates",
            headers=test_token_headers_manager,
            json={
                "code": "new_customer_welcome",
                "name": "新客戶歡迎",
                "content": "【幸福氣】歡迎 {name} 成為我們的新客戶！首次訂購享9折優惠。",
                "description": "新客戶註冊歡迎簡訊",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "new_customer_welcome"
        assert data["name"] == "新客戶歡迎"
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_duplicate_template(
        self, async_client, test_token_headers_manager, test_db
    ):
        """Test create duplicate template code"""
        # Create first template
        await async_client.post(
            "/api/v1/notifications/sms-templates",
            headers=test_token_headers_manager,
            json={"code": "duplicate_test", "name": "Test", "content": "Test"},
        )

        # Try to create duplicate
        response = await async_client.post(
            "/api/v1/notifications/sms-templates",
            headers=test_token_headers_manager,
            json={"code": "duplicate_test", "name": "Test 2", "content": "Test 2"},
        )

        assert response.status_code == 400
        assert "Template code already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_templates(
        self, async_client, test_token_headers_manager, test_db
    ):
        """Test list SMS templates"""
        # Create test templates
        templates = [
            {"code": "test1", "name": "測試1", "content": "內容1", "is_active": True},
            {"code": "test2", "name": "測試2", "content": "內容2", "is_active": False},
            {"code": "test3", "name": "測試3", "content": "內容3", "is_active": True},
        ]

        for template in templates:
            await async_client.post(
                "/api/v1/notifications/sms-templates",
                headers=test_token_headers_manager,
                json=template,
            )

        # List all templates
        response = await async_client.get(
            "/api/v1/notifications/sms-templates", headers=test_token_headers_manager
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

        # List only active templates
        response = await async_client.get(
            "/api/v1/notifications/sms-templates?is_active=true",
            headers=test_token_headers_manager,
        )

        assert response.status_code == 200
        data = response.json()
        active_count = sum(1 for t in data if t["is_active"])
        assert active_count >= 2

    @pytest.mark.asyncio
    async def test_update_template(
        self, async_client, test_token_headers_manager, test_db
    ):
        """Test update SMS template"""
        # Create template
        create_response = await async_client.post(
            "/api/v1/notifications/sms-templates",
            headers=test_token_headers_manager,
            json={"code": "update_test", "name": "原始名稱", "content": "原始內容"},
        )

        template_id = create_response.json()["id"]

        # Update template
        response = await async_client.put(
            f"/api/v1/notifications/sms-templates/{template_id}",
            headers=test_token_headers_manager,
            json={
                "name": "更新後名稱",
                "content": "更新後內容 {name}",
                "is_active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新後名稱"
        assert data["content"] == "更新後內容 {name}"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_template(
        self, async_client, test_token_headers_admin, test_db
    ):
        """Test delete SMS template (admin only)"""
        # Create template
        create_response = await async_client.post(
            "/api/v1/notifications/sms-templates",
            headers=test_token_headers_admin,
            json={"code": "delete_test", "name": "刪除測試", "content": "測試內容"},
        )

        template_id = create_response.json()["id"]

        # Delete template
        response = await async_client.delete(
            f"/api/v1/notifications/sms-templates/{template_id}",
            headers=test_token_headers_admin,
        )

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify deletion
        get_response = await async_client.get(
            "/api/v1/notifications/sms-templates", headers=test_token_headers_admin
        )

        templates = get_response.json()
        assert not any(t["id"] == template_id for t in templates)


class TestProviderConfigEndpoints:
    """Test SMS provider configuration endpoints"""

    @pytest.mark.asyncio
    async def test_create_provider_config(self, async_client, test_token_headers_admin):
        """Test create provider configuration (admin only)"""
        response = await async_client.post(
            "/api/v1/notifications/providers",
            headers=test_token_headers_admin,
            json={
                "provider": "twilio",
                "config": {
                    "account_sid": "test_sid",
                    "auth_token": "test_token",
                    "from_number": "+886912345678",
                },
                "priority": 10,
                "rate_limit": 60,
                "cost_per_message": 2.5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "twilio"
        assert data["priority"] == 10
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_provider_configs(
        self, async_client, test_token_headers_manager, test_db
    ):
        """Test list provider configurations"""
        # Create test config
        await async_client.post(
            "/api/v1/notifications/providers",
            headers=test_token_headers_manager,
            json={
                "provider": "every8d",
                "config": {"username": "test", "password": "secret"},
            },
        )

        response = await async_client.get(
            "/api/v1/notifications/providers", headers=test_token_headers_manager
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        # Manager should see masked config
        for provider in data:
            if "password" in provider["config"]:
                assert provider["config"]["password"] == "***"

    @pytest.mark.asyncio
    async def test_update_provider_config(
        self, async_client, test_token_headers_admin, test_db
    ):
        """Test update provider configuration"""
        # Create config
        await async_client.post(
            "/api/v1/notifications/providers",
            headers=test_token_headers_admin,
            json={
                "provider": "mitake",
                "config": {"username": "old", "password": "old"},
            },
        )

        # Update config
        response = await async_client.put(
            "/api/v1/notifications/providers/mitake",
            headers=test_token_headers_admin,
            json={
                "config": {"username": "new", "password": "new"},
                "priority": 20,
                "is_active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["config"]["username"] == "new"
        assert data["priority"] == 20
        assert data["is_active"] is False


class TestSMSLogsEndpoints:
    """Test SMS logs and analytics endpoints"""

    @pytest.mark.asyncio
    async def test_list_sms_logs(
        self, async_client, test_token_headers_manager, test_db
    ):
        """Test list SMS logs with filtering"""
        # Create test logs by sending SMS
        with patch(
            "app.services.sms_service.enhanced_sms_service.send_sms"
        ) as mock_send:
            mock_send.return_value = {"success": True, "message_id": str(uuid4())}

            # Send test messages
            for i in range(5):
                await async_client.post(
                    "/api/v1/notifications/send-sms",
                    headers=test_token_headers_manager,
                    json={"phone": f"091234567{i}", "message": f"測試 {i}"},
                )

        # Get all logs
        response = await async_client.get(
            "/api/v1/notifications/sms-logs", headers=test_token_headers_manager
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5

        # Filter by recipient
        response = await async_client.get(
            "/api/v1/notifications/sms-logs?recipient=0912345671",
            headers=test_token_headers_manager,
        )

        assert response.status_code == 200
        data = response.json()
        assert any("0912345671" in log["recipient"] for log in data)

    @pytest.mark.asyncio
    async def test_get_notification_stats(
        self, async_client, test_token_headers_manager
    ):
        """Test notification statistics endpoint"""
        with patch("app.core.database.get_db") as mock_get_db:
            # Mock database results
            mock_db = AsyncMock()
            mock_result = AsyncMock()

            # Mock SMS stats
            mock_sms_stats = AsyncMock()
            mock_sms_stats.total = 100
            mock_sms_stats.sent = 90
            mock_sms_stats.delivered = 85
            mock_sms_stats.failed = 10
            mock_sms_stats.total_cost = 150.0
            mock_sms_stats.total_segments = 120

            mock_result.one.return_value = mock_sms_stats
            mock_db.execute.return_value = mock_result

            # Mock provider stats
            mock_provider_stats = [
                AsyncMock(provider="twilio", count=50, cost=75.0, delivered=45),
                AsyncMock(provider="every8d", count=50, cost=75.0, delivered=40),
            ]

            mock_result2 = AsyncMock()
            mock_result2.__iter__ = lambda self: iter(mock_provider_stats)

            mock_db.execute.side_effect = [mock_result, mock_result2]
            mock_get_db.return_value.__aiter__.return_value = [mock_db]

            response = await async_client.get(
                "/api/v1/notifications/stats", headers=test_token_headers_manager
            )

        assert response.status_code == 200
        data = response.json()

        # Check SMS stats
        assert data["sms_stats"]["total"] == 100
        assert data["sms_stats"]["delivered"] == 85
        assert data["sms_stats"]["delivery_rate"] == 85.0
        assert data["sms_stats"]["total_cost"] == 150.0

        # Check provider breakdown
        assert len(data["provider_breakdown"]) == 2
        assert data["provider_breakdown"][0]["success_rate"] == 90.0  # 45/50*100


@pytest.mark.asyncio
async def test_sms_integration_flow(async_client, test_token_headers_manager, test_db):
    """Test complete SMS integration flow"""
    # 1. Create template
    template_response = await async_client.post(
        "/api/v1/notifications/sms-templates",
        headers=test_token_headers_manager,
        json={
            "code": "integration_test",
            "name": "整合測試",
            "content": "【幸福氣】{name} 您好，這是整合測試訊息。",
        },
    )

    assert template_response.status_code == 200

    # 2. Send SMS using template
    with patch("app.services.sms_service.enhanced_sms_service.send_sms") as mock_send:
        message_id = str(uuid4())
        mock_send.return_value = {
            "success": True,
            "message_id": message_id,
            "segments": 1,
            "cost": 1.5,
        }

        send_response = await async_client.post(
            "/api/v1/notifications/send-sms",
            headers=test_token_headers_manager,
            json={
                "phone": "0912345678",
                "template_code": "integration_test",
                "template_data": {"name": "測試用戶"},
            },
        )

    assert send_response.status_code == 200
    assert send_response.json()["success"] is True

    # 3. Check delivery status
    with patch(
        "app.services.sms_service.enhanced_sms_service.check_delivery_status"
    ) as mock_check:
        mock_check.return_value = {
            "success": True,
            "status": NotificationStatus.DELIVERED,
            "delivered_at": datetime.utcnow(),
        }

        status_response = await async_client.get(
            f"/api/v1/notifications/sms-status/{message_id}",
            headers=test_token_headers_manager,
        )

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "delivered"
