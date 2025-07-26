import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Button, Select, Space, Table, Tag, message, Switch, InputNumber, Checkbox, Popconfirm, Card, Row, Col, Statistic } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined, CalendarOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Option } = Select;

interface ProductItem {
  gas_product_id: number;
  quantity: number;
  unit_price?: number;
  discount_percentage?: number;
  is_exchange?: boolean;
  empty_received?: number;
}

interface OrderTemplate {
  id: number;
  template_name: string;
  template_code: string;
  description?: string;
  customer_id: number;
  customer_name?: string;
  products: ProductItem[];
  product_details?: any[];
  delivery_notes?: string;
  priority: string;
  payment_method: string;
  is_recurring: boolean;
  recurrence_pattern?: string;
  recurrence_interval?: number;
  recurrence_days?: number[];
  next_scheduled_date?: string;
  times_used: number;
  last_used_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface OrderTemplateManagerProps {
  customerId?: number;
  onTemplateSelect?: (template: OrderTemplate) => void;
}

const OrderTemplateManager: React.FC<OrderTemplateManagerProps> = ({
  customerId,
  onTemplateSelect
}) => {
  const { t } = useTranslation();
  const [templates, setTemplates] = useState<OrderTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<OrderTemplate | null>(null);
  const [form] = Form.useForm();
  const [products, setProducts] = useState<any[]>([]);

  useEffect(() => {
    fetchTemplates();
    fetchProducts();
  }, [customerId]);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const params = customerId ? { customer_id: customerId } : {};
      const response = await api.get('/order-templates', { params });
      setTemplates(response.data.templates || response.data);
    } catch (error) {
      message.error(t('orders.templates.fetchError'));
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to fetch products:', error);
    }
  };

  const handleAdd = () => {
    setEditingTemplate(null);
    form.resetFields();
    form.setFieldsValue({
      priority: 'normal',
      payment_method: 'cash',
      is_recurring: false,
      is_active: true,
      products: [{ gas_product_id: products[0]?.id, quantity: 1 }]
    });
    setIsModalVisible(true);
  };

  const handleEdit = (template: OrderTemplate) => {
    setEditingTemplate(template);
    form.setFieldsValue({
      ...template,
      recurrence_days: template.recurrence_days || []
    });
    setIsModalVisible(true);
  };

  const handleDelete = async (templateId: number) => {
    try {
      await api.delete(`/order-templates/${templateId}`);
      message.success(t('orders.templates.deleteSuccess'));
      fetchTemplates();
    } catch (error) {
      message.error(t('orders.templates.deleteError'));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // Prepare data
      const data = {
        ...values,
        customer_id: customerId || values.customer_id
      };
      
      if (editingTemplate) {
        await api.put(`/order-templates/${editingTemplate.id}`, data);
        message.success(t('orders.templates.updateSuccess'));
      } else {
        await api.post('/order-templates', data);
        message.success(t('orders.templates.createSuccess'));
      }
      
      setIsModalVisible(false);
      fetchTemplates();
    } catch (error) {
      message.error(t('orders.templates.saveError'));
    }
  };

  const handleCreateOrder = async (template: OrderTemplate) => {
    try {
      await api.post('/order-templates/create-order', {
        template_id: template.id
      });
      message.success(t('orders.templates.orderCreated'));
      
      if (onTemplateSelect) {
        onTemplateSelect(template);
      }
    } catch (error) {
      message.error(t('orders.templates.orderCreateError'));
    }
  };

  const columns: ColumnsType<OrderTemplate> = [
    {
      title: t('orders.templates.templateName'),
      dataIndex: 'template_name',
      key: 'template_name',
    },
    {
      title: t('orders.templates.templateCode'),
      dataIndex: 'template_code',
      key: 'template_code',
    },
    {
      title: t('orders.templates.products'),
      key: 'products',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.product_details?.map((product, index) => (
            <Tag key={index}>{product.product_name} x {product.quantity}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('orders.templates.type'),
      key: 'type',
      render: (_, record) => (
        <Space>
          {record.is_recurring ? (
            <Tag color="blue" icon={<CalendarOutlined />}>
              {t(`orders.templates.recurrence.${record.recurrence_pattern}`)}
            </Tag>
          ) : (
            <Tag>{t('orders.templates.oneTime')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('orders.templates.usage'),
      dataIndex: 'times_used',
      key: 'times_used',
      render: (times_used, record) => (
        <Space direction="vertical" size={0}>
          <span>{t('orders.templates.timesUsed', { count: times_used })}</span>
          {record.last_used_at && (
            <span style={{ fontSize: '12px', color: '#999' }}>
              {t('orders.templates.lastUsed')}: {dayjs(record.last_used_at).format('YYYY-MM-DD')}
            </span>
          )}
        </Space>
      ),
    },
    {
      title: t('orders.templates.status'),
      key: 'status',
      render: (_, record) => (
        <Tag color={record.is_active ? 'green' : 'red'}>
          {record.is_active ? t('common.active') : t('common.inactive')}
        </Tag>
      ),
    },
    {
      title: t('common.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleCreateOrder(record)}
          >
            {t('orders.templates.createOrder')}
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('common.edit')}
          </Button>
          <Popconfirm
            title={t('orders.templates.deleteConfirm')}
            onConfirm={() => handleDelete(record.id)}
            okText={t('common.yes')}
            cancelText={t('common.no')}
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              {t('common.delete')}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const weekDays = [
    { value: 1, label: t('common.weekdays.monday') },
    { value: 2, label: t('common.weekdays.tuesday') },
    { value: 3, label: t('common.weekdays.wednesday') },
    { value: 4, label: t('common.weekdays.thursday') },
    { value: 5, label: t('common.weekdays.friday') },
    { value: 6, label: t('common.weekdays.saturday') },
    { value: 7, label: t('common.weekdays.sunday') },
  ];

  return (
    <div className="order-template-manager">
      <Card
        title={t('orders.templates.title')}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            {t('orders.templates.create')}
          </Button>
        }
      >
        {!customerId && (
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('orders.templates.totalTemplates')}
                  value={templates.length}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('orders.templates.activeTemplates')}
                  value={templates.filter(t => t.is_active).length}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('orders.templates.recurringTemplates')}
                  value={templates.filter(t => t.is_recurring).length}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('orders.templates.totalUsage')}
                  value={templates.reduce((sum, t) => sum + t.times_used, 0)}
                />
              </Card>
            </Col>
          </Row>
        )}

        <Table
          columns={columns}
          dataSource={templates}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => t('common.totalItems', { total }),
          }}
        />
      </Card>

      <Modal
        title={editingTemplate ? t('orders.templates.edit') : t('orders.templates.create')}
        visible={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => setIsModalVisible(false)}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="template_name"
                label={t('orders.templates.templateName')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="template_code"
                label={t('orders.templates.templateCode')}
              >
                <Input placeholder={t('orders.templates.autoGenerate')} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label={t('orders.templates.description')}
          >
            <TextArea rows={2} />
          </Form.Item>

          {!customerId && (
            <Form.Item
              name="customer_id"
              label={t('orders.customer')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Select
                showSearch
                placeholder={t('orders.selectCustomer')}
                optionFilterProp="children"
              >
                {/* Customer options would be loaded here */}
              </Select>
            </Form.Item>
          )}

          <Form.List name="products">
            {(fields, { add, remove }) => (
              <>
                <label>{t('orders.products')}</label>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                    <Form.Item
                      {...restField}
                      name={[name, 'gas_product_id']}
                      rules={[{ required: true, message: t('validation.required') }]}
                    >
                      <Select style={{ width: 200 }} placeholder={t('orders.selectProduct')}>
                        {products.map(product => (
                          <Option key={product.id} value={product.id}>
                            {product.display_name}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'quantity']}
                      rules={[{ required: true, message: t('validation.required') }]}
                    >
                      <InputNumber min={1} placeholder={t('orders.quantity')} />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'unit_price']}
                    >
                      <InputNumber min={0} placeholder={t('orders.unitPrice')} />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'discount_percentage']}
                    >
                      <InputNumber min={0} max={100} placeholder={t('orders.discount')} />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'is_exchange']}
                      valuePropName="checked"
                    >
                      <Checkbox>{t('orders.isExchange')}</Checkbox>
                    </Form.Item>
                    <MinusCircleOutlined onClick={() => remove(name)} />
                  </Space>
                ))}
                <Form.Item>
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    {t('orders.addProduct')}
                  </Button>
                </Form.Item>
              </>
            )}
          </Form.List>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="priority"
                label={t('orders.priority')}
              >
                <Select>
                  <Option value="normal">{t('orders.priorityNormal')}</Option>
                  <Option value="urgent">{t('orders.priorityUrgent')}</Option>
                  <Option value="scheduled">{t('orders.priorityScheduled')}</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="payment_method"
                label={t('orders.paymentMethod')}
              >
                <Select>
                  <Option value="cash">{t('orders.paymentCash')}</Option>
                  <Option value="transfer">{t('orders.paymentTransfer')}</Option>
                  <Option value="credit">{t('orders.paymentCredit')}</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="is_active"
                label={t('orders.templates.isActive')}
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="delivery_notes"
            label={t('orders.deliveryNotes')}
          >
            <TextArea rows={2} />
          </Form.Item>

          <Form.Item
            name="is_recurring"
            label={t('orders.templates.isRecurring')}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.is_recurring !== currentValues.is_recurring}
          >
            {({ getFieldValue }) =>
              getFieldValue('is_recurring') ? (
                <>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="recurrence_pattern"
                        label={t('orders.templates.recurrencePattern')}
                        rules={[{ required: true, message: t('validation.required') }]}
                      >
                        <Select>
                          <Option value="daily">{t('orders.templates.recurrence.daily')}</Option>
                          <Option value="weekly">{t('orders.templates.recurrence.weekly')}</Option>
                          <Option value="monthly">{t('orders.templates.recurrence.monthly')}</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="recurrence_interval"
                        label={t('orders.templates.recurrenceInterval')}
                        rules={[{ required: true, message: t('validation.required') }]}
                      >
                        <InputNumber min={1} max={365} />
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Form.Item
                    noStyle
                    shouldUpdate={(prevValues, currentValues) => prevValues.recurrence_pattern !== currentValues.recurrence_pattern}
                  >
                    {({ getFieldValue }) =>
                      getFieldValue('recurrence_pattern') === 'weekly' ? (
                        <Form.Item
                          name="recurrence_days"
                          label={t('orders.templates.recurrenceDays')}
                        >
                          <Checkbox.Group options={weekDays} />
                        </Form.Item>
                      ) : null
                    }
                  </Form.Item>
                </>
              ) : null
            }
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default OrderTemplateManager;