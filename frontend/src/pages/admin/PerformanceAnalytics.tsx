import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Select,
  Button,
  Space,
  Typography,
  Progress,
  Table,
  Tag,
  List,
  Alert,
  Tooltip,
  Spin,
  message,
  Timeline,
  Badge,
  Divider,
} from 'antd';
import {
  DashboardOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  UserOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LineChartOutlined,
  BarChartOutlined,
  HeatMapOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title as ChartTitle,
  Tooltip as ChartTooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import dayjs from 'dayjs';
import api from '../../services/api';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { Option } = Select;

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ChartTitle,
  ChartTooltip,
  Legend,
  Filler
);

interface PerformanceMetrics {
  systemMetrics: {
    timeSeries: Array<{
      timestamp: string;
      responseTime: number;
      errorRate: number;
      throughput: number;
      cpuUsage: number;
      memoryUsage: number;
    }>;
    averages: {
      responseTime: number;
      errorRate: number;
      throughput: number;
      cpuUsage: number;
      memoryUsage: number;
    };
    alerts: Array<any>;
  };
  apiUsage: {
    totalCalls: number;
    totalErrors: number;
    errorRate: number;
    endpoints: Array<{
      endpoint: string;
      calls: number;
      avgTime: number;
      errors: number;
    }>;
    peakHours: Array<{
      hour: number;
      calls: number;
    }>;
  };
  errorAnalysis: {
    errorTypes: Array<{
      type: string;
      count: number;
      percentage: number;
    }>;
    errorTrends: Array<{
      timestamp: string;
      errorCount: number;
    }>;
    totalErrors: number;
    criticalErrors: number;
    resolvedErrors: number;
  };
  userActivity: {
    activeUsersByRole: Record<string, number>;
    totalActiveUsers: number;
    sessionData: {
      totalSessions: number;
      averageSessionDuration: number;
      pageViews: number;
      bounceRate: number;
    };
    featureUsage: Array<{
      feature: string;
      usage: number;
      users: number;
    }>;
    userGrowth: {
      newUsers: number;
      returningUsers: number;
      churnedUsers: number;
    };
  };
  resourceUtilization: {
    database: {
      connections: number;
      maxConnections: number;
      queryTime: number;
      slowQueries: number;
      diskUsage: number;
    };
    redis: {
      memoryUsage: number;
      hitRate: number;
      evictions: number;
      connectedClients: number;
    };
    storage: {
      used: number;
      total: number;
      percentage: number;
      largestTables: Array<{
        table: string;
        size: number;
      }>;
    };
    api: {
      requestsPerMinute: number;
      averageLatency: number;
      errorRate: number;
      saturation: number;
    };
  };
}

const PerformanceAnalytics: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState('24h');
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, [timeRange]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchMetrics();
      }, 60 * 1000); // Refresh every minute
      setRefreshInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }

    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  }, [autoRefresh, timeRange]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await api.get('/analytics/performance', {
        params: { time_range: timeRange },
      });
      setMetrics(response.data);
    } catch (error) {
      console.error('Failed to fetch performance metrics:', error);
      message.error('無法載入效能數據，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  const getHealthColor = (value: number, metric: string) => {
    switch (metric) {
      case 'responseTime':
        return value < 200 ? '#52c41a' : value < 500 ? '#faad14' : '#f5222d';
      case 'errorRate':
        return value < 1 ? '#52c41a' : value < 5 ? '#faad14' : '#f5222d';
      case 'cpu':
      case 'memory':
        return value < 60 ? '#52c41a' : value < 80 ? '#faad14' : '#f5222d';
      default:
        return '#1890ff';
    }
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
  };

  if (loading && !metrics) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="載入效能數據中..." />
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  // Chart configurations
  const systemPerformanceData = {
    labels: metrics.systemMetrics.timeSeries.map(t => 
      dayjs(t.timestamp).format('HH:mm')
    ),
    datasets: [
      {
        label: '回應時間 (ms)',
        data: metrics.systemMetrics.timeSeries.map(t => t.responseTime),
        borderColor: '#1890ff',
        backgroundColor: 'transparent',
        yAxisID: 'y',
      },
      {
        label: '錯誤率 (%)',
        data: metrics.systemMetrics.timeSeries.map(t => t.errorRate),
        borderColor: '#f5222d',
        backgroundColor: 'transparent',
        yAxisID: 'y1',
        borderDash: [5, 5],
      },
    ],
  };

  const resourceUsageData = {
    labels: metrics.systemMetrics.timeSeries.map(t => 
      dayjs(t.timestamp).format('HH:mm')
    ),
    datasets: [
      {
        label: 'CPU 使用率 (%)',
        data: metrics.systemMetrics.timeSeries.map(t => t.cpuUsage),
        borderColor: '#52c41a',
        backgroundColor: 'rgba(82, 196, 26, 0.1)',
        fill: true,
      },
      {
        label: '記憶體使用率 (%)',
        data: metrics.systemMetrics.timeSeries.map(t => t.memoryUsage),
        borderColor: '#faad14',
        backgroundColor: 'rgba(250, 173, 20, 0.1)',
        fill: true,
      },
    ],
  };

  const apiCallsData = {
    labels: metrics.apiUsage.peakHours.map(h => `${h.hour}:00`),
    datasets: [
      {
        label: 'API 呼叫數',
        data: metrics.apiUsage.peakHours.map(h => h.calls),
        backgroundColor: 'rgba(24, 144, 255, 0.8)',
      },
    ],
  };

  const errorTrendsData = {
    labels: metrics.errorAnalysis.errorTrends.map(e => 
      dayjs(e.timestamp).format('HH:mm')
    ),
    datasets: [
      {
        label: '錯誤數',
        data: metrics.errorAnalysis.errorTrends.map(e => e.errorCount),
        backgroundColor: 'rgba(245, 34, 45, 0.8)',
        borderColor: '#f5222d',
      },
    ],
  };

  const apiEndpointsColumns: ColumnsType<any> = [
    {
      title: 'API 端點',
      dataIndex: 'endpoint',
      key: 'endpoint',
      width: 200,
    },
    {
      title: '呼叫次數',
      dataIndex: 'calls',
      key: 'calls',
      align: 'right',
      sorter: (a, b) => a.calls - b.calls,
      render: (value: number) => value.toLocaleString(),
    },
    {
      title: '平均回應時間',
      dataIndex: 'avgTime',
      key: 'avgTime',
      align: 'right',
      width: 120,
      sorter: (a, b) => a.avgTime - b.avgTime,
      render: (value: number) => (
        <Tag color={getHealthColor(value, 'responseTime')}>
          {value} ms
        </Tag>
      ),
    },
    {
      title: '錯誤數',
      dataIndex: 'errors',
      key: 'errors',
      align: 'right',
      width: 80,
      render: (value: number, record) => {
        const errorRate = (value / record.calls) * 100;
        return (
          <Tooltip title={`錯誤率: ${errorRate.toFixed(2)}%`}>
            <Tag color={errorRate > 1 ? 'error' : 'success'}>
              {value}
            </Tag>
          </Tooltip>
        );
      },
    },
  ];

  const featureUsageColumns: ColumnsType<any> = [
    {
      title: '功能',
      dataIndex: 'feature',
      key: 'feature',
    },
    {
      title: '使用次數',
      dataIndex: 'usage',
      key: 'usage',
      align: 'right',
      render: (value: number) => value.toLocaleString(),
    },
    {
      title: '使用者數',
      dataIndex: 'users',
      key: 'users',
      align: 'right',
    },
    {
      title: '平均使用',
      key: 'average',
      align: 'right',
      render: (_, record) => (record.usage / record.users).toFixed(1),
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              <DashboardOutlined /> 系統效能分析
            </Title>
            <Text type="secondary">監控系統效能與資源使用狀況</Text>
          </Col>
          <Col>
            <Space>
              <Select value={timeRange} onChange={setTimeRange} style={{ width: 120 }}>
                <Option value="1h">過去 1 小時</Option>
                <Option value="6h">過去 6 小時</Option>
                <Option value="24h">過去 24 小時</Option>
                <Option value="7d">過去 7 天</Option>
                <Option value="30d">過去 30 天</Option>
              </Select>
              <Button
                type={autoRefresh ? 'primary' : 'default'}
                icon={<ReloadOutlined spin={autoRefresh} />}
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                {autoRefresh ? '自動刷新' : '手動刷新'}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* System Health Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="平均回應時間"
              value={metrics.systemMetrics.averages.responseTime}
              suffix="ms"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ 
                color: getHealthColor(metrics.systemMetrics.averages.responseTime, 'responseTime') 
              }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="錯誤率"
              value={metrics.systemMetrics.averages.errorRate}
              suffix="%"
              prefix={<ExclamationCircleOutlined />}
              precision={2}
              valueStyle={{ 
                color: getHealthColor(metrics.systemMetrics.averages.errorRate, 'errorRate') 
              }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="吞吐量"
              value={metrics.systemMetrics.averages.throughput}
              suffix="req/min"
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="CPU 使用率"
              value={metrics.systemMetrics.averages.cpuUsage}
              suffix="%"
              prefix={<DatabaseOutlined />}
              valueStyle={{ 
                color: getHealthColor(metrics.systemMetrics.averages.cpuUsage, 'cpu') 
              }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="記憶體使用率"
              value={metrics.systemMetrics.averages.memoryUsage}
              suffix="%"
              prefix={<CloudServerOutlined />}
              valueStyle={{ 
                color: getHealthColor(metrics.systemMetrics.averages.memoryUsage, 'memory') 
              }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="API 總呼叫"
              value={metrics.apiUsage.totalCalls}
              prefix={<ApiOutlined />}
              formatter={(value) => `${(Number(value) / 1000).toFixed(1)}K`}
            />
          </Card>
        </Col>
      </Row>

      {/* Performance Charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="系統效能趨勢" extra={<LineChartOutlined />}>
            <Line
              data={systemPerformanceData}
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
                    title: {
                      display: true,
                      text: '回應時間 (ms)',
                    },
                  },
                  y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                      display: true,
                      text: '錯誤率 (%)',
                    },
                    grid: {
                      drawOnChartArea: false,
                    },
                  },
                },
              }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="資源使用趨勢" extra={<HeatMapOutlined />}>
            <Line
              data={resourceUsageData}
              options={{
                responsive: true,
                plugins: {
                  legend: { position: 'top' },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                      callback: (value: any) => `${value}%`,
                    },
                  },
                },
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* API and Error Analysis */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="API 呼叫高峰時段">
            <Bar
              data={apiCallsData}
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

        <Col xs={24} lg={8}>
          <Card title="錯誤類型分布">
            <List
              size="small"
              dataSource={metrics.errorAnalysis.errorTypes}
              renderItem={(error) => (
                <List.Item>
                  <List.Item.Meta
                    title={error.type}
                    description={`${error.percentage}%`}
                  />
                  <Badge count={error.count} style={{ backgroundColor: '#f5222d' }} />
                </List.Item>
              )}
            />
            <Divider />
            <Row>
              <Col span={8}>
                <Statistic
                  value={metrics.errorAnalysis.criticalErrors}
                  title="嚴重錯誤"
                  valueStyle={{ fontSize: 14, color: '#f5222d' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  value={metrics.errorAnalysis.resolvedErrors}
                  title="已解決"
                  valueStyle={{ fontSize: 14, color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  value={metrics.errorAnalysis.totalErrors - metrics.errorAnalysis.resolvedErrors}
                  title="待處理"
                  valueStyle={{ fontSize: 14, color: '#faad14' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="錯誤趨勢">
            <Bar
              data={errorTrendsData}
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

      {/* API Endpoints Performance */}
      <Card title="API 端點效能" style={{ marginBottom: 24 }}>
        <Table
          columns={apiEndpointsColumns}
          dataSource={metrics.apiUsage.endpoints}
          pagination={{ pageSize: 10 }}
          size="small"
          rowKey="endpoint"
        />
      </Card>

      {/* Resource Utilization */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="資料庫狀態">
            <List size="small">
              <List.Item>
                <Text>連線數</Text>
                <Progress
                  percent={(metrics.resourceUtilization.database.connections / 
                           metrics.resourceUtilization.database.maxConnections) * 100}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                  format={() => 
                    `${metrics.resourceUtilization.database.connections}/${metrics.resourceUtilization.database.maxConnections}`
                  }
                />
              </List.Item>
              <List.Item>
                <Text>平均查詢時間</Text>
                <Tag color={metrics.resourceUtilization.database.queryTime < 50 ? 'success' : 'warning'}>
                  {metrics.resourceUtilization.database.queryTime} ms
                </Tag>
              </List.Item>
              <List.Item>
                <Text>慢查詢</Text>
                <Badge 
                  count={metrics.resourceUtilization.database.slowQueries} 
                  style={{ 
                    backgroundColor: metrics.resourceUtilization.database.slowQueries > 10 ? '#f5222d' : '#faad14' 
                  }} 
                />
              </List.Item>
              <List.Item>
                <Text>磁碟使用率</Text>
                <Progress 
                  percent={metrics.resourceUtilization.database.diskUsage} 
                  strokeColor={getHealthColor(metrics.resourceUtilization.database.diskUsage, 'memory')}
                />
              </List.Item>
            </List>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="Redis 快取">
            <List size="small">
              <List.Item>
                <Text>記憶體使用</Text>
                <Tag>{metrics.resourceUtilization.redis.memoryUsage} MB</Tag>
              </List.Item>
              <List.Item>
                <Text>命中率</Text>
                <Progress 
                  percent={metrics.resourceUtilization.redis.hitRate} 
                  strokeColor="#52c41a"
                />
              </List.Item>
              <List.Item>
                <Text>驅逐次數</Text>
                <Badge 
                  count={metrics.resourceUtilization.redis.evictions} 
                  style={{ backgroundColor: '#faad14' }} 
                />
              </List.Item>
              <List.Item>
                <Text>連線客戶端</Text>
                <Tag color="blue">{metrics.resourceUtilization.redis.connectedClients}</Tag>
              </List.Item>
            </List>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="儲存空間">
            <Progress
              type="circle"
              percent={metrics.resourceUtilization.storage.percentage}
              strokeColor={{
                '0%': '#87d068',
                '50%': '#ffe58f',
                '100%': '#ffccc7',
              }}
              format={() => `${metrics.resourceUtilization.storage.used} GB`}
            />
            <Divider />
            <List
              size="small"
              header={<Text strong>最大資料表</Text>}
              dataSource={metrics.resourceUtilization.storage.largestTables}
              renderItem={(table) => (
                <List.Item>
                  <Text>{table.table}</Text>
                  <Text type="secondary">{table.size} GB</Text>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* User Activity */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="使用者活動">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="活躍使用者"
                  value={metrics.userActivity.totalActiveUsers}
                  prefix={<UserOutlined />}
                />
                <List
                  size="small"
                  dataSource={Object.entries(metrics.userActivity.activeUsersByRole)}
                  renderItem={([role, count]) => (
                    <List.Item>
                      <Text>{role}</Text>
                      <Tag>{count}</Tag>
                    </List.Item>
                  )}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="總工作階段"
                  value={metrics.userActivity.sessionData.totalSessions}
                  suffix={
                    <Text type="secondary" style={{ fontSize: 14 }}>
                      平均 {formatDuration(metrics.userActivity.sessionData.averageSessionDuration)}
                    </Text>
                  }
                />
                <Divider />
                <Row>
                  <Col span={12}>
                    <Statistic
                      value={metrics.userActivity.userGrowth.newUsers}
                      title="新使用者"
                      valueStyle={{ fontSize: 14, color: '#52c41a' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      value={metrics.userActivity.userGrowth.churnedUsers}
                      title="流失使用者"
                      valueStyle={{ fontSize: 14, color: '#f5222d' }}
                    />
                  </Col>
                </Row>
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="功能使用統計">
            <Table
              columns={featureUsageColumns}
              dataSource={metrics.userActivity.featureUsage}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* System Alerts */}
      {metrics.systemMetrics.alerts.length > 0 && (
        <Card title="系統警示" style={{ marginTop: 24 }}>
          <Timeline>
            {metrics.systemMetrics.alerts.map((alert, index) => (
              <Timeline.Item
                key={index}
                color={alert.severity === 'critical' ? 'red' : 'orange'}
                dot={<WarningOutlined />}
              >
                <Text strong>{alert.title}</Text>
                <br />
                <Text type="secondary">{alert.description}</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {dayjs(alert.timestamp).format('YYYY-MM-DD HH:mm:ss')}
                </Text>
              </Timeline.Item>
            ))}
          </Timeline>
        </Card>
      )}
    </div>
  );
};

export default PerformanceAnalytics;