#!/bin/bash

# LuckyGas Performance Testing Script
# Tests backend endpoints and measures response times

set -e

# Configuration
BACKEND_URL="${1:-https://luckygas-backend-154687573210.asia-east1.run.app}"
CONCURRENT_USERS="${2:-10}"
TOTAL_REQUESTS="${3:-100}"

echo "========================================="
echo "LuckyGas Performance Testing"
echo "========================================="
echo "Backend URL: $BACKEND_URL"
echo "Concurrent Users: $CONCURRENT_USERS"
echo "Total Requests: $TOTAL_REQUESTS"
echo ""

# Function to test endpoint
test_endpoint() {
    local endpoint=$1
    local method=$2
    local data=$3
    local description=$4
    
    echo "Testing: $description"
    echo "Endpoint: $method $endpoint"
    
    if [ "$method" = "GET" ]; then
        response_time=$(curl -s -o /dev/null -w "%{time_total}" -X GET "${BACKEND_URL}${endpoint}")
        http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${BACKEND_URL}${endpoint}")
    else
        response_time=$(curl -s -o /dev/null -w "%{time_total}" -X POST "${BACKEND_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data")
        http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BACKEND_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    # Convert to milliseconds
    response_ms=$(echo "$response_time * 1000" | bc)
    
    echo "HTTP Status: $http_code"
    echo "Response Time: ${response_ms}ms"
    
    # Check if meets target
    if (( $(echo "$response_ms < 200" | bc -l) )); then
        echo "✅ Meets <200ms target"
    else
        echo "⚠️  Exceeds 200ms target"
    fi
    echo "---"
}

# Check if backend is accessible
echo "Checking backend connectivity..."
if ! curl -s -f -o /dev/null "${BACKEND_URL}/docs" 2>/dev/null; then
    echo "⚠️  Warning: Backend may not be fully accessible"
    echo "Continuing with tests anyway..."
fi
echo ""

# Test core endpoints
echo "========================================="
echo "Individual Endpoint Tests"
echo "========================================="

test_endpoint "/api/v1/health" "GET" "" "Health Check"
test_endpoint "/api/v1/health/ready" "GET" "" "Readiness Check"
test_endpoint "/docs" "GET" "" "API Documentation"
test_endpoint "/api/v1/customers" "GET" "" "List Customers"
test_endpoint "/api/v1/orders" "GET" "" "List Orders"
test_endpoint "/api/v1/routes" "GET" "" "List Routes"
test_endpoint "/api/v1/products" "GET" "" "List Products"
test_endpoint "/api/v1/analytics/dashboard" "GET" "" "Analytics Dashboard"

# Load testing with Apache Bench (if available)
if command -v ab &> /dev/null; then
    echo ""
    echo "========================================="
    echo "Load Testing with Apache Bench"
    echo "========================================="
    
    echo "Running load test: $TOTAL_REQUESTS requests with $CONCURRENT_USERS concurrent users"
    
    # Test health endpoint under load
    ab -n $TOTAL_REQUESTS -c $CONCURRENT_USERS -g /tmp/gnuplot.tsv \
       "${BACKEND_URL}/api/v1/health" 2>&1 | grep -E "Requests per second:|Time per request:|Transfer rate:|Percentage"
    
    echo ""
    echo "Load test complete!"
else
    echo ""
    echo "⚠️  Apache Bench (ab) not installed. Skipping load tests."
    echo "Install with: brew install httpd (macOS) or apt-get install apache2-utils (Linux)"
fi

# Test with curl in parallel
echo ""
echo "========================================="
echo "Parallel Request Testing"
echo "========================================="

echo "Sending $CONCURRENT_USERS parallel requests..."
start_time=$(date +%s%N)

for i in $(seq 1 $CONCURRENT_USERS); do
    curl -s -o /dev/null "${BACKEND_URL}/api/v1/health" &
done
wait

end_time=$(date +%s%N)
elapsed_ms=$(( ($end_time - $start_time) / 1000000 ))

echo "Completed $CONCURRENT_USERS parallel requests in ${elapsed_ms}ms"
avg_time=$(( $elapsed_ms / $CONCURRENT_USERS ))
echo "Average time per request: ${avg_time}ms"

if (( $avg_time < 200 )); then
    echo "✅ Meets <200ms target under concurrent load"
else
    echo "⚠️  Exceeds 200ms target under concurrent load"
fi

# Summary
echo ""
echo "========================================="
echo "Performance Test Summary"
echo "========================================="
echo "Backend URL: $BACKEND_URL"
echo "Tests Completed: $(date)"
echo ""
echo "Recommendations:"
echo "- Monitor Cloud Run metrics for auto-scaling behavior"
echo "- Check Cloud Monitoring dashboard for detailed latency percentiles"
echo "- Review logs for any errors or warnings during testing"
echo "- Consider enabling Cloud CDN for static content"
echo "- Optimize database queries if response times are high"
echo ""
echo "Dashboard: https://console.cloud.google.com/monitoring/dashboards?project=vast-tributary-466619-m8"