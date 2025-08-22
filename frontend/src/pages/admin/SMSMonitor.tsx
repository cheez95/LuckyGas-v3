import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Statistic,
  Row,
  Col,
  DatePicker,
  Select,
  Input,
  message,
  Modal,
  Descriptions,
  Progress,
  Tooltip,
  Badge,
  Alert,
  Tabs,
  Form,
  InputNumber,
  Switch,
} from 'antd';
import {
  MessageOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  SendOutlined,
  DollarOutlined,
  PercentageOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { Line, Pie } from '@ant-design/charts';
import api from '../../services/api';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TabPane } = Tabs;

interface SMSLog {
  id: string;
  recipient: string;
  message: string;
  message_type: string;
  provider: string;
  status: string;
  sent_at: string;
  delivered_at?: string;
  failed_at?: string;
  error_message?: string;
  cost: number;
  segments: number;
  created_at: string;
}

interface SMSStats {
  total_sent: number;
  total_delivered: number;
  total_failed: number;
  total_pending: number;
  total_cost: number;
  success_rate: number;
  provider_stats: {
    [key: string]: {
      sent: number;
      delivered: number;
      failed: number;
      cost: number;
    };
  };
}

interface SMSTemplate {
  id: string;
  code: string;
  name: string;
  content: string;
  is_active: boolean;
  sent_count: number;
  delivered_count: number;
  effectiveness_score: number;
  variant: string;
}

interface ProviderConfig {
  provider: string;
  is_active: boolean;
  priority: number;
  rate_limit: number;
  success_rate: number;
  total_sent: number;
  total_failed: number;
}

const SMSMonitor: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [smsLogs, setSmsLogs] = useState<SMSLog[]>([]);
  const [stats, setStats] = useState<SMSStats | null>(null);
  const [templates, setTemplates] = useState<SMSTemplate[]>([]);
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedLog, setSelectedLog] = useState<SMSLog | null>(null);
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(7, 'days'),
    dayjs(),
  ]);
  const [filters, setFilters] = useState({
    status: '',
    provider: '',
    message_type: '',
    search: '',
  });
  const [activeTab, setActiveTab] = useState('logs');
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = window.setInterval(fetchData, 30000);
    setRefreshInterval(interval);

    return () => {
      if (interval) window.clearInterval(interval);
    };
  }, [dateRange, filters]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = {
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
        ...filters,
      };

      const [logsRes, statsRes, templatesRes, providersRes] = await Promise.all([
        api.get('/sms/logs', { params }),
        api.get('/sms/stats', { params }),
        api.get('/sms/templates'),
        api.get('/sms/providers'),
      ]);

      setSmsLogs(logsRes.data);
      setStats(statsRes.data);
      setTemplates(templatesRes.data);
      setProviders(providersRes.data);
    } catch (error) {
      message.error('載入簡訊資料失敗');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async (record: SMSLog) => {
    Modal.confirm({
      title: '重新發送簡訊',
      content: `確定要重新發送簡訊給 ${record.recipient} 嗎？`,
      okText: '確定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.post(`/sms/resend/${record.id}`);
          message.success('簡訊已重新發送');
          fetchData();
        } catch (error) {
          message.error('重新發送失敗');
        }
      },
    });
  };

  const getStatusTag = (status: string) => {
    const statusConfig = {
      pending: { color: 'processing', text: '發送中', icon: <SyncOutlined spin /> },
      sent: { color: 'processing', text: '已發送', icon: <SendOutlined /> },
      delivered: { color: 'success', text: '已送達', icon: <CheckCircleOutlined /> },
      failed: { color: 'error', text: '發送失敗', icon: <CloseCircleOutlined /> },
    };

    const config = statusConfig[status] || { color: 'default', text: status, icon: null };

    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  const columns: ColumnsType<SMSLog> = [
    {
      title: '收件人',
      dataIndex: 'recipient',
      key: 'recipient',
      width: 120,
    },
    {
      title: '訊息類型',
      dataIndex: 'message_type',
      key: 'message_type',
      width: 120,
      render: (type: string) => {
        const typeMap = {
          order_confirmation: '訂單確認',
          out_for_delivery: '配送中',
          delivery_completed: '配送完成',
          payment_reminder: '付款提醒',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '供應商',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
      render: (provider: string) => (
        <Tag>{provider.toUpperCase()}</Tag>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '發送時間',
      dataIndex: 'sent_at',
      key: 'sent_at',
      width: 160,
      render: (time: string) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '送達時間',
      dataIndex: 'delivered_at',
      key: 'delivered_at',
      width: 160,
      render: (time: string) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '費用',
      dataIndex: 'cost',
      key: 'cost',
      width: 80,
      render: (cost: number) => `$${cost.toFixed(2)}`,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            onClick={() => {
              setSelectedLog(record);
              setDetailsVisible(true);
            }}
          >
            詳情
          </Button>
          {record.status === 'failed' && (
            <Button
              size="small"
              danger
              onClick={() => handleResend(record)}
            >
              重發
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const renderStats = () => {
    if (!stats) return null;

    const deliveryRateData = [
      { type: '已送達', value: stats.total_delivered },
      { type: '發送失敗', value: stats.total_failed },
      { type: '發送中', value: stats.total_pending },
    ];

    const providerData = Object.entries(stats.provider_stats).map(([provider, data]) => ({
      provider: provider.toUpperCase(),
      sent: data.sent,
      delivered: data.delivered,
      failed: data.failed,
    }));

    return (
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title="總發送數"
              value={stats.total_sent}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功率"
              value={stats.success_rate}
              precision={2}
              suffix="%"
              prefix={<PercentageOutlined />}
              valueStyle={{ color: stats.success_rate > 95 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="總費用"
              value={stats.total_cost}
              precision={2}
              prefix="NT$"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失敗數"
              value={stats.total_failed}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="送達率分析">
            <Pie
              data={deliveryRateData}
              angleField="value"
              colorField="type"
              radius={0.8}
              label={{
                type: 'outer',
                content: '{name} {percentage}',
              }}
              interactions={[{ type: 'element-active' }]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="供應商效能">
            <Table
              dataSource={providerData}
              columns={[
                { title: '供應商', dataIndex: 'provider', key: 'provider' },
                { title: '發送', dataIndex: 'sent', key: 'sent' },
                { title: '送達', dataIndex: 'delivered', key: 'delivered' },
                {
                  title: '成功率',
                  key: 'rate',
                  render: (_, record) => {
                    const rate = record.sent > 0 ? (record.delivered / record.sent) * 100 : 0;
                    return <Progress percent={rate} size="small" />;
                  },
                },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    );
  };

  const renderTemplates = () => (
    <Table
      dataSource={templates}
      columns={[
        { title: '代碼', dataIndex: 'code', key: 'code' },
        { title: '名稱', dataIndex: 'name', key: 'name' },
        {
          title: '內容',
          dataIndex: 'content',
          key: 'content',
          ellipsis: true,
          render: (content: string) => (
            <Tooltip title={content}>
              <span>{content}</span>
            </Tooltip>
          ),
        },
        {
          title: '變體',
          dataIndex: 'variant',
          key: 'variant',
          render: (variant: string) => <Tag>{variant}</Tag>,
        },
        { title: '發送數', dataIndex: 'sent_count', key: 'sent_count' },
        { title: '送達數', dataIndex: 'delivered_count', key: 'delivered_count' },
        {
          title: '效果分數',
          dataIndex: 'effectiveness_score',
          key: 'effectiveness_score',
          render: (score: number) => (
            <Progress percent={score} size="small" />
          ),
        },
        {
          title: '狀態',
          dataIndex: 'is_active',
          key: 'is_active',
          render: (active: boolean) => (
            <Badge status={active ? 'success' : 'default'} text={active ? '啟用' : '停用'} />
          ),
        },
      ]}
      rowKey="id"
    />
  );

  const renderProviders = () => (
    <Row gutter={[16, 16]}>
      {providers.map((provider) => (
        <Col span={12} key={provider.provider}>
          <Card
            title={provider.provider.toUpperCase()}
            extra={
              <Badge
                status={provider.is_active ? 'success' : 'error'}
                text={provider.is_active ? '啟用' : '停用'}
              />
            }
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="優先級">{provider.priority}</Descriptions.Item>
              <Descriptions.Item label="速率限制">{provider.rate_limit}/分鐘</Descriptions.Item>
              <Descriptions.Item label="總發送">{provider.total_sent}</Descriptions.Item>
              <Descriptions.Item label="失敗數">{provider.total_failed}</Descriptions.Item>
              <Descriptions.Item label="成功率" span={2}>
                <Progress percent={provider.success_rate * 100} />
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      ))}
    </Row>
  );

  return (
    <div>
      <Card
        title="簡訊監控中心"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchData}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<SettingOutlined />}
              onClick={() => message.info('設定功能開發中')}
            >
              設定
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Row gutter={16} align="middle">
            <Col span={6}>
              <RangePicker
                value={dateRange}
                onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="狀態"
                style={{ width: '100%' }}
                allowClear
                value={filters.status}
                onChange={(value) => setFilters({ ...filters, status: value || '' })}
              >
                <Option value="pending">發送中</Option>
                <Option value="sent">已發送</Option>
                <Option value="delivered">已送達</Option>
                <Option value="failed">發送失敗</Option>
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="供應商"
                style={{ width: '100%' }}
                allowClear
                value={filters.provider}
                onChange={(value) => setFilters({ ...filters, provider: value || '' })}
              >
                <Option value="twilio">Twilio</Option>
                <Option value="chunghwa">中華電信</Option>
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="訊息類型"
                style={{ width: '100%' }}
                allowClear
                value={filters.message_type}
                onChange={(value) => setFilters({ ...filters, message_type: value || '' })}
              >
                <Option value="order_confirmation">訂單確認</Option>
                <Option value="out_for_delivery">配送中</Option>
                <Option value="delivery_completed">配送完成</Option>
                <Option value="payment_reminder">付款提醒</Option>
              </Select>
            </Col>
            <Col span={6}>
              <Input.Search
                placeholder="搜尋電話號碼"
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                onSearch={fetchData}
              />
            </Col>
          </Row>

          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane tab="發送記錄" key="logs">
              <Table
                columns={columns}
                dataSource={smsLogs}
                loading={loading}
                rowKey="id"
                scroll={{ x: 1200 }}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 筆`,
                }}
              />
            </TabPane>
            <TabPane tab="統計分析" key="stats">
              {renderStats()}
            </TabPane>
            <TabPane tab="訊息模板" key="templates">
              {renderTemplates()}
            </TabPane>
            <TabPane tab="供應商狀態" key="providers">
              {renderProviders()}
            </TabPane>
          </Tabs>
        </Space>
      </Card>

      <Modal
        title="簡訊詳情"
        visible={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={null}
        width={600}
      >
        {selectedLog && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="收件人">{selectedLog.recipient}</Descriptions.Item>
            <Descriptions.Item label="訊息內容">{selectedLog.message}</Descriptions.Item>
            <Descriptions.Item label="訊息類型">{selectedLog.message_type}</Descriptions.Item>
            <Descriptions.Item label="供應商">{selectedLog.provider}</Descriptions.Item>
            <Descriptions.Item label="狀態">{getStatusTag(selectedLog.status)}</Descriptions.Item>
            <Descriptions.Item label="段數">{selectedLog.segments}</Descriptions.Item>
            <Descriptions.Item label="費用">NT${selectedLog.cost}</Descriptions.Item>
            <Descriptions.Item label="建立時間">
              {dayjs(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            {selectedLog.sent_at && (
              <Descriptions.Item label="發送時間">
                {dayjs(selectedLog.sent_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            )}
            {selectedLog.delivered_at && (
              <Descriptions.Item label="送達時間">
                {dayjs(selectedLog.delivered_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            )}
            {selectedLog.error_message && (
              <Descriptions.Item label="錯誤訊息">
                <Alert message={selectedLog.error_message} type="error" />
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default SMSMonitor;