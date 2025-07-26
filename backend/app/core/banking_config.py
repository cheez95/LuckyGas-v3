"""Banking configuration for Taiwan banks."""

from typing import Dict, Any

# Placeholder banking configurations for common Taiwan banks
# In production, these should be stored encrypted in the database
BANKING_CONFIG: Dict[str, Dict[str, Any]] = {
    "banks": {
        "CTBC": {  # 中國信託
            "bank_name": "中國信託商業銀行",
            "sftp_host": "sftp.ctbcbank.com",
            "sftp_port": 22,
            "sftp_username": "PLACEHOLDER_USERNAME",
            "sftp_password": "PLACEHOLDER_PASSWORD",
            "upload_path": "/upload/luckygas/",
            "download_path": "/download/luckygas/",
            "archive_path": "/archive/luckygas/",
            "file_format": "fixed_width",
            "encoding": "Big5",
            "payment_file_pattern": "PAY_{YYYYMMDD}_{BATCH}.txt",
            "reconciliation_file_pattern": "REC_{YYYYMMDD}_{BATCH}.txt",
            "cutoff_time": "15:00",
            "retry_attempts": 3,
            "retry_delay_minutes": 30
        },
        "ESUN": {  # 玉山銀行
            "bank_name": "玉山商業銀行",
            "sftp_host": "sftp.esunbank.com.tw",
            "sftp_port": 22,
            "sftp_username": "PLACEHOLDER_USERNAME",
            "sftp_password": "PLACEHOLDER_PASSWORD",
            "upload_path": "/ach/upload/",
            "download_path": "/ach/download/",
            "archive_path": "/ach/archive/",
            "file_format": "fixed_width",
            "encoding": "UTF-8",
            "payment_file_pattern": "ACH_PAY_{YYYYMMDD}_{BATCH}.DAT",
            "reconciliation_file_pattern": "ACH_REC_{YYYYMMDD}.DAT",
            "cutoff_time": "14:30",
            "retry_attempts": 3,
            "retry_delay_minutes": 30
        },
        "FIRST": {  # 第一銀行
            "bank_name": "第一商業銀行",
            "sftp_host": "sftp.firstbank.com.tw",
            "sftp_port": 22,
            "sftp_username": "PLACEHOLDER_USERNAME",
            "sftp_password": "PLACEHOLDER_PASSWORD",
            "upload_path": "/payment/upload/",
            "download_path": "/payment/download/",
            "archive_path": "/payment/archive/",
            "file_format": "csv",
            "encoding": "Big5",
            "delimiter": ",",
            "payment_file_pattern": "PAYMENT_{YYYYMMDD}_{BATCH}.CSV",
            "reconciliation_file_pattern": "RECON_{YYYYMMDD}.CSV",
            "cutoff_time": "16:00",
            "retry_attempts": 3,
            "retry_delay_minutes": 30
        },
        "CATHAY": {  # 國泰世華
            "bank_name": "國泰世華商業銀行",
            "sftp_host": "sftp.cathaybk.com.tw",
            "sftp_port": 22,
            "sftp_username": "PLACEHOLDER_USERNAME",
            "sftp_password": "PLACEHOLDER_PASSWORD",
            "upload_path": "/corporate/upload/",
            "download_path": "/corporate/download/",
            "archive_path": "/corporate/archive/",
            "file_format": "fixed_width",
            "encoding": "UTF-8",
            "payment_file_pattern": "CB_PAY_{YYYYMMDD}_{BATCH}.TXT",
            "reconciliation_file_pattern": "CB_REC_{YYYYMMDD}.TXT",
            "cutoff_time": "15:30",
            "retry_attempts": 3,
            "retry_delay_minutes": 30
        },
        "FUBON": {  # 富邦銀行
            "bank_name": "台北富邦商業銀行",
            "sftp_host": "sftp.fubonbank.com.tw",
            "sftp_port": 22,
            "sftp_username": "PLACEHOLDER_USERNAME",
            "sftp_password": "PLACEHOLDER_PASSWORD",
            "upload_path": "/edi/upload/",
            "download_path": "/edi/download/",
            "archive_path": "/edi/archive/",
            "file_format": "fixed_width",
            "encoding": "Big5",
            "payment_file_pattern": "FB_PAYMENT_{YYYYMMDD}_{BATCH}.EDI",
            "reconciliation_file_pattern": "FB_RECONCILE_{YYYYMMDD}.EDI",
            "cutoff_time": "14:00",
            "retry_attempts": 3,
            "retry_delay_minutes": 30
        },
        "MEGA": {  # 兆豐銀行
            "bank_name": "兆豐國際商業銀行",
            "sftp_host": "sftp.megabank.com.tw",
            "sftp_port": 22,
            "sftp_username": "PLACEHOLDER_USERNAME",
            "sftp_password": "PLACEHOLDER_PASSWORD",
            "upload_path": "/batch/upload/",
            "download_path": "/batch/download/",
            "archive_path": "/batch/archive/",
            "file_format": "csv",
            "encoding": "UTF-8",
            "delimiter": "|",
            "payment_file_pattern": "MEGA_PAY_{YYYYMMDD}_{BATCH}.CSV",
            "reconciliation_file_pattern": "MEGA_REC_{YYYYMMDD}.CSV",
            "cutoff_time": "15:00",
            "retry_attempts": 3,
            "retry_delay_minutes": 30
        }
    }
}

# Taiwan banking file format specifications
TAIWAN_BANKING_FORMATS = {
    "fixed_width": {
        "header": {
            "record_type": (1, 1),        # H
            "batch_number": (2, 21),      # 批次號碼
            "file_date": (22, 29),        # YYYYMMDD
            "bank_code": (30, 32),        # 銀行代碼
            "company_code": (33, 42),     # 公司代碼
            "version": (43, 45),          # 版本
            "filler": (46, 200)           # 保留
        },
        "detail": {
            "record_type": (1, 1),        # D
            "sequence": (2, 7),           # 序號
            "transaction_id": (8, 27),    # 交易編號
            "account_number": (28, 41),   # 扣款帳號
            "account_holder": (42, 71),   # 戶名
            "amount": (72, 84),          # 金額 (no decimals)
            "payment_date": (85, 92),     # YYYYMMDD
            "id_number": (93, 102),       # 身分證/統編
            "memo": (103, 152),          # 備註
            "filler": (153, 200)         # 保留
        },
        "trailer": {
            "record_type": (1, 1),        # T
            "total_count": (2, 7),        # 總筆數
            "total_amount": (8, 22),      # 總金額
            "success_count": (23, 28),    # 成功筆數
            "success_amount": (29, 43),   # 成功金額
            "fail_count": (44, 49),       # 失敗筆數
            "fail_amount": (50, 64),      # 失敗金額
            "filler": (65, 200)          # 保留
        }
    },
    "csv": {
        "payment_headers": [
            "交易序號",      # Transaction sequence
            "扣款帳號",      # Debit account
            "戶名",          # Account holder
            "扣款金額",      # Amount
            "扣款日期",      # Debit date
            "身分證/統編",   # ID number
            "備註"           # Remarks
        ],
        "reconciliation_headers": [
            "交易序號",      # Transaction sequence
            "銀行參考號",    # Bank reference
            "處理日期",      # Process date
            "回應代碼",      # Response code
            "回應訊息",      # Response message
            "實際扣款金額"   # Actual amount
        ]
    }
}

# Response codes for Taiwan banking
TAIWAN_BANK_RESPONSE_CODES = {
    "000": "交易成功",
    "001": "餘額不足",
    "002": "帳號錯誤",
    "003": "帳戶已結清",
    "004": "帳戶凍結",
    "005": "無此帳號",
    "006": "金額錯誤",
    "007": "系統錯誤",
    "008": "重複交易",
    "009": "逾期交易",
    "010": "未授權交易",
    "099": "其他錯誤"
}