"""
Taiwan Government E-Invoice API Service
"""
import httpx
import json
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import hmac
import base64
from app.core.config import settings
from app.models import Invoice


class EInvoiceService:
    """
    Service for integrating with Taiwan Ministry of Finance E-Invoice platform
    
    This implements the B2B Turnkey API for business invoice management
    """
    
    def __init__(self):
        # In production, these would come from environment variables
        self.api_key = settings.EINVOICE_API_KEY if hasattr(settings, 'EINVOICE_API_KEY') else "test_api_key"
        self.app_id = settings.EINVOICE_APP_ID if hasattr(settings, 'EINVOICE_APP_ID') else "test_app_id"
        
        # API endpoints (test environment)
        self.base_url = "https://www-vc.einvoice.nat.gov.tw/BIZAPIVAN/biz" if settings.ENVIRONMENT == "production" else "https://wwwtest.einvoice.nat.gov.tw/BIZAPIVAN/biz"
        
        self.endpoints = {
            "issue": "/InvoiceIssue",
            "void": "/InvoiceVoid",
            "allowance": "/AllowanceIssue",
            "query": "/InvoiceSearch",
            "print": "/InvoicePrint"
        }
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate HMAC signature for API authentication"""
        # Sort parameters alphabetically
        sorted_params = sorted(data.items())
        param_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        
        # Generate HMAC-SHA256
        signature = hmac.new(
            self.api_key.encode('utf-8'),
            param_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Base64 encode
        return base64.b64encode(signature).decode('utf-8')
    
    def _prepare_invoice_data(self, invoice: Invoice) -> Dict[str, Any]:
        """Prepare invoice data for API submission"""
        # Convert invoice to API format
        data = {
            "MerchantID": self.app_id,
            "InvoiceNumber": invoice.invoice_number,
            "InvoiceDate": invoice.invoice_date.strftime("%Y/%m/%d"),
            "InvoiceTime": datetime.now().strftime("%H:%M:%S"),
            "RandomNumber": invoice.random_code,
            "SalesAmount": int(invoice.sales_amount),
            "TaxType": invoice.tax_type,
            "TaxRate": invoice.tax_rate,
            "TaxAmount": int(invoice.tax_amount),
            "TotalAmount": int(invoice.total_amount),
            "InvoiceType": "07",  # 一般稅額計算
            "PrintMark": "Y" if invoice.is_printed else "N",
            "DonateMark": "0",  # 不捐贈
            
            # Buyer information
            "BuyerIdentifier": invoice.buyer_tax_id or "",
            "BuyerName": invoice.buyer_name,
            "BuyerAddress": invoice.buyer_address or "",
            
            # Seller information (from settings)
            "SellerIdentifier": settings.COMPANY_TAX_ID if hasattr(settings, 'COMPANY_TAX_ID') else "12345678",
            "SellerName": settings.COMPANY_NAME if hasattr(settings, 'COMPANY_NAME') else "幸福氣股份有限公司",
            "SellerAddress": settings.COMPANY_ADDRESS if hasattr(settings, 'COMPANY_ADDRESS') else "台北市信義區信義路五段7號",
            
            # Items
            "Items": []
        }
        
        # Add items
        for item in invoice.items:
            data["Items"].append({
                "ItemSeq": item.sequence,
                "ItemName": item.product_name,
                "ItemCount": item.quantity,
                "ItemWord": item.unit,
                "ItemPrice": item.unit_price,
                "ItemAmount": item.amount,
                "ItemTaxType": item.tax_type
            })
        
        # Add signature
        data["CheckMacValue"] = self._generate_signature(data)
        
        return data
    
    async def submit_invoice(self, invoice: Invoice) -> Dict[str, Any]:
        """Submit invoice to government e-invoice platform"""
        data = self._prepare_invoice_data(invoice)
        
        # In test/development mode, return mock response
        if settings.ENVIRONMENT != "production":
            return {
                "status": "success",
                "einvoice_id": f"TEST{invoice.invoice_number}{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "message": "測試環境 - 發票開立成功",
                "qr_code_url": f"https://test.einvoice.nat.gov.tw/qrcode/{invoice.invoice_number}",
                "response_time": datetime.now().isoformat()
            }
        
        # Production API call
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.endpoints['issue']}",
                    json=data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                if result.get("RtnCode") == "1":
                    return {
                        "status": "success",
                        "einvoice_id": result.get("InvoiceNumber"),
                        "message": result.get("RtnMsg"),
                        "qr_code_url": result.get("QRCodeURL"),
                        "response_time": datetime.now().isoformat()
                    }
                else:
                    raise Exception(f"API Error: {result.get('RtnMsg')}")
                    
            except httpx.HTTPError as e:
                raise Exception(f"HTTP Error: {str(e)}")
            except Exception as e:
                raise Exception(f"Invoice submission failed: {str(e)}")
    
    async def void_invoice(self, einvoice_id: str, reason: str) -> Dict[str, Any]:
        """Void an issued invoice"""
        data = {
            "MerchantID": self.app_id,
            "InvoiceNumber": einvoice_id,
            "InvoiceDate": datetime.now().strftime("%Y/%m/%d"),
            "Reason": reason
        }
        
        # Add signature
        data["CheckMacValue"] = self._generate_signature(data)
        
        # In test/development mode, return mock response
        if settings.ENVIRONMENT != "production":
            return {
                "status": "success",
                "message": "測試環境 - 發票作廢成功",
                "void_time": datetime.now().isoformat()
            }
        
        # Production API call
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.endpoints['void']}",
                    json=data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                if result.get("RtnCode") == "1":
                    return {
                        "status": "success",
                        "message": result.get("RtnMsg"),
                        "void_time": datetime.now().isoformat()
                    }
                else:
                    raise Exception(f"API Error: {result.get('RtnMsg')}")
                    
            except Exception as e:
                raise Exception(f"Invoice void failed: {str(e)}")
    
    async def query_invoice(self, invoice_number: str) -> Dict[str, Any]:
        """Query invoice status from platform"""
        data = {
            "MerchantID": self.app_id,
            "InvoiceNumber": invoice_number
        }
        
        # Add signature
        data["CheckMacValue"] = self._generate_signature(data)
        
        # In test/development mode, return mock response
        if settings.ENVIRONMENT != "production":
            return {
                "status": "success",
                "invoice_status": "issued",
                "message": "測試環境 - 發票查詢成功"
            }
        
        # Production API call would go here
        # ...
    
    async def issue_allowance(
        self,
        original_invoice_number: str,
        allowance_amount: float,
        reason: str
    ) -> Dict[str, Any]:
        """Issue allowance (credit note) for an invoice"""
        data = {
            "MerchantID": self.app_id,
            "InvoiceNumber": original_invoice_number,
            "AllowanceDate": datetime.now().strftime("%Y/%m/%d"),
            "AllowanceAmount": int(allowance_amount),
            "Reason": reason
        }
        
        # Add signature
        data["CheckMacValue"] = self._generate_signature(data)
        
        # In test/development mode, return mock response
        if settings.ENVIRONMENT != "production":
            return {
                "status": "success",
                "allowance_number": f"ALLOW{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "message": "測試環境 - 折讓開立成功"
            }
        
        # Production API call would go here
        # ...
    
    def validate_carrier(self, carrier_type: str, carrier_id: str) -> bool:
        """Validate carrier (載具) format"""
        if carrier_type == "3J0002":  # 手機條碼
            # Should be /[A-Z0-9+-\.]{7}/
            import re
            return bool(re.match(r'^[A-Z0-9+\-\.]{7}$', carrier_id))
        elif carrier_type == "CQ0001":  # 自然人憑證
            # Should be 2 uppercase letters + 14 digits
            import re
            return bool(re.match(r'^[A-Z]{2}\d{14}$', carrier_id))
        # Add more carrier types as needed
        return True