import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Select,
  DatePicker,
  Button,
  Space,
  Typography,
  Progress,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import {
  DollarOutlined,
  UserOutlined,
  ShoppingCartOutlined,
  CarOutlined,
  RiseOutlined,
  FallOutlined,
  DownloadOutlined,
  PrinterOutlined,
  AreaChartOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
} from '@ant-design/icons';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title as ChartTitle,
  Tooltip as ChartTooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Pie, Doughnut } from 'react-chartjs-2';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import { api } from '../../services/api';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  ChartTitle,
  ChartTooltip,
  Legend,
  Filler
);

interface DashboardMetrics {
  revenue: {
    total: number;
    growth: number;
    byMonth: Array<{ month: string; amount: number }>;
    byProduct: Array<{ product: string; amount: number; percentage: number }>;
  };
  orders: {
    total: number;
    completed: number;
    cancelled: number;
    pending: number;
    avgOrderValue: number;
    byStatus: Array<{ status: string; count: number }>;
    byDay: Array<{ date: string; count: number }>;
  };
  customers: {
    total: number;
    active: number;
    new: number;
    churnRate: number;
    topCustomers: Array<{ id: string; name: string; orders: number; revenue: number }>;
  };
  delivery: {
    totalRoutes: number;
    avgDeliveryTime: number;
    onTimeRate: number;
    efficiency: number;
    byDriver: Array<{ driver: string; deliveries: number; efficiency: number }>;
  };
  predictions: {
    nextMonthRevenue: number;
    expectedOrders: number;
    demandForecast: Array<{ date: string; predicted: number; confidence: number }>;
  };
}

const ReportingDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(30, 'days'),
    dayjs(),
  ]);
  const [viewType, setViewType] = useState<'overview' | 'revenue' | 'operations' | 'customers'>('overview');
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, [dateRange]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await api.get('/analytics/dashboard', {
        params: {
          start_date: dateRange[0].format('YYYY-MM-DD'),
          end_date: dateRange[1].format('YYYY-MM-DD'),
        },
      });
      setMetrics(response.data);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      // Use mock data for demonstration
      setMetrics(generateMockMetrics());
    } finally {
      setLoading(false);
    }
  };

  const generateMockMetrics = (): DashboardMetrics => {
    return {
      revenue: {
        total: 2456780,
        growth: 12.5,
        byMonth: [
          { month: '1月', amount: 380000 },
          { month: '2月', amount: 420000 },
          { month: '3月', amount: 390000 },
          { month: '4月', amount: 450000 },
          { month: '5月', amount: 480000 },
          { month: '6月', amount: 336780 },
        ],
        byProduct: [
          { product: '20kg 瓦斯桶', amount: 1475000, percentage: 60 },
          { product: '16kg 瓦斯桶', amount: 736000, percentage: 30 },
          { product: '50kg 瓦斯桶', amount: 245780, percentage: 10 },
        ],
      },
      orders: {
        total: 3254,
        completed: 3102,
        cancelled: 52,
        pending: 100,
        avgOrderValue: 755,
        byStatus: [
          { status: '已完成', count: 3102 },
          { status: '進行中', count: 100 },
          { status: '已取消', count: 52 },
        ],
        byDay: Array.from({ length: 30 }, (_, i) => ({
          date: dayjs().subtract(29 - i, 'days').format('MM/DD'),
          count: Math.floor(Math.random() * 50) + 80,
        })),
      },
      customers: {
        total: 1523,
        active: 1245,
        new: 78,
        churnRate: 3.2,
        topCustomers: [
          { id: '1', name: '統一企業', orders: 156, revenue: 245000 },
          { id: '2', name: '全家便利商店', orders: 132, revenue: 198000 },
          { id: '3', name: '7-11門市', orders: 128, revenue: 186000 },
          { id: '4', name: '王記餐廳', orders: 98, revenue: 125000 },
          { id: '5', name: '李氏食品', orders: 85, revenue: 95000 },
        ],
      },
      delivery: {
        totalRoutes: 456,
        avgDeliveryTime: 32,
        onTimeRate: 94.5,
        efficiency: 87.3,
        byDriver: [
          { driver: '陳大明', deliveries: 342, efficiency: 92.5 },
          { driver: '李小華', deliveries: 298, efficiency: 89.3 },
          { driver: '王志強', deliveries: 276, efficiency: 87.8 },
          { driver: '張美玲', deliveries: 251, efficiency: 85.2 },
          { driver: '林建宏', deliveries: 234, efficiency: 83.7 },
        ],
      },
      predictions: {
        nextMonthRevenue: 520000,
        expectedOrders: 689,
        demandForecast: Array.from({ length: 7 }, (_, i) => ({
          date: dayjs().add(i + 1, 'days').format('MM/DD'),
          predicted: Math.floor(Math.random() * 20) + 90,
          confidence: Math.random() * 20 + 80,
        })),
      },
    };
  };

  const handleExport = (format: 'pdf' | 'excel') => {
    // TODO: Implement export functionality
    console.log(`Exporting as ${format}`);
  };

  if (!metrics) {
    return null;
  }

  // Chart configurations
  const revenueChartData = {
    labels: metrics.revenue.byMonth.map(m => m.month),
    datasets: [
      {
        label: '月營收',
        data: metrics.revenue.byMonth.map(m => m.amount),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
      },
    ],
  };

  const orderChartData = {
    labels: metrics.orders.byDay.map(d => d.date),
    datasets: [
      {
        label: '每日訂單數',
        data: metrics.orders.byDay.map(d => d.count),
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
      },
    ],
  };

  const productPieData = {
    labels: metrics.revenue.byProduct.map(p => p.product),
    datasets: [
      {
        data: metrics.revenue.byProduct.map(p => p.percentage),
        backgroundColor: [
          'rgba(255, 99, 132, 0.5)',
          'rgba(54, 162, 235, 0.5)',
          'rgba(255, 206, 86, 0.5)',
        ],
        borderWidth: 1,
      },
    ],
  };

  const topCustomersColumns: ColumnsType<any> = [
    { title: '客戶名稱', dataIndex: 'name', key: 'name' },
    { title: '訂單數', dataIndex: 'orders', key: 'orders', align: 'right' },
    {
      title: '營收',
      dataIndex: 'revenue',
      key: 'revenue',
      align: 'right',
      render: (value: number) => `NT$ ${value.toLocaleString()}`,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              營運報表儀表板
            </Title>
          </Col>
          <Col>
            <Space>
              <RangePicker
                value={dateRange}
                onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
              />
              <Select
                value={viewType}
                onChange={setViewType}
                style={{ width: 120 }}
                options={[
                  { label: '總覽', value: 'overview' },
                  { label: '營收', value: 'revenue' },
                  { label: '營運', value: 'operations' },
                  { label: '客戶', value: 'customers' },
                ]}
              />
              <Button icon={<DownloadOutlined />} onClick={() => handleExport('excel')}>
                Excel
              </Button>
              <Button icon={<PrinterOutlined />} onClick={() => handleExport('pdf')}>
                PDF
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Key Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="總營收"
              value={metrics.revenue.total}
              prefix="NT$"
              suffix={
                <span style={{ fontSize: 14, color: metrics.revenue.growth > 0 ? '#3f8600' : '#cf1322' }}>
                  {metrics.revenue.growth > 0 ? <RiseOutlined /> : <FallOutlined />}
                  {Math.abs(metrics.revenue.growth)}%
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="總訂單數"
              value={metrics.orders.total}
              prefix={<ShoppingCartOutlined />}
              suffix={
                <Text type="secondary" style={{ fontSize: 14 }}>
                  均價 NT$ {metrics.orders.avgOrderValue}
                </Text>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活躍客戶"
              value={metrics.customers.active}
              prefix={<UserOutlined />}
              suffix={
                <Text type="secondary" style={{ fontSize: 14 }}>
                  / {metrics.customers.total}
                </Text>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="準時送達率"
              value={metrics.delivery.onTimeRate}
              suffix="%"
              prefix={<CarOutlined />}
              valueStyle={{ color: metrics.delivery.onTimeRate > 90 ? '#3f8600' : '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Section */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="營收趨勢" extra={<LineChartOutlined />}>
            <Line
              data={revenueChartData}
              options={{
                responsive: true,
                plugins: {
                  legend: { display: false },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    ticks: {
                      callback: (value) => `NT$ ${value.toLocaleString()}`,
                    },
                  },
                },
              }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="每日訂單" extra={<BarChartOutlined />}>
            <Bar
              data={orderChartData}
              options={{
                responsive: true,
                plugins: {
                  legend: { display: false },
                },
                scales: {
                  y: { beginAtZero: true },
                },
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Product Mix and Top Customers */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="產品組合" extra={<PieChartOutlined />}>
            <Pie
              data={productPieData}
              options={{
                responsive: true,
                plugins: {
                  legend: { position: 'bottom' },
                },
              }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title="重要客戶" extra={`前 ${metrics.customers.topCustomers.length} 名`}>
            <Table
              columns={topCustomersColumns}
              dataSource={metrics.customers.topCustomers}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* Predictions Section */}
      <Card title="需求預測" extra={<AreaChartOutlined />}>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <Statistic
              title="下月預估營收"
              value={metrics.predictions.nextMonthRevenue}
              prefix="NT$"
              valueStyle={{ color: '#1890ff' }}
            />
            <Statistic
              title="預期訂單數"
              value={metrics.predictions.expectedOrders}
              style={{ marginTop: 16 }}
            />
          </Col>
          <Col xs={24} lg={16}>
            <Line
              data={{
                labels: metrics.predictions.demandForecast.map(d => d.date),
                datasets: [
                  {
                    label: '預測需求',
                    data: metrics.predictions.demandForecast.map(d => d.predicted),
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderDash: [5, 5],
                  },
                ],
              }}
              options={{
                responsive: true,
                plugins: {
                  legend: { display: false },
                },
              }}
            />
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default ReportingDashboard;