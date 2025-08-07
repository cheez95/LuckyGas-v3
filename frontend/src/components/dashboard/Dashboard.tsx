import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Typography, Progress, List, Tag, Space, Spin, Alert } from 'antd';
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
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { websocketService } from '../../services/websocket.service';
import { orderService } from '../../services/order.service';
import { customerService } from '../../services/customer.service';
import { routeService } from '../../services/route.service';
import { predictionService } from '../../services/prediction.service';
import { features } from '../../config/features';

const { Title } = Typography;

interface RealtimeActivity {
  id: string;
  type: 'order' | 'route' | 'delivery' | 'prediction';
  message: string;
  timestamp: Date;
  status: 'info' | 'success' | 'warning';
}

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const [isConnected, setIsConnected] = useState(false);
  
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    todayOrders: 0,
    activeCustomers: 0,
    driversOnRoute: 0,
    todayRevenue: 0,
  });
  const [predictions, setPredictions] = useState({
    total: 0,
    urgent: 0,
    confidence: 0,
  });
  const [realtimeActivities, setRealtimeActivities] = useState<RealtimeActivity[]>([]);
  const [todayRoutes, setTodayRoutes] = useState<any[]>([]);

  // Fetch initial statistics
  const fetchStatistics = async () => {
    try {
      setLoading(true);
      const today = dayjs().format('YYYY-MM-DD');
      
      // Fetch today's orders
      const orders = await orderService.getOrders({
        date_from: today,
        date_to: today,
      });
      
      // Fetch active customers
      const customers = await customerService.getCustomers({ is_active: true, limit: 5000 });
      
      // Fetch today's routes
      const routes = await routeService.getRoutes({
        date_from: dayjs().format('YYYY-MM-DD'),
        date_to: dayjs().format('YYYY-MM-DD'),
      });
      setTodayRoutes(routes);
      
      // Calculate statistics
      const driversOnRoute = routes.filter(r => r.status === 'in_progress').length;
      const todayRevenue = features.anyPaymentFeature ? orders.reduce((sum, order) => {
        return sum + order.order_items.reduce((itemSum, item) => itemSum + item.total_price, 0);
      }, 0) : 0;
      
      setStats({
        todayOrders: orders.length,
        activeCustomers: customers.total,
        driversOnRoute,
        todayRevenue,
      });
      
      // Fetch prediction summary
      const predictionSummary = await predictionService.getPredictionSummary();
      setPredictions({
        total: predictionSummary.total,
        urgent: predictionSummary.urgent,
        confidence: Math.round(predictionSummary.average_confidence * 100),
      });
    } catch (error) {
      console.error('Failed to fetch dashboard statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  // Initial data fetch
  useEffect(() => {
    fetchStatistics();
  }, []);

  // WebSocket connection status
  useEffect(() => {
    const handleConnected = () => {
      console.log('📡 Dashboard: WebSocket connected!');
      setIsConnected(true);
    };
    const handleDisconnected = () => {
      console.log('📡 Dashboard: WebSocket disconnected!');
      setIsConnected(false);
    };
    
    websocketService.on('connected', handleConnected);
    websocketService.on('disconnected', handleDisconnected);
    
    // Check current connection status
    const currentStatus = websocketService.isConnected();
    console.log('📡 Dashboard: Current WebSocket status:', currentStatus);
    setIsConnected(currentStatus);
    
    return () => {
      websocketService.off('connected', handleConnected);
      websocketService.off('disconnected', handleDisconnected);
    };
  }, []);

  // WebSocket listeners
  useEffect(() => {
    const handleOrderCreated = (data: any) => {
      console.log('📦 Dashboard: Order update received:', data);
      setStats(prev => ({ ...prev, todayOrders: prev.todayOrders + 1 }));
      addActivity('order', `新訂單 #${data.order_id} 已創建`, 'success');
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
      setStats(prev => ({ ...prev, todayRevenue: prev.todayRevenue + (data.amount || 0) }));
    };

    const handlePredictionGenerated = (data: any) => {
      setPredictions(prev => ({ ...prev, total: prev.total + data.count }));
      addActivity('prediction', `生成了 ${data.count} 個新預測`, 'info');
    };

    websocketService.on('order_update', handleOrderCreated);
    websocketService.on('route_update', handleRouteUpdate);
    websocketService.on('delivery_status', handleDeliveryCompleted);
    websocketService.on('prediction_ready', handlePredictionGenerated);

    return () => {
      websocketService.off('order_update', handleOrderCreated);
      websocketService.off('route_update', handleRouteUpdate);
      websocketService.off('delivery_status', handleDeliveryCompleted);
      websocketService.off('prediction_ready', handlePredictionGenerated);
    };
  }, []);

  // Add activity to the feed
  const addActivity = (type: RealtimeActivity['type'], message: string, status: RealtimeActivity['status']) => {
    const newActivity: RealtimeActivity = {
      id: `${type}-${Date.now()}`,
      type,
      message,
      timestamp: new Date(),
      status,
    };
    setRealtimeActivities(prev => [newActivity, ...prev].slice(0, 10)); // Keep last 10 activities
  };

  // Get activity icon
  const getActivityIcon = (type: RealtimeActivity['type']) => {
    switch (type) {
      case 'order': return <ShoppingCartOutlined />;
      case 'route': return <CarOutlined />;
      case 'delivery': return <CheckCircleOutlined />;
      case 'prediction': return <LineChartOutlined />;
      default: return <AlertOutlined />;
    }
  };

  // Get activity color
  const getActivityColor = (status: RealtimeActivity['status']) => {
    switch (status) {
      case 'success': return 'green';
      case 'warning': return 'orange';
      default: return 'blue';
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="載入中..." />
      </div>
    );
  }

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ margin: 0 }} data-testid="page-title">{t('navigation.dashboard')}</Title>
        </Col>
        <Col>
          <Space>
            {isConnected ? (
              <Tag color="green" icon={<CheckCircleOutlined />}>即時連線</Tag>
            ) : (
              <Tag color="red" icon={<ClockCircleOutlined />}>離線模式</Tag>
            )}
            <Tag>{dayjs().format('YYYY/MM/DD HH:mm')}</Tag>
          </Space>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="dashboard-stats">
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title={t('dashboard.todayOrders')}
              value={stats.todayOrders}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title={t('dashboard.activeCustomers')}
              value={stats.activeCustomers}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title={t('dashboard.driversOnRoute')}
              value={stats.driversOnRoute}
              prefix={<CarOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        {features.anyPaymentFeature && (
          <Col xs={24} sm={12} lg={6}>
            <Card hoverable>
              <Statistic
                title={t('dashboard.todayRevenue')}
                value={stats.todayRevenue}
                prefix={<DollarOutlined />}
                valueStyle={{ color: '#cf1322' }}
                suffix={t('dashboard.yuan')}
              />
            </Card>
          </Col>
        )}
      </Row>
      
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
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
              <Alert
                message="AI 預測系統"
                description="基於歷史數據和天氣資訊的智能預測"
                type="info"
                showIcon
              />
            </Space>
          </Card>
        </Col>
        
        <Col xs={24} lg={8}>
          <Card 
            title="今日路線進度" 
            style={{ height: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {todayRoutes.slice(0, 5).map(route => {
                const progress = Math.round((route.completed_orders / route.total_orders) * 100);
                return (
                  <div key={route.id} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>{route.route_number}</span>
                      <span>{progress}%</span>
                    </div>
                    <Progress 
                      percent={progress} 
                      size="small"
                      status={route.status === 'completed' ? 'success' : 'active'}
                    />
                  </div>
                );
              })}
              {todayRoutes.length === 0 && (
                <div style={{ textAlign: 'center', color: '#999', padding: '20px 0' }}>
                  尚無今日路線
                </div>
              )}
            </Space>
          </Card>
        </Col>
        
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

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="系統功能概覽">
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={12}>
                <Card size="small" hoverable>
                  <Space direction="vertical" align="center" style={{ width: '100%' }}>
                    <ShoppingCartOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                    <div>訂單管理</div>
                  </Space>
                </Card>
              </Col>
              <Col xs={12} sm={12}>
                <Card size="small" hoverable>
                  <Space direction="vertical" align="center" style={{ width: '100%' }}>
                    <CarOutlined style={{ fontSize: 32, color: '#52c41a' }} />
                    <div>路線優化</div>
                  </Space>
                </Card>
              </Col>
              <Col xs={12} sm={12}>
                <Card size="small" hoverable>
                  <Space direction="vertical" align="center" style={{ width: '100%' }}>
                    <LineChartOutlined style={{ fontSize: 32, color: '#fa8c16' }} />
                    <div>需求預測</div>
                  </Space>
                </Card>
              </Col>
              <Col xs={12} sm={12}>
                <Card size="small" hoverable>
                  <Space direction="vertical" align="center" style={{ width: '100%' }}>
                    <RiseOutlined style={{ fontSize: 32, color: '#eb2f96' }} />
                    <div>營運分析</div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={t('dashboard.upcomingFeatures')} data-testid="upcoming-features-card">
            <List
              size="small"
              dataSource={[
                t('dashboard.features.realTimeTracking'),
                t('dashboard.features.demandPrediction'),
                t('dashboard.features.routeMap'),
                t('dashboard.features.satisfaction')
              ]}
              renderItem={(item) => (
                <List.Item>
                  <Space>
                    <RocketOutlined style={{ color: '#1890ff' }} />
                    {item}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;