# Lucky Gas V3 Development Environment Setup Guide

## Prerequisites

- Docker Desktop installed and running
- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL client tools (optional)
- Git

## Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd LuckyGas-v3
```

### 2. Start Infrastructure Services
```bash
# Start PostgreSQL and Redis using Docker Compose
docker compose up -d

# Verify services are running
docker compose ps
```

### 3. Backend Setup
```bash
cd backend

# Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Create .env file (if not exists)
cp .env.example .env

# Initialize database
uv run alembic upgrade head

# Seed test data
uv run python app/scripts/init_test_users.py
uv run python app/scripts/seed_gas_products.py
uv run python app/scripts/seed_driver_test_data.py

# Start backend server
uv run uvicorn app.main:app --reload --port 8001
```

### 4. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file (if not exists)
cp .env.example .env

# Start development server
npm run dev
```

### 5. E2E Test Setup
```bash
cd ../tests/e2e

# Install dependencies
npm install

# Install Playwright browsers
npx playwright install

# Run tests
npm test
```

## Detailed Configuration

### PostgreSQL Database

Default connection settings in `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://luckygas:luckygas123@localhost:5432/luckygas_test
POSTGRES_SERVER=localhost
POSTGRES_USER=luckygas
POSTGRES_PASSWORD=luckygas123
POSTGRES_DB=luckygas_test
```

### Redis Configuration

Default connection settings:
```env
REDIS_URL=redis://localhost:6379/1
```

### Backend API Configuration

```env
# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### Frontend Configuration

Create `frontend/.env`:
```env
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
VITE_APP_TITLE=Lucky Gas 幸福氣
```

## Service URLs

- Frontend: http://localhost:5173
- Backend API: http://localhost:8001
- API Documentation: http://localhost:8001/api/v1/docs
- WebSocket: ws://localhost:8001/api/v1/websocket/ws
- Socket.IO: http://localhost:8001/socket.io

## Common Commands

### Database Management
```bash
# Create new migration
cd backend
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1

# Reset database
docker compose down -v  # Remove volumes
docker compose up -d    # Recreate
```

### Running Tests
```bash
# Backend tests
cd backend
uv run pytest

# Frontend tests
cd frontend
npm test

# E2E tests
cd tests/e2e
npm test

# E2E tests with UI
npm test -- --headed

# Specific test file
npm test -- specs/driver-workflow.spec.ts
```

### Code Quality
```bash
# Backend
cd backend
uv run black app/        # Format code
uv run flake8 app/      # Lint
uv run mypy app/        # Type check

# Frontend
cd frontend
npm run lint            # Lint
npm run type-check      # Type check
npm run format          # Format code
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :8001  # Mac/Linux
netstat -ano | findstr :8001  # Windows

# Kill process
kill -9 <PID>  # Mac/Linux
taskkill /PID <PID> /F  # Windows
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker compose ps

# Check logs
docker compose logs postgres

# Connect manually
psql -h localhost -U luckygas -d luckygas_test
```

### Frontend Can't Connect to Backend
1. Check backend is running on port 8001
2. Verify VITE_API_URL in frontend/.env
3. Check CORS settings in backend/.env
4. Check browser console for errors

### WebSocket Connection Failed
1. Verify WebSocket service is initialized
2. Check authentication token in localStorage
3. Verify WebSocket URL configuration
4. Check browser network tab for WS connections

## Test Data

### Default Test Users
After running `init_test_users.py`:

| Email | Password | Role |
|-------|----------|------|
| admin@luckygas.com.tw | Admin123! | super_admin |
| manager@luckygas.com.tw | Manager123! | manager |
| office@luckygas.com.tw | Office123! | office_staff |
| driver@luckygas.com.tw | Driver123! | driver |
| customer@example.com | Customer123! | customer |

### Sample Data Scripts
- `seed_gas_products.py` - Creates gas products catalog
- `seed_driver_test_data.py` - Creates routes and deliveries for testing
- `import_excel_data.py` - Import customer data from Excel

## Development Workflow

1. **Feature Development**
   - Create feature branch
   - Implement backend API
   - Add frontend components
   - Write tests
   - Update documentation

2. **Testing**
   - Unit tests for business logic
   - Integration tests for APIs
   - E2E tests for user workflows
   - Manual testing for UI/UX

3. **Code Review**
   - Run linters and formatters
   - Ensure tests pass
   - Update API documentation
   - Create pull request

4. **Deployment**
   - Merge to main branch
   - Run CI/CD pipeline
   - Deploy to staging
   - Run smoke tests

## Additional Resources

- [API Documentation](http://localhost:8001/api/v1/docs)
- [Migration Guide](./MIGRATION_PROGRESS_REPORT.md)
- [Sprint Plan](./MIGRATION_SPRINT_PLAN.md)
- [Architecture Decisions](./PLANNING.md)