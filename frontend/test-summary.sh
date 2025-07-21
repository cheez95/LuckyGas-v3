#!/bin/bash

echo "🧪 Running E2E Test Summary..."
echo "================================"
echo ""

# Run each test file individually and capture results
test_files=(
  "auth.spec.ts"
  "customer.spec.ts"
  "localization.spec.ts"
  "offline-error-handling.spec.ts"
  "predictions-routes.spec.ts"
)

total_tests=0
passed_tests=0
failed_tests=0

for test_file in "${test_files[@]}"; do
  echo "Running $test_file..."
  
  # Run test and capture output
  output=$(npx playwright test "$test_file" --config=playwright-simple.config.ts --project=chromium --reporter=json 2>&1)
  
  # Extract results from JSON output
  if echo "$output" | grep -q '"passed"'; then
    passed=$(echo "$output" | grep -o '"passed":[0-9]*' | grep -o '[0-9]*' | head -1)
    failed=$(echo "$output" | grep -o '"failed":[0-9]*' | grep -o '[0-9]*' | head -1)
    skipped=$(echo "$output" | grep -o '"skipped":[0-9]*' | grep -o '[0-9]*' | head -1)
    
    passed=${passed:-0}
    failed=${failed:-0}
    skipped=${skipped:-0}
    
    echo "  ✅ Passed: $passed"
    echo "  ❌ Failed: $failed"
    echo "  ⏭️  Skipped: $skipped"
    echo ""
    
    total_tests=$((total_tests + passed + failed + skipped))
    passed_tests=$((passed_tests + passed))
    failed_tests=$((failed_tests + failed))
  else
    echo "  ❌ Error running test"
    echo ""
  fi
done

echo "================================"
echo "📊 FINAL SUMMARY:"
echo "  Total Tests: $total_tests"
echo "  ✅ Passed: $passed_tests"
echo "  ❌ Failed: $failed_tests"
echo "  Success Rate: $(( passed_tests * 100 / total_tests ))%"
echo "================================"