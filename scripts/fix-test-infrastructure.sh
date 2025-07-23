#!/bin/bash
# Lucky Gas Test Infrastructure Fix Script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo -e "${BLUE}🔧 Lucky Gas Test Infrastructure Fix Script${NC}"
echo ""

# Function to check if PostgreSQL is running
check_postgres() {
    echo -e "${YELLOW}Checking PostgreSQL status...${NC}"
    if command -v pg_isready &> /dev/null; then
        if pg_isready -q; then
            echo -e "${GREEN}✓ PostgreSQL is running${NC}"
            return 0
        else
            echo -e "${RED}✗ PostgreSQL is not running${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  pg_isready not found, assuming PostgreSQL is running${NC}"
        return 0
    fi
}

# Function to setup test database
setup_test_database() {
    echo -e "${YELLOW}Setting up test database...${NC}"
    
    # Check if user exists
    if psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='luckygas'" | grep -q 1; then
        echo -e "${GREEN}✓ User 'luckygas' already exists${NC}"
    else
        echo "Creating user 'luckygas'..."
        createuser -U postgres luckygas || echo "User might already exist"
    fi
    
    # Set password
    psql -U postgres -c "ALTER USER luckygas WITH PASSWORD 'luckygas123';" || true
    
    # Check if database exists
    if psql -U postgres -lqt | cut -d \| -f 1 | grep -qw luckygas_test; then
        echo -e "${GREEN}✓ Database 'luckygas_test' already exists${NC}"
    else
        echo "Creating database 'luckygas_test'..."
        createdb -U postgres -O luckygas luckygas_test
    fi
    
    # Grant privileges
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE luckygas_test TO luckygas;" || true
    
    echo -e "${GREEN}✓ Test database setup complete${NC}"
}

# Function to fix async test decorators
fix_async_decorators() {
    echo -e "${YELLOW}Fixing async test decorators...${NC}"
    
    cd "$BACKEND_DIR"
    
    # Count files that need fixing
    count=$(grep -r "async def test_" tests/ --include="*.py" | grep -v "@pytest.mark.asyncio" | wc -l)
    
    if [ "$count" -gt 0 ]; then
        echo "Found $count async tests without proper decorators"
        
        # Create a Python script to fix the decorators
        cat > fix_async_tests.py << 'EOF'
import os
import re

def fix_async_tests(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern to find async test functions without @pytest.mark.asyncio
    pattern = r'(\n)([ \t]*)(async def test_\w+)'
    
    # Check if file imports pytest
    if 'import pytest' not in content:
        content = 'import pytest\n' + content
    
    # Function to check if @pytest.mark.asyncio exists before the function
    def needs_decorator(match):
        indent = match.group(2)
        # Look backwards for decorator
        pos = match.start()
        lines_before = content[:pos].split('\n')
        if lines_before and '@pytest.mark.asyncio' in lines_before[-1]:
            return match.group(0)  # Already has decorator
        return f"\n{indent}@pytest.mark.asyncio{match.group(0)}"
    
    # Apply fix
    fixed_content = re.sub(pattern, needs_decorator, content)
    
    if fixed_content != content:
        with open(filepath, 'w') as f:
            f.write(fixed_content)
        return True
    return False

# Fix all test files
fixed_count = 0
for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py') and file.startswith('test_'):
            filepath = os.path.join(root, file)
            if fix_async_tests(filepath):
                fixed_count += 1
                print(f"Fixed: {filepath}")

print(f"\nFixed {fixed_count} files")
EOF
        
        # Run the fix script
        uv run python fix_async_tests.py
        rm fix_async_tests.py
    else
        echo -e "${GREEN}✓ All async tests already have proper decorators${NC}"
    fi
}

# Function to create comprehensive conftest.py
create_conftest() {
    echo -e "${YELLOW}Creating comprehensive conftest.py...${NC}"
    
    cat > "$BACKEND_DIR/tests/conftest.py" << 'EOF'
import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
from unittest.mock import Mock, MagicMock, AsyncMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["TESTING"] = "true"

# Mock Google Cloud services before importing app
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['google.cloud.aiplatform'] = MagicMock()
sys.modules['google.oauth2.service_account'] = MagicMock()

from app.main import app
from app.core.config import settings
from app.core.database import Base
from app.models import *  # Import all models

# Test database URL
TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    from app.api.deps import get_db
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    mock.expire = AsyncMock(return_value=True)
    mock.ttl = AsyncMock(return_value=-1)
    return mock

@pytest.fixture
def mock_google_services():
    """Mock all Google Cloud services."""
    # Mock Vertex AI
    mock_vertex_ai = MagicMock()
    mock_vertex_ai.predict = AsyncMock(return_value={
        "predictions": [100, 95, 110],
        "confidence": 0.85
    })
    
    # Mock Routes API
    mock_routes = MagicMock()
    mock_routes.calculate_route = AsyncMock(return_value={
        "routes": [{
            "distanceMeters": 5000,
            "duration": "600s",
            "polyline": {"encodedPolyline": "test_polyline"}
        }]
    })
    
    # Mock Maps API
    mock_maps = MagicMock()
    mock_maps.geocode = AsyncMock(return_value=[{
        "geometry": {"location": {"lat": 25.0330, "lng": 121.5654}}
    }])
    
    return {
        "vertex_ai": mock_vertex_ai,
        "routes": mock_routes,
        "maps": mock_maps
    }

# Playwright fixtures (if needed)
try:
    from playwright.async_api import async_playwright, Browser, Page
    
    @pytest_asyncio.fixture(scope="session")
    async def browser() -> AsyncGenerator[Browser, None]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=not pytest.config.getoption("--headed", default=False)
            )
            yield browser
            await browser.close()
    
    @pytest_asyncio.fixture(scope="function")
    async def page(browser: Browser) -> AsyncGenerator[Page, None]:
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="zh-TW"
        )
        page = await context.new_page()
        yield page
        await context.close()
        
except ImportError:
    pass  # Playwright not required for all tests
EOF
    
    echo -e "${GREEN}✓ Created comprehensive conftest.py${NC}"
}

# Function to install missing dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing missing test dependencies...${NC}"
    
    cd "$BACKEND_DIR"
    
    # Install test dependencies
    uv pip install pytest-asyncio pytest-mock pytest-cov httpx faker pytest-playwright
    
    # Install Playwright browsers
    uv run playwright install
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting test infrastructure fixes...${NC}"
    echo ""
    
    # Check PostgreSQL
    if ! check_postgres; then
        echo -e "${RED}Please start PostgreSQL before running this script${NC}"
        echo "On macOS: brew services start postgresql@14"
        echo "On Linux: sudo systemctl start postgresql"
        exit 1
    fi
    
    # Setup test database
    setup_test_database
    
    # Install dependencies
    install_dependencies
    
    # Fix async decorators
    fix_async_decorators
    
    # Create comprehensive conftest
    create_conftest
    
    echo ""
    echo -e "${GREEN}✅ Test infrastructure fixes complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run tests: cd backend && pytest -v"
    echo "2. Run with coverage: pytest --cov=app --cov-report=html"
    echo "3. Run E2E tests: pytest tests/e2e --headed"
    echo ""
    echo "To run all tests with coverage:"
    echo "  ./scripts/run-tests.sh all true"
}

# Run main function
main "$@"