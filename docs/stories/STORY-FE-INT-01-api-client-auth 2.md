# API Client & Authentication Setup - Brownfield Addition

## User Story

As a Lucky Gas staff member,
I want secure and seamless API communication with automatic authentication,
So that I can access backend services without manual token management or interruptions.

## Story Context

**Existing System Integration:**

- Integrates with: FastAPI backend JWT authentication endpoints
- Technology: React + TypeScript frontend, Axios for HTTP, Material-UI components
- Follows pattern: Service layer pattern with typed interfaces
- Touch points: /api/v1/auth/login, /api/v1/auth/refresh, all protected API endpoints

## Acceptance Criteria

**Functional Requirements:**

1. Axios client configured with request/response interceptors for JWT handling
2. Automatic token refresh when access token expires (without user disruption)
3. Comprehensive error handling with retry logic for network failures

**Integration Requirements:**
4. Existing backend authentication endpoints work unchanged
5. New implementation follows existing TypeScript interface patterns
6. Integration with protected APIs maintains current security model

**Quality Requirements:**
7. 100% test coverage for authentication flows
8. TypeScript interfaces documented for all API responses
9. No regression in existing authentication functionality

## Technical Notes

- **Integration Approach:** 
  - Create axios instance with baseURL from environment config
  - Add request interceptor to inject JWT from localStorage
  - Add response interceptor to handle 401 and refresh tokens
  - Implement exponential backoff for retry logic

- **Existing Pattern Reference:** 
  - Follow service layer pattern in `/frontend/src/services/`
  - Use existing TypeScript interfaces from `/frontend/src/types/`
  - Maintain Material-UI notification patterns for errors

- **Key Constraints:** 
  - Must support both development (localhost:8000) and production API URLs
  - Token storage must use secure methods (httpOnly cookies in production)
  - Refresh token rotation must be supported

## Implementation Details

```typescript
// Example structure following existing patterns
// src/services/api/client.ts
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for JWT
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      // Implement refresh logic
    }
    return Promise.reject(error);
  }
);
```

## Definition of Done

- [x] Functional requirements met
- [x] Integration requirements verified
- [x] Existing functionality regression tested
- [x] Code follows existing patterns and standards
- [x] Tests pass (existing and new)
- [x] Documentation updated if applicable

## Risk and Compatibility Check

**Minimal Risk Assessment:**

- **Primary Risk:** Token refresh race conditions with concurrent requests
- **Mitigation:** Implement request queue during token refresh
- **Rollback:** Revert to previous authentication implementation

**Compatibility Verification:**

- [x] No breaking changes to existing APIs
- [x] Database changes (if any) are additive only
- [x] UI changes follow existing design patterns
- [x] Performance impact is negligible

---

**Developer Notes:**

This story establishes the foundation for all frontend-backend communication. It must be completed before any other frontend integration work. The implementation should be thoroughly tested with both successful and failure scenarios, including network interruptions and token expiration edge cases.

Key files to create/modify:
- `/frontend/src/services/api/client.ts` - Main API client
- `/frontend/src/services/api/auth.ts` - Authentication service
- `/frontend/src/types/auth.ts` - TypeScript interfaces
- `/frontend/src/utils/storage.ts` - Secure token storage utilities
- `/frontend/src/hooks/useAuth.ts` - React hook for authentication state