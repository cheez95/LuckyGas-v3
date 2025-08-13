import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Typography, Progress, List, Tag, Space, Spin, Alert } from 'antd';
import {
  ShoppingCartOutlined,
  UserOutlined,
  CarOutlined,
  DollarOutlined,
  RiseOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const { Title } = Typography;

interface DashboardStats {
  todayOrders: number;
  todayRevenue: number;
  activeCustomers: number;
  driversOnRoute: number;
  recentDeliveries: number;
  urgentOrders: number;
  completionRate: number;
}

interface RouteProgress {
  id: number;
  routeNumber: string;
  status: string;
  totalOrders: number;
  completedOrders: number;
  driverName?: string;
  progressPercentage: number;
}

const DashboardWorking: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats>({
    todayOrders: 0,
    todayRevenue: 0,
    activeCustomers: 0,
    driversOnRoute: 0,
    recentDeliveries: 0,
    urgentOrders: 0,
    completionRate: 0,
  });
  const [routes, setRoutes] = useState<RouteProgress[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('http://localhost:8000/api/v1/dashboard/summary', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      if (response.data) {
        setStats(response.data.stats);
        setRoutes(response.data.routes || []);
        setError(null);
      }
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      // Use mock data if backend fails
      setStats({
        todayOrders: 42,
        todayRevenue: 15280,
        activeCustomers: 238,
        driversOnRoute: 5,
        recentDeliveries: 128,
        urgentOrders: 3,
        completionRate: 87.5,
      });
      setRoutes([
        {
          id: 1,
          routeNumber: "R001",
          status: "進行中",
          totalOrders: 15,
          completedOrders: 8,
          driverName: "陳大明",
          progressPercentage: 53
        },
        {
          id: 2,
          routeNumber: "R002",
          status: "進行中",
          totalOrders: 12,
          completedOrders: 10,
          driverName: "李小華",
          progressPercentage: 83
        }
      ]);
      setError('使用模擬數據 (後端連接失敗)');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="載入儀表板..." />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>營運儀表板</Title>
      
      {error && (
        <Alert
          message="注意"
          description={error}
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日訂單"
              value={stats.todayOrders}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日營收"
              value={stats.todayRevenue}
              prefix={<DollarOutlined />}
              suffix="TWD"
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活躍客戶"
              value={stats.activeCustomers}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="配送中司機"
              value={stats.driversOnRoute}
              prefix={<CarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Route Progress */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="路線進度" extra={<Tag color="blue">即時更新</Tag>}>
            <List
              dataSource={routes}
              renderItem={(route) => (
                <List.Item>
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Space>
                        <strong>{route.routeNumber}</strong>
                        <Tag color={route.status === '進行中' ? 'processing' : 'default'}>
                          {route.status}
                        </Tag>
                        <span>{route.driverName}</span>
                      </Space>
                      <span>{route.completedOrders}/{route.totalOrders} 完成</span>
                    </div>
                    <Progress
                      percent={route.progressPercentage}
                      strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                      }}
                    />
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="AI 預測分析">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="預測今日訂單"
                  value={125}
                  prefix={<RiseOutlined />}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="建議司機數"
                  value={5}
                  prefix={<CarOutlined />}
                />
              </Col>
              <Col span={24}>
                <div style={{ marginTop: 16 }}>
                  <strong>尖峰時段預測：</strong>
                  <div style={{ marginTop: 8 }}>
                    <Tag color="red">09:00-11:00</Tag>
                    <Tag color="orange">14:00-16:00</Tag>
                  </div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Quick Stats */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24}>
          <Card>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Statistic
                  title="緊急訂單"
                  value={stats.urgentOrders}
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="完成率"
                  value={stats.completionRate}
                  suffix="%"
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="近期配送"
                  value={stats.recentDeliveries}
                  prefix={<RocketOutlined />}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="平均配送時間"
                  value={28}
                  suffix="分鐘"
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default DashboardWorking;