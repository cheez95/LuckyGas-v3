# Database Setup Guide

This guide explains how to set up and initialize the Lucky Gas database for development and testing.

## Prerequisites

- PostgreSQL 14+ installed and running
- Python 3.11+ with `uv` package manager
- Database user with CREATE DATABASE privileges

## Configuration

The database configuration is managed through environment variables in `.env` files:

- `.env` - Development environment
- `.env.test` - Test environment
- `.env.production` - Production environment

Key configuration variables:
```bash
POSTGRES_SERVER=localhost
POSTGRES_PORT=5433
POSTGRES_USER=luckygas
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=luckygas
```

## Database URLs

The application uses two database URLs:

1. **Async URL** (`DATABASE_URL`) - Used by the FastAPI application with asyncpg
   ```
   postgresql+asyncpg://user:password@host:port/database
   ```

2. **Sync URL** (`DATABASE_URL_SYNC`) - Used by Alembic migrations
   ```
   postgresql://user:password@host:port/database
   ```

Both URLs are automatically generated from the individual PostgreSQL settings.

## Migration System

We use Alembic for database migrations. The migration files are located in `alembic/versions/`.

### Migration Chain

The migrations follow this order:
```
001_initial_schema
└── 002_orders_and_deliveries
    └── 003_invoicing_and_inventory
        └── 004_add_delivery_history_items
            └── 005_fix_route_driver_foreign_key
                ├── 006_add_security_fields_to_users
                │   └── 007_create_api_keys_table ─┐
                ├── 006_add_invoice_sequence ──────┤
                ├── 006_add_banking_tables ────────┤
                └── 007_add_notification_tables    │
                    └── 008_rename_metadata_columns│
                        └── add_sync_operations    │
                            ├── add_sms_tables     │
                            │   └── add_banking_sftp│
                            │       └── optimization│
                            └── add_feature_flags──┘
                                            │
                                009_merge_branches
```

## Setup Scripts

### 1. Initialize Test Database

```bash
# Create and set up test database with migrations
uv run python scripts/init_test_db.py

# With test data
uv run python scripts/init_test_db.py --with-data
```

### 2. Verify Database Setup

```bash
# Check if database is properly configured
uv run python scripts/verify_db_setup.py
```

### 3. Fix Migration Chain

```bash
# Analyze and report migration chain issues
uv run python scripts/fix_migration_chain.py
```

## Common Tasks

### Create Development Database

```bash
# Connect to PostgreSQL as superuser
psql -U postgres

# Create database and user
CREATE DATABASE luckygas;
CREATE USER luckygas WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE luckygas TO luckygas;
\q
```

### Run Migrations

```bash
# Upgrade to latest migration
uv run alembic upgrade head

# Check current revision
uv run alembic current

# Show migration history
uv run alembic history
```

### Create New Migration

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "description of changes"

# Create empty migration
uv run alembic revision -m "description of changes"
```

### Rollback Migrations

```bash
# Rollback one migration
uv run alembic downgrade -1

# Rollback to specific revision
uv run alembic downgrade <revision_id>

# Rollback all migrations
uv run alembic downgrade base
```

## Troubleshooting

### Error: "relation already exists"

This happens when trying to create a table that already exists. Solutions:
1. Drop and recreate the database
2. Use `IF NOT EXISTS` in migration files
3. Check if you're running migrations twice

### Error: "revision not found"

This indicates a broken migration chain. Run:
```bash
uv run python scripts/fix_migration_chain.py
```

### Error: "asyncpg not supported by Alembic"

Alembic requires synchronous database drivers. The configuration automatically uses `DATABASE_URL_SYNC` which uses the `postgresql://` driver instead of `postgresql+asyncpg://`.

### Error: "multiple heads"

This means there are multiple migration branches. We've created a merge migration (`009_merge_branches`) to consolidate them. If this happens again, create a new merge migration.

## Testing Database Setup

For pytest, the database configuration is in `pytest.ini`:
```ini
[pytest]
env = 
    TESTING=1
    DATABASE_URL=sqlite+aiosqlite:///./test.db
    DATABASE_URL_SYNC=sqlite:///./test.db
```

To use PostgreSQL for tests instead:
```bash
# Set test environment variables
export DATABASE_URL="postgresql+asyncpg://luckygas:password@localhost:5433/luckygas_test"
export DATABASE_URL_SYNC="postgresql://luckygas:password@localhost:5433/luckygas_test"

# Run tests
uv run pytest
```

## Production Considerations

1. **Never run auto-generated migrations in production without review**
2. **Always backup before running migrations**
3. **Use migration locks to prevent concurrent migrations**
4. **Test migrations on a staging database first**
5. **Keep migration files in version control**

## Database Schema

Key tables include:
- `users` - System users and authentication
- `customers` - Customer information
- `products` - Gas products catalog
- `orders` - Customer orders
- `delivery_routes` - Optimized delivery routes
- `payments` - Payment records
- `invoices` - Generated invoices
- `notifications` - System notifications
- `optimization_history` - Route optimization history

For detailed schema information, see the migration files in `alembic/versions/`.