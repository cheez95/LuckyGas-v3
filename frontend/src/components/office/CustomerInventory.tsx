import React, { useState, useEffect } from 'react';
import { Modal, Table, Card, Button, InputNumber, Space, Tag, message, Spin } from 'antd';
import { EditOutlined, SaveOutlined, CloseOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { customerService } from '../../services/customer.service';
import { Customer } from '../../types/order';
import { CustomerInventory, DeliveryMethod, ProductAttribute } from '../../types/product';

interface CustomerInventoryProps {
  customer: Customer;
  open: boolean;
  onClose: () => void;
}

interface EditingCell {
  id: number;
  field: 'owned' | 'rented';
}

const CustomerInventoryComponent: React.FC<CustomerInventoryProps> = ({ customer, open, onClose }) => {
  const [inventory, setInventory] = useState<CustomerInventory[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingCell, setEditingCell] = useState<EditingCell | null>(null);
  const [editingValue, setEditingValue] = useState<number>(0);

  useEffect(() => {
    if (open && customer) {
      fetchInventory();
    }
  }, [open, customer]);

  const fetchInventory = async () => {
    setLoading(true);
    try {
      const response = await customerService.getCustomerInventory(customer.id);
      setInventory(response.items);
    } catch (error) {
      message.error('無法載入庫存資料');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (item: CustomerInventory, field: 'owned' | 'rented') => {
    setEditingCell({ id: item.id!, field });
    setEditingValue(field === 'owned' ? item.quantity_owned : item.quantity_rented);
  };

  const handleSave = async (item: CustomerInventory) => {
    if (!editingCell) return;

    try {
      const updateData = editingCell.field === 'owned' 
        ? { quantity_owned: editingValue }
        : { quantity_rented: editingValue };
      
      await customerService.updateInventoryItem(customer.id, item.gas_product_id, updateData);
      
      // Update local state
      setInventory(inventory.map(inv => 
        inv.id === item.id 
          ? { ...inv, ...updateData }
          : inv
      ));
      
      message.success('庫存更新成功');
      setEditingCell(null);
    } catch (error) {
      message.error('庫存更新失敗');
    }
  };

  const handleCancel = () => {
    setEditingCell(null);
    setEditingValue(0);
  };

  const getDeliveryMethodText = (method: DeliveryMethod) => {
    const methodMap = {
      [DeliveryMethod.CYLINDER]: '桶裝',
      [DeliveryMethod.FLOW]: '流量'
    };
    return methodMap[method] || method;
  };

  const getAttributeText = (attribute: ProductAttribute) => {
    const attributeMap = {
      [ProductAttribute.REGULAR]: '一般',
      [ProductAttribute.HAOYUN]: '好運',
      [ProductAttribute.PINGAN]: '平安'
    };
    return attributeMap[attribute] || attribute;
  };

  const columns: ColumnsType<CustomerInventory> = [
    {
      title: '產品名稱',
      dataIndex: ['gas_product', 'display_name'],
      key: 'product_name',
      render: (_, record) => record.gas_product?.display_name || '-',
    },
    {
      title: '配送方式',
      key: 'delivery_method',
      width: 100,
      render: (_, record) => (
        <Tag color="blue">
          {record.gas_product ? getDeliveryMethodText(record.gas_product.delivery_method) : '-'}
        </Tag>
      ),
    },
    {
      title: '規格',
      key: 'size',
      width: 80,
      render: (_, record) => `${record.gas_product?.size_kg || 0}kg`,
    },
    {
      title: '屬性',
      key: 'attribute',
      width: 80,
      render: (_, record) => {
        if (!record.gas_product || record.gas_product.attribute === ProductAttribute.REGULAR) {
          return '-';
        }
        return <Tag color="gold">{getAttributeText(record.gas_product.attribute)}</Tag>;
      },
    },
    {
      title: '客戶擁有數量',
      dataIndex: 'quantity_owned',
      key: 'quantity_owned',
      width: 150,
      render: (value, record) => {
        const isEditing = editingCell?.id === record.id && editingCell.field === 'owned';
        if (isEditing) {
          return (
            <Space>
              <InputNumber
                min={0}
                value={editingValue}
                onChange={(val) => setEditingValue(val || 0)}
                size="small"
              />
              <Button
                icon={<SaveOutlined />}
                size="small"
                type="primary"
                onClick={() => handleSave(record)}
              />
              <Button
                icon={<CloseOutlined />}
                size="small"
                onClick={handleCancel}
              />
            </Space>
          );
        }
        return (
          <Space>
            <span>{value}</span>
            <Button
              icon={<EditOutlined />}
              size="small"
              type="text"
              onClick={() => handleEdit(record, 'owned')}
            />
          </Space>
        );
      },
    },
    {
      title: '租借數量',
      dataIndex: 'quantity_rented',
      key: 'quantity_rented',
      width: 150,
      render: (value, record) => {
        const isEditing = editingCell?.id === record.id && editingCell.field === 'rented';
        if (isEditing) {
          return (
            <Space>
              <InputNumber
                min={0}
                value={editingValue}
                onChange={(val) => setEditingValue(val || 0)}
                size="small"
              />
              <Button
                icon={<SaveOutlined />}
                size="small"
                type="primary"
                onClick={() => handleSave(record)}
              />
              <Button
                icon={<CloseOutlined />}
                size="small"
                onClick={handleCancel}
              />
            </Space>
          );
        }
        return (
          <Space>
            <span>{value}</span>
            <Button
              icon={<EditOutlined />}
              size="small"
              type="text"
              onClick={() => handleEdit(record, 'rented')}
            />
          </Space>
        );
      },
    },
    {
      title: '可用數量',
      dataIndex: 'quantity_available',
      key: 'quantity_available',
      width: 100,
      render: (value) => (
        <Tag color={value > 0 ? 'green' : 'red'}>
          {value}
        </Tag>
      ),
    },
  ];

  return (
    <Modal
      title={`客戶庫存管理 - ${customer.short_name}`}
      open={open}
      onCancel={onClose}
      width={1000}
      footer={[
        <Button key="close" onClick={onClose}>
          關閉
        </Button>,
      ]}
    >
      <Card>
        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={inventory}
            rowKey="id"
            pagination={false}
            scroll={{ y: 400 }}
          />
        </Spin>
        <div style={{ marginTop: 16, color: '#999' }}>
          <p>* 可用數量 = 客戶擁有數量 - 租借數量</p>
          <p>* 點擊編輯按鈕可修改庫存數量</p>
        </div>
      </Card>
    </Modal>
  );
};

export default CustomerInventoryComponent;