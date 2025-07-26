# API Endpoints - Invoice Operations Module - Lucky Gas Legacy System

## 🎯 API Overview

The Invoice Operations module exposes RESTful APIs for invoice generation, management, void processing, credit notes, and government compliance. All endpoints follow consistent patterns for authentication, validation, and error handling.

## 🔐 Authentication & Headers

```yaml
Required Headers:
  Authorization: Bearer {JWT_TOKEN}
  X-User-ID: {USER_ID}
  X-Department: {DEPT_CODE}
  Accept-Language: zh-TW (default) | en-US

Optional Headers:
  X-Request-ID: {UUID} # For request tracking
  X-Session-ID: {SESSION_ID} # For audit trail
  X-Client-Version: {VERSION} # Client compatibility
```

## 📊 Invoice Generation APIs

### 1. Generate Invoice

**POST /api/v1/invoices/generate**
```yaml
Description: Generate new invoice from order/delivery
Request Body:
  {
    "trigger_type": "delivery", # delivery | order | manual
    "reference_id": "DEL20240120001",
    "reference_type": "delivery",
    "invoice_type": "B2B", # B2B | B2C | EXPORT
    "customer_override": {
      "tax_id": "12345678",
      "name": "客戶名稱",
      "address": "台北市信義區...",
      "contact": "張先生",
      "phone": "0912-345-678"
    },
    "carrier_info": {
      "type": "mobile", # mobile | card | print | donate
      "carrier_id": "/AB+12345",
      "donate_code": "919" # if type = donate
    },
    "consolidate_orders": ["ORD001", "ORD002"], # optional
    "special_handling": {
      "force_generation": false,
      "skip_credit_check": false,
      "override_tax_rate": null
    }
  }

Response:
  {
    "success": true,
    "data": {
      "invoice_no": "AB12345678",
      "invoice_date": "2024-01-20",
      "customer_id": "CUST001",
      "customer_name": "客戶名稱",
      "sales_amount": 10000,
      "tax_amount": 500,
      "total_amount": 10500,
      "invoice_type": "B2B",
      "status": "normal",
      "e_invoice_status": "pending_upload",
      "qr_codes": {
        "left": "AB123456782024012000011050010500...",
        "right": "**產品明細編碼..."
      },
      "print_required": false,
      "carrier_saved": true,
      "generation_time": 2.3
    },
    "message": "發票開立成功",
    "timestamp": "2024-01-20T10:30:00Z"
  }

Errors:
  - 400: Invalid parameters
  - 402: Credit limit exceeded
  - 404: Reference not found
  - 409: Invoice already exists
  - 422: Validation failed
```

### 2. Get Invoice Details

**GET /api/v1/invoices/{invoice_no}**
```yaml
Description: Retrieve invoice details
Path Parameters:
  - invoice_no: string (required)

Query Parameters:
  - include_items: boolean (default: true)
  - include_history: boolean (default: false)
  - include_payment: boolean (default: false)

Response:
  {
    "success": true,
    "data": {
      "invoice_no": "AB12345678",
      "invoice_date": "2024-01-20",
      "invoice_type": "B2B",
      "customer": {
        "id": "CUST001",
        "tax_id": "12345678",
        "name": "客戶名稱",
        "address": "台北市信義區...",
        "contact": "張先生",
        "phone": "0912-345-678"
      },
      "amounts": {
        "sales_amount": 10000,
        "tax_type": "1",
        "tax_rate": 5.0,
        "tax_amount": 500,
        "total_amount": 10500
      },
      "status": {
        "invoice_status": "normal",
        "print_status": "Y",
        "e_invoice_status": "uploaded",
        "payment_status": "unpaid"
      },
      "items": [
        {
          "line_no": 1,
          "product_id": "GAS001",
          "product_name": "20公斤桶裝瓦斯",
          "quantity": 10,
          "unit": "桶",
          "unit_price": 1000,
          "amount": 10000
        }
      ],
      "references": {
        "order_no": "ORD20240120001",
        "delivery_no": "DEL20240120001"
      },
      "audit": {
        "created_by": "USER001",
        "created_date": "2024-01-20T10:30:00Z",
        "modified_by": null,
        "modified_date": null
      }
    }
  }

Errors:
  - 404: Invoice not found
  - 403: Access denied
```

### 3. Search Invoices

**GET /api/v1/invoices/search**
```yaml
Description: Search invoices with filters
Query Parameters:
  - invoice_no: string # Exact or partial
  - customer_id: string
  - customer_name: string # Partial match
  - date_from: date
  - date_to: date
  - status: string # normal | void | credited
  - payment_status: string # unpaid | partial | paid | overdue
  - amount_min: number
  - amount_max: number
  - page: integer (default: 1)
  - size: integer (default: 20, max: 100)
  - sort: string (default: invoice_date desc)

Response:
  {
    "success": true,
    "data": {
      "invoices": [
        {
          "invoice_no": "AB12345678",
          "invoice_date": "2024-01-20",
          "customer_name": "客戶名稱",
          "total_amount": 10500,
          "status": "normal",
          "payment_status": "unpaid",
          "e_invoice_status": "uploaded"
        }
      ],
      "summary": {
        "total_count": 150,
        "total_amount": 1575000,
        "total_tax": 75000
      },
      "pagination": {
        "page": 1,
        "size": 20,
        "total": 150,
        "pages": 8
      }
    }
  }
```

### 4. Batch Invoice Generation

**POST /api/v1/invoices/batch/generate**
```yaml
Description: Generate multiple invoices in batch
Request Body:
  {
    "generation_date": "2024-01-20",
    "filter_criteria": {
      "delivery_date_from": "2024-01-19",
      "delivery_date_to": "2024-01-19",
      "uninvoiced_only": true,
      "customer_ids": ["CUST001", "CUST002"]
    },
    "options": {
      "skip_credit_check": false,
      "consolidate_by_customer": true,
      "auto_upload": true
    }
  }

Response:
  {
    "success": true,
    "data": {
      "batch_id": "BATCH20240120001",
      "total_processed": 50,
      "success_count": 48,
      "failed_count": 2,
      "invoices_generated": [
        {
          "invoice_no": "AB12345678",
          "customer_id": "CUST001",
          "amount": 10500
        }
      ],
      "failures": [
        {
          "reference": "DEL20240119050",
          "reason": "Credit limit exceeded",
          "customer_id": "CUST050"
        }
      ],
      "processing_time": 15.6
    }
  }
```

## 🚫 Invoice Void APIs

### 5. Void Invoice

**POST /api/v1/invoices/{invoice_no}/void**
```yaml
Description: Process invoice cancellation
Path Parameters:
  - invoice_no: string (required)

Request Body:
  {
    "void_reason": "01", # 01:資料錯誤 02:重複 03:退貨 04:其他
    "void_description": "客戶名稱錯誤",
    "physical_returned": true,
    "return_date": "2024-01-20",
    "replacement_required": true,
    "approver_id": "MGR001",
    "approval_notes": "已確認錯誤"
  }

Response:
  {
    "success": true,
    "data": {
      "void_id": 12345,
      "invoice_no": "AB12345678",
      "void_date": "2024-01-20",
      "void_status": "completed",
      "upload_required": true,
      "upload_status": "pending",
      "replacement_order": "ORD20240120999"
    },
    "message": "發票作廢成功"
  }

Errors:
  - 400: Invalid void request
  - 403: No permission to void
  - 409: Already voided
  - 422: Period restriction
```

### 6. Get Void Records

**GET /api/v1/invoices/voids**
```yaml
Description: List void records
Query Parameters:
  - date_from: date
  - date_to: date
  - void_type: string
  - upload_status: string
  - page: integer
  - size: integer

Response:
  {
    "success": true,
    "data": {
      "void_records": [
        {
          "void_id": 12345,
          "invoice_no": "AB12345678",
          "void_date": "2024-01-20",
          "void_reason": "01",
          "void_description": "資料錯誤",
          "approved_by": "MGR001",
          "upload_status": "uploaded"
        }
      ],
      "pagination": {...}
    }
  }
```

## 💳 Credit Note APIs

### 7. Create Credit Note

**POST /api/v1/invoices/credit-notes**
```yaml
Description: Issue credit note for invoice adjustment
Request Body:
  {
    "original_invoice_no": "AB12345678",
    "credit_type": "01", # 01:退貨 02:折讓 03:品質 04:其他
    "credit_reason": "產品退回",
    "credit_items": [
      {
        "line_no": 1,
        "product_id": "GAS001",
        "quantity": 2,
        "credit_amount": 2000
      }
    ],
    "credit_amount": 2000,
    "tax_amount": 100,
    "total_credit": 2100,
    "return_authorization": "RMA20240120001",
    "approval_required": true
  }

Response:
  {
    "success": true,
    "data": {
      "credit_note_no": "CN2024010001",
      "credit_date": "2024-01-20",
      "original_invoice_no": "AB12345678",
      "credit_amount": 2000,
      "tax_amount": 100,
      "total_credit": 2100,
      "status": "approved",
      "upload_status": "pending"
    }
  }
```

### 8. Get Credit Note

**GET /api/v1/invoices/credit-notes/{credit_note_no}**
```yaml
Description: Get credit note details
Path Parameters:
  - credit_note_no: string (required)

Response:
  {
    "success": true,
    "data": {
      "credit_note_no": "CN2024010001",
      "credit_date": "2024-01-20",
      "original_invoice": {
        "invoice_no": "AB12345678",
        "invoice_date": "2024-01-15",
        "original_amount": 10500
      },
      "credit_details": {
        "credit_amount": 2000,
        "tax_amount": 100,
        "total_credit": 2100
      },
      "items": [...],
      "approval": {
        "status": "approved",
        "approved_by": "MGR001",
        "approved_date": "2024-01-20T11:00:00Z"
      }
    }
  }
```

### 9. Approve Credit Note

**POST /api/v1/invoices/credit-notes/{credit_note_no}/approve**
```yaml
Description: Approve pending credit note
Path Parameters:
  - credit_note_no: string (required)

Request Body:
  {
    "action": "approve", # approve | reject
    "comments": "核准退貨",
    "modified_amount": null # optional override
  }

Response:
  {
    "success": true,
    "data": {
      "credit_note_no": "CN2024010001",
      "status": "approved",
      "approved_by": "MGR001",
      "approved_date": "2024-01-20T15:00:00Z"
    }
  }
```

## 📤 E-Invoice Upload APIs

### 10. Upload E-Invoices

**POST /api/v1/invoices/upload**
```yaml
Description: Upload invoices to government platform
Request Body:
  {
    "upload_type": "manual", # manual | scheduled | automatic
    "selection_criteria": {
      "date_from": "2024-01-19",
      "date_to": "2024-01-20",
      "invoice_type": ["B2B", "B2C"],
      "status": "pending_upload"
    },
    "batch_options": {
      "max_batch_size": 5000,
      "include_voids": true,
      "include_credits": true
    }
  }

Response:
  {
    "success": true,
    "data": {
      "batch_id": "BATCH20240120001",
      "upload_timestamp": "2024-01-20T23:05:00Z",
      "total_invoices": 500,
      "batches_created": 1,
      "upload_status": "processing",
      "estimated_completion": "2024-01-20T23:10:00Z"
    }
  }
```

### 11. Check Upload Status

**GET /api/v1/invoices/upload/{batch_id}/status**
```yaml
Description: Check government upload status
Path Parameters:
  - batch_id: string (required)

Response:
  {
    "success": true,
    "data": {
      "batch_id": "BATCH20240120001",
      "status": "completed", # processing | completed | failed | partial
      "upload_details": {
        "start_time": "2024-01-20T23:05:00Z",
        "end_time": "2024-01-20T23:08:30Z",
        "total_invoices": 500,
        "success_count": 498,
        "fail_count": 2
      },
      "failures": [
        {
          "invoice_no": "AB12345679",
          "error_code": "E001",
          "error_message": "重複的發票號碼"
        }
      ],
      "confirmation_number": "2024012000123"
    }
  }
```

### 12. Retry Failed Uploads

**POST /api/v1/invoices/upload/retry**
```yaml
Description: Retry failed invoice uploads
Request Body:
  {
    "batch_id": "BATCH20240120001",
    "invoice_numbers": ["AB12345679", "AB12345680"], # optional
    "retry_all_failed": true
  }

Response:
  {
    "success": true,
    "data": {
      "retry_batch_id": "BATCH20240120002",
      "retry_count": 2,
      "status": "queued"
    }
  }
```

## 🖨️ Reprint APIs

### 13. Reprint Invoice

**POST /api/v1/invoices/{invoice_no}/reprint**
```yaml
Description: Request invoice reprint
Path Parameters:
  - invoice_no: string (required)

Request Body:
  {
    "reason": "customer_request", # customer_request | lost | damaged | internal
    "delivery_method": "print", # print | email | both
    "email_address": "customer@example.com",
    "add_watermark": true,
    "authorization": "客戶來電要求"
  }

Response:
  {
    "success": true,
    "data": {
      "reprint_id": 789,
      "invoice_no": "AB12345678",
      "print_count": 2,
      "watermark_applied": true,
      "delivery_status": "completed",
      "printed_at": "2024-01-20T14:00:00Z"
    }
  }

Errors:
  - 403: Reprint limit exceeded
  - 404: Invoice not found
```

## 📊 Reconciliation APIs

### 14. Invoice Reconciliation

**GET /api/v1/invoices/reconciliation**
```yaml
Description: Get invoice reconciliation data
Query Parameters:
  - period_year: integer (required)
  - period_month: integer (required)
  - reconciliation_type: string # daily | monthly | custom

Response:
  {
    "success": true,
    "data": {
      "period": "2024-01",
      "summary": {
        "total_invoices": 15000,
        "total_amount": 15750000,
        "total_tax": 750000,
        "void_count": 50,
        "credit_count": 100
      },
      "by_type": {
        "B2B": {
          "count": 8000,
          "amount": 10000000
        },
        "B2C": {
          "count": 7000,
          "amount": 5750000
        }
      },
      "upload_status": {
        "uploaded": 14900,
        "pending": 50,
        "failed": 50
      },
      "payment_status": {
        "paid": 12000,
        "unpaid": 2950,
        "overdue": 50
      }
    }
  }
```

### 15. Close Invoice Period

**POST /api/v1/invoices/periods/close**
```yaml
Description: Close monthly invoice period
Request Body:
  {
    "period_year": 2024,
    "period_month": 1,
    "validation_checks": {
      "all_uploaded": true,
      "reconciliation_complete": true,
      "voids_processed": true,
      "credits_processed": true
    },
    "force_close": false
  }

Response:
  {
    "success": true,
    "data": {
      "period": "2024-01",
      "closed_at": "2024-02-05T10:00:00Z",
      "closed_by": "FIN001",
      "statistics": {
        "total_invoices": 15000,
        "total_revenue": 15750000,
        "total_tax": 750000
      },
      "reports_generated": [
        "monthly_tax_report.pdf",
        "invoice_summary.xlsx",
        "void_report.pdf"
      ]
    }
  }
```

## 🔧 Configuration APIs

### 16. Get Invoice Parameters

**GET /api/v1/invoices/parameters**
```yaml
Description: Get invoice system parameters
Query Parameters:
  - param_type: string # number_range | tax_setting | print_config

Response:
  {
    "success": true,
    "data": {
      "parameters": [
        {
          "param_id": "CURRENT_RANGE",
          "param_type": "number_range",
          "param_value": "AB12340000-AB12349999",
          "description": "當期發票號碼區間",
          "effective_date": "2024-01-01",
          "active": true
        },
        {
          "param_id": "TAX_RATE",
          "param_type": "tax_setting",
          "param_value": "5",
          "description": "營業稅率",
          "active": true
        }
      ]
    }
  }
```

### 17. Update Invoice Parameters

**PUT /api/v1/invoices/parameters/{param_id}**
```yaml
Description: Update invoice parameter (Admin only)
Path Parameters:
  - param_id: string (required)

Request Body:
  {
    "param_value": "AB12350000-AB12359999",
    "effective_date": "2024-02-01",
    "reason": "新期別號碼區間"
  }

Response:
  {
    "success": true,
    "data": {
      "param_id": "CURRENT_RANGE",
      "old_value": "AB12340000-AB12349999",
      "new_value": "AB12350000-AB12359999",
      "effective_date": "2024-02-01",
      "updated_by": "ADMIN001",
      "updated_at": "2024-01-25T10:00:00Z"
    }
  }
```

## 📈 Analytics APIs

### 18. Invoice Statistics

**GET /api/v1/invoices/statistics**
```yaml
Description: Get invoice statistics and analytics
Query Parameters:
  - date_from: date (required)
  - date_to: date (required)
  - group_by: string # day | week | month | customer | product

Response:
  {
    "success": true,
    "data": {
      "period": {
        "from": "2024-01-01",
        "to": "2024-01-31"
      },
      "summary": {
        "total_invoices": 15000,
        "total_revenue": 15750000,
        "average_invoice": 1050,
        "void_rate": 0.33,
        "credit_rate": 0.67
      },
      "trends": [
        {
          "date": "2024-01-01",
          "count": 450,
          "amount": 472500
        }
      ],
      "top_customers": [
        {
          "customer_id": "CUST001",
          "customer_name": "大客戶A",
          "invoice_count": 150,
          "total_amount": 315000
        }
      ]
    }
  }
```

### 19. Tax Report

**GET /api/v1/invoices/reports/tax**
```yaml
Description: Generate tax report for period
Query Parameters:
  - year: integer (required)
  - month: integer (required)
  - report_type: string # summary | detailed | government

Response:
  {
    "success": true,
    "data": {
      "report_period": "2024-01",
      "tax_summary": {
        "total_sales": 15000000,
        "taxable_sales": 15000000,
        "zero_rated_sales": 0,
        "tax_exempt_sales": 0,
        "output_tax": 750000
      },
      "by_tax_type": {
        "standard_rated": {
          "amount": 15000000,
          "tax": 750000
        }
      },
      "void_adjustments": {
        "void_amount": -52500,
        "void_tax": -2625
      },
      "credit_adjustments": {
        "credit_amount": -105000,
        "credit_tax": -5250
      },
      "net_tax_payable": 742125,
      "report_url": "/api/v1/invoices/reports/download/tax_202401.pdf"
    }
  }
```

## 📱 Customer Portal APIs

### 20. Customer Invoice History

**GET /api/v1/invoices/customer/{customer_id}/history**
```yaml
Description: Get customer's invoice history
Path Parameters:
  - customer_id: string (required)

Query Parameters:
  - date_from: date
  - date_to: date
  - status: string
  - page: integer
  - size: integer

Response:
  {
    "success": true,
    "data": {
      "customer": {
        "id": "CUST001",
        "name": "客戶名稱",
        "tax_id": "12345678"
      },
      "invoices": [
        {
          "invoice_no": "AB12345678",
          "invoice_date": "2024-01-20",
          "amount": 10500,
          "status": "normal",
          "payment_status": "paid",
          "download_url": "/api/v1/invoices/AB12345678/download"
        }
      ],
      "summary": {
        "total_invoices": 45,
        "total_amount": 472500,
        "unpaid_amount": 31500
      },
      "pagination": {...}
    }
  }
```

## 🔍 Common Error Responses

```yaml
400 Bad Request:
  {
    "success": false,
    "error": {
      "code": "INVALID_PARAMETERS",
      "message": "參數驗證失敗",
      "details": {
        "invoice_date": "日期格式錯誤",
        "tax_id": "統編格式不正確"
      }
    }
  }

403 Forbidden:
  {
    "success": false,
    "error": {
      "code": "INSUFFICIENT_PERMISSION",
      "message": "權限不足",
      "required_role": "INVOICE_VOID"
    }
  }

409 Conflict:
  {
    "success": false,
    "error": {
      "code": "DUPLICATE_INVOICE",
      "message": "發票已存在",
      "existing_invoice": "AB12345678"
    }
  }

422 Unprocessable Entity:
  {
    "success": false,
    "error": {
      "code": "BUSINESS_RULE_VIOLATION",
      "message": "違反商業規則",
      "rule": "發票必須在7天內開立"
    }
  }

500 Internal Server Error:
  {
    "success": false,
    "error": {
      "code": "INTERNAL_ERROR",
      "message": "系統錯誤，請稍後再試",
      "request_id": "REQ123456"
    }
  }
```

## 🔒 Security Headers

All API responses include:
```yaml
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: default-src 'self'
```

## 📈 Rate Limiting

```yaml
Default Limits:
  - Per user: 100 requests/minute
  - Per IP: 300 requests/minute
  - Invoice generation: 10 per minute
  - Batch operations: 1 per minute
  - Upload operations: 5 per hour

Headers:
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1642694400
```