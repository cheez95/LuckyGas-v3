import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Space,
  Alert,
  Card,
  Row,
  Col,
  Typography,
  Divider,
  message,
  Tag,
} from 'antd';
import {
  ExclamationCircleOutlined,
  FireOutlined,
  UserOutlined,
  CarOutlined,
  EnvironmentOutlined,
  PhoneOutlined,
  ClockCircleOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { customerService } from '../../../services/customer.service';
import { driverService } from '../../../services/driver.service';
import { orderService } from '../../../services/order.service';

const { TextArea } = Input;
const { Title, Text } = Typography;

export interface EmergencyDispatchData {
  type: 'gas_leak' | 'urgent_delivery' | 'customer_emergency' | 'driver_emergency';
  customerId?: number;
  orderId?: number;
  driverId?: number;
  priority: 'high' | 'critical';
  description: string;
  contactPhone: string;
  address: string;
  location?: {
    lat: number;
    lng: number;
  };
}

interface EmergencyDispatchModalProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (data: EmergencyDispatchData) => Promise<void>;
  initialData?: Partial<EmergencyDispatchData>;
}

const EmergencyDispatchModal: React.FC<EmergencyDispatchModalProps> = ({
  visible,
  onClose,
  onSubmit,
  initialData,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<any[]>([]);
  const [availableDrivers, setAvailableDrivers] = useState<any[]>([]);
  const [customerDetails, setCustomerDetails] = useState<any>(null);

  useEffect(() => {
    if (visible) {
      fetchCustomers();
      fetchAvailableDrivers();
      if (initialData) {
        form.setFieldsValue(initialData);
      }
    }
  }, [visible, initialData, form]);

  const fetchCustomers = async () => {
    try {
      const response = await customerService.searchCustomers({ limit: 100 });
      setCustomers(response.customers);
    } catch (error) {
      message.error(t('common.error.fetchFailed'));
    }
  };

  const fetchAvailableDrivers = async () => {
    try {
      const drivers = await driverService.getDrivers();
      setAvailableDrivers(drivers.filter((d: any) => d.isAvailable));
    } catch (error) {
      message.error(t('common.error.fetchFailed'));
    }
  };

  const handleCustomerChange = async (customerId: number) => {
    try {
      const customer = await customerService.getCustomer(customerId);
      setCustomerDetails(customer);
      form.setFieldsValue({
        contactPhone: customer.phone,
        address: customer.address,
      });
    } catch (error) {
      message.error(t('common.error.fetchFailed'));
    }
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      await onSubmit({
        ...values,
        location: customerDetails?.location,
      });
      message.success(t('dispatch.emergency.dispatchSuccess'));
      form.resetFields();
      onClose();
    } catch (error) {
      message.error(t('dispatch.emergency.dispatchError'));
    } finally {
      setLoading(false);
    }
  };

  const getEmergencyIcon = (type?: string) => {
    switch (type) {
      case 'gas_leak':
        return <FireOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;
      case 'urgent_delivery':
        return <ClockCircleOutlined style={{ color: '#faad14', fontSize: 20 }} />;
      case 'customer_emergency':
        return <UserOutlined style={{ color: '#ff7a45', fontSize: 20 }} />;
      case 'driver_emergency':
        return <CarOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;
      default:
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;
    }
  };

  return (
    <Modal
      title={
        <Space>
          <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
          <Title level={4} style={{ margin: 0 }}>
            {t('dispatch.emergency.title')}
          </Title>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={600}
      footer={[
        <Button key="cancel" onClick={onClose}>
          {t('common.action.cancel')}
        </Button>,
        <Button
          key="submit"
          type="primary"
          danger
          icon={<SendOutlined />}
          loading={loading}
          onClick={() => form.submit()}
        >
          {t('dispatch.emergency.dispatchNow')}
        </Button>,
      ]}
    >
      <Alert
        message={t('dispatch.emergency.alertMessage')}
        description={t('dispatch.emergency.alertDescription')}
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          priority: 'high',
          type: 'urgent_delivery',
          ...initialData,
        }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="type"
              label={t('dispatch.emergency.type')}
              rules={[{ required: true, message: t('common.validation.required') }]}
            >
              <Select>
                <Select.Option value="gas_leak">
                  <Space>
                    <FireOutlined style={{ color: '#ff4d4f' }} />
                    {t('dispatch.emergency.gasLeak')}
                  </Space>
                </Select.Option>
                <Select.Option value="urgent_delivery">
                  <Space>
                    <ClockCircleOutlined style={{ color: '#faad14' }} />
                    {t('dispatch.emergency.urgentDelivery')}
                  </Space>
                </Select.Option>
                <Select.Option value="customer_emergency">
                  <Space>
                    <UserOutlined style={{ color: '#ff7a45' }} />
                    {t('dispatch.emergency.customerEmergency')}
                  </Space>
                </Select.Option>
                <Select.Option value="driver_emergency">
                  <Space>
                    <CarOutlined style={{ color: '#ff4d4f' }} />
                    {t('dispatch.emergency.driverEmergency')}
                  </Space>
                </Select.Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="priority"
              label={t('dispatch.emergency.priority')}
              rules={[{ required: true, message: t('common.validation.required') }]}
            >
              <Select>
                <Select.Option value="high">
                  <Tag color="orange">{t('dispatch.emergency.priorityHigh')}</Tag>
                </Select.Option>
                <Select.Option value="critical">
                  <Tag color="red">{t('dispatch.emergency.priorityCritical')}</Tag>
                </Select.Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="customerId"
          label={t('dispatch.emergency.customer')}
          rules={[{ required: true, message: t('common.validation.required') }]}
        >
          <Select
            showSearch
            placeholder={t('dispatch.emergency.selectCustomer')}
            onChange={handleCustomerChange}
            filterOption={(input, option) =>
              option?.label?.toLowerCase().includes(input.toLowerCase()) ?? false
            }
            options={customers.map(c => ({
              value: c.id,
              label: `${c.customerCode} - ${c.shortName}`,
            }))}
          />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="contactPhone"
              label={t('dispatch.emergency.contactPhone')}
              rules={[{ required: true, message: t('common.validation.required') }]}
            >
              <Input prefix={<PhoneOutlined />} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="driverId"
              label={t('dispatch.emergency.assignDriver')}
            >
              <Select
                showSearch
                allowClear
                placeholder={t('dispatch.emergency.selectDriver')}
                filterOption={(input, option) =>
                  option?.label?.toLowerCase().includes(input.toLowerCase()) ?? false
                }
                options={availableDrivers.map(d => ({
                  value: d.id,
                  label: `${d.fullName} (${d.vehicleNumber})`,
                }))}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="address"
          label={t('dispatch.emergency.address')}
          rules={[{ required: true, message: t('common.validation.required') }]}
        >
          <Input prefix={<EnvironmentOutlined />} />
        </Form.Item>

        <Form.Item
          name="description"
          label={t('dispatch.emergency.description')}
          rules={[{ required: true, message: t('common.validation.required') }]}
        >
          <TextArea
            rows={4}
            placeholder={t('dispatch.emergency.descriptionPlaceholder')}
            maxLength={500}
            showCount
          />
        </Form.Item>

        {customerDetails && (
          <Card size="small" style={{ marginTop: 16 }}>
            <Title level={5}>{t('dispatch.emergency.customerInfo')}</Title>
            <Row gutter={16}>
              <Col span={12}>
                <Text type="secondary">{t('customer.code')}:</Text>
                <br />
                <Text strong>{customerDetails.customerCode}</Text>
              </Col>
              <Col span={12}>
                <Text type="secondary">{t('customer.area')}:</Text>
                <br />
                <Text strong>{customerDetails.area}</Text>
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            <Text type="secondary">{t('dispatch.emergency.recentOrders')}:</Text>
            <br />
            <Text>{customerDetails.recentOrderCount || 0} {t('common.unit.orders')}</Text>
          </Card>
        )}
      </Form>
    </Modal>
  );
};

export default EmergencyDispatchModal;