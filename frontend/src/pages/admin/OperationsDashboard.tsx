import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  DatePicker,
  Button,
  Space,
  Typography,
  Progress,
  Table,
  Tag,
  Timeline,
  List,
  Badge,
  Alert,
  Tooltip,
  Spin,
  message,
  Avatar,
  Divider,
} from 'antd';
import {
  ShoppingCartOutlined,
  CarOutlined,
  UserOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  DashboardOutlined,
  EnvironmentOutlined,
  FireOutlined,
  WarningOutlined,
  BellOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  ArcElement,
  Title as ChartTitle,
  Tooltip as ChartTooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Radar, Doughnut } from 'react-chartjs-2';
import dayjs from 'dayjs';
import api from '../../services/api';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  ArcElement,
  ChartTitle,
  ChartTooltip,
  Legend,
  Filler
);

interface OperationsMetrics {
  realTimeOrders: {
    statusBreakdown: Record<string, { count: number; amount: number }>;
    recentOrders: Array<{
      id: string;
      orderNumber: string;
      customer: string;
      status: string;
      amount: number;
      createdAt: string;
      items: Array<{ product: string; quantity: number }>;
    }>;
    hourlyTrend: Array<{ hour: number; count: number }>;
    lastUpdated: string;
  };
  driverUtilization: {
    totalDrivers: number;
    activeDrivers: number;
    utilizationRate: number;
    driverPerformance: Array<{
      name: string;
      routes: number;
      deliveries: number;
      completed: number;
      status: string;
    }>;
    summary: {
      idle: number;
      active: number;
      completed: number;
    };
  };
  routeEfficiency: {
    totalRoutes: number;
    totalDeliveries: number;
    completedDeliveries: number;
    overallEfficiency: number;
    onTimeRate: number;
    routes: Array<{
      id: string;
      name: string;
      status: string;
      deliveryCount: number;
      completedCount: number;
      efficiency: number;
      onTime: boolean;
    }>;
    statusBreakdown: {
      planned: number;
      inProgress: number;
      completed: number;
      cancelled: number;
    };
  };
  deliveryMetrics: {
    totalDeliveries: number;
    successfulDeliveries: number;
    successRate: number;
    averageDeliveryTime: number;
    statusBreakdown: Record<string, number>;
    failureReasons: Array<{ reason: string; count: number }>;
  };
  inventory: {
    cylinders: {
      total: number;
      inUse: number;
      empty: number;
      byType: Array<{
        product: string;
        size: string;
        totalCylinders: number;
        inUse: number;
        empty: number;
        utilizationRate: number;
      }>;
    };
    vehicles: {
      total: number;
      active: number;
      maintenance: number;
      available: number;
    };
    alerts: Array<any>;
  };
  alerts: Array<{
    type: 'error' | 'warning' | 'info';
    category: string;
    message: string;
    timestamp: string;
  }>;
}

const OperationsDashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [date, setDate] = useState(dayjs());
  const [metrics, setMetrics] = useState<OperationsMetrics | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const refreshIntervalRef = useRef<NodeJS.Timeout>();
  const { socket, isConnected } = useWebSocketContext();

  useEffect(() => {
    fetchMetrics();
  }, [date]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (autoRefresh) {
      refreshIntervalRef.current = window.setInterval(() => {
        fetchMetrics();
      }, 30 * 1000);
    }

    return () => {
      if (refreshIntervalRef.current) {
        window.clearInterval(refreshIntervalRef.current);
      }
    };
  }, [date, autoRefresh]);

  // WebSocket real-time updates
  useEffect(() => {
    if (!socket || !isConnected) return;

    const handleOrderUpdate = (data: any) => {
      message.info(`新訂單: ${data.orderNumber}`);
      fetchMetrics(); // Refresh data
    };

    const handleRouteUpdate = (data: any) => {
      fetchMetrics(); // Refresh data
    };

    socket.on('order:created', handleOrderUpdate);
    socket.on('order:updated', handleOrderUpdate);
    socket.on('route:updated', handleRouteUpdate);

    return () => {
      socket.off('order:created', handleOrderUpdate);
      socket.off('order:updated', handleOrderUpdate);
      socket.off('route:updated', handleRouteUpdate);
    };
  }, [socket, isConnected]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await api.get('/analytics/operations', {
        params: {
          date: date.format('YYYY-MM-DD'),
        },
      });
      setMetrics(response.data);
    } catch (error) {
      console.error('Failed to fetch operations metrics:', error);
      message.error('無法載入數據，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'orange',
      confirmed: 'blue',
      in_progress: 'processing',
      completed: 'success',
      delivered: 'success',
      cancelled: 'error',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  const getDriverStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CarOutlined style={{ color: '#52c41a' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  if (loading && !metrics) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="載入中..." />
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  // Chart configurations
  const hourlyOrdersData = {
    labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    datasets: [
      {
        label: '訂單數',
        data: Array.from({ length: 24 }, (_, i) => {
          const hourData = metrics.realTimeOrders.hourlyTrend.find(h => h.hour === i);
          return hourData?.count || 0;
        }),
        backgroundColor: 'rgba(24, 144, 255, 0.5)',
        borderColor: '#1890ff',
      },
    ],
  };

  const driverUtilizationData = {
    labels: ['使用中', '閒置', '已完成'],
    datasets: [
      {
        data: [
          metrics.driverUtilization.summary.active,
          metrics.driverUtilization.summary.idle,
          metrics.driverUtilization.summary.completed,
        ],
        backgroundColor: [
          'rgba(82, 196, 26, 0.8)',
          'rgba(140, 140, 140, 0.8)',
          'rgba(24, 144, 255, 0.8)',
        ],
      },
    ],
  };

  const routeEfficiencyData = {
    labels: ['規劃效率', '準時率', '完成率', '司機使用率'],
    datasets: [
      {
        label: '今日表現',
        data: [
          metrics.routeEfficiency.overallEfficiency,
          metrics.routeEfficiency.onTimeRate,
          (metrics.routeEfficiency.completedDeliveries / metrics.routeEfficiency.totalDeliveries) * 100,
          metrics.driverUtilization.utilizationRate,
        ],
        backgroundColor: 'rgba(24, 144, 255, 0.2)',
        borderColor: '#1890ff',
        pointBackgroundColor: '#1890ff',
      },
    ],
  };

  const cylinderInventoryData = {
    labels: metrics.inventory.cylinders.byType.map(t => t.product),
    datasets: [
      {
        label: '使用中',
        data: metrics.inventory.cylinders.byType.map(t => t.inUse),
        backgroundColor: 'rgba(82, 196, 26, 0.8)',
      },
      {
        label: '空瓶',
        data: metrics.inventory.cylinders.byType.map(t => t.empty),
        backgroundColor: 'rgba(250, 140, 22, 0.8)',
      },
    ],
  };

  const recentOrdersColumns: ColumnsType<any> = [
    {
      title: '訂單編號',
      dataIndex: 'orderNumber',
      key: 'orderNumber',
      width: 120,
      render: (text: string) => <a>{text}</a>,
    },
    {
      title: '客戶',
      dataIndex: 'customer',
      key: 'customer',
      ellipsis: true,
    },
    {
      title: '商品',
      dataIndex: 'items',
      key: 'items',
      render: (items: any[]) => (
        <Space size="small">
          {items.map((item, index) => (
            <Tag key={index}>{item.product} x{item.quantity}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '金額',
      dataIndex: 'amount',
      key: 'amount',
      align: 'right',
      width: 100,
      render: (value: number) => `NT$ ${value.toLocaleString()}`,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status.replace('_', ' ').toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '時間',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 100,
      render: (time: string) => dayjs(time).format('HH:mm'),
    },
  ];

  const routePerformanceColumns: ColumnsType<any> = [
    {
      title: '路線',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          planned: { color: 'default', text: '已規劃' },
          in_progress: { color: 'processing', text: '進行中' },
          completed: { color: 'success', text: '已完成' },
          cancelled: { color: 'error', text: '已取消' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '配送進度',
      key: 'progress',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Progress
            percent={record.efficiency}
            size="small"
            strokeColor={record.efficiency >= 90 ? '#52c41a' : record.efficiency >= 70 ? '#1890ff' : '#faad14'}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.completedCount}/{record.deliveryCount} 完成
          </Text>
        </Space>
      ),
    },
    {
      title: '準時',
      dataIndex: 'onTime',
      key: 'onTime',
      width: 60,
      align: 'center',
      render: (onTime: boolean) => (
        onTime ? 
          <CheckCircleOutlined style={{ color: '#52c41a' }} /> : 
          <ClockCircleOutlined style={{ color: '#faad14' }} />
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              <DashboardOutlined /> 營運監控中心
            </Title>
            <Text type="secondary">
              即時掌握營運狀況 · 最後更新: {dayjs(metrics.realTimeOrders.lastUpdated).format('HH:mm:ss')}
            </Text>
          </Col>
          <Col>
            <Space>
              <DatePicker
                value={date}
                onChange={(value) => value && setDate(value)}
                disabledDate={(current) => current && current > dayjs().endOf('day')}
              />
              <Button
                type={autoRefresh ? 'primary' : 'default'}
                icon={<SyncOutlined spin={autoRefresh} />}
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                {autoRefresh ? '自動刷新' : '手動刷新'}
              </Button>
              <Badge dot={isConnected} status={isConnected ? 'success' : 'error'}>
                <Button icon={<BellOutlined />}>
                  即時通知
                </Button>
              </Badge>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Alerts Section */}
      {metrics.alerts.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={24}>
            <Alert
              message="營運警示"
              description={
                <List
                  size="small"
                  dataSource={metrics.alerts}
                  renderItem={(alert) => (
                    <List.Item>
                      <Space>
                        {alert.type === 'error' && <ExclamationCircleOutlined style={{ color: '#f5222d' }} />}
                        {alert.type === 'warning' && <WarningOutlined style={{ color: '#faad14' }} />}
                        {alert.type === 'info' && <BellOutlined style={{ color: '#1890ff' }} />}
                        <Text>{alert.message}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {dayjs(alert.timestamp).format('HH:mm')}
                        </Text>
                      </Space>
                    </List.Item>
                  )}
                />
              }
              type="warning"
              showIcon
              closable
            />
          </Col>
        </Row>
      )}

      {/* Real-time Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日訂單"
              value={Object.values(metrics.realTimeOrders.statusBreakdown).reduce((sum, s) => sum + s.count, 0)}
              prefix={<ShoppingCartOutlined />}
              suffix={
                <Space size="small">
                  <Tag color="orange">{metrics.realTimeOrders.statusBreakdown.pending?.count || 0} 待處理</Tag>
                </Space>
              }
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="司機使用率"
              value={metrics.driverUtilization.utilizationRate}
              prefix={<CarOutlined />}
              suffix="%"
              valueStyle={{ 
                color: metrics.driverUtilization.utilizationRate >= 80 ? '#52c41a' : 
                       metrics.driverUtilization.utilizationRate >= 60 ? '#1890ff' : '#faad14' 
              }}
            />
            <Text type="secondary">
              {metrics.driverUtilization.activeDrivers} / {metrics.driverUtilization.totalDrivers} 位司機
            </Text>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="路線效率"
              value={metrics.routeEfficiency.overallEfficiency}
              prefix={<RocketOutlined />}
              suffix="%"
              valueStyle={{ 
                color: metrics.routeEfficiency.overallEfficiency >= 90 ? '#52c41a' : 
                       metrics.routeEfficiency.overallEfficiency >= 80 ? '#1890ff' : '#faad14' 
              }}
            />
            <Text type="secondary">
              準時率: {metrics.routeEfficiency.onTimeRate}%
            </Text>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="配送成功率"
              value={metrics.deliveryMetrics.successRate}
              prefix={<CheckCircleOutlined />}
              suffix="%"
              valueStyle={{ 
                color: metrics.deliveryMetrics.successRate >= 95 ? '#52c41a' : 
                       metrics.deliveryMetrics.successRate >= 90 ? '#1890ff' : '#f5222d' 
              }}
            />
            <Text type="secondary">
              平均配送時間: {metrics.deliveryMetrics.averageDeliveryTime} 分鐘
            </Text>
          </Card>
        </Col>
      </Row>

      {/* Order and Route Status */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card 
            title="即時訂單狀態" 
            extra={
              <Badge 
                count={metrics.realTimeOrders.statusBreakdown.pending?.count || 0} 
                overflowCount={99}
              >
                <FireOutlined style={{ fontSize: 20 }} />
              </Badge>
            }
          >
            <Table
              columns={recentOrdersColumns}
              dataSource={metrics.realTimeOrders.recentOrders}
              pagination={false}
              size="small"
              scroll={{ y: 300 }}
              rowKey="id"
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="路線執行狀況">
            <Table
              columns={routePerformanceColumns}
              dataSource={metrics.routeEfficiency.routes}
              pagination={false}
              size="small"
              scroll={{ y: 300 }}
              rowKey="id"
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Section */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="訂單時段分布">
            <Bar
              data={hourlyOrdersData}
              options={{
                responsive: true,
                plugins: {
                  legend: { display: false },
                },
                scales: {
                  y: { beginAtZero: true },
                },
              }}
              height={200}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="司機狀態分布">
            <Doughnut
              data={driverUtilizationData}
              options={{
                responsive: true,
                plugins: {
                  legend: { position: 'bottom' },
                },
              }}
              height={200}
            />
            <Divider />
            <List
              size="small"
              dataSource={metrics.driverUtilization.driverPerformance.slice(0, 5)}
              renderItem={(driver) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={getDriverStatusIcon(driver.status)}
                    title={driver.name}
                    description={`${driver.deliveries} 配送 | ${driver.completed} 完成`}
                  />
                  <Tag color={driver.status === 'active' ? 'success' : 'default'}>
                    {driver.routes} 路線
                  </Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="營運效率指標">
            <Radar
              data={routeEfficiencyData}
              options={{
                responsive: true,
                scales: {
                  r: {
                    beginAtZero: true,
                    max: 100,
                  },
                },
              }}
              height={200}
            />
          </Card>
        </Col>
      </Row>

      {/* Inventory and Equipment Status */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="瓦斯桶庫存狀態">
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <Statistic
                  title="總庫存"
                  value={metrics.inventory.cylinders.total}
                  suffix="個"
                />
                <Progress
                  percent={(metrics.inventory.cylinders.inUse / metrics.inventory.cylinders.total) * 100}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
              </Col>
              <Col span={16}>
                <Bar
                  data={cylinderInventoryData}
                  options={{
                    responsive: true,
                    plugins: {
                      legend: { position: 'top' },
                    },
                    scales: {
                      x: { stacked: true },
                      y: { stacked: true },
                    },
                  }}
                  height={100}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="車輛狀態">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="使用中"
                  value={metrics.inventory.vehicles.active}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CarOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="可用"
                  value={metrics.inventory.vehicles.available}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<CarOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="保養中"
                  value={metrics.inventory.vehicles.maintenance}
                  valueStyle={{ color: '#faad14' }}
                  prefix={<CarOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="總車輛"
                  value={metrics.inventory.vehicles.total}
                  prefix={<CarOutlined />}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Delivery Failure Analysis */}
      {metrics.deliveryMetrics.failureReasons.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col span={24}>
            <Card title="配送失敗原因分析">
              <List
                size="small"
                dataSource={metrics.deliveryMetrics.failureReasons}
                renderItem={(item) => (
                  <List.Item>
                    <Text>{item.reason}</Text>
                    <Badge count={item.count} style={{ backgroundColor: '#f5222d' }} />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default OperationsDashboard;