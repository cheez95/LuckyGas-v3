# Lucky Gas Delivery Management System - Claude Code Instructions

## 🚀 Project Context

You are building a comprehensive gas delivery management system for Lucky Gas (幸福氣), a Taiwan-based gas delivery company. This is a full-stack web application with predictive AI capabilities, route optimization, and real-time tracking.

## 🎯 Development Philosophy

### Core Principles
1. **Frontend-First Development**: Build accessible web interfaces early to minimize CLI dependency
2. **Cloud-Native Approach**: Leverage Google Cloud Platform services for AI/ML and infrastructure
3. **User-Centric Design**: Prioritize Traditional Chinese UI and Taiwan-specific requirements
4. **Data-Driven Decisions**: Use existing historical data in `raw/` folder for insights

### Technical Standards
- **Code Quality**: Production-ready, scalable, maintainable
- **Testing**: Comprehensive test coverage for critical paths
- **Documentation**: Bilingual docs (English code, Traditional Chinese UI)
- **Security**: Enterprise-grade security with RBAC

## 📋 Initial Setup Tasks

When starting development, always:

1. **Read PLANNING.md** to understand the current architecture and decisions
2. **Check TASK.md** for the current development phase and pending tasks
3. **Review `raw/` folder** to understand existing data structures:
   - `2025-05 client list.xlsx` - Customer information
   - `2025-05 deliver history.xlsx` - Historical delivery data
   - `luckygas.db` - Existing SQLite database

## 🏗️ Architecture Guidelines

### Frontend (React + TypeScript)
```typescript
// Component structure example
components/
├── common/          // Shared components
├── features/        // Feature-specific components
│   ├── orders/
│   ├── customers/
│   ├── routes/
│   └── predictions/
├── layouts/         // Page layouts
└── admin/          // Admin-specific components
```

### Backend (FastAPI + Python)
```python
# API structure example
app/
├── api/
│   ├── v1/
│   │   ├── auth.py      # Authentication endpoints
│   │   ├── customers.py # Customer management
│   │   ├── orders.py    # Order operations
│   │   ├── routes.py    # Route optimization
│   │   └── predictions.py # ML predictions
├── core/
│   ├── config.py    # Configuration management
│   ├── security.py  # Security utilities
│   └── database.py  # Database setup
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic schemas
└── services/        # Business logic
```

### Database Management Interface
- Implement web-based database viewer early (like Adminer or custom React component)
- Include query builder for non-technical users
- Support data import/export functionality
- Enable direct data editing with validation

## 🔧 Development Workflow

### Phase-Based Development
1. **Always check current phase** in TASK.md
2. **Complete phase requirements** before moving forward
3. **Update PLANNING.md** with architectural decisions
4. **Document in README.md** as features are completed

### Google Cloud Integration Priority
When implementing features, prefer these GCP services:
- **Vertex AI** over local ML implementations
- **Cloud SQL** over self-managed PostgreSQL
- **Cloud Storage** for file handling
- **Routes API** for route optimization
- **BigQuery** for analytics

### Testing Requirements
For each feature, create tests covering:
- Happy path scenarios
- Edge cases (empty data, max limits)
- Error conditions
- Taiwan-specific cases (address formats, phone numbers)

## 🌏 Taiwan-Specific Considerations

### Localization
- All user-facing text in Traditional Chinese (繁體中文)
- Use Taiwan date format (民國年 or YYYY/MM/DD)
- Taiwan phone format: 09XX-XXX-XXX or 0X-XXXX-XXXX
- Address format: 郵遞區號 + 縣市 + 區/鄉/鎮 + 路/街 + 號

### Business Logic
- Gas cylinder sizes specific to Taiwan market
- Delivery hours considering Taiwan work culture
- Holiday calendar for Taiwan
- Payment methods common in Taiwan

## 📊 Data Migration Strategy

When working with existing data:
1. **Analyze Excel files** to understand schema
2. **Create migration scripts** with validation
3. **Preserve historical data** for ML training
4. **Document data transformations**

Example migration approach:
```python
# migrations/import_historical_data.py
def import_customer_data():
    """Import customer data from Excel with validation."""
    df = pd.read_excel('raw/2025-05 client list.xlsx')
    # Validate and transform data
    # Insert into PostgreSQL
```

## 🔒 Security Implementation

### Authentication Flow
1. JWT tokens with refresh mechanism
2. Role-based permissions at API level
3. Frontend route guards
4. Audit logging for all actions

### RBAC Implementation
```python
# Roles hierarchy
ROLES = {
    'super_admin': ['*'],  # All permissions
    'manager': ['view_reports', 'assign_routes', 'manage_drivers'],
    'office_staff': ['manage_orders', 'manage_customers'],
    'driver': ['view_routes', 'update_delivery'],
    'customer': ['view_orders', 'track_delivery']
}
```

## 🚦 API Design Standards

### RESTful Endpoints
```
GET    /api/v1/customers      # List with pagination
POST   /api/v1/customers      # Create new
GET    /api/v1/customers/{id} # Get specific
PUT    /api/v1/customers/{id} # Update
DELETE /api/v1/customers/{id} # Soft delete

# Complex operations
POST   /api/v1/routes/optimize       # Optimize routes
GET    /api/v1/predictions/daily     # Daily predictions
POST   /api/v1/orders/bulk-import    # Bulk operations
```

### Response Format
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

## 🎨 UI/UX Guidelines

### Component Library
- Use Ant Design or Material-UI with Taiwan locale
- Implement consistent loading states
- Error boundaries for graceful failures
- Responsive design for mobile drivers

### Admin Dashboard Requirements
- Real-time WebSocket updates
- Drag-and-drop route adjustment
- Interactive maps with markers
- Export functionality for reports

## 📝 Code Style Rules

### Python Backend
- Use `uv` for all Python commands
- Type hints required for all functions
- Docstrings in Google style
- Max line length: 88 (Black formatter)
- Async/await for I/O operations

### TypeScript Frontend
- Strict mode enabled
- Interface over type aliases
- Custom hooks for logic reuse
- Lazy loading for routes
- Error boundaries for components

## 🧪 Testing Strategy

### Backend Tests
```python
# tests/test_predictions.py
async def test_daily_prediction_generation():
    """Test that daily predictions are generated correctly."""
    # Test with historical data
    # Verify prediction accuracy
    # Check confidence scores
```

### Frontend Tests
```typescript
// tests/components/OrderList.test.tsx
describe('OrderList Component', () => {
  it('displays orders in Traditional Chinese', () => {
    // Test localization
  });
  
  it('handles empty state gracefully', () => {
    // Test edge cases
  });
});
```

## 🔄 Continuous Integration

### Pre-commit Checks
1. Code formatting (Black, Prettier)
2. Type checking (mypy, TypeScript)
3. Linting (flake8, ESLint)
4. Test execution
5. Security scanning

### Deployment Pipeline
1. Build Docker images
2. Run integration tests
3. Deploy to Cloud Run
4. Run smoke tests
5. Monitor performance

## 📚 Documentation Requirements

### Code Documentation
- README.md with setup instructions
- API documentation via OpenAPI/Swagger
- Architecture decisions in PLANNING.md
- Traditional Chinese user guides

### Inline Documentation
```python
# Reason: Using Vertex AI for superior prediction accuracy
# compared to local scikit-learn models
prediction_service = VertexAIPredictionService()
```

## ⚡ Performance Targets

- Page load: < 3 seconds
- API response: < 200ms (p95)
- Route optimization: < 5 seconds for 100 stops
- Prediction generation: < 30 seconds daily batch
- Database queries: Indexed and optimized

## 🛠️ Development Tools

### Required VS Code Extensions
- Python
- Pylance
- ESLint
- Prettier
- Thunder Client (API testing)
- Database client

### Environment Setup
```bash
# Backend
cd backend
uv pip install -r requirements.txt
uv run app

# Frontend  
cd frontend
npm install
npm run dev
```

## 🚨 Common Pitfalls to Avoid

1. **Don't use local ML models** - Use Google Cloud AI
2. **Don't skip web DB interface** - Build it early
3. **Don't hardcode Chinese text** - Use i18n
4. **Don't ignore mobile UX** - Drivers use phones
5. **Don't skip data validation** - Taiwan formats differ

## 💡 Best Practices

1. **Start with database design** and web interface
2. **Import historical data early** for testing
3. **Build API documentation** as you code
4. **Test with real Taiwan addresses**
5. **Use WebSockets** for real-time features
6. **Implement caching** for predictions
7. **Add monitoring** from the start

Remember: This is a production system for a real business. Code quality, reliability, and user experience are paramount. Always consider the end users - office staff who may not be technical and drivers who need simple, reliable mobile interfaces.