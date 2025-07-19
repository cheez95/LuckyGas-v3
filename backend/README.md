# Lucky Gas Backend API

FastAPI backend for the Lucky Gas Delivery Management System.

## Quick Start

### 1. Start Required Services

From the project root directory:
```bash
docker-compose up -d db redis adminer
```

This starts:
- PostgreSQL database on port 5432
- Redis cache on port 6379
- Adminer (database UI) on port 8080

### 2. Run Database Migrations

```bash
# Create database tables
uv run alembic upgrade head

# Import customer data from Excel
uv run python ../database/migrations/001_import_excel.py

# Import drivers/vehicles from SQLite
uv run python ../database/migrations/002_import_sqlite.py
```

### 3. Start the Backend

```bash
# Development mode with auto-reload
uv run python run.py

# Or use uvicorn directly
uv run uvicorn app.main:app --reload
```

The API will be available at:
- http://localhost:8000 - API root
- http://localhost:8000/docs - Interactive API documentation (Swagger UI)
- http://localhost:8000/redoc - Alternative API documentation

### 4. Default Login

- Username: admin@luckygas.tw
- Password: admin123

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login to get JWT token
- `POST /api/v1/auth/register` - Register new user
- `GET /api/v1/auth/me` - Get current user info

### Customers
- `GET /api/v1/customers` - List customers (with pagination)
- `GET /api/v1/customers/{id}` - Get customer details
- `POST /api/v1/customers` - Create new customer
- `PUT /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Soft delete customer

## Environment Variables

Copy `.env.example` to `.env` and update values as needed:

- `SECRET_KEY` - JWT secret key (change in production!)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `GCP_PROJECT_ID` - Google Cloud project ID (for AI features)
- `GOOGLE_MAPS_API_KEY` - Google Maps API key (for route optimization)

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html
```

## Database Management

Access Adminer at http://localhost:8080 with:
- System: PostgreSQL
- Server: localhost
- Username: luckygas
- Password: luckygas123
- Database: luckygas