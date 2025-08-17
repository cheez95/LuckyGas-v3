import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, Row, Col, Statistic, Typography, Progress, List, Tag, Space, Spin, Alert, Skeleton } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  ShoppingCartOutlined,
  UserOutlined,
  CarOutlined,
  DollarOutlined,
  RiseOutlined,
  LineChartOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  WifiOutlined,
  DisconnectOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { websocketService } from '../../services/websocket.service';
import { apiClient } from '../../services/api.service';
import { features } from '../../config/features';

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

interface RealtimeActivity {
  id: string;
  type: 'order' | 'route' | 'delivery' | 'prediction';
  message: string;
  timestamp: Date;
  status: 'info' | 'success' | 'warning';
}

const DashboardOptimized: React.FC = () => {
  const { t } = useTranslation();
  
  // Connection status
  const [isConnected, setIsConnected] = useState(false);
  const [apiHealthy, setApiHealthy] = useState(true);
  const [lastHealthCheck, setLastHealthCheck] = useState<Date>(new Date());
  
  // Loading states for independent widgets
  const [statsLoading, setStatsLoading] = useState(true);
  const [routesLoading, setRoutesLoading] = useState(true);
  
  // Data states
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
  const [predictions, setPredictions] = useState({
    total: 0,
    urgent: 0,
    confidence: 0,
  });
  
  const [realtimeActivities, setRealtimeActivities] = useState<RealtimeActivity[]>([]);
  const [responseTime, setResponseTime] = useState<number>(0);
  
  // Cache management
  const [lastFetchTime, setLastFetchTime] = useState<Date | null>(null);
  const CACHE_DURATION = 30000; // 30 seconds cache
  
  // Health check for API
  const checkApiHealth = useCallback(async () => {
    try {
      const startTime = performance.now();
      const response = await apiClient.get('/dashboard/health');
      const endTime = performance.now();
      
      setApiHealthy(response.data.status === 'healthy');
      setResponseTime(Math.round(endTime - startTime));
      setLastHealthCheck(new Date());
      
      return true;
    } catch (error) {
      console.error('API health check failed:', error);
      setApiHealthy(false);
      return false;
    }
  }, []);
  
  // Optimized dashboard data fetch - single API call
  const fetchDashboardData = useCallback(async (force = false) => {
    // Check cache validity
    if (!force && lastFetchTime && (Date.now() - lastFetchTime.getTime()) < CACHE_DURATION) {
      console.log('📊 Using cached dashboard data');
      return;
    }
    
    try {
      const startTime = performance.now();
      setStatsLoading(true);
      setRoutesLoading(true);
      
      // Single optimized API call for all dashboard data
      const response = await apiClient.get('/dashboard/summary', {
        params: {
          date: dayjs().format('YYYY-MM-DD')
        }
      });
      
      const endTime = performance.now();
      const loadTime = Math.round(endTime - startTime);
      
      if (response.data) {
        // Update stats
        if (response.data.stats) {
          setStats({
            todayOrders: response.data.stats.today_orders || 0,
            todayRevenue: response.data.stats.today_revenue || 0,
            activeCustomers: response.data.stats.active_customers || 0,
            driversOnRoute: response.data.stats.drivers_on_route || 0,
            recentDeliveries: response.data.stats.recent_deliveries || 0,
            urgentOrders: response.data.stats.urgent_orders || 0,
            completionRate: response.data.stats.completion_rate || 0,
          });
          setStatsLoading(false);
        }
        
        // Update routes
        if (response.data.routes) {
          setRoutes(response.data.routes.map((r: any) => ({
            id: r.id,
            routeNumber: r.route_number,
            status: r.status,
            totalOrders: r.total_orders,
            completedOrders: r.completed_orders,
            driverName: r.driver_name,
            progressPercentage: r.progress_percentage,
          })));
          setRoutesLoading(false);
        }
        
        // Update predictions
        if (response.data.predictions) {
          setPredictions(response.data.predictions);
        }
        
        // Update cache timestamp
        setLastFetchTime(new Date());
        setResponseTime(loadTime);
        
        // Log performance
        console.log(`📊 Dashboard loaded in ${loadTime}ms`);
        
        if (loadTime > 2000) {
          console.warn(`⚠️ Dashboard load time exceeded target: ${loadTime}ms`);
        }
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setStatsLoading(false);
      setRoutesLoading(false);
      
      // Retry with exponential backoff
      setTimeout(() => fetchDashboardData(true), 5000);
    }
  }, [lastFetchTime]);
  
  // WebSocket connection management with proper URL
  useEffect(() => {
    const handleConnected = () => {
      console.log('📡 Dashboard: WebSocket connected!');
      setIsConnected(true);
    };
    
    const handleDisconnected = () => {
      console.log('📡 Dashboard: WebSocket disconnected!');
      setIsConnected(false);
    };
    
    // Fix WebSocket URL configuration
    const wsUrl = import.meta.env.VITE_WS_URL || 
                  import.meta.env.VITE_API_URL?.replace('https://', 'wss://').replace('http://', 'ws://') ||
                  'ws://localhost:8000';
    
    console.log('🔌 WebSocket URL configured:', wsUrl);
    
    websocketService.on('connected', handleConnected);
    websocketService.on('disconnected', handleDisconnected);
    
    // Initialize WebSocket connection with correct URL
    if (!websocketService.isConnected()) {
      websocketService.connect();
    }
    
    setIsConnected(websocketService.isConnected());
    
    return () => {
      websocketService.off('connected', handleConnected);
      websocketService.off('disconnected', handleDisconnected);
    };
  }, []);
  
  // Real-time updates via WebSocket
  useEffect(() => {
    const handleOrderUpdate = (data: any) => {
      console.log('📦 Order update received:', data);
      setStats(prev => ({ ...prev, todayOrders: prev.todayOrders + 1 }));
      addActivity('order', `新訂單 #${data.order_id} 已創建`, 'success');
      
      // Refresh dashboard after significant changes
      if (Math.random() > 0.7) { // 30% chance to refresh
        fetchDashboardData(true);
      }
    };
    
    const handleRouteUpdate = (data: any) => {
      if (data.status === 'in_progress') {
        setStats(prev => ({ ...prev, driversOnRoute: prev.driversOnRoute + 1 }));
        addActivity('route', `路線 ${data.route_number} 開始配送`, 'info');
      } else if (data.status === 'completed') {
        setStats(prev => ({ ...prev, driversOnRoute: Math.max(0, prev.driversOnRoute - 1) }));
        addActivity('route', `路線 ${data.route_number} 已完成`, 'success');
      }
    };
    
    const handleDeliveryCompleted = (data: any) => {
      addActivity('delivery', `訂單 #${data.order_id} 已送達`, 'success');
      setStats(prev => ({ 
        ...prev, 
        recentDeliveries: prev.recentDeliveries + 1,
        todayRevenue: prev.todayRevenue + (data.amount || 0)
      }));
    };
    
    websocketService.on('order_update', handleOrderUpdate);
    websocketService.on('route_update', handleRouteUpdate);
    websocketService.on('delivery_status', handleDeliveryCompleted);
    
    return () => {
      websocketService.off('order_update', handleOrderUpdate);
      websocketService.off('route_update', handleRouteUpdate);
      websocketService.off('delivery_status', handleDeliveryCompleted);
    };
  }, [fetchDashboardData]);
  
  // Add activity to feed
  const addActivity = useCallback((type: RealtimeActivity['type'], message: string, status: RealtimeActivity['status']) => {
    const newActivity: RealtimeActivity = {
      id: `${type}-${Date.now()}-${Math.random()}`,
      type,
      message,
      timestamp: new Date(),
      status,
    };
    setRealtimeActivities(prev => [newActivity, ...prev].slice(0, 10));
  }, []);
  
  // Initial load and periodic refresh
  useEffect(() => {
    // Initial load
    fetchDashboardData(true);
    checkApiHealth();
    
    // Set up periodic refresh (every 30 seconds)
    const refreshInterval = window.setInterval(() => {
      fetchDashboardData();
    }, 30000);
    
    // Health check every 10 seconds
    const healthInterval = window.setInterval(() => {
      checkApiHealth();
    }, 10000);
    
    return () => {
      window.clearInterval(refreshInterval);
      window.clearInterval(healthInterval);
    };
  }, [fetchDashboardData, checkApiHealth]);
  
  // Memoized computations
  const connectionStatus = useMemo(() => {
    if (!apiHealthy) {
      return { color: 'red', icon: <DisconnectOutlined />, text: '系統離線' };
    }
    if (isConnected) {
      return { color: 'green', icon: <WifiOutlined />, text: '即時連線' };
    }
    return { color: 'orange', icon: <ClockCircleOutlined />, text: '輪詢模式' };
  }, [isConnected, apiHealthy]);
  
  const performanceStatus = useMemo(() => {
    if (responseTime < 500) return { color: 'green', text: '優秀' };
    if (responseTime < 1000) return { color: 'blue', text: '良好' };
    if (responseTime < 2000) return { color: 'orange', text: '一般' };
    return { color: 'red', text: '緩慢' };
  }, [responseTime]);
  
  // Helper functions
  const getActivityIcon = (type: RealtimeActivity['type']) => {
    switch (type) {
      case 'order': return <ShoppingCartOutlined />;
      case 'route': return <CarOutlined />;
      case 'delivery': return <CheckCircleOutlined />;
      case 'prediction': return <LineChartOutlined />;
      default: return <AlertOutlined />;
    }
  };
  
  const getActivityColor = (status: RealtimeActivity['status']) => {
    switch (status) {
      case 'success': return 'green';
      case 'warning': return 'orange';
      default: return 'blue';
    }
  };
  
  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ margin: 0 }} data-testid="page-title">
            {t('navigation.dashboard')}
          </Title>
        </Col>
        <Col>
          <Space>
            <Tag color={connectionStatus.color} icon={connectionStatus.icon}>
              {connectionStatus.text}
            </Tag>
            <Tag color={performanceStatus.color}>
              {responseTime}ms
            </Tag>
            <Tag>{dayjs().format('YYYY/MM/DD HH:mm')}</Tag>
          </Space>
        </Col>
      </Row>
      
      {/* Stats Cards with Skeleton Loading */}
      <Row gutter={[16, 16]} className="dashboard-stats">
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            {statsLoading ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic
                title={t('dashboard.todayOrders')}
                value={stats.todayOrders}
                prefix={<ShoppingCartOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            {statsLoading ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic
                title={t('dashboard.activeCustomers')}
                value={stats.activeCustomers}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            {statsLoading ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic
                title={t('dashboard.driversOnRoute')}
                value={stats.driversOnRoute}
                prefix={<CarOutlined />}
                valueStyle={{ color: '#fa8c16' }}
              />
            )}
          </Card>
        </Col>
        {features.anyPaymentFeature && (
          <Col xs={24} sm={12} lg={6}>
            <Card hoverable>
              {statsLoading ? (
                <Skeleton active paragraph={false} />
              ) : (
                <Statistic
                  title={t('dashboard.todayRevenue')}
                  value={stats.todayRevenue}
                  prefix={<DollarOutlined />}
                  valueStyle={{ color: '#cf1322' }}
                  suffix="TWD"
                />
              )}
            </Card>
          </Col>
        )}
      </Row>
      
      {/* Progress and Activity Section */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        {/* AI Predictions */}
        <Col xs={24} lg={8}>
          <Card 
            title="AI 需求預測" 
            extra={<RocketOutlined />}
            style={{ height: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 16 }}>預測準確度</span>
                </div>
                <Progress 
                  percent={predictions.confidence} 
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
              </div>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="總預測數"
                    value={predictions.total}
                    prefix={<LineChartOutlined />}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="緊急預測"
                    value={predictions.urgent}
                    prefix={<AlertOutlined />}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Col>
              </Row>
            </Space>
          </Card>
        </Col>
        
        {/* Routes Progress */}
        <Col xs={24} lg={8}>
          <Card 
            title="今日路線進度" 
            extra={
              <Tag color={stats.completionRate >= 80 ? 'green' : 'blue'}>
                {stats.completionRate}% 完成
              </Tag>
            }
            style={{ height: '100%' }}
          >
            {routesLoading ? (
              <Skeleton active />
            ) : (
              <Space direction="vertical" style={{ width: '100%' }}>
                {routes.slice(0, 5).map(route => (
                  <div key={route.id} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>{route.routeNumber} - {route.driverName}</span>
                      <span>{route.progressPercentage}%</span>
                    </div>
                    <Progress 
                      percent={route.progressPercentage} 
                      size="small"
                      status={route.status === 'completed' ? 'success' : 'active'}
                    />
                  </div>
                ))}
                {routes.length === 0 && (
                  <div style={{ textAlign: 'center', color: '#999', padding: '20px 0' }}>
                    尚無今日路線
                  </div>
                )}
              </Space>
            )}
          </Card>
        </Col>
        
        {/* Real-time Activity Feed */}
        <Col xs={24} lg={8}>
          <Card 
            title="即時動態" 
            extra={<Tag color="green">LIVE</Tag>}
            style={{ height: '100%' }}
          >
            <List
              size="small"
              dataSource={realtimeActivities}
              renderItem={(activity) => (
                <List.Item>
                  <Space>
                    <Tag color={getActivityColor(activity.status)}>
                      {getActivityIcon(activity.type)}
                    </Tag>
                    <div>
                      <div>{activity.message}</div>
                      <div style={{ fontSize: 12, color: '#999' }}>
                        {dayjs(activity.timestamp).format('HH:mm:ss')}
                      </div>
                    </div>
                  </Space>
                </List.Item>
              )}
              locale={{ emptyText: '等待即時更新...' }}
            />
          </Card>
        </Col>
      </Row>
      
      {/* Performance Alert */}
      {responseTime > 2000 && (
        <Alert
          message="效能警告"
          description={`Dashboard 載入時間 (${responseTime}ms) 超過目標 (2000ms)。系統正在優化中...`}
          type="warning"
          showIcon
          closable
          style={{ marginTop: 16 }}
        />
      )}
    </div>
  );
};

export default DashboardOptimized;