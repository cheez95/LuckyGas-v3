"""
Financial reporting API endpoints
"""
from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.api.deps import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.financial_report_service import FinancialReportService

router = APIRouter(prefix="/financial-reports", tags=["financial-reports"])


@router.get("/revenue-summary")
async def get_revenue_summary(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get revenue summary for a period"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看財務報表")
    
    service = FinancialReportService(db)
    summary = await service.get_revenue_summary(period)
    
    return summary


@router.get("/accounts-receivable")
async def get_accounts_receivable_report(
    as_of_date: date = Query(default=date.today()),
    customer_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get accounts receivable aging report"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限查看應收帳款報表")
    
    service = FinancialReportService(db)
    report = await service.get_accounts_receivable_report(
        as_of_date=as_of_date,
        customer_id=customer_id
    )
    
    return report


@router.get("/tax-report")
async def get_tax_report(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tax report for government filing"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看稅務報表")
    
    service = FinancialReportService(db)
    report = await service.get_tax_report(period)
    
    return report


@router.get("/cash-flow")
async def get_cash_flow_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get cash flow report"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看現金流量報表")
    
    service = FinancialReportService(db)
    report = await service.get_cash_flow_report(
        date_from=date_from,
        date_to=date_to
    )
    
    return report


@router.get("/profit-loss")
async def get_profit_loss_statement(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get profit and loss statement"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看損益表")
    
    service = FinancialReportService(db)
    statement = await service.get_profit_loss_statement(period)
    
    return statement


@router.get("/customer-statement")
async def get_customer_statement(
    customer_id: int,
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer account statement"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限查看客戶對帳單")
    
    service = FinancialReportService(db)
    statement = await service.get_customer_statement(
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to
    )
    
    return statement


@router.get("/sales-analysis")
async def get_sales_analysis(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    group_by: str = Query("customer", pattern="^(customer|product|area|date)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get sales analysis report"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限查看銷售分析")
    
    service = FinancialReportService(db)
    analysis = await service.get_sales_analysis(
        period=period,
        group_by=group_by
    )
    
    return analysis


@router.get("/compliance-report")
async def get_compliance_report(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get compliance report for regulatory requirements"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看合規報表")
    
    service = FinancialReportService(db)
    report = await service.get_compliance_report(period)
    
    return report


@router.post("/generate-401")
async def generate_401_file(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate 401 file for government tax filing"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限產生401申報檔")
    
    service = FinancialReportService(db)
    file_content = await service.generate_401_file(period)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(file_content.encode('utf-8')),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=401_{period}.txt"
        }
    )


@router.post("/generate-403")
async def generate_403_file(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate 403 file for government tax filing"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限產生403申報檔")
    
    service = FinancialReportService(db)
    file_content = await service.generate_403_file(period)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(file_content.encode('utf-8')),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=403_{period}.txt"
        }
    )


@router.get("/dashboard-metrics")
async def get_financial_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get financial metrics for dashboard"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限查看財務指標")
    
    service = FinancialReportService(db)
    metrics = await service.get_dashboard_metrics()
    
    return metrics


@router.post("/export-to-accounting")
async def export_to_accounting_system(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    system: str = Query(..., pattern="^(excel|csv|quickbooks|sap)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export financial data to accounting system"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限匯出會計資料")
    
    service = FinancialReportService(db)
    
    if system == "excel":
        file_content = await service.export_to_excel(period)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"financial_export_{period}.xlsx"
    elif system == "csv":
        file_content = await service.export_to_csv(period)
        media_type = "text/csv"
        filename = f"financial_export_{period}.csv"
    else:
        # For QuickBooks or SAP, would implement specific formats
        raise HTTPException(status_code=501, detail="此匯出格式尚未實作")
    
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )