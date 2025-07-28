#!/bin/bash
# setup_tests.sh - Test environment setup script

# Set environment variables
export PYTHONPATH="/Users/lgee258/Desktop/LuckyGas-v3/backend:$PYTHONPATH"
export ENVIRONMENT="test"
export DATABASE_URL="postgresql://test:test@localhost:5432/luckygas_test"
export DISABLE_GOOGLE_APIS="true"
export JWT_SECRET_KEY="test-secret-key-for-testing-only"
export REDIS_URL="redis://localhost:6379/1"

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up test environment...${NC}"

# Check if docker-compose.test.yml exists
if [ -f "docker-compose.test.yml" ]; then
    echo -e "${GREEN}Starting test database...${NC}"
    docker-compose -f docker-compose.test.yml up -d
else
    echo -e "${RED}docker-compose.test.yml not found. Creating it...${NC}"
    # Create a basic test docker-compose file
    cat > docker-compose.test.yml << EOF
version: '3.8'
services:
  postgres_test:
    image: postgres:15
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: luckygas_test
    ports:
      - "5432:5432"
    volumes:
      - test_postgres_data:/var/lib/postgresql/data

  redis_test:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  test_postgres_data:
EOF
    docker-compose -f docker-compose.test.yml up -d
fi

# Wait for database to be ready
echo -e "${GREEN}Waiting for database to be ready...${NC}"
sleep 5

# Run migrations
echo -e "${GREEN}Running database migrations...${NC}"
uv run alembic upgrade head

# Seed test data if script exists
if [ -f "app/scripts/setup_test_users.py" ]; then
    echo -e "${GREEN}Seeding test data...${NC}"
    uv run python app/scripts/setup_test_users.py
else
    echo -e "${RED}Test data script not found. Skipping...${NC}"
fi

# Install/update dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
uv sync

echo -e "${GREEN}Test environment setup complete!${NC}"
echo -e "${GREEN}You can now run tests with: uv run pytest${NC}"