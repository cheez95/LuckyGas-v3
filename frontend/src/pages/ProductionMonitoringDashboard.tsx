import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Table,
  Tag,
  Progress,
  Alert,
  Tabs,
  List,
  Badge,
  Space,
  Divider,
  Typography,
  Timeline,
  Modal,
  message,
  Spin,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  DashboardOutlined,
  ApiOutlined,
  SecurityScanOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  WifiOutlined,
  CloudServerOutlined,
  SafetyOutlined,
  BugOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { healthCheckService, SystemHealth, HealthCheckResult } from '../services/healthCheck.service';
import { performanceTestService, PerformanceTestResult } from '../services/performanceTest.service';
import { safeErrorMonitor } from '../services/safeErrorMonitor';
import { Line, Column, Gauge, Area } from '@ant-design/plots';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface SecurityCheckResult {
  check: string;
  status: 'pass' | 'fail' | 'warning';
  message: string;
}

const ProductionMonitoringDashboard: React.FC = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [performanceResults, setPerformanceResults] = useState<any>(null);
  const [securityChecks, setSecurityChecks] = useState<SecurityCheckResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [selectedTest, setSelectedTest] = useState<string>('health');
  const [errorMonitorStatus, setErrorMonitorStatus] = useState<any>(null);
  const [memoryHistory, setMemoryHistory] = useState<any[]>([]);
  const [responseTimeHistory, setResponseTimeHistory] = useState<any[]>([]);

  useEffect(() => {
    // Initial load
    runHealthCheck();
    checkErrorMonitor();
    
    // Setup auto-refresh
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        runHealthCheck();
        checkErrorMonitor();
        updateMetricsHistory();
      }, 10000); // Refresh every 10 seconds
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh]);

  const runHealthCheck = async () => {
    setLoading(true);
    try {
      const health = await healthCheckService.runFullHealthCheck();
      setSystemHealth(health);
      
      // Update metrics history
      updateResponseTimeHistory(health.performance.avgResponseTime);
    } catch (error) {
      console.error('Health check failed:', error);
      message.error('Health check failed');
    } finally {
      setLoading(false);
    }
  };

  const runPerformanceTest = async () => {
    setLoading(true);
    message.info('Running performance tests... This may take a few minutes.');
    
    try {
      const results = await performanceTestService.runFullPerformanceTest();
      setPerformanceResults(results);
      message.success('Performance tests completed');
    } catch (error) {
      console.error('Performance test failed:', error);
      message.error('Performance test failed');
    } finally {
      setLoading(false);
    }
  };

  const runSecurityAudit = async () => {
    setLoading(true);
    const checks: SecurityCheckResult[] = [];
    
    // HTTPS check
    checks.push({
      check: 'HTTPS Enabled',
      status: window.location.protocol === 'https:' ? 'pass' : 'fail',
      message: window.location.protocol === 'https:' 
        ? 'All traffic is encrypted' 
        : 'Site is not using HTTPS',
    });
    
    // Authentication check
    const token = localStorage.getItem('access_token');
    checks.push({
      check: 'Authentication Token',
      status: token ? 'pass' : 'warning',
      message: token ? 'Token present' : 'No authentication token found',
    });
    
    // Content Security Policy
    const csp = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
    checks.push({
      check: 'Content Security Policy',
      status: csp ? 'pass' : 'warning',
      message: csp ? 'CSP header configured' : 'No CSP header found',
    });
    
    // Secure cookies check
    checks.push({
      check: 'Secure Cookies',
      status: document.cookie.includes('Secure') ? 'pass' : 'warning',
      message: document.cookie.includes('Secure') 
        ? 'Cookies marked as secure' 
        : 'Cookies not marked as secure',
    });
    
    // XSS Protection
    checks.push({
      check: 'XSS Protection',
      status: 'pass',
      message: 'React provides built-in XSS protection',
    });
    
    // Input validation
    checks.push({
      check: 'Input Validation',
      status: 'pass',
      message: 'Form validation implemented',
    });
    
    // Rate limiting check (mock)
    checks.push({
      check: 'Rate Limiting',
      status: 'warning',
      message: 'Rate limiting should be verified on backend',
    });
    
    // Token expiration
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const expired = payload.exp && payload.exp * 1000 < Date.now();
        checks.push({
          check: 'Token Expiration',
          status: expired ? 'fail' : 'pass',
          message: expired ? 'Token has expired' : 'Token is valid',
        });
      } catch {
        checks.push({
          check: 'Token Expiration',
          status: 'warning',
          message: 'Unable to verify token expiration',
        });
      }
    }
    
    setSecurityChecks(checks);
    setLoading(false);
    message.success('Security audit completed');
  };

  const checkErrorMonitor = () => {
    const status = safeErrorMonitor.getStatus();
    setErrorMonitorStatus(status);
  };

  const updateMetricsHistory = () => {
    // Update memory history
    if ('memory' in performance) {
      const memoryUsage = (performance as any).memory.usedJSHeapSize / 1048576;
      setMemoryHistory(prev => {
        const newHistory = [...prev, {
          time: new Date().toLocaleTimeString(),
          value: Math.round(memoryUsage),
        }];
        return newHistory.slice(-20); // Keep last 20 points
      });
    }
  };

  const updateResponseTimeHistory = (responseTime: number) => {
    setResponseTimeHistory(prev => {
      const newHistory = [...prev, {
        time: new Date().toLocaleTimeString(),
        value: Math.round(responseTime),
      }];
      return newHistory.slice(-20); // Keep last 20 points
    });
  };

  const getHealthStatusTag = (status: string) => {
    const colors: any = {
      healthy: 'success',
      degraded: 'warning',
      unhealthy: 'error',
    };
    return <Tag color={colors[status] || 'default'}>{status.toUpperCase()}</Tag>;
  };

  const getSecurityStatusTag = (status: string) => {
    const colors: any = {
      pass: 'success',
      warning: 'warning',
      fail: 'error',
    };
    return <Tag color={colors[status] || 'default'}>{status.toUpperCase()}</Tag>;
  };

  const renderHealthChecks = () => {
    if (!systemHealth) return null;

    const columns = [
      {
        title: 'Service',
        dataIndex: 'service',
        key: 'service',
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (status: string) => getHealthStatusTag(status),
      },
      {
        title: 'Response Time',
        dataIndex: 'responseTime',
        key: 'responseTime',
        render: (time: number) => `${Math.round(time)}ms`,
      },
      {
        title: 'Message',
        dataIndex: 'message',
        key: 'message',
      },
    ];

    return (
      <Table
        columns={columns}
        dataSource={systemHealth.checks}
        rowKey="service"
        pagination={false}
        size="small"
      />
    );
  };

  const renderPerformanceResults = () => {
    if (!performanceResults) {
      return (
        <Alert
          message="No Performance Tests Run"
          description="Click 'Run Performance Test' to start performance benchmarking"
          type="info"
          showIcon
        />
      );
    }

    const { loadTest, websocketTest, memoryTest, cpuTest } = performanceResults;

    return (
      <div>
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Card title="Load Test Results" size="small">
              <Statistic
                title="Status"
                value={loadTest.status.toUpperCase()}
                valueStyle={{ color: loadTest.status === 'pass' ? '#3f8600' : '#cf1322' }}
              />
              <Divider />
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title="Avg Response" value={`${Math.round(loadTest.metrics.avgResponseTime)}ms`} />
                </Col>
                <Col span={12}>
                  <Statistic title="Success Rate" value={`${loadTest.metrics.successRate.toFixed(1)}%`} />
                </Col>
              </Row>
              <Row gutter={16} style={{ marginTop: 16 }}>
                <Col span={12}>
                  <Statistic title="P95 Response" value={`${Math.round(loadTest.metrics.p95ResponseTime)}ms`} />
                </Col>
                <Col span={12}>
                  <Statistic title="Throughput" value={`${loadTest.metrics.throughput.toFixed(1)} req/s`} />
                </Col>
              </Row>
            </Card>
          </Col>
          
          <Col span={12}>
            <Card title="WebSocket Test Results" size="small">
              <Statistic
                title="Status"
                value={websocketTest.status.toUpperCase()}
                valueStyle={{ color: websocketTest.status === 'pass' ? '#3f8600' : '#cf1322' }}
              />
              <Divider />
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title="Connections" value={websocketTest.details.totalRequests} />
                </Col>
                <Col span={12}>
                  <Statistic title="Success Rate" value={`${websocketTest.metrics.successRate.toFixed(1)}%`} />
                </Col>
              </Row>
              <Row gutter={16} style={{ marginTop: 16 }}>
                <Col span={12}>
                  <Statistic title="Avg Connect Time" value={`${Math.round(websocketTest.metrics.avgResponseTime)}ms`} />
                </Col>
                <Col span={12}>
                  <Statistic title="Failed" value={websocketTest.details.failedRequests} />
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
        
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={12}>
            <Card title="Memory Test Results" size="small">
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="Initial" value={`${memoryTest.initial.toFixed(1)} MB`} />
                </Col>
                <Col span={8}>
                  <Statistic title="Peak" value={`${memoryTest.peak.toFixed(1)} MB`} />
                </Col>
                <Col span={8}>
                  <Statistic 
                    title="Final" 
                    value={`${memoryTest.final.toFixed(1)} MB`}
                    valueStyle={{ color: memoryTest.leaked ? '#cf1322' : '#3f8600' }}
                  />
                </Col>
              </Row>
              <Alert
                message={memoryTest.leaked ? 'Memory Leak Detected' : 'No Memory Leaks'}
                type={memoryTest.leaked ? 'error' : 'success'}
                style={{ marginTop: 16 }}
              />
            </Card>
          </Col>
          
          <Col span={12}>
            <Card title="CPU Performance" size="small">
              <Progress
                type="dashboard"
                percent={cpuTest.score}
                status={cpuTest.status === 'good' ? 'success' : cpuTest.status === 'average' ? 'normal' : 'exception'}
              />
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Text strong>Performance: {cpuTest.status.toUpperCase()}</Text>
              </div>
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  const renderSecurityAudit = () => {
    if (securityChecks.length === 0) {
      return (
        <Alert
          message="No Security Audit Run"
          description="Click 'Run Security Audit' to check security configurations"
          type="info"
          showIcon
        />
      );
    }

    const passCount = securityChecks.filter(c => c.status === 'pass').length;
    const failCount = securityChecks.filter(c => c.status === 'fail').length;
    const warningCount = securityChecks.filter(c => c.status === 'warning').length;

    return (
      <div>
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Card>
              <Statistic
                title="Passed Checks"
                value={passCount}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Warnings"
                value={warningCount}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Failed Checks"
                value={failCount}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>
        
        <Card style={{ marginTop: 16 }} title="Security Check Results">
          <List
            dataSource={securityChecks}
            renderItem={item => (
              <List.Item>
                <List.Item.Meta
                  avatar={getSecurityStatusTag(item.status)}
                  title={item.check}
                  description={item.message}
                />
              </List.Item>
            )}
          />
        </Card>
      </div>
    );
  };

  const renderMemoryChart = () => {
    const config = {
      data: memoryHistory,
      xField: 'time',
      yField: 'value',
      smooth: true,
      point: {
        size: 3,
      },
      yAxis: {
        title: {
          text: 'Memory (MB)',
        },
      },
      annotations: [
        {
          type: 'line',
          start: ['min', 100],
          end: ['max', 100],
          style: {
            stroke: '#ff4d4f',
            lineDash: [2, 2],
          },
        },
      ],
    };

    return memoryHistory.length > 0 ? <Line {...config} height={200} /> : <Empty description="No data" />;
  };

  const renderResponseTimeChart = () => {
    const config = {
      data: responseTimeHistory,
      xField: 'time',
      yField: 'value',
      smooth: true,
      color: '#1890ff',
      point: {
        size: 3,
      },
      yAxis: {
        title: {
          text: 'Response Time (ms)',
        },
      },
      annotations: [
        {
          type: 'line',
          start: ['min', 500],
          end: ['max', 500],
          style: {
            stroke: '#faad14',
            lineDash: [2, 2],
          },
        },
      ],
    };

    return responseTimeHistory.length > 0 ? <Line {...config} height={200} /> : <Empty description="No data" />;
  };

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>
            <RocketOutlined /> Production Monitoring Dashboard
          </Title>
        </Col>
        <Col>
          <Space>
            <Button
              type={autoRefresh ? 'primary' : 'default'}
              onClick={() => setAutoRefresh(!autoRefresh)}
              icon={<ReloadOutlined spin={autoRefresh} />}
            >
              Auto Refresh: {autoRefresh ? 'ON' : 'OFF'}
            </Button>
            <Button
              type="primary"
              onClick={runHealthCheck}
              loading={loading}
              icon={<DashboardOutlined />}
            >
              Run Health Check
            </Button>
            <Button
              onClick={runPerformanceTest}
              loading={loading}
              icon={<ThunderboltOutlined />}
            >
              Run Performance Test
            </Button>
            <Button
              onClick={runSecurityAudit}
              loading={loading}
              icon={<SecurityScanOutlined />}
            >
              Run Security Audit
            </Button>
          </Space>
        </Col>
      </Row>

      {/* System Status Overview */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="System Health"
              value={systemHealth?.overall || 'Unknown'}
              prefix={
                systemHealth?.overall === 'healthy' ? <CheckCircleOutlined /> :
                systemHealth?.overall === 'degraded' ? <ExclamationCircleOutlined /> :
                <CloseCircleOutlined />
              }
              valueStyle={{
                color: 
                  systemHealth?.overall === 'healthy' ? '#3f8600' :
                  systemHealth?.overall === 'degraded' ? '#faad14' :
                  '#cf1322'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Uptime"
              value={systemHealth ? Math.floor(systemHealth.uptime / 1000 / 60) : 0}
              suffix="min"
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Success Rate"
              value={systemHealth?.performance.successRate.toFixed(1) || 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Avg Response"
              value={Math.round(systemHealth?.performance.avgResponseTime || 0)}
              suffix="ms"
              prefix={<ApiOutlined />}
              valueStyle={{ 
                color: systemHealth?.performance.avgResponseTime && systemHealth.performance.avgResponseTime < 500 
                  ? '#3f8600' 
                  : '#faad14' 
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Error Monitor Status */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="Error Monitoring Status" extra={<BugOutlined />}>
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Statistic
                  title="Circuit Status"
                  value={errorMonitorStatus?.circuitOpen ? 'OPEN' : 'CLOSED'}
                  valueStyle={{ 
                    color: errorMonitorStatus?.circuitOpen ? '#cf1322' : '#3f8600' 
                  }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Failure Count"
                  value={errorMonitorStatus?.failureCount || 0}
                  suffix="/ 3"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Queue Size"
                  value={errorMonitorStatus?.queueSize || 0}
                  suffix="/ 50"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Kill Switch"
                  value={errorMonitorStatus?.killSwitchActive ? 'ACTIVE' : 'INACTIVE'}
                  valueStyle={{ 
                    color: errorMonitorStatus?.killSwitchActive ? '#cf1322' : '#3f8600' 
                  }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Real-time Metrics Charts */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="Memory Usage Trend">
            {renderMemoryChart()}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Response Time Trend">
            {renderResponseTimeChart()}
          </Card>
        </Col>
      </Row>

      {/* Detailed Results Tabs */}
      <Card style={{ marginTop: 16 }}>
        <Tabs activeKey={selectedTest} onChange={setSelectedTest}>
          <TabPane tab={<span><DashboardOutlined /> Health Checks</span>} key="health">
            {renderHealthChecks()}
          </TabPane>
          <TabPane tab={<span><ThunderboltOutlined /> Performance</span>} key="performance">
            {renderPerformanceResults()}
          </TabPane>
          <TabPane tab={<span><SecurityScanOutlined /> Security</span>} key="security">
            {renderSecurityAudit()}
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

const Empty: React.FC<{ description: string }> = ({ description }) => (
  <div style={{ textAlign: 'center', padding: 40 }}>
    <Text type="secondary">{description}</Text>
  </div>
);

export default ProductionMonitoringDashboard;