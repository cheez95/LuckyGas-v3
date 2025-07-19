import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-tw';
import './App.css';

// Contexts
import { AuthProvider } from './contexts/AuthContext';

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
      <Router>
        <AuthProvider>
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
        </AuthProvider>
      </Router>
    </ConfigProvider>
  );
};

export default App;