import React, { useState, useEffect } from 'react';
import { 
  Modal, 
  Descriptions, 
  Button, 
  Tag, 
  Tabs, 
  Space, 
  Spin, 
  message,
  Card,
  Row,
  Col,
  Statistic,
  Timeline,
  Avatar,
  Divider,
  Tooltip,
  Badge
} from 'antd';
import {
  UserOutlined,
  EditOutlined,
  PhoneOutlined,
  MailOutlined,
  HomeOutlined,
  ShoppingCartOutlined,
  CalendarOutlined,
  DollarOutlined,
  FireOutlined,
  FieldTimeOutlined,
  SafetyOutlined,
  TeamOutlined,
  CarOutlined,
  HistoryOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { customerService } from '../../services/customer.service';
import { Customer } from '../../types/order';

interface CustomerViewModalProps {
  customerId: number | string;
  visible: boolean;
  onClose: () => void;
  onEdit: () => void;
}

const CustomerViewModal: React.FC<CustomerViewModalProps> = ({
  customerId,
  visible,
  onClose,
  onEdit
}) => {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');

  useEffect(() => {
    if (visible && customerId) {
      loadCustomer();
    }
  }, [visible, customerId]);

  const loadCustomer = async () => {
    setLoading(true);
    try {
      const data = await customerService.getCustomer(customerId.toString());
      setCustomer(data);
    } catch (error) {
      message.error('無法載入客戶資料');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const getCylinderDisplay = () => {
    if (!customer) return [];
    const cylinders = [];
    if (customer.cylinders_50kg > 0) cylinders.push({ type: '50kg', count: customer.cylinders_50kg, color: '#fa541c' });
    if (customer.cylinders_20kg > 0) cylinders.push({ type: '20kg', count: customer.cylinders_20kg, color: '#fa8c16' });
    if (customer.cylinders_16kg > 0) cylinders.push({ type: '16kg', count: customer.cylinders_16kg, color: '#faad14' });
    if (customer.cylinders_4kg > 0) cylinders.push({ type: '4kg', count: customer.cylinders_4kg, color: '#fadb14' });
    return cylinders;
  };

  const tabItems = [
    {
      key: 'basic',
      label: (
        <span>
          <InfoCircleOutlined />
          基本資料
        </span>
      ),
      children: customer && (
        <div>
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card size="small" className="info-card">
                <Descriptions column={2} size="small">
                  <Descriptions.Item label={<><UserOutlined /> 客戶編號</>}>
                    <Tag color="blue">{customer.customer_code}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label={<><UserOutlined /> 客戶簡稱</>}>
                    <strong>{customer.short_name}</strong>
                  </Descriptions.Item>
                  <Descriptions.Item label={<><UserOutlined /> 客戶全名</>} span={2}>
                    {customer.full_name || customer.short_name}
                  </Descriptions.Item>
                  <Descriptions.Item label={<><SafetyOutlined /> 客戶類型</>}>
                    <Tag color="purple">{customer.customer_type || '一般'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label={<><CheckCircleOutlined /> 狀態</>}>
                    {customer.is_active ? (
                      <Badge status="success" text="使用中" />
                    ) : (
                      <Badge status="error" text="已停用" />
                    )}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>

          <Divider orientation="left">聯絡資訊</Divider>
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card size="small" className="info-card">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label={<><HomeOutlined /> 地址</>}>
                    {customer.address}
                  </Descriptions.Item>
                  <Descriptions.Item label={<><PhoneOutlined /> 電話</>}>
                    {customer.phone || '未提供'}
                  </Descriptions.Item>
                  <Descriptions.Item label={<><MailOutlined /> 電子郵件</>}>
                    {customer.email || '未提供'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>
        </div>
      )
    },
    {
      key: 'delivery',
      label: (
        <span>
          <CarOutlined />
          配送資訊
        </span>
      ),
      children: customer && (
        <div>
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card size="small" title={<><FieldTimeOutlined /> 配送設定</>} className="info-card">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="配送區域">
                    <Tag color="green">{customer.area || '未指定'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="配送時段">
                    {customer.delivery_time_start && customer.delivery_time_end
                      ? `${customer.delivery_time_start} - ${customer.delivery_time_end}`
                      : '全天'}
                  </Descriptions.Item>
                  <Descriptions.Item label="當天配送">
                    {customer.needs_same_day_delivery ? (
                      <Tag color="orange">需要</Tag>
                    ) : (
                      <Tag>不需要</Tag>
                    )}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" title={<><DollarOutlined /> 付款資訊</>} className="info-card">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="付款方式">
                    <Tag color="cyan">{customer.payment_method || '現金'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="發票抬頭">
                    {customer.invoice_title || '未設定'}
                  </Descriptions.Item>
                  <Descriptions.Item label="訂閱會員">
                    {customer.is_subscription ? (
                      <Tag color="gold">是</Tag>
                    ) : (
                      <Tag>否</Tag>
                    )}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>
        </div>
      )
    },
    {
      key: 'cylinders',
      label: (
        <span>
          <FireOutlined />
          瓦斯配置
        </span>
      ),
      children: customer && (
        <div>
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card size="small" title="瓦斯桶配置" className="info-card">
                <Row gutter={[16, 16]}>
                  {getCylinderDisplay().map((cylinder, index) => (
                    <Col span={6} key={index}>
                      <Card size="small" style={{ textAlign: 'center', borderColor: cylinder.color }}>
                        <Statistic
                          title={cylinder.type}
                          value={cylinder.count}
                          suffix="個"
                          valueStyle={{ color: cylinder.color }}
                        />
                      </Card>
                    </Col>
                  ))}
                  {getCylinderDisplay().length === 0 && (
                    <Col span={24}>
                      <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                        暫無瓦斯桶配置
                      </div>
                    </Col>
                  )}
                </Row>
              </Card>
            </Col>
            <Col span={24}>
              <Card size="small" title="使用量資訊" className="info-card">
                <Descriptions column={3} size="small">
                  <Descriptions.Item label="平均日使用量">
                    {customer.avg_daily_usage ? `${customer.avg_daily_usage} kg/日` : '未設定'}
                  </Descriptions.Item>
                  <Descriptions.Item label="最大週期">
                    {customer.max_cycle_days ? `${customer.max_cycle_days} 天` : '未設定'}
                  </Descriptions.Item>
                  <Descriptions.Item label="可延後天數">
                    {customer.can_delay_days ? `${customer.can_delay_days} 天` : '0 天'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>
        </div>
      )
    },
    {
      key: 'history',
      label: (
        <span>
          <HistoryOutlined />
          歷史記錄
        </span>
      ),
      children: (
        <div style={{ padding: '20px 0' }}>
          <Timeline>
            <Timeline.Item color="green" dot={<CheckCircleOutlined />}>
              <p>客戶建立</p>
              <p style={{ color: '#999', fontSize: 12 }}>2024-01-15 09:30</p>
            </Timeline.Item>
            <Timeline.Item color="blue" dot={<ShoppingCartOutlined />}>
              <p>首次訂購</p>
              <p style={{ color: '#999', fontSize: 12 }}>2024-01-20 14:20</p>
            </Timeline.Item>
            <Timeline.Item color="orange" dot={<ClockCircleOutlined />}>
              <p>最近配送</p>
              <p style={{ color: '#999', fontSize: 12 }}>2024-03-10 10:15</p>
            </Timeline.Item>
          </Timeline>
        </div>
      )
    }
  ];

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Space>
            <Avatar 
              size="large" 
              icon={<UserOutlined />} 
              style={{ backgroundColor: '#1890ff' }}
            />
            <div>
              <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                {customer?.short_name || '客戶詳情'}
              </div>
              <div style={{ fontSize: 12, color: '#999' }}>
                {customer?.customer_code}
              </div>
            </div>
          </Space>
          <Space>
            <Tooltip title="編輯客戶">
              <Button 
                type="primary" 
                icon={<EditOutlined />}
                onClick={() => {
                  onEdit();
                  onClose();
                }}
              >
                編輯
              </Button>
            </Tooltip>
          </Space>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="close" onClick={onClose}>
          關閉
        </Button>
      ]}
      bodyStyle={{ padding: '0 24px' }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Spin size="large" tip="載入中..." />
        </div>
      ) : (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          style={{ marginTop: 20 }}
        />
      )}
    </Modal>
  );
};

export default CustomerViewModal;

<style>
{`
.info-card {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.info-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.09);
  transition: all 0.3s;
}

.ant-descriptions-item-label {
  font-weight: 500;
  color: #595959;
}

.ant-tabs-tab {
  font-size: 14px;
}

.ant-modal-header {
  border-bottom: 1px solid #f0f0f0;
  padding: 16px 24px;
}

.ant-modal-body {
  max-height: 70vh;
  overflow-y: auto;
}
`}
</style>