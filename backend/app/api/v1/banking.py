"""Banking API endpoints for payment processing and reconciliation."""
from typing import Any, List, Optional

import logging
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api import deps
from app.models.banking import BankConfiguration, PaymentBatch
from app.models.user import User
from app.schemas.banking import (
    BankConfigCreate,
    BankConfigResponse,
    BankConfigUpdate,
    CheckReconciliationResponse,
    GeneratePaymentFileRequest,
    GeneratePaymentFileResponse,
    PaymentBatchCreate,
    PaymentBatchListResponse,
    PaymentBatchResponse,
    PaymentStatusReport,
    ProcessReconciliationRequest,
    ReconciliationLogResponse,
    UploadFileRequest,
    UploadFileResponse,
)
from app.services.banking_service import BankingService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate - payment - file", response_model=GeneratePaymentFileResponse)
async def generate_payment_file(
    *,
    db: Session = Depends(deps.get_db),
    request: GeneratePaymentFileRequest,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Generate payment collection file for a batch.

    Requires: Manager or Admin role
    """
    if not current_user.is_superuser and current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    banking_service = BankingService(db)

    try:
        # Get batch
        batch = db.query(PaymentBatch).filter_by(id=request.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Payment batch not found")

        # Generate file
        content = banking_service.generate_payment_file(request.batch_id)

        # Update batch
        batch.file_content = content
        batch.status = "generated"
        batch.generated_at = datetime.utcnow()
        db.commit()

        return GeneratePaymentFileResponse(
            success=True,
            file_name=f"{batch.batch_number}.txt",
            file_size=len(content.encode("utf - 8")),
            message="Payment file generated successfully",
        )

    except Exception as e:
        logger.error(f"Failed to generate payment file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload - file/{bank_code}", response_model=UploadFileResponse)
async def upload_payment_file(
    *,
    db: Session = Depends(deps.get_db),
    bank_code: str,
    request: UploadFileRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Upload payment file to bank via SFTP.

    Requires: Manager or Admin role
    """
    if not current_user.is_superuser and current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Verify bank configuration exists
    bank_config = (
        db.query(BankConfiguration)
        .filter_by(bank_code=bank_code, is_active=True)
        .first()
    )

    if not bank_config:
        raise HTTPException(
            status_code=404, detail=f"No active configuration for bank {bank_code}"
        )

    banking_service = BankingService(db)

    try:
        # Upload file
        success = banking_service.upload_payment_file(request.batch_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload file")

        batch = db.query(PaymentBatch).filter_by(id=request.batch_id).first()

        return UploadFileResponse(
            success=True,
            uploaded_at=batch.uploaded_at,
            remote_path=batch.sftp_upload_path,
            message="File uploaded successfully",
        )

    except Exception as e:
        logger.error(f"Failed to upload payment file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check - reconciliation", response_model=List[CheckReconciliationResponse])
async def check_reconciliation_files(
    *,
    db: Session = Depends(deps.get_db),
    bank_codes: Optional[List[str]] = Query(None, description="Bank codes to check"),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Check for new reconciliation files from banks.

    Requires: Manager or Admin role
    """
    if not current_user.is_superuser and current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    banking_service = BankingService(db)

    # Get active bank configurations
    query = db.query(BankConfiguration).filter_by(is_active=True)

    if bank_codes:
        query = query.filter(BankConfiguration.bank_code.in_(bank_codes))

    banks = query.all()

    results = []
    for bank in banks:
        try:
            new_files = banking_service.check_reconciliation_files(bank.bank_code)
            results.append(
                CheckReconciliationResponse(
                    bank_code=bank.bank_code,
                    new_files=new_files,
                    checked_at=datetime.utcnow(),
                )
            )
        except Exception as e:
            logger.error(
                f"Failed to check reconciliation for {bank.bank_code}: {str(e)}"
            )
            results.append(
                CheckReconciliationResponse(
                    bank_code=bank.bank_code, new_files=[], checked_at=datetime.utcnow()
                )
            )

    return results


@router.post("/process - reconciliation", response_model=ReconciliationLogResponse)
async def process_reconciliation_file(
    *,
    db: Session = Depends(deps.get_db),
    request: ProcessReconciliationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Process a reconciliation file from bank.

    Requires: Manager or Admin role
    """
    if not current_user.is_superuser and current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    banking_service = BankingService(db)

    try:
        # Process file
        log = banking_service.process_reconciliation_file(
            request.bank_code, request.file_name
        )

        return ReconciliationLogResponse.model_validate(log)

    except Exception as e:
        logger.error(f"Failed to process reconciliation file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payment - status/{batch_id}", response_model=PaymentStatusReport)
async def get_payment_status(
    *,
    db: Session = Depends(deps.get_db),
    batch_id: int,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get detailed payment status report for a batch.

    Requires: Any authenticated user
    """
    banking_service = BankingService(db)

    try:
        report = banking_service.get_payment_status_report(batch_id)
        return PaymentStatusReport(**report)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get payment status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payment - batches", response_model=PaymentBatchResponse)
async def create_payment_batch(
    *,
    db: Session = Depends(deps.get_db),
    batch_in: PaymentBatchCreate,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Create a new payment batch for processing.

    Requires: Manager or Admin role
    """
    if not current_user.is_superuser and current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    banking_service = BankingService(db)

    try:
        batch = banking_service.create_payment_batch(
            bank_code=batch_in.bank_code,
            processing_date=batch_in.processing_date,
            invoice_ids=batch_in.invoice_ids,
        )

        return PaymentBatchResponse.model_validate(batch)

    except Exception as e:
        logger.error(f"Failed to create payment batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payment - batches", response_model=PaymentBatchListResponse)
async def list_payment_batches(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    bank_code: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    current_user: User = Depends(deps.get_current_user),
):
    """
    List payment batches with filters.

    Requires: Any authenticated user
    """
    query = db.query(PaymentBatch)

    # Apply filters
    filters = []
    if bank_code:
        filters.append(PaymentBatch.bank_code == bank_code)
    if status:
        filters.append(PaymentBatch.status == status)
    if from_date:
        filters.append(PaymentBatch.processing_date >= from_date)
    if to_date:
        filters.append(PaymentBatch.processing_date <= to_date)

    if filters:
        query = query.filter(and_(*filters))

    # Get total count
    total = query.count()

    # Get paginated results
    batches = (
        query.order_by(PaymentBatch.created_at.desc()).offset(skip).limit(limit).all()
    )

    return PaymentBatchListResponse(
        items=[PaymentBatchResponse.model_validate(b) for b in batches],
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit,
    )


# Bank Configuration Endpoints


@router.get("/banks", response_model=List[BankConfigResponse])
async def list_bank_configurations(
    *,
    db: Session = Depends(deps.get_db),
    active_only: bool = Query(True, description="Only return active configurations"),
    current_user: User = Depends(deps.get_current_user),
):
    """
    List all bank configurations.

    Requires: Manager or Admin role
    """
    if not current_user.is_superuser and current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    query = db.query(BankConfiguration)

    if active_only:
        query = query.filter_by(is_active=True)

    banks = query.all()

    return [BankConfigResponse.model_validate(b) for b in banks]


@router.post("/banks", response_model=BankConfigResponse)
async def create_bank_configuration(
    *,
    db: Session = Depends(deps.get_db),
    bank_in: BankConfigCreate,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Create a new bank configuration.

    Requires: Admin role
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check if bank code already exists
    existing = (
        db.query(BankConfiguration).filter_by(bank_code=bank_in.bank_code).first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail=f"Bank code {bank_in.bank_code} already exists"
        )

    # Create bank configuration
    bank_config = BankConfiguration(
        **bank_in.model_dump(exclude={"sftp_password"}),
        # In production, encrypt the password
        sftp_password=bank_in.sftp_password,  # TODO: Encrypt this
    )

    db.add(bank_config)
    db.commit()
    db.refresh(bank_config)

    return BankConfigResponse.model_validate(bank_config)


@router.patch("/banks/{bank_code}", response_model=BankConfigResponse)
async def update_bank_configuration(
    *,
    db: Session = Depends(deps.get_db),
    bank_code: str,
    bank_in: BankConfigUpdate,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update a bank configuration.

    Requires: Admin role
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get bank configuration
    bank_config = db.query(BankConfiguration).filter_by(bank_code=bank_code).first()
    if not bank_config:
        raise HTTPException(status_code=404, detail=f"Bank {bank_code} not found")

    # Update fields
    update_data = bank_in.model_dump(exclude_unset=True)

    # Handle password separately (encrypt in production)
    if "sftp_password" in update_data and update_data["sftp_password"]:
        update_data["sftp_password"] = update_data[
            "sftp_password"
        ]  # TODO: Encrypt this

    for field, value in update_data.items():
        setattr(bank_config, field, value)

    bank_config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(bank_config)

    return BankConfigResponse.model_validate(bank_config)


@router.delete("/banks/{bank_code}")
async def delete_bank_configuration(
    *,
    db: Session = Depends(deps.get_db),
    bank_code: str,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Delete (deactivate) a bank configuration.

    Requires: Admin role
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get bank configuration
    bank_config = db.query(BankConfiguration).filter_by(bank_code=bank_code).first()
    if not bank_config:
        raise HTTPException(status_code=404, detail=f"Bank {bank_code} not found")

    # Soft delete by deactivating
    bank_config.is_active = False
    bank_config.updated_at = datetime.utcnow()

    db.commit()

    return {"message": f"Bank {bank_code} deactivated successfully"}
