"""
Budget Alert Processor for Lucky Gas
Processes budget alerts and generates cost reports
"""
import json
import os
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import requests
from flask import Request, jsonify
from google.cloud import bigquery
from google.cloud import secretmanager
from google.cloud import monitoring_v3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.environ.get('PROJECT_ID', 'vast-tributary-466619-m8')
MONTHLY_BUDGET_NTD = int(os.environ.get('MONTHLY_BUDGET_NTD', 3000))
EXCHANGE_RATE = 31.5  # USD to NTD


class BudgetProcessor:
    """Process budget alerts and generate reports"""
    
    def __init__(self):
        self.project_id = PROJECT_ID
        self.budget_ntd = MONTHLY_BUDGET_NTD
        self.budget_usd = MONTHLY_BUDGET_NTD / EXCHANGE_RATE
        self.bq_client = bigquery.Client()
        self.metrics_client = monitoring_v3.MetricServiceClient()
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
    def get_slack_webhook(self) -> str:
        """Get Slack webhook URL from Secret Manager"""
        try:
            secret_name = f"projects/{self.project_id}/secrets/cost-alerts-webhook/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": secret_name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to get Slack webhook: {e}")
            return None
    
    def process_budget_alert(self, alert_data: Dict) -> Dict:
        """Process a budget alert from Pub/Sub"""
        try:
            # Extract alert details
            budget_amount = alert_data.get('budgetAmount', 0)
            cost_amount = alert_data.get('costAmount', 0)
            threshold_percent = alert_data.get('thresholdPercent', 0)
            budget_name = alert_data.get('budgetDisplayName', 'Unknown')
            
            # Calculate percentages and amounts
            percent_used = (cost_amount / budget_amount) * 100 if budget_amount > 0 else 0
            cost_ntd = cost_amount * EXCHANGE_RATE
            remaining_usd = budget_amount - cost_amount
            remaining_ntd = remaining_usd * EXCHANGE_RATE
            
            # Determine alert severity
            if percent_used >= 100:
                severity = "CRITICAL"
                emoji = "🚨"
            elif percent_used >= 80:
                severity = "WARNING"
                emoji = "⚠️"
            elif percent_used >= 50:
                severity = "INFO"
                emoji = "ℹ️"
            else:
                severity = "OK"
                emoji = "✅"
            
            # Get cost breakdown
            cost_breakdown = self.get_cost_breakdown()
            
            # Create alert message
            message = {
                "severity": severity,
                "emoji": emoji,
                "budget_name": budget_name,
                "percent_used": round(percent_used, 1),
                "cost_usd": round(cost_amount, 2),
                "cost_ntd": round(cost_ntd, 0),
                "budget_usd": round(budget_amount, 2),
                "budget_ntd": round(budget_amount * EXCHANGE_RATE, 0),
                "remaining_usd": round(remaining_usd, 2),
                "remaining_ntd": round(remaining_ntd, 0),
                "cost_breakdown": cost_breakdown,
                "recommendations": self.get_recommendations(percent_used, cost_breakdown)
            }
            
            # Send to Slack
            self.send_slack_alert(message)
            
            # Record metrics
            self.record_metrics(message)
            
            return message
            
        except Exception as e:
            logger.error(f"Error processing budget alert: {e}")
            raise
    
    def get_cost_breakdown(self) -> List[Dict]:
        """Get cost breakdown by service from BigQuery"""
        try:
            query = """
            SELECT
                service.description AS service_name,
                SUM(cost) AS total_cost_usd,
                SUM(cost) * 31.5 AS total_cost_ntd
            FROM
                `{}.billing_export.gcp_billing_export_v1_*`
            WHERE
                DATE(_PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                AND project.id = '{}'
            GROUP BY
                service_name
            ORDER BY
                total_cost_usd DESC
            LIMIT 5
            """.format(self.project_id, self.project_id)
            
            results = self.bq_client.query(query).result()
            
            breakdown = []
            for row in results:
                breakdown.append({
                    "service": row.service_name,
                    "cost_usd": round(row.total_cost_usd, 2),
                    "cost_ntd": round(row.total_cost_ntd, 0)
                })
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Failed to get cost breakdown: {e}")
            return []
    
    def get_recommendations(self, percent_used: float, breakdown: List[Dict]) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        # Budget-based recommendations
        if percent_used >= 100:
            recommendations.append("🚨 IMMEDIATE ACTION: Implement emergency cost controls")
            recommendations.append("🚨 Consider disabling non-critical services temporarily")
        elif percent_used >= 80:
            recommendations.append("⚠️ Review and optimize high-cost services immediately")
            recommendations.append("⚠️ Enable aggressive caching for all API calls")
        elif percent_used >= 50:
            recommendations.append("ℹ️ Monitor daily costs closely")
            recommendations.append("ℹ️ Review caching strategies for optimization")
        
        # Service-specific recommendations
        for service in breakdown:
            if "Routes" in service["service"] and service["cost_usd"] > 10:
                recommendations.append(f"💡 Routes API: Enable response caching (potential savings: {service['cost_usd'] * 0.3:.0f} USD)")
            elif "Vertex" in service["service"] and service["cost_usd"] > 5:
                recommendations.append(f"💡 Vertex AI: Batch predictions to reduce costs")
            elif "Cloud Run" in service["service"] and service["cost_usd"] > 15:
                recommendations.append(f"💡 Cloud Run: Optimize scaling settings and request handling")
            elif "Cloud SQL" in service["service"] and service["cost_usd"] > 20:
                recommendations.append(f"💡 Cloud SQL: Consider connection pooling and query optimization")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def send_slack_alert(self, message: Dict):
        """Send alert to Slack"""
        webhook_url = self.get_slack_webhook()
        if not webhook_url:
            logger.warning("No Slack webhook configured")
            return
        
        # Format Slack message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{message['emoji']} Lucky Gas Budget Alert"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Budget Used:*\n{message['percent_used']}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Current Cost:*\nNT${message['cost_ntd']:,.0f} (${message['cost_usd']:,.2f})"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Monthly Budget:*\nNT${message['budget_ntd']:,.0f} (${message['budget_usd']:,.2f})"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Remaining:*\nNT${message['remaining_ntd']:,.0f} (${message['remaining_usd']:,.2f})"
                    }
                ]
            }
        ]
        
        # Add cost breakdown
        if message['cost_breakdown']:
            breakdown_text = "*Top Services by Cost:*\n"
            for service in message['cost_breakdown']:
                breakdown_text += f"• {service['service']}: NT${service['cost_ntd']:,.0f}\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": breakdown_text
                }
            })
        
        # Add recommendations
        if message['recommendations']:
            rec_text = "*Recommendations:*\n" + "\n".join(message['recommendations'])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": rec_text
                }
            })
        
        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Alert generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                }
            ]
        })
        
        slack_payload = {
            "blocks": blocks,
            "text": f"{message['emoji']} Budget Alert: {message['percent_used']}% used"
        }
        
        try:
            response = requests.post(webhook_url, json=slack_payload)
            response.raise_for_status()
            logger.info("Slack alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def record_metrics(self, message: Dict):
        """Record custom metrics for monitoring"""
        try:
            series = monitoring_v3.TimeSeries()
            series.metric.type = "custom.googleapis.com/luckygas/budget_utilization"
            series.metric.labels["severity"] = message["severity"]
            
            point = monitoring_v3.Point()
            point.value.double_value = message["percent_used"]
            point.interval.end_time.seconds = int(datetime.utcnow().timestamp())
            
            series.points.append(point)
            
            project_name = f"projects/{self.project_id}"
            self.metrics_client.create_time_series(name=project_name, time_series=[series])
            
            logger.info(f"Recorded budget utilization metric: {message['percent_used']}%")
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
    
    def generate_daily_report(self) -> Dict:
        """Generate daily cost report"""
        try:
            # Query for daily report data
            query = """
            SELECT
                *
            FROM
                `{}.billing_export.daily_costs_{}`
            WHERE
                usage_date = CURRENT_DATE() - 1
            """.format(self.project_id, (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d'))
            
            results = list(self.bq_client.query(query).result())
            
            if results:
                report_data = results[0]
                
                # Format report
                report = {
                    "date": report_data.usage_date.strftime('%Y-%m-%d'),
                    "daily_cost_ntd": round(report_data.daily_total_ntd, 0),
                    "projected_monthly_ntd": round(report_data.projected_monthly_ntd, 0),
                    "budget_utilization": round(report_data.budget_utilization_percent, 1),
                    "status": report_data.budget_status,
                    "top_services": report_data.top_cost_services,
                    "recommendations": report_data.optimization_recommendations
                }
                
                # Send report
                self.send_daily_report(report)
                
                return report
            else:
                logger.warning("No daily report data available")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            raise
    
    def send_daily_report(self, report: Dict):
        """Send daily cost report to Slack"""
        webhook_url = self.get_slack_webhook()
        if not webhook_url:
            return
        
        # Determine emoji based on status
        if "CRITICAL" in report['status']:
            emoji = "🚨"
        elif "WARNING" in report['status']:
            emoji = "⚠️"
        else:
            emoji = "📊"
        
        # Format message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Daily Cost Report - {report['date']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Daily Cost:*\nNT${report['daily_cost_ntd']:,.0f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Monthly Projection:*\nNT${report['projected_monthly_ntd']:,.0f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Budget Used:*\n{report['budget_utilization']}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{report['status']}"
                    }
                ]
            }
        ]
        
        slack_payload = {"blocks": blocks}
        
        try:
            response = requests.post(webhook_url, json=slack_payload)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")


def process_budget_alert(request: Request):
    """Cloud Function entry point for budget alerts"""
    try:
        # Parse Pub/Sub message
        envelope = request.get_json()
        if not envelope:
            return jsonify({'error': 'No message received'}), 400
        
        pubsub_message = envelope['message']
        data = json.loads(pubsub_message['data'].decode('base64'))
        
        # Process alert
        processor = BudgetProcessor()
        result = processor.process_budget_alert(data)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500


def generate_report(request: Request):
    """Generate cost report on demand"""
    try:
        data = request.get_json() or {}
        report_type = data.get('type', 'daily')
        
        processor = BudgetProcessor()
        
        if report_type == 'daily':
            result = processor.generate_daily_report()
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({'error': str(e)}), 500