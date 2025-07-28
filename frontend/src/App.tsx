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
import WebSocketManager from './components/common/WebSocketManager';

// Pages/Components
import Login from './components/Login';
import ForgotPassword from './components/ForgotPassword';
import ResetPassword from './components/ResetPassword';
import MainLayout from './components/MainLayout';
import Dashboard from './components/dashboard/Dashboard';
import CustomerManagement from './pages/office/CustomerManagement';
import OrderManagement from './pages/office/OrderManagement';
import RoutePlanning from './pages/dispatch/RoutePlanning';
import DriverAssignment from './pages/dispatch/DriverAssignment';
import EmergencyDispatch from './pages/dispatch/EmergencyDispatch';
import DispatchDashboard from './pages/dispatch/DispatchDashboard';
import DeliveryHistory from './components/office/DeliveryHistory';
import UserProfile from './components/UserProfile';

// Driver Pages
import DriverDashboard from './pages/driver/DriverDashboard';
import RouteDetails from './pages/driver/RouteDetails';
import DeliveryView from './pages/driver/DeliveryView';
import DriverNavigation from './pages/driver/DriverNavigation';
import DeliveryScanner from './pages/driver/DeliveryScanner';

// Customer Pages
import CustomerPortal from './pages/customer/CustomerPortal';
import OrderTracking from './pages/customer/OrderTracking';

// Analytics Pages
import ReportingDashboard from './pages/analytics/ReportingDashboard';

// Admin Pages
import ExecutiveDashboard from './pages/admin/ExecutiveDashboard';
import OperationsDashboard from './pages/admin/OperationsDashboard';
import FinancialDashboard from './pages/admin/FinancialDashboard';
import PerformanceAnalytics from './pages/admin/PerformanceAnalytics';

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
                  <WebSocketManager />
                  <SessionManager>
                    <Routes>
                      <Route path="/login" element={<Login />} />
                      <Route path="/forgot-password" element={<ForgotPassword />} />
                      <Route path="/reset-password" element={<ResetPassword />} />
                      
                      {/* Driver Routes - No MainLayout for mobile optimization */}
                      <Route path="/driver">
                        <Route index element={<DriverDashboard />} />
                        <Route path="route/:routeId" element={<RouteDetails />} />
                        <Route path="delivery/:routeId/:deliveryIndex" element={<DeliveryView />} />
                        <Route path="navigation" element={<DriverNavigation />} />
                        <Route path="scan" element={<DeliveryScanner />} />
                        <Route path="routes/completed" element={<DriverDashboard />} />
                        <Route path="cylinder-return" element={<DriverDashboard />} />
                        <Route path="communication" element={<DriverDashboard />} />
                        <Route path="clock-out" element={<DriverDashboard />} />
                      </Route>

                      {/* Main App Routes with Layout */}
                      <Route path="/" element={<MainLayout />}>
                        <Route index element={<Navigate to="/dashboard" replace />} />
                        <Route path="dashboard" element={<Dashboard />} />
                        <Route path="customers" element={<CustomerManagement />} />
                        <Route path="orders" element={<OrderManagement />} />
                        <Route path="routes" element={<RoutePlanning />} />
                        <Route path="driver-assignment" element={<DriverAssignment />} />
                        <Route path="emergency-dispatch" element={<EmergencyDispatch />} />
                        <Route path="dispatch-dashboard" element={<DispatchDashboard />} />
                        <Route path="delivery-history" element={<DeliveryHistory />} />
                        <Route path="customer" element={<CustomerPortal />} />
                        <Route path="customer/track/:orderId" element={<OrderTracking />} />
                        <Route path="analytics" element={<ReportingDashboard />} />
                        
                        {/* Admin Routes */}
                        <Route path="admin/executive" element={<ExecutiveDashboard />} />
                        <Route path="admin/operations" element={<OperationsDashboard />} />
                        <Route path="admin/financial" element={<FinancialDashboard />} />
                        <Route path="admin/performance" element={<PerformanceAnalytics />} />
                        
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