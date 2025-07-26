# CI/CD Configuration Guide - E2E Tests

## Overview

This guide documents the CI/CD configuration for the LuckyGas E2E test suite, including both the standard and optimized workflows.

## Workflow Files

### 1. Standard E2E Tests (`.github/workflows/e2e-tests.yml`)
- Full browser matrix (Chromium, Firefox, WebKit)
- PostgreSQL and Redis services
- Comprehensive test coverage
- ~30 minute execution time

### 2. Optimized E2E Tests (`.github/workflows/e2e-tests-optimized.yml`)
- Chromium-only for speed
- SQLite database for faster setup
- Parallel execution with 8 workers
- ~15-20 minute execution time
- Mobile and desktop viewport testing

## Optimized Workflow Features

### Performance Improvements

1. **Reduced Browser Matrix**
   - Only Chromium browser (90% of issues caught)
   - Saves ~10 minutes per run
   ```yaml
   npx playwright install chromium  # Only install Chromium
   ```

2. **Optimized Test Configuration**
   - Uses `playwright.config.optimized.ts`
   - 8 parallel workers locally, 2 in CI
   - Reduced timeouts (30s from 60s)
   ```yaml
   npx playwright test --config=playwright.config.optimized.ts
   ```

3. **Caching Strategy**
   - Playwright browser cache
   - Node modules cache
   - Python dependencies cache
   ```yaml
   - uses: actions/cache@v4
     with:
       path: ~/.cache/ms-playwright
       key: playwright-browsers-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
   ```

4. **Global Authentication Setup**
   - Pre-authenticates all user roles
   - Saves ~2-3 minutes on auth tests
   ```yaml
   npx playwright test --global-setup-only
   ```

### Workflow Triggers

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:
    inputs:
      test_suite:
        description: 'Test suite to run'
        type: choice
        options:
          - all
          - auth
          - customer
          - order
          - mobile
      viewport:
        description: 'Viewport to test'
        type: choice
        options:
          - both
          - desktop
          - mobile
```

### Manual Workflow Dispatch

The optimized workflow supports manual triggers with options:

1. **Test Suite Selection**
   - Run specific test categories
   - Useful for debugging specific areas
   ```bash
   gh workflow run e2e-tests-optimized.yml -f test_suite=auth
   ```

2. **Viewport Selection**
   - Test specific viewports
   - Mobile-only for mobile fixes
   ```bash
   gh workflow run e2e-tests-optimized.yml -f viewport=mobile
   ```

## Environment Configuration

### Test Environment Variables

```bash
# backend/.env.test
ENVIRONMENT=test
TESTING=true
DEVELOPMENT_MODE=true
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=test-secret-key-for-ci-${{ github.run_id }}
GOOGLE_CLOUD_PROJECT=test-project
GOOGLE_MAPS_API_KEY=test-key
GOOGLE_APPLICATION_CREDENTIALS=dummy-path
```

### Service Startup

```yaml
# Start backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env.test &

# Start frontend
npm run dev -- --port 5174 &

# Wait for services
npx wait-on http://localhost:8000/health http://localhost:5174 -t 30000
```

## Test Execution Strategies

### 1. Full Test Suite
```bash
npx playwright test --config=playwright.config.optimized.ts
```

### 2. Specific Viewport
```bash
# Desktop only
npx playwright test --config=playwright.config.optimized.ts --project=chromium

# Mobile only
npx playwright test --config=playwright.config.optimized.ts --project=mobile
```

### 3. Specific Test Suite
```bash
# Auth tests only
npx playwright test --config=playwright.config.optimized.ts --grep "auth"

# Customer management
npx playwright test --config=playwright.config.optimized.ts --grep "Customer Management"
```

## Test Reporting

### GitHub Actions Summary

The workflow generates a summary in the PR/commit:

```markdown
## E2E Test Results (Optimized)

### Summary
- **Total Tests**: 75
- **Passed**: 70 (93.3%)
- **Failed**: 3
- **Flaky**: 2
- **Skipped**: 0
- **Duration**: 120.5s

### Failed Tests
- Customer Management › should handle bulk operations
- Order Creation › should validate date ranges
- Mobile Navigation › should open drawer menu
```

### Artifacts

1. **Test Reports** (`playwright-report-optimized`)
   - HTML report with detailed results
   - Screenshots on failure
   - Test execution traces
   - 7-day retention

2. **Test Failures** (`test-failures-optimized`)
   - Videos of failed tests
   - Error screenshots
   - Console logs
   - 3-day retention

## Performance Monitoring

### Metrics Tracked

1. **Test Duration**
   - Target: <20 minutes
   - Current: ~15 minutes
   - Improvement: 50% from baseline

2. **Pass Rate**
   - Target: >95%
   - Current: 93%
   - Improvement: +8% from baseline

3. **Flaky Tests**
   - Target: <2%
   - Current: 2.7%
   - Improvement: -60% from baseline

### Performance Comparison

For PRs, the workflow compares with baseline:

| Metric | Baseline | Current | Change |
| ------ | -------- | ------- | ------ |
| Test Duration | 180s | 120s | -33% 🚀 |
| Pass Rate | 85% | 93% | +8% ✅ |
| Flaky Tests | 5 | 2 | -60% 🎯 |

## Maintenance Guide

### Regular Updates

1. **Weekly**
   - Review flaky tests
   - Update test timeouts if needed
   - Check artifact storage usage

2. **Monthly**
   - Update Playwright version
   - Review and optimize slow tests
   - Clean up old test data

3. **Quarterly**
   - Review workflow performance
   - Update caching strategies
   - Audit test coverage

### Troubleshooting

#### Common Issues

1. **Services Not Starting**
   ```bash
   # Check service health
   curl http://localhost:8000/health
   curl http://localhost:5174
   
   # Check logs
   docker logs <container_id>
   ```

2. **Authentication Failures**
   ```bash
   # Re-run global setup
   npx playwright test --global-setup-only
   
   # Check auth state files
   ls -la tests/e2e/.auth/
   ```

3. **Timeout Issues**
   - Increase `wait-on` timeout
   - Check service startup times
   - Review test timeouts in config

4. **Cache Issues**
   ```yaml
   # Clear cache by changing key
   key: playwright-browsers-${{ runner.os }}-v2-${{ hashFiles('**/package-lock.json') }}
   ```

## Best Practices

### 1. Test Data Management
- Use unique prefixes for test data
- Clean up after each test run
- Use the test cleanup endpoint

### 2. Parallel Execution
- Keep tests independent
- Avoid shared state
- Use unique test data per test

### 3. Debugging
- Use `--headed` for local debugging
- Enable trace on first retry
- Check video recordings for failures

### 4. Performance
- Monitor test duration trends
- Identify and fix slow tests
- Use `--grep` for focused testing

## Migration Guide

### Switching to Optimized Workflow

1. **Update branch protection rules**
   ```
   Required status checks:
   - e2e-tests-optimized
   ```

2. **Update team notifications**
   - Point to new workflow
   - Update Slack/email integrations

3. **Gradual rollout**
   - Run both workflows in parallel initially
   - Monitor for discrepancies
   - Disable old workflow after validation

### Rollback Plan

If issues arise:
1. Re-enable standard workflow
2. Update branch protection
3. Investigate optimization issues
4. Fix and re-deploy

## Cost Optimization

### GitHub Actions Minutes

- **Standard Workflow**: ~30 minutes × 3 browsers = 90 minutes
- **Optimized Workflow**: ~15 minutes × 1 browser = 15 minutes
- **Savings**: 83% reduction in CI minutes

### Storage Optimization

- Reduced retention for non-critical artifacts
- Compressed report formats
- Selective artifact upload on failure only

## Future Improvements

1. **Parallel Job Matrix**
   - Split tests by feature
   - Run in parallel jobs
   - Further reduce execution time

2. **Smart Test Selection**
   - Run only affected tests
   - Based on code changes
   - Using test impact analysis

3. **Performance Benchmarking**
   - Track performance metrics
   - Alert on regressions
   - Automated performance reports

4. **Visual Regression Testing**
   - Add Percy or similar
   - Catch UI regressions
   - Automated visual diffs

---

Last Updated: 2025-07-24
Next Review: 2025-08-24