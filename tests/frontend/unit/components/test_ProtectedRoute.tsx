/**
 * Unit tests for ProtectedRoute component
 * Tests authentication, authorization, and role-based access control
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import ProtectedRoute from '../../../../frontend/src/components/ProtectedRoute';
import { AuthProvider } from '../../../../frontend/src/contexts/AuthContext';
import { UserRole } from '../../../../frontend/src/types/auth';

// Mock the auth context
const mockUseAuth = vi.fn();
vi.mock('../../../../frontend/src/contexts/AuthContext', async () => {
  const actual = await vi.importActual('../../../../frontend/src/contexts/AuthContext');
  return {
    ...actual,
    useAuth: () => mockUseAuth()
  };
});

// Mock Ant Design Spin component
vi.mock('antd', () => ({
  Spin: ({ tip }: any) => <div data-testid="loading-spinner">{tip}</div>
}));

describe('ProtectedRoute Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('displays loading spinner when authentication is loading', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      user: null
    });

    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </BrowserRouter>
    );

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(screen.getByText('載入中...')).toBeInTheDocument();
  });

  it('redirects to login when user is not authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null
    });

    const { container } = render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Protected Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Dashboard')).not.toBeInTheDocument();
  });

  it('redirects to login when access token is missing', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true, // Even if authenticated
      isLoading: false,
      user: { id: 1, role: 'office_staff' as UserRole }
    });
    
    // Ensure no token in localStorage
    localStorage.removeItem('access_token');

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Protected Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('allows access when user is authenticated with token', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { id: 1, role: 'office_staff' as UserRole }
    });
    
    localStorage.setItem('access_token', 'valid-token');

    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </BrowserRouter>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('enforces role-based access control for office staff', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { id: 1, role: 'office_staff' as UserRole }
    });
    
    localStorage.setItem('access_token', 'valid-token');

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute requiredRoles={['super_admin', 'manager'] as UserRole[]}>
                <div>Admin Panel</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    // Should redirect to dashboard since office_staff doesn't have admin access
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument();
  });

  it('redirects driver to driver dashboard when accessing unauthorized route', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { id: 2, role: 'driver' as UserRole }
    });
    
    localStorage.setItem('access_token', 'valid-token');

    render(
      <MemoryRouter initialEntries={['/office']}>
        <Routes>
          <Route path="/driver" element={<div>Driver Dashboard</div>} />
          <Route
            path="/office"
            element={
              <ProtectedRoute requiredRoles={['office_staff', 'manager'] as UserRole[]}>
                <div>Office Panel</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Driver Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Office Panel')).not.toBeInTheDocument();
  });

  it('redirects customer to customer dashboard when accessing unauthorized route', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { id: 3, role: 'customer' as UserRole }
    });
    
    localStorage.setItem('access_token', 'valid-token');

    render(
      <MemoryRouter initialEntries={['/office']}>
        <Routes>
          <Route path="/customer" element={<div>Customer Dashboard</div>} />
          <Route
            path="/office"
            element={
              <ProtectedRoute requiredRoles={['office_staff'] as UserRole[]}>
                <div>Office Panel</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Customer Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Office Panel')).not.toBeInTheDocument();
  });

  it('allows access when user has one of the required roles', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { id: 1, role: 'manager' as UserRole }
    });
    
    localStorage.setItem('access_token', 'valid-token');

    render(
      <BrowserRouter>
        <ProtectedRoute requiredRoles={['manager', 'super_admin'] as UserRole[]}>
          <div>Management Panel</div>
        </ProtectedRoute>
      </BrowserRouter>
    );

    expect(screen.getByText('Management Panel')).toBeInTheDocument();
  });

  it('preserves original location in login redirect state', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null
    });

    const TestComponent = () => {
      const location = window.location;
      return <div>{location.pathname}</div>;
    };

    render(
      <MemoryRouter initialEntries={['/orders/123']}>
        <Routes>
          <Route path="/login" element={<TestComponent />} />
          <Route
            path="/orders/:id"
            element={
              <ProtectedRoute>
                <div>Order Details</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    // Should be redirected to login
    expect(screen.getByText('/login')).toBeInTheDocument();
  });

  it('renders multiple children correctly when authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { id: 1, role: 'office_staff' as UserRole }
    });
    
    localStorage.setItem('access_token', 'valid-token');

    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div>Child 1</div>
          <div>Child 2</div>
          <div>Child 3</div>
        </ProtectedRoute>
      </BrowserRouter>
    );

    expect(screen.getByText('Child 1')).toBeInTheDocument();
    expect(screen.getByText('Child 2')).toBeInTheDocument();
    expect(screen.getByText('Child 3')).toBeInTheDocument();
  });
});