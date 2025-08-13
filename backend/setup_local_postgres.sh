#!/bin/bash

echo "🚀 Lucky Gas Local PostgreSQL Setup"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Setup PostgreSQL
echo "Step 1: Setting up PostgreSQL..."
echo "--------------------------------"
chmod +x setup_postgres.sh
./setup_postgres.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}PostgreSQL setup failed. Please fix the issues and try again.${NC}"
    exit 1
fi

# Step 2: Install Python dependencies
echo ""
echo "Step 2: Installing Python dependencies..."
echo "-----------------------------------------"
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

echo "Installing requirements..."
uv pip install -r requirements_simple.txt
uv pip install python-dotenv  # For loading .env.local

# Step 3: Load environment variables
echo ""
echo "Step 3: Setting up environment..."
echo "----------------------------------"
if [ -f .env.local ]; then
    echo -e "${GREEN}✓ Found .env.local${NC}"
    # Export environment variables
    export $(cat .env.local | grep -v '^#' | xargs)
else
    echo -e "${RED}✗ .env.local not found!${NC}"
    echo "Please create .env.local with your database configuration"
    exit 1
fi

# Step 4: Initialize database
echo ""
echo "Step 4: Initializing database..."
echo "---------------------------------"
uv run python init_db.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Database initialization failed.${NC}"
    exit 1
fi

# Step 5: Start the backend (optional)
echo ""
echo "===================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "===================================="
echo ""
echo "You can now start the backend with:"
echo "  uv run python run_backend.py"
echo ""
echo "Or use the full stack starter:"
echo "  cd .. && ./start_local.sh"
echo ""
echo "API will be available at:"
echo "  http://localhost:8000"
echo "  http://localhost:8000/docs (API Documentation)"
echo ""

# Ask if user wants to start the backend now
read -p "Do you want to start the backend now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${GREEN}Starting Lucky Gas Backend...${NC}"
    echo "Press Ctrl+C to stop"
    echo ""
    uv run python run_backend.py
fi