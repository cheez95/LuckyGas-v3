"""Banking transfer tasks with scheduling and monitoring."""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import setup_logging
from app.models.banking import (BankConfiguration, PaymentBatch,
                                PaymentBatchStatus, ReconciliationLog,
                                ReconciliationStatus)
from app.services.banking_service import BankingService
from app.services.banking_sftp import BankingSFTPService
from app.services.file_generators.ach_format import TaiwanACHGenerator
from app.services.notification_service import NotificationService

# Setup logging
logger = logging.getLogger(__name__)
setup_logging()

# Initialize Celery
celery_app = Celery(
    "banking_tasks",
    broker=settings.REDIS_URL or "redis://localhost:6379/0",
    backend=settings.REDIS_URL or "redis://localhost:6379/0",
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Create database session factory
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_task_db() -> Session:
    """Get database session for tasks."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Schedule configuration
celery_app.conf.beat_schedule = {
    # Daily payment file generation and upload (6 AM Taiwan time)
    "generate-daily-payments": {
        "task": "banking_tasks.generate_and_upload_payments",
        "schedule": crontab(hour=6, minute=0),
        "args": (),
    },
    # Check for reconciliation files every 30 minutes during business hours
    "check-reconciliation-files": {
        "task": "banking_tasks.check_and_process_reconciliation",
        "schedule": crontab(minute="*/30", hour="8-18"),
        "args": (),
    },
    # Process retry queue every hour
    "process-retry-queue": {
        "task": "banking_tasks.process_retry_queue",
        "schedule": crontab(minute=0),
        "args": (),
    },
    # Daily reconciliation report (7 PM Taiwan time)
    "daily-reconciliation-report": {
        "task": "banking_tasks.generate_daily_report",
        "schedule": crontab(hour=19, minute=0),
        "args": (),
    },
    # Health check every 5 minutes
    "sftp-health-check": {
        "task": "banking_tasks.perform_health_check",
        "schedule": crontab(minute="*/5"),
        "args": (),
    },
}


@celery_app.task(bind=True, max_retries=3)
def generate_and_upload_payments(self) -> Dict[str, Any]:
    """
    Generate and upload daily payment files for all active banks.

    This task:
    1. Queries pending invoices for each bank
    2. Creates payment batches
    3. Generates ACH files
    4. Uploads via SFTP
    5. Sends notifications
    """
    db = next(get_task_db())
    results = {
        "processed_banks": [],
        "total_batches": 0,
        "total_transactions": 0,
        "total_amount": 0,
        "errors": [],
    }

    try:
        banking_service = BankingService(db)
        sftp_service = BankingSFTPService(db)
        notification_service = NotificationService(db)
        ach_generator = TaiwanACHGenerator()

        # Get all active bank configurations
        banks = db.query(BankConfiguration).filter_by(is_active=True).all()

        for bank_config in banks:
            try:
                logger.info(f"Processing payments for {bank_config.bank_code}")

                # Check if we're within the bank's processing window
                if not _is_within_processing_window(bank_config):
                    logger.info(
                        f"Outside processing window for {bank_config.bank_code}"
                    )
                    continue

                # Create payment batch
                batch = banking_service.create_payment_batch(
                    bank_code=bank_config.bank_code,
                    processing_date=datetime.utcnow().date(),
                )

                if batch.total_transactions == 0:
                    logger.info(
                        f"No transactions to process for {bank_config.bank_code}"
                    )
                    continue

                # Generate ACH file
                file_content = ach_generator.generate_payment_file(
                    batch, encoding=bank_config.encoding or "big5"
                )

                # Save file content to batch
                batch.file_content = file_content.decode(bank_config.encoding or "big5")
                batch.status = PaymentBatchStatus.GENERATED
                batch.generated_at = datetime.utcnow()
                db.commit()

                # Prepare file for upload
                file_name = _generate_file_name(
                    bank_config.payment_file_pattern,
                    batch.batch_number,
                    batch.processing_date,
                )

                # Create temporary file
                import tempfile

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".txt"
                ) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_path = tmp_file.name

                try:
                    # Upload via SFTP
                    remote_path = f"{bank_config.upload_path}/{file_name}"
                    result = asyncio.run(
                        sftp_service.transfer_file_with_retry(
                            bank_config=bank_config,
                            local_path=tmp_path,
                            remote_path=remote_path,
                            direction="upload",
                            encrypt=True,
                        )
                    )

                    if result.success:
                        # Update batch status
                        batch.status = PaymentBatchStatus.UPLOADED
                        batch.uploaded_at = datetime.utcnow()
                        batch.sftp_upload_path = remote_path
                        batch.file_name = file_name
                        batch.file_checksum = result.checksum
                        db.commit()

                        # Track results
                        results["total_batches"] += 1
                        results["total_transactions"] += batch.total_transactions
                        results["total_amount"] += float(batch.total_amount)
                        results["processed_banks"].append(
                            {
                                "bank_code": bank_config.bank_code,
                                "batch_number": batch.batch_number,
                                "transactions": batch.total_transactions,
                                "amount": float(batch.total_amount),
                                "file_name": file_name,
                            }
                        )

                        # Send success notification
                        # TODO: Fix async notification in sync Celery task
                        # await notification_service.send_notification(
                        #     type='email',
                        #     recipient=settings.BANKING_NOTIFICATION_EMAIL,
                        #     subject=f'Payment Batch Uploaded - {bank_config.bank_name}',
                        #     content=f"""
                        #     Payment batch {batch.batch_number} has been successfully uploaded.
                        #
                        #     Details:
                        #     - Bank: {bank_config.bank_name}
                        #     - Transactions: {batch.total_transactions}
                        #     - Total Amount: NT${batch.total_amount:,.2f}
                        #     - File: {file_name}
                        #     - Upload Time: {batch.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}
                        #     """
                        # )

                    else:
                        # Upload failed
                        batch.status = PaymentBatchStatus.FAILED
                        batch.error_message = result.error
                        db.commit()

                        results["errors"].append(
                            {
                                "bank_code": bank_config.bank_code,
                                "batch_number": batch.batch_number,
                                "error": result.error,
                            }
                        )

                        # Send failure notification
                        # TODO: Fix async notification in sync Celery task
                        # await notification_service.send_notification(
                        #     type='email',
                        #     recipient=settings.BANKING_NOTIFICATION_EMAIL,
                        #     subject=f'Payment Batch Upload Failed - {bank_config.bank_name}',
                        #     content=f"""
                        #     Failed to upload payment batch {batch.batch_number}.
                        #
                        #     Error: {result.error}
                        #     Retry Count: {result.retry_count}
                        #
                        #     The batch has been added to the retry queue.
                        #     """
                        # )

                finally:
                    # Clean up temp file
                    import os

                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            except Exception as e:
                logger.error(f"Error processing {bank_config.bank_code}: {e}")
                results["errors"].append(
                    {"bank_code": bank_config.bank_code, "error": str(e)}
                )

                # Send error notification
                await notification_service.send_alert(
                    level="error",
                    message=f"Banking task error for {bank_config.bank_code}: {e}",
                )

        logger.info(f"Daily payment generation completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Fatal error in payment generation task: {e}")
        self.retry(countdown=300, exc=e)  # Retry in 5 minutes

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def check_and_process_reconciliation(self) -> Dict[str, Any]:
    """
    Check for and process reconciliation files from all banks.
    """
    db = next(get_task_db())
    results = {
        "banks_checked": 0,
        "files_found": 0,
        "files_processed": 0,
        "transactions_reconciled": 0,
        "errors": [],
    }

    try:
        banking_service = BankingService(db)
        sftp_service = BankingSFTPService(db)
        notification_service = NotificationService(db)

        # Get all active bank configurations
        banks = db.query(BankConfiguration).filter_by(is_active=True).all()
        results["banks_checked"] = len(banks)

        for bank_config in banks:
            try:
                logger.info(
                    f"Checking reconciliation files for {bank_config.bank_code}"
                )

                # Check for new files
                new_files = banking_service.check_reconciliation_files(
                    bank_config.bank_code
                )
                results["files_found"] += len(new_files)

                for file_name in new_files:
                    try:
                        # Process reconciliation file
                        log = banking_service.process_reconciliation_file(
                            bank_config.bank_code, file_name
                        )

                        results["files_processed"] += 1
                        results["transactions_reconciled"] += log.matched_records

                        # Send notification for unmatched transactions
                        if log.unmatched_records > 0:
                            # TODO: Fix async notification in sync Celery task
                            # await notification_service.send_notification(
                            #     type='email',
                            #     recipient=settings.BANKING_NOTIFICATION_EMAIL,
                            #     subject=f'Reconciliation Alert - {bank_config.bank_name}',
                            #     content=f"""
                            #     Reconciliation file {file_name} has been processed with unmatched transactions.
                            #
                            #     Summary:
                            #     - Total Records: {log.total_records}
                            #     - Matched: {log.matched_records}
                            #     - Unmatched: {log.unmatched_records}
                            #     - Failed: {log.failed_records}
                            #
                            #     Please review the unmatched transactions in the admin panel.
                            #     """
                            # )
                            pass  # TODO: Implement sync notification

                    except Exception as e:
                        logger.error(f"Error processing {file_name}: {e}")
                        results["errors"].append(
                            {
                                "bank_code": bank_config.bank_code,
                                "file_name": file_name,
                                "error": str(e),
                            }
                        )

            except Exception as e:
                logger.error(f"Error checking {bank_config.bank_code}: {e}")
                results["errors"].append(
                    {"bank_code": bank_config.bank_code, "error": str(e)}
                )

        logger.info(f"Reconciliation check completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Fatal error in reconciliation task: {e}")
        self.retry(countdown=600, exc=e)  # Retry in 10 minutes

    finally:
        db.close()


@celery_app.task
def process_retry_queue() -> Dict[str, Any]:
    """Process failed transfers from the retry queue."""
    db = next(get_task_db())

    try:
        sftp_service = BankingSFTPService(db)

        # Process retry queue
        processed = asyncio.run(sftp_service.process_retry_queue())

        logger.info(f"Processed {processed} items from retry queue")

        return {"processed": processed, "remaining": sftp_service._retry_queue.qsize()}

    except Exception as e:
        logger.error(f"Error processing retry queue: {e}")
        return {"error": str(e), "processed": 0}

    finally:
        db.close()


@celery_app.task
def generate_daily_report() -> Dict[str, Any]:
    """Generate daily banking operations report."""
    db = next(get_task_db())

    try:
        # Get today's data
        today = datetime.utcnow().date()

        # Query batches
        batches = (
            db.query(PaymentBatch).filter(PaymentBatch.processing_date == today).all()
        )

        # Query reconciliations
        reconciliations = (
            db.query(ReconciliationLog)
            .filter(ReconciliationLog.file_received_at >= today)
            .all()
        )

        # Compile report
        report = {
            "date": today.isoformat(),
            "payment_batches": {
                "total": len(batches),
                "uploaded": len(
                    [b for b in batches if b.status == PaymentBatchStatus.UPLOADED]
                ),
                "failed": len(
                    [b for b in batches if b.status == PaymentBatchStatus.FAILED]
                ),
                "total_amount": sum(b.total_amount for b in batches),
                "total_transactions": sum(b.total_transactions for b in batches),
            },
            "reconciliations": {
                "files_processed": len(reconciliations),
                "matched_transactions": sum(r.matched_records for r in reconciliations),
                "unmatched_transactions": sum(
                    r.unmatched_records for r in reconciliations
                ),
                "failed_transactions": sum(r.failed_records for r in reconciliations),
            },
        }

        # Send report
        notification_service = NotificationService(db)
        # TODO: Fix async notification in sync Celery task
        # await notification_service.send_notification(
        #     type='email',
        #     recipient=settings.BANKING_NOTIFICATION_EMAIL,
        #     subject=f'Daily Banking Report - {today}',
        #     content=_format_daily_report(report)
        # )

        logger.info(f"Daily report generated: {report}")
        return report

    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task
def perform_health_check() -> Dict[str, Any]:
    """Perform health check on banking SFTP connections."""
    db = next(get_task_db())

    try:
        sftp_service = BankingSFTPService(db)
        health = sftp_service.health_check()

        # Check for degraded status
        if health["status"] == "degraded":
            # Send alert
            notification_service = NotificationService(db)
            failed_banks = [
                check["bank"]
                for check in health["checks"]
                if check["status"] == "failed"
            ]

            await notification_service.send_alert(
                level="warning",
                message=f"Banking SFTP connections degraded. Failed banks: {', '.join(failed_banks)}",
            )

        return health

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {"status": "error", "error": str(e)}

    finally:
        db.close()


def _is_within_processing_window(bank_config: BankConfiguration) -> bool:
    """Check if current time is within bank's processing window."""
    if not bank_config.cutoff_time:
        return True  # No cutoff time set

    try:
        # Parse cutoff time (HH:MM format)
        hour, minute = map(int, bank_config.cutoff_time.split(":"))
        cutoff = time(hour, minute)

        # Get current Taiwan time
        from pytz import timezone

        taiwan_tz = timezone("Asia/Taipei")
        current_time = datetime.now(taiwan_tz).time()

        return current_time < cutoff

    except Exception as e:
        logger.error(f"Error parsing cutoff time: {e}")
        return True  # Process anyway if error


def _generate_file_name(pattern: str, batch_number: str, date: datetime) -> str:
    """Generate file name from pattern."""
    import time as time_module

    replacements = {
        "{YYYY}": date.strftime("%Y"),
        "{MM}": date.strftime("%m"),
        "{DD}": date.strftime("%d"),
        "{YYYYMMDD}": date.strftime("%Y%m%d"),
        "{BATCH}": batch_number,
        "{TIMESTAMP}": str(int(time_module.time())),
    }

    file_name = pattern
    for key, value in replacements.items():
        file_name = file_name.replace(key, value)

    return file_name


def _format_daily_report(report: Dict[str, Any]) -> str:
    """Format daily report for email."""
    return f"""
Daily Banking Operations Report
Date: {report['date']}

Payment Batches:
- Total Batches: {report['payment_batches']['total']}
- Successfully Uploaded: {report['payment_batches']['uploaded']}
- Failed: {report['payment_batches']['failed']}
- Total Amount: NT${report['payment_batches']['total_amount']:,.2f}
- Total Transactions: {report['payment_batches']['total_transactions']}

Reconciliation Summary:
- Files Processed: {report['reconciliations']['files_processed']}
- Matched Transactions: {report['reconciliations']['matched_transactions']}
- Unmatched Transactions: {report['reconciliations']['unmatched_transactions']}
- Failed Transactions: {report['reconciliations']['failed_transactions']}

This is an automated report. For details, please check the admin panel.
"""


# Manual task triggers for testing
@celery_app.task
def test_bank_connection(bank_code: str) -> Dict[str, Any]:
    """Test SFTP connection for a specific bank."""
    db = next(get_task_db())

    try:
        bank_config = (
            db.query(BankConfiguration)
            .filter_by(bank_code=bank_code, is_active=True)
            .first()
        )

        if not bank_config:
            return {"error": f"Bank {bank_code} not found or inactive"}

        sftp_service = BankingSFTPService(db)

        with sftp_service.get_sftp_connection(bank_config) as sftp:
            # Test operations
            sftp.stat(".")
            files = sftp.listdir(bank_config.upload_path)

            return {
                "status": "connected",
                "bank_code": bank_code,
                "upload_path": bank_config.upload_path,
                "files_count": len(files),
            }

    except Exception as e:
        return {"status": "failed", "bank_code": bank_code, "error": str(e)}

    finally:
        db.close()
