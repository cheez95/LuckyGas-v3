"""
Service Account Key Rotation Function
Automatically rotates service account keys based on age
"""

import json
import base64
import os
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from google.cloud import iam
from google.cloud import secretmanager
from google.cloud import pubsub_v1
from google.cloud import monitoring_v3
from google.oauth2 import service_account

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
iam_client = iam.IAMClient()
secret_client = secretmanager.SecretManagerServiceClient()
publisher = pubsub_v1.PublisherClient()
monitoring_client = monitoring_v3.MetricServiceClient()

# Configuration
PROJECT_ID = os.environ.get('PROJECT_ID')
KEY_AGE_DAYS = int(os.environ.get('KEY_AGE_DAYS', '30'))
NOTIFICATION_TOPIC = os.environ.get('NOTIFICATION_TOPIC')


def rotate_keys(event: Dict[str, Any], context: Any) -> None:
    """
    Main function to rotate service account keys
    
    Args:
        event: Pub/Sub event triggering the rotation
        context: Cloud Function context
    """
    try:
        # Decode the Pub/Sub message
        message_data = json.loads(base64.b64decode(event['data']).decode('utf-8'))
        service_accounts = message_data.get('service_accounts', [])
        
        logger.info(f"Starting key rotation for {len(service_accounts)} service accounts")
        
        rotation_results = []
        
        for sa_email in service_accounts:
            try:
                result = rotate_service_account_keys(sa_email)
                rotation_results.append(result)
                
                # Log metrics
                log_rotation_metric(
                    'key_rotation_success',
                    service_account=sa_email,
                    keys_rotated=result['keys_rotated']
                )
                
            except Exception as e:
                logger.error(f"Failed to rotate keys for {sa_email}: {str(e)}")
                rotation_results.append({
                    'service_account': sa_email,
                    'status': 'failed',
                    'error': str(e)
                })
                
                # Log failure metric
                log_rotation_metric(
                    'key_rotation_failure',
                    service_account=sa_email,
                    error=str(e)
                )
        
        # Send notification with results
        send_rotation_notification(rotation_results)
        
        logger.info("Key rotation completed")
        
    except Exception as e:
        logger.error(f"Key rotation function failed: {str(e)}")
        raise


def rotate_service_account_keys(service_account_email: str) -> Dict[str, Any]:
    """
    Rotate keys for a specific service account
    
    Args:
        service_account_email: Email of the service account
        
    Returns:
        Dict with rotation results
    """
    logger.info(f"Rotating keys for service account: {service_account_email}")
    
    # List all keys for the service account
    resource_name = f"projects/{PROJECT_ID}/serviceAccounts/{service_account_email}"
    
    try:
        keys_response = iam_client.list_service_account_keys(
            request={"name": resource_name}
        )
        
        keys_to_rotate = []
        current_time = datetime.now(timezone.utc)
        
        # Check age of each key
        for key in keys_response.keys:
            # Skip system-managed keys
            if key.key_origin != iam.ServiceAccountKey.KeyOrigin.GOOGLE_PROVIDED:
                key_age = current_time - key.valid_after_time
                
                if key_age.days >= KEY_AGE_DAYS:
                    keys_to_rotate.append(key)
                    logger.info(f"Key {key.name} is {key_age.days} days old - marking for rotation")
        
        if not keys_to_rotate:
            logger.info(f"No keys need rotation for {service_account_email}")
            return {
                'service_account': service_account_email,
                'status': 'no_rotation_needed',
                'keys_rotated': 0
            }
        
        # Create new key first
        new_key = create_new_key(service_account_email)
        
        # Store new key in Secret Manager
        store_key_in_secret_manager(service_account_email, new_key)
        
        # Update applications to use new key
        update_applications_with_new_key(service_account_email, new_key)
        
        # Wait for propagation (in production, this might be longer)
        import time
        time.sleep(60)  # 1 minute
        
        # Delete old keys
        for old_key in keys_to_rotate:
            delete_old_key(old_key.name)
        
        return {
            'service_account': service_account_email,
            'status': 'success',
            'keys_rotated': len(keys_to_rotate),
            'new_key_id': new_key.name.split('/')[-1]
        }
        
    except Exception as e:
        logger.error(f"Error rotating keys for {service_account_email}: {str(e)}")
        raise


def create_new_key(service_account_email: str) -> iam.ServiceAccountKey:
    """Create a new service account key"""
    resource_name = f"projects/{PROJECT_ID}/serviceAccounts/{service_account_email}"
    
    key = iam_client.create_service_account_key(
        request={
            "name": resource_name,
            "private_key_type": iam.ServiceAccountKey.PrivateKeyType.TYPE_GOOGLE_CREDENTIALS_FILE
        }
    )
    
    logger.info(f"Created new key: {key.name}")
    return key


def store_key_in_secret_manager(service_account_email: str, key: iam.ServiceAccountKey) -> None:
    """Store the new key in Secret Manager"""
    # Create secret name based on service account
    secret_id = f"sa-key-{service_account_email.replace('@', '-').replace('.', '-')}"
    secret_name = f"projects/{PROJECT_ID}/secrets/{secret_id}"
    
    try:
        # Try to create the secret
        secret = secret_client.create_secret(
            request={
                "parent": f"projects/{PROJECT_ID}",
                "secret_id": secret_id,
                "secret": {
                    "replication": {
                        "automatic": {}
                    },
                    "labels": {
                        "service_account": service_account_email,
                        "rotation_date": datetime.now().strftime("%Y-%m-%d")
                    }
                }
            }
        )
    except Exception:
        # Secret already exists, just add new version
        pass
    
    # Add the new key as a secret version
    version = secret_client.add_secret_version(
        request={
            "parent": secret_name,
            "payload": {
                "data": base64.b64decode(key.private_key_data)
            }
        }
    )
    
    logger.info(f"Stored new key in Secret Manager: {version.name}")


def update_applications_with_new_key(service_account_email: str, key: iam.ServiceAccountKey) -> None:
    """Update applications to use the new key"""
    # This is where you would update your applications
    # For example, updating environment variables, restarting services, etc.
    
    # For Cloud Run services using Workload Identity, no action needed
    # For other services, you might need to:
    # 1. Update Kubernetes secrets
    # 2. Trigger Cloud Run redeployment
    # 3. Update environment variables
    # 4. Notify applications via Pub/Sub
    
    logger.info(f"Updating applications for {service_account_email}")
    
    # Publish update event
    topic_path = publisher.topic_path(PROJECT_ID, 'service-account-key-updated')
    
    message_data = {
        'service_account': service_account_email,
        'key_id': key.name.split('/')[-1],
        'timestamp': datetime.now().isoformat()
    }
    
    future = publisher.publish(
        topic_path,
        data=json.dumps(message_data).encode('utf-8')
    )
    
    logger.info(f"Published key update notification: {future.result()}")


def delete_old_key(key_name: str) -> None:
    """Delete an old service account key"""
    try:
        iam_client.delete_service_account_key(
            request={"name": key_name}
        )
        logger.info(f"Deleted old key: {key_name}")
    except Exception as e:
        logger.error(f"Failed to delete key {key_name}: {str(e)}")


def send_rotation_notification(results: List[Dict[str, Any]]) -> None:
    """Send notification about rotation results"""
    topic_path = publisher.topic_path(PROJECT_ID, NOTIFICATION_TOPIC.split('/')[-1])
    
    # Prepare summary
    total_accounts = len(results)
    successful = len([r for r in results if r.get('status') == 'success'])
    failed = len([r for r in results if r.get('status') == 'failed'])
    no_rotation = len([r for r in results if r.get('status') == 'no_rotation_needed'])
    
    message = {
        'summary': {
            'total_accounts': total_accounts,
            'successful_rotations': successful,
            'failed_rotations': failed,
            'no_rotation_needed': no_rotation
        },
        'details': results,
        'timestamp': datetime.now().isoformat()
    }
    
    future = publisher.publish(
        topic_path,
        data=json.dumps(message).encode('utf-8')
    )
    
    logger.info(f"Sent rotation notification: {future.result()}")


def log_rotation_metric(metric_type: str, **labels) -> None:
    """Log custom metrics for key rotation"""
    try:
        project_name = f"projects/{PROJECT_ID}"
        
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/security/{metric_type}"
        series.resource.type = "global"
        series.resource.labels["project_id"] = PROJECT_ID
        
        # Add custom labels
        for key, value in labels.items():
            series.metric.labels[key] = str(value)
        
        # Create a data point
        now = datetime.utcnow()
        point = monitoring_v3.Point()
        point.value.int64_value = 1
        point.interval.end_time.seconds = int(now.timestamp())
        series.points = [point]
        
        # Write the time series
        monitoring_client.create_time_series(
            name=project_name,
            time_series=[series]
        )
        
    except Exception as e:
        logger.error(f"Failed to log rotation metric: {str(e)}")


def check_key_age(service_account_email: str) -> List[Dict[str, Any]]:
    """
    Check the age of all keys for a service account
    Used for monitoring and alerting
    """
    resource_name = f"projects/{PROJECT_ID}/serviceAccounts/{service_account_email}"
    
    keys_response = iam_client.list_service_account_keys(
        request={"name": resource_name}
    )
    
    key_ages = []
    current_time = datetime.now(timezone.utc)
    
    for key in keys_response.keys:
        if key.key_origin != iam.ServiceAccountKey.KeyOrigin.GOOGLE_PROVIDED:
            key_age = current_time - key.valid_after_time
            
            key_ages.append({
                'key_id': key.name.split('/')[-1],
                'age_days': key_age.days,
                'created': key.valid_after_time.isoformat(),
                'expires': key.valid_before_time.isoformat() if key.valid_before_time else 'Never'
            })
            
            # Log metric for key age
            log_rotation_metric(
                'service_account_key_age',
                service_account=service_account_email,
                key_id=key.name.split('/')[-1],
                age_days=key_age.days
            )
    
    return key_ages


# For local testing
if __name__ == "__main__":
    test_event = {
        'data': base64.b64encode(json.dumps({
            'action': 'rotate_keys',
            'service_accounts': [
                'test-sa@project.iam.gserviceaccount.com'
            ]
        }).encode()).decode()
    }
    
    rotate_keys(test_event, None)