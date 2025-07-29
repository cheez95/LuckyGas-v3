"""Banking monitoring and management API endpoints."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.api.auth_deps.security import get_current_user
from app.api.deps import get_db
from app.models.user import User
from app.models.banking import (
    PaymentBatch, PaymentBatchStatus, PaymentTransaction,
    ReconciliationLog, ReconciliationStatus, BankConfiguration,
    TransactionStatus
)
from app.services.banking_sftp import BankingSFTPService
from app.services.banking_service import BankingService
# TODO: Fix async notifications in banking_transfers.py
# from app.tasks.banking_transfers import (
#     test_bank_connection,
#     generate_and_upload_payments,
#     check_and_process_reconciliation
# )
from app.schemas.banking import (
    BankingHealthCheck, TransferHistory, PaymentBatchDetail,
    ReconciliationDetail, BankConnectionTest, BankingDashboard,
    RetryQueueStatus, BankConfigurationUpdate
)

router = APIRouter(prefix="/banking-monitor", tags=["Banking Monitor"])


@router.get("/health", response_model=BankingHealthCheck)
def get_banking_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive health status of banking systems."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    sftp_service = BankingSFTPService(db)
    health = sftp_service.health_check()
    
    # Add additional metrics
    today = datetime.utcnow().date()
    
    # Get today's batch statistics
    batch_stats = db.query(
        PaymentBatchStatus,
        func.count(PaymentBatch.id).label('count')
    ).join(
        PaymentBatch
    ).filter(
        PaymentBatch.processing_date == today
    ).group_by(PaymentBatchStatus).all()
    
    health['daily_batches'] = {
        status.value: count for status, count in batch_stats
    }
    
    # Get reconciliation statistics
    recon_stats = db.query(
        ReconciliationStatus,
        func.count(ReconciliationLog.id).label('count')
    ).join(
        ReconciliationLog
    ).filter(
        ReconciliationLog.file_received_at >= today
    ).group_by(ReconciliationStatus).all()
    
    health['daily_reconciliations'] = {
        status.value: count for status, count in recon_stats
    }
    
    return health


@router.get("/dashboard", response_model=BankingDashboard)
def get_banking_dashboard(
    days: int = Query(7, description="Number of days to include"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get banking operations dashboard data."""
    if current_user.role not in ["admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    start_date = datetime.utcnow().date() - timedelta(days=days)
    
    # Payment batch trends
    batch_trends = db.query(
        PaymentBatch.processing_date,
        PaymentBatch.bank_code,
        func.count(PaymentBatch.id).label('batch_count'),
        func.sum(PaymentBatch.total_transactions).label('transaction_count'),
        func.sum(PaymentBatch.total_amount).label('total_amount')
    ).filter(
        PaymentBatch.processing_date >= start_date
    ).group_by(
        PaymentBatch.processing_date,
        PaymentBatch.bank_code
    ).all()
    
    # Success rates by bank
    success_rates = db.query(
        PaymentBatch.bank_code,
        PaymentBatchStatus,
        func.count(PaymentBatch.id).label('count')
    ).filter(
        PaymentBatch.processing_date >= start_date
    ).group_by(
        PaymentBatch.bank_code,
        PaymentBatchStatus
    ).all()
    
    # Recent failures
    recent_failures = db.query(PaymentBatch).filter(
        and_(
            PaymentBatch.status == PaymentBatchStatus.FAILED,
            PaymentBatch.created_at >= datetime.utcnow() - timedelta(days=days)
        )
    ).order_by(PaymentBatch.created_at.desc()).limit(10).all()
    
    # Pending reconciliations
    pending_recons = db.query(ReconciliationLog).filter(
        ReconciliationLog.status.in_([
            ReconciliationStatus.PENDING,
            ReconciliationStatus.UNMATCHED
        ])
    ).count()
    
    return {
        'period_days': days,
        'batch_trends': [
            {
                'date': trend.processing_date.isoformat(),
                'bank_code': trend.bank_code,
                'batch_count': trend.batch_count,
                'transaction_count': trend.transaction_count or 0,
                'total_amount': float(trend.total_amount or 0)
            }
            for trend in batch_trends
        ],
        'success_rates': _calculate_success_rates(success_rates),
        'recent_failures': [
            {
                'batch_number': batch.batch_number,
                'bank_code': batch.bank_code,
                'error_message': batch.error_message,
                'created_at': batch.created_at.isoformat()
            }
            for batch in recent_failures
        ],
        'pending_reconciliations': pending_recons,
        'last_updated': datetime.utcnow().isoformat()
    }


@router.get("/transfer-history", response_model=List[TransferHistory])
def get_transfer_history(
    bank_code: Optional[str] = None,
    hours: int = Query(24, description="Hours of history to retrieve"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent SFTP transfer history."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    sftp_service = BankingSFTPService(db)
    history = sftp_service.get_transfer_history(bank_code, hours)
    
    return [
        {
            'file_name': transfer.file_name,
            'remote_path': transfer.remote_path,
            'success': transfer.success,
            'transfer_time': transfer.transfer_time,
            'checksum': transfer.checksum,
            'error': transfer.error,
            'retry_count': transfer.retry_count,
            'timestamp': datetime.utcnow().isoformat()  # Would need to add to TransferResult
        }
        for transfer in history
    ]


@router.get("/batches/{batch_id}", response_model=PaymentBatchDetail)
def get_batch_detail(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a payment batch."""
    if current_user.role not in ["admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    banking_service = BankingService(db)
    
    try:
        report = banking_service.get_payment_status_report(batch_id)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/reconciliations/{log_id}", response_model=ReconciliationDetail)
def get_reconciliation_detail(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a reconciliation log."""
    if current_user.role not in ["admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    log = db.query(ReconciliationLog).filter_by(id=log_id).first()
    
    if not log:
        raise HTTPException(status_code=404, detail="Reconciliation log not found")
    
    # Get unmatched transactions
    unmatched_transactions = []
    if log.batch_id and log.unmatched_records > 0:
        unmatched = db.query(PaymentTransaction).filter(
            and_(
                PaymentTransaction.batch_id == log.batch_id,
                PaymentTransaction.status != TransactionStatus.SUCCESS
            )
        ).all()
        
        unmatched_transactions = [
            {
                'transaction_id': t.transaction_id,
                'customer_id': t.customer_id,
                'amount': float(t.amount),
                'status': t.status.value,
                'error_code': t.bank_response_code,
                'error_message': t.bank_response_message
            }
            for t in unmatched
        ]
    
    return {
        'id': log.id,
        'file_name': log.file_name,
        'file_received_at': log.file_received_at.isoformat(),
        'status': log.status.value,
        'total_records': log.total_records,
        'matched_records': log.matched_records,
        'unmatched_records': log.unmatched_records,
        'failed_records': log.failed_records,
        'processed_at': log.processed_at.isoformat() if log.processed_at else None,
        'error_details': log.error_details,
        'unmatched_transactions': unmatched_transactions
    }


@router.post("/test-connection", response_model=BankConnectionTest)
def test_bank_sftp_connection(
    bank_code: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test SFTP connection for a specific bank."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Verify bank exists
    bank = db.query(BankConfiguration).filter_by(
        bank_code=bank_code,
        is_active=True
    ).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Bank configuration not found")
    
    # Run test asynchronously
    task = test_bank_connection.delay(bank_code)
    
    return {
        'task_id': task.id,
        'bank_code': bank_code,
        'status': 'testing',
        'message': 'Connection test started'
    }


@router.get("/retry-queue", response_model=RetryQueueStatus)
def get_retry_queue_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of the retry queue."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    sftp_service = BankingSFTPService(db)
    
    return {
        'queue_size': sftp_service._retry_queue.qsize(),
        'oldest_item_age': None,  # Would need to track this
        'processing': False,  # Would need to track this
        'last_processed': None  # Would need to track this
    }


@router.post("/retry-queue/process")
def trigger_retry_processing(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger retry queue processing."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.tasks.banking_transfers import process_retry_queue
    
    task = process_retry_queue.delay()
    
    return {
        'task_id': task.id,
        'status': 'processing',
        'message': 'Retry queue processing started'
    }


@router.post("/batches/generate")
def trigger_payment_generation(
    bank_code: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger payment batch generation."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    task = generate_and_upload_payments.delay()
    
    return {
        'task_id': task.id,
        'status': 'processing',
        'message': f'Payment generation started for {"all banks" if not bank_code else bank_code}'
    }


@router.post("/reconciliations/check")
def trigger_reconciliation_check(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger reconciliation file checking."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    task = check_and_process_reconciliation.delay()
    
    return {
        'task_id': task.id,
        'status': 'processing',
        'message': 'Reconciliation check started'
    }


@router.put("/banks/{bank_code}/config", response_model=Dict[str, str])
def update_bank_configuration(
    bank_code: str,
    config: BankConfigurationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update bank configuration settings."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    bank = db.query(BankConfiguration).filter_by(bank_code=bank_code).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Bank configuration not found")
    
    # Update allowed fields
    update_fields = config.dict(exclude_unset=True)
    
    # Don't allow updating sensitive fields via API
    sensitive_fields = ['sftp_password', 'sftp_private_key']
    for field in sensitive_fields:
        update_fields.pop(field, None)
    
    for field, value in update_fields.items():
        setattr(bank, field, value)
    
    bank.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        'status': 'updated',
        'bank_code': bank_code,
        'updated_fields': list(update_fields.keys())
    }


def _calculate_success_rates(success_data: List) -> Dict[str, Dict[str, float]]:
    """Calculate success rates by bank from status data."""
    rates = {}
    
    # Group by bank
    bank_stats = {}
    for bank_code, status, count in success_data:
        if bank_code not in bank_stats:
            bank_stats[bank_code] = {}
        bank_stats[bank_code][status.value] = count
    
    # Calculate rates
    for bank_code, stats in bank_stats.items():
        total = sum(stats.values())
        uploaded = stats.get('uploaded', 0)
        reconciled = stats.get('reconciled', 0)
        
        rates[bank_code] = {
            'total_batches': total,
            'upload_rate': (uploaded / total * 100) if total > 0 else 0,
            'reconciliation_rate': (reconciled / total * 100) if total > 0 else 0
        }
    
    return rates


# Add to app/api/v1/__init__.py to register the router
# from app.api.v1 import banking_monitor
# api_router.include_router(banking_monitor.router)