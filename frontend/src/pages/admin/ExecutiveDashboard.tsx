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
  Spin,
  message,
  Divider,
} from 'antd';
import {
  DollarOutlined,
  UserOutlined,
  ShoppingCartOutlined,
  RiseOutlined,
  FallOutlined,
  DownloadOutlined,
  PrinterOutlined,
  ReloadOutlined,
  CalendarOutlined,
  TrophyOutlined,
  TeamOutlined,
  CarOutlined,
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
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import dayjs from 'dayjs';
import api from '../../services/api';
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

interface ExecutiveMetrics {
  revenue: {
    total: number;
    growth: number;
    orderCount: number;
    averageOrderValue: number;
    dailyTrend: Array<{ date: string; amount: number }>;
    byProduct: Array<{ product: string; amount: number; quantity: number }>;
    previousPeriod: number;
  };
  orders: {
    total: number;
    statusBreakdown: Record<string, number>;
    completed: number;
    pending: number;
    cancelled: number;
    hourlyDistribution: Array<{ hour: number; count: number }>;
    orderTypes: Record<string, number>;
    completionRate: number;
  };
  customers: {
    total: number;
    new: number;
    active: number;
    topCustomers: Array<{ id: string; name: string; revenue: number; orderCount: number }>;
    segments: Record<string, number>;
    retentionRate: number;
    churnRate: number;
  };
  cashFlow: {
    totalInflow: number;
    outstandingReceivables: number;
    dailyTrend: Array<{ date: string; inflow: number; cumulative: number }>;
    paymentMethods: Array<{ method: string; amount: number; count: number }>;
    collectionRate: number;
  };
  performance: {
    current: {
      revenue: number;
      orders: number;
      activeCustomers: number;
      averageOrderValue: number;
    };
    monthOverMonth: {
      revenue: number;
      orders: number;
      customers: number;
    };
    yearOverYear: {
      revenue: number;
      orders: number;
      customers: number;
    };
  };
  topMetrics: {
    routes: Array<{ name: string; deliveryCount: number; avgDeliveryTime: number }>;
    drivers: Array<{ name: string; deliveryCount: number; completionRate: number }>;
    products: Array<{ name: string; revenue: number; quantity: number }>;
  };
}

const ExecutiveDashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(30, 'days'),
    dayjs(),
  ]);
  const [metrics, setMetrics] = useState<ExecutiveMetrics | null>(null);
  const [exportLoading, setExportLoading] = useState(false);

  useEffect(() => {
    fetchMetrics();
  }, [dateRange]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = window.setInterval(() => {
      fetchMetrics(true);
    }, 5 * 60 * 1000);

    return () => window.clearInterval(interval);
  }, [dateRange]);

  const fetchMetrics = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const response = await api.get('/analytics/executive', {
        params: {
          start_date: dateRange[0].format('YYYY-MM-DD'),
          end_date: dateRange[1].format('YYYY-MM-DD'),
        },
      });
      setMetrics(response.data);
    } catch (error) {
      console.error('Failed to fetch executive metrics:', error);
      message.error('無法載入數據，請稍後再試');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleExport = async (format: 'pdf' | 'excel') => {
    setExportLoading(true);
    try {
      const response = await api.post('/analytics/export', null, {
        params: {
          report_type: 'executive',
          format: format,
          start_date: dateRange[0].format('YYYY-MM-DD'),
          end_date: dateRange[1].format('YYYY-MM-DD'),
        },
      });

      if (response.data.url) {
        window.open(response.data.url, '_blank');
        message.success('報表已生成');
      } else if (response.data.message) {
        message.info(response.data.message);
      }
    } catch (error) {
      console.error('Export failed:', error);
      message.error('報表生成失敗');
    } finally {
      setExportLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return `NT$ ${value.toLocaleString('zh-TW')}`;
  };

  const formatPercentage = (value: number, showSign = true) => {
    const formatted = `${Math.abs(value).toFixed(1)}%`;
    if (!showSign) return formatted;
    
    if (value > 0) {
      return <span style={{ color: '#52c41a' }}>+{formatted}</span>;
    } else if (value < 0) {
      return <span style={{ color: '#f5222d' }}>-{formatted}</span>;
    }
    return formatted;
  };

  if (loading) {
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
  const revenueChartData = {
    labels: metrics.revenue.dailyTrend.map(d => dayjs(d.date).format('MM/DD')),
    datasets: [
      {
        label: '每日營收',
        data: metrics.revenue.dailyTrend.map(d => d.amount),
        borderColor: '#1890ff',
        backgroundColor: 'rgba(24, 144, 255, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  };

  const revenueChartOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: any) => `營收: ${formatCurrency(context.parsed.y)}`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value: any) => `NT$ ${(value / 1000).toFixed(0)}K`,
        },
      },
    },
  };

  const cashFlowChartData = {
    labels: metrics.cashFlow.dailyTrend.map(d => dayjs(d.date).format('MM/DD')),
    datasets: [
      {
        label: '每日現金流入',
        data: metrics.cashFlow.dailyTrend.map(d => d.inflow),
        type: 'bar' as const,
        backgroundColor: 'rgba(82, 196, 26, 0.8)',
      },
      {
        label: '累計現金',
        data: metrics.cashFlow.dailyTrend.map(d => d.cumulative),
        type: 'line' as const,
        borderColor: '#fa8c16',
        backgroundColor: 'transparent',
        yAxisID: 'y1',
      },
    ],
  };

  const cashFlowChartOptions = {
    responsive: true,
    plugins: {
      legend: { position: 'top' as const },
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        ticks: {
          callback: (value: any) => `${(value / 1000).toFixed(0)}K`,
        },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        grid: { drawOnChartArea: false },
        ticks: {
          callback: (value: any) => `${(value / 1000).toFixed(0)}K`,
        },
      },
    },
  };

  const productMixData = {
    labels: metrics.revenue.byProduct.map(p => p.product),
    datasets: [
      {
        data: metrics.revenue.byProduct.map(p => p.amount),
        backgroundColor: [
          'rgba(24, 144, 255, 0.8)',
          'rgba(82, 196, 26, 0.8)',
          'rgba(250, 140, 22, 0.8)',
          'rgba(245, 34, 45, 0.8)',
          'rgba(114, 46, 209, 0.8)',
        ],
      },
    ],
  };

  const topCustomersColumns: ColumnsType<any> = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_, __, index) => (
        <span style={{ fontWeight: index < 3 ? 'bold' : 'normal' }}>
          {index + 1}
        </span>
      ),
    },
    { 
      title: '客戶名稱', 
      dataIndex: 'name', 
      key: 'name',
      ellipsis: true,
    },
    { 
      title: '訂單數', 
      dataIndex: 'orderCount', 
      key: 'orderCount', 
      align: 'right',
      width: 80,
    },
    {
      title: '營收貢獻',
      dataIndex: 'revenue',
      key: 'revenue',
      align: 'right',
      width: 120,
      render: (value: number) => formatCurrency(value),
    },
  ];

  const topDriversColumns: ColumnsType<any> = [
    {
      title: '司機',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '配送數',
      dataIndex: 'deliveryCount',
      key: 'deliveryCount',
      align: 'right',
    },
    {
      title: '完成率',
      dataIndex: 'completionRate',
      key: 'completionRate',
      align: 'right',
      render: (value: number) => (
        <Progress 
          percent={value} 
          size="small" 
          strokeColor={value >= 95 ? '#52c41a' : value >= 90 ? '#1890ff' : '#faad14'}
        />
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
              <DollarOutlined /> 經營管理儀表板
            </Title>
            <Text type="secondary">即時掌握企業營運狀況</Text>
          </Col>
          <Col>
            <Space>
              <RangePicker
                value={dateRange}
                onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
                presets={[
                  { label: '過去 7 天', value: [dayjs().subtract(7, 'days'), dayjs()] },
                  { label: '過去 30 天', value: [dayjs().subtract(30, 'days'), dayjs()] },
                  { label: '本月', value: [dayjs().startOf('month'), dayjs()] },
                  { label: '上月', value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
                ]}
              />
              <Button 
                icon={<ReloadOutlined spin={refreshing} />} 
                onClick={() => fetchMetrics(true)}
                loading={refreshing}
              >
                刷新
              </Button>
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => handleExport('excel')}
                loading={exportLoading}
              >
                Excel
              </Button>
              <Button 
                icon={<PrinterOutlined />} 
                onClick={() => handleExport('pdf')}
                loading={exportLoading}
              >
                PDF
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Key Performance Indicators */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title={
                <Space>
                  <DollarOutlined />
                  <span>總營收</span>
                </Space>
              }
              value={metrics.revenue.total}
              formatter={(value) => formatCurrency(Number(value))}
              suffix={
                <Tooltip title={`較上期 ${formatCurrency(metrics.revenue.previousPeriod)}`}>
                  <span style={{ fontSize: 14, marginLeft: 8 }}>
                    {metrics.revenue.growth > 0 ? <RiseOutlined /> : <FallOutlined />}
                    {formatPercentage(metrics.revenue.growth)}
                  </span>
                </Tooltip>
              }
            />
            <Progress 
              percent={Math.min(100, (metrics.revenue.total / (metrics.revenue.previousPeriod * 1.2)) * 100)} 
              showInfo={false}
              strokeColor={metrics.revenue.growth > 0 ? '#52c41a' : '#f5222d'}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title={
                <Space>
                  <ShoppingCartOutlined />
                  <span>訂單總數</span>
                </Space>
              }
              value={metrics.orders.total}
              suffix={
                <span style={{ fontSize: 14 }}>
                  筆
                </span>
              }
            />
            <Row gutter={8} style={{ marginTop: 16 }}>
              <Col span={8}>
                <Statistic 
                  value={metrics.orders.completionRate} 
                  suffix="%" 
                  valueStyle={{ fontSize: 14 }}
                  title={<Text type="secondary" style={{ fontSize: 12 }}>完成率</Text>}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  value={metrics.revenue.averageOrderValue} 
                  valueStyle={{ fontSize: 14 }}
                  formatter={(value) => `NT$ ${Number(value).toFixed(0)}`}
                  title={<Text type="secondary" style={{ fontSize: 12 }}>平均單價</Text>}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  value={metrics.orders.pending} 
                  valueStyle={{ fontSize: 14, color: '#faad14' }}
                  title={<Text type="secondary" style={{ fontSize: 12 }}>待處理</Text>}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title={
                <Space>
                  <UserOutlined />
                  <span>活躍客戶</span>
                </Space>
              }
              value={metrics.customers.active}
              suffix={
                <span style={{ fontSize: 14 }}>
                  / {metrics.customers.total}
                </span>
              }
            />
            <Row gutter={8} style={{ marginTop: 16 }}>
              <Col span={8}>
                <Statistic 
                  value={metrics.customers.new} 
                  valueStyle={{ fontSize: 14, color: '#52c41a' }}
                  title={<Text type="secondary" style={{ fontSize: 12 }}>新客戶</Text>}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  value={metrics.customers.retentionRate} 
                  suffix="%" 
                  valueStyle={{ fontSize: 14 }}
                  title={<Text type="secondary" style={{ fontSize: 12 }}>留存率</Text>}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  value={metrics.customers.churnRate} 
                  suffix="%" 
                  valueStyle={{ fontSize: 14, color: '#f5222d' }}
                  title={<Text type="secondary" style={{ fontSize: 12 }}>流失率</Text>}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title={
                <Space>
                  <CalendarOutlined />
                  <span>現金流入</span>
                </Space>
              }
              value={metrics.cashFlow.totalInflow}
              formatter={(value) => formatCurrency(Number(value))}
            />
            <Row gutter={8} style={{ marginTop: 16 }}>
              <Col span={12}>
                <Statistic 
                  value={metrics.cashFlow.collectionRate} 
                  suffix="%" 
                  valueStyle={{ fontSize: 14 }}
                  title={<Text type="secondary" style={{ fontSize: 12 }}>收款率</Text>}
                />
              </Col>
              <Col span={12}>
                <Statistic 
                  value={metrics.cashFlow.outstandingReceivables} 
                  valueStyle={{ fontSize: 14, color: '#faad14' }}
                  formatter={(value) => `${(Number(value) / 1000).toFixed(0)}K`}
                  title={<Text type="secondary" style={{ fontSize: 12 }}>應收帳款</Text>}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Performance Comparison */}
      <Card 
        title="績效比較" 
        style={{ marginBottom: 24 }}
        extra={
          <Space>
            <Tag color="blue">當期</Tag>
            <Tag>月增率</Tag>
            <Tag>年增率</Tag>
          </Space>
        }
      >
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={8}>
            <Card size="small" bordered={false}>
              <Statistic
                title="營收表現"
                value={metrics.performance.current.revenue}
                formatter={(value) => formatCurrency(Number(value))}
              />
              <Row style={{ marginTop: 16 }}>
                <Col span={12}>
                  <Text type="secondary">月增率</Text>
                  <div>{formatPercentage(metrics.performance.monthOverMonth.revenue)}</div>
                </Col>
                <Col span={12}>
                  <Text type="secondary">年增率</Text>
                  <div>{formatPercentage(metrics.performance.yearOverYear.revenue)}</div>
                </Col>
              </Row>
            </Card>
          </Col>

          <Col xs={24} lg={8}>
            <Card size="small" bordered={false}>
              <Statistic
                title="訂單成長"
                value={metrics.performance.current.orders}
                suffix="筆"
              />
              <Row style={{ marginTop: 16 }}>
                <Col span={12}>
                  <Text type="secondary">月增率</Text>
                  <div>{formatPercentage(metrics.performance.monthOverMonth.orders)}</div>
                </Col>
                <Col span={12}>
                  <Text type="secondary">年增率</Text>
                  <div>{formatPercentage(metrics.performance.yearOverYear.orders)}</div>
                </Col>
              </Row>
            </Card>
          </Col>

          <Col xs={24} lg={8}>
            <Card size="small" bordered={false}>
              <Statistic
                title="客戶成長"
                value={metrics.performance.current.activeCustomers}
                suffix="位"
              />
              <Row style={{ marginTop: 16 }}>
                <Col span={12}>
                  <Text type="secondary">月增率</Text>
                  <div>{formatPercentage(metrics.performance.monthOverMonth.customers)}</div>
                </Col>
                <Col span={12}>
                  <Text type="secondary">年增率</Text>
                  <div>{formatPercentage(metrics.performance.yearOverYear.customers)}</div>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* Charts Section */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card 
            title="營收趨勢" 
            extra={<Text type="secondary">過去 {dateRange[1].diff(dateRange[0], 'day')} 天</Text>}
          >
            <Line data={revenueChartData} options={revenueChartOptions} />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card 
            title="現金流分析" 
            extra={<Text type="secondary">每日現金流入與累計</Text>}
          >
            <Bar data={cashFlowChartData} options={cashFlowChartOptions} />
          </Card>
        </Col>
      </Row>

      {/* Product Mix and Top Performers */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="產品營收組合">
            <Doughnut 
              data={productMixData} 
              options={{
                responsive: true,
                plugins: {
                  legend: { position: 'bottom' },
                  tooltip: {
                    callbacks: {
                      label: (context: any) => {
                        const label = context.label || '';
                        const value = formatCurrency(context.parsed);
                        const percentage = ((context.parsed / metrics.revenue.total) * 100).toFixed(1);
                        return `${label}: ${value} (${percentage}%)`;
                      },
                    },
                  },
                },
              }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card 
            title={
              <Space>
                <TrophyOutlined style={{ color: '#faad14' }} />
                <span>重要客戶</span>
              </Space>
            }
            extra={<Text type="secondary">前 5 名</Text>}
          >
            <Table
              columns={topCustomersColumns}
              dataSource={metrics.customers.topCustomers.slice(0, 5)}
              pagination={false}
              size="small"
              rowKey="id"
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card 
            title={
              <Space>
                <TeamOutlined style={{ color: '#52c41a' }} />
                <span>優秀司機</span>
              </Space>
            }
            extra={<Text type="secondary">完成率排行</Text>}
          >
            <Table
              columns={topDriversColumns}
              dataSource={metrics.topMetrics.drivers.slice(0, 5)}
              pagination={false}
              size="small"
              rowKey="name"
            />
          </Card>
        </Col>
      </Row>

      {/* Bottom Stats */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={6}>
          <Card>
            <Statistic
              title="最熱銷產品"
              value={metrics.topMetrics.products[0]?.name || '-'}
              valueStyle={{ fontSize: 16 }}
            />
            <Text type="secondary">
              銷量: {metrics.topMetrics.products[0]?.quantity || 0} 個
            </Text>
          </Card>
        </Col>

        <Col xs={24} lg={6}>
          <Card>
            <Statistic
              title="最佳路線"
              value={metrics.topMetrics.routes[0]?.name || '-'}
              valueStyle={{ fontSize: 16 }}
            />
            <Text type="secondary">
              配送: {metrics.topMetrics.routes[0]?.deliveryCount || 0} 次
            </Text>
          </Card>
        </Col>

        <Col xs={24} lg={6}>
          <Card>
            <Statistic
              title="付款方式"
              value={metrics.cashFlow.paymentMethods[0]?.method || '-'}
              valueStyle={{ fontSize: 16 }}
            />
            <Text type="secondary">
              佔比: {((metrics.cashFlow.paymentMethods[0]?.amount || 0) / metrics.cashFlow.totalInflow * 100).toFixed(1)}%
            </Text>
          </Card>
        </Col>

        <Col xs={24} lg={6}>
          <Card>
            <Statistic
              title="客戶分布"
              value={Object.keys(metrics.customers.segments)[0] || '-'}
              valueStyle={{ fontSize: 16 }}
            />
            <Text type="secondary">
              數量: {Object.values(metrics.customers.segments)[0] || 0} 位
            </Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ExecutiveDashboard;