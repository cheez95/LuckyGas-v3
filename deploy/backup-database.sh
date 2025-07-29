#!/bin/bash

# LuckyGas Database Backup Script
# Creates comprehensive backup before deployment

set -euo pipefail

# Configuration
DEPLOYMENT_ID="${1:-$(date +%Y%m%d_%H%M%S)}"
BACKUP_DIR="${BACKUP_DIR:-/backup/database}"
DB_HOST="${DB_HOST:-10.20.30.40}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-luckygas_prod}"
DB_USER="${DB_USER:-luckygas}"
DB_PASSWORD="${DB_PASSWORD:-}"
GCS_BUCKET="${GCS_BUCKET:-gs://lucky-gas-backups}"
RETENTION_DAYS=30

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${2:-}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup filename
BACKUP_FILE="luckygas_${DEPLOYMENT_ID}.sql"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
BACKUP_COMPRESSED="${BACKUP_PATH}.gz"
BACKUP_ENCRYPTED="${BACKUP_COMPRESSED}.enc"

# Export password for pg_dump
export PGPASSWORD="$DB_PASSWORD"

perform_backup() {
    log "Starting database backup..." "$BLUE"
    
    # Get database size
    local db_size=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null || echo "unknown")
    log "Database size: $db_size" "$YELLOW"
    
    # Perform the backup with progress
    log "Backing up database to $BACKUP_PATH..." "$BLUE"
    
    pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-owner \
        --no-privileges \
        --format=plain \
        --encoding=UTF8 \
        --jobs=4 \
        > "$BACKUP_PATH" 2> "${BACKUP_PATH}.log"
    
    if [ $? -eq 0 ]; then
        log "Database backup completed ✓" "$GREEN"
        local backup_size=$(du -h "$BACKUP_PATH" | cut -f1)
        log "Backup size (uncompressed): $backup_size" "$YELLOW"
    else
        log "Database backup failed ✗" "$RED"
        cat "${BACKUP_PATH}.log"
        exit 1
    fi
}

compress_backup() {
    log "Compressing backup..." "$BLUE"
    
    gzip -9 "$BACKUP_PATH"
    
    if [ -f "$BACKUP_COMPRESSED" ]; then
        local compressed_size=$(du -h "$BACKUP_COMPRESSED" | cut -f1)
        log "Backup compressed ✓ Size: $compressed_size" "$GREEN"
    else
        log "Compression failed ✗" "$RED"
        exit 1
    fi
}

encrypt_backup() {
    log "Encrypting backup..." "$BLUE"
    
    # Use deployment ID as part of encryption key for uniqueness
    local encryption_key="${BACKUP_ENCRYPTION_KEY:-$(openssl rand -base64 32)}"
    
    # Encrypt the backup
    openssl enc -aes-256-cbc -salt -in "$BACKUP_COMPRESSED" -out "$BACKUP_ENCRYPTED" -k "$encryption_key"
    
    if [ $? -eq 0 ]; then
        log "Backup encrypted ✓" "$GREEN"
        
        # Store encryption key securely
        echo "$encryption_key" | gcloud secrets create "backup-key-${DEPLOYMENT_ID}" --data-file=- || \
        echo "$encryption_key" | gcloud secrets versions add "backup-key-${DEPLOYMENT_ID}" --data-file=-
        
        # Remove unencrypted files
        rm -f "$BACKUP_COMPRESSED"
    else
        log "Encryption failed ✗" "$RED"
        exit 1
    fi
}

verify_backup() {
    log "Verifying backup integrity..." "$BLUE"
    
    # Create checksum
    local checksum=$(sha256sum "$BACKUP_ENCRYPTED" | cut -d' ' -f1)
    echo "$checksum" > "${BACKUP_ENCRYPTED}.sha256"
    
    # Test decryption (without writing to disk)
    local encryption_key=$(gcloud secrets versions access latest --secret="backup-key-${DEPLOYMENT_ID}")
    
    if openssl enc -aes-256-cbc -d -in "$BACKUP_ENCRYPTED" -k "$encryption_key" | gzip -t; then
        log "Backup integrity verified ✓" "$GREEN"
        log "Checksum: $checksum" "$YELLOW"
    else
        log "Backup integrity check failed ✗" "$RED"
        exit 1
    fi
}

upload_to_gcs() {
    log "Uploading backup to Google Cloud Storage..." "$BLUE"
    
    # Upload encrypted backup
    gsutil -m cp "$BACKUP_ENCRYPTED" "${GCS_BUCKET}/database/${DEPLOYMENT_ID}/"
    
    # Upload checksum
    gsutil cp "${BACKUP_ENCRYPTED}.sha256" "${GCS_BUCKET}/database/${DEPLOYMENT_ID}/"
    
    # Upload backup metadata
    cat > "${BACKUP_DIR}/backup_metadata.json" <<EOF
{
    "deployment_id": "$DEPLOYMENT_ID",
    "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "database_name": "$DB_NAME",
    "backup_size_compressed": "$(du -b "$BACKUP_ENCRYPTED" | cut -f1)",
    "checksum": "$(cat ${BACKUP_ENCRYPTED}.sha256)",
    "retention_days": $RETENTION_DAYS,
    "postgres_version": "$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c 'SELECT version();' | head -1)"
}
EOF
    
    gsutil cp "${BACKUP_DIR}/backup_metadata.json" "${GCS_BUCKET}/database/${DEPLOYMENT_ID}/"
    
    if [ $? -eq 0 ]; then
        log "Backup uploaded to GCS ✓" "$GREEN"
        log "Location: ${GCS_BUCKET}/database/${DEPLOYMENT_ID}/" "$YELLOW"
    else
        log "GCS upload failed ✗" "$RED"
        exit 1
    fi
}

create_quick_restore_script() {
    log "Creating quick restore script..." "$BLUE"
    
    cat > "${BACKUP_DIR}/restore_${DEPLOYMENT_ID}.sh" <<'EOF'
#!/bin/bash
# Quick restore script for deployment: ${DEPLOYMENT_ID}

set -euo pipefail

DEPLOYMENT_ID="${DEPLOYMENT_ID}"
GCS_BUCKET="${GCS_BUCKET}"
DB_HOST="${DB_HOST}"
DB_PORT="${DB_PORT}"
DB_NAME="${DB_NAME}"
DB_USER="${DB_USER}"

# Download backup
echo "Downloading backup from GCS..."
gsutil cp "${GCS_BUCKET}/database/${DEPLOYMENT_ID}/*.enc" /tmp/

# Get encryption key
ENCRYPTION_KEY=$(gcloud secrets versions access latest --secret="backup-key-${DEPLOYMENT_ID}")

# Decrypt and decompress
echo "Decrypting and decompressing backup..."
openssl enc -aes-256-cbc -d -in /tmp/*.enc -k "$ENCRYPTION_KEY" | gunzip > /tmp/restore.sql

# Restore database
echo "Restoring database..."
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME}_old;"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "ALTER DATABASE ${DB_NAME} RENAME TO ${DB_NAME}_old;"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME};"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < /tmp/restore.sql

echo "Database restored successfully!"
EOF
    
    chmod +x "${BACKUP_DIR}/restore_${DEPLOYMENT_ID}.sh"
    log "Restore script created: restore_${DEPLOYMENT_ID}.sh ✓" "$GREEN"
}

cleanup_old_backups() {
    log "Cleaning up old backups..." "$BLUE"
    
    # Clean local backups older than 7 days
    find "$BACKUP_DIR" -name "*.enc" -mtime +7 -delete
    find "$BACKUP_DIR" -name "*.log" -mtime +7 -delete
    
    # Clean GCS backups older than retention period
    local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
    
    gsutil ls "${GCS_BUCKET}/database/" | while read -r backup_path; do
        local backup_date=$(echo "$backup_path" | grep -oE '[0-9]{8}' | head -1 || echo "0")
        if [ "$backup_date" -lt "$cutoff_date" ] && [ "$backup_date" != "0" ]; then
            log "Removing old backup: $backup_path" "$YELLOW"
            gsutil -m rm -r "$backup_path"
        fi
    done
    
    log "Cleanup completed ✓" "$GREEN"
}

backup_application_data() {
    log "Backing up application data..." "$BLUE"
    
    # Backup uploaded files
    if [ -d "/app/uploads" ]; then
        tar -czf "${BACKUP_DIR}/uploads_${DEPLOYMENT_ID}.tar.gz" -C /app uploads/
        gsutil cp "${BACKUP_DIR}/uploads_${DEPLOYMENT_ID}.tar.gz" "${GCS_BUCKET}/uploads/${DEPLOYMENT_ID}/"
        log "Application uploads backed up ✓" "$GREEN"
    fi
    
    # Backup configuration
    tar -czf "${BACKUP_DIR}/config_${DEPLOYMENT_ID}.tar.gz" \
        -C /app \
        .env \
        config/ \
        --exclude='*.key' \
        --exclude='*.pem'
    
    gsutil cp "${BACKUP_DIR}/config_${DEPLOYMENT_ID}.tar.gz" "${GCS_BUCKET}/config/${DEPLOYMENT_ID}/"
    log "Configuration backed up ✓" "$GREEN"
}

generate_backup_report() {
    cat > "${BACKUP_DIR}/backup_report_${DEPLOYMENT_ID}.txt" <<EOF
LuckyGas Database Backup Report
===============================
Deployment ID: $DEPLOYMENT_ID
Date: $(date)
Database: $DB_NAME @ $DB_HOST

Backup Details:
- Original Size: $(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null || echo "unknown")
- Compressed Size: $(du -h "$BACKUP_ENCRYPTED" 2>/dev/null | cut -f1 || echo "unknown")
- Checksum: $(cat ${BACKUP_ENCRYPTED}.sha256 2>/dev/null || echo "unknown")
- GCS Location: ${GCS_BUCKET}/database/${DEPLOYMENT_ID}/
- Encryption Key: Stored in Google Secret Manager (backup-key-${DEPLOYMENT_ID})
- Retention: $RETENTION_DAYS days

Restore Script: restore_${DEPLOYMENT_ID}.sh
===============================
EOF
    
    log "Backup report generated ✓" "$GREEN"
}

# Main backup flow
main() {
    log "=== Starting Database Backup for Deployment $DEPLOYMENT_ID ===" "$BLUE"
    
    # Check prerequisites
    if ! command -v pg_dump &> /dev/null; then
        log "Error: pg_dump not found!" "$RED"
        exit 1
    fi
    
    if ! command -v gsutil &> /dev/null; then
        log "Error: gsutil not found!" "$RED"
        exit 1
    fi
    
    # Perform backup steps
    perform_backup
    compress_backup
    encrypt_backup
    verify_backup
    upload_to_gcs
    create_quick_restore_script
    backup_application_data
    cleanup_old_backups
    generate_backup_report
    
    # Clean up local files (keep only encrypted backup temporarily)
    rm -f "$BACKUP_PATH" "${BACKUP_PATH}.log"
    
    log "=== Database Backup Completed Successfully ===" "$GREEN"
    log "Backup can be restored using: restore_${DEPLOYMENT_ID}.sh" "$YELLOW"
}

# Execute main function
main