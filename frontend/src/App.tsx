import React, { useEffect, lazy, Suspense } from 'react';
import { HashRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ConfigProvider, Spin } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-tw';
import './App.css';

// Utils
import { setNavigate } from './utils/router';
import { features } from './config/features';

// Contexts
import { AuthProvider } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { WebSocketProvider } from './contexts/WebSocketContext';

// Common Components
import ErrorBoundary from './components/common/ErrorBoundary';
import SessionManager from './components/common/SessionManager';
import WebSocketManager from './components/common/WebSocketManager';

// Loading fallback component
const PageLoader = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    minHeight: '400px' 
  }}>
    <Spin size="large" tip="載入中..." />
  </div>
);

// Pages/Components - Lazy loaded
const Login = lazy(() => import('./components/Login'));
const ForgotPassword = lazy(() => import('./components/ForgotPassword'));
const ResetPassword = lazy(() => import('./components/ResetPassword'));
const MainLayout = lazy(() => import('./components/MainLayout'));
const Dashboard = lazy(() => import('./components/dashboard/DashboardOptimized'));
const CustomerManagement = lazy(() => import('./pages/office/CustomerManagement'));
const OrderManagement = lazy(() => import('./pages/office/OrderManagement'));
const RoutePlanning = lazy(() => import('./pages/dispatch/RoutePlanning'));
const DriverAssignment = lazy(() => import('./pages/dispatch/DriverAssignment'));
const EmergencyDispatch = lazy(() => import('./pages/dispatch/EmergencyDispatch'));
const DispatchDashboard = lazy(() => import('./pages/dispatch/DispatchDashboard'));
const DeliveryHistory = lazy(() => import('./components/office/DeliveryHistory'));
const UserProfile = lazy(() => import('./components/UserProfile'));

// Driver Pages - Lazy loaded
const DriverDashboard = lazy(() => import('./pages/driver/DriverDashboard'));
const RouteDetails = lazy(() => import('./pages/driver/RouteDetails'));
const DeliveryView = lazy(() => import('./pages/driver/DeliveryView'));
const DriverNavigation = lazy(() => import('./pages/driver/DriverNavigation'));
const DeliveryScanner = lazy(() => import('./pages/driver/DeliveryScanner'));

// Customer Pages - Lazy loaded
const CustomerPortal = lazy(() => import('./pages/customer/CustomerPortal'));
const OrderTracking = lazy(() => import('./pages/customer/OrderTracking'));

// Analytics Pages - Lazy loaded with prefetch
const ReportingDashboard = lazy(() => 
  import(/* webpackPrefetch: true */ './pages/analytics/ReportingDashboard')
);
const AnalyticsPage = lazy(() => 
  import(/* webpackPrefetch: true */ './pages/AnalyticsPage')
);

// Admin Pages - Lazy loaded with prefetch for frequent users
const ExecutiveDashboard = lazy(() => 
  import(/* webpackPrefetch: true */ './pages/admin/ExecutiveDashboard')
);
const OperationsDashboard = lazy(() => 
  import(/* webpackPrefetch: true */ './pages/admin/OperationsDashboard')
);
const FinancialDashboard = lazy(() => 
  import(/* webpackPrefetch: true */ './pages/admin/FinancialDashboard')
);
const PerformanceAnalytics = lazy(() => 
  import(/* webpackPrefetch: true */ './pages/admin/PerformanceAnalytics')
);

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
  // Prevent infinite reload loops
  useEffect(() => {
    const reloadKey = 'last_reload_time';
    const maxReloadsKey = 'reload_count';
    const now = Date.now();
    const lastReload = parseInt(sessionStorage.getItem(reloadKey) || '0');
    const reloadCount = parseInt(sessionStorage.getItem(maxReloadsKey) || '0');
    
    // If last reload was less than 3 seconds ago, increment counter
    if (now - lastReload < 3000) {
      const newCount = reloadCount + 1;
      sessionStorage.setItem(maxReloadsKey, newCount.toString());
      
      // If we've reloaded more than 3 times in quick succession, stop
      if (newCount > 3) {
        console.error('🚨 Reload loop detected! Breaking the cycle.');
        sessionStorage.removeItem(reloadKey);
        sessionStorage.removeItem(maxReloadsKey);
        // Clear any problematic auth state
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('token_expiry');
        return;
      }
    } else {
      // Reset counter if enough time has passed
      sessionStorage.setItem(maxReloadsKey, '1');
    }
    
    sessionStorage.setItem(reloadKey, now.toString());
    
    // Clear reload tracking after 10 seconds
    const cleanup = setTimeout(() => {
      sessionStorage.removeItem(reloadKey);
      sessionStorage.removeItem(maxReloadsKey);
    }, 10000);
    
    return () => clearTimeout(cleanup);
  }, []);

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
                    <Suspense fallback={<PageLoader />}>
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
                        <Route path="analytics/dashboard" element={<AnalyticsPage />} />
                        
                        {/* Admin Routes */}
                        <Route path="admin/executive" element={<ExecutiveDashboard />} />
                        <Route path="admin/operations" element={<OperationsDashboard />} />
                        {features.financialReports && (
                          <Route path="admin/financial" element={<FinancialDashboard />} />
                        )}
                        <Route path="admin/performance" element={<PerformanceAnalytics />} />
                        
                        <Route path="profile" element={<UserProfile />} />
                      </Route>
                    </Routes>
                    </Suspense>
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