#!/bin/bash

# Setup Load Balancer and Custom Domain for LuckyGas

set -e

PROJECT_ID="vast-tributary-466619-m8"
REGION="asia-east1"
DOMAIN="luckygas.com.tw"
API_DOMAIN="api.luckygas.com.tw"

echo "Setting up Load Balancer and Custom Domain..."

# Reserve static IP addresses
echo "1. Reserving static IP addresses..."
gcloud compute addresses create luckygas-lb-ip \
    --global \
    --project=$PROJECT_ID 2>/dev/null || echo "IP already reserved"

LB_IP=$(gcloud compute addresses describe luckygas-lb-ip \
    --global \
    --format="value(address)" \
    --project=$PROJECT_ID)

echo "Load Balancer IP: $LB_IP"

# Create backend bucket for frontend
echo "2. Creating backend bucket for frontend..."
gcloud compute backend-buckets create luckygas-frontend-backend \
    --gcs-bucket-name=luckygas-frontend-prod \
    --project=$PROJECT_ID 2>/dev/null || echo "Backend bucket exists"

# Create NEG for Cloud Run backend
echo "3. Creating Network Endpoint Group for Cloud Run..."
gcloud compute network-endpoint-groups create luckygas-backend-neg \
    --region=$REGION \
    --network-endpoint-type=serverless \
    --cloud-run-service=luckygas-backend \
    --project=$PROJECT_ID 2>/dev/null || echo "NEG exists"

# Create backend service for API
echo "4. Creating backend service for API..."
gcloud compute backend-services create luckygas-api-backend \
    --global \
    --project=$PROJECT_ID 2>/dev/null || echo "Backend service exists"

gcloud compute backend-services add-backend luckygas-api-backend \
    --global \
    --network-endpoint-group=luckygas-backend-neg \
    --network-endpoint-group-region=$REGION \
    --project=$PROJECT_ID 2>/dev/null || echo "Backend already added"

# Create URL map
echo "5. Creating URL map..."
cat > /tmp/url-map.yaml << EOF
kind: compute#urlMap
name: luckygas-lb
defaultService: https://www.googleapis.com/compute/v1/projects/$PROJECT_ID/global/backendBuckets/luckygas-frontend-backend
hostRules:
  - hosts:
      - $DOMAIN
      - www.$DOMAIN
    pathMatcher: frontend
  - hosts:
      - $API_DOMAIN
    pathMatcher: api
pathMatchers:
  - name: frontend
    defaultService: https://www.googleapis.com/compute/v1/projects/$PROJECT_ID/global/backendBuckets/luckygas-frontend-backend
  - name: api
    defaultService: https://www.googleapis.com/compute/v1/projects/$PROJECT_ID/global/backendServices/luckygas-api-backend
    pathRules:
      - paths:
          - /api/*
          - /docs
          - /openapi.json
        service: https://www.googleapis.com/compute/v1/projects/$PROJECT_ID/global/backendServices/luckygas-api-backend
EOF

gcloud compute url-maps import luckygas-lb \
    --source=/tmp/url-map.yaml \
    --global \
    --project=$PROJECT_ID 2>/dev/null || \
gcloud compute url-maps update luckygas-lb \
    --source=/tmp/url-map.yaml \
    --global \
    --project=$PROJECT_ID

# Create managed SSL certificate
echo "6. Creating managed SSL certificates..."
gcloud compute ssl-certificates create luckygas-ssl \
    --domains=$DOMAIN,www.$DOMAIN,$API_DOMAIN \
    --global \
    --project=$PROJECT_ID 2>/dev/null || echo "SSL certificate exists"

# Create HTTPS proxy
echo "7. Creating HTTPS proxy..."
gcloud compute target-https-proxies create luckygas-https-proxy \
    --url-map=luckygas-lb \
    --ssl-certificates=luckygas-ssl \
    --global \
    --project=$PROJECT_ID 2>/dev/null || echo "HTTPS proxy exists"

# Create forwarding rule
echo "8. Creating forwarding rule..."
gcloud compute forwarding-rules create luckygas-https-rule \
    --address=luckygas-lb-ip \
    --global \
    --target-https-proxy=luckygas-https-proxy \
    --ports=443 \
    --project=$PROJECT_ID 2>/dev/null || echo "Forwarding rule exists"

# Enable CDN for frontend
echo "9. Enabling CDN for frontend..."
gcloud compute backend-buckets update luckygas-frontend-backend \
    --enable-cdn \
    --project=$PROJECT_ID

# Set up Cloud Armor (DDoS protection)
echo "10. Setting up Cloud Armor..."
gcloud compute security-policies create luckygas-security-policy \
    --description="Security policy for LuckyGas" \
    --project=$PROJECT_ID 2>/dev/null || echo "Security policy exists"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
    --security-policy=luckygas-security-policy \
    --expression="true" \
    --action="rate-based-ban" \
    --rate-limit-threshold-count=100 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=600 \
    --conform-action="allow" \
    --exceed-action="deny-403" \
    --enforce-on-key="IP" \
    --project=$PROJECT_ID 2>/dev/null || echo "Rate limit rule exists"

# Apply security policy to backend service
gcloud compute backend-services update luckygas-api-backend \
    --security-policy=luckygas-security-policy \
    --global \
    --project=$PROJECT_ID

# Output DNS configuration
echo ""
echo "========================================="
echo "Load Balancer Setup Complete!"
echo "========================================="
echo ""
echo "Static IP Address: $LB_IP"
echo ""
echo "DNS Configuration Required:"
echo "Add these records to your DNS provider:"
echo ""
echo "Type  | Name    | Value"
echo "------|---------|----------------"
echo "A     | @       | $LB_IP"
echo "A     | www     | $LB_IP"
echo "A     | api     | $LB_IP"
echo ""
echo "SSL Certificate Status:"
gcloud compute ssl-certificates describe luckygas-ssl \
    --global \
    --format="value(managed.status,managed.domainStatus)" \
    --project=$PROJECT_ID

echo ""
echo "Note: SSL certificates will be provisioned automatically after DNS is configured."
echo "This process can take up to 60 minutes."
echo ""
echo "URLs (after DNS propagation):"
echo "- Frontend: https://$DOMAIN"
echo "- API: https://$API_DOMAIN"
echo "- API Docs: https://$API_DOMAIN/docs"