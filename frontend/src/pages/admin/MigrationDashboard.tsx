import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Button,
  Space,
  Alert,
  Modal,
  Form,
  InputNumber,
  Select,
  Divider,
  Timeline,
  Badge,
  Tabs,
  message,
  Spin,
  Typography,
  Switch,
  Popconfirm,
  Tooltip,
  Input
} from 'antd';
import {
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  RollbackOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  DownloadOutlined,
  UploadOutlined,
  TeamOutlined,
  LineChartOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { ColumnsType } from 'antd/es/table';
import { Line, Pie } from '@ant-design/plots';
import { PageContainer } from '@/components/layouts';
import { useRequest, useInterval } from '@/hooks';
import api from '@/services/api';
import { formatDateTime, formatNumber } from '@/utils/format';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface MigrationMetrics {
  totalCustomers: number;
  migratedCustomers: number;
  pendingCustomers: number;
  failedCustomers: number;
  successRate: number;
  averageSyncTime: number;
  lastSyncAt: string;
  estimatedCompletion: string;
}

interface SyncOperation {
  id: string;
  entityType: string;
  entityId: string;
  direction: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'conflict';
  createdAt: string;
  completedAt?: string;
  errorMessage?: string;
  retryCount: number;
}

interface FeatureFlag {
  name: string;
  description: string;
  type: string;
  status: string;
  percentage?: number;
  enabledCustomers?: number;
}

interface ConflictItem {
  id: string;
  entityType: string;
  entityId: string;
  customerName?: string;
  conflictType: string;
  detectedAt: string;
  newValue: any;
  legacyValue: any;
}

const MigrationDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<MigrationMetrics | null>(null);
  const [syncOperations, setSyncOperations] = useState<SyncOperation[]>([]);
  const [featureFlags, setFeatureFlags] = useState<FeatureFlag[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [isSyncEnabled, setIsSyncEnabled] = useState(true);
  const [selectedCustomers, setSelectedCustomers] = useState<string[]>([]);
  const [isSelectionModalVisible, setIsSelectionModalVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [refreshInterval, setRefreshInterval] = useState(5000); // 5 seconds

  // Fetch migration metrics
  const { loading: metricsLoading, run: fetchMetrics } = useRequest(
    async () => {
      const response = await api.get('/admin/migration/metrics');
      setMetrics(response.data);
      return response.data;
    },
    {
      pollingInterval: refreshInterval,
    }
  );

  // Fetch sync operations
  const { loading: operationsLoading, run: fetchOperations } = useRequest(
    async () => {
      const response = await api.get('/admin/migration/sync-operations', {
        params: { limit: 50 }
      });
      setSyncOperations(response.data);
      return response.data;
    }
  );

  // Fetch feature flags
  const { run: fetchFeatureFlags } = useRequest(
    async () => {
      const response = await api.get('/admin/feature-flags');
      setFeatureFlags(response.data);
      return response.data;
    }
  );

  // Fetch conflicts
  const { run: fetchConflicts } = useRequest(
    async () => {
      const response = await api.get('/admin/migration/conflicts');
      setConflicts(response.data);
      return response.data;
    }
  );

  // Toggle sync service
  const handleToggleSync = async () => {
    try {
      const endpoint = isSyncEnabled ? '/admin/migration/pause' : '/admin/migration/resume';
      await api.post(endpoint);
      setIsSyncEnabled(!isSyncEnabled);
      message.success(`同步服務已${isSyncEnabled ? '暫停' : '恢復'}`);
    } catch (error) {
      message.error('操作失敗');
    }
  };

  // Handle customer selection
  const handleSelectCustomers = async (values: any) => {
    try {
      const response = await api.post('/admin/migration/select-customers', values);
      setSelectedCustomers(response.data.customerIds);
      message.success(`已選擇 ${response.data.customerIds.length} 位客戶`);
      setIsSelectionModalVisible(false);
    } catch (error) {
      message.error('選擇客戶失敗');
    }
  };

  // Start migration
  const handleStartMigration = async () => {
    if (selectedCustomers.length === 0) {
      message.warning('請先選擇要遷移的客戶');
      return;
    }

    try {
      await api.post('/admin/migration/start', {
        customerIds: selectedCustomers
      });
      message.success('遷移已開始');
      fetchMetrics();
    } catch (error) {
      message.error('啟動遷移失敗');
    }
  };

  // Rollback migration
  const handleRollback = async () => {
    try {
      await api.post('/admin/migration/rollback');
      message.success('回滾已開始');
      fetchMetrics();
    } catch (error) {
      message.error('回滾失敗');
    }
  };

  // Resolve conflict
  const handleResolveConflict = async (conflictId: string, resolution: string) => {
    try {
      await api.post(`/admin/migration/conflicts/${conflictId}/resolve`, {
        resolution
      });
      message.success('衝突已解決');
      fetchConflicts();
    } catch (error) {
      message.error('解決衝突失敗');
    }
  };

  // Update feature flag
  const handleUpdateFeatureFlag = async (flagName: string, value: any) => {
    try {
      await api.put(`/admin/feature-flags/${flagName}`, value);
      message.success('功能標誌已更新');
      fetchFeatureFlags();
    } catch (error) {
      message.error('更新功能標誌失敗');
    }
  };

  // Auto refresh
  useInterval(() => {
    if (activeTab === 'overview') {
      fetchMetrics();
      fetchOperations();
    } else if (activeTab === 'conflicts') {
      fetchConflicts();
    }
  }, refreshInterval);

  // Sync operations table columns
  const operationColumns: ColumnsType<SyncOperation> = [
    {
      title: '操作ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
      ellipsis: true,
    },
    {
      title: '實體類型',
      dataIndex: 'entityType',
      key: 'entityType',
      render: (type) => (
        <Tag color="blue">{type}</Tag>
      ),
    },
    {
      title: '實體ID',
      dataIndex: 'entityId',
      key: 'entityId',
      ellipsis: true,
    },
    {
      title: '同步方向',
      dataIndex: 'direction',
      key: 'direction',
      render: (direction) => {
        const directionMap: Record<string, { text: string; icon: React.ReactNode }> = {
          to_legacy: { text: '到舊系統', icon: <UploadOutlined /> },
          from_legacy: { text: '從舊系統', icon: <DownloadOutlined /> },
          bidirectional: { text: '雙向', icon: <SyncOutlined /> },
        };
        const config = directionMap[direction] || { text: direction, icon: null };
        return (
          <Space>
            {config.icon}
            {config.text}
          </Space>
        );
      },
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          pending: { color: 'default', text: '待處理' },
          in_progress: { color: 'processing', text: '處理中' },
          completed: { color: 'success', text: '已完成' },
          failed: { color: 'error', text: '失敗' },
          conflict: { color: 'warning', text: '衝突' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '重試次數',
      dataIndex: 'retryCount',
      key: 'retryCount',
      width: 100,
      render: (count) => (
        <Badge count={count} style={{ backgroundColor: count > 0 ? '#f5222d' : '#52c41a' }} />
      ),
    },
    {
      title: '創建時間',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (time) => formatDateTime(time),
    },
    {
      title: '錯誤訊息',
      dataIndex: 'errorMessage',
      key: 'errorMessage',
      ellipsis: true,
      render: (error) => error && (
        <Tooltip title={error}>
          <Text type="danger">{error}</Text>
        </Tooltip>
      ),
    },
  ];

  // Conflicts table columns
  const conflictColumns: ColumnsType<ConflictItem> = [
    {
      title: '衝突ID',
      dataIndex: 'id',
      key: 'id',
      width: 150,
      ellipsis: true,
    },
    {
      title: '客戶名稱',
      dataIndex: 'customerName',
      key: 'customerName',
    },
    {
      title: '衝突類型',
      dataIndex: 'conflictType',
      key: 'conflictType',
      render: (type) => (
        <Tag color="warning">{type}</Tag>
      ),
    },
    {
      title: '新系統值',
      dataIndex: 'newValue',
      key: 'newValue',
      render: (value) => (
        <Paragraph copyable ellipsis={{ rows: 2 }}>
          {JSON.stringify(value, null, 2)}
        </Paragraph>
      ),
    },
    {
      title: '舊系統值',
      dataIndex: 'legacyValue',
      key: 'legacyValue',
      render: (value) => (
        <Paragraph copyable ellipsis={{ rows: 2 }}>
          {JSON.stringify(value, null, 2)}
        </Paragraph>
      ),
    },
    {
      title: '檢測時間',
      dataIndex: 'detectedAt',
      key: 'detectedAt',
      render: (time) => formatDateTime(time),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            type="primary"
            onClick={() => handleResolveConflict(record.id, 'new_system_wins')}
          >
            使用新值
          </Button>
          <Button
            size="small"
            onClick={() => handleResolveConflict(record.id, 'legacy_wins')}
          >
            使用舊值
          </Button>
          <Button
            size="small"
            type="link"
            onClick={() => {
              Modal.info({
                title: '衝突詳情',
                content: (
                  <div>
                    <Title level={5}>新系統值：</Title>
                    <pre>{JSON.stringify(record.newValue, null, 2)}</pre>
                    <Divider />
                    <Title level={5}>舊系統值：</Title>
                    <pre>{JSON.stringify(record.legacyValue, null, 2)}</pre>
                  </div>
                ),
                width: 600,
              });
            }}
          >
            詳情
          </Button>
        </Space>
      ),
    },
  ];

  // Feature flags columns
  const featureFlagColumns: ColumnsType<FeatureFlag> = [
    {
      title: '功能名稱',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '類型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => (
        <Tag>{type}</Tag>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => (
        <Switch
          checked={status === 'active'}
          onChange={(checked) => handleUpdateFeatureFlag(record.name, {
            status: checked ? 'active' : 'inactive'
          })}
        />
      ),
    },
    {
      title: '百分比',
      dataIndex: 'percentage',
      key: 'percentage',
      render: (percentage, record) => 
        record.type === 'percentage' ? (
          <InputNumber
            value={percentage}
            min={0}
            max={100}
            formatter={value => `${value}%`}
            parser={value => value!.replace('%', '')}
            onChange={(value) => handleUpdateFeatureFlag(record.name, { percentage: value })}
          />
        ) : '-',
    },
    {
      title: '啟用客戶數',
      dataIndex: 'enabledCustomers',
      key: 'enabledCustomers',
      render: (count) => formatNumber(count || 0),
    },
  ];

  // Progress chart config
  const progressConfig = {
    data: metrics ? [
      { type: '已遷移', value: metrics.migratedCustomers },
      { type: '待處理', value: metrics.pendingCustomers },
      { type: '失敗', value: metrics.failedCustomers },
    ] : [],
    angleField: 'value',
    colorField: 'type',
    radius: 0.8,
    label: {
      type: 'spider',
      content: '{name}\n{percentage}',
    },
    color: ['#52c41a', '#faad14', '#f5222d'],
  };

  // Timeline chart config
  const timelineConfig = {
    data: syncOperations.map((op, index) => ({
      time: formatDateTime(op.createdAt),
      value: index + 1,
      category: op.status,
    })),
    xField: 'time',
    yField: 'value',
    seriesField: 'category',
    smooth: true,
    animation: {
      appear: {
        animation: 'path-in',
        duration: 1000,
      },
    },
  };

  return (
    <PageContainer
      title="遷移監控儀表板"
      extra={[
        <Button
          key="refresh"
          icon={<ReloadOutlined />}
          onClick={() => {
            fetchMetrics();
            fetchOperations();
            fetchConflicts();
          }}
        >
          刷新
        </Button>,
        <Button
          key="sync"
          type={isSyncEnabled ? 'default' : 'primary'}
          icon={isSyncEnabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
          onClick={handleToggleSync}
        >
          {isSyncEnabled ? '暫停同步' : '恢復同步'}
        </Button>,
      ]}
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="總覽" key="overview">
          {/* Metrics Cards */}
          <Row gutter={[16, 16]}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="總客戶數"
                  value={metrics?.totalCustomers || 0}
                  prefix={<TeamOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="已遷移"
                  value={metrics?.migratedCustomers || 0}
                  valueStyle={{ color: '#3f8600' }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="待處理"
                  value={metrics?.pendingCustomers || 0}
                  valueStyle={{ color: '#faad14' }}
                  prefix={<SyncOutlined spin />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="失敗"
                  value={metrics?.failedCustomers || 0}
                  valueStyle={{ color: '#cf1322' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* Progress and Actions */}
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col span={12}>
              <Card title="遷移進度">
                <Progress
                  percent={metrics ? (metrics.migratedCustomers / metrics.totalCustomers) * 100 : 0}
                  status={metrics?.failedCustomers ? 'exception' : 'active'}
                  format={(percent) => `${percent?.toFixed(1)}%`}
                />
                <div style={{ marginTop: 16 }}>
                  <Text>成功率：</Text>
                  <Text strong>{metrics?.successRate.toFixed(1)}%</Text>
                  <Divider type="vertical" />
                  <Text>平均同步時間：</Text>
                  <Text strong>{metrics?.averageSyncTime.toFixed(0)}ms</Text>
                </div>
                {metrics?.estimatedCompletion && (
                  <Alert
                    message={`預計完成時間：${formatDateTime(metrics.estimatedCompletion)}`}
                    type="info"
                    showIcon
                    style={{ marginTop: 16 }}
                  />
                )}
              </Card>
            </Col>
            <Col span={12}>
              <Card title="操作">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button
                    type="primary"
                    icon={<TeamOutlined />}
                    block
                    onClick={() => setIsSelectionModalVisible(true)}
                  >
                    選擇試點客戶
                  </Button>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    block
                    onClick={handleStartMigration}
                    disabled={selectedCustomers.length === 0}
                  >
                    開始遷移 ({selectedCustomers.length} 位客戶)
                  </Button>
                  <Popconfirm
                    title="確定要回滾所有遷移嗎？"
                    onConfirm={handleRollback}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button
                      danger
                      icon={<RollbackOutlined />}
                      block
                    >
                      回滾所有遷移
                    </Button>
                  </Popconfirm>
                </Space>
              </Card>
            </Col>
          </Row>

          {/* Charts */}
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col span={12}>
              <Card title="遷移分布" loading={metricsLoading}>
                <Pie {...progressConfig} />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="同步時間線" loading={operationsLoading}>
                <Line {...timelineConfig} />
              </Card>
            </Col>
          </Row>

          {/* Recent Operations */}
          <Card title="最近同步操作" style={{ marginTop: 16 }}>
            <Table
              columns={operationColumns}
              dataSource={syncOperations}
              rowKey="id"
              loading={operationsLoading}
              pagination={{ pageSize: 10 }}
              scroll={{ x: 1200 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={<Badge count={conflicts.length}>衝突管理</Badge>} key="conflicts">
          <Card
            title="數據衝突"
            extra={
              <Select
                defaultValue="newest_wins"
                style={{ width: 200 }}
                onChange={(value) => {
                  // Update default conflict resolution strategy
                }}
              >
                <Select.Option value="newest_wins">最新數據優先</Select.Option>
                <Select.Option value="legacy_wins">舊系統優先</Select.Option>
                <Select.Option value="new_system_wins">新系統優先</Select.Option>
                <Select.Option value="manual">手動處理</Select.Option>
              </Select>
            }
          >
            {conflicts.length === 0 ? (
              <Alert
                message="無衝突"
                description="目前沒有需要處理的數據衝突"
                type="success"
                showIcon
              />
            ) : (
              <Table
                columns={conflictColumns}
                dataSource={conflicts}
                rowKey="id"
                pagination={{ pageSize: 10 }}
              />
            )}
          </Card>
        </TabPane>

        <TabPane tab="功能標誌" key="features">
          <Card
            title="功能標誌管理"
            extra={
              <Button type="primary" icon={<SettingOutlined />}>
                新增標誌
              </Button>
            }
          >
            <Table
              columns={featureFlagColumns}
              dataSource={featureFlags}
              rowKey="name"
              pagination={false}
            />
          </Card>
        </TabPane>

        <TabPane tab="設定" key="settings">
          <Card title="同步設定">
            <Form layout="vertical">
              <Form.Item label="自動刷新間隔">
                <Select
                  value={refreshInterval}
                  onChange={setRefreshInterval}
                  style={{ width: 200 }}
                >
                  <Select.Option value={5000}>5 秒</Select.Option>
                  <Select.Option value={10000}>10 秒</Select.Option>
                  <Select.Option value={30000}>30 秒</Select.Option>
                  <Select.Option value={60000}>1 分鐘</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item label="衝突解決策略">
                <Select defaultValue="newest_wins" style={{ width: 300 }}>
                  <Select.Option value="newest_wins">最新數據優先</Select.Option>
                  <Select.Option value="legacy_wins">舊系統優先</Select.Option>
                  <Select.Option value="new_system_wins">新系統優先</Select.Option>
                  <Select.Option value="manual">手動處理</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item label="同步批次大小">
                <InputNumber
                  defaultValue={50}
                  min={10}
                  max={500}
                  style={{ width: 200 }}
                />
              </Form.Item>
              <Form.Item label="重試次數">
                <InputNumber
                  defaultValue={3}
                  min={0}
                  max={10}
                  style={{ width: 200 }}
                />
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
      </Tabs>

      {/* Customer Selection Modal */}
      <Modal
        title="選擇試點客戶"
        visible={isSelectionModalVisible}
        onCancel={() => setIsSelectionModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          layout="vertical"
          onFinish={handleSelectCustomers}
        >
          <Form.Item
            label="選擇百分比"
            name="percentage"
            initialValue={10}
            rules={[{ required: true, message: '請輸入百分比' }]}
          >
            <InputNumber
              min={1}
              max={100}
              formatter={value => `${value}%`}
              parser={value => value!.replace('%', '')}
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item
            label="最小訂單數"
            name="minOrderCount"
          >
            <InputNumber
              min={0}
              placeholder="不限制"
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item
            label="地區篩選"
            name="region"
          >
            <Select placeholder="選擇地區">
              <Select.Option value="台北市">台北市</Select.Option>
              <Select.Option value="新北市">新北市</Select.Option>
              <Select.Option value="桃園市">桃園市</Select.Option>
              <Select.Option value="台中市">台中市</Select.Option>
              <Select.Option value="台南市">台南市</Select.Option>
              <Select.Option value="高雄市">高雄市</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="客戶類型"
            name="customerType"
          >
            <Select placeholder="選擇客戶類型">
              <Select.Option value="residential">住宅</Select.Option>
              <Select.Option value="commercial">商業</Select.Option>
              <Select.Option value="restaurant">餐廳</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              選擇客戶
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default MigrationDashboard;