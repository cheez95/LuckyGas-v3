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
import { WebSocketProvider } from './contexts/WebSocketContext';

// Common Components
import ErrorBoundary from './components/common/ErrorBoundary';
import SessionManager from './components/common/SessionManager';

// Pages/Components
import Login from './components/Login';
import ForgotPassword from './components/ForgotPassword';
import ResetPassword from './components/ResetPassword';
import MainLayout from './components/MainLayout';
import Dashboard from './components/dashboard/Dashboard';
import CustomerManagement from './pages/office/CustomerManagement';
import OrderManagement from './pages/office/OrderManagement';
import RoutePlanning from './pages/office/RoutePlanning';
import DeliveryHistory from './components/office/DeliveryHistory';
import DriverInterface from './components/driver/DriverInterface';
import UserProfile from './components/UserProfile';

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
                <WebSocketProvider>
                  <SessionManager>
                    <Routes>
                      <Route path="/login" element={<Login />} />
                      <Route path="/forgot-password" element={<ForgotPassword />} />
                      <Route path="/reset-password" element={<ResetPassword />} />
                      <Route path="/" element={<MainLayout />}>
                        <Route index element={<Navigate to="/dashboard" replace />} />
                        <Route path="dashboard" element={<Dashboard />} />
                        <Route path="customers" element={<CustomerManagement />} />
                        <Route path="orders" element={<OrderManagement />} />
                        <Route path="routes" element={<RoutePlanning />} />
                        <Route path="delivery-history" element={<DeliveryHistory />} />
                        <Route path="driver" element={<DriverInterface />} />
                        <Route path="profile" element={<UserProfile />} />
                      </Route>
                    </Routes>
                  </SessionManager>
                </WebSocketProvider>
              </NotificationProvider>
            </AuthProvider>
          </NavigationSetup>
        </Router>
      </ErrorBoundary>
    </ConfigProvider>
  );
};

export default App;