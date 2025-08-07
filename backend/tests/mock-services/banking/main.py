"""
Mock Banking API Service for Testing
Simulates banking operations and payment processing
"""

import logging
import random
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock Banking Service", version="1.0.0")

# Store transactions and accounts for testing
accounts: Dict[str, dict] = {
    "1234567890": {
        "account_number": "1234567890",
        "account_name": "Lucky Gas Co., Ltd.",
        "balance": 1000000.00,
        "currency": "TWD",
        "status": "active",
    }
}

transactions: List[dict] = []
payment_orders: Dict[str, dict] = {}


class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    to_account_name: str
    to_bank_code: str
    amount: float
    currency: str = "TWD"
    purpose: str
    reference: Optional[str] = None


class PaymentOrderRequest(BaseModel):
    account_number: str
    total_amount: float
    payment_date: date
    payments: List[Dict[str, Any]]


class AccountBalanceResponse(BaseModel):
    account_number: str
    account_name: str
    balance: float
    available_balance: float
    currency: str
    as_of: str


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "mock - banking",
        "timestamp": datetime.now().isoformat(),
    }


@app.get(
    "/api / banking / account/{account_number}/balance",
    response_model=AccountBalanceResponse,
)
async def get_account_balance(
    account_number: str, authorization: Optional[str] = Header(None)
):
    """Get account balance"""
    logger.info(f"Balance inquiry for account: {account_number}")

    if account_number not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    account = accounts[account_number]

    return AccountBalanceResponse(
        account_number=account_number,
        account_name=account["account_name"],
        balance=account["balance"],
        available_balance=account["balance"] * 0.95,  # 95% available
        currency=account["currency"],
        as_of=datetime.now().isoformat(),
    )


@app.post("/api / banking / transfer")
async def create_transfer(
    request: TransferRequest, authorization: Optional[str] = Header(None)
):
    """Create a bank transfer"""
    logger.info(f"Transfer request from {request.from_account} to {request.to_account}")

    # Validate source account
    if request.from_account not in accounts:
        raise HTTPException(status_code=404, detail="Source account not found")

    source_account = accounts[request.from_account]

    # Check balance
    if source_account["balance"] < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Simulate random failures (2% failure rate)
    if random.random() < 0.02:
        raise HTTPException(
            status_code=500, detail="Banking system temporarily unavailable"
        )

    # Create transaction
    transaction_id = f"TXN{uuid.uuid4().hex[:12].upper()}"

    transaction = {
        "transaction_id": transaction_id,
        "type": "transfer",
        "from_account": request.from_account,
        "to_account": request.to_account,
        "to_account_name": request.to_account_name,
        "to_bank_code": request.to_bank_code,
        "amount": request.amount,
        "currency": request.currency,
        "purpose": request.purpose,
        "reference": request.reference,
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "fee": 15.0,  # Mock transfer fee
    }

    # Update balance
    source_account["balance"] -= request.amount + transaction["fee"]

    # Store transaction
    transactions.append(transaction)

    logger.info(f"Transfer completed: {transaction_id}")

    return {
        "transaction_id": transaction_id,
        "status": "completed",
        "amount": request.amount,
        "fee": transaction["fee"],
        "total_debit": request.amount + transaction["fee"],
        "reference": request.reference,
        "timestamp": transaction["created_at"],
    }


@app.get("/api / banking / account/{account_number}/transactions")
async def get_account_transactions(
    account_number: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
):
    """Get account transaction history"""
    logger.info(f"Transaction history request for account: {account_number}")

    if account_number not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    # Filter transactions
    account_txns = [
        txn
        for txn in transactions
        if txn.get("from_account") == account_number
        or txn.get("to_account") == account_number
    ]

    # Apply date filters
    if start_date:
        account_txns = [
            txn
            for txn in account_txns
            if datetime.fromisoformat(txn["created_at"]).date() >= start_date
        ]

    if end_date:
        account_txns = [
            txn
            for txn in account_txns
            if datetime.fromisoformat(txn["created_at"]).date() <= end_date
        ]

    # Sort by date descending
    account_txns.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "account_number": account_number,
        "total": len(account_txns),
        "transactions": account_txns[:limit],
    }


@app.post("/api / banking / payment - order")
async def create_payment_order(request: PaymentOrderRequest):
    """Create batch payment order (ACH)"""
    logger.info(f"Payment order request with {len(request.payments)} payments")

    # Validate account
    if request.account_number not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    account = accounts[request.account_number]

    # Check total balance
    if account["balance"] < request.total_amount:
        raise HTTPException(
            status_code=400, detail="Insufficient balance for payment order"
        )

    # Create payment order
    order_id = (
        f"PMT{datetime.now().strftime('%Y % m % d')}{uuid.uuid4().hex[:6].upper()}"
    )

    payment_order = {
        "order_id": order_id,
        "account_number": request.account_number,
        "payment_date": request.payment_date.isoformat(),
        "total_amount": request.total_amount,
        "total_count": len(request.payments),
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "payments": [],
    }

    # Process individual payments
    for payment in request.payments:
        payment_record = {
            "payment_id": f"P{uuid.uuid4().hex[:8].upper()}",
            "account_number": payment["account_number"],
            "account_name": payment["account_name"],
            "bank_code": payment["bank_code"],
            "amount": payment["amount"],
            "reference": payment.get("reference", ""),
            "status": "pending",
        }
        payment_order["payments"].append(payment_record)

    # Store payment order
    payment_orders[order_id] = payment_order

    # Deduct from balance (held amount)
    account["balance"] -= request.total_amount

    logger.info(f"Payment order created: {order_id}")

    return {
        "order_id": order_id,
        "status": "processing",
        "total_amount": request.total_amount,
        "payment_count": len(request.payments),
        "estimated_completion": (datetime.now() + timedelta(days=1)).isoformat(),
    }


@app.get("/api / banking / payment - order/{order_id}")
async def get_payment_order_status(order_id: str):
    """Get payment order status"""
    logger.info(f"Payment order status request: {order_id}")

    if order_id not in payment_orders:
        raise HTTPException(status_code=404, detail="Payment order not found")

    order = payment_orders[order_id]

    # Simulate processing progress
    created_time = datetime.fromisoformat(order["created_at"])
    time_diff = (datetime.now() - created_time).seconds

    if time_diff > 300:  # After 5 minutes, mark as completed
        order["status"] = "completed"
        order["completed_at"] = datetime.now().isoformat()

        # Update payment statuses
        for payment in order["payments"]:
            payment["status"] = "completed" if random.random() > 0.05 else "failed"

    # Calculate summary
    completed_count = sum(1 for p in order["payments"] if p["status"] == "completed")
    failed_count = sum(1 for p in order["payments"] if p["status"] == "failed")
    completed_amount = sum(
        p["amount"] for p in order["payments"] if p["status"] == "completed"
    )

    return {
        "order_id": order_id,
        "status": order["status"],
        "total_amount": order["total_amount"],
        "total_count": order["total_count"],
        "completed_count": completed_count,
        "failed_count": failed_count,
        "completed_amount": completed_amount,
        "created_at": order["created_at"],
        "completed_at": order.get("completed_at"),
        "payments": order["payments"],
    }


@app.post("/api / banking / validate - account")
async def validate_bank_account(
    account_number: str, bank_code: str, account_name: Optional[str] = None
):
    """Validate bank account details"""
    logger.info(f"Account validation request: {bank_code}-{account_number}")

    # Simulate validation
    is_valid = len(account_number) >= 10 and len(bank_code) == 3

    # Random validation for testing
    if random.random() < 0.1:
        is_valid = False

    response = {
        "account_number": account_number,
        "bank_code": bank_code,
        "is_valid": is_valid,
        "bank_name": f"Test Bank {bank_code}",
        "branch_name": "Test Branch",
    }

    if account_name:
        # Simulate name matching
        response["name_match"] = random.choice([True, False])
        response["registered_name"] = f"Test Company {account_number[:4]}"

    return response


@app.get("/api / banking / exchange - rates")
async def get_exchange_rates(base_currency: str = "TWD"):
    """Get current exchange rates"""
    logger.info(f"Exchange rate request for base currency: {base_currency}")

    rates = {
        "TWD": 1.0,
        "USD": 0.032 + random.uniform(-0.001, 0.001),
        "EUR": 0.029 + random.uniform(-0.001, 0.001),
        "JPY": 4.67 + random.uniform(-0.05, 0.05),
        "CNY": 0.22 + random.uniform(-0.005, 0.005),
        "HKD": 0.25 + random.uniform(-0.005, 0.005),
    }

    return {
        "base_currency": base_currency,
        "rates": rates,
        "last_updated": datetime.now().isoformat(),
    }


@app.post("/api / banking / statement / download")
async def download_statement(
    account_number: str, start_date: date, end_date: date, format: str = "pd"
):
    """Generate account statement"""
    logger.info(f"Statement download request for account: {account_number}")

    if account_number not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    # Simulate statement generation
    statement_id = f"STMT{uuid.uuid4().hex[:8].upper()}"

    return {
        "statement_id": statement_id,
        "account_number": account_number,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "format": format,
        "download_url": f"/api / banking / statement/{statement_id}/download",
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
    }


@app.delete("/api / banking / clear")
async def clear_banking_data():
    """Clear all banking data (for testing)"""
    # Reset to initial state
    accounts.clear()
    accounts["1234567890"] = {
        "account_number": "1234567890",
        "account_name": "Lucky Gas Co., Ltd.",
        "balance": 1000000.00,
        "currency": "TWD",
        "status": "active",
    }
    transactions.clear()
    payment_orders.clear()

    return {"message": "All banking data cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
