# Contract Testing Guide for Lucky Gas API

## Overview

This guide documents the contract testing implementation for the Lucky Gas Delivery Management System using Pact. Contract testing ensures API stability between the frontend (consumer) and backend (provider), preventing breaking changes and enabling independent development.

## What is Contract Testing?

Contract testing is a technique for testing integration points between different services or components by:
- Recording the interactions between services
- Verifying both sides of the integration comply with the recorded interactions
- Ensuring changes don't break existing integrations

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│                 │         │                 │         │                 │
│  Frontend       │  Pact   │  Pact Broker   │  Pact   │  Backend API   │
│  (Consumer)     │ ──────> │  (Optional)    │ <────── │  (Provider)    │
│                 │         │                 │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
        │                                                        │
        │                    Contract File                       │
        └───────────────────────────────────────────────────────┘
```

## Key Components

### 1. Consumer Tests
Location: `tests/contracts/consumer/`

These tests define what the frontend expects from the backend API:
- **test_customer_api_contract.py** - Customer management endpoints
- **test_order_api_contract.py** - Order management endpoints
- **test_auth_api_contract.py** - Authentication endpoints
- **test_prediction_api_contract.py** - AI prediction endpoints

### 2. Provider Tests
Location: `tests/contracts/provider/`

These tests verify that the backend API meets the frontend's expectations:
- **test_provider_verification.py** - Verifies all consumer contracts

### 3. Pact Files
Location: `tests/contracts/pacts/`

Generated JSON files containing the contract specifications.

## Running Contract Tests

### Prerequisites

```bash
# Install contract testing dependencies
cd backend
uv pip install pact-python
```

### Run Consumer Tests

```bash
# Generate pact files from consumer expectations
python tests/contracts/run_contract_tests.py --consumer-only
```

### Run Provider Tests

```bash
# Verify provider meets consumer expectations
python tests/contracts/run_contract_tests.py --provider-only
```

### Run All Tests

```bash
# Run both consumer and provider tests
python tests/contracts/run_contract_tests.py
```

### Additional Options

```bash
# Skip publishing to Pact Broker
python tests/contracts/run_contract_tests.py --skip-publish

# Check if it's safe to deploy
python tests/contracts/run_contract_tests.py --check-deploy
```

## CI/CD Integration

The contract tests are integrated into the CI/CD pipeline via GitHub Actions:

### Workflow: `.github/workflows/contract-tests.yml`

1. **Consumer Tests Job**
   - Runs on every PR and push to main/develop
   - Generates pact files
   - Uploads artifacts for provider testing

2. **Provider Tests Job**
   - Downloads pact files from consumer tests
   - Sets up test database and services
   - Verifies provider compliance

3. **Can-I-Deploy Job**
   - Runs only on main branch
   - Checks with Pact Broker if deployment is safe
   - Prevents breaking changes from being deployed

## Writing New Contract Tests

### Consumer Test Example

```python
def test_new_endpoint(self, pact: Any, mock_provider_url: str) -> None:
    """Test contract for new endpoint."""
    expected_response = {
        "id": 1,
        "data": "example"
    }
    
    (pact
     .given("precondition state")
     .upon_receiving("description of request")
     .with_request(
         method="GET",
         path="/api/v1/new-endpoint",
         headers=auth_headers()
     )
     .will_respond_with(
         status=200,
         headers={"Content-Type": "application/json"},
         body=expected_response
     ))
    
    with pact:
        response = requests.get(
            f"{mock_provider_url}/api/v1/new-endpoint",
            headers=auth_headers()
        )
        
        assert response.status_code == 200
        assert response.json() == expected_response
```

### Provider State Setup

```python
@self.verifier.provider_state("precondition state")
async def setup_state():
    # Set up database state
    # Create test data
    pass
```

## Best Practices

### 1. Test Data Consistency
Use the data generators in `conftest.py` to ensure consistent test data:
- `generate_customer_data()`
- `generate_order_data()`
- `generate_auth_token_response()`
- `generate_prediction_data()`

### 2. Provider States
- Keep provider states simple and focused
- Use descriptive state names
- Clean up after each test

### 3. Contract Evolution
- Version your contracts
- Use Pact Broker for contract management
- Follow semantic versioning

### 4. Testing Strategy
- Focus on critical integration points
- Test happy paths and error scenarios
- Don't test implementation details

## Pact Broker Setup (Optional)

To use Pact Broker for contract management:

1. **Set Environment Variables**
   ```bash
   export PACT_BROKER_URL=https://your-pact-broker.com
   export PACT_BROKER_USERNAME=your-username
   export PACT_BROKER_PASSWORD=your-password
   ```

2. **Publish Contracts**
   ```bash
   python tests/contracts/run_contract_tests.py
   ```

3. **View Contracts**
   Visit your Pact Broker URL to view contracts, versions, and verification results.

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill process using port 8888
   lsof -ti:8888 | xargs kill -9
   ```

2. **Pact File Not Found**
   - Ensure consumer tests run before provider tests
   - Check `tests/contracts/pacts/` directory

3. **Provider State Not Found**
   - Add missing provider state handler
   - Check state name matches exactly

### Debug Mode

```python
# Enable Pact debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Benefits of Contract Testing

1. **API Stability** 🔒
   - Prevents breaking changes
   - Ensures backward compatibility

2. **Independent Development** 🚀
   - Frontend and backend teams work independently
   - Reduces integration issues

3. **Living Documentation** 📝
   - Contracts serve as API documentation
   - Always up-to-date with actual usage

4. **Early Detection** 🛡️
   - Catch issues before deployment
   - Reduce production incidents

5. **Confidence in Changes** ✅
   - Safe refactoring
   - Clear impact analysis

## Contract Testing vs Other Testing Types

| Testing Type | Purpose | Scope | Speed |
|-------------|---------|-------|-------|
| Unit Tests | Test individual components | Single function/class | Fast |
| Contract Tests | Test integration points | API interactions | Medium |
| Integration Tests | Test full system integration | Multiple services | Slow |
| E2E Tests | Test user workflows | Full application | Very Slow |

## Future Enhancements

1. **Pact Broker Integration**
   - Centralized contract storage
   - Version management
   - Can-i-deploy checks

2. **Message Queue Contracts**
   - Test async messaging contracts
   - Event-driven architecture support

3. **Performance Contracts**
   - Response time expectations
   - Payload size limits

4. **GraphQL Support**
   - Contract testing for GraphQL APIs
   - Schema evolution tracking

## Resources

- [Pact Documentation](https://docs.pact.io/)
- [Contract Testing Best Practices](https://docs.pact.io/best_practices)
- [Pact Python Guide](https://github.com/pact-foundation/pact-python)

## Contact

For questions or issues with contract testing:
- Check this guide first
- Review existing contract tests
- Contact the QA team (Sam) for assistance