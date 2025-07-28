import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Button, Space, Typography, Select, DatePicker, Badge, Tabs, Empty } from 'antd';
import {
  DashboardOutlined,
  ReloadOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import dayjs, { Dayjs } from 'dayjs';
import DispatchMetrics from '../../components/dispatch/dashboard/DispatchMetrics';
import LiveRouteTracker from '../../components/dispatch/dashboard/LiveRouteTracker';
import EmergencyAlertBanner from '../../components/dispatch/emergency/EmergencyAlertBanner';
import PriorityQueueManager from '../../components/dispatch/emergency/PriorityQueueManager';
import { useWebSocketContext } from '../../contexts/WebSocketContext';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const DispatchDashboard: React.FC = () => {
  const { t } = useTranslation();
  const { isConnected } = useWebSocketContext();
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [selectedArea, setSelectedArea] = useState<string>('all');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    // Set up auto-refresh every minute
    const refreshInterval = setInterval(() => {
      setRefreshKey(prev => prev + 1);
    }, 60000);

    return () => clearInterval(refreshInterval);
  }, []);

  const handleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleManualRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleEmergencyAlert = (alert: any) => {
    // Switch to emergency tab when alert is clicked
    setActiveTab('emergency');
  };

  return (
    <div style={{ padding: isFullscreen ? '8px' : '24px', backgroundColor: '#f0f2f5' }}>
      {/* Emergency Alert Banner */}
      <EmergencyAlertBanner onAlertClick={handleEmergencyAlert} />

      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space size="large">
              <DashboardOutlined style={{ fontSize: 32, color: '#1890ff' }} />
              <div>
                <Title level={3} style={{ margin: 0 }}>
                  {t('dispatch.dashboard.title')}
                </Title>
                <Space>
                  <Badge
                    status={isConnected ? 'success' : 'error'}
                    text={
                      <Text type="secondary">
                        {isConnected ? t('common.status.online') : t('common.status.offline')}
                      </Text>
                    }
                  />
                  <Text type="secondary">
                    {t('dispatch.dashboard.lastRefresh')}: {new Date().toLocaleTimeString('zh-TW')}
                  </Text>
                </Space>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <DatePicker
                value={selectedDate}
                onChange={(date) => setSelectedDate(date || dayjs())}
                format="YYYY-MM-DD"
              />
              <Select
                value={selectedArea}
                onChange={setSelectedArea}
                style={{ width: 120 }}
                suffixIcon={<FilterOutlined />}
              >
                <Select.Option value="all">{t('dispatch.route.allAreas')}</Select.Option>
                <Select.Option value="信義區">信義區</Select.Option>
                <Select.Option value="大安區">大安區</Select.Option>
                <Select.Option value="中山區">中山區</Select.Option>
                <Select.Option value="松山區">松山區</Select.Option>
                <Select.Option value="內湖區">內湖區</Select.Option>
              </Select>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleManualRefresh}
              >
                {t('common.action.refresh')}
              </Button>
              <Button
                icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                onClick={handleFullscreen}
              >
                {isFullscreen ? t('common.action.exitFullscreen') : t('common.action.fullscreen')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Main Content */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        size="large"
      >
        <TabPane
          tab={
            <span>
              <DashboardOutlined />
              {t('dispatch.dashboard.overview')}
            </span>
          }
          key="overview"
        >
          {/* Metrics Dashboard */}
          <DispatchMetrics key={`metrics-${refreshKey}`} />
          
          {/* Live Route Tracking */}
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={24}>
              <LiveRouteTracker
                key={`tracker-${refreshKey}`}
                maxHeight={isFullscreen ? 'calc(100vh - 400px)' : '600px'}
              />
            </Col>
          </Row>
        </TabPane>
        
        <TabPane
          tab={
            <span>
              <Badge count={2} offset={[10, 0]}>
                <span>
                  🚨 {t('dispatch.dashboard.emergency')}
                </span>
              </Badge>
            </span>
          }
          key="emergency"
        >
          <Row gutter={16}>
            <Col span={24}>
              <PriorityQueueManager
                onDispatch={(order) => {
                  console.log('Dispatch emergency order:', order);
                }}
              />
            </Col>
          </Row>
        </TabPane>
        
        <TabPane
          tab={
            <span>
              📊 {t('dispatch.dashboard.analytics')}
            </span>
          }
          key="analytics"
        >
          {/* Analytics content would go here */}
          <Card>
            <Empty description={t('common.comingSoon')} />
          </Card>
        </TabPane>
      </Tabs>

      {/* Footer Status Bar (only in fullscreen) */}
      {isFullscreen && (
        <Card
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            borderRadius: 0,
            boxShadow: '0 -2px 8px rgba(0,0,0,0.15)',
          }}
          bodyStyle={{ padding: '8px 24px' }}
        >
          <Row align="middle">
            <Col flex="auto">
              <Space split="|">
                <Text>{t('dispatch.dashboard.dispatchCenter')}</Text>
                <Text>{new Date().toLocaleString('zh-TW')}</Text>
                <Badge
                  status={isConnected ? 'success' : 'error'}
                  text={isConnected ? t('common.status.connected') : t('common.status.disconnected')}
                />
              </Space>
            </Col>
            <Col>
              <Button
                type="text"
                icon={<FullscreenExitOutlined />}
                onClick={handleFullscreen}
              >
                {t('common.action.exitFullscreen')}
              </Button>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
};

export default DispatchDashboard;