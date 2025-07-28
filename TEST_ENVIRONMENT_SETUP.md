# Lucky Gas Test Environment Setup

## Overview

This document provides instructions for setting up and using the Lucky Gas test environment for load testing, security testing, and general QA.

## Quick Start

```bash
# Start the test environment
cd backend/scripts
./start_test_env.sh

# Stop the test environment
./stop_test_env.sh
```

## Architecture

The test environment includes:

1. **PostgreSQL Test Database** (Port 5433)
   - Database: `luckygas_test`
   - User: `luckygas`
   - Password: `your-secure-database-password-here`

2. **Redis Test Cache** (Port 6380)
   - Database: 1 (isolated from production)
   - No password for test environment

3. **Mock Services**:
   - **SMS Service** (Port 8001): Simulates SMS sending
   - **E-Invoice Service** (Port 8002): Simulates Taiwan e-invoice system
   - **Banking API** (Port 8003): Simulates bank payment processing

4. **Backend API** (Port 3001)
   - Test environment configuration
   - Health endpoints: `/api/health`, `/api/v1/health`

5. **Frontend** (Port 3000)
   - Connected to test backend

## Test Data

The setup script creates:

- **Users**: 
  - 1 Super Admin
  - 1 Manager
  - 1 Office Staff
  - 10 Drivers

- **Customers**: 1,000 test customers across Taiwan cities

- **Products**: 5 gas cylinder sizes (50kg, 20kg, 16kg, 10kg, 4kg)

- **Orders**: 100 test orders with various statuses

- **Delivery History**: 6 months of historical delivery data

- **Order Templates**: Recurring order templates for 20% of customers

## Test Credentials

### Admin Users
- **Super Admin**: admin@test.com / adminpass123
- **Manager**: manager@test.com / managerpass123
- **Office Staff**: office@test.com / officepass123

### Driver Accounts
- driver1@test.com / driverpass1
- driver2@test.com / driverpass2
- ... through driver10@test.com / driverpass10

## API Endpoints

### Health Checks
- `GET http://localhost:3001/health` - Basic health check
- `GET http://localhost:3001/api/health` - API health check
- `GET http://localhost:3001/api/v1/health` - Detailed health check
- `GET http://localhost:3001/api/v1/health/ready` - Readiness probe

### Mock Service Endpoints
- **SMS**: `POST http://localhost:8001/mock-sms`
- **E-Invoice**: `POST http://localhost:8002/mock-einvoice`
- **Banking**: `POST http://localhost:8003/mock-banking/payment`

## Load Testing

### Using K6

```bash
# Install k6
brew install k6

# Run load test
k6 run tests/load/api_load_test.js
```

### Using Apache Bench

```bash
# Test authentication endpoint
ab -n 1000 -c 10 -p login.json -T application/json http://localhost:3001/api/v1/auth/login

# Test customer listing
ab -n 1000 -c 10 -H "Authorization: Bearer <token>" http://localhost:3001/api/v1/customers
```

## Security Testing

### OWASP ZAP

```bash
# Start OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:3001
```

### SQLMap (SQL Injection Testing)

```bash
# Test for SQL injection
sqlmap -u "http://localhost:3001/api/v1/customers?search=test" --headers="Authorization: Bearer <token>"
```

## Performance Monitoring

The test environment includes:
- Prometheus metrics at `/metrics`
- Custom performance tracking
- Circuit breaker monitoring

## Troubleshooting

### Port Conflicts

If you see "Port already in use" errors:

```bash
# Find process using port
lsof -i :5433  # PostgreSQL
lsof -i :6380  # Redis
lsof -i :3001  # Backend

# Kill process
kill -9 <PID>
```

### Database Issues

```bash
# Connect to test database
psql -h localhost -p 5433 -U luckygas -d luckygas_test

# Reset test database
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
```

### Backend Startup Issues

Check the backend logs:
```bash
# View backend logs
tail -f backend/logs/app.log

# Check for environment issues
cd backend
ENVIRONMENT=test uv run python -c "from app.core.config import settings; print(settings)"
```

## Clean Up

To completely remove the test environment:

```bash
# Stop all services
./scripts/stop_test_env.sh

# Remove Docker volumes (deletes all test data)
docker-compose -f docker-compose.test.yml down -v

# Remove test database data
docker volume rm luckygas-v3_postgres_test_data
docker volume rm luckygas-v3_redis_test_data
```

## Environment Variables

The test environment uses `.env.test` with these key differences from production:
- Separate database: `luckygas_test`
- Different ports: PostgreSQL (5433), Redis (6380)
- Mock service URLs for SMS, E-Invoice, and Banking
- Test-specific secrets and API keys

## Best Practices

1. **Always use test environment** for load/security testing
2. **Reset data** between major test runs
3. **Monitor resources** during load tests
4. **Document findings** in test reports
5. **Never use production credentials** in test environment

## Next Steps

1. Run initial health checks
2. Verify mock services are responding
3. Test authentication flow
4. Begin load/security testing
5. Monitor and collect metrics