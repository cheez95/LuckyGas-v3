# Core Feature Integration - Brownfield Addition

## User Story

As a Lucky Gas office staff member,
I want to manage customers, create orders, and view routes through the web interface,
So that I can efficiently handle daily operations without switching between systems.

## Story Context

**Existing System Integration:**

- Integrates with: Customer, Order, and Route REST APIs
- Technology: React + TypeScript, Material-UI DataGrid, React Router
- Follows pattern: Container/Component pattern with service layer
- Touch points: /api/v1/customers, /api/v1/orders, /api/v1/routes endpoints

## Acceptance Criteria

**Functional Requirements:**

1. Customer management UI displays all customers with search, filter, and CRUD operations
2. Order creation form integrates with customer data and validates business rules
3. Route visualization shows delivery routes with driver assignments and status

**Integration Requirements:**
4. All existing backend APIs consumed correctly with proper error handling
5. Data validation matches backend business rules exactly
6. UI components follow existing Material-UI patterns in the codebase

**Quality Requirements:**
7. Loading states and error boundaries implemented for all data operations
8. Traditional Chinese (繁體中文) labels throughout the interface
9. Response time <200ms for all list operations with pagination

## Technical Notes

- **Integration Approach:** 
  - Use API client from STORY-FE-INT-01 for all backend calls
  - Implement React Query for caching and synchronization
  - Material-UI DataGrid for tabular data with server-side operations

- **Existing Pattern Reference:** 
  - Component structure: `/frontend/src/components/features/`
  - Service calls: `/frontend/src/services/`
  - State management: React Context + hooks pattern

- **Key Constraints:** 
  - Must handle Taiwan-specific data formats (phone, address)
  - Support for both commercial and residential customer types
  - Order creation must validate cylinder quantities against inventory

## Implementation Details

```typescript
// Example customer service integration
// src/services/customerService.ts
export const customerService = {
  async getCustomers(params: CustomerQueryParams): Promise<PaginatedResponse<Customer>> {
    const { data } = await apiClient.get('/api/v1/customers', { params });
    return data;
  },
  
  async createCustomer(customer: CreateCustomerDto): Promise<Customer> {
    const { data } = await apiClient.post('/api/v1/customers', customer);
    return data;
  },
  
  async updateCustomer(id: number, updates: UpdateCustomerDto): Promise<Customer> {
    const { data } = await apiClient.put(`/api/v1/customers/${id}`, updates);
    return data;
  }
};

// React Query hook example
export const useCustomers = (params: CustomerQueryParams) => {
  return useQuery({
    queryKey: ['customers', params],
    queryFn: () => customerService.getCustomers(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
```

## Component Structure

```
/frontend/src/components/features/
├── customers/
│   ├── CustomerList.tsx
│   ├── CustomerForm.tsx
│   ├── CustomerDetail.tsx
│   └── index.ts
├── orders/
│   ├── OrderList.tsx
│   ├── OrderForm.tsx
│   ├── OrderDetail.tsx
│   └── index.ts
└── routes/
    ├── RouteList.tsx
    ├── RouteMap.tsx
    ├── RouteAssignment.tsx
    └── index.ts
```

## Definition of Done

- [x] All three core features (customers, orders, routes) integrated
- [x] Data operations working with proper loading and error states
- [x] Traditional Chinese UI labels implemented
- [x] Backend validation rules enforced in frontend
- [x] Unit tests for services and integration tests for components
- [x] Performance targets met (<200ms response times)

## Risk and Compatibility Check

**Minimal Risk Assessment:**

- **Primary Risk:** Data synchronization issues between frontend and backend
- **Mitigation:** Implement optimistic updates with rollback on failure
- **Rollback:** Disable frontend features and revert to direct API testing

**Compatibility Verification:**

- [x] No changes to backend API contracts
- [x] Frontend routing follows existing patterns
- [x] UI components consistent with design system
- [x] Performance within acceptable limits

---

**Developer Notes:**

This story connects the frontend to the three core business features. Focus on getting basic CRUD operations working first, then enhance with advanced features like real-time updates. Ensure all Taiwan-specific business rules are properly implemented (e.g., customer types, address formats, phone validation).

Priority order for implementation:
1. Customer management (foundation for orders)
2. Order creation (depends on customers)
3. Route visualization (depends on orders)

Test with the migrated data to ensure compatibility with existing records.