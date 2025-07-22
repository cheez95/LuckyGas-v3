#!/usr/bin/env python3
"""
Script to set up Google Cloud Monitoring for Lucky Gas application.

This script creates custom metrics, dashboards, and alert policies.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List
from google.cloud import monitoring_v3
from google.cloud import monitoring_dashboard_v1

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from infrastructure.monitoring.metrics_config import MetricsCollector


def create_slo_dashboard(project_id: str) -> Dict:
    """Create an SLO (Service Level Objective) dashboard configuration."""
    return {
        "displayName": "Lucky Gas - SLO Dashboard",
        "mosaicLayout": {
            "columns": 12,
            "tiles": [
                {
                    "width": 4,
                    "height": 4,
                    "widget": {
                        "title": "Availability SLO (99.9%)",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": f'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count"',
                                    "aggregation": {
                                        "alignmentPeriod": "3600s",
                                        "perSeriesAligner": "ALIGN_RATE",
                                        "crossSeriesReducer": "REDUCE_SUM"
                                    }
                                }
                            },
                            "gaugeView": {
                                "lowerBound": 0.0,
                                "upperBound": 100.0
                            }
                        }
                    }
                },
                {
                    "xPos": 4,
                    "width": 4,
                    "height": 4,
                    "widget": {
                        "title": "Latency SLO (p95 < 500ms)",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": f'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_latencies"',
                                    "aggregation": {
                                        "alignmentPeriod": "300s",
                                        "perSeriesAligner": "ALIGN_PERCENTILE_95",
                                        "crossSeriesReducer": "REDUCE_MEAN"
                                    }
                                }
                            },
                            "gaugeView": {
                                "lowerBound": 0.0,
                                "upperBound": 500.0
                            }
                        }
                    }
                },
                {
                    "xPos": 8,
                    "width": 4,
                    "height": 4,
                    "widget": {
                        "title": "Error Budget Remaining",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": f'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count"',
                                    "aggregation": {
                                        "alignmentPeriod": "86400s",
                                        "perSeriesAligner": "ALIGN_RATE",
                                        "crossSeriesReducer": "REDUCE_SUM"
                                    }
                                }
                            },
                            "sparkChartView": {
                                "sparkChartType": "SPARK_LINE"
                            }
                        }
                    }
                }
            ]
        }
    }


def create_business_dashboard(project_id: str) -> Dict:
    """Create a business metrics dashboard configuration."""
    return {
        "displayName": "Lucky Gas - Business Metrics",
        "mosaicLayout": {
            "columns": 12,
            "tiles": [
                {
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Orders by Type",
                        "xyChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": f'metric.type="custom.googleapis.com/luckygas/orders/created"',
                                        "aggregation": {
                                            "alignmentPeriod": "3600s",
                                            "perSeriesAligner": "ALIGN_RATE",
                                            "crossSeriesReducer": "REDUCE_SUM",
                                            "groupByFields": ["metric.label.order_type"]
                                        }
                                    }
                                }
                            }]
                        }
                    }
                },
                {
                    "xPos": 6,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Revenue by Product Type",
                        "pieChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": f'metric.type="custom.googleapis.com/luckygas/revenue/total"',
                                        "aggregation": {
                                            "alignmentPeriod": "86400s",
                                            "perSeriesAligner": "ALIGN_RATE",
                                            "crossSeriesReducer": "REDUCE_SUM",
                                            "groupByFields": ["metric.label.product_type"]
                                        }
                                    }
                                }
                            }]
                        }
                    }
                },
                {
                    "yPos": 4,
                    "width": 12,
                    "height": 4,
                    "widget": {
                        "title": "Deliveries by Zone",
                        "xyChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": f'metric.type="custom.googleapis.com/luckygas/deliveries/completed"',
                                        "aggregation": {
                                            "alignmentPeriod": "3600s",
                                            "perSeriesAligner": "ALIGN_RATE",
                                            "crossSeriesReducer": "REDUCE_SUM",
                                            "groupByFields": ["metric.label.zone"]
                                        }
                                    }
                                }
                            }],
                            "chartOptions": {
                                "mode": "STACKED"
                            }
                        }
                    }
                },
                {
                    "yPos": 8,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Route Optimization Performance",
                        "xyChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": f'metric.type="custom.googleapis.com/luckygas/route/optimization_time"',
                                        "aggregation": {
                                            "alignmentPeriod": "300s",
                                            "perSeriesAligner": "ALIGN_MEAN"
                                        }
                                    }
                                }
                            }]
                        }
                    }
                },
                {
                    "xPos": 6,
                    "yPos": 8,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "ML Prediction Accuracy",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": f'metric.type="custom.googleapis.com/luckygas/prediction/accuracy"',
                                    "aggregation": {
                                        "alignmentPeriod": "3600s",
                                        "perSeriesAligner": "ALIGN_MEAN"
                                    }
                                }
                            },
                            "gaugeView": {
                                "lowerBound": 0.0,
                                "upperBound": 100.0
                            }
                        }
                    }
                }
            ]
        }
    }


def create_cost_dashboard(project_id: str) -> Dict:
    """Create a cost monitoring dashboard configuration."""
    return {
        "displayName": "Lucky Gas - Cost Monitoring",
        "mosaicLayout": {
            "columns": 12,
            "tiles": [
                {
                    "width": 12,
                    "height": 4,
                    "widget": {
                        "title": "Google API Costs by Service",
                        "xyChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": f'metric.type="custom.googleapis.com/luckygas/google_api/cost"',
                                        "aggregation": {
                                            "alignmentPeriod": "3600s",
                                            "perSeriesAligner": "ALIGN_RATE",
                                            "crossSeriesReducer": "REDUCE_SUM",
                                            "groupByFields": ["metric.label.api_name"]
                                        }
                                    }
                                }
                            }],
                            "chartOptions": {
                                "mode": "STACKED"
                            }
                        }
                    }
                },
                {
                    "yPos": 4,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "API Call Volume",
                        "xyChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": f'metric.type="custom.googleapis.com/luckygas/google_api/calls"',
                                        "aggregation": {
                                            "alignmentPeriod": "300s",
                                            "perSeriesAligner": "ALIGN_RATE",
                                            "crossSeriesReducer": "REDUCE_SUM",
                                            "groupByFields": ["metric.label.api_name"]
                                        }
                                    }
                                }
                            }]
                        }
                    }
                },
                {
                    "xPos": 6,
                    "yPos": 4,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "API Error Rate",
                        "xyChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": f'metric.type="custom.googleapis.com/luckygas/google_api/calls" AND metric.label.status!="success"',
                                        "aggregation": {
                                            "alignmentPeriod": "300s",
                                            "perSeriesAligner": "ALIGN_RATE",
                                            "crossSeriesReducer": "REDUCE_SUM",
                                            "groupByFields": ["metric.label.api_name"]
                                        }
                                    }
                                }
                            }]
                        }
                    }
                }
            ]
        }
    }


def create_alert_policies(project_id: str, notification_channels: List[str]):
    """Create alert policies for the application."""
    client = monitoring_v3.AlertPolicyServiceClient()
    project_path = f"projects/{project_id}"
    
    policies = [
        {
            "display_name": "Lucky Gas - Order Processing Failure",
            "conditions": [{
                "display_name": "Order creation failures > 10 in 5 minutes",
                "condition_threshold": {
                    "filter": 'resource.type="cloud_run_revision" AND metric.type="logging.googleapis.com/user/order_creation_failed"',
                    "comparison": "COMPARISON_GT",
                    "threshold_value": 10,
                    "duration": "300s",
                    "aggregations": [{
                        "alignment_period": "60s",
                        "per_series_aligner": "ALIGN_RATE"
                    }]
                }
            }],
            "alert_strategy": {
                "notification_rate_limit": {
                    "period": "3600s"
                }
            }
        },
        {
            "display_name": "Lucky Gas - Route Optimization Timeout",
            "conditions": [{
                "display_name": "Route optimization > 30 seconds",
                "condition_threshold": {
                    "filter": 'metric.type="custom.googleapis.com/luckygas/route/optimization_time"',
                    "comparison": "COMPARISON_GT",
                    "threshold_value": 30,
                    "duration": "300s",
                    "aggregations": [{
                        "alignment_period": "60s",
                        "per_series_aligner": "ALIGN_MAX"
                    }]
                }
            }]
        },
        {
            "display_name": "Lucky Gas - Low Prediction Accuracy",
            "conditions": [{
                "display_name": "Prediction accuracy < 80%",
                "condition_threshold": {
                    "filter": 'metric.type="custom.googleapis.com/luckygas/prediction/accuracy"',
                    "comparison": "COMPARISON_LT",
                    "threshold_value": 80,
                    "duration": "1800s",
                    "aggregations": [{
                        "alignment_period": "300s",
                        "per_series_aligner": "ALIGN_MEAN"
                    }]
                }
            }]
        },
        {
            "display_name": "Lucky Gas - High Google API Cost",
            "conditions": [{
                "display_name": "API cost > $10/hour",
                "condition_threshold": {
                    "filter": 'metric.type="custom.googleapis.com/luckygas/google_api/cost"',
                    "comparison": "COMPARISON_GT",
                    "threshold_value": 10,
                    "duration": "3600s",
                    "aggregations": [{
                        "alignment_period": "3600s",
                        "per_series_aligner": "ALIGN_RATE",
                        "cross_series_reducer": "REDUCE_SUM"
                    }]
                }
            }]
        }
    ]
    
    created_policies = []
    
    for policy_config in policies:
        policy = monitoring_v3.AlertPolicy()
        policy.display_name = policy_config["display_name"]
        
        for condition_config in policy_config["conditions"]:
            condition = monitoring_v3.AlertPolicy.Condition()
            condition.display_name = condition_config["display_name"]
            condition.condition_threshold = condition_config["condition_threshold"]
            policy.conditions.append(condition)
        
        if "alert_strategy" in policy_config:
            policy.alert_strategy = policy_config["alert_strategy"]
        
        policy.notification_channels.extend(notification_channels)
        policy.combiner = monitoring_v3.AlertPolicy.ConditionCombinerType.OR
        
        try:
            created_policy = client.create_alert_policy(
                name=project_path,
                alert_policy=policy
            )
            created_policies.append(created_policy.name)
            print(f"Created alert policy: {policy.display_name}")
        except Exception as e:
            print(f"Failed to create alert policy {policy.display_name}: {e}")
    
    return created_policies


def setup_monitoring(project_id: str, notification_emails: List[str]):
    """Set up complete monitoring for the application."""
    print(f"Setting up monitoring for project: {project_id}")
    
    # Initialize metrics collector
    metrics = MetricsCollector(project_id)
    
    # Create custom metrics
    print("\nCreating custom metrics...")
    metrics.create_custom_metrics()
    
    # Create notification channels
    print("\nCreating notification channels...")
    nc_client = monitoring_v3.NotificationChannelServiceClient()
    project_path = f"projects/{project_id}"
    
    notification_channels = []
    for email in notification_emails:
        channel = monitoring_v3.NotificationChannel()
        channel.type = "email"
        channel.display_name = f"Email - {email}"
        channel.labels["email_address"] = email
        channel.enabled = True
        
        try:
            created_channel = nc_client.create_notification_channel(
                name=project_path,
                notification_channel=channel
            )
            notification_channels.append(created_channel.name)
            print(f"Created notification channel for: {email}")
        except Exception as e:
            print(f"Failed to create notification channel for {email}: {e}")
    
    # Create dashboards
    print("\nCreating dashboards...")
    dashboard_client = monitoring_dashboard_v1.DashboardsServiceClient()
    
    dashboards = [
        ("SLO Dashboard", create_slo_dashboard(project_id)),
        ("Business Metrics", create_business_dashboard(project_id)),
        ("Cost Monitoring", create_cost_dashboard(project_id))
    ]
    
    for name, config in dashboards:
        try:
            dashboard = monitoring_dashboard_v1.Dashboard()
            dashboard.display_name = config["displayName"]
            dashboard.mosaic_layout = config["mosaicLayout"]
            
            created_dashboard = dashboard_client.create_dashboard(
                parent=project_path,
                dashboard=dashboard
            )
            print(f"Created dashboard: {name}")
        except Exception as e:
            print(f"Failed to create dashboard {name}: {e}")
    
    # Create alert policies
    print("\nCreating alert policies...")
    create_alert_policies(project_id, notification_channels)
    
    print("\nMonitoring setup complete!")


def main():
    parser = argparse.ArgumentParser(description="Set up Google Cloud Monitoring")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--emails", nargs="+", required=True, 
                        help="Notification email addresses")
    
    args = parser.parse_args()
    
    # Set project ID environment variable
    os.environ["GCP_PROJECT_ID"] = args.project
    
    setup_monitoring(args.project, args.emails)


if __name__ == "__main__":
    main()