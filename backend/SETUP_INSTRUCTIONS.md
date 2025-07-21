# Lucky Gas Backend Setup Instructions

## Prerequisites

- Python 3.12+ installed
- PostgreSQL server running (default port 5433)
- Redis server running (default port 6379)
- `uv` package manager installed

## Initial Setup

### 1. Install Dependencies

```bash
cd backend
uv pip install -r requirements.txt
```

### 2. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Generate a secure SECRET_KEY:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. Edit `.env` and set the following required variables:
   - `SECRET_KEY`: Use the generated key from step 2
   - `POSTGRES_PASSWORD`: Your PostgreSQL password
   - `FIRST_SUPERUSER_PASSWORD`: Set a strong admin password (min 8 characters)
   - `DATABASE_URL`: Should match your PostgreSQL settings
   - `REDIS_URL`: Should match your Redis settings

### 3. Database Setup

1. Ensure PostgreSQL is running on port 5433
2. Create the database and user if they don't exist:
   ```sql
   CREATE USER luckygas WITH PASSWORD 'your-password';
   CREATE DATABASE luckygas OWNER luckygas;
   ```

3. The application will automatically create tables on first startup

### 4. Start the Application

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server should start and be available at:
- API: http://localhost:8000
- Health Check: http://localhost:8000/health
- API Documentation: http://localhost:8000/docs

## Security Improvements Applied

✅ All critical security changes have been implemented:

1. **No Hardcoded Credentials**: All sensitive values must be set via environment variables
2. **Secure SECRET_KEY**: Must be at least 32 characters, generated using cryptographically secure methods
3. **CORS Restrictions**: Limited to specific methods and headers (no wildcards)
4. **HTTPS Enforcement**: Automatically enabled in production environment
5. **API Key Management**: Secure storage system for Google API keys
6. **Access Token Expiration**: Reduced from 8 days to 2 hours

## Adding Google API Keys (Production)

Once the basic setup is working:

1. Add Google API keys to `.env`:
   ```
   GOOGLE_MAPS_API_KEY=AIza...
   GCP_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

2. The system will automatically:
   - Encrypt and store API keys securely
   - Monitor usage and costs
   - Apply rate limiting
   - Use mock services in development mode

## Common Issues

### Import Errors
- Fixed: Pydantic v2 compatibility (`regex` → `pattern`)
- Fixed: Import paths for api_key_manager
- Fixed: DeliveryHistory import from correct module
- Fixed: CircuitBreaker initialization parameters

### Database Connection
- Fixed: Removed keepalives parameters (not supported by asyncpg)
- Ensure PostgreSQL is running on port 5433
- Check DATABASE_URL format: `postgresql+asyncpg://user:password@localhost:5433/dbname`

### Environment Variables
- The application uses Pydantic Settings to load from `.env` file
- Environment validation is handled automatically during settings initialization

## Monitoring & Dashboard

Access the Google API monitoring dashboard at:
- `/api/v1/google-api/dashboard` - View API usage and costs
- `/api/v1/google-api/dashboard/costs` - Detailed cost breakdown
- `/api/v1/google-api/dashboard/rate-limits` - Rate limit status

Note: Dashboard endpoints require admin authentication.

## Development Tips

1. **Use Development Mode**: The system automatically uses mock services when Google API keys are not configured
2. **Check Logs**: Structured JSON logging provides detailed debugging information
3. **Run Tests**: `uv run pytest` to ensure everything is working correctly
4. **API Documentation**: Visit `/docs` for interactive API documentation

## Next Steps

1. Configure frontend to connect to backend API
2. Set up Google Cloud credentials for production
3. Configure monitoring and alerting
4. Set up CI/CD pipeline
5. Deploy to production environment