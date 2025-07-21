import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-tw';
import './App.css';

// Utils
import { setNavigate } from './utils/router';

// Contexts
import { AuthProvider } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';

// Common Components
import ErrorBoundary from './components/common/ErrorBoundary';
import SessionManager from './components/common/SessionManager';

// Pages/Components (to be created)
import Login from './components/Login';
import MainLayout from './components/MainLayout';
import Dashboard from './components/dashboard/Dashboard';
import CustomerList from './components/office/CustomerList';
import OrderList from './components/office/OrderList';
import RouteManagement from './components/office/RouteManagement';
import DeliveryHistory from './components/office/DeliveryHistory';
import DriverInterface from './components/driver/DriverInterface';

// Set dayjs locale
dayjs.locale('zh-tw');

// Component to set up the navigate function
const NavigationSetup: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  
  useEffect(() => {
    setNavigate(navigate);
  }, [navigate]);
  
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhTW}
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <ErrorBoundary>
        <Router>
          <NavigationSetup>
            <AuthProvider>
              <NotificationProvider>
                <SessionManager>
                  <Routes>
                    <Route path="/login" element={<Login />} />
                    <Route path="/" element={<MainLayout />}>
                      <Route index element={<Navigate to="/dashboard" replace />} />
                      <Route path="dashboard" element={<Dashboard />} />
                      <Route path="customers" element={<CustomerList />} />
                      <Route path="orders" element={<OrderList />} />
                      <Route path="routes" element={<RouteManagement />} />
                      <Route path="delivery-history" element={<DeliveryHistory />} />
                      <Route path="driver" element={<DriverInterface />} />
                    </Route>
                  </Routes>
                </SessionManager>
              </NotificationProvider>
            </AuthProvider>
          </NavigationSetup>
        </Router>
      </ErrorBoundary>
    </ConfigProvider>
  );
};

export default App;