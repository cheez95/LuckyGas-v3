#!/bin/bash
# Set up test environment variables

export ENVIRONMENT=test
export TESTING=true

# Database
export POSTGRES_SERVER=localhost
export POSTGRES_USER=luckygas
export POSTGRES_PASSWORD=luckygas123
export POSTGRES_DB=luckygas_test
export DATABASE_URL="postgresql+asyncpg://luckygas:luckygas123@localhost:5432/luckygas_test"

# Redis
export REDIS_URL="redis://localhost:6379/1"

# Security
export SECRET_KEY="test-secret-key-for-testing-only"
export FIRST_SUPERUSER=admin
export FIRST_SUPERUSER_EMAIL=admin@luckygas.tw
export FIRST_SUPERUSER_PASSWORD=TestAdmin123!

# CORS
export BACKEND_CORS_ORIGINS='["http://localhost:3000","http://localhost:80","http://testserver"]'

# JWT
export ACCESS_TOKEN_EXPIRE_MINUTES=30
export REFRESH_TOKEN_EXPIRE_DAYS=7

# Google Cloud (disabled for tests)
export GOOGLE_CLOUD_PROJECT=""
export GOOGLE_APPLICATION_CREDENTIALS=""
export GOOGLE_MAPS_API_KEY=""
export VERTEX_AI_LOCATION=""
export VERTEX_AI_MODEL_NAME=""

# Logging
export LOG_LEVEL=DEBUG

# Rate limiting
export RATE_LIMIT_ENABLED=false

echo "Test environment variables set!"