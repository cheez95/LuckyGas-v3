"""
Taiwan Government E-Invoice Platform Configuration

This module contains configuration for integrating with the Taiwan
Government E-Invoice Platform (財政部電子發票整合服務平台).

Reference: https://www.einvoice.nat.gov.tw/
"""
import os
from typing import Dict, Any
from enum import Enum


class EInvoiceEnvironment(str, Enum):
    """E-Invoice platform environments"""
    TEST = "test"
    PRODUCTION = "production"


class EInvoiceAPIVersion(str, Enum):
    """E-Invoice API versions"""
    V2 = "V2"  # Current version as of 2025


# E-Invoice Platform Configuration
EINVOICE_CONFIG = {
    "test": {
        # Test environment base URLs
        "api_url": "https://wwwtest.einvoice.nat.gov.tw",
        "b2b_api_url": "https://wwwtest.einvoice.nat.gov.tw/BIZAPIVAN/biz",
        "b2c_api_url": "https://wwwtest.einvoice.nat.gov.tw/INVAPIVAN/invapp",
        
        # Credentials (to be set via environment variables)
        "app_id": os.getenv("EINVOICE_TEST_APP_ID", "PLACEHOLDER_TEST_APP_ID"),
        "api_key": os.getenv("EINVOICE_TEST_API_KEY", "PLACEHOLDER_TEST_API_KEY"),
        
        # Certificate paths for mutual TLS (if required)
        "cert_path": os.getenv("EINVOICE_TEST_CERT_PATH", ""),
        "key_path": os.getenv("EINVOICE_TEST_KEY_PATH", ""),
        
        # API settings
        "timeout": 30,
        "max_retries": 3,
        "retry_delay": 1,  # seconds
    },
    "production": {
        # Production environment base URLs
        "api_url": "https://www.einvoice.nat.gov.tw",
        "b2b_api_url": "https://www.einvoice.nat.gov.tw/BIZAPIVAN/biz",
        "b2c_api_url": "https://www.einvoice.nat.gov.tw/INVAPIVAN/invapp",
        
        # Credentials (to be set via environment variables)
        "app_id": os.getenv("EINVOICE_PROD_APP_ID", "PLACEHOLDER_PROD_APP_ID"),
        "api_key": os.getenv("EINVOICE_PROD_API_KEY", "PLACEHOLDER_PROD_API_KEY"),
        
        # Certificate paths for mutual TLS (if required)
        "cert_path": os.getenv("EINVOICE_PROD_CERT_PATH", ""),
        "key_path": os.getenv("EINVOICE_PROD_KEY_PATH", ""),
        
        # API settings
        "timeout": 30,
        "max_retries": 3,
        "retry_delay": 1,  # seconds
    }
}


# API Endpoints
EINVOICE_ENDPOINTS = {
    # B2B Invoice APIs
    "b2b": {
        "issue": "/InvoiceIssue",                    # 開立發票
        "void": "/InvoiceVoid",                      # 作廢發票
        "allowance": "/AllowanceIssue",              # 開立折讓
        "allowance_void": "/AllowanceVoid",          # 作廢折讓
        "query": "/InvoiceSearch",                   # 查詢發票
        "print": "/InvoicePrint",                    # 列印發票
        "notify": "/InvoiceNotify",                  # 發送通知
    },
    # B2C Invoice APIs
    "b2c": {
        "issue": "/InvoiceIssue",                    # 開立發票
        "void": "/InvoiceVoid",                      # 作廢發票
        "donate": "/InvoiceDonate",                  # 捐贈發票
        "carrier_save": "/CarrierSave",              # 儲存載具
        "qrcode": "/QRCodeINV",                      # 產生QR Code
    }
}


# Error Codes and Messages
EINVOICE_ERROR_CODES = {
    # Success
    "1": "成功",
    
    # Common errors
    "0": "失敗",
    "9000001": "系統錯誤",
    "9000002": "參數錯誤",
    "9000003": "驗證錯誤",
    
    # Invoice specific errors
    "5000001": "發票號碼重複",
    "5000002": "發票號碼格式錯誤",
    "5000003": "發票日期錯誤",
    "5000004": "買方統編錯誤",
    "5000005": "賣方統編錯誤",
    "5000006": "發票金額錯誤",
    "5000007": "發票已作廢",
    "5000008": "發票不存在",
    
    # Allowance specific errors
    "6000001": "折讓單號碼重複",
    "6000002": "原發票號碼不存在",
    "6000003": "折讓金額超過原發票金額",
    "6000004": "折讓單已作廢",
    
    # Authentication errors
    "7000001": "APP_ID錯誤",
    "7000002": "簽章驗證失敗",
    "7000003": "憑證過期",
    "7000004": "IP不在白名單內",
}


# Invoice Types
INVOICE_TYPES = {
    "07": "一般稅額計算",
    "08": "特種稅額計算"
}


# Tax Types
TAX_TYPES = {
    "1": "應稅",
    "2": "零稅率",
    "3": "免稅",
    "4": "應稅(特種稅率)",
    "9": "混合應稅與免稅或零稅率"
}


# Carrier Types
CARRIER_TYPES = {
    "": "無載具",
    "3J0002": "手機條碼載具",
    "CQ0001": "自然人憑證載具",
    "1K0001": "悠遊卡載具",
    "1H0001": "一卡通載具",
    "2G0001": "icash載具"
}


# Print Marks
PRINT_MARKS = {
    "Y": "列印",
    "N": "不列印"
}


# Donate Marks
DONATE_MARKS = {
    "0": "不捐贈",
    "1": "捐贈"
}


# QR Code Encryption Settings
QRCODE_SETTINGS = {
    "aes_key": os.getenv("EINVOICE_QRCODE_AES_KEY", ""),  # 32 bytes AES key
    "version": "1.0",
    "encoding": "UTF-8"
}


def get_einvoice_config(environment: str = None) -> Dict[str, Any]:
    """
    Get E-Invoice configuration for specified environment
    
    Args:
        environment: 'test' or 'production', defaults to ENVIRONMENT setting
        
    Returns:
        Configuration dictionary for the specified environment
    """
    if environment is None:
        from app.core.config import settings
        environment = "test" if settings.ENVIRONMENT != "production" else "production"
    
    if environment not in EINVOICE_CONFIG:
        raise ValueError(f"Invalid environment: {environment}")
    
    return EINVOICE_CONFIG[environment]


def validate_einvoice_config(config: Dict[str, Any]) -> bool:
    """
    Validate E-Invoice configuration has required fields
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = ["app_id", "api_key", "b2b_api_url", "b2c_api_url"]
    
    for field in required_fields:
        if not config.get(field) or config[field].startswith("PLACEHOLDER"):
            raise ValueError(
                f"E-Invoice configuration field '{field}' is not set. "
                f"Please set the appropriate environment variable."
            )
    
    return True