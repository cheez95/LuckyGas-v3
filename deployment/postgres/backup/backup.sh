#!/bin/bash
# PostgreSQL Backup Script for Lucky Gas
# Performs full and incremental backups with retention management

set -euo pipefail

# Configuration
BACKUP_DIR="/backups"
POSTGRES_HOST="${POSTGRES_HOST:-postgres-primary}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-luckygas}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-gzip}"
LOG_FILE="/var/log/postgres_backup.log"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}/full" "${BACKUP_DIR}/wal" "${BACKUP_DIR}/incremental"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Error handling
handle_error() {
    log "ERROR: Backup failed at line $1"
    exit 1
}
trap 'handle_error $LINENO' ERR

# Check disk space
check_disk_space() {
    local required_space_gb=10
    local available_space_gb=$(df -BG "${BACKUP_DIR}" | awk 'NR==2 {print int($4)}')
    
    if [ "${available_space_gb}" -lt "${required_space_gb}" ]; then
        log "ERROR: Insufficient disk space. Required: ${required_space_gb}GB, Available: ${available_space_gb}GB"
        exit 1
    fi
}

# Perform full backup using pg_basebackup
perform_full_backup() {
    local backup_name="full_backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="${BACKUP_DIR}/full/${backup_name}"
    
    log "Starting full backup: ${backup_name}"
    
    # Create backup with pg_basebackup
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_basebackup \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -D "${backup_path}" \
        -Ft \
        -z \
        -Xs \
        -P \
        -v \
        2>&1 | tee -a "${LOG_FILE}"
    
    # Create backup manifest
    cat > "${backup_path}.manifest" <<EOF
{
    "backup_type": "full",
    "backup_name": "${backup_name}",
    "start_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "database": "${POSTGRES_DB}",
    "host": "${POSTGRES_HOST}",
    "size_bytes": $(du -sb "${backup_path}" | cut -f1),
    "compression": "${BACKUP_COMPRESSION}"
}
EOF
    
    log "Full backup completed: ${backup_name}"
    return 0
}

# Perform logical backup of specific schemas/tables
perform_logical_backup() {
    local backup_name="logical_backup_$(date +%Y%m%d_%H%M%S).sql"
    local backup_path="${BACKUP_DIR}/logical/${backup_name}"
    
    log "Starting logical backup: ${backup_name}"
    
    # Create logical backup with pg_dump
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -f "${backup_path}" \
        --verbose \
        --format=custom \
        --compress=9 \
        --no-owner \
        --no-privileges \
        --schema=public \
        2>&1 | tee -a "${LOG_FILE}"
    
    # Compress if not already compressed
    if [ "${BACKUP_COMPRESSION}" = "gzip" ] && [[ ! "${backup_path}" =~ \.gz$ ]]; then
        gzip "${backup_path}"
        backup_path="${backup_path}.gz"
    fi
    
    log "Logical backup completed: ${backup_name}"
    return 0
}

# Archive WAL files
archive_wal_files() {
    local wal_archive_dir="${BACKUP_DIR}/wal/$(date +%Y%m%d)"
    mkdir -p "${wal_archive_dir}"
    
    log "Archiving WAL files to ${wal_archive_dir}"
    
    # Copy WAL files from pg_wal to archive
    # This would be handled by archive_command in postgresql.conf
    # Here we just ensure the directory structure is maintained
    
    return 0
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than ${BACKUP_RETENTION_DAYS} days"
    
    # Remove old full backups
    find "${BACKUP_DIR}/full" -name "full_backup_*" -type d -mtime +${BACKUP_RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true
    
    # Remove old logical backups
    find "${BACKUP_DIR}/logical" -name "logical_backup_*" -type f -mtime +${BACKUP_RETENTION_DAYS} -delete 2>/dev/null || true
    
    # Remove old WAL archives
    find "${BACKUP_DIR}/wal" -type d -mtime +${BACKUP_RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true
    
    # Remove old manifests
    find "${BACKUP_DIR}/full" -name "*.manifest" -type f -mtime +${BACKUP_RETENTION_DAYS} -delete 2>/dev/null || true
    
    log "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    local backup_path="$1"
    
    log "Verifying backup: ${backup_path}"
    
    # For pg_basebackup tar format
    if [ -f "${backup_path}/base.tar.gz" ]; then
        tar -tzf "${backup_path}/base.tar.gz" > /dev/null 2>&1 || {
            log "ERROR: Backup verification failed for ${backup_path}"
            return 1
        }
    fi
    
    log "Backup verification passed"
    return 0
}

# Send notification (implement based on notification service)
send_notification() {
    local status="$1"
    local message="$2"
    
    # Implement notification logic here (email, Slack, etc.)
    # For now, just log
    log "NOTIFICATION [${status}]: ${message}"
}

# Main backup workflow
main() {
    log "=== Starting PostgreSQL backup process ==="
    
    # Pre-flight checks
    check_disk_space
    
    # Determine backup type based on day of week
    local day_of_week=$(date +%u)
    
    if [ "${day_of_week}" -eq 7 ]; then
        # Sunday: Full backup
        perform_full_backup || {
            send_notification "ERROR" "Full backup failed"
            exit 1
        }
    else
        # Other days: Logical backup
        perform_logical_backup || {
            send_notification "ERROR" "Logical backup failed"
            exit 1
        }
    fi
    
    # Archive WAL files
    archive_wal_files
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Send success notification
    send_notification "SUCCESS" "Backup completed successfully"
    
    log "=== Backup process completed successfully ==="
}

# Run main function
main "$@"