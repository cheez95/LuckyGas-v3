import React from 'react';
import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { AuthProvider } from '../contexts/AuthContext';

// Import all components
import Dashboard from '../components/dashboard/Dashboard';
import CustomerList from '../components/office/CustomerList';
import OrderList from '../components/office/OrderList';
import RouteManagement from '../components/office/RouteManagement';
import DeliveryHistory from '../components/office/DeliveryHistory';
import DriverInterface from '../components/driver/DriverInterface';

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <BrowserRouter>
    <ConfigProvider locale={zhTW}>
      <AuthProvider>
        {children}
      </AuthProvider>
    </ConfigProvider>
  </BrowserRouter>
);

describe('Frontend Tabs Verification', () => {
  test('Dashboard component renders without error', () => {
    const { container } = render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    );
    expect(container).toBeTruthy();
  });

  test('CustomerList component renders without error', () => {
    const { container } = render(
      <TestWrapper>
        <CustomerList />
      </TestWrapper>
    );
    expect(container).toBeTruthy();
  });

  test('OrderList component renders without error', () => {
    const { container } = render(
      <TestWrapper>
        <OrderList />
      </TestWrapper>
    );
    expect(container).toBeTruthy();
  });

  test('RouteManagement component renders without error', () => {
    const { container } = render(
      <TestWrapper>
        <RouteManagement />
      </TestWrapper>
    );
    expect(container).toBeTruthy();
  });

  test('DeliveryHistory component renders without error', () => {
    const { container } = render(
      <TestWrapper>
        <DeliveryHistory />
      </TestWrapper>
    );
    expect(container).toBeTruthy();
  });

  test('DriverInterface component renders without error', () => {
    const { container } = render(
      <TestWrapper>
        <DriverInterface />
      </TestWrapper>
    );
    expect(container).toBeTruthy();
  });
});