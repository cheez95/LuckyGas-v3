"""
Mock E-Invoice Service for Testing
Simulates Taiwan E-Invoice API functionality
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date
import uuid
import random
import string
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock E-Invoice Service", version="1.0.0")

# Store invoices for testing
invoices: Dict[str, dict] = {}


class InvoiceItem(BaseModel):
    description: str
    quantity: int
    unit_price: float
    amount: float
    tax_type: str = "1"  # 1: Taxable, 2: Zero-rated, 3: Tax-exempt


class InvoiceRequest(BaseModel):
    buyer_id: Optional[str] = None  # Unified Business Number
    buyer_name: str
    buyer_address: Optional[str] = None
    buyer_email: Optional[str] = None
    buyer_mobile: Optional[str] = None
    carrier_type: Optional[str] = None  # 3J0002: Mobile, CQ0001: Natural person
    carrier_id: Optional[str] = None  # Carrier barcode
    items: List[InvoiceItem]
    total_amount: float
    tax_amount: float
    sales_amount: float
    invoice_type: str = "07"  # 07: B2C, 08: B2B
    print_mark: str = "Y"
    donate_mark: str = "0"  # 0: No donation, 1: Donation
    love_code: Optional[str] = None


class InvoiceResponse(BaseModel):
    invoice_number: str
    invoice_date: str
    invoice_time: str
    random_number: str
    sales_amount: float
    tax_amount: float
    total_amount: float
    qr_code_left: str
    qr_code_right: str
    bar_code: str
    status: str


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "mock-einvoice",
        "timestamp": datetime.now().isoformat(),
    }


def generate_invoice_number() -> str:
    """Generate Taiwan format invoice number (XX12345678)"""
    letters = "".join(random.choices(string.ascii_uppercase, k=2))
    numbers = "".join(random.choices(string.digits, k=8))
    return f"{letters}{numbers}"


def generate_random_number() -> str:
    """Generate 4-digit random number for invoice"""
    return "".join(random.choices(string.digits, k=4))


def generate_qr_code(
    invoice_number: str, date: str, random_num: str, amount: float
) -> tuple:
    """Generate mock QR codes for invoice"""
    # Left QR code contains basic info
    left = f"{invoice_number}{date}{random_num}{int(amount):08d}"

    # Right QR code contains detailed info
    right = f"**{invoice_number}{date}{random_num}:{int(amount)}"

    return left, right


def generate_bar_code(invoice_number: str, date: str) -> str:
    """Generate mock bar code for invoice"""
    # Format: Period(5) + Invoice number(10) + Random(4)
    period = date[:5].replace("-", "")  # YMMDD format for Taiwan
    return f"{period}{invoice_number}{generate_random_number()}"


@app.post("/api/einvoice/issue", response_model=InvoiceResponse)
async def issue_invoice(
    request: InvoiceRequest, authorization: Optional[str] = Header(None)
):
    """Issue a new e-invoice"""
    logger.info(f"E-Invoice issue request for buyer: {request.buyer_name}")

    # Validate items total matches
    calculated_total = sum(item.amount for item in request.items)
    if abs(calculated_total - request.sales_amount) > 0.01:
        raise HTTPException(
            status_code=400, detail="Items total does not match sales amount"
        )

    # Generate invoice details
    invoice_number = generate_invoice_number()
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    invoice_time = datetime.now().strftime("%H:%M:%S")
    random_number = generate_random_number()

    # Generate codes
    qr_left, qr_right = generate_qr_code(
        invoice_number,
        invoice_date.replace("-", ""),
        random_number,
        request.total_amount,
    )
    bar_code = generate_bar_code(invoice_number, invoice_date)

    # Create response
    response = InvoiceResponse(
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_time=invoice_time,
        random_number=random_number,
        sales_amount=request.sales_amount,
        tax_amount=request.tax_amount,
        total_amount=request.total_amount,
        qr_code_left=qr_left,
        qr_code_right=qr_right,
        bar_code=bar_code,
        status="issued",
    )

    # Store invoice
    invoices[invoice_number] = {
        **response.dict(),
        "buyer_info": {
            "buyer_id": request.buyer_id,
            "buyer_name": request.buyer_name,
            "buyer_address": request.buyer_address,
            "buyer_email": request.buyer_email,
            "buyer_mobile": request.buyer_mobile,
        },
        "items": [item.dict() for item in request.items],
        "carrier_info": {
            "carrier_type": request.carrier_type,
            "carrier_id": request.carrier_id,
        },
        "print_mark": request.print_mark,
        "donate_mark": request.donate_mark,
        "love_code": request.love_code,
    }

    logger.info(f"E-Invoice issued successfully: {invoice_number}")

    return response


@app.get("/api/einvoice/{invoice_number}")
async def get_invoice(invoice_number: str):
    """Get invoice details"""
    logger.info(f"Get invoice request: {invoice_number}")

    if invoice_number not in invoices:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoices[invoice_number]


@app.post("/api/einvoice/{invoice_number}/void")
async def void_invoice(invoice_number: str, reason: str = "Customer request"):
    """Void an issued invoice"""
    logger.info(f"Void invoice request: {invoice_number}")

    if invoice_number not in invoices:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = invoices[invoice_number]

    if invoice["status"] == "voided":
        raise HTTPException(status_code=400, detail="Invoice already voided")

    # Update status
    invoice["status"] = "voided"
    invoice["void_date"] = datetime.now().isoformat()
    invoice["void_reason"] = reason

    return {
        "invoice_number": invoice_number,
        "status": "voided",
        "void_date": invoice["void_date"],
        "void_reason": reason,
    }


@app.post("/api/einvoice/{invoice_number}/allowance")
async def create_allowance(
    invoice_number: str,
    allowance_amount: float,
    allowance_tax: float,
    reason: str = "Price adjustment",
):
    """Create allowance for invoice"""
    logger.info(f"Create allowance for invoice: {invoice_number}")

    if invoice_number not in invoices:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = invoices[invoice_number]

    # Generate allowance number
    allowance_number = f"A{generate_random_number()}{generate_random_number()}"

    # Store allowance
    if "allowances" not in invoice:
        invoice["allowances"] = []

    allowance = {
        "allowance_number": allowance_number,
        "allowance_date": datetime.now().isoformat(),
        "allowance_amount": allowance_amount,
        "allowance_tax": allowance_tax,
        "total_allowance": allowance_amount + allowance_tax,
        "reason": reason,
    }

    invoice["allowances"].append(allowance)

    return allowance


@app.get("/api/einvoice/query")
async def query_invoices(
    start_date: date,
    end_date: date,
    status: Optional[str] = None,
    buyer_id: Optional[str] = None,
):
    """Query invoices by criteria"""
    logger.info(f"Query invoices from {start_date} to {end_date}")

    results = []

    for invoice_num, invoice in invoices.items():
        invoice_date = datetime.fromisoformat(invoice["invoice_date"]).date()

        # Apply filters
        if invoice_date < start_date or invoice_date > end_date:
            continue

        if status and invoice["status"] != status:
            continue

        if buyer_id and invoice["buyer_info"]["buyer_id"] != buyer_id:
            continue

        results.append(
            {
                "invoice_number": invoice_num,
                "invoice_date": invoice["invoice_date"],
                "buyer_name": invoice["buyer_info"]["buyer_name"],
                "total_amount": invoice["total_amount"],
                "status": invoice["status"],
            }
        )

    return {"total": len(results), "invoices": results}


@app.post("/api/einvoice/batch")
async def batch_issue_invoices(invoices_data: List[InvoiceRequest]):
    """Issue multiple invoices in batch"""
    logger.info(f"Batch invoice request for {len(invoices_data)} invoices")

    results = []

    for invoice_req in invoices_data:
        try:
            result = await issue_invoice(invoice_req)
            results.append(
                {
                    "success": True,
                    "invoice_number": result.invoice_number,
                    "buyer_name": invoice_req.buyer_name,
                }
            )
        except Exception as e:
            results.append(
                {
                    "success": False,
                    "buyer_name": invoice_req.buyer_name,
                    "error": str(e),
                }
            )

    return {
        "total": len(invoices_data),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results,
    }


@app.get("/api/einvoice/winning")
async def check_winning_numbers(period: str, invoice_number: str):  # Format: YYYYMM
    """Check if invoice won lottery"""
    logger.info(f"Check winning for invoice: {invoice_number} in period {period}")

    # Mock winning check (0.1% chance)
    is_winner = random.random() < 0.001

    if is_winner:
        prizes = [
            {"prize": "特別獎", "amount": 10000000},
            {"prize": "特獎", "amount": 2000000},
            {"prize": "頭獎", "amount": 200000},
            {"prize": "二獎", "amount": 40000},
            {"prize": "三獎", "amount": 10000},
            {"prize": "四獎", "amount": 4000},
            {"prize": "五獎", "amount": 1000},
            {"prize": "六獎", "amount": 200},
        ]
        prize = random.choice(prizes)

        return {
            "is_winner": True,
            "invoice_number": invoice_number,
            "period": period,
            "prize_name": prize["prize"],
            "prize_amount": prize["amount"],
        }

    return {"is_winner": False, "invoice_number": invoice_number, "period": period}


@app.delete("/api/einvoice/clear")
async def clear_invoices():
    """Clear all invoices (for testing)"""
    invoices.clear()
    return {"message": "All invoices cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
