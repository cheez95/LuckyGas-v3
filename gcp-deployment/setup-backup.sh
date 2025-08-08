#!/bin/bash

# Setup Automated Backups for LuckyGas

set -e

PROJECT_ID="vast-tributary-466619-m8"
REGION="asia-east1"
DB_INSTANCE="luckygas-staging"
BACKUP_BUCKET="gs://luckygas-backups-prod"

echo "Setting up automated backups..."

# Create backup bucket if it doesn't exist
echo "1. Creating backup bucket..."
gsutil mb -p $PROJECT_ID -l $REGION $BACKUP_BUCKET 2>/dev/null || echo "Backup bucket exists"

# Set lifecycle policy for backup retention (90 days)
echo "2. Setting backup retention policy..."
cat > /tmp/lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle.json $BACKUP_BUCKET

# Create backup export function
echo "3. Creating backup export script..."
cat > /tmp/backup-database.sh << 'SCRIPT'
#!/bin/bash

# Database backup script
PROJECT_ID="vast-tributary-466619-m8"
DB_INSTANCE="luckygas-staging"
BACKUP_BUCKET="gs://luckygas-backups-prod"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${TIMESTAMP}.sql"

echo "Starting database backup at $(date)"

# Export database
gcloud sql export sql $DB_INSTANCE \
    ${BACKUP_BUCKET}/${BACKUP_FILE} \
    --database=luckygas \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "Backup completed successfully: ${BACKUP_BUCKET}/${BACKUP_FILE}"
    
    # Log success to Cloud Logging
    gcloud logging write luckygas-backup \
        "Database backup completed: ${BACKUP_FILE}" \
        --severity=INFO \
        --project=$PROJECT_ID
else
    echo "Backup failed!"
    
    # Log failure to Cloud Logging
    gcloud logging write luckygas-backup \
        "Database backup failed for ${TIMESTAMP}" \
        --severity=ERROR \
        --project=$PROJECT_ID
    
    exit 1
fi

# List recent backups
echo "Recent backups:"
gsutil ls -l ${BACKUP_BUCKET}/backup_*.sql | tail -5
SCRIPT

# Create Cloud Function for automated backup
echo "4. Creating Cloud Function for automated backup..."
cat > /tmp/main.py << 'EOF'
import os
import subprocess
from datetime import datetime
from google.cloud import storage
from google.cloud import sql_v1
import functions_framework

PROJECT_ID = "vast-tributary-466619-m8"
DB_INSTANCE = "luckygas-staging"
BACKUP_BUCKET = "luckygas-backups-prod"

@functions_framework.http
def backup_database(request):
    """HTTP Cloud Function for database backup."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.sql"
    backup_uri = f"gs://{BACKUP_BUCKET}/{backup_file}"
    
    # Create SQL Admin client
    client = sql_v1.SqlBackupRunsServiceClient()
    
    # Create backup request
    project = f"projects/{PROJECT_ID}"
    instance = f"{project}/instances/{DB_INSTANCE}"
    
    try:
        # Export database
        export_context = {
            "uri": backup_uri,
            "databases": ["luckygas"],
            "kind": "sql#exportContext",
            "fileType": "SQL"
        }
        
        operation = client.export(
            project=PROJECT_ID,
            instance=DB_INSTANCE,
            body={"exportContext": export_context}
        )
        
        print(f"Backup started: {backup_uri}")
        return {"status": "success", "backup": backup_uri, "timestamp": timestamp}
        
    except Exception as e:
        print(f"Backup failed: {str(e)}")
        return {"status": "error", "error": str(e)}, 500
EOF

cat > /tmp/requirements.txt << EOF
functions-framework==3.*
google-cloud-storage==2.*
google-cloud-sql==0.*
EOF

# Create Cloud Scheduler job for daily backup
echo "5. Creating Cloud Scheduler job..."
gcloud scheduler jobs create http luckygas-daily-backup \
    --location=$REGION \
    --schedule="0 3 * * *" \
    --time-zone="Asia/Taipei" \
    --uri="https://sql.googleapis.com/sql/v1beta4/projects/$PROJECT_ID/instances/$DB_INSTANCE/export" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body="{
        \"exportContext\": {
            \"fileType\": \"SQL\",
            \"uri\": \"${BACKUP_BUCKET}/scheduled_backup_\$(date +%Y%m%d_%H%M%S).sql\",
            \"databases\": [\"luckygas\"]
        }
    }" \
    --project=$PROJECT_ID 2>/dev/null || echo "Scheduler job exists"

# Create restore script
echo "6. Creating restore script..."
cat > /tmp/restore-database.sh << 'SCRIPT'
#!/bin/bash

# Database restore script
PROJECT_ID="vast-tributary-466619-m8"
DB_INSTANCE="luckygas-staging"
BACKUP_BUCKET="gs://luckygas-backups-prod"

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backup_20250808_030000.sql"
    echo ""
    echo "Available backups:"
    gsutil ls ${BACKUP_BUCKET}/backup_*.sql | tail -10
    exit 1
fi

BACKUP_FILE=$1
BACKUP_PATH="${BACKUP_BUCKET}/${BACKUP_FILE}"

echo "Restoring database from: $BACKUP_PATH"
read -p "This will overwrite the current database. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 1
fi

# Import database
gcloud sql import sql $DB_INSTANCE \
    $BACKUP_PATH \
    --database=luckygas \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "Restore completed successfully!"
    
    # Log success
    gcloud logging write luckygas-restore \
        "Database restored from: ${BACKUP_FILE}" \
        --severity=INFO \
        --project=$PROJECT_ID
else
    echo "Restore failed!"
    
    # Log failure
    gcloud logging write luckygas-restore \
        "Database restore failed from: ${BACKUP_FILE}" \
        --severity=ERROR \
        --project=$PROJECT_ID
    
    exit 1
fi
SCRIPT

# Copy scripts to backup bucket for safekeeping
echo "7. Storing backup scripts..."
gsutil cp /tmp/backup-database.sh ${BACKUP_BUCKET}/scripts/
gsutil cp /tmp/restore-database.sh ${BACKUP_BUCKET}/scripts/

# Test backup
echo "8. Running test backup..."
bash /tmp/backup-database.sh

echo ""
echo "========================================="
echo "Backup Setup Complete!"
echo "========================================="
echo ""
echo "Backup Configuration:"
echo "- Daily backups at 3:00 AM Taiwan time"
echo "- Retention period: 90 days"
echo "- Backup location: $BACKUP_BUCKET"
echo ""
echo "Manual Operations:"
echo "- Run backup: bash /tmp/backup-database.sh"
echo "- Restore: bash /tmp/restore-database.sh <backup_file>"
echo ""
echo "Monitoring:"
echo "- View backup logs: gcloud logging read 'resource.labels.function_name=luckygas-daily-backup'"
echo "- List backups: gsutil ls -l $BACKUP_BUCKET"