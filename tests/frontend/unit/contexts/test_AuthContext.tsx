/**
 * Unit tests for AuthContext
 * Tests authentication state management, token handling, and user session
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from '../../../../frontend/src/contexts/AuthContext';
import { authService } from '../../../../frontend/src/services/authService';

// Mock auth service
vi.mock('../../../../frontend/src/services/authService', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    getCurrentUser: vi.fn(),
    isTokenExpired: vi.fn()
  }
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
};
global.localStorage = localStorageMock as any;

// Test component to access auth context
const TestComponent = () => {
  const auth = useAuth();
  
  return (
    <div>
      <div data-testid="auth-status">{auth.isAuthenticated ? 'Authenticated' : 'Not Authenticated'}</div>
      <div data-testid="loading-status">{auth.isLoading ? 'Loading' : 'Ready'}</div>
      <div data-testid="user-info">{auth.user ? auth.user.email : 'No User'}</div>
      <div data-testid="user-role">{auth.user?.role || 'No Role'}</div>
      <button onClick={() => auth.login('test@luckygas.tw', 'Test123!')}>Login</button>
      <button onClick={() => auth.logout()}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
  });

  it('provides initial unauthenticated state', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('Not Authenticated');
    expect(screen.getByTestId('loading-status')).toHaveTextContent('Ready');
    expect(screen.getByTestId('user-info')).toHaveTextContent('No User');
  });

  it('loads user from localStorage on mount', async () => {
    const mockUser = {
      id: 1,
      email: 'test@luckygas.tw',
      full_name: '測試用戶',
      role: 'office_staff'
    };

    localStorageMock.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'valid_token';
      if (key === 'user') return JSON.stringify(mockUser);
      return null;
    });

    authService.isTokenExpired.mockReturnValue(false);

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Authenticated');
      expect(screen.getByTestId('user-info')).toHaveTextContent('test@luckygas.tw');
      expect(screen.getByTestId('user-role')).toHaveTextContent('office_staff');
    });
  });

  it('handles login flow correctly', async () => {
    const mockUser = {
      id: 1,
      email: 'test@luckygas.tw',
      full_name: '測試用戶',
      role: 'manager'
    };

    authService.login.mockResolvedValue({
      access_token: 'new_token',
      refresh_token: 'refresh_token',
      user: mockUser
    });

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    // Click login button
    act(() => {
      screen.getByText('Login').click();
    });

    // Should show loading state
    expect(screen.getByTestId('loading-status')).toHaveTextContent('Loading');

    // Wait for login to complete
    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Authenticated');
      expect(screen.getByTestId('user-info')).toHaveTextContent('test@luckygas.tw');
      expect(screen.getByTestId('user-role')).toHaveTextContent('manager');
    });

    // Verify localStorage was updated
    expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'new_token');
    expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'refresh_token');
    expect(localStorageMock.setItem).toHaveBeenCalledWith('user', JSON.stringify(mockUser));
  });

  it('handles login failure', async () => {
    authService.login.mockRejectedValue(new Error('Invalid credentials'));

    const { container } = render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    act(() => {
      screen.getByText('Login').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Not Authenticated');
      expect(screen.getByTestId('loading-status')).toHaveTextContent('Ready');
    });

    // Should not update localStorage on failure
    expect(localStorageMock.setItem).not.toHaveBeenCalledWith('access_token', expect.anything());
  });

  it('handles logout correctly', async () => {
    // Start with authenticated state
    const mockUser = {
      id: 1,
      email: 'test@luckygas.tw',
      full_name: '測試用戶',
      role: 'office_staff'
    };

    localStorageMock.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'valid_token';
      if (key === 'user') return JSON.stringify(mockUser);
      return null;
    });

    authService.isTokenExpired.mockReturnValue(false);
    authService.logout.mockResolvedValue(undefined);

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Authenticated');
    });

    // Click logout
    act(() => {
      screen.getByText('Logout').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Not Authenticated');
      expect(screen.getByTestId('user-info')).toHaveTextContent('No User');
    });

    // Verify localStorage was cleared
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('user');
  });

  it('refreshes token when expired', async () => {
    const mockUser = {
      id: 1,
      email: 'test@luckygas.tw',
      full_name: '測試用戶',
      role: 'driver'
    };

    localStorageMock.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'expired_token';
      if (key === 'refresh_token') return 'valid_refresh_token';
      if (key === 'user') return JSON.stringify(mockUser);
      return null;
    });

    authService.isTokenExpired.mockReturnValue(true);
    authService.refreshToken.mockResolvedValue({
      access_token: 'new_access_token',
      refresh_token: 'new_refresh_token'
    });

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(authService.refreshToken).toHaveBeenCalledWith('valid_refresh_token');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'new_access_token');
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Authenticated');
    });
  });

  it('logs out when refresh fails', async () => {
    localStorageMock.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'expired_token';
      if (key === 'refresh_token') return 'invalid_refresh_token';
      return null;
    });

    authService.isTokenExpired.mockReturnValue(true);
    authService.refreshToken.mockRejectedValue(new Error('Invalid refresh token'));

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Not Authenticated');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    });
  });

  it('provides role-based helper methods', async () => {
    const mockUser = {
      id: 1,
      email: 'manager@luckygas.tw',
      full_name: '經理',
      role: 'manager'
    };

    localStorageMock.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'valid_token';
      if (key === 'user') return JSON.stringify(mockUser);
      return null;
    });

    authService.isTokenExpired.mockReturnValue(false);

    const RoleTestComponent = () => {
      const auth = useAuth();
      
      return (
        <div>
          <div data-testid="is-manager">{auth.hasRole('manager') ? 'Yes' : 'No'}</div>
          <div data-testid="is-admin">{auth.hasRole('super_admin') ? 'Yes' : 'No'}</div>
          <div data-testid="can-manage">{auth.hasAnyRole(['manager', 'super_admin']) ? 'Yes' : 'No'}</div>
          <div data-testid="is-driver">{auth.hasRole('driver') ? 'Yes' : 'No'}</div>
        </div>
      );
    };

    render(
      <BrowserRouter>
        <AuthProvider>
          <RoleTestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-manager')).toHaveTextContent('Yes');
      expect(screen.getByTestId('is-admin')).toHaveTextContent('No');
      expect(screen.getByTestId('can-manage')).toHaveTextContent('Yes');
      expect(screen.getByTestId('is-driver')).toHaveTextContent('No');
    });
  });

  it('handles concurrent login attempts', async () => {
    const mockUser = {
      id: 1,
      email: 'test@luckygas.tw',
      full_name: '測試用戶',
      role: 'office_staff'
    };

    let loginCallCount = 0;
    authService.login.mockImplementation(() => {
      loginCallCount++;
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            access_token: `token_${loginCallCount}`,
            refresh_token: 'refresh_token',
            user: mockUser
          });
        }, 100);
      });
    });

    const ConcurrentTestComponent = () => {
      const auth = useAuth();
      
      const handleMultipleLogins = () => {
        // Attempt multiple logins simultaneously
        auth.login('test@luckygas.tw', 'Test123!');
        auth.login('test@luckygas.tw', 'Test123!');
        auth.login('test@luckygas.tw', 'Test123!');
      };
      
      return (
        <div>
          <button onClick={handleMultipleLogins}>Multiple Logins</button>
          <div data-testid="login-state">{auth.isLoading ? 'Loading' : 'Ready'}</div>
        </div>
      );
    };

    render(
      <BrowserRouter>
        <AuthProvider>
          <ConcurrentTestComponent />
        </AuthProvider>
      </BrowserRouter>
    );

    act(() => {
      screen.getByText('Multiple Logins').click();
    });

    await waitFor(() => {
      // Should only call login once despite multiple attempts
      expect(loginCallCount).toBe(1);
    });
  });
});