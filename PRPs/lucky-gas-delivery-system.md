name: "Lucky Gas Delivery Management System - Comprehensive Implementation PRP"
description: |

## Purpose
Implementation blueprint for building a comprehensive gas delivery management system for Lucky Gas (幸福氣) in Taiwan, featuring predictive AI, route optimization, and real-time tracking with full-stack modern web architecture.

## Core Principles
1. **Cloud-Native First**: Leverage Google Cloud Platform services for superior AI/ML capabilities
2. **Frontend-First Development**: Build accessible web interfaces early to minimize CLI dependency
3. **Taiwan-Specific Design**: Traditional Chinese UI with local formats and conventions
4. **Data-Driven Architecture**: Use existing historical data for ML training and insights
5. **Production-Ready Code**: Enterprise-grade security, scalability, and maintainability

---

## Goal
Build a comprehensive web-based gas delivery management system that:
- Predicts customer gas needs using Google Vertex AI AutoML
- Optimizes delivery routes using Google Maps Routes API
- Provides real-time tracking and multi-role access control
- Supports office staff, drivers, managers, and customers
- Includes web-based database management interface
- Achieves 80%+ prediction accuracy and 20% route efficiency improvement

## Why
- **Business Value**: Reduce operational costs through optimized routes and predictive ordering
- **Customer Satisfaction**: Ensure customers never run out of gas with proactive deliveries
- **Driver Efficiency**: Provide mobile-friendly interfaces with optimized routes
- **Data Insights**: Transform existing Excel/SQLite data into actionable predictions
- **Scalability**: Support 100+ concurrent users with 99.9% uptime

## What
### User-Visible Features
1. **Admin Dashboard**: Real-time monitoring, user management, system configuration
2. **Office Portal**: Order management, customer database, route planning (Traditional Chinese)
3. **Driver Mobile App**: Route navigation, delivery updates, photo proof of delivery
4. **Customer Portal**: Order tracking, delivery history, consumption insights
5. **Database Management**: Web-based viewer/editor for direct data access

### Technical Requirements
- FastAPI backend with async/await, JWT authentication, WebSocket support
- React + TypeScript frontend with Material-UI/Ant Design
- PostgreSQL + Redis for data storage and caching
- Google Cloud integration (Vertex AI, Maps, Cloud SQL)
- Traditional Chinese localization throughout

### Success Criteria
- [ ] Import all existing Excel/SQLite data successfully
- [ ] Achieve 80%+ accuracy in gas demand predictions
- [ ] Reduce delivery route time by 20% through optimization
- [ ] Support 10+ concurrent users with <100ms API response
- [ ] Complete Traditional Chinese localization
- [ ] Mobile-responsive driver interface works on all devices
- [ ] All 5 user roles have appropriate access controls

## All Needed Context

### Documentation & References
```yaml
# Google Cloud Services
- url: https://cloud.google.com/vertex-ai/docs/tabular-data/forecasting/overview
  why: Vertex AI AutoML for demand prediction - time series forecasting
  
- url: https://github.com/GoogleCloudPlatform/vertex-ai-samples/blob/main/notebooks/official/automl/sdk_automl_tabular_forecasting_batch.ipynb
  why: Complete example of AutoML tabular forecasting with batch prediction
  
- url: https://developers.google.com/maps/documentation/routes/opt-way
  why: Routes API waypoint optimization for delivery routes
  
- url: https://googleapis.dev/python/google-maps-routeoptimization/latest/
  why: Python client for Google Maps Route Optimization API

# FastAPI + React Architecture
- url: https://testdriven.io/blog/fastapi-jwt-auth/
  why: JWT authentication implementation with FastAPI
  
- url: https://christophergs.com/tutorials/ultimate-fastapi-tutorial-pt-12-react-js-frontend/
  why: FastAPI + React integration patterns
  
- url: https://github.com/CynthiaWahome/fastapi-react-integration
  why: Complete example of FastAPI + React with JWT auth

# UI Libraries
- url: https://ant.design/components/overview
  why: Ant Design components with excellent i18n support for Traditional Chinese
  
- url: https://mui.com/material-ui/react-autocomplete/#country-select
  why: Material-UI components for Taiwan address/region selection

# WebSocket & Real-time
- url: https://fastapi.tiangolo.com/advanced/websockets/
  why: FastAPI WebSocket implementation for real-time updates
```

### Current Codebase Structure
```bash
luckygas-v3/
├── raw/                        # Existing data files
│   ├── 2025-05 client liss.xlsx    # 1,267 customers with 76 columns
│   ├── 2025-05 deliver history.xlsx # 349,920 delivery records
│   └── luckygas.db                 # SQLite with 6 tables
├── PRPs/                      # Project requirement prompts
├── CLAUDE.md                  # AI assistant rules
└── pyproject.toml            # Python project config
```

### Desired Codebase Structure
```bash
luckygas-v3/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py          # JWT authentication endpoints
│   │   │   │   ├── customers.py     # Customer CRUD operations
│   │   │   │   ├── orders.py        # Order management
│   │   │   │   ├── routes.py        # Route optimization endpoints
│   │   │   │   ├── predictions.py   # AI prediction endpoints
│   │   │   │   └── websocket.py     # Real-time updates
│   │   │   └── deps.py              # Dependencies (auth, db)
│   │   ├── core/
│   │   │   ├── config.py            # Settings management
│   │   │   ├── security.py          # Password hashing, JWT
│   │   │   └── database.py          # Database connection
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── customer.py
│   │   │   ├── order.py
│   │   │   ├── delivery.py
│   │   │   ├── route.py
│   │   │   └── user.py
│   │   ├── schemas/                 # Pydantic schemas
│   │   │   └── [matching models]
│   │   ├── services/                # Business logic
│   │   │   ├── google_cloud/
│   │   │   │   ├── vertex_ai.py    # Demand prediction
│   │   │   │   └── maps.py         # Route optimization
│   │   │   ├── prediction.py       # Prediction logic
│   │   │   └── notification.py     # WebSocket notifications
│   │   └── utils/
│   │       ├── taiwan.py           # Taiwan-specific formatting
│   │       └── validators.py       # Input validation
│   ├── alembic/                    # Database migrations
│   ├── tests/                      # pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/             # Shared components
│   │   │   ├── dashboard/          # Admin dashboard
│   │   │   ├── office/             # Office portal
│   │   │   ├── driver/             # Driver interface
│   │   │   └── customer/           # Customer portal
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx     # Authentication state
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── services/               # API integration
│   │   │   ├── api.ts              # Axios setup
│   │   │   └── websocket.ts       # WebSocket client
│   │   ├── locales/                # i18n translations
│   │   │   └── zh-TW.json          # Traditional Chinese
│   │   └── utils/
│   │       └── taiwan.ts           # Taiwan formatting
│   ├── public/
│   └── package.json
├── database/
│   ├── migrations/                 # Data migration scripts
│   │   ├── 001_import_excel.py     # Excel → PostgreSQL
│   │   └── 002_import_sqlite.py    # SQLite → PostgreSQL
│   └── web-viewer/                 # Database management UI
│       └── index.html              # Adminer or custom
└── docs/                          # Documentation
```

### Existing Data Structures
```python
# Excel: Client List (1,267 rows, 76 columns)
CLIENT_COLUMNS = [
    '客戶', '電子發票抬頭', '客戶簡稱', '地址',
    '50KG', '20KG', '16KG', '10KG', '4KG',  # Cylinder types
    '計價方式', '結帳方式', '區域',
    '8~9', '9~10', ..., '19~20',  # Delivery time slots
    '平均日使用', '最大週期', '可延後天數'
]

# Excel: Delivery History (349,920 rows)
DELIVERY_COLUMNS = ['客戶', '電子發票抬頭', '客戶簡稱', '地址', '最後十次日期']

# SQLite Tables
TABLES = [
    'clients',             # 72 columns matching Excel
    'drivers',             # Driver info and licenses
    'vehicles',            # Vehicle capacity info
    'deliveries',          # Historical deliveries
    'routes',              # Route planning data
    'delivery_predictions' # AI prediction results
]
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Google Cloud Authentication
# Must set GOOGLE_APPLICATION_CREDENTIALS env var to service account JSON
# OR use google.auth.default() with proper IAM roles

# CRITICAL: Vertex AI Batch Prediction Only
# AutoML forecasting doesn't support online predictions
# Must use batch prediction for demand forecasting

# CRITICAL: Taiwan Address Format
# Addresses use Traditional Chinese with specific format:
# 郵遞區號 + 縣市 + 區/鄉/鎮 + 路/街 + 號
# Example: "950 臺東市中興路三段320號"

# CRITICAL: JWT Token Storage
# Store in httpOnly cookies for security, not localStorage
# Implement refresh token rotation

# CRITICAL: WebSocket Connection Management
# FastAPI WebSockets require proper connection lifecycle
# Implement reconnection logic in React client

# CRITICAL: Pydantic v2 Validation
# Use field_validator instead of validator
# ConfigDict instead of Config class
```

## Implementation Blueprint

### Phase 1: Foundation Setup (Week 1-2)

#### Task 1: Initialize Project Structure
```yaml
CREATE backend/ directory structure:
  - Use cookiecutter or manual setup
  - Initialize with uv: uv init
  - Add dependencies: fastapi, sqlalchemy, pydantic, etc.

CREATE frontend/ directory:
  - npx create-react-app frontend --template typescript
  - Install dependencies: antd, axios, react-router-dom, i18next
  - Configure TypeScript strict mode

CREATE database/web-viewer/:
  - Download Adminer PHP file
  - Create docker-compose for easy setup
```

#### Task 2: Database Design and Setup
```python
# backend/app/models/customer.py
class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True)
    customer_code = Column(String(20), unique=True, index=True)
    invoice_title = Column(String(200))
    short_name = Column(String(100))
    address = Column(String(500))
    
    # Cylinder inventory
    cylinders_50kg = Column(Integer, default=0)
    cylinders_20kg = Column(Integer, default=0)
    cylinders_16kg = Column(Integer, default=0)
    
    # Delivery preferences
    delivery_time_start = Column(String(5))  # "08:00"
    delivery_time_end = Column(String(5))    # "09:00"
    area = Column(String(50))
    
    # Consumption data
    avg_daily_usage = Column(Float)
    max_cycle_days = Column(Integer)
    can_delay_days = Column(Integer)
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    predictions = relationship("DeliveryPrediction", back_populates="customer")
```

#### Task 3: Data Migration Scripts
```python
# database/migrations/001_import_excel.py
import pandas as pd
from sqlalchemy.orm import Session
from app.models import Customer
from app.core.database import engine

def import_customers():
    # Read Excel with proper encoding for Chinese
    df = pd.read_excel('raw/2025-05 client liss.xlsx')
    
    # Data validation and transformation
    customers = []
    for _, row in df.iterrows():
        # Map Excel columns to model fields
        customer = Customer(
            customer_code=str(row['客戶']),
            invoice_title=row['電子發票抬頭'],
            short_name=row['客戶簡稱'],
            address=row['地址'],
            # ... map all fields
        )
        customers.append(customer)
    
    # Bulk insert with error handling
    with Session(engine) as session:
        session.bulk_save_objects(customers)
        session.commit()
```

#### Task 4: Authentication System
```python
# backend/app/core/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, role: str):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "role": role})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# backend/app/api/v1/auth.py
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    access_token = create_access_token(
        data={"sub": user.username},
        role=user.role
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

### Phase 2: Core Features (Week 3-4)

#### Task 5: Customer Management API
```python
# backend/app/api/v1/customers.py
@router.get("/", response_model=List[CustomerSchema])
async def get_customers(
    skip: int = 0,
    limit: int = 100,
    area: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check permissions
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    query = db.query(Customer)
    if area:
        query = query.filter(Customer.area == area)
    
    return query.offset(skip).limit(limit).all()
```

#### Task 6: React Frontend Setup
```typescript
// frontend/src/contexts/AuthContext.tsx
interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

export const AuthProvider: React.FC = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  
  const login = async (username: string, password: string) => {
    const response = await api.post('/auth/login', { username, password });
    const { access_token } = response.data;
    
    // Store token securely
    localStorage.setItem('token', access_token);
    api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    
    // Decode token to get user info
    const decoded = jwt_decode(access_token) as JWTPayload;
    setUser({ username: decoded.sub, role: decoded.role });
  };
  
  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};
```

#### Task 7: Office Portal UI
```typescript
// frontend/src/components/office/CustomerList.tsx
import { Table, Button, Space, Input } from 'antd';
import { useTranslation } from 'react-i18next';

const CustomerList: React.FC = () => {
  const { t } = useTranslation();
  const [customers, setCustomers] = useState<Customer[]>([]);
  
  const columns = [
    {
      title: t('customer.code'),
      dataIndex: 'customer_code',
      key: 'customer_code',
    },
    {
      title: t('customer.name'),
      dataIndex: 'short_name',
      key: 'short_name',
    },
    {
      title: t('customer.address'),
      dataIndex: 'address',
      key: 'address',
      ellipsis: true,
    },
    {
      title: t('actions'),
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button type="link">{t('edit')}</Button>
          <Button type="link">{t('view')}</Button>
        </Space>
      ),
    },
  ];
  
  return (
    <div>
      <Table 
        columns={columns} 
        dataSource={customers}
        pagination={{ pageSize: 20 }}
        locale={{ emptyText: t('no_data') }}
      />
    </div>
  );
};
```

### Phase 3: Advanced Features (Week 5-6)

#### Task 8: Google Vertex AI Integration
```python
# backend/app/services/google_cloud/vertex_ai.py
from google.cloud import aiplatform
from google.cloud.aiplatform import TabularDataset, AutoMLTabularTrainingJob

class DemandPredictionService:
    def __init__(self):
        aiplatform.init(
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION
        )
    
    async def train_demand_model(self):
        # Create dataset from historical data
        dataset = TabularDataset.create(
            display_name="lucky_gas_demand",
            gcs_source="gs://your-bucket/training-data.csv"
        )
        
        # Configure AutoML training
        job = AutoMLTabularTrainingJob(
            display_name="demand_prediction_model",
            optimization_prediction_type="regression",
            optimization_objective="minimize-mae"  # Resilient to outliers
        )
        
        # Train model
        model = job.run(
            dataset=dataset,
            target_column="next_order_days",
            training_fraction_split=0.8,
            validation_fraction_split=0.1,
            test_fraction_split=0.1,
            model_display_name="demand_predictor_v1",
            disable_early_stopping=False,
        )
        
        return model
    
    async def predict_demand_batch(self):
        # Load trained model
        model = aiplatform.Model(model_name=settings.VERTEX_MODEL_ID)
        
        # Prepare batch prediction data
        customers = await self.get_active_customers()
        prediction_data = self.prepare_prediction_features(customers)
        
        # Run batch prediction
        batch_prediction_job = model.batch_predict(
            job_display_name="daily_demand_prediction",
            gcs_source="gs://your-bucket/prediction-input.jsonl",
            gcs_destination_prefix="gs://your-bucket/predictions/",
            machine_type="n1-standard-4",
        )
        
        # Process results
        await self.process_prediction_results(batch_prediction_job)
```

#### Task 9: Google Maps Route Optimization
```python
# backend/app/services/google_cloud/maps.py
from google.maps import routeoptimization_v1
from typing import List, Dict

class RouteOptimizationService:
    def __init__(self):
        self.client = routeoptimization_v1.RouteOptimizationClient()
    
    async def optimize_delivery_routes(
        self,
        deliveries: List[Delivery],
        vehicles: List[Vehicle]
    ) -> Dict:
        # Build shipments from deliveries
        shipments = []
        for delivery in deliveries:
            shipment = routeoptimization_v1.Shipment(
                deliveries=[routeoptimization_v1.VisitRequest(
                    arrival_location=routeoptimization_v1.LatLng(
                        latitude=delivery.latitude,
                        longitude=delivery.longitude
                    ),
                    time_windows=[routeoptimization_v1.TimeWindow(
                        start_time=delivery.time_window_start,
                        end_time=delivery.time_window_end
                    )],
                    duration=delivery.estimated_duration
                )]
            )
            shipments.append(shipment)
        
        # Configure vehicles
        vehicle_configs = []
        for vehicle in vehicles:
            config = routeoptimization_v1.Vehicle(
                start_location=routeoptimization_v1.LatLng(
                    latitude=settings.DEPOT_LAT,
                    longitude=settings.DEPOT_LNG
                ),
                end_location=routeoptimization_v1.LatLng(
                    latitude=settings.DEPOT_LAT,
                    longitude=settings.DEPOT_LNG
                ),
                capacities=[routeoptimization_v1.Vehicle.LoadLimit(
                    max_load=vehicle.max_cylinders_total
                )]
            )
            vehicle_configs.append(config)
        
        # Create optimization request
        request = routeoptimization_v1.OptimizeToursRequest(
            parent=f"projects/{settings.GCP_PROJECT_ID}",
            model=routeoptimization_v1.ShipmentModel(
                shipments=shipments,
                vehicles=vehicle_configs,
                global_duration_cost_per_hour=settings.DRIVER_COST_PER_HOUR
            ),
            solving_mode="DEFAULT_SOLVE"
        )
        
        # Execute optimization
        response = await self.client.optimize_tours(request=request)
        return self.format_optimized_routes(response)
```

#### Task 10: WebSocket Real-time Updates
```python
# backend/app/api/v1/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "admin": set(),
            "office": set(),
            "driver": set(),
            "customer": set()
        }
    
    async def connect(self, websocket: WebSocket, role: str, user_id: str):
        await websocket.accept()
        self.active_connections[role].add(websocket)
    
    async def broadcast_to_role(self, message: dict, role: str):
        for connection in self.active_connections[role]:
            try:
                await connection.send_json(message)
            except:
                # Remove dead connections
                self.active_connections[role].remove(connection)

manager = ConnectionManager()

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Validate token and get user
    user = await validate_ws_token(token)
    if not user:
        await websocket.close(code=1008)
        return
    
    await manager.connect(websocket, user.role, user.id)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            # Handle different message types
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.role)
```

#### Task 11: Driver Mobile Interface
```typescript
// frontend/src/components/driver/RouteNavigation.tsx
import { useState, useEffect } from 'react';
import { List, Card, Button, Steps, message } from 'antd';
import { CheckOutlined, EnvironmentOutlined } from '@ant-design/icons';

const RouteNavigation: React.FC = () => {
  const [route, setRoute] = useState<Route | null>(null);
  const [currentStop, setCurrentStop] = useState(0);
  const [ws, setWs] = useState<WebSocket | null>(null);
  
  // WebSocket connection for real-time updates
  useEffect(() => {
    const token = localStorage.getItem('token');
    const websocket = new WebSocket(`ws://localhost:8000/ws/${token}`);
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'route_update') {
        setRoute(data.route);
      }
    };
    
    setWs(websocket);
    return () => websocket.close();
  }, []);
  
  const completeDelivery = async (stopIndex: number) => {
    const stop = route?.stops[stopIndex];
    if (!stop) return;
    
    // Update delivery status
    await api.post(`/deliveries/${stop.delivery_id}/complete`, {
      proof_photo: await capturePhoto(),
      notes: ''
    });
    
    // Send real-time update
    ws?.send(JSON.stringify({
      type: 'delivery_completed',
      delivery_id: stop.delivery_id
    }));
    
    message.success('配送完成！');
    setCurrentStop(currentStop + 1);
  };
  
  return (
    <div className="driver-route-nav">
      <Steps current={currentStop} direction="vertical">
        {route?.stops.map((stop, index) => (
          <Steps.Step
            key={stop.id}
            title={stop.customer_name}
            description={
              <Card size="small">
                <p><EnvironmentOutlined /> {stop.address}</p>
                <p>📦 {stop.cylinders_50kg}x50kg, {stop.cylinders_20kg}x20kg</p>
                <p>⏰ {stop.time_window}</p>
                {index === currentStop && (
                  <Button 
                    type="primary" 
                    icon={<CheckOutlined />}
                    onClick={() => completeDelivery(index)}
                  >
                    完成配送
                  </Button>
                )}
              </Card>
            }
            status={index < currentStop ? 'finish' : index === currentStop ? 'process' : 'wait'}
          />
        ))}
      </Steps>
    </div>
  );
};
```

### Phase 4: Polish & Deploy (Week 7-8)

#### Task 12: Performance Optimization
```python
# backend/app/core/cache.py
import redis
from functools import wraps
import json

redis_client = redis.from_url(settings.REDIS_URL)

def cache_result(expire_time=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and args
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            redis_client.setex(
                cache_key,
                expire_time,
                json.dumps(result, ensure_ascii=False)
            )
            return result
        return wrapper
    return decorator

# Use in predictions
@cache_result(expire_time=86400)  # Cache for 24 hours
async def get_daily_predictions():
    return await prediction_service.get_today_predictions()
```

#### Task 13: Comprehensive Testing
```python
# backend/tests/test_predictions.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_prediction_generation():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as manager
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "manager@luckygas.tw", "password": "test123"}
        )
        token = login_response.json()["access_token"]
        
        # Trigger prediction generation
        response = await client.post(
            "/api/v1/predictions/generate",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "predictions_count" in data
        assert data["predictions_count"] > 0

@pytest.mark.asyncio
async def test_taiwan_address_validation():
    from app.utils.taiwan import validate_taiwan_address
    
    # Valid addresses
    assert validate_taiwan_address("950 臺東市中興路三段320號")
    assert validate_taiwan_address("100 臺北市中正區重慶南路一段122號")
    
    # Invalid addresses
    assert not validate_taiwan_address("Invalid address")
    assert not validate_taiwan_address("")
```

#### Task 14: Deployment Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/luckygas
      - REDIS_URL=redis://redis:6379
      - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
    volumes:
      - ./service-account.json:/app/service-account.json:ro
    depends_on:
      - db
      - redis
    ports:
      - "8000:8000"
  
  frontend:
    build: ./frontend
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_WS_URL=ws://localhost:8000
    ports:
      - "3000:3000"
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=luckygas
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  adminer:
    image: adminer
    ports:
      - "8080:8080"
    depends_on:
      - db

volumes:
  postgres_data:
  redis_data:
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Backend validation
cd backend
ruff check app/ --fix
mypy app/

# Frontend validation
cd frontend
npm run lint
npm run type-check

# Expected: No errors. Fix any issues before proceeding.
```

### Level 2: Unit Tests
```bash
# Backend tests
cd backend
uv run pytest tests/ -v --cov=app --cov-report=term-missing

# Frontend tests
cd frontend
npm test -- --coverage

# Expected: >80% coverage, all tests passing
```

### Level 3: Integration Tests
```bash
# Start all services
docker-compose up -d

# Wait for services to be ready
wait-for-it localhost:8000 --timeout=30
wait-for-it localhost:3000 --timeout=30

# Run E2E tests
npm run test:e2e

# Test specific workflows
# 1. Login flow
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@luckygas.tw", "password": "admin123"}'

# 2. Customer list
curl http://localhost:8000/api/v1/customers \
  -H "Authorization: Bearer $TOKEN"

# 3. Generate predictions
curl -X POST http://localhost:8000/api/v1/predictions/generate \
  -H "Authorization: Bearer $TOKEN"

# Expected: All endpoints return successful responses
```

### Level 4: Performance Tests
```bash
# Load testing with locust
locust -f tests/load_test.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 60s

# Expected benchmarks:
# - API response time: p95 < 200ms
# - Route optimization: < 5s for 100 deliveries
# - Prediction generation: < 30s for all customers
# - WebSocket latency: < 50ms
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `ruff check app/`
- [ ] No type errors: `mypy app/`
- [ ] API documentation generated: http://localhost:8000/docs
- [ ] Traditional Chinese UI working: All text properly displayed
- [ ] Mobile responsive: Driver interface works on phones
- [ ] Real-time updates: WebSocket notifications working
- [ ] Data migration successful: All Excel/SQLite data imported
- [ ] Role-based access: All 5 roles properly restricted
- [ ] Performance targets met: <200ms API, <3s page load
- [ ] Google Cloud integration: Predictions and routes working
- [ ] Error handling: Graceful failures with Chinese messages

---

## Anti-Patterns to Avoid
- ❌ Don't hardcode Chinese text - use i18n
- ❌ Don't skip data validation for Taiwan formats
- ❌ Don't use sync functions in async FastAPI routes
- ❌ Don't store JWT in localStorage - use httpOnly cookies
- ❌ Don't ignore mobile UX - drivers primarily use phones
- ❌ Don't use local ML models - leverage Google Cloud
- ❌ Don't skip WebSocket reconnection logic
- ❌ Don't forget timezone handling (Asia/Taipei)
- ❌ Don't use generic error messages - provide Chinese context
- ❌ Don't skip caching for expensive operations

## Success Confidence Score: 8.5/10

The PRP provides comprehensive context including:
- ✅ Complete project structure and architecture
- ✅ Existing data analysis and migration strategy  
- ✅ Google Cloud service integration patterns
- ✅ Authentication and authorization implementation
- ✅ Real-time WebSocket configuration
- ✅ Taiwan-specific localization requirements
- ✅ Detailed validation and testing strategy
- ✅ Performance optimization techniques
- ✅ Deployment configuration

The 1.5 point deduction is for:
- Complex multi-phase implementation requiring careful coordination
- Google Cloud service setup may require additional configuration details
- Taiwan-specific business logic may need refinement based on actual usage

This PRP enables one-pass implementation with iterative refinement through the validation loops.