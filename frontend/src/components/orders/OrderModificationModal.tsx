import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, DatePicker, Row, Col, Space, Button, Alert, Timeline, Card, Divider, Tag, message, InputNumber } from 'antd';
import { ExclamationCircleOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import api from '../../services/api';

interface OrderModificationModalProps {
  visible: boolean;
  order: any;
  onClose: () => void;
  onSuccess: () => void;
}

interface ModificationHistory {
  id: string;
  timestamp: string;
  field: string;
  oldValue: any;
  newValue: any;
  modifiedBy: string;
  reason?: string;
}

const OrderModificationModal: React.FC<OrderModificationModalProps> = ({
  visible,
  order,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [modificationHistory, setModificationHistory] = useState<ModificationHistory[]>([]);
  const [canModify, setCanModify] = useState(true);
  const [modificationReasons, setModificationReasons] = useState<string[]>([]);

  // Define which fields can be modified based on order status
  const getModifiableFields = (status: string) => {
    const fields: Record<string, string[]> = {
      pending: ['deliveryDate', 'priority', 'quantity', 'paymentMethod', 'deliveryNotes'],
      confirmed: ['deliveryDate', 'priority', 'deliveryNotes'],
      assigned: ['priority', 'deliveryNotes'],
      in_delivery: ['deliveryNotes'],
      delivered: [],
      cancelled: [],
    };
    return fields[status] || [];
  };

  // Modification rules based on status
  const getModificationRules = (status: string) => {
    const rules: Record<string, any> = {
      pending: {
        canCancel: true,
        canChangeQuantity: true,
        canChangeDate: true,
        requiresApproval: false,
      },
      confirmed: {
        canCancel: true,
        canChangeQuantity: false,
        canChangeDate: true,
        requiresApproval: true,
      },
      assigned: {
        canCancel: false,
        canChangeQuantity: false,
        canChangeDate: false,
        requiresApproval: true,
      },
      in_delivery: {
        canCancel: false,
        canChangeQuantity: false,
        canChangeDate: false,
        requiresApproval: true,
      },
      delivered: {
        canCancel: false,
        canChangeQuantity: false,
        canChangeDate: false,
        requiresApproval: false,
      },
    };
    return rules[status] || {};
  };

  useEffect(() => {
    if (order && visible) {
      // Load modification history
      fetchModificationHistory(order.id);
      
      // Set form values
      form.setFieldsValue({
        ...order,
        deliveryDate: order.deliveryDate ? dayjs(order.deliveryDate) : null,
        orderDate: dayjs(order.orderDate),
      });

      // Check if order can be modified
      const modifiableFields = getModifiableFields(order.status);
      setCanModify(modifiableFields.length > 0);
    }
  }, [order, visible]);

  const fetchModificationHistory = async (orderId: string) => {
    try {
      const response = await api.get(`/orders/${orderId}/modifications`);
      setModificationHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch modification history:', error);
    }
  };

  const handleSubmit = async (values: any) => {
    if (!order) return;

    const modifiableFields = getModifiableFields(order.status);
    const changes: any = {};
    const changeReasons: any = {};

    // Detect changes
    modifiableFields.forEach(field => {
      const oldValue = order[field];
      const newValue = values[field];
      
      // Handle date comparison
      if (field.includes('Date')) {
        const oldDate = oldValue ? dayjs(oldValue).format('YYYY-MM-DD') : null;
        const newDate = newValue ? newValue.format('YYYY-MM-DD') : null;
        if (oldDate !== newDate) {
          changes[field] = newValue;
          changeReasons[field] = values[`${field}_reason`];
        }
      } else if (oldValue !== newValue) {
        changes[field] = newValue;
        changeReasons[field] = values[`${field}_reason`];
      }
    });

    if (Object.keys(changes).length === 0) {
      message.warning(t('orders.noChangesDetected'));
      return;
    }

    // Validate required reasons for certain changes
    const rules = getModificationRules(order.status);
    if (rules.requiresApproval) {
      for (const field of Object.keys(changes)) {
        if (!changeReasons[field]) {
          message.error(t('orders.modificationReasonRequired'));
          return;
        }
      }
    }

    setLoading(true);
    try {
      const payload = {
        orderId: order.id,
        modifications: changes,
        reasons: changeReasons,
        modifiedAt: new Date().toISOString(),
        requiresApproval: rules.requiresApproval,
      };

      await api.put(`/orders/${order.id}/modify`, payload);
      message.success(t('orders.modificationSuccess'));
      onSuccess();
      onClose();
    } catch (error: any) {
      if (error.response?.status === 422) {
        message.error(error.response.data.detail || t('orders.modificationNotAllowed'));
      } else {
        message.error(t('orders.modificationError'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    const rules = getModificationRules(order.status);
    if (!rules.canCancel) {
      message.error(t('orders.cannotCancelOrder'));
      return;
    }

    Modal.confirm({
      title: t('orders.cancelOrderConfirm'),
      content: t('orders.cancelOrderWarning'),
      okText: t('common.confirm'),
      cancelText: t('common.cancel'),
      onOk: async () => {
        try {
          await api.put(`/orders/${order.id}/cancel`, {
            reason: form.getFieldValue('cancellationReason'),
          });
          message.success(t('orders.orderCancelled'));
          onSuccess();
          onClose();
        } catch (error) {
          message.error(t('orders.cancelError'));
        }
      },
    });
  };

  const renderModificationHistory = () => {
    if (modificationHistory.length === 0) return null;

    return (
      <Card title={t('orders.modificationHistory')} style={{ marginTop: 16 }}>
        <Timeline>
          {modificationHistory.map((mod) => (
            <Timeline.Item
              key={mod.id}
              color="blue"
              dot={<ClockCircleOutlined />}
            >
              <Space direction="vertical" size="small">
                <div>
                  <strong>{t(`orders.field.${mod.field}`)}</strong>
                  {': '}
                  <Tag>{mod.oldValue}</Tag>
                  {' → '}
                  <Tag color="blue">{mod.newValue}</Tag>
                </div>
                {mod.reason && (
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {t('orders.reason')}: {mod.reason}
                  </div>
                )}
                <div style={{ fontSize: '12px', color: '#999' }}>
                  {dayjs(mod.timestamp).format('YYYY/MM/DD HH:mm')} - {mod.modifiedBy}
                </div>
              </Space>
            </Timeline.Item>
          ))}
        </Timeline>
      </Card>
    );
  };

  if (!order) return null;

  const modifiableFields = getModifiableFields(order.status);
  const rules = getModificationRules(order.status);

  return (
    <Modal
      title={t('orders.modifyOrder')}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
    >
      {!canModify && (
        <Alert
          message={t('orders.cannotModifyOrder')}
          description={t('orders.orderStatusRestriction')}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        disabled={!canModify}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label={t('orders.orderNumber')}>
              <Input value={order.orderNumber} disabled />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label={t('orders.status')}>
              <Select value={order.status} disabled>
                <Select.Option value={order.status}>
                  {t(`orders.status.${order.status}`)}
                </Select.Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Divider />

        {modifiableFields.includes('deliveryDate') && (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="deliveryDate"
                  label={t('orders.deliveryDate')}
                  rules={[{ required: false }]}
                >
                  <DatePicker
                    style={{ width: '100%' }}
                    disabledDate={(current) => {
                      // Cannot select past dates
                      return current && current < dayjs().startOf('day');
                    }}
                  />
                </Form.Item>
              </Col>
              {rules.requiresApproval && (
                <Col span={12}>
                  <Form.Item
                    name="deliveryDate_reason"
                    label={t('orders.modificationReason')}
                  >
                    <Input placeholder={t('orders.enterReason')} />
                  </Form.Item>
                </Col>
              )}
            </Row>
          </>
        )}

        {modifiableFields.includes('priority') && (
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="priority"
                label={t('orders.priority')}
              >
                <Select>
                  <Select.Option value="normal">{t('orders.priority.normal')}</Select.Option>
                  <Select.Option value="urgent">{t('orders.priority.urgent')}</Select.Option>
                  <Select.Option value="scheduled">{t('orders.priority.scheduled')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            {rules.requiresApproval && (
              <Col span={12}>
                <Form.Item
                  name="priority_reason"
                  label={t('orders.modificationReason')}
                >
                  <Input placeholder={t('orders.enterReason')} />
                </Form.Item>
              </Col>
            )}
          </Row>
        )}

        {modifiableFields.includes('quantity') && order.products && (
          <Card title={t('orders.products')} style={{ marginBottom: 16 }}>
            {order.products.map((product: any, index: number) => (
              <Row gutter={16} key={index}>
                <Col span={8}>
                  <Form.Item label={t('orders.cylinderType')}>
                    <Input value={product.cylinderType} disabled />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name={['products', index, 'quantity']}
                    label={t('orders.quantity')}
                    initialValue={product.quantity}
                  >
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name={['products', index, 'quantity_reason']}
                    label={t('orders.modificationReason')}
                  >
                    <Input placeholder={t('orders.enterReason')} />
                  </Form.Item>
                </Col>
              </Row>
            ))}
          </Card>
        )}

        {modifiableFields.includes('deliveryNotes') && (
          <Form.Item
            name="deliveryNotes"
            label={t('orders.deliveryNotes')}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
        )}

        {rules.canCancel && (
          <Card title={t('orders.cancelOrder')} style={{ marginBottom: 16 }}>
            <Form.Item
              name="cancellationReason"
              label={t('orders.cancellationReason')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Input.TextArea rows={2} placeholder={t('orders.enterCancellationReason')} />
            </Form.Item>
            <Button danger onClick={handleCancel}>
              {t('orders.cancelOrder')}
            </Button>
          </Card>
        )}

        <Form.Item>
          <Space>
            {canModify && (
              <Button type="primary" htmlType="submit" loading={loading}>
                {t('orders.saveModifications')}
              </Button>
            )}
            <Button onClick={onClose}>
              {t('common.close')}
            </Button>
          </Space>
        </Form.Item>
      </Form>

      {renderModificationHistory()}
    </Modal>
  );
};

export default OrderModificationModal;