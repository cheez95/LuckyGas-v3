import React, { useState, useEffect } from 'react';
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
  List,
  Badge,
  Alert,
  Tooltip,
  Spin,
  message,
  Divider,
  Tabs,
  Select,
} from 'antd';
import {
  DollarOutlined,
  BankOutlined,
  FileTextOutlined,
  RiseOutlined,
  FallOutlined,
  DownloadOutlined,
  PrinterOutlined,
  CalendarOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  PieChartOutlined,
  LineChartOutlined,
  BarChartOutlined,
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
import dayjs from 'dayjs';
import api from '../../services/api';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

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

interface FinancialMetrics {
  receivables: {
    totalReceivables: number;
    totalCount: number;
    agingBreakdown: {
      current: { count: number; amount: number };
      '1-30': { count: number; amount: number };
      '31-60': { count: number; amount: number };
      '61-90': { count: number; amount: number };
      over90: { count: number; amount: number };
    };
    topDebtors: Array<{
      id: string;
      name: string;
      amount: number;
      invoiceCount: number;
    }>;
    averageDaysOutstanding: number;
  };
  collections: {
    totalInvoiced: number;
    totalCollected: number;
    collectionRate: number;
    dailyTrend: Array<{
      date: string;
      amount: number;
      count: number;
    }>;
    paymentMethods: Array<{
      method: string;
      amount: number;
      count: number;
      percentage: number;
    }>;
    outstanding: number;
  };
  outstandingInvoices: {
    totalOutstanding: number;
    overdueCount: number;
    overdueAmount: number;
    invoices: Array<{
      id: string;
      invoiceNumber: string;
      customer: string;
      amount: number;
      paid: number;
      outstanding: number;
      dueDate: string;
      invoiceDate: string;
      isOverdue: boolean;
      daysOverdue: number;
    }>;
    summary: {
      total: number;
      current: number;
      overdue: number;
    };
  };
  revenueBySegment: {
    segments: Array<{
      segment: string;
      customerCount: number;
      revenue: number;
      orderCount: number;
      averageOrderValue: number;
      percentage: number;
    }>;
    topAreas: Array<{
      area: string;
      revenue: number;
      customerCount: number;
    }>;
    totalRevenue: number;
  };
  profitMargins: {
    overallMargin: number;
    totalRevenue: number;
    totalCost: number;
    totalProfit: number;
    productMargins: Array<{
      product: string;
      quantitySold: number;
      revenue: number;
      cost: number;
      profit: number;
      margin: number;
      avgPrice: number;
    }>;
    monthlyTrend: Array<{
      month: string;
      revenue: number;
      profit: number;
      margin: number;
    }>;
  };
  cashPosition: {
    cashMovements: Array<{
      date: string;
      inflow: number;
      outflow: number;
      netMovement: number;
      balance: number;
    }>;
    currentBalance: number;
    averageDailyInflow: number;
    averageDailyOutflow: number;
    cashConversionCycle: {
      daysSalesOutstanding: number;
      daysInventoryOutstanding: number;
      daysPayableOutstanding: number;
    };
  };
}

const FinancialDashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().startOf('month'),
    dayjs(),
  ]);
  const [metrics, setMetrics] = useState<FinancialMetrics | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchMetrics();
  }, [dateRange]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await api.get('/analytics/financial', {
        params: {
          start_date: dateRange[0].format('YYYY-MM-DD'),
          end_date: dateRange[1].format('YYYY-MM-DD'),
        },
      });
      setMetrics(response.data);
    } catch (error) {
      console.error('Failed to fetch financial metrics:', error);
      message.error('無法載入財務數據，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'pdf' | 'excel') => {
    setExportLoading(true);
    try {
      const response = await api.post('/analytics/export', null, {
        params: {
          report_type: 'financial',
          format: format,
          start_date: dateRange[0].format('YYYY-MM-DD'),
          end_date: dateRange[1].format('YYYY-MM-DD'),
        },
      });

      if (response.data.url) {
        window.open(response.data.url, '_blank');
        message.success('財務報表已生成');
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

  const getAgingColor = (bucket: string) => {
    const colors: Record<string, string> = {
      current: '#52c41a',
      '1-30': '#1890ff',
      '31-60': '#faad14',
      '61-90': '#fa8c16',
      over90: '#f5222d',
    };
    return colors[bucket] || '#8c8c8c';
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="載入財務數據中..." />
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  // Chart configurations
  const agingChartData = {
    labels: ['當期', '1-30天', '31-60天', '61-90天', '90天以上'],
    datasets: [
      {
        data: [
          metrics.receivables.agingBreakdown.current.amount,
          metrics.receivables.agingBreakdown['1-30'].amount,
          metrics.receivables.agingBreakdown['31-60'].amount,
          metrics.receivables.agingBreakdown['61-90'].amount,
          metrics.receivables.agingBreakdown.over90.amount,
        ],
        backgroundColor: [
          'rgba(82, 196, 26, 0.8)',
          'rgba(24, 144, 255, 0.8)',
          'rgba(250, 173, 20, 0.8)',
          'rgba(250, 140, 22, 0.8)',
          'rgba(245, 34, 45, 0.8)',
        ],
      },
    ],
  };

  const collectionTrendData = {
    labels: metrics.collections.dailyTrend.map(d => dayjs(d.date).format('MM/DD')),
    datasets: [
      {
        label: '每日收款',
        data: metrics.collections.dailyTrend.map(d => d.amount),
        backgroundColor: 'rgba(82, 196, 26, 0.5)',
        borderColor: '#52c41a',
      },
    ],
  };

  const revenueBySegmentData = {
    labels: metrics.revenueBySegment.segments.map(s => s.segment),
    datasets: [
      {
        data: metrics.revenueBySegment.segments.map(s => s.revenue),
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

  const profitMarginTrendData = {
    labels: metrics.profitMargins.monthlyTrend.map(m => m.month),
    datasets: [
      {
        label: '營收',
        data: metrics.profitMargins.monthlyTrend.map(m => m.revenue),
        borderColor: '#1890ff',
        backgroundColor: 'transparent',
        yAxisID: 'y',
      },
      {
        label: '利潤',
        data: metrics.profitMargins.monthlyTrend.map(m => m.profit),
        borderColor: '#52c41a',
        backgroundColor: 'transparent',
        yAxisID: 'y',
      },
      {
        label: '利潤率 (%)',
        data: metrics.profitMargins.monthlyTrend.map(m => m.margin),
        borderColor: '#fa8c16',
        backgroundColor: 'transparent',
        yAxisID: 'y1',
        borderDash: [5, 5],
      },
    ],
  };

  const cashFlowData = {
    labels: metrics.cashPosition.cashMovements.map(m => dayjs(m.date).format('MM/DD')),
    datasets: [
      {
        label: '現金流入',
        data: metrics.cashPosition.cashMovements.map(m => m.inflow),
        backgroundColor: 'rgba(82, 196, 26, 0.8)',
      },
      {
        label: '現金流出',
        data: metrics.cashPosition.cashMovements.map(m => -m.outflow),
        backgroundColor: 'rgba(245, 34, 45, 0.8)',
      },
    ],
  };

  const outstandingInvoicesColumns: ColumnsType<any> = [
    {
      title: '發票編號',
      dataIndex: 'invoiceNumber',
      key: 'invoiceNumber',
      width: 120,
      fixed: 'left',
    },
    {
      title: '客戶',
      dataIndex: 'customer',
      key: 'customer',
      ellipsis: true,
    },
    {
      title: '發票金額',
      dataIndex: 'amount',
      key: 'amount',
      align: 'right',
      width: 120,
      render: (value: number) => formatCurrency(value),
    },
    {
      title: '已付金額',
      dataIndex: 'paid',
      key: 'paid',
      align: 'right',
      width: 120,
      render: (value: number) => formatCurrency(value),
    },
    {
      title: '未付餘額',
      dataIndex: 'outstanding',
      key: 'outstanding',
      align: 'right',
      width: 120,
      render: (value: number) => (
        <Text strong style={{ color: '#f5222d' }}>
          {formatCurrency(value)}
        </Text>
      ),
    },
    {
      title: '到期日',
      dataIndex: 'dueDate',
      key: 'dueDate',
      width: 100,
      render: (date: string, record) => (
        <Space direction="vertical" size="small">
          <Text>{dayjs(date).format('YYYY-MM-DD')}</Text>
          {record.isOverdue && (
            <Tag color="error">逾期 {record.daysOverdue} 天</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '狀態',
      key: 'status',
      width: 100,
      render: (_, record) => (
        record.isOverdue ? 
          <Badge status="error" text="逾期" /> : 
          <Badge status="processing" text="未到期" />
      ),
    },
  ];

  const topDebtorsColumns: ColumnsType<any> = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_, __, index) => index + 1,
    },
    {
      title: '客戶名稱',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '欠款金額',
      dataIndex: 'amount',
      key: 'amount',
      align: 'right',
      width: 120,
      render: (value: number) => (
        <Text strong style={{ color: '#f5222d' }}>
          {formatCurrency(value)}
        </Text>
      ),
    },
    {
      title: '發票數',
      dataIndex: 'invoiceCount',
      key: 'invoiceCount',
      align: 'center',
      width: 80,
    },
  ];

  const productMarginsColumns: ColumnsType<any> = [
    {
      title: '產品',
      dataIndex: 'product',
      key: 'product',
    },
    {
      title: '銷售量',
      dataIndex: 'quantitySold',
      key: 'quantitySold',
      align: 'right',
    },
    {
      title: '營收',
      dataIndex: 'revenue',
      key: 'revenue',
      align: 'right',
      render: (value: number) => formatCurrency(value),
    },
    {
      title: '成本',
      dataIndex: 'cost',
      key: 'cost',
      align: 'right',
      render: (value: number) => formatCurrency(value),
    },
    {
      title: '利潤',
      dataIndex: 'profit',
      key: 'profit',
      align: 'right',
      render: (value: number) => formatCurrency(value),
    },
    {
      title: '利潤率',
      dataIndex: 'margin',
      key: 'margin',
      align: 'right',
      width: 100,
      render: (value: number) => (
        <Progress
          percent={value}
          size="small"
          strokeColor={value >= 30 ? '#52c41a' : value >= 20 ? '#1890ff' : '#faad14'}
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
              <BankOutlined /> 財務管理儀表板
            </Title>
            <Text type="secondary">全面掌握財務狀況與現金流</Text>
          </Col>
          <Col>
            <Space>
              <RangePicker
                value={dateRange}
                onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
                presets={[
                  { label: '本月', value: [dayjs().startOf('month'), dayjs()] },
                  { label: '上月', value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
                  { label: '本季', value: [dayjs().startOf('quarter'), dayjs()] },
                  { label: '本年', value: [dayjs().startOf('year'), dayjs()] },
                ]}
              />
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

      {/* Key Financial Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="應收帳款總額"
              value={metrics.receivables.totalReceivables}
              prefix={<FileTextOutlined />}
              formatter={(value) => formatCurrency(Number(value))}
              valueStyle={{ color: '#faad14' }}
            />
            <Divider style={{ margin: '12px 0' }} />
            <Row>
              <Col span={12}>
                <Statistic
                  value={metrics.receivables.totalCount}
                  valueStyle={{ fontSize: 14 }}
                  suffix="筆"
                  title={<Text type="secondary" style={{ fontSize: 12 }}>未收發票</Text>}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  value={metrics.outstandingInvoices.overdueCount}
                  valueStyle={{ fontSize: 14, color: '#f5222d' }}
                  suffix="筆"
                  title={<Text type="secondary" style={{ fontSize: 12 }}>逾期發票</Text>}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="收款率"
              value={metrics.collections.collectionRate}
              prefix={<CheckCircleOutlined />}
              suffix="%"
              valueStyle={{ 
                color: metrics.collections.collectionRate >= 90 ? '#52c41a' : 
                       metrics.collections.collectionRate >= 80 ? '#1890ff' : '#f5222d' 
              }}
            />
            <Progress
              percent={metrics.collections.collectionRate}
              showInfo={false}
              strokeColor={{
                '0%': '#f5222d',
                '80%': '#faad14',
                '90%': '#52c41a',
              }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              已收: {formatCurrency(metrics.collections.totalCollected)}
            </Text>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="利潤率"
              value={metrics.profitMargins.overallMargin}
              prefix={<PieChartOutlined />}
              suffix="%"
              valueStyle={{ 
                color: metrics.profitMargins.overallMargin >= 30 ? '#52c41a' : 
                       metrics.profitMargins.overallMargin >= 20 ? '#1890ff' : '#faad14' 
              }}
            />
            <Divider style={{ margin: '12px 0' }} />
            <Row>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>總利潤</Text>
                <div style={{ fontSize: 14, fontWeight: 'bold' }}>
                  {formatCurrency(metrics.profitMargins.totalProfit)}
                </div>
              </Col>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>總成本</Text>
                <div style={{ fontSize: 14 }}>
                  {formatCurrency(metrics.profitMargins.totalCost)}
                </div>
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="現金餘額"
              value={metrics.cashPosition.currentBalance}
              prefix={<BankOutlined />}
              formatter={(value) => formatCurrency(Number(value))}
              valueStyle={{ color: '#1890ff' }}
            />
            <Divider style={{ margin: '12px 0' }} />
            <Row>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>日均流入</Text>
                <div style={{ fontSize: 14, color: '#52c41a' }}>
                  +{formatCurrency(metrics.cashPosition.averageDailyInflow)}
                </div>
              </Col>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>日均流出</Text>
                <div style={{ fontSize: 14, color: '#f5222d' }}>
                  -{formatCurrency(metrics.cashPosition.averageDailyOutflow)}
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Tabs for different sections */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="應收帳款" key="receivables">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Card title="帳齡分析" size="small">
                  <Doughnut
                    data={agingChartData}
                    options={{
                      responsive: true,
                      plugins: {
                        legend: { position: 'right' },
                        tooltip: {
                          callbacks: {
                            label: (context: any) => {
                              const label = context.label || '';
                              const value = formatCurrency(context.parsed);
                              return `${label}: ${value}`;
                            },
                          },
                        },
                      },
                    }}
                  />
                  <Divider />
                  <List
                    size="small"
                    dataSource={Object.entries(metrics.receivables.agingBreakdown)}
                    renderItem={([bucket, data]) => (
                      <List.Item>
                        <Badge color={getAgingColor(bucket)} text={bucket === 'current' ? '當期' : `${bucket} 天`} />
                        <Space>
                          <Text>{data.count} 筆</Text>
                          <Text strong>{formatCurrency(data.amount)}</Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                <Card title="前十大欠款客戶" size="small">
                  <Table
                    columns={topDebtorsColumns}
                    dataSource={metrics.receivables.topDebtors}
                    pagination={false}
                    size="small"
                    rowKey="id"
                  />
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="現金流" key="cashflow">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={16}>
                <Card title="現金流動分析" size="small">
                  <Bar
                    data={cashFlowData}
                    options={{
                      responsive: true,
                      plugins: {
                        legend: { position: 'top' },
                      },
                      scales: {
                        x: { stacked: true },
                        y: { 
                          stacked: true,
                          ticks: {
                            callback: (value: any) => formatCurrency(value),
                          },
                        },
                      },
                    }}
                  />
                </Card>
              </Col>

              <Col xs={24} lg={8}>
                <Card title="現金轉換週期" size="small">
                  <List>
                    <List.Item>
                      <List.Item.Meta
                        title="應收帳款週轉天數"
                        description={`${metrics.cashPosition.cashConversionCycle.daysSalesOutstanding.toFixed(1)} 天`}
                      />
                    </List.Item>
                    <List.Item>
                      <List.Item.Meta
                        title="存貨週轉天數"
                        description={`${metrics.cashPosition.cashConversionCycle.daysInventoryOutstanding} 天`}
                      />
                    </List.Item>
                    <List.Item>
                      <List.Item.Meta
                        title="應付帳款週轉天數"
                        description={`${metrics.cashPosition.cashConversionCycle.daysPayableOutstanding} 天`}
                      />
                    </List.Item>
                  </List>
                  <Divider />
                  <Alert
                    message="現金轉換週期"
                    description={`${(
                      metrics.cashPosition.cashConversionCycle.daysSalesOutstanding +
                      metrics.cashPosition.cashConversionCycle.daysInventoryOutstanding -
                      metrics.cashPosition.cashConversionCycle.daysPayableOutstanding
                    ).toFixed(1)} 天`}
                    type="info"
                    showIcon
                  />
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="收款管理" key="collections">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={16}>
                <Card title="每日收款趨勢" size="small">
                  <Bar
                    data={collectionTrendData}
                    options={{
                      responsive: true,
                      plugins: {
                        legend: { display: false },
                      },
                      scales: {
                        y: {
                          beginAtZero: true,
                          ticks: {
                            callback: (value: any) => formatCurrency(value),
                          },
                        },
                      },
                    }}
                  />
                </Card>
              </Col>

              <Col xs={24} lg={8}>
                <Card title="付款方式分析" size="small">
                  <List
                    dataSource={metrics.collections.paymentMethods}
                    renderItem={(method) => (
                      <List.Item>
                        <List.Item.Meta
                          title={method.method}
                          description={`${method.count} 筆 (${method.percentage}%)`}
                        />
                        <Text strong>{formatCurrency(method.amount)}</Text>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="利潤分析" key="profit">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Card title="利潤趨勢" size="small">
                  <Line
                    data={profitMarginTrendData}
                    options={{
                      responsive: true,
                      interaction: {
                        mode: 'index',
                        intersect: false,
                      },
                      scales: {
                        y: {
                          type: 'linear',
                          display: true,
                          position: 'left',
                          ticks: {
                            callback: (value: any) => formatCurrency(value),
                          },
                        },
                        y1: {
                          type: 'linear',
                          display: true,
                          position: 'right',
                          grid: {
                            drawOnChartArea: false,
                          },
                          ticks: {
                            callback: (value: any) => `${value}%`,
                          },
                        },
                      },
                    }}
                  />
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                <Card title="產品利潤分析" size="small">
                  <Table
                    columns={productMarginsColumns}
                    dataSource={metrics.profitMargins.productMargins}
                    pagination={false}
                    size="small"
                    scroll={{ y: 300 }}
                  />
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="營收分析" key="revenue">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Card title="客戶類型營收分布" size="small">
                  <Pie
                    data={revenueBySegmentData}
                    options={{
                      responsive: true,
                      plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                          callbacks: {
                            label: (context: any) => {
                              const segment = metrics.revenueBySegment.segments[context.dataIndex];
                              return [
                                `${segment.segment}: ${formatCurrency(segment.revenue)}`,
                                `客戶數: ${segment.customerCount}`,
                                `平均單價: ${formatCurrency(segment.averageOrderValue)}`,
                              ];
                            },
                          },
                        },
                      },
                    }}
                  />
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                <Card title="地區營收排行" size="small">
                  <List
                    dataSource={metrics.revenueBySegment.topAreas}
                    renderItem={(area, index) => (
                      <List.Item>
                        <Badge
                          count={index + 1}
                          style={{ backgroundColor: index < 3 ? '#52c41a' : '#8c8c8c' }}
                        />
                        <List.Item.Meta
                          title={area.area}
                          description={`${area.customerCount} 位客戶`}
                          style={{ marginLeft: 12 }}
                        />
                        <Text strong>{formatCurrency(area.revenue)}</Text>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="未收發票" key="invoices">
            <Card title="未收發票明細" size="small">
              <Alert
                message={`共 ${metrics.outstandingInvoices.summary.total} 筆未收發票，其中 ${metrics.outstandingInvoices.overdueCount} 筆已逾期`}
                description={`逾期金額: ${formatCurrency(metrics.outstandingInvoices.overdueAmount)}`}
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Table
                columns={outstandingInvoicesColumns}
                dataSource={metrics.outstandingInvoices.invoices}
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 筆`,
                }}
                size="small"
                scroll={{ x: 800 }}
                rowKey="id"
                rowClassName={(record) => record.isOverdue ? 'ant-table-row-error' : ''}
              />
            </Card>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default FinancialDashboard;