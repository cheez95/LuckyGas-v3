# Contributing to Lucky Gas Delivery Management System

Thank you for your interest in contributing to the Lucky Gas project! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Process](#development-process)
4. [Coding Standards](#coding-standards)
5. [Submitting Changes](#submitting-changes)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Accept constructive criticism gracefully
- Focus on what's best for the project and users
- Show empathy towards other contributors

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing others' private information
- Any conduct that would be inappropriate in a professional setting

## Getting Started

### Prerequisites

- Python 3.11+ (managed with `uv`)
- Node.js 18+ and npm
- PostgreSQL 14+
- Redis 6.2+
- Git

### Setting Up Development Environment

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/LuckyGas-v3.git
   cd LuckyGas-v3
   ```

2. **Backend Setup**
   ```bash
   cd backend
   uv pip install -r requirements.txt
   uv pip install -r requirements-dev.txt
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

4. **Database Setup**
   ```bash
   # Create PostgreSQL database
   createdb luckygas_dev
   
   # Run migrations
   cd backend
   uv run alembic upgrade head
   ```

## Development Process

### Branch Naming

- `feature/` - New features (e.g., `feature/customer-analytics`)
- `fix/` - Bug fixes (e.g., `fix/route-optimization-error`)
- `docs/` - Documentation updates (e.g., `docs/api-endpoints`)
- `refactor/` - Code refactoring (e.g., `refactor/cache-service`)
- `test/` - Test additions/updates (e.g., `test/order-service`)

### Workflow

1. Create a new branch from `main`
2. Make your changes following coding standards
3. Write/update tests for your changes
4. Update documentation if needed
5. Commit with clear, descriptive messages
6. Push to your fork and create a pull request

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints for all functions
- Maximum line length: 88 characters (Black formatter)
- Docstrings in Google style for all public functions
- Use `async/await` for I/O operations

```python
async def get_customer(customer_id: int) -> Optional[Customer]:
    """
    Retrieve a customer by ID.
    
    Args:
        customer_id: The unique identifier of the customer
        
    Returns:
        Customer object if found, None otherwise
        
    Raises:
        DatabaseError: If database connection fails
    """
    # Implementation
```

### TypeScript (Frontend)

- Use strict mode
- Prefer interfaces over type aliases
- Use functional components with hooks
- Follow ESLint configuration
- Meaningful component and variable names

```typescript
interface CustomerProps {
  customerId: string;
  onUpdate: (data: CustomerData) => Promise<void>;
}

const CustomerDetails: React.FC<CustomerProps> = ({ customerId, onUpdate }) => {
  // Implementation
};
```

### Commit Messages

Follow conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Example:
```
feat(orders): add bulk order import functionality

Implemented CSV import for bulk order creation with validation
and error reporting. Supports up to 1000 orders per import.

Closes #123
```

## Submitting Changes

### Pull Request Process

1. **Update your branch**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Run tests locally**
   ```bash
   # Backend tests
   cd backend
   uv run pytest
   
   # Frontend tests
   cd frontend
   npm test
   ```

3. **Check code quality**
   ```bash
   # Backend
   uv run black .
   uv run ruff check .
   uv run mypy .
   
   # Frontend
   npm run lint
   npm run type-check
   ```

4. **Create Pull Request**
   - Use a clear, descriptive title
   - Reference related issues (e.g., "Fixes #123")
   - Describe what changes were made and why
   - Include screenshots for UI changes
   - Ensure all CI checks pass

### Review Process

- At least one maintainer review required
- Address all review comments
- Keep discussions focused and professional
- Update PR based on feedback
- Squash commits if requested

## Testing Guidelines

### Backend Testing

- Write unit tests for all new functions
- Use pytest fixtures for common test data
- Mock external services (Google APIs, etc.)
- Aim for >80% code coverage

```python
@pytest.mark.asyncio
async def test_create_customer(db_session):
    """Test customer creation with valid data."""
    customer_data = CustomerCreate(
        name="測試客戶",
        phone="0912345678",
        address="台北市信義區"
    )
    
    service = CustomerService(db_session)
    customer = await service.create_customer(customer_data)
    
    assert customer.id is not None
    assert customer.name == "測試客戶"
```

### Frontend Testing

- Use React Testing Library
- Test user interactions, not implementation
- Write integration tests for critical paths
- Mock API calls

```typescript
describe('CustomerList', () => {
  it('displays customers in Traditional Chinese', async () => {
    render(<CustomerList />);
    
    await waitFor(() => {
      expect(screen.getByText('客戶列表')).toBeInTheDocument();
    });
  });
});
```

## Documentation

### What to Document

- API endpoints (OpenAPI/Swagger)
- Component props and usage
- Complex algorithms or business logic
- Configuration options
- Traditional Chinese translations

### Documentation Standards

- Keep documentation close to code
- Update docs with code changes
- Include examples where helpful
- Use clear, concise language
- Provide both English and Traditional Chinese where appropriate

### API Documentation Example

```python
@router.post("/customers", response_model=Customer)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new customer.
    
    建立新客戶
    
    - **name**: Customer name (客戶名稱)
    - **phone**: Phone number (電話號碼)
    - **address**: Delivery address (配送地址)
    """
```

## Questions or Need Help?

- Check existing issues and documentation
- Ask in discussions or create an issue
- Join our developer chat (if available)
- Email maintainers for sensitive issues

Thank you for contributing to Lucky Gas! 🚀