import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { NotificationProvider } from '../contexts/NotificationContext';
import { WebSocketProvider } from '../contexts/WebSocketContext';

// Mock providers for testing
const AllTheProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          <WebSocketProvider>
            {children}
          </WebSocketProvider>
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

// Custom render function that includes all providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything
export * from '@testing-library/react';
export { customRender as render };

// Common test data
export const mockUser = {
  id: 1,
  username: 'testuser',
  role: 'admin' as const,
  email: 'test@example.com',
};

export const mockCustomer = {
  id: 1,
  code: 'C001',
  name: '測試客戶',
  phone: '0912345678',
  address: '台北市信義區測試路1號',
  area: '信義區',
  active: true,
};

export const mockOrder = {
  id: 1,
  customer_id: 1,
  delivery_date: '2024-01-20',
  status: 'pending' as const,
  items: [
    { product_id: 1, quantity: 2, price: 500 }
  ],
  total_amount: 1000,
};

export const mockRoute = {
  id: 1,
  name: '路線1',
  driver_id: 1,
  date: '2024-01-20',
  stops: [
    { 
      customer_id: 1, 
      sequence: 1, 
      address: '台北市信義區測試路1號',
      status: 'pending' as const 
    }
  ],
  status: 'active' as const,
};

// Helper to wait for async operations
export const waitForAsync = async () => {
  return new Promise(resolve => setTimeout(resolve, 0));
};

// Mock API responses
export function createMockApiResponse<T>(data: T, delay = 0): Promise<{ data: T }> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ data });
    }, delay);
  });
}

// Test error scenarios
export function createMockApiError(message: string, status = 400) {
  return Promise.reject({
    response: {
      status,
      data: { message },
    },
  });
}