# API Endpoints - Reports Module - Lucky Gas Legacy System

## 🎯 API Overview

The Reports module exposes RESTful APIs for report generation, scheduling, dashboard access, and report management. All endpoints follow consistent patterns for authentication, pagination, and error handling.

## 🔐 Authentication & Headers

```yaml
Required Headers:
  Authorization: Bearer {JWT_TOKEN}
  X-User-ID: {USER_ID}
  X-Department: {DEPT_CODE}
  Accept-Language: zh-TW (default) | en-US

Optional Headers:
  X-Request-ID: {UUID} # For request tracking
  X-Client-Version: {VERSION} # Client compatibility
```

## 📊 Report Generation APIs

### 1. Report Catalog

**GET /api/v1/reports/catalog**
```yaml
Description: Get available reports for current user
Parameters:
  - category: string (optional) # Filter by category
  - type: string (optional) # Filter by report type
  - search: string (optional) # Search in report names
  - page: integer (default: 1)
  - size: integer (default: 20, max: 100)

Response:
  {
    "success": true,
    "data": {
      "reports": [
        {
          "report_id": "RPT001",
          "report_code": "DAILY_SALES_REPORT",
          "report_name": "每日銷售報表",
          "category": "01",
          "category_name": "銷售報表",
          "type": "01",
          "type_name": "預設報表",
          "description": "每日銷售統計報表",
          "output_formats": ["HTML", "PDF", "EXCEL", "CSV"],
          "parameters": [
            {
              "name": "date_from",
              "label": "開始日期",
              "type": "DATE",
              "required": true,
              "default": "TODAY"
            }
          ],
          "is_favorite": false,
          "last_run": "2024-01-20T08:30:00Z"
        }
      ],
      "pagination": {
        "page": 1,
        "size": 20,
        "total": 150,
        "pages": 8
      }
    },
    "timestamp": "2024-01-20T10:00:00Z"
  }

Errors:
  - 401: Unauthorized
  - 403: Forbidden
```

### 2. Report Details

**GET /api/v1/reports/{report_id}**
```yaml
Description: Get detailed report information
Path Parameters:
  - report_id: string (required)

Response:
  {
    "success": true,
    "data": {
      "report_id": "RPT001",
      "report_code": "DAILY_SALES_REPORT",
      "report_name": "每日銷售報表",
      "report_name_en": "Daily Sales Report",
      "category": "01",
      "type": "01",
      "description": "每日銷售統計報表，包含各區域、產品類別的銷售數據",
      "help_text": "選擇日期範圍查看銷售統計...",
      "output_formats": ["HTML", "PDF", "EXCEL", "CSV"],
      "processing_type": "01",
      "cache_duration": 60,
      "max_rows": 10000,
      "timeout_seconds": 300,
      "security_level": "02",
      "parameters": [...],
      "sample_preview": "base64_encoded_image",
      "estimated_time": 30,
      "version": "1.0",
      "last_modified": "2024-01-15T10:00:00Z"
    }
  }

Errors:
  - 404: Report not found
  - 403: No access permission
```

### 3. Generate Report

**POST /api/v1/reports/{report_id}/generate**
```yaml
Description: Generate a report with parameters
Path Parameters:
  - report_id: string (required)

Request Body:
  {
    "parameters": {
      "date_from": "2024-01-01",
      "date_to": "2024-01-31",
      "customer_id": "CUST001",
      "include_details": true
    },
    "output_format": "PDF",
    "delivery_method": "download", # download | email | portal
    "email_recipients": ["user@example.com"],
    "async": false # true for background processing
  }

Response (Synchronous):
  {
    "success": true,
    "data": {
      "execution_id": 123456,
      "report_id": "RPT001",
      "status": "completed",
      "generation_time": 2.5,
      "row_count": 1500,
      "download_url": "/api/v1/reports/download/abc123",
      "expires_at": "2024-01-21T10:00:00Z",
      "file_size": 2048576
    }
  }

Response (Asynchronous):
  {
    "success": true,
    "data": {
      "execution_id": 123456,
      "status": "queued",
      "queue_position": 3,
      "estimated_time": 120,
      "status_url": "/api/v1/reports/execution/123456"
    }
  }

Errors:
  - 400: Invalid parameters
  - 402: Resource limit exceeded
  - 503: Queue full
```

### 4. Check Generation Status

**GET /api/v1/reports/execution/{execution_id}**
```yaml
Description: Check report generation status
Path Parameters:
  - execution_id: integer (required)

Response:
  {
    "success": true,
    "data": {
      "execution_id": 123456,
      "report_id": "RPT001",
      "status": "running", # queued | running | completed | failed | cancelled
      "progress": 65,
      "started_at": "2024-01-20T10:00:00Z",
      "completed_at": null,
      "error_message": null,
      "download_url": null
    }
  }
```

### 5. Download Report

**GET /api/v1/reports/download/{token}**
```yaml
Description: Download generated report file
Path Parameters:
  - token: string (required)

Headers:
  Range: bytes=0-1023 # For partial download

Response:
  Binary file stream
  
Response Headers:
  Content-Type: application/pdf
  Content-Disposition: attachment; filename="report_20240120.pdf"
  Content-Length: 2048576
  Accept-Ranges: bytes

Errors:
  - 404: File not found
  - 410: Link expired
```

### 6. Cancel Generation

**POST /api/v1/reports/execution/{execution_id}/cancel**
```yaml
Description: Cancel running report generation
Path Parameters:
  - execution_id: integer (required)

Response:
  {
    "success": true,
    "data": {
      "execution_id": 123456,
      "status": "cancelled",
      "cancelled_at": "2024-01-20T10:05:00Z"
    }
  }

Errors:
  - 400: Cannot cancel completed report
  - 404: Execution not found
```

## 📅 Report Scheduling APIs

### 7. List Schedules

**GET /api/v1/reports/schedules**
```yaml
Description: List user's report schedules
Parameters:
  - report_id: string (optional)
  - active: boolean (optional)
  - page: integer (default: 1)
  - size: integer (default: 20)

Response:
  {
    "success": true,
    "data": {
      "schedules": [
        {
          "schedule_id": 1,
          "report_id": "RPT001",
          "report_name": "每日銷售報表",
          "schedule_name": "每日早上6點銷售報表",
          "schedule_type": "01",
          "cron_expression": "0 6 * * *",
          "next_run": "2024-01-21T06:00:00Z",
          "last_run": "2024-01-20T06:00:00Z",
          "last_status": "01",
          "active": true,
          "recipients": ["manager@luckygas.com"]
        }
      ],
      "pagination": {...}
    }
  }
```

### 8. Create Schedule

**POST /api/v1/reports/schedules**
```yaml
Description: Create new report schedule
Request Body:
  {
    "report_id": "RPT001",
    "schedule_name": "每週一銷售總結",
    "schedule_type": "02", # 01:Daily, 02:Weekly, etc.
    "cron_expression": "0 9 * * 1",
    "time_zone": "Asia/Taipei",
    "start_date": "2024-02-01",
    "end_date": "2024-12-31",
    "parameters": {
      "date_from": "WEEK_START",
      "date_to": "WEEK_END"
    },
    "output_format": "PDF",
    "distribution_list": "manager@luckygas.com,sales@luckygas.com",
    "email_subject": "每週銷售報表 - {DATE}",
    "email_body": "請查收本週銷售報表",
    "attach_report": true,
    "compress_attachment": true,
    "active": true
  }

Response:
  {
    "success": true,
    "data": {
      "schedule_id": 123,
      "next_run": "2024-02-05T09:00:00Z"
    }
  }

Errors:
  - 400: Invalid cron expression
  - 409: Schedule conflict
```

### 9. Update Schedule

**PUT /api/v1/reports/schedules/{schedule_id}**
```yaml
Description: Update existing schedule
Path Parameters:
  - schedule_id: integer (required)

Request Body:
  # Same as create, all fields optional

Response:
  {
    "success": true,
    "data": {
      "schedule_id": 123,
      "updated_at": "2024-01-20T10:00:00Z"
    }
  }
```

### 10. Delete Schedule

**DELETE /api/v1/reports/schedules/{schedule_id}**
```yaml
Description: Delete report schedule
Path Parameters:
  - schedule_id: integer (required)

Response:
  {
    "success": true,
    "message": "排程已刪除"
  }
```

### 11. Run Schedule Now

**POST /api/v1/reports/schedules/{schedule_id}/run**
```yaml
Description: Trigger scheduled report immediately
Path Parameters:
  - schedule_id: integer (required)

Response:
  {
    "success": true,
    "data": {
      "execution_id": 123456,
      "status": "queued"
    }
  }
```

## 📊 Dashboard APIs

### 12. List Dashboards

**GET /api/v1/reports/dashboards**
```yaml
Description: Get available dashboards
Parameters:
  - type: string (optional) # executive | operations | sales | custom

Response:
  {
    "success": true,
    "data": {
      "dashboards": [
        {
          "dashboard_id": "DASH001",
          "name": "營運總覽",
          "type": "operations",
          "description": "即時營運數據監控",
          "widgets": 12,
          "refresh_rate": 30,
          "last_accessed": "2024-01-20T09:00:00Z"
        }
      ]
    }
  }
```

### 13. Get Dashboard Data

**GET /api/v1/reports/dashboards/{dashboard_id}**
```yaml
Description: Get dashboard configuration and initial data
Path Parameters:
  - dashboard_id: string (required)

Response:
  {
    "success": true,
    "data": {
      "dashboard_id": "DASH001",
      "layout": {...},
      "widgets": [
        {
          "widget_id": "W001",
          "type": "kpi_card",
          "title": "今日訂單",
          "position": {"x": 0, "y": 0, "w": 3, "h": 2},
          "config": {...},
          "data": {
            "value": 156,
            "change": 12.5,
            "trend": "up"
          }
        }
      ],
      "filters": {...},
      "last_update": "2024-01-20T10:00:00Z"
    }
  }
```

### 14. Dashboard WebSocket Connection

**WS /api/v1/reports/dashboards/{dashboard_id}/stream**
```yaml
Description: Real-time dashboard updates via WebSocket
Path Parameters:
  - dashboard_id: string (required)

Connection:
  const ws = new WebSocket('wss://api.luckygas.com/api/v1/reports/dashboards/DASH001/stream');
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'bearer_token'
  }));

Messages (Server -> Client):
  {
    "type": "widget_update",
    "widget_id": "W001",
    "data": {
      "value": 157,
      "change": 13.2,
      "trend": "up"
    },
    "timestamp": "2024-01-20T10:00:30Z"
  }

  {
    "type": "alert",
    "severity": "warning",
    "message": "庫存不足警告",
    "widget_id": "W005",
    "data": {...}
  }

Messages (Client -> Server):
  {
    "type": "subscribe",
    "widgets": ["W001", "W002", "W003"]
  }

  {
    "type": "filter",
    "filters": {
      "region": "north",
      "date_range": "today"
    }
  }
```

### 15. Export Dashboard

**POST /api/v1/reports/dashboards/{dashboard_id}/export**
```yaml
Description: Export dashboard as PDF or image
Path Parameters:
  - dashboard_id: string (required)

Request Body:
  {
    "format": "PDF", # PDF | PNG | JPEG
    "include_data": true,
    "paper_size": "A4"
  }

Response:
  {
    "success": true,
    "data": {
      "download_url": "/api/v1/reports/download/xyz789",
      "expires_at": "2024-01-21T10:00:00Z"
    }
  }
```

## 🔧 Report Management APIs

### 16. Favorite Reports

**GET /api/v1/reports/favorites**
```yaml
Description: Get user's favorite reports
Response:
  {
    "success": true,
    "data": {
      "favorites": [
        {
          "favorite_id": 1,
          "report_id": "RPT001",
          "report_name": "每日銷售報表",
          "custom_name": "我的銷售報表",
          "saved_parameters": {...},
          "last_accessed": "2024-01-20T09:00:00Z",
          "access_count": 45
        }
      ]
    }
  }
```

**POST /api/v1/reports/favorites**
```yaml
Description: Add report to favorites
Request Body:
  {
    "report_id": "RPT001",
    "custom_name": "我的銷售報表",
    "save_parameters": true,
    "parameters": {...}
  }
```

**DELETE /api/v1/reports/favorites/{favorite_id}**
```yaml
Description: Remove from favorites
```

### 17. Report History

**GET /api/v1/reports/history**
```yaml
Description: Get report execution history
Parameters:
  - report_id: string (optional)
  - date_from: date (optional)
  - date_to: date (optional)
  - status: string (optional)
  - page: integer
  - size: integer

Response:
  {
    "success": true,
    "data": {
      "executions": [
        {
          "execution_id": 123456,
          "report_id": "RPT001",
          "report_name": "每日銷售報表",
          "execution_type": "01",
          "start_time": "2024-01-20T09:00:00Z",
          "duration": 2.5,
          "status": "03",
          "row_count": 1500,
          "download_available": true
        }
      ],
      "pagination": {...}
    }
  }
```

### 18. Report Templates

**GET /api/v1/reports/templates**
```yaml
Description: Get custom report templates
Response:
  {
    "success": true,
    "data": {
      "templates": [
        {
          "template_id": "TPL001",
          "name": "銷售分析模板",
          "description": "標準銷售分析報表模板",
          "preview_url": "/api/v1/reports/templates/TPL001/preview"
        }
      ]
    }
  }
```

### 19. Report Permissions

**GET /api/v1/reports/{report_id}/permissions**
```yaml
Description: Get report access permissions
Response:
  {
    "success": true,
    "data": {
      "report_id": "RPT001",
      "security_level": "02",
      "required_roles": ["MANAGER", "SUPERVISOR"],
      "department_access": ["SALES", "FINANCE"],
      "data_filters": {
        "region": "USER_REGION",
        "customer": "ASSIGNED_CUSTOMERS"
      }
    }
  }
```

### 20. Batch Operations

**POST /api/v1/reports/batch**
```yaml
Description: Execute multiple reports in batch
Request Body:
  {
    "reports": [
      {
        "report_id": "RPT001",
        "parameters": {...},
        "output_format": "PDF"
      },
      {
        "report_id": "RPT002",
        "parameters": {...},
        "output_format": "EXCEL"
      }
    ],
    "delivery_method": "email",
    "combine_files": true,
    "compress": true
  }

Response:
  {
    "success": true,
    "data": {
      "batch_id": "BATCH123",
      "total_reports": 2,
      "status": "processing",
      "status_url": "/api/v1/reports/batch/BATCH123"
    }
  }
```

## 📊 Analytics APIs

### 21. Report Usage Analytics

**GET /api/v1/reports/analytics/usage**
```yaml
Description: Get report usage statistics
Parameters:
  - date_from: date (required)
  - date_to: date (required)
  - group_by: string # report | user | department

Response:
  {
    "success": true,
    "data": {
      "total_executions": 15420,
      "unique_users": 125,
      "popular_reports": [
        {
          "report_id": "RPT001",
          "report_name": "每日銷售報表",
          "executions": 3250,
          "unique_users": 45,
          "avg_duration": 2.3
        }
      ],
      "peak_hours": [
        {"hour": 9, "executions": 1250},
        {"hour": 14, "executions": 980}
      ],
      "format_distribution": {
        "PDF": 45,
        "EXCEL": 30,
        "HTML": 20,
        "CSV": 5
      }
    }
  }
```

### 22. Performance Metrics

**GET /api/v1/reports/analytics/performance**
```yaml
Description: Get report performance metrics
Parameters:
  - report_id: string (optional)
  - date_from: date
  - date_to: date

Response:
  {
    "success": true,
    "data": {
      "avg_generation_time": 3.5,
      "p95_generation_time": 8.2,
      "success_rate": 98.5,
      "timeout_rate": 0.5,
      "cache_hit_rate": 65.2,
      "resource_usage": {
        "avg_memory_mb": 512,
        "avg_cpu_percent": 35
      }
    }
  }
```

## 🛠️ Admin APIs

### 23. Report Configuration

**PUT /api/v1/admin/reports/{report_id}/config**
```yaml
Description: Update report configuration (Admin only)
Request Body:
  {
    "max_rows": 50000,
    "timeout_seconds": 600,
    "cache_duration": 120,
    "security_level": "03",
    "required_roles": ["MANAGER", "DIRECTOR"]
  }

Response:
  {
    "success": true,
    "data": {
      "report_id": "RPT001",
      "updated_at": "2024-01-20T10:00:00Z",
      "updated_by": "ADMIN001"
    }
  }
```

### 24. Clear Report Cache

**POST /api/v1/admin/reports/cache/clear**
```yaml
Description: Clear report cache (Admin only)
Request Body:
  {
    "report_id": "RPT001", # Optional, clears all if not specified
    "older_than": "2024-01-19T00:00:00Z" # Optional
  }

Response:
  {
    "success": true,
    "data": {
      "cleared_entries": 125,
      "freed_space_mb": 2048
    }
  }
```

### 25. Report Queue Management

**GET /api/v1/admin/reports/queue**
```yaml
Description: View report generation queue (Admin only)
Response:
  {
    "success": true,
    "data": {
      "queue_depth": 15,
      "processing": 5,
      "queued": 10,
      "avg_wait_time": 45,
      "reports": [
        {
          "execution_id": 123456,
          "report_id": "RPT001",
          "user_id": "USER001",
          "queued_at": "2024-01-20T10:00:00Z",
          "priority": 5,
          "estimated_start": "2024-01-20T10:02:00Z"
        }
      ]
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
        "date_from": "日期格式錯誤",
        "customer_id": "客戶不存在"
      }
    }
  }

401 Unauthorized:
  {
    "success": false,
    "error": {
      "code": "UNAUTHORIZED",
      "message": "請先登入"
    }
  }

403 Forbidden:
  {
    "success": false,
    "error": {
      "code": "ACCESS_DENIED",
      "message": "您沒有權限存取此報表",
      "required_roles": ["MANAGER"]
    }
  }

404 Not Found:
  {
    "success": false,
    "error": {
      "code": "NOT_FOUND",
      "message": "報表不存在"
    }
  }

429 Too Many Requests:
  {
    "success": false,
    "error": {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "請求過於頻繁",
      "retry_after": 60
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

503 Service Unavailable:
  {
    "success": false,
    "error": {
      "code": "SERVICE_UNAVAILABLE",
      "message": "報表服務暫時無法使用",
      "retry_after": 300
    }
  }
```

## 🔒 Security Headers

All API responses include:
```yaml
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## 📈 Rate Limiting

```yaml
Default Limits:
  - Per user: 100 requests/minute
  - Per IP: 300 requests/minute
  - Report generation: 10 concurrent
  - Large exports: 3 concurrent

Headers:
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1642694400
```