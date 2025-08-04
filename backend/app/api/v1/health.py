"""Health check and monitoring endpoints for production APIs."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.core.api_monitoring import api_monitor
from app.core.cache import cache
from app.models.user import User
from app.services.banking_service import BankingService
from app.services.einvoice_service import get_einvoice_service
from app.services.sms_service import enhanced_sms_service

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LuckyGas Backend",
        "version": "1.0.0",
    }


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint.
    Checks database and Redis connectivity.
    """
    checks = {"database": False, "redis": False}
    errors = {}

    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = True
    except Exception as e:
        errors["database"] = str(e)

    # Check Redis connectivity
    try:
        if cache._connected:
            await cache.redis.ping()
            checks["redis"] = True
        else:
            # Try to connect if not already connected
            await cache.connect()
            if cache._connected:
                checks["redis"] = True
            else:
                errors["redis"] = "Redis connection not established"
    except Exception as e:
        errors["redis"] = str(e)

    # Determine overall readiness
    is_ready = all(checks.values())

    response = {
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }

    if errors:
        response["errors"] = errors

    # Return 503 Service Unavailable if not ready
    if not is_ready:
        raise HTTPException(status_code=503, detail=response)

    return response


@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Detailed health check for all integrated services.
    Requires superuser authentication.
    """
    health_status = {
        "status": "checking",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
    }

    # Check E-Invoice service
    try:
        einvoice_service = get_einvoice_service()
        einvoice_health = await einvoice_service.health_check()
        health_status["services"]["einvoice"] = einvoice_health
    except Exception as e:
        health_status["services"]["einvoice"] = {"status": "error", "error": str(e)}

    # Check Banking services
    banking_banks = ["mega", "ctbc", "esun", "first", "taishin"]
    for bank in banking_banks:
        try:
            # Get circuit breaker state from monitoring
            cb_state = api_monitor.circuit_breakers.get(f"banking_{bank}")
            if cb_state:
                health_status["services"][f"banking_{bank}"] = {
                    "status": (
                        "healthy"
                        if cb_state.state.state.value == "closed"
                        else "unhealthy"
                    ),
                    "circuit_breaker": cb_state.get_state(),
                }
            else:
                health_status["services"][f"banking_{bank}"] = {
                    "status": "unknown",
                    "error": "Circuit breaker not initialized",
                }
        except Exception as e:
            health_status["services"][f"banking_{bank}"] = {
                "status": "error",
                "error": str(e),
            }

    # Check SMS providers
    sms_providers = ["twilio", "every8d", "mitake"]
    for provider in sms_providers:
        try:
            cb_state = api_monitor.circuit_breakers.get(f"sms_{provider}")
            if cb_state:
                health_status["services"][f"sms_{provider}"] = {
                    "status": (
                        "healthy"
                        if cb_state.state.state.value == "closed"
                        else "unhealthy"
                    ),
                    "circuit_breaker": cb_state.get_state(),
                }
            else:
                health_status["services"][f"sms_{provider}"] = {
                    "status": "unknown",
                    "error": "Circuit breaker not initialized",
                }
        except Exception as e:
            health_status["services"][f"sms_{provider}"] = {
                "status": "error",
                "error": str(e),
            }

    # Determine overall status
    all_healthy = all(
        service.get("status") == "healthy"
        for service in health_status["services"].values()
    )
    health_status["status"] = "healthy" if all_healthy else "degraded"

    return health_status


@router.get("/circuit-breakers", response_model=Dict[str, Any])
async def get_circuit_breakers(
    current_user: User = Depends(get_current_active_superuser),
):
    """Get circuit breaker states for all services."""
    return api_monitor.get_circuit_breaker_states()


@router.get("/metrics", response_model=Dict[str, Any])
async def get_api_metrics(current_user: User = Depends(get_current_active_superuser)):
    """Get API monitoring metrics dashboard."""
    return api_monitor.get_dashboard_data()


@router.post("/circuit-breakers/{service_name}/reset")
async def reset_circuit_breaker(
    service_name: str, current_user: User = Depends(get_current_active_superuser)
):
    """Manually reset a circuit breaker."""
    cb = api_monitor.circuit_breakers.get(service_name)
    if not cb:
        raise HTTPException(
            status_code=404, detail=f"Circuit breaker {service_name} not found"
        )

    # Force reset by transitioning to closed state
    await cb._transition_state(cb.state.CircuitState.CLOSED)
    cb.state.failure_count = 0
    cb.state.consecutive_successes = 0

    return {
        "message": f"Circuit breaker {service_name} reset successfully",
        "state": cb.get_state(),
    }


@router.post("/test/{service_type}")
async def test_service_integration(
    service_type: str,
    current_user: User = Depends(get_current_active_superuser),
    db=Depends(get_db),
):
    """
    Test specific service integration.

    Service types:
    - einvoice: Test E-Invoice API connection
    - banking_{bank}: Test banking SFTP connection
    - sms_{provider}: Test SMS provider connection
    """

    if service_type == "einvoice":
        try:
            service = get_einvoice_service()
            # Create a test invoice (in mock mode)
            from app.models.invoice import Invoice, InvoiceType

            test_invoice = Invoice(
                invoice_number="TEST00000001",
                invoice_type=InvoiceType.B2C,
                buyer_name="測試客戶",
                total_amount=1000,
                invoice_date=datetime.utcnow(),
            )
            result = await service._mock_submit_invoice(test_invoice)
            return {"service": "einvoice", "status": "success", "result": result}
        except Exception as e:
            return {"service": "einvoice", "status": "error", "error": str(e)}

    elif service_type.startswith("banking_"):
        bank_code = service_type.replace("banking_", "")
        try:
            from app.models.banking import BankConfiguration

            bank_config = (
                db.query(BankConfiguration)
                .filter_by(bank_code=bank_code, is_active=True)
                .first()
            )

            if not bank_config:
                return {
                    "service": service_type,
                    "status": "error",
                    "error": f"Bank configuration for {bank_code} not found",
                }

            banking_service = BankingService(db)
            with banking_service.get_sftp_client(bank_config) as sftp:
                # Test connection by listing root directory
                files = sftp.listdir(".")
                return {
                    "service": service_type,
                    "status": "success",
                    "message": f"Connected successfully, found {len(files)} items in root directory",
                }
        except Exception as e:
            return {"service": service_type, "status": "error", "error": str(e)}

    elif service_type.startswith("sms_"):
        provider_name = service_type.replace("sms_", "")
        try:
            # Send test SMS to monitoring number
            result = await enhanced_sms_service.send_sms(
                phone="0900000000",  # Test number
                message="LuckyGas API test message",
                message_type="test",
                retry_on_failure=False,
                db=db,
            )
            return {
                "service": service_type,
                "status": "success" if result["success"] else "error",
                "result": result,
            }
        except Exception as e:
            return {"service": service_type, "status": "error", "error": str(e)}

    else:
        raise HTTPException(
            status_code=400, detail=f"Unknown service type: {service_type}"
        )
