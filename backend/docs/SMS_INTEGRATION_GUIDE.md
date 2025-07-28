# SMS Gateway Integration Guide

## Overview

The LuckyGas SMS Gateway provides a production-ready SMS notification system with multiple provider support, automatic failover, and comprehensive monitoring. The system is specifically designed for Taiwan's market with Traditional Chinese support and local provider integration.

## Architecture

### Components

1. **SMS Gateway** (`app/services/sms_gateway.py`)
   - Provider abstraction layer
   - Automatic failover between providers
   - Rate limiting and connection pooling
   - Message template rendering

2. **SMS Providers**
   - **Twilio** (`app/services/sms_providers/twilio.py`) - International provider
   - **Chunghwa Telecom** (`app/services/sms_providers/chunghwa.py`) - Taiwan local provider

3. **SMS Service** (`app/services/sms_service.py`)
   - Enhanced service with circuit breakers
   - A/B testing for templates
   - Bulk SMS support
   - Delivery tracking

4. **Admin Interface** (`frontend/src/pages/admin/SMSMonitor.tsx`)
   - Real-time SMS monitoring
   - Statistics and analytics
   - Template management
   - Provider health monitoring

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# SMS Configuration
SMS_ENABLED=true
SMS_PRIMARY_PROVIDER=twilio
SMS_FALLBACK_PROVIDERS=["chunghwa"]
SMS_RATE_LIMIT_PER_MINUTE=60

# Twilio Configuration
SMS_TWILIO_ENABLED=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
TWILIO_WEBHOOK_URL=https://api.luckygas.tw/api/v1

# Chunghwa Telecom Configuration
SMS_CHUNGHWA_ENABLED=true
CHT_SMS_ACCOUNT_ID=your_account_id
CHT_SMS_PASSWORD=your_password
CHT_SMS_WEBHOOK_SECRET=your_webhook_secret
```

### Database Migration

Run the migration to create SMS tables:

```bash
cd backend
uv run alembic upgrade head
```

## Usage

### Sending SMS

#### Direct Message

```python
from app.services.sms_service import enhanced_sms_service

result = await enhanced_sms_service.send_sms(
    phone="0912345678",
    message="測試簡訊",
    message_type="test"
)
```

#### Using Template

```python
result = await enhanced_sms_service.send_sms(
    phone="0912345678",
    template_code="order_confirmation",
    template_data={
        "order_id": "ORD123",
        "delivery_time": "14:30"
    },
    message_type="order_confirmation"
)
```

#### Bulk SMS

```python
recipients = [
    {"phone": "0912345678", "data": {"name": "張三"}},
    {"phone": "0923456789", "data": {"name": "李四"}}
]

result = await enhanced_sms_service.send_bulk_sms(
    recipients=recipients,
    message_type="promotion",
    template_code="promotion_template"
)
```

### API Endpoints

#### Send SMS
```http
POST /api/v1/sms/send
Content-Type: application/json
Authorization: Bearer {token}

{
  "phone": "0912345678",
  "message": "測試簡訊",
  "message_type": "test"
}
```

#### Get SMS Logs
```http
GET /api/v1/sms/logs?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}
```

#### Get SMS Statistics
```http
GET /api/v1/sms/stats?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}
```

## Message Templates

### Default Templates

The system includes pre-configured templates:

1. **order_confirmation** - 訂單確認
   - Variant A: Detailed version
   - Variant B: Concise version

2. **out_for_delivery** - 配送中通知
3. **delivery_completed** - 配送完成
4. **payment_reminder** - 付款提醒

### Creating New Templates

```python
POST /api/v1/sms/templates
{
  "code": "new_template",
  "name": "新模板",
  "content": "【幸福氣】{content}",
  "variant": "A",
  "weight": 100
}
```

## Webhook Configuration

### Twilio Webhook

Configure in Twilio console:
```
https://api.luckygas.tw/api/v1/sms/delivery/twilio
```

### Chunghwa Telecom Webhook

Configure with CHT:
```
https://api.luckygas.tw/api/v1/sms/delivery/chunghwa
```

## Monitoring

### Admin Dashboard

Access the SMS monitoring dashboard at:
```
https://app.luckygas.tw/admin/sms-monitor
```

Features:
- Real-time delivery status
- Provider performance metrics
- Template effectiveness tracking
- Cost analysis
- Failed message management

### Metrics

The system tracks:
- Total messages sent/delivered/failed
- Success rate by provider
- Cost per message
- Template performance (A/B testing)
- Provider health status

## Error Handling

### Circuit Breaker

The system implements circuit breakers for each provider:
- Opens after 3 consecutive failures
- Half-open state after 5 minutes
- Automatic recovery on successful send

### Retry Logic

- Automatic retry with different provider on failure
- Maximum 3 retry attempts
- Exponential backoff between retries

## Production Deployment

### 1. Secret Management

For production, use Google Secret Manager:

```bash
# Create secrets
gcloud secrets create sms-twilio-credentials --data-file=twilio-creds.json
gcloud secrets create sms-chunghwa-credentials --data-file=cht-creds.json
```

### 2. Provider Setup

#### Twilio
1. Create account at https://www.twilio.com
2. Purchase phone number with SMS capability
3. Configure webhook URL
4. Note Account SID and Auth Token

#### Chunghwa Telecom
1. Apply for business SMS account
2. Get API credentials
3. Configure IP whitelist
4. Set up webhook endpoint

### 3. Load Testing

Test the system before production:

```python
# Load test script
import asyncio
from app.services.sms_service import enhanced_sms_service

async def load_test():
    tasks = []
    for i in range(100):
        task = enhanced_sms_service.send_sms(
            phone=f"091234{i:04d}",
            message="Load test",
            message_type="test"
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    success = sum(1 for r in results if r["success"])
    print(f"Success rate: {success/100*100}%")
```

### 4. Monitoring Setup

Configure alerts for:
- Low success rate (<95%)
- High failure count (>10/minute)
- Provider health issues
- Low account balance

## Security Considerations

1. **API Keys**: Store in environment variables or secret manager
2. **Webhook Validation**: Verify signatures from providers
3. **Rate Limiting**: Implement per-customer rate limits
4. **Phone Number Validation**: Validate Taiwan format
5. **Message Content**: Sanitize template variables

## Cost Management

### Cost Optimization

1. Use templates to reduce message length
2. Batch messages when possible
3. Monitor usage by customer/type
4. Set daily/monthly limits

### Pricing (Approximate)

- Twilio: ~NT$0.50 per SMS segment
- Chunghwa: ~NT$0.70 per SMS segment
- Unicode messages use more segments

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check API credentials
   - Verify account is active
   - Check IP whitelist (CHT)

2. **Message Not Delivered**
   - Check phone number format
   - Verify recipient can receive SMS
   - Check provider status

3. **High Failure Rate**
   - Check provider health
   - Verify rate limits
   - Check account balance

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("app.services.sms_service").setLevel(logging.DEBUG)
```

## Compliance

### Taiwan Regulations

1. Include company name in message
2. Provide opt-out mechanism
3. Respect quiet hours (9 PM - 8 AM)
4. Maintain delivery logs for audit

### GDPR/Privacy

1. Get explicit consent
2. Allow data deletion
3. Encrypt sensitive data
4. Log access for audit

## Future Enhancements

1. **WhatsApp Business API** integration
2. **LINE Notify** support
3. **Rich media messages** (MMS)
4. **Two-way SMS** for customer replies
5. **Smart routing** based on cost/performance
6. **Message scheduling** for optimal delivery times