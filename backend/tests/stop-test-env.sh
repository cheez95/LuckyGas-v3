#!/bin/bash

# Stop Lucky Gas Test Environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛑 Stopping Lucky Gas Test Environment..."
echo "========================================="

# Stop containers
echo "🐳 Stopping Docker containers..."
docker-compose -f docker-compose.test.yml down

# Ask if user wants to remove volumes
read -p "🗑️  Do you want to remove test data volumes? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing volumes..."
    docker-compose -f docker-compose.test.yml down -v
fi

echo ""
echo "✅ Test environment stopped successfully!"
echo "========================================="