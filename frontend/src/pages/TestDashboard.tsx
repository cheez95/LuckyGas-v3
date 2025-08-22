import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, Table, message, Spin, Alert, Tag, Progress } from 'antd';
import {
  ShoppingCartOutlined,
  UserOutlined,
  CarOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import api from '../services/api';
import { safeErrorMonitor } from '../services/safeErrorMonitor';

const TestDashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    totalOrders: 0,
    pendingOrders: 0,
    completedOrders: 0,
    totalRevenue: 0,
    activeDrivers: 0,
    totalCustomers: 0,
  });
  const [recentOrders, setRecentOrders] = useState<any[]>([]);
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [monitorStatus, setMonitorStatus] = useState<any>(null);
  const [memoryUsage, setMemoryUsage] = useState<number>(0);

  useEffect(() => {
    checkSystemStatus();
    testAPIConnection();
    checkMemoryUsage();
  }, []);

  const checkSystemStatus = () => {
    // Check SafeErrorMonitor status
    const status = safeErrorMonitor.getStatus();
    setMonitorStatus(status);
  };

  const testAPIConnection = async () => {
    setLoading(true);
    try {
      // Test API connectivity
      const response = await fetch(`${import.meta.env.VITE_API_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        setApiStatus('online');
        message.success('API connection successful');
      } else {
        setApiStatus('offline');
        message.warning(`API returned status: ${response.status}`);
      }
    } catch (error) {
      setApiStatus('offline');
      message.error('API connection failed');
      console.error('API test failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkMemoryUsage = () => {
    if (performance.memory) {
      const used = performance.memory.usedJSHeapSize / 1048576; // Convert to MB
      setMemoryUsage(Math.round(used));
    }
  };

  const testErrorLogging = () => {
    const testError = new Error('Test error for monitoring system');
    safeErrorMonitor.logError(testError, { context: 'TestDashboard' });
    message.info('Test error logged to monitoring system');
    
    // Refresh monitor status
    setTimeout(checkSystemStatus, 100);
  };

  const testDataFetch = async () => {
    setLoading(true);
    try {
      // Simulate fetching data
      const mockData = {
        totalOrders: Math.floor(Math.random() * 1000),
        pendingOrders: Math.floor(Math.random() * 50),
        completedOrders: Math.floor(Math.random() * 900),
        totalRevenue: Math.floor(Math.random() * 1000000),
        activeDrivers: Math.floor(Math.random() * 20),
        totalCustomers: Math.floor(Math.random() * 500),
      };
      
      setStats(mockData);
      
      // Mock recent orders
      const mockOrders = Array.from({ length: 5 }, (_, i) => ({
        key: i,
        orderNumber: `ORD-${Date.now()}-${i}`,
        customer: `Customer ${i + 1}`,
        status: ['pending', 'processing', 'delivered'][Math.floor(Math.random() * 3)],
        amount: Math.floor(Math.random() * 5000),
      }));
      
      setRecentOrders(mockOrders);
      message.success('Data fetched successfully');
    } catch (error) {
      message.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Order Number',
      dataIndex: 'orderNumber',
      key: 'orderNumber',
    },
    {
      title: 'Customer',
      dataIndex: 'customer',
      key: 'customer',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: any = {
          pending: 'orange',
          processing: 'blue',
          delivered: 'green',
        };
        return <Tag color={colors[status]}>{status.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => `NT$ ${amount.toLocaleString()}`,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1>Test Dashboard - System Verification</h1>
      
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Alert
            message="System Status"
            description={
              <div>
                <p><strong>Safe Error Monitor:</strong> {monitorStatus ? 'Active' : 'Not Available'}</p>
                {monitorStatus && (
                  <>
                    <p>Circuit Open: {monitorStatus.circuitOpen ? 'Yes' : 'No'}</p>
                    <p>Failure Count: {monitorStatus.failureCount}</p>
                    <p>Queue Size: {monitorStatus.queueSize}</p>
                    <p>Kill Switch: {monitorStatus.killSwitchActive ? 'Active' : 'Inactive'}</p>
                  </>
                )}
                <p><strong>API Status:</strong> {apiStatus === 'checking' ? 'Checking...' : apiStatus === 'online' ? '🟢 Online' : '🔴 Offline'}</p>
                <p><strong>Memory Usage:</strong> {memoryUsage} MB</p>
              </div>
            }
            type={apiStatus === 'online' ? 'success' : apiStatus === 'offline' ? 'error' : 'info'}
            showIcon
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={6}>
          <Button type="primary" onClick={testAPIConnection} loading={loading}>
            Test API Connection
          </Button>
        </Col>
        <Col span={6}>
          <Button onClick={testDataFetch} loading={loading}>
            Fetch Mock Data
          </Button>
        </Col>
        <Col span={6}>
          <Button onClick={testErrorLogging}>
            Test Error Logging
          </Button>
        </Col>
        <Col span={6}>
          <Button onClick={checkSystemStatus} icon={<ReloadOutlined />}>
            Refresh Status
          </Button>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <Statistic
              title="Total Orders"
              value={stats.totalOrders}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <Statistic
              title="Pending Orders"
              value={stats.pendingOrders}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <Statistic
              title="Active Drivers"
              value={stats.activeDrivers}
              prefix={<CarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <Statistic
              title="Total Revenue"
              value={stats.totalRevenue}
              prefix={<DollarOutlined />}
              suffix="NT$"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title="Recent Orders" loading={loading}>
            <Table
              columns={columns}
              dataSource={recentOrders}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="Memory Performance">
            <Progress
              percent={Math.min((memoryUsage / 100) * 100, 100)}
              status={memoryUsage > 80 ? 'exception' : memoryUsage > 60 ? 'normal' : 'success'}
              format={() => `${memoryUsage} MB`}
            />
            <p style={{ marginTop: 8 }}>
              Target: Keep under 100MB
            </p>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="WebSocket Status">
            <p>Status: Not Connected (Test Mode)</p>
            <p>Messages: 0</p>
            <p>Reconnect Attempts: 0</p>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default TestDashboard;