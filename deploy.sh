#!/bin/bash
# Lucky Gas Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    print_info "Creating .env from .env.example..."
    cp .env.example .env
    print_info "Please update .env with your actual values before running this script again."
    exit 1
fi

# Parse command
COMMAND=${1:-help}

case $COMMAND in
    "build")
        print_info "Building Docker images..."
        docker-compose build
        print_success "Build completed!"
        ;;
        
    "up")
        print_info "Starting services..."
        docker-compose up -d
        print_success "Services started!"
        print_info "Access the application at:"
        echo "  - Frontend: http://localhost"
        echo "  - Backend API: http://localhost:8000"
        echo "  - API Docs: http://localhost:8000/docs"
        ;;
        
    "down")
        print_info "Stopping services..."
        docker-compose down
        print_success "Services stopped!"
        ;;
        
    "restart")
        print_info "Restarting services..."
        docker-compose restart
        print_success "Services restarted!"
        ;;
        
    "logs")
        SERVICE=${2:-}
        if [ -z "$SERVICE" ]; then
            docker-compose logs -f --tail=100
        else
            docker-compose logs -f --tail=100 $SERVICE
        fi
        ;;
        
    "setup")
        print_info "Running initial database setup..."
        docker-compose --profile setup run --rm setup
        print_success "Database setup completed!"
        ;;
        
    "migrate")
        print_info "Running database migrations..."
        docker-compose exec backend python manage.py init-db
        docker-compose exec backend python manage.py create-indexes
        print_success "Migrations completed!"
        ;;
        
    "import-data")
        print_info "Importing historical data..."
        docker-compose exec backend python manage.py migrate-data
        print_success "Data import completed!"
        ;;
        
    "shell")
        SERVICE=${2:-backend}
        print_info "Opening shell in $SERVICE container..."
        docker-compose exec $SERVICE sh
        ;;
        
    "test")
        print_info "Running tests..."
        docker-compose exec backend pytest
        print_success "Tests completed!"
        ;;
        
    "clean")
        print_info "Cleaning up Docker resources..."
        docker-compose down -v
        docker system prune -f
        print_success "Cleanup completed!"
        ;;
        
    "tools")
        print_info "Starting admin tools..."
        docker-compose --profile tools up -d
        print_success "Admin tools started!"
        print_info "Access admin tools at:"
        echo "  - Adminer: http://localhost:8080"
        echo "  - pgAdmin: http://localhost:5050"
        echo "  - Redis Commander: http://localhost:8081"
        ;;
        
    "backup")
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p $BACKUP_DIR
        print_info "Creating backup in $BACKUP_DIR..."
        
        # Backup database
        docker-compose exec -T postgres pg_dump -U luckygas luckygas > "$BACKUP_DIR/database.sql"
        
        # Backup environment
        cp .env "$BACKUP_DIR/.env.backup"
        
        print_success "Backup completed!"
        ;;
        
    "restore")
        BACKUP_FILE=${2:-}
        if [ -z "$BACKUP_FILE" ]; then
            print_error "Please specify backup file: ./deploy.sh restore backups/YYYYMMDD_HHMMSS/database.sql"
            exit 1
        fi
        
        print_info "Restoring from $BACKUP_FILE..."
        docker-compose exec -T postgres psql -U luckygas luckygas < "$BACKUP_FILE"
        print_success "Restore completed!"
        ;;
        
    "status")
        print_info "Service Status:"
        docker-compose ps
        ;;
        
    "update")
        print_info "Updating services..."
        git pull
        docker-compose build
        docker-compose up -d
        docker-compose exec backend python manage.py migrate
        print_success "Update completed!"
        ;;
        
    "help"|*)
        echo "Lucky Gas Deployment Script"
        echo ""
        echo "Usage: ./deploy.sh [command] [options]"
        echo ""
        echo "Commands:"
        echo "  build          Build Docker images"
        echo "  up             Start all services"
        echo "  down           Stop all services"
        echo "  restart        Restart all services"
        echo "  logs [service] View logs (optionally for specific service)"
        echo "  setup          Run initial database setup"
        echo "  migrate        Run database migrations"
        echo "  import-data    Import historical data from Excel files"
        echo "  shell [service] Open shell in container (default: backend)"
        echo "  test           Run test suite"
        echo "  clean          Clean up Docker resources"
        echo "  tools          Start admin tools (Adminer, pgAdmin, Redis Commander)"
        echo "  backup         Create database backup"
        echo "  restore [file] Restore database from backup"
        echo "  status         Show service status"
        echo "  update         Update and restart services"
        echo "  help           Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./deploy.sh build        # Build images"
        echo "  ./deploy.sh up           # Start services"
        echo "  ./deploy.sh logs backend # View backend logs"
        echo "  ./deploy.sh shell        # Open backend shell"
        ;;
esac