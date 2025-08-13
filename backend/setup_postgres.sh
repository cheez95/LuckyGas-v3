#!/bin/bash

echo "🐘 Setting up PostgreSQL for Lucky Gas"
echo "======================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}PostgreSQL not found. Installing...${NC}"
    
    # Detect OS and install PostgreSQL
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "Installing PostgreSQL via Homebrew..."
            brew install postgresql@15
            brew services start postgresql@15
            # Add to PATH for current session
            export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
        else
            echo -e "${RED}Please install Homebrew first: https://brew.sh${NC}"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "Installing PostgreSQL via apt..."
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    else
        echo -e "${RED}Unsupported OS. Please install PostgreSQL manually.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ PostgreSQL is already installed${NC}"
fi

# Wait for PostgreSQL to be ready
echo -n "Waiting for PostgreSQL to start"
for i in {1..10}; do
    if pg_isready &> /dev/null; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Create database
echo ""
echo "Creating database 'luckygas'..."
createdb luckygas 2>/dev/null && echo -e "${GREEN}✓ Database created${NC}" || echo -e "${YELLOW}Database may already exist${NC}"

# Create user and grant privileges
echo "Setting up database user..."
psql -d postgres << EOF 2>/dev/null
-- Create user if not exists
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'luckygas') THEN
      CREATE USER luckygas WITH PASSWORD 'luckygas123';
   END IF;
END
\$\$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE luckygas TO luckygas;
ALTER USER luckygas CREATEDB;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database user configured${NC}"
else
    echo -e "${YELLOW}User may already exist${NC}"
fi

# Test connection
echo ""
echo "Testing database connection..."
PGPASSWORD=luckygas123 psql -U luckygas -d luckygas -h localhost -c "SELECT 1" &> /dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Connection successful!${NC}"
else
    echo -e "${YELLOW}⚠ Connection test failed. Trying without password...${NC}"
    psql -U luckygas -d luckygas -c "SELECT 1" &> /dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Connection successful (no password)${NC}"
    else
        echo -e "${RED}✗ Could not connect to database${NC}"
        echo "Please check PostgreSQL installation and try again"
    fi
fi

echo ""
echo "======================================="
echo -e "${GREEN}✅ PostgreSQL setup complete!${NC}"
echo "======================================="
echo ""
echo "Connection Details:"
echo "  Database: luckygas"
echo "  User:     luckygas"
echo "  Password: luckygas123"
echo "  Host:     localhost"
echo "  Port:     5432"
echo ""
echo "Connection URL:"
echo "  postgresql://luckygas:luckygas123@localhost:5432/luckygas"
echo ""