"""
Business Continuity Testing Suite for LuckyGas v3
Tests backup, restore, disaster recovery, and operational continuity
"""

import asyncio
import json
import time
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
import asyncpg
import redis.asyncio as redis
from minio import Minio
from kubernetes import client, config
import pytest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessContinuityTest:
    def __init__(self, 
                 base_url: str = "http://localhost:8000",
                 db_url: str = "postgresql://postgres:password@localhost:5432/luckygas",
                 redis_url: str = "redis://localhost:6379",
                 minio_url: str = "localhost:9000"):
        self.base_url = base_url
        self.db_url = db_url
        self.redis_url = redis_url
        self.minio_url = minio_url
        self.results = []
        self.backup_location = "/tmp/luckygas-backups"
        
        # Initialize Kubernetes client
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.k8s_v1 = client.CoreV1Api()
        self.k8s_apps_v1 = client.AppsV1Api()
        
        # Ensure backup directory exists
        os.makedirs(self.backup_location, exist_ok=True)

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all business continuity tests"""
        test_scenarios = [
            self.test_backup_procedures,
            self.test_restore_procedures,
            self.test_point_in_time_recovery,
            self.test_disaster_recovery,
            self.test_data_consistency,
            self.test_rollback_procedures,
            self.test_alert_notifications,
            self.test_failover_procedures,
            self.test_data_export_import,
            self.test_service_degradation,
            self.test_compliance_requirements,
            self.test_recovery_time_objectives,
        ]
        
        for test in test_scenarios:
            logger.info(f"Running {test.__name__}...")
            result = await test()
            self.results.append(result)
            
        return self.generate_report()

    async def test_backup_procedures(self) -> Dict[str, Any]:
        """Test automated backup procedures"""
        result = {
            "test": "Backup Procedures",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Test database backup
            start_time = time.time()
            backup_file = f"{self.backup_location}/db_backup_{int(time.time())}.sql"
            
            # Trigger database backup
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/admin/backup/database",
                    headers={"Authorization": "Bearer admin_token"},
                    json={"destination": backup_file}
                )
                
                if response.status_code == 200:
                    backup_time = time.time() - start_time
                    result["metrics"]["database_backup_time"] = f"{backup_time:.2f}s"
                    result["details"].append(f"Database backup completed in {backup_time:.2f}s")
                    
                    # Verify backup file
                    if os.path.exists(backup_file):
                        file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
                        result["metrics"]["backup_size_mb"] = f"{file_size:.2f}"
                        
                        # Calculate checksum
                        with open(backup_file, 'rb') as f:
                            checksum = hashlib.sha256(f.read()).hexdigest()
                        result["metrics"]["backup_checksum"] = checksum[:16]
                    else:
                        result["status"] = "FAILED"
                        result["details"].append("Backup file not created")
                else:
                    result["status"] = "FAILED"
                    result["details"].append(f"Backup API failed: {response.status_code}")
            
            # Test file storage backup
            start_time = time.time()
            response = await client.post(
                f"{self.base_url}/api/v1/admin/backup/files",
                headers={"Authorization": "Bearer admin_token"},
                json={"bucket": "luckygas-files"}
            )
            
            if response.status_code == 200:
                file_backup_time = time.time() - start_time
                result["metrics"]["file_backup_time"] = f"{file_backup_time:.2f}s"
                result["details"].append(f"File backup completed in {file_backup_time:.2f}s")
            
            # Test configuration backup
            config_backup = await self._backup_configuration()
            if config_backup:
                result["details"].append("Configuration backup successful")
                result["metrics"]["config_backup_items"] = len(config_backup)
            
            # Test backup retention policy
            old_backups = self._get_old_backups(days=30)
            if old_backups:
                result["details"].append(f"Found {len(old_backups)} backups older than 30 days")
                # Test cleanup
                cleaned = await self._cleanup_old_backups(old_backups)
                if cleaned:
                    result["details"].append(f"Cleaned up {cleaned} old backups")
                    
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_restore_procedures(self) -> Dict[str, Any]:
        """Test restore procedures from backups"""
        result = {
            "test": "Restore Procedures",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Create test data
            test_customer = await self._create_test_customer()
            if not test_customer:
                result["status"] = "FAILED"
                result["details"].append("Failed to create test data")
                return result
            
            # Perform backup
            backup_file = await self._perform_full_backup()
            if not backup_file:
                result["status"] = "FAILED"
                result["details"].append("Failed to create backup")
                return result
            
            # Delete test data
            await self._delete_test_customer(test_customer["id"])
            
            # Verify deletion
            exists = await self._verify_customer_exists(test_customer["id"])
            if exists:
                result["status"] = "FAILED"
                result["details"].append("Failed to delete test data")
                return result
            
            # Perform restore
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/admin/restore/database",
                    headers={"Authorization": "Bearer admin_token"},
                    json={"backup_file": backup_file}
                )
                
                if response.status_code == 200:
                    restore_time = time.time() - start_time
                    result["metrics"]["restore_time"] = f"{restore_time:.2f}s"
                    result["details"].append(f"Database restored in {restore_time:.2f}s")
                    
                    # Verify restored data
                    await asyncio.sleep(2)  # Wait for restore to complete
                    exists = await self._verify_customer_exists(test_customer["id"])
                    if exists:
                        result["details"].append("Test data successfully restored")
                    else:
                        result["status"] = "FAILED"
                        result["details"].append("Restored data verification failed")
                else:
                    result["status"] = "FAILED"
                    result["details"].append(f"Restore API failed: {response.status_code}")
                    
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_point_in_time_recovery(self) -> Dict[str, Any]:
        """Test point-in-time recovery capabilities"""
        result = {
            "test": "Point-in-Time Recovery",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Create timeline of test data
            timeline_data = []
            base_time = datetime.now()
            
            for i in range(5):
                timestamp = base_time + timedelta(minutes=i*10)
                data = await self._create_timestamped_data(timestamp)
                timeline_data.append(data)
                result["details"].append(f"Created data at {timestamp.isoformat()}")
            
            # Select recovery point (3rd entry)
            recovery_point = timeline_data[2]["timestamp"]
            expected_data_count = 3
            
            # Perform point-in-time recovery
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/admin/restore/point-in-time",
                    headers={"Authorization": "Bearer admin_token"},
                    json={"recovery_point": recovery_point.isoformat()}
                )
                
                if response.status_code == 200:
                    result["details"].append(f"Point-in-time recovery to {recovery_point}")
                    
                    # Verify only data up to recovery point exists
                    actual_count = await self._count_data_before_timestamp(recovery_point)
                    if actual_count == expected_data_count:
                        result["details"].append("Point-in-time recovery verified successfully")
                    else:
                        result["status"] = "FAILED"
                        result["details"].append(f"Expected {expected_data_count} records, found {actual_count}")
                        
                    # Check WAL replay metrics
                    metrics = response.json().get("metrics", {})
                    result["metrics"]["wal_replay_time"] = metrics.get("replay_time", "N/A")
                    result["metrics"]["transactions_replayed"] = metrics.get("transactions", 0)
                else:
                    result["status"] = "FAILED"
                    result["details"].append("Point-in-time recovery not supported or failed")
                    
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_disaster_recovery(self) -> Dict[str, Any]:
        """Test complete disaster recovery scenario"""
        result = {
            "test": "Disaster Recovery",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Capture initial state
            initial_state = await self._capture_system_state()
            
            # Simulate disaster - delete all deployments
            logger.warning("Simulating disaster scenario...")
            deleted_resources = await self._simulate_disaster()
            result["details"].append(f"Simulated disaster: deleted {len(deleted_resources)} resources")
            
            # Measure downtime
            downtime_start = time.time()
            
            # Execute disaster recovery procedure
            recovery_start = time.time()
            
            # 1. Restore infrastructure
            infra_restored = await self._restore_infrastructure()
            if not infra_restored:
                result["status"] = "FAILED"
                result["details"].append("Infrastructure restoration failed")
                return result
            
            # 2. Restore databases
            db_restored = await self._restore_databases_from_backup()
            if not db_restored:
                result["status"] = "FAILED"
                result["details"].append("Database restoration failed")
                return result
            
            # 3. Restore application state
            app_restored = await self._restore_application_state()
            if not app_restored:
                result["status"] = "FAILED"
                result["details"].append("Application restoration failed")
                return result
            
            # 4. Verify system functionality
            system_healthy = await self._verify_system_health()
            
            recovery_time = time.time() - recovery_start
            total_downtime = time.time() - downtime_start
            
            result["metrics"]["recovery_time"] = f"{recovery_time:.2f}s"
            result["metrics"]["total_downtime"] = f"{total_downtime:.2f}s"
            result["metrics"]["rto_target"] = "300s"
            result["metrics"]["rto_achieved"] = recovery_time < 300
            
            if system_healthy:
                result["details"].append("System fully recovered and operational")
                
                # Verify data integrity
                final_state = await self._capture_system_state()
                data_loss = self._calculate_data_loss(initial_state, final_state)
                result["metrics"]["data_loss_percentage"] = f"{data_loss:.2f}%"
                
                if data_loss > 0.1:  # More than 0.1% data loss
                    result["status"] = "FAILED"
                    result["details"].append(f"Unacceptable data loss: {data_loss:.2f}%")
            else:
                result["status"] = "FAILED"
                result["details"].append("System health check failed after recovery")
                
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_data_consistency(self) -> Dict[str, Any]:
        """Test data consistency during backup and restore"""
        result = {
            "test": "Data Consistency",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Create complex transactional data
            test_order = await self._create_complex_order()
            
            # Calculate checksums for all related data
            original_checksums = await self._calculate_data_checksums(test_order["id"])
            
            # Perform backup during active transactions
            backup_task = asyncio.create_task(self._perform_full_backup())
            
            # Continue creating transactions during backup
            additional_orders = []
            for i in range(5):
                order = await self._create_complex_order()
                additional_orders.append(order)
                await asyncio.sleep(0.5)
            
            backup_file = await backup_task
            
            # Restore to new database instance
            test_db = await self._create_test_database()
            restore_success = await self._restore_to_database(backup_file, test_db)
            
            if restore_success:
                # Verify original order consistency
                restored_checksums = await self._calculate_data_checksums(
                    test_order["id"], 
                    db_name=test_db
                )
                
                if original_checksums == restored_checksums:
                    result["details"].append("Data consistency verified for backed up transactions")
                else:
                    result["status"] = "FAILED"
                    result["details"].append("Data inconsistency detected in backup")
                    result["metrics"]["checksum_mismatch"] = True
                
                # Check foreign key constraints
                fk_valid = await self._verify_foreign_keys(db_name=test_db)
                if fk_valid:
                    result["details"].append("Foreign key constraints maintained")
                else:
                    result["status"] = "FAILED"
                    result["details"].append("Foreign key violations detected")
                
                # Check data integrity rules
                integrity_valid = await self._verify_business_rules(db_name=test_db)
                if integrity_valid:
                    result["details"].append("Business rule integrity maintained")
                else:
                    result["status"] = "FAILED"
                    result["details"].append("Business rule violations detected")
                    
            # Cleanup test database
            await self._cleanup_test_database(test_db)
            
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_rollback_procedures(self) -> Dict[str, Any]:
        """Test rollback procedures for failed deployments"""
        result = {
            "test": "Rollback Procedures",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Get current deployment version
            current_version = await self._get_current_version()
            result["details"].append(f"Current version: {current_version}")
            
            # Create backup point
            rollback_point = await self._create_rollback_point()
            
            # Simulate bad deployment
            bad_version = "v99.99.99-bad"
            deployment_result = await self._deploy_version(bad_version)
            
            if deployment_result["status"] == "failed":
                result["details"].append("Bad deployment failed as expected")
                
                # Execute rollback
                rollback_start = time.time()
                rollback_success = await self._execute_rollback(rollback_point)
                rollback_time = time.time() - rollback_start
                
                if rollback_success:
                    result["metrics"]["rollback_time"] = f"{rollback_time:.2f}s"
                    result["details"].append(f"Rollback completed in {rollback_time:.2f}s")
                    
                    # Verify system is back to original version
                    restored_version = await self._get_current_version()
                    if restored_version == current_version:
                        result["details"].append("System successfully rolled back to previous version")
                    else:
                        result["status"] = "FAILED"
                        result["details"].append(f"Version mismatch after rollback: {restored_version}")
                    
                    # Verify no data loss
                    data_intact = await self._verify_data_integrity_after_rollback(rollback_point)
                    if data_intact:
                        result["details"].append("Data integrity maintained after rollback")
                    else:
                        result["status"] = "FAILED"
                        result["details"].append("Data integrity compromised after rollback")
                else:
                    result["status"] = "FAILED"
                    result["details"].append("Rollback procedure failed")
            else:
                result["status"] = "FAILED"
                result["details"].append("Test setup failed - bad deployment succeeded")
                
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_alert_notifications(self) -> Dict[str, Any]:
        """Test alert and notification systems during incidents"""
        result = {
            "test": "Alert Notifications",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Configure test notification endpoints
            notification_configs = [
                {"type": "email", "target": "ops@luckygas.com"},
                {"type": "sms", "target": "+886912345678"},
                {"type": "slack", "target": "#alerts"},
                {"type": "webhook", "target": "https://alerts.luckygas.com/webhook"}
            ]
            
            # Trigger various alert scenarios
            alert_scenarios = [
                ("database_down", "CRITICAL", "Database connection lost"),
                ("high_error_rate", "WARNING", "Error rate exceeded 5%"),
                ("backup_failed", "ERROR", "Nightly backup failed"),
                ("disk_space_low", "WARNING", "Disk usage above 85%"),
                ("security_breach", "CRITICAL", "Unauthorized access detected"),
            ]
            
            notifications_sent = []
            notifications_failed = []
            
            for alert_type, severity, message in alert_scenarios:
                # Trigger alert
                alert_result = await self._trigger_alert(alert_type, severity, message)
                
                if alert_result["sent"]:
                    notifications_sent.append(alert_type)
                    result["details"].append(f"Alert sent: {alert_type} ({severity})")
                    
                    # Verify delivery
                    delivered = await self._verify_notification_delivery(
                        alert_result["notification_id"]
                    )
                    if not delivered:
                        notifications_failed.append(alert_type)
                else:
                    notifications_failed.append(alert_type)
                    result["details"].append(f"Failed to send alert: {alert_type}")
            
            # Calculate metrics
            total_alerts = len(alert_scenarios)
            successful = len(notifications_sent) - len(notifications_failed)
            result["metrics"]["alerts_sent"] = len(notifications_sent)
            result["metrics"]["alerts_delivered"] = successful
            result["metrics"]["delivery_rate"] = f"{(successful/total_alerts)*100:.1f}%"
            
            # Test alert escalation
            escalation_test = await self._test_alert_escalation()
            if escalation_test["escalated"]:
                result["details"].append("Alert escalation working correctly")
                result["metrics"]["escalation_time"] = escalation_test["time"]
            else:
                result["status"] = "FAILED"
                result["details"].append("Alert escalation failed")
            
            # Test notification deduplication
            dedup_test = await self._test_notification_deduplication()
            if dedup_test["working"]:
                result["details"].append("Notification deduplication working")
            else:
                result["details"].append("Warning: Duplicate notifications detected")
                
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_failover_procedures(self) -> Dict[str, Any]:
        """Test automatic failover procedures"""
        result = {
            "test": "Failover Procedures",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Test database failover
            db_failover = await self._test_database_failover()
            if db_failover["success"]:
                result["details"].append("Database failover successful")
                result["metrics"]["db_failover_time"] = db_failover["time"]
            else:
                result["status"] = "FAILED"
                result["details"].append("Database failover failed")
            
            # Test application failover
            app_failover = await self._test_application_failover()
            if app_failover["success"]:
                result["details"].append("Application failover successful")
                result["metrics"]["app_failover_time"] = app_failover["time"]
            else:
                result["status"] = "FAILED"
                result["details"].append("Application failover failed")
            
            # Test load balancer failover
            lb_failover = await self._test_load_balancer_failover()
            if lb_failover["success"]:
                result["details"].append("Load balancer failover successful")
                result["metrics"]["lb_failover_time"] = lb_failover["time"]
            
            # Calculate total failover time
            total_failover_time = sum([
                float(db_failover.get("time", "0").rstrip("s")),
                float(app_failover.get("time", "0").rstrip("s")),
                float(lb_failover.get("time", "0").rstrip("s"))
            ])
            
            result["metrics"]["total_failover_time"] = f"{total_failover_time:.2f}s"
            result["metrics"]["meets_rto"] = total_failover_time < 300  # 5 minute RTO
            
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_data_export_import(self) -> Dict[str, Any]:
        """Test data export and import procedures"""
        result = {
            "test": "Data Export/Import",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Test customer data export
            export_formats = ["csv", "excel", "json"]
            
            for format in export_formats:
                export_result = await self._export_data("customers", format)
                if export_result["success"]:
                    result["details"].append(f"Customer data exported to {format}")
                    result["metrics"][f"{format}_export_size"] = export_result["size"]
                    
                    # Test import
                    import_result = await self._import_data(
                        "customers", 
                        export_result["file"], 
                        format
                    )
                    if import_result["success"]:
                        result["details"].append(f"Successfully imported from {format}")
                        result["metrics"][f"{format}_import_records"] = import_result["records"]
                    else:
                        result["status"] = "FAILED"
                        result["details"].append(f"Import failed for {format}")
                else:
                    result["status"] = "FAILED"
                    result["details"].append(f"Export failed for {format}")
            
            # Test large dataset handling
            large_export = await self._test_large_data_export(records=100000)
            if large_export["success"]:
                result["details"].append("Large dataset export successful")
                result["metrics"]["large_export_time"] = large_export["time"]
                result["metrics"]["throughput_mbps"] = large_export["throughput"]
            
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_service_degradation(self) -> Dict[str, Any]:
        """Test graceful service degradation"""
        result = {
            "test": "Service Degradation",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Test with various service failures
            degradation_scenarios = [
                ("redis", "caching"),
                ("elasticsearch", "search"),
                ("email", "notifications"),
                ("maps_api", "route_optimization"),
            ]
            
            for service, feature in degradation_scenarios:
                # Disable service
                await self._disable_service(service)
                
                # Test system functionality
                functionality = await self._test_core_functionality()
                
                if functionality["operational"]:
                    result["details"].append(f"System operational without {service}")
                    result["metrics"][f"{service}_degraded"] = True
                    
                    # Check if feature is properly degraded
                    feature_status = await self._check_feature_status(feature)
                    if feature_status == "degraded":
                        result["details"].append(f"{feature} feature gracefully degraded")
                    elif feature_status == "failed":
                        result["status"] = "FAILED"
                        result["details"].append(f"{feature} feature failed instead of degrading")
                else:
                    result["status"] = "FAILED"
                    result["details"].append(f"System failed without {service}")
                
                # Re-enable service
                await self._enable_service(service)
                
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_compliance_requirements(self) -> Dict[str, Any]:
        """Test compliance and audit requirements"""
        result = {
            "test": "Compliance Requirements",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Test audit log completeness
            audit_test = await self._test_audit_logging()
            if audit_test["complete"]:
                result["details"].append("Audit logging is comprehensive")
                result["metrics"]["audit_coverage"] = audit_test["coverage"]
            else:
                result["status"] = "FAILED"
                result["details"].append("Audit logging incomplete")
            
            # Test data retention policies
            retention_test = await self._test_data_retention()
            if retention_test["compliant"]:
                result["details"].append("Data retention policies enforced")
                result["metrics"]["retention_days"] = retention_test["days"]
            else:
                result["status"] = "FAILED"
                result["details"].append("Data retention non-compliant")
            
            # Test data privacy compliance
            privacy_test = await self._test_data_privacy()
            if privacy_test["compliant"]:
                result["details"].append("Data privacy requirements met")
            else:
                result["status"] = "FAILED"
                result["details"].append("Data privacy violations found")
            
            # Test backup encryption
            encryption_test = await self._test_backup_encryption()
            if encryption_test["encrypted"]:
                result["details"].append("Backups are properly encrypted")
                result["metrics"]["encryption_algorithm"] = encryption_test["algorithm"]
            else:
                result["status"] = "FAILED"
                result["details"].append("Backup encryption not implemented")
                
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    async def test_recovery_time_objectives(self) -> Dict[str, Any]:
        """Test Recovery Time and Point Objectives"""
        result = {
            "test": "RTO/RPO Compliance",
            "status": "PASSED",
            "details": [],
            "metrics": {}
        }
        
        try:
            # Define objectives
            rto_target = 300  # 5 minutes
            rpo_target = 60   # 1 minute
            
            # Test RTO
            simulated_failures = [
                "database_crash",
                "app_server_failure",
                "network_partition",
                "storage_failure"
            ]
            
            recovery_times = []
            
            for failure in simulated_failures:
                # Simulate failure
                failure_time = datetime.now()
                await self._simulate_failure(failure)
                
                # Measure recovery
                recovery_start = time.time()
                recovery_success = await self._automated_recovery()
                recovery_time = time.time() - recovery_start
                
                recovery_times.append(recovery_time)
                
                if recovery_success and recovery_time <= rto_target:
                    result["details"].append(f"{failure}: Recovered in {recovery_time:.2f}s ✓")
                else:
                    result["status"] = "FAILED"
                    result["details"].append(f"{failure}: Recovery took {recovery_time:.2f}s ✗")
            
            # Calculate metrics
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            max_recovery_time = max(recovery_times)
            
            result["metrics"]["average_rto"] = f"{avg_recovery_time:.2f}s"
            result["metrics"]["max_rto"] = f"{max_recovery_time:.2f}s"
            result["metrics"]["rto_target"] = f"{rto_target}s"
            result["metrics"]["rto_achieved"] = max_recovery_time <= rto_target
            
            # Test RPO
            data_loss_test = await self._test_maximum_data_loss()
            if data_loss_test["max_loss_seconds"] <= rpo_target:
                result["details"].append(f"RPO achieved: {data_loss_test['max_loss_seconds']}s")
                result["metrics"]["rpo_achieved"] = True
            else:
                result["status"] = "FAILED"
                result["details"].append(f"RPO violated: {data_loss_test['max_loss_seconds']}s > {rpo_target}s")
                result["metrics"]["rpo_achieved"] = False
            
            result["metrics"]["rpo_actual"] = f"{data_loss_test['max_loss_seconds']}s"
            result["metrics"]["rpo_target"] = f"{rpo_target}s"
            
        except Exception as e:
            result["status"] = "FAILED"
            result["details"].append(f"Error: {str(e)}")
            
        return result

    # Helper methods
    async def _create_test_customer(self) -> Optional[Dict[str, Any]]:
        """Create a test customer for backup/restore testing"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/customers",
                json={
                    "code": f"BCT_TEST_{int(time.time())}",
                    "name": "Business Continuity Test Customer",
                    "phone": "0912345678",
                    "address": "Test Address"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            if response.status_code == 201:
                return response.json()
            return None

    async def _delete_test_customer(self, customer_id: int) -> bool:
        """Delete test customer"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/customers/{customer_id}",
                headers={"Authorization": "Bearer test_token"}
            )
            return response.status_code == 204

    async def _verify_customer_exists(self, customer_id: int) -> bool:
        """Verify if customer exists"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/customers/{customer_id}",
                headers={"Authorization": "Bearer test_token"}
            )
            return response.status_code == 200

    async def _perform_full_backup(self) -> Optional[str]:
        """Perform full system backup"""
        backup_file = f"{self.backup_location}/full_backup_{int(time.time())}.tar.gz"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/admin/backup/full",
                json={"destination": backup_file},
                headers={"Authorization": "Bearer admin_token"},
                timeout=300.0
            )
            
            if response.status_code == 200:
                return backup_file
            return None

    async def _backup_configuration(self) -> Optional[Dict[str, Any]]:
        """Backup system configuration"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/admin/configuration/export",
                headers={"Authorization": "Bearer admin_token"}
            )
            
            if response.status_code == 200:
                return response.json()
            return None

    def _get_old_backups(self, days: int) -> List[str]:
        """Get backups older than specified days"""
        old_backups = []
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for file in os.listdir(self.backup_location):
            file_path = os.path.join(self.backup_location, file)
            if os.path.isfile(file_path):
                if os.path.getmtime(file_path) < cutoff_time:
                    old_backups.append(file_path)
                    
        return old_backups

    async def _cleanup_old_backups(self, backups: List[str]) -> int:
        """Clean up old backup files"""
        cleaned = 0
        for backup in backups:
            try:
                os.remove(backup)
                cleaned += 1
            except:
                pass
        return cleaned

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive business continuity test report"""
        passed_tests = sum(1 for r in self.results if r["status"] == "PASSED")
        total_tests = len(self.results)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "readiness_score": f"{(passed_tests/total_tests)*100:.1f}%"
            },
            "compliance": {
                "rto_target": "5 minutes",
                "rpo_target": "1 minute",
                "backup_frequency": "hourly",
                "retention_period": "30 days"
            },
            "test_results": self.results,
            "recommendations": [],
            "risk_assessment": []
        }
        
        # Generate recommendations
        for result in self.results:
            if result["status"] == "FAILED":
                if "Backup" in result["test"]:
                    report["recommendations"].append({
                        "priority": "CRITICAL",
                        "action": "Fix backup procedures immediately",
                        "details": "Backup failures put business continuity at risk"
                    })
                elif "RTO" in result["test"] or "Recovery" in result["test"]:
                    report["recommendations"].append({
                        "priority": "HIGH",
                        "action": "Improve recovery procedures",
                        "details": "Current recovery times exceed business requirements"
                    })
                elif "Alert" in result["test"]:
                    report["recommendations"].append({
                        "priority": "MEDIUM",
                        "action": "Fix notification system",
                        "details": "Alert failures delay incident response"
                    })
        
        # Risk assessment
        if report["summary"]["readiness_score"] < "80%":
            report["risk_assessment"].append({
                "risk": "HIGH",
                "description": "Business continuity readiness below acceptable threshold",
                "impact": "Extended downtime and potential data loss during incidents",
                "mitigation": "Immediate remediation of failed tests required"
            })
        
        return report


async def main():
    """Run business continuity tests"""
    tester = BusinessContinuityTest()
    report = await tester.run_all_tests()
    
    # Save report
    with open("business-continuity-report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nBusiness Continuity Test Summary:")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Readiness Score: {report['summary']['readiness_score']}")
    
    if report['recommendations']:
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"- [{rec['priority']}] {rec['action']}")
    
    return report['summary']['failed'] == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)