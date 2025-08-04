"""
Security Alert Processor Function
Processes security alerts from Google Security Command Center
"""

import json
import base64
import os
import logging
from typing import Dict, Any
import requests
from google.cloud import secretmanager
from google.cloud import monitoring_v3
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
secret_client = secretmanager.SecretManagerServiceClient()
monitoring_client = monitoring_v3.MetricServiceClient()

# Configuration
PROJECT_ID = os.environ.get('PROJECT_ID')
SLACK_WEBHOOK_SECRET = os.environ.get('SLACK_WEBHOOK_SECRET')


def process_alert(event: Dict[str, Any], context: Any) -> None:
    """
    Process security alert from Security Command Center
    
    Args:
        event: Pub/Sub event containing the alert
        context: Cloud Function context
    """
    try:
        # Decode the Pub/Sub message
        alert_data = json.loads(base64.b64decode(event['data']).decode('utf-8'))
        
        logger.info(f"Processing security alert: {alert_data.get('finding', {}).get('name', 'Unknown')}")
        
        # Extract alert details
        finding = alert_data.get('finding', {})
        severity = finding.get('severity', 'UNKNOWN')
        category = finding.get('category', 'UNKNOWN')
        resource = finding.get('resourceName', 'Unknown resource')
        description = finding.get('description', 'No description provided')
        source = finding.get('sourceProperties', {})
        
        # Check if it's a critical alert
        is_critical = severity in ['HIGH', 'CRITICAL']
        
        # Format alert message
        alert_message = format_alert_message(
            severity=severity,
            category=category,
            resource=resource,
            description=description,
            source=source,
            finding_name=finding.get('name', 'Unknown')
        )
        
        # Send notifications based on severity
        if is_critical:
            # Send immediate Slack notification
            send_slack_notification(alert_message, is_critical=True)
            
            # Create incident ticket
            create_incident_ticket(finding)
            
            # Log to monitoring
            log_security_metric(
                metric_type='critical_security_alert',
                severity=severity,
                category=category
            )
        else:
            # Send regular notification
            send_slack_notification(alert_message, is_critical=False)
            
            # Log to monitoring
            log_security_metric(
                metric_type='security_alert',
                severity=severity,
                category=category
            )
        
        # Apply automatic remediation if possible
        if should_auto_remediate(finding):
            apply_remediation(finding)
        
        logger.info("Security alert processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing security alert: {str(e)}")
        # Log error metric
        log_security_metric(
            metric_type='security_alert_processing_error',
            error=str(e)
        )
        raise


def format_alert_message(
    severity: str,
    category: str,
    resource: str,
    description: str,
    source: Dict[str, Any],
    finding_name: str
) -> Dict[str, Any]:
    """Format alert message for notification"""
    
    emoji_map = {
        'CRITICAL': '🚨',
        'HIGH': '⚠️',
        'MEDIUM': '📢',
        'LOW': 'ℹ️'
    }
    
    return {
        'text': f"{emoji_map.get(severity, '❓')} Security Alert: {category}",
        'blocks': [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f'Security Alert - {severity}'
                }
            },
            {
                'type': 'section',
                'fields': [
                    {
                        'type': 'mrkdwn',
                        'text': f'*Category:*\n{category}'
                    },
                    {
                        'type': 'mrkdwn',
                        'text': f'*Resource:*\n{resource}'
                    }
                ]
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*Description:*\n{description}'
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*Finding ID:*\n`{finding_name}`'
                }
            },
            {
                'type': 'actions',
                'elements': [
                    {
                        'type': 'button',
                        'text': {
                            'type': 'plain_text',
                            'text': 'View in Security Command Center'
                        },
                        'url': f'https://console.cloud.google.com/security/command-center/findings?project={PROJECT_ID}'
                    }
                ]
            }
        ]
    }


def send_slack_notification(message: Dict[str, Any], is_critical: bool) -> None:
    """Send notification to Slack webhook"""
    try:
        # Get Slack webhook URL from Secret Manager
        secret_name = f"projects/{PROJECT_ID}/secrets/{SLACK_WEBHOOK_SECRET}/versions/latest"
        response = secret_client.access_secret_version(request={"name": secret_name})
        webhook_url = response.payload.data.decode('UTF-8')
        
        # Add urgency indicator for critical alerts
        if is_critical:
            message['text'] = f"<!channel> {message['text']}"
        
        # Send to Slack
        response = requests.post(
            webhook_url,
            json=message,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {str(e)}")


def create_incident_ticket(finding: Dict[str, Any]) -> None:
    """Create incident ticket for critical findings"""
    # This would integrate with your ticketing system (e.g., Jira, ServiceNow)
    logger.info(f"Creating incident ticket for finding: {finding.get('name')}")
    # Implementation depends on your ticketing system


def should_auto_remediate(finding: Dict[str, Any]) -> bool:
    """Determine if finding should be auto-remediated"""
    auto_remediate_categories = [
        'PUBLIC_BUCKET_ACL',
        'WEAK_PASSWORD_POLICY',
        'FIREWALL_RULE_LOGGING_DISABLED',
        'LEGACY_AUTHORIZATION_ENABLED'
    ]
    
    return finding.get('category') in auto_remediate_categories


def apply_remediation(finding: Dict[str, Any]) -> None:
    """Apply automatic remediation for certain finding types"""
    category = finding.get('category')
    resource = finding.get('resourceName')
    
    logger.info(f"Applying remediation for {category} on {resource}")
    
    # Implement specific remediation logic based on category
    if category == 'PUBLIC_BUCKET_ACL':
        # Remove public access from bucket
        pass
    elif category == 'WEAK_PASSWORD_POLICY':
        # Enforce strong password policy
        pass
    elif category == 'FIREWALL_RULE_LOGGING_DISABLED':
        # Enable firewall logging
        pass
    elif category == 'LEGACY_AUTHORIZATION_ENABLED':
        # Disable legacy authorization
        pass
    
    # Log remediation action
    log_security_metric(
        metric_type='auto_remediation_applied',
        category=category,
        resource=resource
    )


def log_security_metric(metric_type: str, **labels) -> None:
    """Log custom security metrics to Cloud Monitoring"""
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
        logger.error(f"Failed to log security metric: {str(e)}")


# For local testing
if __name__ == "__main__":
    test_event = {
        'data': base64.b64encode(json.dumps({
            'finding': {
                'name': 'test-finding',
                'severity': 'HIGH',
                'category': 'PUBLIC_BUCKET_ACL',
                'resourceName': 'test-bucket',
                'description': 'Test security finding'
            }
        }).encode()).decode()
    }
    
    process_alert(test_event, None)