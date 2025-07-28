#!/bin/bash

# Fix PostgreSQL Docker Permission Issues
# This script provides multiple solutions for the permission denied error

echo "=== PostgreSQL Docker Permission Fix Script ==="
echo "Current issue: UID mismatch between volume data (UID 999) and postgres:15-alpine (UID 70)"
echo ""

# Function to check if PostgreSQL container is running
check_postgres_status() {
    if docker ps | grep -q "luckygas-postgres"; then
        echo "⚠️  PostgreSQL container is currently running (but restarting due to errors)"
        return 0
    else
        echo "✓ PostgreSQL container is not running"
        return 1
    fi
}

# Function to stop PostgreSQL
stop_postgres() {
    echo "Stopping PostgreSQL container..."
    docker compose -f docker-compose.yml stop postgres
    docker compose -f docker-compose.yml rm -f postgres
}

echo "Choose a solution:"
echo "1. Quick Fix - Remove volume and start fresh (⚠️  DATA LOSS)"
echo "2. Safe Fix - Change ownership of existing data to UID 70"
echo "3. Alternative Fix - Use postgres:15 (non-alpine) image"
echo "4. Custom Fix - Create a wrapper script to handle permissions"
echo "5. Exit"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "=== Quick Fix: Remove volume and start fresh ==="
        echo "⚠️  WARNING: This will DELETE all existing PostgreSQL data!"
        read -p "Are you sure you want to continue? (yes/no): " confirm
        
        if [ "$confirm" = "yes" ]; then
            stop_postgres
            echo "Removing PostgreSQL volume..."
            docker volume rm luckygas-v3_postgres_data
            echo "✓ Volume removed"
            echo ""
            echo "Starting PostgreSQL with fresh volume..."
            docker compose -f docker-compose.yml up -d postgres
            echo ""
            echo "✓ PostgreSQL should now start successfully with correct permissions"
        else
            echo "Operation cancelled"
        fi
        ;;
        
    2)
        echo ""
        echo "=== Safe Fix: Change ownership of existing data ==="
        stop_postgres
        
        echo "Fixing permissions inside the volume..."
        # Use a temporary container to fix permissions
        docker run --rm -v luckygas-v3_postgres_data:/data alpine sh -c "
            echo 'Current permissions:'
            ls -la /data
            echo ''
            echo 'Changing ownership to UID 70 (postgres user in alpine)...'
            chown -R 70:70 /data
            echo ''
            echo 'New permissions:'
            ls -la /data
        "
        
        echo ""
        echo "Starting PostgreSQL..."
        docker compose -f docker-compose.yml up -d postgres
        echo ""
        echo "✓ Permissions fixed. PostgreSQL should now start successfully"
        ;;
        
    3)
        echo ""
        echo "=== Alternative Fix: Use non-alpine PostgreSQL image ==="
        stop_postgres
        
        echo "Creating a temporary docker-compose override file..."
        cat > docker-compose.override.yml << 'EOF'
version: '3.8'

services:
  postgres:
    # Override to use non-alpine version which typically uses UID 999
    image: postgres:15
EOF
        
        echo "✓ Created docker-compose.override.yml"
        echo ""
        echo "Starting PostgreSQL with non-alpine image..."
        docker compose -f docker-compose.yml up -d postgres
        echo ""
        echo "✓ PostgreSQL should now start with the non-alpine image"
        echo "Note: The override file will persist. Delete it to revert to alpine image."
        ;;
        
    4)
        echo ""
        echo "=== Custom Fix: Create permission wrapper ==="
        stop_postgres
        
        echo "Creating custom entrypoint script..."
        mkdir -p ./postgres-init
        cat > ./postgres-init/fix-permissions.sh << 'EOF'
#!/bin/bash
# Custom entrypoint to fix permissions before starting PostgreSQL

echo "Fixing PostgreSQL data directory permissions..."

# Ensure the postgres user owns the data directory
if [ -d "/var/lib/postgresql/data" ]; then
    chown -R postgres:postgres /var/lib/postgresql/data
fi

# Call the original entrypoint
exec docker-entrypoint.sh "$@"
EOF
        
        chmod +x ./postgres-init/fix-permissions.sh
        
        echo "Creating Dockerfile for custom PostgreSQL image..."
        cat > ./postgres-init/Dockerfile << 'EOF'
FROM postgres:15-alpine

# Copy our custom entrypoint
COPY fix-permissions.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/fix-permissions.sh

# Use our custom entrypoint
ENTRYPOINT ["/usr/local/bin/fix-permissions.sh"]
CMD ["postgres"]
EOF
        
        echo "Building custom PostgreSQL image..."
        docker build -t luckygas-postgres-fixed ./postgres-init/
        
        echo "Creating docker-compose override for custom image..."
        cat > docker-compose.override.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: luckygas-postgres-fixed
EOF
        
        echo "Starting PostgreSQL with custom image..."
        docker compose -f docker-compose.yml up -d postgres
        echo ""
        echo "✓ Custom PostgreSQL image with permission fixes created and started"
        ;;
        
    5)
        echo "Exiting without changes"
        exit 0
        ;;
        
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=== Checking PostgreSQL Status ==="
sleep 5
docker compose -f docker-compose.yml ps postgres
docker compose -f docker-compose.yml logs --tail=10 postgres

echo ""
echo "=== Additional Recommendations ==="
echo "1. For production, use named volumes (as you're already doing)"
echo "2. Avoid bind mounts for PostgreSQL data on macOS"
echo "3. Consider using the postgres:15 (non-alpine) image for better compatibility"
echo "4. The docker-compose.postgres-only.yml file in your project has good examples"
echo ""
echo "If issues persist, check:"
echo "- Docker Desktop permissions"
echo "- Available disk space"
echo "- Docker daemon logs: docker logs"