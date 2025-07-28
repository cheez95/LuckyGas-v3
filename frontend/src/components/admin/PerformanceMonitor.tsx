import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, Table, Tag, Space, Button, Alert } from 'antd';
import { 
  DashboardOutlined, 
  ThunderboltOutlined, 
  ApiOutlined, 
  WarningOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  LineChartOutlined
} from '@ant-design/icons';
import { performanceMonitor, usePerformanceMonitor } from '../../services/performance.service';
import type { ColumnsType } from 'antd/es/table';

interface SlowEndpoint {
  endpoint: string;
  avgTime: number;
}

const PerformanceMonitor: React.FC = () => {
  const { generateReport, getCoreWebVitals } = usePerformanceMonitor();
  const [report, setReport] = useState<any>(null);
  const [coreWebVitals, setCoreWebVitals] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchMetrics = () => {
    setLoading(true);
    const newReport = generateReport();
    const vitals = getCoreWebVitals();
    setReport(newReport);
    setCoreWebVitals(vitals);
    setLoading(false);
  };

  useEffect(() => {
    fetchMetrics();
    
    if (autoRefresh) {
      const interval = setInterval(fetchMetrics, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getPerformanceScore = () => {
    if (!coreWebVitals) return 0;
    
    let score = 100;
    
    // LCP scoring (should be < 2.5s)
    if (coreWebVitals.lcp) {
      if (coreWebVitals.lcp > 4000) score -= 30;
      else if (coreWebVitals.lcp > 2500) score -= 15;
    }
    
    // FID scoring (should be < 100ms)
    if (coreWebVitals.fid) {
      if (coreWebVitals.fid > 300) score -= 30;
      else if (coreWebVitals.fid > 100) score -= 15;
    }
    
    // CLS scoring (should be < 0.1)
    if (coreWebVitals.cls) {
      if (coreWebVitals.cls > 0.25) score -= 30;
      else if (coreWebVitals.cls > 0.1) score -= 15;
    }
    
    // API performance
    if (report?.summary.avgApiResponseTime > 1000) score -= 10;
    if (report?.summary.errorRate > 0.05) score -= 15;
    
    return Math.max(0, score);
  };

  const performanceScore = getPerformanceScore();
  const performanceColor = performanceScore >= 80 ? '#52c41a' : performanceScore >= 60 ? '#faad14' : '#ff4d4f';

  const slowEndpointsColumns: ColumnsType<SlowEndpoint> = [
    {
      title: 'API 端點',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
    },
    {
      title: '平均回應時間',
      dataIndex: 'avgTime',
      key: 'avgTime',
      width: 150,
      render: (time) => {
        const color = time > 1000 ? 'red' : time > 500 ? 'orange' : 'green';
        return <Tag color={color}>{time.toFixed(0)}ms</Tag>;
      },
    },
  ];

  const getCoreWebVitalStatus = (metric: string, value: number | null) => {
    if (value === null) return { status: 'N/A', color: 'default' };
    
    switch (metric) {
      case 'lcp':
        if (value <= 2500) return { status: '良好', color: 'success' };
        if (value <= 4000) return { status: '需要改進', color: 'warning' };
        return { status: '差', color: 'error' };
      case 'fid':
        if (value <= 100) return { status: '良好', color: 'success' };
        if (value <= 300) return { status: '需要改進', color: 'warning' };
        return { status: '差', color: 'error' };
      case 'cls':
        if (value <= 0.1) return { status: '良好', color: 'success' };
        if (value <= 0.25) return { status: '需要改進', color: 'warning' };
        return { status: '差', color: 'error' };
      default:
        return { status: 'N/A', color: 'default' };
    }
  };

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Space>
            <LineChartOutlined style={{ fontSize: 24 }} />
            <h2 style={{ margin: 0 }}>效能監控儀表板</h2>
          </Space>
        </Col>
        <Col>
          <Space>
            <Button 
              icon={<SyncOutlined spin={loading} />} 
              onClick={fetchMetrics}
              loading={loading}
            >
              重新整理
            </Button>
            <Button 
              type={autoRefresh ? 'primary' : 'default'}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              自動更新: {autoRefresh ? '開啟' : '關閉'}
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Performance Score */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card>
            <Row align="middle" gutter={24}>
              <Col flex="none">
                <Progress
                  type="circle"
                  percent={performanceScore}
                  strokeColor={performanceColor}
                  format={() => (
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 24, fontWeight: 'bold' }}>{performanceScore}</div>
                      <div style={{ fontSize: 12 }}>效能分數</div>
                    </div>
                  )}
                />
              </Col>
              <Col flex="auto">
                <Space direction="vertical">
                  <h3>整體效能評估</h3>
                  <p style={{ margin: 0 }}>
                    基於 Core Web Vitals 和 API 效能指標的綜合評分。
                    {performanceScore >= 80 && ' 您的應用程式運行良好！'}
                    {performanceScore >= 60 && performanceScore < 80 && ' 有一些地方可以優化。'}
                    {performanceScore < 60 && ' 需要立即關注效能問題。'}
                  </p>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Core Web Vitals */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Largest Contentful Paint (LCP)"
              value={coreWebVitals?.lcp || 0}
              suffix="ms"
              prefix={<DashboardOutlined />}
              valueStyle={{ color: getCoreWebVitalStatus('lcp', coreWebVitals?.lcp).color === 'success' ? '#52c41a' : 
                                   getCoreWebVitalStatus('lcp', coreWebVitals?.lcp).color === 'warning' ? '#faad14' : '#ff4d4f' }}
            />
            <Tag color={getCoreWebVitalStatus('lcp', coreWebVitals?.lcp).color as any}>
              {getCoreWebVitalStatus('lcp', coreWebVitals?.lcp).status}
            </Tag>
            <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
              載入效能 - 應該 &lt; 2.5秒
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="First Input Delay (FID)"
              value={coreWebVitals?.fid || 0}
              suffix="ms"
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: getCoreWebVitalStatus('fid', coreWebVitals?.fid).color === 'success' ? '#52c41a' : 
                                   getCoreWebVitalStatus('fid', coreWebVitals?.fid).color === 'warning' ? '#faad14' : '#ff4d4f' }}
            />
            <Tag color={getCoreWebVitalStatus('fid', coreWebVitals?.fid).color as any}>
              {getCoreWebVitalStatus('fid', coreWebVitals?.fid).status}
            </Tag>
            <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
              互動性 - 應該 &lt; 100ms
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Cumulative Layout Shift (CLS)"
              value={coreWebVitals?.cls || 0}
              precision={3}
              prefix={<WarningOutlined />}
              valueStyle={{ color: getCoreWebVitalStatus('cls', coreWebVitals?.cls).color === 'success' ? '#52c41a' : 
                                   getCoreWebVitalStatus('cls', coreWebVitals?.cls).color === 'warning' ? '#faad14' : '#ff4d4f' }}
            />
            <Tag color={getCoreWebVitalStatus('cls', coreWebVitals?.cls).color as any}>
              {getCoreWebVitalStatus('cls', coreWebVitals?.cls).status}
            </Tag>
            <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
              視覺穩定性 - 應該 &lt; 0.1
            </div>
          </Card>
        </Col>
      </Row>

      {/* API Performance */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} md={6}>
          <Card>
            <Statistic
              title="平均 API 回應時間"
              value={report?.summary.avgApiResponseTime || 0}
              suffix="ms"
              prefix={<ApiOutlined />}
              valueStyle={{ color: report?.summary.avgApiResponseTime > 1000 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic
              title="API 呼叫總數"
              value={report?.summary.totalApiCalls || 0}
              prefix={<SyncOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic
              title="錯誤率"
              value={(report?.summary.errorRate || 0) * 100}
              suffix="%"
              precision={1}
              prefix={report?.summary.errorRate > 0.05 ? <WarningOutlined /> : <CheckCircleOutlined />}
              valueStyle={{ color: report?.summary.errorRate > 0.05 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic
              title="平均頁面載入時間"
              value={report?.summary.avgPageLoadTime || 0}
              suffix="ms"
              prefix={<DashboardOutlined />}
              valueStyle={{ color: report?.summary.avgPageLoadTime > 3000 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Slowest Endpoints */}
      <Row gutter={16}>
        <Col span={24}>
          <Card title="最慢的 API 端點" extra={<Tag color="orange">需要優化</Tag>}>
            {report?.summary.slowestEndpoints.length > 0 ? (
              <Table
                columns={slowEndpointsColumns}
                dataSource={report.summary.slowestEndpoints}
                rowKey="endpoint"
                pagination={false}
                size="small"
              />
            ) : (
              <Alert
                message="沒有發現緩慢的 API 端點"
                description="所有 API 回應時間都在可接受範圍內。"
                type="success"
                showIcon
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* Performance Tips */}
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={24}>
          <Alert
            message="效能優化建議"
            description={
              <ul style={{ marginBottom: 0 }}>
                {performanceScore < 80 && <li>考慮實施懶加載以改善 LCP</li>}
                {coreWebVitals?.fid > 100 && <li>減少主線程阻塞的 JavaScript 執行</li>}
                {coreWebVitals?.cls > 0.1 && <li>為動態內容預留空間以減少佈局偏移</li>}
                {report?.summary.avgApiResponseTime > 1000 && <li>優化後端 API 效能或實施快取策略</li>}
                {report?.summary.errorRate > 0.05 && <li>調查並修復高錯誤率的 API 端點</li>}
              </ul>
            }
            type="info"
            showIcon
          />
        </Col>
      </Row>
    </div>
  );
};

export default PerformanceMonitor;