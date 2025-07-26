# Warehouse Management API Endpoints - Lucky Gas Legacy System

## 🔌 API Overview

The Warehouse Management API provides comprehensive endpoints for managing all warehouse operations including receiving, storage, inventory control, order fulfillment, and quality management. All endpoints follow RESTful conventions with JSON request/response formats.

**Base URL**: `/api/v1/warehouse`  
**Authentication**: Bearer token required for all endpoints  
**Content-Type**: `application/json`

## 📥 Receiving Management Endpoints

### Create ASN (Advance Shipment Notice)
```http
POST /receiving/asn
Content-Type: application/json
Authorization: Bearer {token}

{
  "asnNumber": "ASN-2024-001234",
  "supplierId": "SUPP_001",
  "expectedDate": "2024-01-20T10:00:00Z",
  "poNumbers": ["PO-2024-0001", "PO-2024-0002"],
  "items": [
    {
      "productId": "PROD_O2_50L",
      "quantity": 100,
      "lotNumber": "LOT20240120",
      "expiryDate": "2026-01-20"
    }
  ],
  "carrierInfo": {
    "name": "Taiwan Express",
    "vehicleNumber": "TPE-1234",
    "driverName": "王大明"
  },
  "specialInstructions": "Temperature sensitive - store immediately"
}

Response: 201 Created
{
  "success": true,
  "data": {
    "asnId": "ASN_ID_12345",
    "status": "SCHEDULED",
    "dockAssignment": "DOCK_02",
    "scheduledTime": "2024-01-20T10:00:00Z"
  }
}
```

### Get Receiving Schedule
```http
GET /receiving/schedule?date=2024-01-20&warehouse=WH001
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": [
    {
      "receivingId": "REC_2024_001",
      "asnNumber": "ASN-2024-001234",
      "supplier": "Industrial Gas Co.",
      "scheduledTime": "10:00",
      "dockDoor": "DOCK_02",
      "status": "SCHEDULED",
      "totalPallets": 5,
      "totalUnits": 100
    }
  ],
  "pagination": {
    "total": 15,
    "page": 1,
    "pageSize": 20
  }
}
```

### Start Receiving Process
```http
POST /receiving/{receivingId}/start
Authorization: Bearer {token}

{
  "actualArrivalTime": "2024-01-20T09:55:00Z",
  "driverCheckIn": {
    "driverId": "D123456",
    "vehiclePlate": "TPE-1234",
    "sealNumber": "SEAL001"
  }
}

Response: 200 OK
{
  "success": true,
  "data": {
    "receivingId": "REC_2024_001",
    "status": "IN_PROGRESS",
    "startTime": "2024-01-20T10:00:00Z",
    "assignedStaff": ["USER_001", "USER_002"]
  }
}
```

### Record Receipt Line
```http
POST /receiving/{receivingId}/items
Authorization: Bearer {token}

{
  "productId": "PROD_O2_50L",
  "serialNumbers": ["SN001", "SN002", "SN003"],
  "quantity": 3,
  "condition": "GOOD",
  "qualityCheckRequired": true,
  "location": "RECEIVING_01"
}

Response: 201 Created
{
  "success": true,
  "data": {
    "lineId": "LINE_001",
    "quantityReceived": 3,
    "quantityPending": 97,
    "qualityTasks": ["QC_TASK_001"]
  }
}
```

### Complete Receiving
```http
POST /receiving/{receivingId}/complete
Authorization: Bearer {token}

{
  "endTime": "2024-01-20T11:30:00Z",
  "summary": {
    "totalReceived": 98,
    "totalDamaged": 2,
    "totalRejected": 0
  },
  "discrepancies": [
    {
      "type": "DAMAGE",
      "productId": "PROD_O2_50L",
      "quantity": 2,
      "notes": "Valve damage on 2 cylinders"
    }
  ]
}

Response: 200 OK
{
  "success": true,
  "data": {
    "receivingId": "REC_2024_001",
    "status": "COMPLETED",
    "putawayTasks": ["PUT_001", "PUT_002"],
    "qualityTasks": ["QC_001", "QC_002"]
  }
}
```

## 🏪 Storage Management Endpoints

### Create Storage Location
```http
POST /locations
Authorization: Bearer {token}

{
  "locationCode": "A-01-02-03",
  "warehouseId": "WH001",
  "zone": "A",
  "aisle": "01",
  "rack": "02",
  "level": "03",
  "locationType": "STORAGE",
  "dimensions": {
    "length": 2.5,
    "width": 1.5,
    "height": 2.0
  },
  "capacity": {
    "maxCylinders": 12,
    "maxWeight": 1000
  },
  "attributes": {
    "temperatureControlled": false,
    "hazmatCertified": false,
    "velocityCategory": "A"
  }
}

Response: 201 Created
{
  "success": true,
  "data": {
    "locationId": "LOC_12345",
    "barcode": "LOC-A010203",
    "status": "ACTIVE"
  }
}
```

### Get Location Availability
```http
GET /locations/availability?zone=A&productType=MEDICAL
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": [
    {
      "locationId": "LOC_12345",
      "locationCode": "A-01-02-03",
      "availableCapacity": 8,
      "currentOccupancy": 4,
      "percentUsed": 33.3,
      "compatible": true
    }
  ]
}
```

### Execute Putaway
```http
POST /putaway
Authorization: Bearer {token}

{
  "taskId": "PUT_001",
  "movements": [
    {
      "productId": "PROD_O2_50L",
      "serialNumber": "SN001",
      "fromLocation": "RECEIVING_01",
      "toLocation": "A-01-02-03",
      "quantity": 1
    }
  ],
  "completedBy": "USER_001",
  "completionTime": "2024-01-20T12:00:00Z"
}

Response: 200 OK
{
  "success": true,
  "data": {
    "taskId": "PUT_001",
    "status": "COMPLETED",
    "movementsProcessed": 1,
    "inventoryUpdated": true
  }
}
```

### Optimize Slotting
```http
POST /locations/slotting/optimize
Authorization: Bearer {token}

{
  "zone": "A",
  "optimizationCriteria": {
    "velocityBased": true,
    "minimizeTravel": true,
    "consolidateSKUs": true
  },
  "simulationOnly": true
}

Response: 200 OK
{
  "success": true,
  "data": {
    "currentEfficiency": 72.5,
    "projectedEfficiency": 85.3,
    "recommendedMoves": 45,
    "estimatedHours": 6,
    "savings": {
      "travelReduction": "23%",
      "pickingTime": "18%"
    }
  }
}
```

## 📊 Inventory Control Endpoints

### Get Inventory Status
```http
GET /inventory?location=A-01-02-03&status=AVAILABLE
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": [
    {
      "inventoryId": "INV_12345",
      "productId": "PROD_O2_50L",
      "serialNumber": "SN001",
      "location": "A-01-02-03",
      "quantity": 1,
      "status": "AVAILABLE",
      "qualityStatus": "GOOD",
      "ownership": "OWNED",
      "expiryDate": "2026-01-20",
      "lastMovement": "2024-01-20T12:00:00Z"
    }
  ]
}
```

### Create Inventory Adjustment
```http
POST /inventory/adjustments
Authorization: Bearer {token}

{
  "adjustmentType": "COUNT_VARIANCE",
  "location": "A-01-02-03",
  "productId": "PROD_O2_50L",
  "systemQuantity": 10,
  "actualQuantity": 9,
  "variance": -1,
  "reason": "Physical count discrepancy",
  "countedBy": "USER_003",
  "approvalRequired": false
}

Response: 201 Created
{
  "success": true,
  "data": {
    "adjustmentId": "ADJ_2024_001",
    "status": "APPROVED",
    "postedDate": "2024-01-20T14:00:00Z",
    "inventoryUpdated": true
  }
}
```

### Transfer Inventory
```http
POST /inventory/transfers
Authorization: Bearer {token}

{
  "transferType": "LOCATION",
  "items": [
    {
      "inventoryId": "INV_12345",
      "fromLocation": "A-01-02-03",
      "toLocation": "B-05-01-02",
      "quantity": 1,
      "reason": "CONSOLIDATION"
    }
  ],
  "priority": "NORMAL",
  "scheduledDate": "2024-01-20T15:00:00Z"
}

Response: 201 Created
{
  "success": true,
  "data": {
    "transferId": "TRANS_2024_001",
    "taskId": "TASK_MOVE_001",
    "status": "PENDING"
  }
}
```

### Update Inventory Status
```http
PUT /inventory/{inventoryId}/status
Authorization: Bearer {token}

{
  "newStatus": "HOLD",
  "reason": "QUALITY_INSPECTION",
  "holdType": "QUALITY_HOLD",
  "expectedReleaseDate": "2024-01-22",
  "notes": "Pending pressure test results"
}

Response: 200 OK
{
  "success": true,
  "data": {
    "inventoryId": "INV_12345",
    "previousStatus": "AVAILABLE",
    "currentStatus": "HOLD",
    "statusChangeId": "SC_2024_001"
  }
}
```

## 📤 Order Fulfillment Endpoints

### Create Pick Wave
```http
POST /picking/waves
Authorization: Bearer {token}

{
  "waveType": "DELIVERY_ROUTE",
  "criteria": {
    "deliveryDate": "2024-01-21",
    "routes": ["ROUTE_01", "ROUTE_02"],
    "customerTypes": ["HOSPITAL", "INDUSTRIAL"]
  },
  "optimization": {
    "minimizeTravel": true,
    "balanceWorkload": true,
    "consolidateZones": true
  }
}

Response: 201 Created
{
  "success": true,
  "data": {
    "waveId": "WAVE_2024_001",
    "ordersIncluded": 25,
    "totalLines": 150,
    "totalUnits": 300,
    "estimatedTime": 180,
    "pickLists": ["PICK_001", "PICK_002", "PICK_003"]
  }
}
```

### Get Pick List
```http
GET /picking/lists/{pickListId}
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "pickListId": "PICK_001",
    "assignedTo": "USER_004",
    "zone": "A",
    "status": "IN_PROGRESS",
    "items": [
      {
        "lineId": "LINE_001",
        "orderId": "ORD_2024_001",
        "productId": "PROD_O2_50L",
        "location": "A-01-02-03",
        "quantity": 2,
        "picked": 0,
        "serialNumbers": []
      }
    ],
    "startTime": "2024-01-21T08:00:00Z"
  }
}
```

### Confirm Pick
```http
POST /picking/confirm
Authorization: Bearer {token}

{
  "pickListId": "PICK_001",
  "lineId": "LINE_001",
  "location": "A-01-02-03",
  "serialNumbers": ["SN001", "SN002"],
  "quantity": 2,
  "confirmationMethod": "SCAN",
  "timestamp": "2024-01-21T08:15:00Z"
}

Response: 200 OK
{
  "success": true,
  "data": {
    "lineId": "LINE_001",
    "status": "PICKED",
    "remaining": 0,
    "nextLocation": "A-02-01-01"
  }
}
```

### Complete Packing
```http
POST /packing/{orderId}/complete
Authorization: Bearer {token}

{
  "packageDetails": [
    {
      "packageId": "PKG_001",
      "packageType": "PALLET",
      "items": ["SN001", "SN002", "SN003"],
      "weight": 150.5,
      "dimensions": {
        "length": 1.2,
        "width": 1.0,
        "height": 1.8
      }
    }
  ],
  "sealNumber": "SEAL12345",
  "qualityChecked": true,
  "readyForShipping": true
}

Response: 200 OK
{
  "success": true,
  "data": {
    "orderId": "ORD_2024_001",
    "status": "PACKED",
    "shipmentId": "SHIP_2024_001",
    "labels": ["url_to_shipping_label"],
    "stagingLocation": "STAGING_01"
  }
}
```

## 🔍 Quality Control Endpoints

### Create Quality Inspection
```http
POST /quality/inspections
Authorization: Bearer {token}

{
  "inspectionType": "RECEIVING",
  "referenceType": "RECEIVING",
  "referenceId": "REC_2024_001",
  "items": [
    {
      "productId": "PROD_O2_50L",
      "serialNumber": "SN001",
      "location": "QC_AREA_01"
    }
  ],
  "inspectorId": "QC_USER_001",
  "priority": "HIGH"
}

Response: 201 Created
{
  "success": true,
  "data": {
    "inspectionId": "QC_2024_001",
    "status": "PENDING",
    "scheduledTime": "2024-01-20T14:00:00Z",
    "checklistId": "CHECKLIST_CYLINDER"
  }
}
```

### Record Inspection Results
```http
PUT /quality/inspections/{inspectionId}/results
Authorization: Bearer {token}

{
  "serialNumber": "SN001",
  "checkResults": {
    "visualInspection": "PASS",
    "pressureTest": "PASS",
    "valveCheck": "PASS",
    "weightCheck": "PASS",
    "certificationCheck": "PASS"
  },
  "overallResult": "PASS",
  "measurements": {
    "pressure": 2000,
    "weight": 50.2,
    "testDate": "2024-01-20"
  },
  "photos": ["photo_url_1", "photo_url_2"],
  "notes": "All checks passed, minor cosmetic scratches noted"
}

Response: 200 OK
{
  "success": true,
  "data": {
    "inspectionId": "QC_2024_001",
    "result": "PASS",
    "qualityStatus": "GOOD",
    "nextInspectionDate": "2025-01-20"
  }
}
```

### Quarantine Product
```http
POST /quality/quarantine
Authorization: Bearer {token}

{
  "reason": "FAILED_INSPECTION",
  "items": [
    {
      "inventoryId": "INV_12346",
      "serialNumber": "SN003",
      "currentLocation": "A-01-02-04",
      "defectCodes": ["VALVE_LEAK", "PRESSURE_FAIL"]
    }
  ],
  "severity": "CRITICAL",
  "immediateAction": "ISOLATE",
  "notifySupplier": true
}

Response: 201 Created
{
  "success": true,
  "data": {
    "quarantineId": "QUAR_2024_001",
    "quarantineLocation": "Q-01-01",
    "status": "QUARANTINED",
    "investigationId": "INV_2024_001",
    "supplierNotified": true
  }
}
```

## 📈 Analytics and Reporting Endpoints

### Get Warehouse Performance Metrics
```http
GET /analytics/performance?startDate=2024-01-01&endDate=2024-01-31
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "period": "2024-01",
    "metrics": {
      "receiving": {
        "totalReceipts": 150,
        "onTimeRate": 92.5,
        "accuracyRate": 99.2,
        "avgProcessTime": 2.5
      },
      "inventory": {
        "accuracy": 99.8,
        "turnoverRate": 12.5,
        "stockouts": 3,
        "utilizationRate": 87.5
      },
      "picking": {
        "ordersProcessed": 1250,
        "pickAccuracy": 99.7,
        "avgPicksPerHour": 62,
        "onTimeShipment": 96.8
      },
      "quality": {
        "inspectionCount": 450,
        "passRate": 98.5,
        "defectRate": 1.5,
        "supplierScorecard": {
          "SUPP_001": 99.2,
          "SUPP_002": 97.8
        }
      }
    }
  }
}
```

### Get Space Utilization Report
```http
GET /analytics/space-utilization?warehouse=WH001
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "warehouse": "WH001",
    "totalLocations": 2000,
    "metrics": {
      "occupancyRate": 85.5,
      "honeycombingRate": 5.2,
      "byZone": {
        "A": { "occupancy": 92.0, "efficiency": 88.5 },
        "B": { "occupancy": 78.5, "efficiency": 82.0 },
        "C": { "occupancy": 65.0, "efficiency": 90.0 }
      },
      "topProducts": [
        {
          "productId": "PROD_O2_50L",
          "locations": 125,
          "volume": 2500
        }
      ]
    }
  }
}
```

### Generate Cycle Count Plan
```http
POST /cycle-count/generate-plan
Authorization: Bearer {token}

{
  "method": "ABC_BASED",
  "criteria": {
    "aItems": { "frequency": "WEEKLY", "coverage": 100 },
    "bItems": { "frequency": "MONTHLY", "coverage": 25 },
    "cItems": { "frequency": "QUARTERLY", "coverage": 10 }
  },
  "excludeLocations": ["RECEIVING", "SHIPPING"],
  "startDate": "2024-02-01"
}

Response: 201 Created
{
  "success": true,
  "data": {
    "planId": "CC_PLAN_2024_02",
    "totalCounts": 450,
    "schedule": [
      {
        "date": "2024-02-01",
        "locations": 50,
        "estimatedHours": 2
      }
    ]
  }
}
```

## 🚨 Error Response Format

All error responses follow a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "WH_ERR_001",
    "message": "Location not found",
    "details": "Location A-99-99-99 does not exist",
    "timestamp": "2024-01-20T10:00:00Z",
    "requestId": "req_12345"
  }
}
```

### Common Error Codes
- `WH_ERR_001`: Location not found
- `WH_ERR_002`: Insufficient inventory
- `WH_ERR_003`: Invalid serial number
- `WH_ERR_004`: Capacity exceeded
- `WH_ERR_005`: Quality check failed
- `WH_ERR_006`: Authorization denied
- `WH_ERR_007`: Invalid status transition
- `WH_ERR_008`: Duplicate serial number
- `WH_ERR_009`: Location incompatible
- `WH_ERR_010`: Task already completed