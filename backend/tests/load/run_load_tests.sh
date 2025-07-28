#!/bin/bash
set -e

# Load test runner script for Lucky Gas API

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
HOST="${API_HOST:-http://localhost:8000}"
RESULTS_DIR="load_test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create results directory
mkdir -p $RESULTS_DIR

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    log_error "Locust is not installed. Please run: pip install -r requirements.txt"
    exit 1
fi

# Function to run a load test scenario
run_scenario() {
    local scenario_name=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local user_class=${5:-"MixedWorkloadUser"}
    
    log_info "Running scenario: $scenario_name"
    log_info "Users: $users, Spawn rate: $spawn_rate/s, Duration: ${duration}s"
    
    locust \
        --headless \
        --host $HOST \
        --users $users \
        --spawn-rate $spawn_rate \
        --run-time $duration \
        --html ${RESULTS_DIR}/${scenario_name}_${TIMESTAMP}.html \
        --csv ${RESULTS_DIR}/${scenario_name}_${TIMESTAMP} \
        --class-picker \
        -f locustfile.py \
        $user_class
        
    log_info "Scenario $scenario_name completed"
    echo ""
}

# Performance baseline test
baseline_test() {
    log_info "=== Running Performance Baseline Test ==="
    
    # Warm-up
    log_info "Warming up the system..."
    run_scenario "warmup" 5 1 30 "MixedWorkloadUser"
    
    # Baseline test - light load
    run_scenario "baseline_light" 10 2 120 "MixedWorkloadUser"
    
    # Baseline test - moderate load
    run_scenario "baseline_moderate" 50 5 180 "MixedWorkloadUser"
    
    # Baseline test - heavy load
    run_scenario "baseline_heavy" 100 10 180 "MixedWorkloadUser"
}

# Stress test
stress_test() {
    log_info "=== Running Stress Test ==="
    
    # Gradual increase
    run_scenario "stress_gradual" 200 5 300 "MixedWorkloadUser"
    
    # Spike test
    run_scenario "stress_spike" 100 50 120 "MixedWorkloadUser"
}

# Endurance test
endurance_test() {
    log_info "=== Running Endurance Test ==="
    
    # Long-running test with moderate load
    run_scenario "endurance" 50 2 3600 "MixedWorkloadUser"  # 1 hour
}

# Mobile app load test
mobile_test() {
    log_info "=== Running Mobile App Load Test ==="
    
    # Simulate mobile drivers
    run_scenario "mobile_drivers" 30 3 300 "MobileDriverUser"
}

# Admin dashboard test
admin_test() {
    log_info "=== Running Admin Dashboard Test ==="
    
    # Simulate admin users
    run_scenario "admin_dashboard" 10 1 300 "AdminDashboardUser"
}

# Parse command line arguments
case "${1:-baseline}" in
    baseline)
        baseline_test
        ;;
    stress)
        stress_test
        ;;
    endurance)
        endurance_test
        ;;
    mobile)
        mobile_test
        ;;
    admin)
        admin_test
        ;;
    all)
        baseline_test
        stress_test
        mobile_test
        admin_test
        ;;
    *)
        echo "Usage: $0 {baseline|stress|endurance|mobile|admin|all}"
        exit 1
        ;;
esac

# Generate summary report
log_info "Generating summary report..."
cat > ${RESULTS_DIR}/summary_${TIMESTAMP}.txt <<EOF
Load Test Summary
=================
Timestamp: $(date)
Host: $HOST
Test Type: $1

Results Location: ${RESULTS_DIR}/

Key Metrics to Review:
- Response Time (95th percentile should be < 1s)
- Error Rate (should be < 1%)
- Requests per Second
- CPU and Memory usage on server

Performance Baseline Thresholds:
- API Response Time: < 200ms (p95)
- Database Query Time: < 100ms (p95)
- Static Content: < 50ms (p95)
- Error Rate: < 0.1%
- Availability: > 99.9%
EOF

log_info "Load tests completed. Results saved to ${RESULTS_DIR}/"
log_info "View HTML reports for detailed analysis"