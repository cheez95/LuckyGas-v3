#!/bin/bash
# LuckyGas Repository Cleanup Script
# Generated: 2025-08-08
# Purpose: Remove 504 unnecessary files (~9.85 MB) while preserving all working code

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
DRY_RUN=false
BACKUP_DIR="cleanup_backup_$(date +%Y%m%d_%H%M%S)"
VERBOSE=false
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --dry-run    Show what would be deleted without actually deleting"
            echo "  --verbose    Show detailed progress"
            echo "  --force      Skip confirmation prompt"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to log messages
log() {
    if [ "$VERBOSE" = true ]; then
        echo -e "$1"
    fi
}

# Function to remove file with backup
remove_file() {
    local file="$1"
    if [ -f "$file" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY-RUN] Would remove: $file"
        else
            # Create backup directory structure
            local dir=$(dirname "$file")
            mkdir -p "$BACKUP_DIR/$dir"
            # Copy to backup
            cp "$file" "$BACKUP_DIR/$file" 2>/dev/null || true
            # Remove file
            rm -f "$file"
            log "  ${GREEN}✓${NC} Removed: $file"
        fi
        return 0
    fi
    return 1
}

# Function to remove directory
remove_directory() {
    local dir="$1"
    if [ -d "$dir" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY-RUN] Would remove directory: $dir"
        else
            # Create backup
            mkdir -p "$BACKUP_DIR/$(dirname "$dir")"
            cp -r "$dir" "$BACKUP_DIR/$dir" 2>/dev/null || true
            # Remove directory
            rm -rf "$dir"
            log "  ${GREEN}✓${NC} Removed directory: $dir"
        fi
        return 0
    fi
    return 1
}

# Print header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   LuckyGas Repository Cleanup Script   ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Running in DRY-RUN mode - no files will be deleted${NC}"
    echo ""
fi

# Show summary
echo "This script will remove:"
echo "  • 38 backend duplicate files (1.5 MB)"
echo "  • 383 Python cache files (500 KB)"
echo "  • 47 outdated documentation files (5 MB)"
echo "  • 16 debug/test scripts in root (350 KB)"
echo "  • 12 frontend duplicate files (1.5 MB)"
echo "  • 8 configuration duplicates (1 MB)"
echo ""
echo -e "${GREEN}Total: 504 files, ~9.85 MB${NC}"
echo -e "${YELLOW}All working code will be preserved${NC}"
echo ""

# Confirmation prompt (unless --force is used)
if [ "$FORCE" = false ] && [ "$DRY_RUN" = false ]; then
    read -p "Do you want to proceed? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cleanup cancelled."
        exit 0
    fi
fi

# Create backup directory (if not dry-run)
if [ "$DRY_RUN" = false ]; then
    echo -e "\n${BLUE}Creating backup in: $BACKUP_DIR${NC}"
    mkdir -p "$BACKUP_DIR"
fi

# Initialize counters
REMOVED_COUNT=0
FAILED_COUNT=0
SPACE_SAVED=0

echo -e "\n${BLUE}Starting cleanup...${NC}\n"

# ============================================================================
# PART 1: Backend Cleanup
# ============================================================================

echo -e "${YELLOW}[1/6] Removing backend duplicate files...${NC}"

# Remove files with " 2" suffix
for file in backend/*" 2".*; do
    if remove_file "$file"; then
        ((REMOVED_COUNT++))
    fi
done

# Remove files with " 3" suffix
for file in backend/*" 3".*; do
    if remove_file "$file"; then
        ((REMOVED_COUNT++))
    fi
done

# Remove test duplicates
remove_file "backend/tests/mock-services/gcp/test-credentials 2.json" && ((REMOVED_COUNT++))
remove_file "backend/tests/mock-services/gcp/test-credentials 3.json" && ((REMOVED_COUNT++))
remove_file "backend/tests/contracts/consumer/test_example_new_feature.py 2.example" && ((REMOVED_COUNT++))
remove_file "backend/tests/contracts/consumer/test_example_new_feature.py 3.example" && ((REMOVED_COUNT++))
remove_file "backend/tests/init-scripts/01-init-test-db 2.sql" && ((REMOVED_COUNT++))
remove_file "backend/tests/init-scripts/01-init-test-db 3.sql" && ((REMOVED_COUNT++))

# Remove unused service files
remove_file "backend/app/services/order_service_updated.py" && ((REMOVED_COUNT++))
remove_file "backend/app/api/v1/health_simple.py" && ((REMOVED_COUNT++))
remove_file "backend/app/api/v1/websocket_simple.py" && ((REMOVED_COUNT++))

# ============================================================================
# PART 2: Debug/Test Scripts Cleanup
# ============================================================================

echo -e "${YELLOW}[2/6] Removing debug/test scripts from backend root...${NC}"

BACKEND_SCRIPTS=(
    "backend/check_customer_schema.py"
    "backend/check_drivers_schema.py"
    "backend/check_orders_schema.py"
    "backend/check_users.py"
    "backend/create_test_user.py"
    "backend/create_initial_migration.py"
    "backend/analyze_database.py"
    "backend/analyze_test_coverage.py"
    "backend/create_test_data.py"
    "backend/init_test_data.py"
    "backend/init_test_db.py"
    "backend/security_audit.py"
    "backend/simple_app.py"
    "backend/run_all_tests.py"
    "backend/generate_coverage_visualization.py"
    "backend/ui_deep_examination.py"
)

for script in "${BACKEND_SCRIPTS[@]}"; do
    if remove_file "$script"; then
        ((REMOVED_COUNT++))
    fi
done

# ============================================================================
# PART 3: Python Cache Cleanup
# ============================================================================

echo -e "${YELLOW}[3/6] Cleaning Python cache files...${NC}"

# Remove __pycache__ directories
if [ "$DRY_RUN" = true ]; then
    echo "  [DRY-RUN] Would remove all __pycache__ directories"
    CACHE_COUNT=$(find . -type d -name __pycache__ 2>/dev/null | wc -l)
    echo "  [DRY-RUN] Found $CACHE_COUNT __pycache__ directories"
else
    CACHE_COUNT=0
    while IFS= read -r -d '' pycache; do
        rm -rf "$pycache"
        ((CACHE_COUNT++))
        log "  ${GREEN}✓${NC} Removed cache: $pycache"
    done < <(find . -type d -name __pycache__ -print0 2>/dev/null)
    ((REMOVED_COUNT+=CACHE_COUNT))
fi

# Remove .pyc and .pyo files
if [ "$DRY_RUN" = true ]; then
    PYC_COUNT=$(find . -name "*.pyc" -o -name "*.pyo" 2>/dev/null | wc -l)
    echo "  [DRY-RUN] Found $PYC_COUNT .pyc/.pyo files"
else
    PYC_COUNT=0
    find . -name "*.pyc" -o -name "*.pyo" -exec rm -f {} \; 2>/dev/null
    log "  ${GREEN}✓${NC} Removed .pyc and .pyo files"
fi

# ============================================================================
# PART 4: Documentation Cleanup
# ============================================================================

echo -e "${YELLOW}[4/6] Removing outdated documentation...${NC}"

OUTDATED_DOCS=(
    "GCP_SETUP_GUIDE.md"
    "GCP_SETUP_README.md"
    "SETUP_INSTRUCTIONS.md"
    "GOOGLE_API_INTEGRATION.md"
    "E_INVOICE_SECURITY_CHECKLIST.md"
    "E_INVOICE_FIXES_REQUIRED.md"
    "SMS_GATEWAY_README.md"
    "SECURITY_KEY_INVENTORY.md"
    "DATABASE_SETUP.md"
    "CI_CD_FIX_STATUS.md"
    "TEST_ENVIRONMENT_FIXES.md"
    "TEST_RECOVERY_GUIDE.md"
    "PROJECT_TASKS.md"
    "PARALLEL_EXECUTION_PLAN.md"
    "TEST_FIX_ACTION_PLAN.md"
    "MONITORING_INSTRUCTIONS.md"
    "API_ENHANCEMENTS_README.md"
    "INTEGRATION_TEST_RESULTS.md"
    "TEST_COVERAGE_DELIVERABLES.md"
    "TEST_COVERAGE_ANALYSIS.md"
    "GCP-INTEGRATION-ERRORS-RESOLUTION.md"
    "FRONTEND_PRODUCTION_ARCHITECTURE_REVIEW.md"
    "PRODUCTION_SECURITY_IMPLEMENTATION.md"
    "BIGQUERY_BILLING_EXPORT_GUIDE.md"
)

for doc in "${OUTDATED_DOCS[@]}"; do
    if remove_file "$doc"; then
        ((REMOVED_COUNT++))
    fi
done

# Remove migration documentation
MIGRATION_DOCS=(
    "migrations/data_migration/BUSINESS_RULES_VALIDATION.md"
    "migrations/data_migration/ROLLBACK_PROCEDURES.md"
    "migrations/data_migration/DAY3_DELIVERY_MIGRATION_PLAN.md"
    "migrations/data_migration/HANDOFF_DEVIN_TO_SAM.md"
    "migrations/data_migration/DATA_MIGRATION_ANALYSIS.md"
    "migrations/data_migration/BUSINESS_LOGIC_CLARIFICATIONS_NEEDED.md"
    "migrations/data_migration/EDGE_CASE_HANDLING_GUIDE.md"
    "migrations/data_migration/PRODUCTION_MIGRATION_LOG.md"
    "migrations/data_migration/MIGRATION_COORDINATION_SCRIPT.md"
)

for doc in "${MIGRATION_DOCS[@]}"; do
    if remove_file "backend/$doc"; then
        ((REMOVED_COUNT++))
    fi
done

# Remove duplicate READMEs
DUPLICATE_READMES=(
    "backend/app/scripts/MIGRATION_README.md"
    "backend/app/services/google_cloud/ROUTES_API_README.md"
    "backend/tests/README.md"
    "backend/tests/TEST_ENVIRONMENT_README.md"
    "backend/tests/contracts/CONTRACT_TESTING_GUIDE.md"
    "backend/tests/contracts/QUICK_REFERENCE.md"
    "backend/.pytest_cache/README.md"
    "backend/tests/integration/.pytest_cache/README.md"
)

for readme in "${DUPLICATE_READMES[@]}"; do
    if remove_file "$readme"; then
        ((REMOVED_COUNT++))
    fi
done

# ============================================================================
# PART 5: Frontend Cleanup
# ============================================================================

echo -e "${YELLOW}[5/6] Cleaning frontend files...${NC}"

# Remove test files
FRONTEND_FILES=(
    "frontend/fix-duplicate-tests.cjs"
    "frontend/fix-duplicate-tests 2.cjs"
    "frontend/public/test-service-worker.html"
    "frontend/public/test-service-worker 2.html"
    "frontend/public/test-service-worker 3.html"
    "frontend/src/components/Analytics/FuelSavingsChart 4.tsx"
    "frontend/src/components/Analytics/FuelSavingsChart 5.tsx"
    "frontend/src/components/Analytics/WeeklyTrendChart 4.tsx"
    "frontend/src/components/Analytics/WeeklyTrendChart 5.tsx"
)

for file in "${FRONTEND_FILES[@]}"; do
    if remove_file "$file"; then
        ((REMOVED_COUNT++))
    fi
done

# ============================================================================
# PART 6: Root Directory Cleanup
# ============================================================================

echo -e "${YELLOW}[6/6] Cleaning root directory...${NC}"

# Remove configuration duplicates
remove_file "nginx 2.conf" && ((REMOVED_COUNT++))

# Remove deployment script duplicates
remove_file "deploy_integrated_backend 2.sh" && ((REMOVED_COUNT++))

# Remove verification scripts (if they exist)
for file in verify_*.py; do
    if [ -f "$file" ]; then
        if remove_file "$file"; then
            ((REMOVED_COUNT++))
        fi
    fi
done

# ============================================================================
# Backup Files Cleanup
# ============================================================================

echo -e "\n${YELLOW}Removing old backup files...${NC}"

# Remove old .env backups
remove_file "backend/.env.backup" && ((REMOVED_COUNT++))
remove_file "backend/.env.test.backup" && ((REMOVED_COUNT++))

# ============================================================================
# Summary
# ============================================================================

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}           Cleanup Complete!            ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY-RUN Summary:${NC}"
    echo "  • Files that would be removed: ~504"
    echo "  • Space that would be saved: ~9.85 MB"
    echo ""
    echo "Run without --dry-run to actually perform the cleanup."
else
    # Calculate approximate space saved
    if [ -d "$BACKUP_DIR" ]; then
        BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
        echo -e "${GREEN}Cleanup Summary:${NC}"
        echo "  • Files removed: $REMOVED_COUNT"
        echo "  • Space saved: ~$BACKUP_SIZE"
        echo "  • Backup created: $BACKUP_DIR"
        echo ""
        echo -e "${YELLOW}Note:${NC} Backup directory can be deleted after verification:"
        echo "  rm -rf $BACKUP_DIR"
    else
        echo -e "${GREEN}Cleanup Summary:${NC}"
        echo "  • Files removed: $REMOVED_COUNT"
        echo "  • Estimated space saved: ~9.85 MB"
    fi
fi

echo ""
echo -e "${GREEN}✅ Repository cleanup completed successfully!${NC}"

# Optional: Run git status to show changes
if command -v git &> /dev/null && [ "$DRY_RUN" = false ]; then
    echo ""
    echo -e "${BLUE}Git status after cleanup:${NC}"
    git status --short | head -20
    DELETED_COUNT=$(git status --short | grep -c "^ D ")
    if [ $DELETED_COUNT -gt 20 ]; then
        echo "... and $((DELETED_COUNT - 20)) more deleted files"
    fi
fi

exit 0