# Lucky Gas (幸福氣) Delivery Management System

## PROJECT OVERVIEW

Lucky Gas Delivery Management System is a comprehensive web-based solution for managing gas delivery operations across Taiwan. The system integrates modern cloud AI/ML services for predictive ordering, optimized route planning, and real-time delivery tracking.

## FEATURE REQUIREMENTS

### 1. Full-Stack Modern Web Architecture
- **Frontend**: React with TypeScript, Material-UI or Ant Design for UI components
- **Backend**: FastAPI with Python 3.11+, async/await support
- **Database**: PostgreSQL for primary data, Redis for caching
- **Infrastructure**: Google Cloud Platform preferred for superior AI/ML services

### 2. Core Features

#### A. Customer & Order Management
- Complete customer database with delivery history
- Order creation, modification, and cancellation
- Gas quantity tracking (different cylinder sizes)
- Payment status and invoice management
- Customer communication logs

#### B. Predictive Order Generation (Google Cloud AI)
- **Primary**: Google Vertex AI AutoML for demand prediction
- Historical data analysis from Excel files in `raw/` folder
- Daily prediction lists based on:
  - Historical delivery patterns
  - Seasonal variations
  - Customer-specific consumption rates
  - Weather data integration
- Confidence scoring for predictions
- Manual override capabilities

#### C. Route Optimization (Google Maps Platform)
- Google Routes API for real-time route optimization
- Multi-stop route planning considering:
  - Traffic conditions
  - Vehicle capacity
  - Driver work hours
  - Priority deliveries
  - Geographic clustering
- Dynamic route adjustment
- Estimated delivery time windows

#### D. Multi-Level Access Control (RBAC)
- **Super Admin**: Full system access, user management
- **Manager**: Reports, route approval, driver assignment
- **Office Staff**: Order management, customer service
- **Driver**: Mobile interface, delivery updates
- **Customer**: Order tracking, history viewing

#### E. User Interfaces
- **Admin Dashboard**: 
  - Real-time delivery monitoring
  - Performance metrics
  - System configuration
  - User/permission management via web UI
  
- **Office Portal (Traditional Chinese)**:
  - Order management
  - Customer database
  - Route planning interface
  - Report generation
  
- **Driver Mobile Web App**:
  - Route navigation
  - Delivery status updates
  - Customer signatures
  - Photo upload for proof of delivery
  
- **Database Management Interface**:
  - Web-based database viewer/editor (like phpMyAdmin)
  - Direct data inspection without CLI
  - Bulk data operations
  - Query builder interface

#### F. Real-Time Features
- WebSocket connections for live updates
- Driver location tracking
- Delivery status notifications
- Alert system for urgent situations

### 3. Technical Specifications

#### Database Schema Requirements
- Customers table (from existing data)
- Orders table with status tracking
- Delivery history (from Excel data)
- Drivers and vehicles tables
- Routes and route segments
- Prediction models metadata
- User authentication and permissions

#### API Design
- RESTful API with OpenAPI documentation
- GraphQL consideration for complex queries
- Webhook support for external integrations
- Rate limiting and API key management

#### Security Requirements
- JWT-based authentication
- Role-based access control (RBAC)
- Data encryption at rest and in transit
- Audit logging for all actions
- GDPR-compliant data handling

## DEVELOPMENT PHASES

### Phase 1: Foundation (Week 1-2)
1. Database design and setup with web viewer
2. Basic FastAPI backend structure
3. Authentication system
4. React frontend scaffolding
5. Database management web interface

### Phase 2: Core Features (Week 3-4)
1. Customer management module
2. Order management system
3. Basic route planning
4. Office portal interface
5. Import existing Excel data

### Phase 3: Advanced Features (Week 5-6)
1. Google Cloud AI integration
2. Predictive ordering system
3. Google Maps route optimization
4. Real-time tracking setup
5. Driver mobile interface

### Phase 4: Polish & Deploy (Week 7-8)
1. Performance optimization
2. Comprehensive testing
3. Documentation
4. Deployment setup
5. User training materials

## EXISTING DATA IN `raw/` FOLDER

1. **2025-05 client list.xlsx**: Customer database with contact information
2. **2025-05 deliver history.xlsx**: Historical delivery records for ML training
3. **luckygas.db**: Existing SQLite database (to be migrated to PostgreSQL)

## GOOGLE CLOUD SERVICES INTEGRATION

### Preferred Services:
- **Vertex AI**: AutoML for demand prediction
- **Cloud SQL**: Managed PostgreSQL
- **Cloud Storage**: File uploads and backups
- **Cloud Functions**: Serverless computing for specific tasks
- **Cloud Run**: Container deployment
- **Maps Platform**: Route optimization and geocoding
- **BigQuery**: Analytics and reporting

### Alternative Services (if needed):
- Firebase for real-time updates
- Cloud Memorystore for Redis caching
- Cloud Logging for centralized logs

## DEVELOPMENT GUIDELINES

### Code Organization:
```
luckygas/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   └── alembic/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── utils/
│   └── public/
├── database/
│   ├── migrations/
│   └── seeds/
├── ml/
│   ├── training/
│   └── models/
└── docs/
```

### Frontend Requirements:
- TypeScript for type safety
- React Query for data fetching
- React Router for navigation
- Zustand or Redux Toolkit for state management
- React Hook Form for forms
- i18n for Traditional Chinese support
- Responsive design for mobile drivers

### Backend Requirements:
- FastAPI with async support
- SQLAlchemy 2.0 with async
- Pydantic for data validation
- Celery for background tasks
- pytest for testing
- Black for code formatting

## DELIVERABLES

1. Fully functional web application
2. Database management interface
3. API documentation
4. Deployment scripts
5. User manuals in Traditional Chinese
6. Admin documentation
7. Data migration scripts
8. ML model training pipelines

## SUCCESS CRITERIA

- Successfully import and utilize existing Excel data
- Achieve 80%+ accuracy in order predictions
- Reduce delivery route time by 20%
- Support 100+ concurrent users
- 99.9% uptime for critical features
- Mobile-responsive driver interface
- Complete Traditional Chinese localization

## NOTES FOR CLAUDE CODE

- Prioritize frontend and database tools early for easier development
- Always create web interfaces for data management (avoid CLI-only tools)
- Use Google Cloud services where they provide superior functionality
- Implement comprehensive error handling and logging
- Write tests for critical business logic
- Consider Taiwan-specific requirements (addresses, phone formats, etc.)
- Ensure all user-facing text supports Traditional Chinese