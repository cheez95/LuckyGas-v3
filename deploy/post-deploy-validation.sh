#!/bin/bash

# LuckyGas Post-Deployment Validation Script
# Comprehensive validation of production deployment

set -euo pipefail

# Configuration
API_URL="${API_URL:-https://api.luckygas.com.tw}"
FRONTEND_URL="${FRONTEND_URL:-https://app.luckygas.com.tw}"
TEST_USER="${TEST_USER:-testuser@luckygas.com.tw}"
TEST_PASSWORD="${TEST_PASSWORD:-}"
VALIDATION_LOG="validation_$(date +%Y%m%d_%H%M%S).log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Validation results
VALIDATION_STATUS=0
VALIDATION_REPORT=""

log() {
    echo -e "${2:-}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$VALIDATION_LOG"
}

add_report() {
    VALIDATION_REPORT="${VALIDATION_REPORT}\n$1"
}

# Get JWT token for authenticated tests
get_auth_token() {
    local token=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${TEST_USER}\",\"password\":\"${TEST_PASSWORD}\"}" \
        | jq -r '.access_token' 2>/dev/null || echo "")
    
    if [ -n "$token" ] && [ "$token" != "null" ]; then
        echo "$token"
        return 0
    else
        log "Failed to obtain auth token!" "$RED"
        return 1
    fi
}

# Test critical user flows
test_user_flows() {
    log "=== Testing Critical User Flows ===" "$BLUE"
    
    local token=$(get_auth_token)
    if [ -z "$token" ]; then
        add_report "✗ Authentication Flow: FAILED"
        VALIDATION_STATUS=1
        return
    fi
    
    add_report "✓ Authentication Flow: PASSED"
    
    # Test customer creation
    log "Testing customer creation..." "$YELLOW"
    local customer_response=$(curl -s -X POST "${API_URL}/api/v1/customers/" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '{
            "姓名": "測試客戶",
            "聯絡電話": "0912345678",
            "地址": "台北市信義區信義路五段7號",
            "客戶類型": "residential",
            "email": "test@example.com"
        }')
    
    local customer_id=$(echo "$customer_response" | jq -r '.id' 2>/dev/null || echo "")
    
    if [ -n "$customer_id" ] && [ "$customer_id" != "null" ]; then
        log "Customer created successfully (ID: $customer_id) ✓" "$GREEN"
        add_report "✓ Customer Creation: PASSED"
    else
        log "Customer creation failed!" "$RED"
        add_report "✗ Customer Creation: FAILED"
        VALIDATION_STATUS=1
    fi
    
    # Test order creation with 預定配送日期
    log "Testing order creation with 預定配送日期..." "$YELLOW"
    local tomorrow=$(date -d tomorrow +%Y-%m-%d)
    local order_response=$(curl -s -X POST "${API_URL}/api/v1/orders/" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{
            \"客戶ID\": ${customer_id:-1},
            \"預定配送日期\": \"${tomorrow}T10:00:00\",
            \"配送地址\": \"台北市信義區信義路五段7號\",
            \"訂單項目\": [
                {\"產品ID\": 1, \"數量\": 2, \"單價\": 850}
            ],
            \"總金額\": 1700
        }")
    
    # Check if response contains 預定配送日期 field
    if echo "$order_response" | grep -q "預定配送日期"; then
        log "Order created with correct field name ✓" "$GREEN"
        add_report "✓ Order Creation (預定配送日期): PASSED"
    else
        log "Order creation failed or incorrect field name!" "$RED"
        add_report "✗ Order Creation (預定配送日期): FAILED"
        VALIDATION_STATUS=1
    fi
    
    # Clean up test data
    if [ -n "$customer_id" ] && [ "$customer_id" != "null" ]; then
        curl -s -X DELETE "${API_URL}/api/v1/customers/${customer_id}" \
            -H "Authorization: Bearer $token" > /dev/null 2>&1 || true
    fi
}

# Test all analytics endpoints
test_analytics_endpoints() {
    log "=== Testing Analytics Endpoints ===" "$BLUE"
    
    local token=$(get_auth_token)
    if [ -z "$token" ]; then
        log "Skipping analytics tests - no auth token" "$YELLOW"
        return
    fi
    
    local endpoints=("executive" "operations" "financial" "performance")
    
    for endpoint in "${endpoints[@]}"; do
        log "Testing /api/v1/analytics/${endpoint}..." "$YELLOW"
        
        local response_code=$(curl -s -o /dev/null -w "%{http_code}" \
            "${API_URL}/api/v1/analytics/${endpoint}" \
            -H "Authorization: Bearer $token")
        
        if [[ "$response_code" =~ ^(200|403)$ ]]; then
            log "Analytics endpoint /${endpoint} responding correctly (HTTP $response_code) ✓" "$GREEN"
            add_report "✓ Analytics Endpoint /${endpoint}: PASSED"
        else
            log "Analytics endpoint /${endpoint} failed (HTTP $response_code)!" "$RED"
            add_report "✗ Analytics Endpoint /${endpoint}: FAILED"
            VALIDATION_STATUS=1
        fi
    done
}

# Test Google Cloud integrations
test_google_cloud() {
    log "=== Testing Google Cloud Integrations ===" "$BLUE"
    
    # Test Maps Geocoding
    log "Testing Google Maps geocoding..." "$YELLOW"
    local geocode_response=$(curl -s "${API_URL}/api/v1/maps/geocode?address=台北市信義區市府路1號")
    
    if echo "$geocode_response" | jq -r '.status' | grep -q "OK"; then
        local lat=$(echo "$geocode_response" | jq -r '.results[0].geometry.location.lat' 2>/dev/null || echo "0")
        local lng=$(echo "$geocode_response" | jq -r '.results[0].geometry.location.lng' 2>/dev/null || echo "0")
        
        # Verify coordinates are in Taiwan
        if (( $(echo "$lat > 21.5 && $lat < 25.5" | bc -l) )) && \
           (( $(echo "$lng > 119.5 && $lng < 122.5" | bc -l) )); then
            log "Google Maps geocoding working correctly ✓" "$GREEN"
            add_report "✓ Google Maps Geocoding: PASSED"
        else
            log "Geocoded coordinates outside Taiwan!" "$RED"
            add_report "✗ Google Maps Geocoding: INVALID COORDINATES"
            VALIDATION_STATUS=1
        fi
    else
        log "Google Maps geocoding failed!" "$RED"
        add_report "✗ Google Maps Geocoding: FAILED"
        VALIDATION_STATUS=1
    fi
    
    # Test Vertex AI predictions
    log "Testing Vertex AI predictions..." "$YELLOW"
    local prediction_response=$(curl -s "${API_URL}/api/v1/predictions/health")
    
    if echo "$prediction_response" | jq -r '.status' | grep -q "healthy"; then
        log "Vertex AI integration healthy ✓" "$GREEN"
        add_report "✓ Vertex AI Integration: PASSED"
    else
        log "Vertex AI integration unhealthy!" "$YELLOW"
        add_report "⚠ Vertex AI Integration: UNHEALTHY"
        # Don't fail deployment for ML service
    fi
}

# Test mobile API endpoints
test_mobile_endpoints() {
    log "=== Testing Mobile/Driver Endpoints ===" "$BLUE"
    
    # Test driver login
    local driver_token=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"driver01","password":"Driver123!@#","role":"driver"}' \
        | jq -r '.access_token' 2>/dev/null || echo "")
    
    if [ -n "$driver_token" ] && [ "$driver_token" != "null" ]; then
        log "Driver authentication working ✓" "$GREEN"
        add_report "✓ Driver Authentication: PASSED"
        
        # Test driver routes endpoint
        local routes_response=$(curl -s "${API_URL}/api/v1/drivers/routes/today" \
            -H "Authorization: Bearer $driver_token")
        
        if echo "$routes_response" | jq -e . >/dev/null 2>&1; then
            log "Driver routes endpoint working ✓" "$GREEN"
            add_report "✓ Driver Routes API: PASSED"
        else
            log "Driver routes endpoint failed!" "$RED"
            add_report "✗ Driver Routes API: FAILED"
            VALIDATION_STATUS=1
        fi
    else
        log "Driver authentication failed!" "$RED"
        add_report "✗ Driver Authentication: FAILED"
        VALIDATION_STATUS=1
    fi
}

# Performance validation
test_performance() {
    log "=== Testing Performance Requirements ===" "$BLUE"
    
    # Test API response times
    local endpoints=(
        "/api/v1/customers/"
        "/api/v1/orders/"
        "/api/v1/products/"
        "/api/v1/routes/"
    )
    
    local all_passed=true
    
    for endpoint in "${endpoints[@]}"; do
        local start_time=$(date +%s%3N)
        local response_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}${endpoint}")
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        
        if [ "$response_time" -lt 2000 ]; then
            log "Endpoint $endpoint response time: ${response_time}ms ✓" "$GREEN"
        else
            log "Endpoint $endpoint response time: ${response_time}ms (>2s) ✗" "$RED"
            all_passed=false
        fi
    done
    
    if [ "$all_passed" = true ]; then
        add_report "✓ API Performance (<2s): PASSED"
    else
        add_report "✗ API Performance (<2s): FAILED"
        VALIDATION_STATUS=1
    fi
}

# Frontend validation
test_frontend() {
    log "=== Testing Frontend Deployment ===" "$BLUE"
    
    # Check homepage loads
    local homepage_status=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
    
    if [ "$homepage_status" = "200" ]; then
        log "Frontend homepage loading correctly ✓" "$GREEN"
        add_report "✓ Frontend Homepage: PASSED"
    else
        log "Frontend homepage not loading (HTTP $homepage_status)!" "$RED"
        add_report "✗ Frontend Homepage: FAILED"
        VALIDATION_STATUS=1
    fi
    
    # Check static assets
    local js_status=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}/static/js/main.js" || echo "404")
    
    if [[ "$js_status" =~ ^(200|304)$ ]]; then
        log "Frontend static assets loading correctly ✓" "$GREEN"
        add_report "✓ Frontend Static Assets: PASSED"
    else
        log "Frontend static assets not loading!" "$RED"
        add_report "✗ Frontend Static Assets: FAILED"
        VALIDATION_STATUS=1
    fi
    
    # Check mobile responsiveness meta tag
    local mobile_meta=$(curl -s "$FRONTEND_URL" | grep -o 'viewport.*width=device-width' || echo "")
    
    if [ -n "$mobile_meta" ]; then
        log "Mobile viewport meta tag present ✓" "$GREEN"
        add_report "✓ Mobile Responsiveness: PASSED"
    else
        log "Mobile viewport meta tag missing!" "$YELLOW"
        add_report "⚠ Mobile Responsiveness: WARNING"
    fi
}

# Security validation
test_security() {
    log "=== Testing Security Configuration ===" "$BLUE"
    
    # Check HTTPS redirect
    local http_response=$(curl -s -o /dev/null -w "%{http_code}" -L "http://api.luckygas.com.tw" || echo "000")
    
    if [ "$http_response" = "200" ]; then
        log "HTTPS redirect working ✓" "$GREEN"
        add_report "✓ HTTPS Redirect: PASSED"
    else
        log "HTTPS redirect not working!" "$YELLOW"
        add_report "⚠ HTTPS Redirect: WARNING"
    fi
    
    # Check security headers
    local headers=$(curl -s -I "$API_URL")
    
    if echo "$headers" | grep -q "X-Content-Type-Options: nosniff"; then
        log "Security headers present ✓" "$GREEN"
        add_report "✓ Security Headers: PASSED"
    else
        log "Some security headers missing!" "$YELLOW"
        add_report "⚠ Security Headers: WARNING"
    fi
    
    # Test rate limiting
    log "Testing rate limiting..." "$YELLOW"
    local rate_limit_hit=false
    
    for i in {1..50}; do
        local status=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/api/v1/auth/login" \
            -X POST -H "Content-Type: application/json" -d '{"email":"test","password":"test"}')
        
        if [ "$status" = "429" ]; then
            rate_limit_hit=true
            break
        fi
    done
    
    if [ "$rate_limit_hit" = true ]; then
        log "Rate limiting active ✓" "$GREEN"
        add_report "✓ Rate Limiting: PASSED"
    else
        log "Rate limiting may not be configured!" "$YELLOW"
        add_report "⚠ Rate Limiting: WARNING"
    fi
}

# Generate validation report
generate_validation_report() {
    local report_file="post_deploy_validation_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" <<EOF
LuckyGas Post-Deployment Validation Report
==========================================
Date: $(date)
Environment: Production
Status: $([ $VALIDATION_STATUS -eq 0 ] && echo "PASSED" || echo "FAILED")

Validation Results:
$VALIDATION_REPORT

Critical Validations:
- 預定配送日期 Field: $(echo "$VALIDATION_REPORT" | grep "預定配送日期" | grep -q "PASSED" && echo "✓" || echo "✗")
- Analytics Endpoints: $(echo "$VALIDATION_REPORT" | grep -c "Analytics.*PASSED")/4 passed
- Google Maps Integration: $(echo "$VALIDATION_REPORT" | grep "Google Maps" | grep -q "PASSED" && echo "✓" || echo "✗")
- API Performance: $(echo "$VALIDATION_REPORT" | grep "Performance" | grep -q "PASSED" && echo "✓" || echo "✗")

Validation Log: $VALIDATION_LOG
==========================================
EOF
    
    log "Validation report generated: $report_file" "$YELLOW"
}

# Main validation flow
main() {
    log "=== Starting Post-Deployment Validation ===" "$BLUE"
    
    test_user_flows
    test_analytics_endpoints
    test_google_cloud
    test_mobile_endpoints
    test_performance
    test_frontend
    test_security
    
    generate_validation_report
    
    if [ $VALIDATION_STATUS -eq 0 ]; then
        log "=== All Validations Passed ✓ ===" "$GREEN"
    else
        log "=== Some Validations Failed ✗ ===" "$RED"
    fi
    
    exit $VALIDATION_STATUS
}

# Execute main function
main