"""
Taiwan E - Invoice Pydantic schemas for API validation
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class InvoiceData(BaseModel):
    """Schema for Taiwan e - invoice data validation"""

    # Basic Information
    MerchantID: str = Field(..., description="Merchant ID")
    InvoiceNo: str = Field(
        ..., regex=r"^[A - Z]{2}\d{8}$", description="Invoice number (e.g., AB12345678)"
    )
    InvoiceDate: str = Field(
        ..., regex=r"^\d{4}/\d{2}/\d{2}$", description="Invoice date (YYYY / MM / DD)"
    )
    InvoiceTime: str = Field(
        ..., regex=r"^\d{2}:\d{2}:\d{2}$", description="Invoice time (HH:MM:SS)"
    )
    RandomNumber: str = Field(
        ..., regex=r"^\d{4}$", description="4 - digit random code"
    )

    # Amounts (integers only for e - invoice API)
    SalesAmount: int = Field(..., ge=0, description="Sales amount before tax")
    TaxType: Literal["1", "2", "3", "4", "9"] = Field(..., description="Tax type code")
    TaxRate: float = Field(..., ge=0, le=1, description="Tax rate (0 - 1)")
    TaxAmount: int = Field(..., ge=0, description="Tax amount")
    TotalAmount: int = Field(..., ge=0, description="Total amount including tax")

    # Invoice Type and Marks
    InvoiceType: str = Field(..., regex=r"^\d{2}$", description="Invoice type code")
    PrintMark: Literal["Y", "N"] = Field(..., description="Print mark (Y / N)")
    DonateMark: Literal["0", "1"] = Field(..., description="Donate mark (0 / 1)")

    # Carrier Information
    CarrierType: str = Field("", description="Carrier type code")
    CarrierId1: str = Field("", description="Carrier ID 1")
    CarrierId2: str = Field("", description="Carrier ID 2")

    # Tax ID
    TaxID: str = Field("", description="Tax ID")

    # Buyer Information
    BuyerId: Optional[str] = Field(
        None, regex=r"^\d{8}$", description="Buyer tax ID (8 digits)"
    )
    BuyerName: str = Field("", description="Buyer name")
    BuyerAddress: str = Field("", description="Buyer address")
    BuyerEmail: str = Field("", description="Buyer email")
    BuyerPhone: str = Field("", description="Buyer phone")

    # Seller Information
    SellerId: str = Field(..., regex=r"^\d{8}$", description="Seller tax ID (8 digits)")
    SellerName: str = Field(..., description="Seller name")
    SellerAddress: str = Field("", description="Seller address")
    SellerPhone: str = Field("", description="Seller phone")
    SellerEmail: str = Field("", description="Seller email")

    # Items
    ItemCount: str = Field(..., description="Number of items")
    ItemWord: str = Field("式", description="Item unit word")
    ItemDescription: List[str] = Field(
        ..., min_length=1, description="Item descriptions"
    )
    ItemQuantity: List[str] = Field(..., min_length=1, description="Item quantities")
    ItemUnit: List[str] = Field(..., min_length=1, description="Item units")
    ItemUnitPrice: List[str] = Field(..., min_length=1, description="Item unit prices")
    ItemAmount: List[str] = Field(..., min_length=1, description="Item amounts")
    ItemTaxType: List[str] = Field(..., min_length=1, description="Item tax types")

    # System fields
    TimeStamp: str = Field(..., description="Unix timestamp")
    CheckMacValue: str = Field(..., description="HMAC signature")

    @field_validator("PrintMark")
    def validate_print_mark(cls, v):
        """Ensure PrintMark is Y or N only"""
        if v not in ["Y", "N"]:
            raise ValueError(f"PrintMark must be 'Y' or 'N', got '{v}'")
        return v

    @field_validator("DonateMark")
    def validate_donate_mark(cls, v):
        """Ensure DonateMark is 0 or 1 only"""
        if v not in ["0", "1"]:
            raise ValueError(f"DonateMark must be '0' or '1', got '{v}'")
        return v

    @field_validator(
        "ItemCount",
        "ItemDescription",
        "ItemQuantity",
        "ItemUnit",
        "ItemUnitPrice",
        "ItemAmount",
        "ItemTaxType",
    )
    def validate_item_arrays(cls, v, values):
        """Ensure all item arrays have the same length"""
        if "ItemCount" in values:
            expected_count = int(values["ItemCount"])
            if isinstance(v, list) and len(v) != expected_count:
                raise ValueError(f"Expected {expected_count} items but got {len(v)}")
        return v


class InvoiceResponse(BaseModel):
    """Response from e - invoice API"""

    RtnCode: str = Field(..., description="Return code (1=success)")
    RtnMsg: str = Field(..., description="Return message")
    InvoiceNo: Optional[str] = Field(None, description="Invoice number")
    InvoiceDate: Optional[str] = Field(None, description="Invoice date")
    RandomNumber: Optional[str] = Field(None, description="Random number")
    QRCode_Left: Optional[str] = Field(None, description="QR code left part")
    QRCode_Right: Optional[str] = Field(None, description="QR code right part")
    BarCode: Optional[str] = Field(None, description="Bar code")


class InvoiceSubmitRequest(BaseModel):
    """Request to submit an invoice"""

    invoice_id: int = Field(..., description="Internal invoice ID")


class InvoiceSubmitResponse(BaseModel):
    """Response after submitting invoice"""

    status: Literal["success", "error"] = Field(..., description="Submission status")
    einvoice_id: Optional[str] = Field(
        None, description="E - invoice ID from government"
    )
    message: str = Field(..., description="Status message")
    qr_code_left: Optional[str] = Field(None, description="QR code left part")
    qr_code_right: Optional[str] = Field(None, description="QR code right part")
    bar_code: Optional[str] = Field(None, description="Bar code")
    response_time: datetime = Field(..., description="Response timestamp")
    api_response: Optional[dict] = Field(None, description="Raw API response")


class InvoiceVoidRequest(BaseModel):
    """Request to void an invoice"""

    invoice_number: str = Field(
        ..., regex=r"^[A - Z]{2}\d{8}$", description="Invoice number to void"
    )
    reason: str = Field(..., max_length=200, description="Void reason")


class InvoiceAllowanceRequest(BaseModel):
    """Request to issue allowance"""

    original_invoice_number: str = Field(
        ..., regex=r"^[A - Z]{2}\d{8}$", description="Original invoice number"
    )
    allowance_amount: float = Field(
        ..., gt=0, description="Allowance amount before tax"
    )
    tax_amount: float = Field(..., ge=0, description="Tax amount")
    reason: str = Field(..., max_length=200, description="Allowance reason")
    items: Optional[List[dict]] = Field(None, description="Allowance items")
