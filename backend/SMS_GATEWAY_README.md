# SMS Gateway Integration for LuckyGas

## Overview

The SMS Gateway Integration provides a robust, multi-provider SMS notification system for LuckyGas delivery notifications. It supports Taiwan-specific SMS providers with Traditional Chinese support, delivery tracking, and comprehensive logging.

## Features

### Core Features
- ✅ Multiple SMS provider support (Twilio, Every8d, Mitake)
- ✅ Traditional Chinese (繁體中文) support with Unicode handling
- ✅ Automatic provider failover and retry logic
- ✅ Rate limiting to prevent abuse
- ✅ SMS template management with A/B testing
- ✅ Delivery status tracking via webhooks
- ✅ Cost tracking and analytics
- ✅ Bulk SMS sending capabilities
- ✅ Comprehensive audit trail

### SMS Providers

#### 1. **Twilio** (International)
- Global coverage with Taiwan support
- Real-time delivery status via webhooks
- Higher cost but reliable
- Best for: International customers, critical notifications

#### 2. **Every8d** (台灣簡訊供應商)
- Local Taiwan provider with competitive rates
- Native Traditional Chinese support
- Fast delivery within Taiwan
- Best for: Local customers, marketing campaigns

#### 3. **Mitake** (三竹簡訊)
- Established Taiwan SMS provider
- Enterprise-grade reliability
- Good API documentation
- Best for: Business communications, official notices

## Configuration

### 1. Database Migration

Run the migration to create notification tables:

```bash
cd backend
alembic upgrade head
```

### 2. Initialize Provider Configurations

Run the initialization script to set up provider configs:

```bash
cd backend
python -m app.scripts.init_sms_providers
```

### 3. Configure Provider Credentials

Update provider configurations via API or directly in database:

```json
// Twilio Configuration
{
  "provider": "twilio",
  "config": {
    "account_sid": "YOUR_TWILIO_ACCOUNT_SID",
    "auth_token": "YOUR_TWILIO_AUTH_TOKEN",
    "from_number": "+886912345678"
  },
  "is_active": true,
  "priority": 10
}

// Every8d Configuration
{
  "provider": "every8d",
  "config": {
    "username": "YOUR_EVERY8D_USERNAME",
    "password": "YOUR_EVERY8D_PASSWORD",
    "api_url": "https://api.e8d.tw/SMS/BulkSMS"
  },
  "is_active": true,
  "priority": 20
}

// Mitake Configuration
{
  "provider": "mitake",
  "config": {
    "username": "YOUR_MITAKE_USERNAME",
    "password": "YOUR_MITAKE_PASSWORD",
    "api_url": "https://api.mitake.com.tw/api/mtk/SmSend"
  },
  "is_active": true,
  "priority": 15
}
```

### 4. Configure Webhook URLs

Set up webhook endpoints with your SMS providers:

- **Twilio**: `https://your-domain.com/api/v1/webhooks/sms/twilio`
- **Every8d**: `https://your-domain.com/api/v1/webhooks/sms/every8d`
- **Mitake**: `https://your-domain.com/api/v1/webhooks/sms/mitake`

## API Endpoints

### Send SMS

```bash
POST /api/v1/notifications/send-sms
Authorization: Bearer {token}

{
  "phone": "0912345678",
  "message": "您的瓦斯訂單已確認",
  "message_type": "order_confirmation",
  "metadata": {
    "order_id": "ORD-123"
  }
}
```

### Send SMS with Template

```bash
POST /api/v1/notifications/send-sms
Authorization: Bearer {token}

{
  "phone": "0912345678",
  "template_code": "delivery_on_way",
  "template_data": {
    "driver_name": "王大明",
    "eta": "30"
  }
}
```

### Send Bulk SMS

```bash
POST /api/v1/notifications/send-bulk-sms
Authorization: Bearer {token}

{
  "recipients": [
    {
      "phone": "0912345678",
      "template_data": {"name": "張三"}
    },
    {
      "phone": "0923456789",
      "template_data": {"name": "李四"}
    }
  ],
  "template_code": "payment_reminder",
  "message_type": "payment_reminder",
  "batch_name": "2025年1月付款提醒"
}
```

### Check SMS Status

```bash
GET /api/v1/notifications/sms-status/{message_id}
Authorization: Bearer {token}
```

### SMS Template Management

```bash
# Create template
POST /api/v1/notifications/sms-templates
{
  "code": "new_template",
  "name": "新模板",
  "content": "【幸福氣】{message}"
}

# List templates
GET /api/v1/notifications/sms-templates?is_active=true

# Update template
PUT /api/v1/notifications/sms-templates/{template_id}
{
  "content": "【幸福氣】更新的內容 {message}"
}
```

### Provider Management (Admin Only)

```bash
# List providers
GET /api/v1/notifications/providers

# Update provider
PUT /api/v1/notifications/providers/twilio
{
  "priority": 15,
  "rate_limit": 100
}
```

### Analytics

```bash
# Get SMS statistics
GET /api/v1/notifications/stats?start_date=2025-01-01

# Get SMS logs
GET /api/v1/notifications/sms-logs?status=delivered&limit=100
```

## Message Templates

Default templates are created during initialization:

| Code | Description | Template |
|------|-------------|----------|
| `order_confirmation` | 訂單確認 | 【幸福氣】您的訂單 {order_number} 已確認，預計配送時間：{delivery_time} |
| `delivery_on_way` | 配送中 | 【幸福氣】您的瓦斯正在配送中，司機 {driver_name} 預計 {eta} 分鐘後到達 |
| `delivery_arrived` | 已到達 | 【幸福氣】配送員已到達您的地址，請準備接收瓦斯 |
| `delivery_completed` | 配送完成 | 【幸福氣】您的訂單 {order_number} 已送達完成，感謝您的訂購！ |
| `payment_reminder` | 付款提醒 | 【幸福氣】提醒您，訂單 {order_number} 尚有 NT${amount} 待付款 |

## Integration with Order System

The notification service is integrated with the order system:

```python
from app.services.notification_service import notification_service

# Send order confirmation
await notification_service.send_order_notifications(
    order={
        "order_number": "ORD-123",
        "customer_phone": "0912345678",
        "customer_email": "customer@example.com",
        "scheduled_delivery_time": "今天下午2點"
    },
    event_type=NotificationType.ORDER_CONFIRMATION
)
```

## Testing

### Unit Tests

Run SMS service unit tests:

```bash
cd backend
pytest tests/services/test_sms_service.py -v
```

### API Tests

Run notification API tests:

```bash
cd backend
pytest tests/api/test_notifications.py -v
```

### Manual Testing

1. Use the test SMS endpoint (development only):
```bash
POST /api/v1/test/send-test-sms
{
  "phone": "0912345678",
  "provider": "twilio"
}
```

2. Check logs for SMS sending:
```bash
tail -f backend/logs/app.log | grep SMS
```

## Best Practices

### 1. Phone Number Formatting
- Always validate Taiwan phone numbers before sending
- Mobile: 09XX-XXX-XXX format
- Landline: 0X-XXXX-XXXX format
- International: +886 format

### 2. Message Content
- Keep messages concise (< 70 characters for single segment)
- Include company identifier 【幸福氣】
- Use clear call-to-action
- Avoid special characters that may not render

### 3. Cost Optimization
- Use templates to ensure consistency
- Monitor segment counts (Unicode messages cost more)
- Set daily limits per provider
- Review analytics regularly

### 4. Error Handling
- Always handle SMS failures gracefully
- Provide alternative contact methods
- Log all failures for investigation
- Monitor delivery rates

### 5. Security
- Never log full phone numbers in production
- Encrypt provider credentials
- Validate webhook signatures
- Rate limit API endpoints

## Monitoring

### Key Metrics to Monitor

1. **Delivery Rate**: Target > 95%
2. **Average Cost per Message**: Track by provider
3. **Response Time**: SMS should be sent < 1 second
4. **Failed Messages**: Investigate patterns
5. **Provider Availability**: Track uptime

### Alerts to Configure

- Delivery rate drops below 90%
- Provider returns multiple failures
- Daily spend exceeds budget
- Rate limit exceeded
- Webhook errors

## Troubleshooting

### Common Issues

1. **SMS Not Delivered**
   - Check provider status and balance
   - Verify phone number format
   - Check SMS logs for errors
   - Verify provider is active

2. **Unicode Characters Not Displaying**
   - Ensure provider supports Unicode
   - Check message encoding
   - Verify template content

3. **Webhook Not Updating Status**
   - Verify webhook URL is accessible
   - Check webhook logs
   - Validate webhook signature
   - Ensure provider message ID matches

4. **Rate Limiting Issues**
   - Check current rate limit settings
   - Monitor usage patterns
   - Consider increasing limits
   - Implement queuing for bulk sends

## Future Enhancements

1. **WhatsApp Business API Integration**
2. **LINE Notify Integration** (Popular in Taiwan)
3. **SMS Scheduling** (Send at optimal times)
4. **Smart Routing** (ML-based provider selection)
5. **Two-way SMS** (Customer replies)
6. **MMS Support** (Images/media)
7. **SMS Analytics Dashboard**
8. **Automated A/B Testing**

## Support

For issues or questions:
1. Check SMS logs in the database
2. Review application logs
3. Contact provider support
4. Create an issue in the repository