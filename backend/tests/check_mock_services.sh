#!/bin/bash
# Quick script to check status of all mock services

echo "🔍 Lucky Gas Mock Services Status Check"
echo "======================================"
echo ""

# Check if services are running
echo "📦 Docker Container Status:"
docker-compose -f docker-compose.test.yml ps | grep -E "(mock-sms|mock-einvoice|mock-banking|mock-gcp)" | while read line; do
    if echo "$line" | grep -q "healthy"; then
        echo "  ✅ $line"
    elif echo "$line" | grep -q "unhealthy"; then
        echo "  ❌ $line"
    else
        echo "  ⏳ $line"
    fi
done

echo ""
echo "🌐 Service Health Endpoints:"

# Check each service's health endpoint
services=(
    "SMS Gateway|http://localhost:8001/health"
    "E-Invoice|http://localhost:8002/health"
    "Banking|http://localhost:8003/health"
    "GCP Services|http://localhost:8085/health"
)

for service in "${services[@]}"; do
    IFS='|' read -r name url <<< "$service"
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo "  ✅ $name: Online"
    else
        echo "  ❌ $name: Offline"
    fi
done

echo ""
echo "💡 Tips:"
echo "  - Run './validate_mock_services.py' for basic health checks"
echo "  - Run './validate_mock_services_comprehensive.py' for full API tests"
echo "  - View logs: docker-compose -f docker-compose.test.yml logs [service-name]"
echo "  - Restart service: docker-compose -f docker-compose.test.yml restart [service-name]"
echo ""