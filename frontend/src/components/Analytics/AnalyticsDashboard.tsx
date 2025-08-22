import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Tabs,
  Spin,
  Alert,
  Button,
  Tooltip,
} from 'antd';
import {
  ReloadOutlined,
  RiseOutlined,
  FallOutlined,
  CarOutlined,
  EnvironmentOutlined,
  TruckOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { format, subDays } from 'date-fns';
import { zhTW } from 'date-fns/locale';
import axios from 'axios';

import DailyMetricsCard from './DailyMetricsCard';
import FuelSavingsChart from './FuelSavingsChart';
import DriverPerformanceTable from './DriverPerformanceTable';
import DeliveryHeatmap from './DeliveryHeatmap';
import WeeklyTrendChart from './WeeklyTrendChart';
import RouteOptimizationGauge from './RouteOptimizationGauge';

interface DashboardSummary {
  today: {
    date: string;
    total_routes: number;
    total_deliveries: number;
    total_distance_km: number;
    fuel_saved_liters: number;
    cost_saved_twd: number;
    on_time_percentage: number;
  };
  changes: {
    routes_change: number;
    deliveries_change: number;
    distance_change: number;
    fuel_savings_change: number;
  };
  highlights: {
    best_driver: {
      driver_id: string;
      driver_name: string;
      on_time_pct: number;
    } | null;
    peak_hour: number | null;
    optimization_effectiveness: number;
  };
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const { TabPane } = Tabs;
const { Title, Text } = Typography;

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && <div style={{ padding: '24px 0' }}>{children}</div>}
    </div>
  );
}

const AnalyticsDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get<DashboardSummary>(
        '/api/v1/analytics/dashboard/summary'
      );
      
      setDashboardData(response.data);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('無法載入儀表板資料，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    
    // Auto-refresh every 5 minutes
    const interval = window.setInterval(fetchDashboardData, 5 * 60 * 1000);
    
    return () => window.clearInterval(interval);
  }, []);


  const handleRefresh = () => {
    fetchDashboardData();
  };

  const getChangeIcon = (change: number) => {
    if (change > 0) {
      return <RiseOutlined style={{ color: '#52c41a' }} />;
    } else if (change < 0) {
      return <FallOutlined style={{ color: '#ff4d4f' }} />;
    }
    return null;
  };

  const formatChange = (change: number) => {
    const sign = change > 0 ? '+' : '';
    return `${sign}${change.toFixed(1)}%`;
  };

  if (loading && !dashboardData) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert type="error" message={error} style={{ marginBottom: 16 }} />
    );
  }

  if (!dashboardData) {
    return null;
  }

  const { today, changes, highlights } = dashboardData;

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>
          路線分析儀表板
        </Title>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Text type="secondary">
            最後更新: {format(lastRefresh, 'HH:mm', { locale: zhTW })}
          </Text>
          <Tooltip title="重新整理">
            <Button size="small" icon={<ReloadOutlined />} onClick={handleRefresh} />
          </Tooltip>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <DailyMetricsCard
            title="今日路線"
            value={today.total_routes}
            change={changes.routes_change}
            icon={<EnvironmentOutlined />}
            color="primary"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <DailyMetricsCard
            title="總配送數"
            value={today.total_deliveries}
            change={changes.deliveries_change}
            icon={<TruckOutlined />}
            color="secondary"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <DailyMetricsCard
            title="節省燃料"
            value={`${today.fuel_saved_liters.toFixed(1)}L`}
            change={changes.fuel_savings_change}
            icon={<CarOutlined />}
            color="success"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <DailyMetricsCard
            title="準時率"
            value={`${today.on_time_percentage.toFixed(1)}%`}
            icon={<ClockCircleOutlined />}
            color="info"
            showChange={false}
          />
        </Col>
      </Row>

      {/* Highlights */}
      {highlights.best_driver && (
        <Card style={{ padding: 16, marginBottom: 24, backgroundColor: '#e6f7ff' }}>
          <Text strong style={{ color: '#1890ff' }}>
            🏆 今日最佳司機: {highlights.best_driver.driver_name} 
            (準時率 {highlights.best_driver.on_time_pct.toFixed(1)}%)
          </Text>
        </Card>
      )}

      {/* Tabs for Different Views */}
      <Card>
        <Tabs
          activeKey={activeTab.toString()}
          onChange={(key) => setActiveTab(parseInt(key))}
          type="line"
        >
          <TabPane tab="總覽" key="0">
            <Row gutter={[24, 24]}>
              <Col xs={24} lg={16}>
                <WeeklyTrendChart />
              </Col>
              <Col xs={24} lg={8}>
                <RouteOptimizationGauge 
                  value={highlights.optimization_effectiveness} 
                />
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="燃料分析" key="1">
            <FuelSavingsChart />
          </TabPane>

          <TabPane tab="司機績效" key="2">
            <DriverPerformanceTable />
          </TabPane>

          <TabPane tab="配送熱圖" key="3">
            <DeliveryHeatmap peakHour={highlights.peak_hour} />
          </TabPane>

          <TabPane tab="週趨勢" key="4">
            <WeeklyTrendChart detailed />
          </TabPane>
        </Tabs>
      </Card>

      {/* Summary Stats */}
      <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
        <Col xs={24} md={8}>
          <Card style={{ padding: 24, textAlign: 'center' }}>
            <Title level={5} style={{ marginBottom: 8 }}>
              本日總節省
            </Title>
            <Title level={2} style={{ color: '#52c41a', margin: 0 }}>
              ${today.cost_saved_twd.toLocaleString()}
            </Title>
            <Text type="secondary">
              新台幣
            </Text>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card style={{ padding: 24, textAlign: 'center' }}>
            <Title level={5} style={{ marginBottom: 8 }}>
              總行駛距離
            </Title>
            <Title level={2} style={{ color: '#1890ff', margin: 0 }}>
              {today.total_distance_km.toFixed(1)}
            </Title>
            <Text type="secondary">
              公里
            </Text>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card style={{ padding: 24, textAlign: 'center' }}>
            <Title level={5} style={{ marginBottom: 8 }}>
              尖峰時段
            </Title>
            <Title level={2} style={{ color: '#722ed1', margin: 0 }}>
              {highlights.peak_hour !== null ? `${highlights.peak_hour}:00` : '--:--'}
            </Title>
            <Text type="secondary">
              最多配送
            </Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AnalyticsDashboard;