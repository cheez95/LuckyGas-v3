"""
Credit-related schemas for API responses
"""

from typing import Optional
from pydantic import BaseModel, Field


class CreditCheckResult(BaseModel):
    """Result of credit limit check"""

    approved: bool = Field(..., description="是否通過信用額度檢查")
    reason: str = Field(..., description="檢查結果原因")
    credit_limit: float = Field(..., description="信用額度")
    current_balance: float = Field(..., description="當前應收帳款")
    available_credit: float = Field(..., description="可用信用額度")
    requested_amount: Optional[float] = Field(None, description="請求金額")
    exceeds_by: Optional[float] = Field(None, description="超出額度金額")
    is_blocked: bool = Field(default=False, description="信用是否被封鎖")

    model_config = {
        "json_schema_extra": {
            "example": {
                "approved": True,
                "reason": "Within credit limit",
                "credit_limit": 100000.0,
                "current_balance": 25000.0,
                "available_credit": 75000.0,
                "requested_amount": 5000.0,
                "exceeds_by": None,
                "is_blocked": False,
            }
        }
    }


class CreditSummary(BaseModel):
    """Customer credit summary"""

    customer_id: int = Field(..., description="客戶ID")
    customer_name: str = Field(..., description="客戶名稱")
    credit_limit: float = Field(..., description="信用額度")
    current_balance: float = Field(..., description="當前應收帳款")
    available_credit: float = Field(..., description="可用信用額度")
    overdue_amount: float = Field(..., description="逾期金額")
    is_credit_blocked: bool = Field(..., description="信用是否被封鎖")
    credit_utilization: float = Field(..., description="信用額度使用率(%)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": 1,
                "customer_name": "測試客戶",
                "credit_limit": 100000.0,
                "current_balance": 25000.0,
                "available_credit": 75000.0,
                "overdue_amount": 5000.0,
                "is_credit_blocked": False,
                "credit_utilization": 25.0,
            }
        }
    }


class CreditBlockRequest(BaseModel):
    """Request to block/unblock customer credit"""

    reason: str = Field(..., description="封鎖/解除封鎖原因")

    model_config = {"json_schema_extra": {"example": {"reason": "逾期款項超過30天"}}}
