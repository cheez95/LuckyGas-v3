import React, { useState } from 'react';
import { Space, Dropdown, Button, Modal, Form, Select, DatePicker, message, Radio, Input } from 'antd';
import { DownOutlined, ExportOutlined, PrinterOutlined, EditOutlined, CarOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { MenuProps } from 'antd';
import dayjs from 'dayjs';
import api from '../../services/api';
import * as XLSX from 'xlsx';

interface BulkOrderActionsProps {
  selectedOrderIds: string[];
  selectedOrders: any[];
  onActionComplete: () => void;
}

const BulkOrderActions: React.FC<BulkOrderActionsProps> = ({
  selectedOrderIds,
  selectedOrders,
  onActionComplete,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [actionType, setActionType] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [drivers, setDrivers] = useState<any[]>([]);

  // Fetch available drivers when needed
  const fetchDrivers = async () => {
    try {
      const response = await api.get('/users/drivers');
      setDrivers(response.data);
    } catch (error) {
      console.error('Failed to fetch drivers:', error);
    }
  };

  // Check if all selected orders have the same status
  const checkOrderStatuses = () => {
    const statuses = selectedOrders.map(order => order.status);
    return {
      allSame: statuses.every(status => status === statuses[0]),
      currentStatus: statuses[0],
      statuses: [...new Set(statuses)],
    };
  };

  // Handle bulk status update
  const handleBulkStatusUpdate = async (values: any) => {
    setLoading(true);
    try {
      await api.put('/orders/bulk/status', {
        orderIds: selectedOrderIds,
        newStatus: values.status,
        reason: values.reason,
      });
      message.success(t('orders.bulkStatusUpdateSuccess'));
      onActionComplete();
      setIsModalVisible(false);
    } catch (error) {
      message.error(t('orders.bulkStatusUpdateError'));
    } finally {
      setLoading(false);
    }
  };

  // Handle bulk driver assignment
  const handleBulkDriverAssignment = async (values: any) => {
    setLoading(true);
    try {
      await api.put('/orders/bulk/assign-driver', {
        orderIds: selectedOrderIds,
        driverId: values.driverId,
        routeId: values.routeId,
      });
      message.success(t('orders.bulkDriverAssignmentSuccess'));
      onActionComplete();
      setIsModalVisible(false);
    } catch (error) {
      message.error(t('orders.bulkDriverAssignmentError'));
    } finally {
      setLoading(false);
    }
  };

  // Handle bulk priority update
  const handleBulkPriorityUpdate = async (values: any) => {
    setLoading(true);
    try {
      await api.put('/orders/bulk/priority', {
        orderIds: selectedOrderIds,
        priority: values.priority,
        reason: values.reason,
      });
      message.success(t('orders.bulkPriorityUpdateSuccess'));
      onActionComplete();
      setIsModalVisible(false);
    } catch (error) {
      message.error(t('orders.bulkPriorityUpdateError'));
    } finally {
      setLoading(false);
    }
  };

  // Handle bulk delivery date update
  const handleBulkDeliveryDateUpdate = async (values: any) => {
    setLoading(true);
    try {
      await api.put('/orders/bulk/delivery-date', {
        orderIds: selectedOrderIds,
        deliveryDate: values.deliveryDate.format('YYYY-MM-DD'),
        reason: values.reason,
      });
      message.success(t('orders.bulkDeliveryDateUpdateSuccess'));
      onActionComplete();
      setIsModalVisible(false);
    } catch (error) {
      message.error(t('orders.bulkDeliveryDateUpdateError'));
    } finally {
      setLoading(false);
    }
  };

  // Export orders to Excel
  const exportToExcel = () => {
    const data = selectedOrders.map(order => ({
      訂單編號: order.orderNumber,
      客戶名稱: order.customerName,
      客戶電話: order.customerPhone,
      客戶地址: order.customerAddress,
      訂單日期: dayjs(order.orderDate).format('YYYY/MM/DD'),
      配送日期: order.deliveryDate ? dayjs(order.deliveryDate).format('YYYY/MM/DD') : '',
      狀態: t(`orders.status.${order.status}`),
      優先級: t(`orders.priority.${order.priority}`),
      瓦斯桶規格: order.cylinderType,
      數量: order.quantity,
      單價: order.unitPrice,
      總金額: order.totalAmount,
      付款方式: t(`orders.paymentMethod.${order.paymentMethod}`),
      付款狀態: t(`orders.paymentStatus.${order.paymentStatus}`),
      司機: order.driverName || '',
      配送備註: order.deliveryNotes || '',
    }));

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, '訂單列表');

    // Set column widths
    const colWidths = [
      { wch: 15 }, // 訂單編號
      { wch: 20 }, // 客戶名稱
      { wch: 15 }, // 客戶電話
      { wch: 30 }, // 客戶地址
      { wch: 12 }, // 訂單日期
      { wch: 12 }, // 配送日期
      { wch: 10 }, // 狀態
      { wch: 10 }, // 優先級
      { wch: 12 }, // 瓦斯桶規格
      { wch: 8 },  // 數量
      { wch: 10 }, // 單價
      { wch: 12 }, // 總金額
      { wch: 10 }, // 付款方式
      { wch: 10 }, // 付款狀態
      { wch: 15 }, // 司機
      { wch: 30 }, // 配送備註
    ];
    ws['!cols'] = colWidths;

    // Generate filename with current date
    const filename = `訂單列表_${dayjs().format('YYYYMMDD_HHmmss')}.xlsx`;
    XLSX.writeFile(wb, filename);
    
    message.success(t('orders.exportSuccess'));
  };

  // Print invoices
  const printInvoices = async () => {
    setLoading(true);
    try {
      const response = await api.post('/orders/bulk/generate-invoices', {
        orderIds: selectedOrderIds,
      }, {
        responseType: 'blob',
      });

      // Create a URL for the blob
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `invoices_${dayjs().format('YYYYMMDD_HHmmss')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      message.success(t('orders.printSuccess'));
    } catch (error) {
      message.error(t('orders.printError'));
    } finally {
      setLoading(false);
    }
  };

  const handleMenuClick: MenuProps['onClick'] = async (e) => {
    switch (e.key) {
      case 'updateStatus':
        setActionType('status');
        setIsModalVisible(true);
        break;
      case 'assignDriver':
        setActionType('driver');
        await fetchDrivers();
        setIsModalVisible(true);
        break;
      case 'updatePriority':
        setActionType('priority');
        setIsModalVisible(true);
        break;
      case 'updateDeliveryDate':
        setActionType('deliveryDate');
        setIsModalVisible(true);
        break;
      case 'export':
        exportToExcel();
        break;
      case 'print':
        await printInvoices();
        break;
    }
  };

  const items: MenuProps['items'] = [
    {
      key: 'updateStatus',
      icon: <EditOutlined />,
      label: t('orders.bulkUpdateStatus'),
    },
    {
      key: 'assignDriver',
      icon: <CarOutlined />,
      label: t('orders.bulkAssignDriver'),
    },
    {
      key: 'updatePriority',
      icon: <ExclamationCircleOutlined />,
      label: t('orders.bulkUpdatePriority'),
    },
    {
      key: 'updateDeliveryDate',
      icon: <EditOutlined />,
      label: t('orders.bulkUpdateDeliveryDate'),
    },
    {
      type: 'divider',
    },
    {
      key: 'export',
      icon: <ExportOutlined />,
      label: t('orders.exportToExcel'),
    },
    {
      key: 'print',
      icon: <PrinterOutlined />,
      label: t('orders.printInvoices'),
    },
  ];

  const handleModalSubmit = async (values: any) => {
    switch (actionType) {
      case 'status':
        await handleBulkStatusUpdate(values);
        break;
      case 'driver':
        await handleBulkDriverAssignment(values);
        break;
      case 'priority':
        await handleBulkPriorityUpdate(values);
        break;
      case 'deliveryDate':
        await handleBulkDeliveryDateUpdate(values);
        break;
    }
  };

  const renderModalContent = () => {
    const statusInfo = checkOrderStatuses();

    switch (actionType) {
      case 'status':
        return (
          <>
            {!statusInfo.allSame && (
              <p style={{ color: '#ff4d4f', marginBottom: 16 }}>
                {t('orders.mixedStatusWarning', { statuses: statusInfo.statuses.join(', ') })}
              </p>
            )}
            <Form.Item
              name="status"
              label={t('orders.newStatus')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Select>
                <Select.Option value="confirmed">{t('orders.status.confirmed')}</Select.Option>
                <Select.Option value="assigned">{t('orders.status.assigned')}</Select.Option>
                <Select.Option value="in_delivery">{t('orders.status.in_delivery')}</Select.Option>
                <Select.Option value="delivered">{t('orders.status.delivered')}</Select.Option>
                <Select.Option value="cancelled">{t('orders.status.cancelled')}</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item
              name="reason"
              label={t('orders.updateReason')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Input.TextArea rows={3} placeholder={t('orders.enterUpdateReason')} />
            </Form.Item>
          </>
        );

      case 'driver':
        return (
          <>
            <Form.Item
              name="driverId"
              label={t('orders.selectDriver')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Select
                showSearch
                placeholder={t('orders.selectDriver')}
                optionFilterProp="children"
                filterOption={(input, option) =>
                  option?.children?.toLowerCase().indexOf(input.toLowerCase()) >= 0
                }
              >
                {drivers.map(driver => (
                  <Select.Option key={driver.id} value={driver.id}>
                    {driver.fullName}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item
              name="routeId"
              label={t('orders.routeNumber')}
            >
              <Input placeholder={t('orders.enterRouteNumber')} />
            </Form.Item>
          </>
        );

      case 'priority':
        return (
          <>
            <Form.Item
              name="priority"
              label={t('orders.newPriority')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Radio.Group>
                <Radio value="normal">{t('orders.priority.normal')}</Radio>
                <Radio value="urgent">{t('orders.priority.urgent')}</Radio>
                <Radio value="scheduled">{t('orders.priority.scheduled')}</Radio>
              </Radio.Group>
            </Form.Item>
            <Form.Item
              name="reason"
              label={t('orders.updateReason')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Input.TextArea rows={3} placeholder={t('orders.enterUpdateReason')} />
            </Form.Item>
          </>
        );

      case 'deliveryDate':
        return (
          <>
            <Form.Item
              name="deliveryDate"
              label={t('orders.newDeliveryDate')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <DatePicker
                style={{ width: '100%' }}
                disabledDate={(current) => {
                  return current && current < dayjs().startOf('day');
                }}
              />
            </Form.Item>
            <Form.Item
              name="reason"
              label={t('orders.updateReason')}
              rules={[{ required: true, message: t('validation.required') }]}
            >
              <Input.TextArea rows={3} placeholder={t('orders.enterUpdateReason')} />
            </Form.Item>
          </>
        );
    }
  };

  const getModalTitle = () => {
    switch (actionType) {
      case 'status':
        return t('orders.bulkUpdateStatus');
      case 'driver':
        return t('orders.bulkAssignDriver');
      case 'priority':
        return t('orders.bulkUpdatePriority');
      case 'deliveryDate':
        return t('orders.bulkUpdateDeliveryDate');
      default:
        return '';
    }
  };

  return (
    <>
      <Space>
        <span>{t('orders.selectedCount', { count: selectedOrderIds.length })}</span>
        <Dropdown
          menu={{ items, onClick: handleMenuClick }}
          disabled={selectedOrderIds.length === 0}
        >
          <Button>
            {t('orders.bulkActions')} <DownOutlined />
          </Button>
        </Dropdown>
      </Space>

      <Modal
        title={getModalTitle()}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleModalSubmit}
        >
          {renderModalContent()}
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {t('common.confirm')}
              </Button>
              <Button onClick={() => setIsModalVisible(false)}>
                {t('common.cancel')}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default BulkOrderActions;