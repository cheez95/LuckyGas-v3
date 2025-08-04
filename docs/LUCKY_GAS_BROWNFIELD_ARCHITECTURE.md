# Lucky Gas Delivery Management System - Brownfield Architecture Document

## Introduction

This document captures the CURRENT STATE of the Lucky Gas (幸福氣) delivery management system codebase, including technical accomplishments, integration points, and real-world patterns. It serves as a reference for AI agents and developers working on Phase 2 enhancements.

### Document Scope

Comprehensive documentation covering:
- Completed Phase 1 infrastructure and data migration
- Backend API implementation with FastAPI
- Frontend React application structure
- Database schema with migrated data
- Integration points for Phase 2 features

### Change Log

| Date       | Version | Description                           | Author      |
|------------|---------|---------------------------------------|-------------|
| 2025-01-29 | 1.0     | Initial brownfield analysis post-Phase 1 | BMad Master |

## Quick Reference - Key Files and Entry Points

### Critical Files for Understanding the System

- **Backend Entry**: `backend/app/main.py` - FastAPI application entry
- **Frontend Entry**: `frontend/src/main.tsx` - React application entry
- **Backend Config**: `backend/app/core/config.py`, `backend/.env`
- **Frontend Config**: `frontend/.env`, `frontend/vite.config.ts`
- **Core Business Logic**: `backend/app/services/`
- **API Definitions**: `backend/app/api/v1/`
- **Database Models**: `backend/app/models/`
- **Database Migrations**: `backend/alembic/versions/`
- **Data Migration Scripts**: `backend/migrations/data_migration/`

### Phase 2 Enhancement Impact Areas

Based on the planned enhancements:
- **Route Optimization**: `backend/app/services/route_optimization.py` (exists, needs Google Routes API)
- **AI Predictions**: `backend/app/services/vertex_ai_service.py` (exists, needs implementation)
- **Frontend Integration**: `frontend/src/services/` (needs creation)
- **WebSocket**: `backend/app/services/websocket_service.py` (exists)

## High Level Architecture

### Technical Summary

Lucky Gas is a full-stack web application for managing gas cylinder deliveries in Taiwan. The system handles customer management, order processing, route optimization, delivery tracking, and predictive analytics.

### Actual Tech Stack

| Category     | Technology    | Version | Notes                                    |
|--------------|---------------|---------|------------------------------------------|
| Backend Runtime | Python     | 3.12    | Using uv package manager                 |
| Backend Framework | FastAPI  | 0.116.1 | Async REST API with WebSocket support    |
| Frontend Runtime | Node.js   | 18+     | Development environment                  |
| Frontend Framework | React   | 19.1.0  | With TypeScript and Vite                 |
| Database     | PostgreSQL    | 15      | Primary data store                       |
| Cache        | Redis         | 6.2.0   | Session storage and caching              |
| UI Library   | Ant Design    | 5.26.5  | With Traditional Chinese locale          |
| Maps         | Google Maps   | JS API  | For route visualization                  |
| Testing      | Pytest/Jest   | Latest  | Backend and frontend testing             |
| E2E Testing  | Playwright    | 1.40.0  | Cross-browser testing                    |

### Repository Structure Reality Check

- Type: Monorepo with separate backend/frontend directories
- Backend Package Manager: uv (Python)
- Frontend Package Manager: npm
- Notable: Template-based structure from Context Engineering template

## Source Tree and Module Organization

### Project Structure (Actual)

```text
LuckyGas-v3/
├── backend/
│   ├── app/
│   │   ├── api/               # API endpoints (v1 versioned)
│   │   ├── core/              # Core configs, security, database
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── services/          # Business logic layer
│   │   ├── middleware/        # Auth, rate limiting, logging
│   │   └── main.py           # FastAPI app entry point
│   ├── alembic/              # Database migrations
│   │   └── versions/         # Migration files (001-008 + custom)
│   ├── migrations/
│   │   └── data_migration/   # Excel data import scripts
│   ├── tests/                # Comprehensive test suite
│   └── scripts/              # Utility scripts
├── frontend/
│   ├── src/
│   │   ├── components/       # React components (needs organization)
│   │   ├── services/         # API service layer (TO BE CREATED)
│   │   ├── hooks/            # Custom React hooks
│   │   ├── types/            # TypeScript definitions
│   │   ├── locales/          # i18n translations (zh-TW)
│   │   └── main.tsx         # React entry point
│   ├── public/              # Static assets, service worker
│   └── e2e/                 # Playwright E2E tests
├── docs/
│   ├── epics/               # BMad epics for features
│   └── stories/             # User stories
└── raw/                     # Original Excel data files
```

### Key Modules and Their Current State

#### Backend Modules

- **Authentication**: `app/core/security.py` - JWT-based with refresh tokens
- **Customer Management**: `app/services/customer_service.py` - CRUD operations
- **Order Processing**: `app/services/order_service.py` - Order lifecycle management
- **Route Optimization**: `app/services/route_optimization.py` - Stub for Google Routes API
- **AI Predictions**: `app/services/vertex_ai_service.py` - Stub for Vertex AI
- **WebSocket**: `app/services/websocket_service.py` - Real-time updates ready
- **SMS Gateway**: `app/services/sms_service.py` - Taiwan SMS providers integrated
- **Banking**: `app/services/banking_service.py` - SFTP file transfers

#### Frontend Modules (Current Gaps)

- **API Client**: Not yet implemented (Story STORY-FE-INT-01)
- **Authentication**: No JWT handling yet
- **Customer UI**: Components exist but not connected
- **Order Management**: UI components need API integration
- **Route Visualization**: Google Maps integration started
- **Localization**: i18n setup exists, needs content

## Data Models and Current Data State

### Database Schema

The database has been fully migrated with:
- **13,295 customers** (1,267 commercial + 12,028 auto-created)
- **349,920 delivery history records** (2021-2025)
- Complete schema established via Alembic migrations

Key models (see actual files for details):
- **User Model**: `app/models/user.py` - Staff and driver accounts
- **Customer Model**: `app/models/customer.py` - Commercial/residential customers
- **Order Model**: `app/models/order.py` - Order lifecycle
- **Delivery Model**: `app/models/delivery.py` - Delivery tracking
- **Route Model**: `app/models/route.py` - Route planning
- **Gas Product Model**: `app/models/gas_product.py` - Cylinder types

### API Specifications

Backend APIs are implemented and tested:
- **Auth**: `/api/v1/auth/` - Login, refresh, logout
- **Customers**: `/api/v1/customers/` - Full CRUD with search
- **Orders**: `/api/v1/orders/` - Order management
- **Routes**: `/api/v1/routes/` - Route CRUD (optimization pending)
- **Predictions**: `/api/v1/predictions/` - Stub for AI predictions

Frontend needs to consume these APIs (Phase 2 work).

## Integration Points and External Dependencies

### External Services (Phase 2)

| Service | Purpose | Integration Type | Status | Key Files |
|---------|---------|------------------|---------|-----------|
| Google Routes API | Route optimization | REST API | Pending | `app/services/route_optimization.py` |
| Google Vertex AI | Demand prediction | Python SDK | Pending | `app/services/vertex_ai_service.py` |
| Taiwan SMS | Notifications | HTTP API | Ready | `app/services/sms_service.py` |
| Google Maps | Visualization | JavaScript API | Partial | `frontend/src/components/Map/` |

### Internal Integration Points

- **Frontend-Backend**: REST API on port 8000, needs axios setup
- **WebSocket**: Socket.io on ws://localhost:8000/ws
- **Background Jobs**: Celery with Redis broker (configured)
- **File Storage**: Local filesystem, Google Cloud Storage ready

## Development and Deployment

### Local Development Setup

#### Backend Setup
```bash
cd backend
uv pip install -r requirements.txt
# Set up .env file with database credentials
uv run alembic upgrade head
uv run python app/main.py
```

#### Frontend Setup
```bash
cd frontend
npm install
# Set up .env file with API URL
npm run dev
```

#### Known Setup Issues
- PostgreSQL must be running locally or via Docker
- Redis required for WebSocket and caching
- Taiwan timezone (UTC+8) must be configured

### Current Deployment Status

- **Development**: Local environment working
- **Staging**: Not yet configured
- **Production**: Infrastructure defined but not deployed
- **CI/CD**: GitHub Actions workflows defined

## Testing Reality

### Current Test Coverage

#### Backend
- Unit Tests: ~70% coverage (Pytest)
- Integration Tests: Database and API tests
- E2E Tests: Basic flows covered
- Contract Tests: Pact framework integrated

#### Frontend
- Unit Tests: Jest configured, minimal coverage
- Component Tests: React Testing Library ready
- E2E Tests: Playwright tests for core flows
- Visual Tests: Not implemented

### Running Tests

```bash
# Backend tests
cd backend
uv run pytest
uv run pytest --cov

# Frontend tests
cd frontend
npm test
npm run test:e2e
```

## Technical Accomplishments and Constraints

### Phase 1 Accomplishments

1. **Database Infrastructure**: 
   - Complete schema with 30+ tables
   - Successful migration of 350K+ historical records
   - Referential integrity maintained

2. **Backend API**:
   - All core endpoints implemented
   - JWT authentication with refresh tokens
   - WebSocket support for real-time updates
   - Comprehensive error handling

3. **Data Quality**:
   - Customer data cleaned and validated
   - Taiwan-specific formats handled (dates, phones, addresses)
   - Missing data intelligently filled

### Current Constraints

1. **Frontend Disconnected**: React app exists but not connected to backend
2. **No Route Optimization**: Google Routes API integration pending
3. **No AI Predictions**: Vertex AI integration pending
4. **Limited Localization**: UI strings need Traditional Chinese translation
5. **No Production Deployment**: Local development only

### Technical Debt

1. **Frontend Service Layer**: No standardized API client pattern
2. **State Management**: No Redux/Zustand, using local state
3. **Component Organization**: Frontend components need restructuring
4. **Test Coverage**: Frontend tests minimal
5. **Environment Config**: Some hardcoded values need extraction

## Phase 2 Implementation Guide

### Frontend-Backend Integration (EPIC-006)
Files to create/modify:
- `frontend/src/services/api/client.ts` - Axios configuration
- `frontend/src/services/api/auth.ts` - Authentication service
- `frontend/src/hooks/useAuth.ts` - Auth state management
- `frontend/src/types/` - TypeScript interfaces for API

### Google Cloud Setup (EPIC-007)
Files to create/modify:
- `backend/app/core/google_cloud_config.py` - GCP client setup
- `backend/.env` - Add GCP credentials path
- Update service files to use real APIs instead of stubs

### Route Optimization (EPIC-003)
Files to modify:
- `backend/app/services/route_optimization.py` - Implement Google Routes API
- `backend/app/api/v1/routes.py` - Add optimization endpoint
- Frontend route visualization components

### AI Predictions (EPIC-005)
Files to modify:
- `backend/app/services/vertex_ai_service.py` - Implement Vertex AI
- `backend/app/models/prediction.py` - Enhance prediction model
- Create batch prediction job scheduler

## Appendix - Useful Commands and Scripts

### Frequently Used Commands

```bash
# Backend
cd backend
uv run alembic upgrade head      # Run migrations
uv run python scripts/create_test_users.py  # Create test data
uv run python app/main.py        # Start backend server

# Frontend  
cd frontend
npm run dev                      # Start dev server
npm run build                    # Production build
npm run test:e2e                 # Run E2E tests

# Data Migration (already completed)
cd backend
uv run python migrations/data_migration/001_migrate_clients_simple.py --production
uv run python migrations/data_migration/003_migrate_deliveries_fixed.py --production
```

### Debugging and Troubleshooting

- **Backend Logs**: Check console output, structured JSON logging
- **Frontend Logs**: Browser console, React Developer Tools
- **Database**: Use pgAdmin or `psql` to inspect data
- **API Testing**: Use Thunder Client or Postman
- **WebSocket Testing**: `frontend/src/test-websocket.html`

## Key Decisions and Patterns

### Backend Patterns
- Service layer pattern for business logic
- Repository pattern for data access (partial)
- Dependency injection via FastAPI
- Async/await throughout

### Frontend Patterns (Planned)
- Container/Component separation
- Custom hooks for logic reuse
- Service layer for API calls
- Context providers for global state

### Security Decisions
- JWT with short-lived access tokens
- Refresh token rotation
- Role-based access control (RBAC)
- API key management for external services

This document will be updated as Phase 2 features are implemented.