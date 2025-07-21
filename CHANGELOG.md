# Changelog

All notable changes to the Lucky Gas Delivery Management System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive Google API integration with monitoring and protection
- Enhanced security with API key encryption (Fernet) and Google Secret Manager support
- Rate limiting system with Redis backend (per-second/minute/day quotas)
- Cost monitoring with automatic budget enforcement
- Circuit breaker pattern for API resilience
- API response caching with configurable TTLs
- Development mode manager for seamless mock/production switching
- Mock services with Taiwan-specific patterns
- Google OR-Tools integration for vehicle routing optimization
- Environment variable validation on startup
- Audit logging for security compliance
- Custom cache service replacing fastapi-cache2

### Changed
- Upgraded Redis dependency to >=6.2.0 for better performance
- Replaced fastapi-cache2 with custom cache implementation
- Enhanced API services with monitoring and protection layers

### Fixed
- Redis version conflict with fastapi-cache2
- Missing dependencies for cryptography and google-cloud-secret-manager
- Import order issues in API cache module
- API key manager factory function async compatibility

## [1.0.0] - 2025-07-21
### Added
- Initial release of Lucky Gas Delivery Management System
- Customer management with CRUD operations
- Order processing and tracking
- Route optimization with Google Routes API
- Demand prediction with Vertex AI
- Real-time updates via WebSocket/Socket.IO
- Role-based access control (RBAC)
- Traditional Chinese (繁體中文) interface
- Comprehensive backend API with FastAPI
- React-based frontend with TypeScript
- PostgreSQL database with SQLAlchemy ORM
- Redis caching for performance optimization
- Docker containerization
- Prometheus metrics integration
- Structured logging with correlation IDs

### Security
- JWT-based authentication
- Password hashing with bcrypt
- CORS configuration for security
- Environment-based configuration management