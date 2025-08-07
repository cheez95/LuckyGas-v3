/**
 * Enhanced render utilities for React Testing Library
 */
import React, { ReactElement } from 'react';
import { render as rtlRender, RenderOptions, RenderResult } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import { AuthContext, AuthContextType } from '../../contexts/AuthContext';
import { WebSocketContext, WebSocketContextType } from '../../contexts/WebSocketContext';

interface TestUser {
  id: number;
  username: string;
  email: string;
  role: string;
  full_name: string;
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  // Auth context options
  user?: TestUser | null;
  isAuthenticated?: boolean;
  isLoading?: boolean;
  authError?: string | null;
  
  // Router options
  initialRoute?: string;
  routerType?: 'browser' | 'memory';
  
  // WebSocket options
  wsConnected?: boolean;
  wsMessages?: any[];
  
  // i18n options
  locale?: string;
}

// Default test user
export const defaultTestUser: TestUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  role: 'office_staff',
  full_name: 'Test User'
};

// Mock auth context
const createMockAuthContext = (options: CustomRenderOptions): AuthContextType => ({
  user: options.user !== undefined ? options.user : defaultTestUser,
  isAuthenticated: options.isAuthenticated ?? true,
  isLoading: options.isLoading ?? false,
  error: options.authError ?? null,
  login: jest.fn(),
  logout: jest.fn(),
  updateUser: jest.fn(),
  checkAuth: jest.fn(),
});

// Mock WebSocket context
const createMockWebSocketContext = (options: CustomRenderOptions): WebSocketContextType => ({
  isConnected: options.wsConnected ?? false,
  messages: options.wsMessages ?? [],
  sendMessage: jest.fn(),
  subscribe: jest.fn(),
  unsubscribe: jest.fn(),
  connect: jest.fn(),
  disconnect: jest.fn(),
  lastError: null,
});

// Custom render function
export function customRender(
  ui: ReactElement,
  options: CustomRenderOptions = {}
): RenderResult {
  const {
    user,
    isAuthenticated,
    isLoading,
    authError,
    initialRoute = '/',
    routerType = 'memory',
    wsConnected,
    wsMessages,
    locale = 'zh-TW',
    ...renderOptions
  } = options;

  // Setup i18n
  i18n.changeLanguage(locale);

  const Router = routerType === 'browser' ? BrowserRouter : MemoryRouter;
  const routerProps = routerType === 'memory' ? { initialEntries: [initialRoute] } : {};

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Router {...routerProps}>
        <I18nextProvider i18n={i18n}>
          <ConfigProvider locale={zhTW}>
            <AuthContext.Provider value={createMockAuthContext(options)}>
              <WebSocketContext.Provider value={createMockWebSocketContext(options)}>
                {children}
              </WebSocketContext.Provider>
            </AuthContext.Provider>
          </ConfigProvider>
        </I18nextProvider>
      </Router>
    );
  }

  return rtlRender(ui, { wrapper: Wrapper, ...renderOptions });
}

// Render with specific user roles
export const renderAsAdmin = (ui: ReactElement, options: CustomRenderOptions = {}) => {
  return customRender(ui, {
    ...options,
    user: {
      ...defaultTestUser,
      role: 'super_admin',
      username: 'admin',
      email: 'admin@example.com'
    }
  });
};

export const renderAsManager = (ui: ReactElement, options: CustomRenderOptions = {}) => {
  return customRender(ui, {
    ...options,
    user: {
      ...defaultTestUser,
      role: 'manager',
      username: 'manager',
      email: 'manager@example.com'
    }
  });
};

export const renderAsDriver = (ui: ReactElement, options: CustomRenderOptions = {}) => {
  return customRender(ui, {
    ...options,
    user: {
      ...defaultTestUser,
      role: 'driver',
      username: 'driver',
      email: 'driver@example.com'
    }
  });
};

export const renderAsCustomer = (ui: ReactElement, options: CustomRenderOptions = {}) => {
  return customRender(ui, {
    ...options,
    user: {
      ...defaultTestUser,
      role: 'customer',
      username: 'customer',
      email: 'customer@example.com'
    }
  });
};

// Render unauthenticated
export const renderUnauthenticated = (ui: ReactElement, options: CustomRenderOptions = {}) => {
  return customRender(ui, {
    ...options,
    user: null,
    isAuthenticated: false
  });
};

// Export everything from RTL for convenience
export * from '@testing-library/react';

// Export custom render as default
export { customRender as render };