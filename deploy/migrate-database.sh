#!/bin/bash

# LuckyGas Database Migration Script
# Safely applies database migrations with rollback capability

set -euo pipefail

# Configuration
DEPLOYMENT_ID="${DEPLOYMENT_ID:-$(date +%Y%m%d_%H%M%S)}"
BACKEND_DIR="/Users/lgee258/Desktop/LuckyGas-v3/backend"
DB_HOST="${DB_HOST:-10.20.30.40}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-luckygas_prod}"
DB_USER="${DB_USER:-luckygas}"
DB_PASSWORD="${DB_PASSWORD:-}"
MIGRATION_LOG="migrations_${DEPLOYMENT_ID}.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${2:-}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$MIGRATION_LOG"
}

# Export database credentials
export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
export PGPASSWORD="$DB_PASSWORD"

check_prerequisites() {
    log "Checking migration prerequisites..." "$BLUE"
    
    # Check if alembic is installed
    if ! command -v alembic &> /dev/null; then
        log "Installing alembic..." "$YELLOW"
        cd "$BACKEND_DIR"
        uv pip install alembic
    fi
    
    # Check database connectivity
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
        log "Database connection verified ✓" "$GREEN"
    else
        log "Cannot connect to database!" "$RED"
        exit 1
    fi
    
    # Check if migrations directory exists
    if [ ! -d "${BACKEND_DIR}/alembic" ]; then
        log "Error: Alembic migrations directory not found!" "$RED"
        exit 1
    fi
}

get_current_revision() {
    cd "$BACKEND_DIR"
    local current=$(alembic current 2>/dev/null | grep -oE '[a-f0-9]{12}' | head -1 || echo "base")
    echo "$current"
}

get_latest_revision() {
    cd "$BACKEND_DIR"
    local latest=$(alembic heads 2>/dev/null | grep -oE '[a-f0-9]{12}' | head -1 || echo "")
    echo "$latest"
}

check_pending_migrations() {
    log "Checking for pending migrations..." "$BLUE"
    
    local current_rev=$(get_current_revision)
    local latest_rev=$(get_latest_revision)
    
    log "Current revision: $current_rev" "$YELLOW"
    log "Latest revision: $latest_rev" "$YELLOW"
    
    if [ "$current_rev" = "$latest_rev" ]; then
        log "Database is up to date, no migrations needed" "$GREEN"
        return 1
    else
        # List pending migrations
        cd "$BACKEND_DIR"
        log "Pending migrations:" "$YELLOW"
        alembic history -r"${current_rev}:${latest_rev}" | tee -a "$MIGRATION_LOG"
        return 0
    fi
}

validate_migrations() {
    log "Validating migration files..." "$BLUE"
    
    cd "$BACKEND_DIR"
    
    # Check for migration conflicts
    local heads_count=$(alembic heads 2>/dev/null | wc -l)
    if [ "$heads_count" -gt 1 ]; then
        log "Error: Multiple migration heads detected! Manual merge required." "$RED"
        alembic heads
        exit 1
    fi
    
    # Run migration syntax check
    if python -m py_compile alembic/versions/*.py 2>/dev/null; then
        log "Migration syntax valid ✓" "$GREEN"
    else
        log "Migration syntax errors detected!" "$RED"
        exit 1
    fi
    
    # Check for 預定配送日期 field references
    if grep -r "預計配送日期" alembic/versions/ 2>/dev/null; then
        log "WARNING: Found incorrect field name '預計配送日期' in migrations!" "$RED"
        log "Should be '預定配送日期' - please fix before continuing" "$RED"
        exit 1
    fi
}

create_migration_backup() {
    log "Creating migration state backup..." "$BLUE"
    
    local current_rev=$(get_current_revision)
    echo "Previous version: $current_rev" >> "$MIGRATION_LOG"
    
    # Backup alembic_version table
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -t alembic_version \
        > "alembic_version_backup_${DEPLOYMENT_ID}.sql"
    
    log "Migration state backed up ✓" "$GREEN"
}

apply_migrations() {
    log "Applying database migrations..." "$BLUE"
    
    cd "$BACKEND_DIR"
    
    # Run migrations with output capture
    if alembic upgrade head 2>&1 | tee -a "$MIGRATION_LOG"; then
        log "Migrations applied successfully ✓" "$GREEN"
        
        # Record new revision
        local new_rev=$(get_current_revision)
        echo "New version: $new_rev" >> "$MIGRATION_LOG"
    else
        log "Migration failed!" "$RED"
        return 1
    fi
}

verify_migration_success() {
    log "Verifying migration success..." "$BLUE"
    
    # Check if we're at the latest revision
    local current_rev=$(get_current_revision)
    local latest_rev=$(get_latest_revision)
    
    if [ "$current_rev" = "$latest_rev" ]; then
        log "Database is at latest revision ✓" "$GREEN"
    else
        log "Database is not at latest revision!" "$RED"
        return 1
    fi
    
    # Run custom migration tests
    cd "$BACKEND_DIR"
    
    # Test critical fields exist
    log "Checking critical database fields..." "$BLUE"
    
    # Check 預定配送日期 field exists in orders table
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
        "SELECT column_name FROM information_schema.columns WHERE table_name='orders' AND column_name='預定配送日期';" \
        | grep -q "預定配送日期"; then
        log "✓ Field '預定配送日期' exists in orders table" "$GREEN"
    else
        log "✗ Field '預定配送日期' not found in orders table!" "$RED"
        return 1
    fi
    
    # Check other critical tables
    local required_tables=("customers" "orders" "users" "products" "routes" "drivers")
    for table in "${required_tables[@]}"; do
        if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
            "SELECT 1 FROM information_schema.tables WHERE table_name='$table';" \
            | grep -q "1"; then
            log "✓ Table '$table' exists" "$GREEN"
        else
            log "✗ Table '$table' not found!" "$RED"
            return 1
        fi
    done
}

run_post_migration_scripts() {
    log "Running post-migration scripts..." "$BLUE"
    
    # Update database statistics
    log "Updating database statistics..." "$YELLOW"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ANALYZE;"
    
    # Create any required indexes
    if [ -f "${BACKEND_DIR}/alembic/post_migration.sql" ]; then
        log "Running post-migration SQL..." "$YELLOW"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            < "${BACKEND_DIR}/alembic/post_migration.sql"
    fi
    
    # Data migrations for Taiwan-specific fields
    log "Checking Taiwan-specific data migrations..." "$YELLOW"
    
    # Ensure phone numbers are in correct format
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Update phone format if needed
UPDATE customers 
SET phone = REGEXP_REPLACE(phone, '^09([0-9]{8})$', '09\\1')
WHERE phone ~ '^09[0-9]{8}$';

-- Ensure addresses have proper format
UPDATE customers
SET address = TRIM(address)
WHERE address != TRIM(address);
EOF
    
    log "Post-migration scripts completed ✓" "$GREEN"
}

generate_migration_report() {
    cat > "migration_report_${DEPLOYMENT_ID}.txt" <<EOF
LuckyGas Database Migration Report
==================================
Deployment ID: $DEPLOYMENT_ID
Date: $(date)
Database: $DB_NAME @ $DB_HOST

Migration Summary:
$(grep -E "(Previous|New) version:" "$MIGRATION_LOG" || echo "No version information")

Tables Verified:
- customers ✓
- orders (with 預定配送日期) ✓
- users ✓
- products ✓
- routes ✓
- drivers ✓

Migration Log: $MIGRATION_LOG
==================================
EOF
    
    log "Migration report generated ✓" "$GREEN"
}

rollback_migrations() {
    log "Rolling back migrations..." "$RED"
    
    if [ -f "alembic_version_backup_${DEPLOYMENT_ID}.sql" ]; then
        # Restore alembic version
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            < "alembic_version_backup_${DEPLOYMENT_ID}.sql"
        
        # Get previous version and downgrade
        local previous_rev=$(grep "Previous version:" "$MIGRATION_LOG" | cut -d: -f2 | tr -d ' ')
        if [ -n "$previous_rev" ] && [ "$previous_rev" != "base" ]; then
            cd "$BACKEND_DIR"
            alembic downgrade "$previous_rev"
            log "Rolled back to revision: $previous_rev" "$YELLOW"
        fi
    else
        log "No backup found for rollback!" "$RED"
    fi
}

# Main migration flow
main() {
    log "=== Starting Database Migration ===" "$BLUE"
    
    check_prerequisites
    
    if check_pending_migrations; then
        validate_migrations
        create_migration_backup
        
        if apply_migrations; then
            if verify_migration_success; then
                run_post_migration_scripts
                generate_migration_report
                log "=== Database Migration Completed Successfully ===" "$GREEN"
                exit 0
            else
                log "Migration verification failed!" "$RED"
                rollback_migrations
                exit 1
            fi
        else
            log "Migration application failed!" "$RED"
            rollback_migrations
            exit 1
        fi
    else
        log "=== No Migrations Needed ===" "$GREEN"
        exit 0
    fi
}

# Execute main function
main