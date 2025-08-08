#\!/bin/bash

PROJECT_ID="vast-tributary-466619-m8"
SERVICE_NAME="luckygas-backend"
REGION="asia-east1"

echo "Creating Cloud Monitoring uptime check..."

# Create uptime check for health endpoint
gcloud monitoring uptime-check-configs create luckygas-health \
  --display-name="LuckyGas Backend Health Check" \
  --monitored-resource-type="gce_instance" \
  --resource-labels="project_id=$PROJECT_ID" \
  --http-check-path="/api/v1/health" \
  --port=443 \
  --use-ssl \
  --selected-regions="ASIA_PACIFIC,USA,EUROPE" \
  --timeout=10s \
  --period=60s \
  --project=$PROJECT_ID 2>/dev/null || echo "Uptime check already exists"

# Create notification channel
gcloud alpha monitoring channels create \
  --display-name="LuckyGas Admin Email" \
  --type=email \
  --channel-labels="email_address=admin@luckygas.com.tw" \
  --project=$PROJECT_ID 2>/dev/null || echo "Notification channel exists"

# Get notification channel ID
CHANNEL_ID=$(gcloud alpha monitoring channels list \
  --filter="displayName='LuckyGas Admin Email'" \
  --format="value(name)" \
  --project=$PROJECT_ID | head -1)

echo "Notification channel: $CHANNEL_ID"

# Create alert policy for high latency
cat > /tmp/alert-latency.json << JSON
{
  "displayName": "High Response Time Alert",
  "conditions": [{
    "displayName": "Response time > 500ms",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_latencies\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": 500,
      "duration": "300s",
      "aggregations": [{
        "alignmentPeriod": "60s",
        "perSeriesAligner": "ALIGN_PERCENTILE_95"
      }]
    }
  }],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$CHANNEL_ID"]
}
JSON

gcloud alpha monitoring policies create --policy-from-file=/tmp/alert-latency.json --project=$PROJECT_ID 2>/dev/null || echo "Latency alert exists"

# Create alert policy for high error rate
cat > /tmp/alert-errors.json << JSON
{
  "displayName": "High Error Rate Alert",
  "conditions": [{
    "displayName": "Error rate > 2%",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_count\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": 0.02,
      "duration": "300s",
      "aggregations": [{
        "alignmentPeriod": "60s",
        "perSeriesAligner": "ALIGN_RATE"
      }]
    }
  }],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$CHANNEL_ID"]
}
JSON

gcloud alpha monitoring policies create --policy-from-file=/tmp/alert-errors.json --project=$PROJECT_ID 2>/dev/null || echo "Error rate alert exists"

echo "Monitoring setup complete\!"
echo "Dashboard URL: https://console.cloud.google.com/monitoring/dashboards?project=$PROJECT_ID"
