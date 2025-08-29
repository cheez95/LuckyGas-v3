import React, { useState } from 'react';
import { Table, Tag, Space, Button, Switch, Tooltip, Input } from 'antd';
import { EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType, TableProps } from 'antd/es/table';
import { GasProduct } from '../../types/product';
import { useTranslation } from 'react-i18next';
import ProductService from '../../services/product.service';

interface ProductListProps {
  products: GasProduct[];
  loading: boolean;
  onEdit: (product: GasProduct) => void;
  onDelete: (product: GasProduct) => void;
  onRefresh: () => void;
}

const ProductList: React.FC<ProductListProps> = ({
  products,
  loading,
  onEdit,
  onDelete,
  onRefresh,
}) => {
  const { t } = useTranslation();
  const [searchText, setSearchText] = useState('');
  const [filteredProducts, setFilteredProducts] = useState<GasProduct[]>(products);

  React.useEffect(() => {
    const filtered = products.filter(
      product =>
        product.name_zh.toLowerCase().includes(searchText.toLowerCase()) ||
        product.sku.toLowerCase().includes(searchText.toLowerCase()) ||
        product.display_name.toLowerCase().includes(searchText.toLowerCase())
    );
    setFilteredProducts(filtered);
  }, [products, searchText]);

  const handleToggleActive = async (product: GasProduct) => {
    try {
      await ProductService.updateProduct(product.id, {
        is_active: !product.is_active,
      });
      onRefresh();
    } catch (error) {
      console.error('Failed to toggle product status:', error);
    }
  };

  const handleToggleAvailable = async (product: GasProduct) => {
    try {
      await ProductService.updateProduct(product.id, {
        is_available: !product.is_available,
      });
      onRefresh();
    } catch (error) {
      console.error('Failed to toggle product availability:', error);
    }
  };

  const columns: ColumnsType<GasProduct> = [
    {
      title: '產品編號',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      sorter: (a, b) => a.sku.localeCompare(b.sku),
    },
    {
      title: '產品名稱',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text, record) => (
        <div>
          <div>{record.name_zh}</div>
          {record.name_en && (
            <div style={{ fontSize: '12px', color: '#999' }}>{record.name_en}</div>
          )}
        </div>
      ),
    },
    {
      title: '配送方式',
      dataIndex: 'delivery_method',
      key: 'delivery_method',
      width: 100,
      render: (method) => (
        <Tag color={method === 'CYLINDER' ? 'blue' : 'green'}>
          {t(`product.deliveryMethods.${method.toLowerCase()}`)}
        </Tag>
      ),
      filters: [
        { text: '桶裝', value: 'CYLINDER' },
        { text: '流量', value: 'FLOW' },
      ],
      onFilter: (value, record) => record.delivery_method === value,
    },
    {
      title: '規格',
      dataIndex: 'size_kg',
      key: 'size_kg',
      width: 80,
      render: (size) => `${size}kg`,
      sorter: (a, b) => a.size_kg - b.size_kg,
      filters: [
        { text: '4kg', value: 4 },
        { text: '10kg', value: 10 },
        { text: '16kg', value: 16 },
        { text: '20kg', value: 20 },
        { text: '50kg', value: 50 },
      ],
      onFilter: (value, record) => record.size_kg === value,
    },
    {
      title: '屬性',
      dataIndex: 'attribute',
      key: 'attribute',
      width: 100,
      render: (attribute) => {
        const colorMap: Record<string, string> = {
          REGULAR: 'default',
          COMMERCIAL: 'purple',
          HAOYUN: 'gold',
          PINGAN: 'cyan',
          XINGFU: 'magenta',
          SPECIAL: 'volcano',
        };
        return (
          <Tag color={colorMap[attribute] || 'default'}>
            {t(`product.attributes.${attribute.toLowerCase()}`)}
          </Tag>
        );
      },
      filters: [
        { text: '一般', value: 'REGULAR' },
        { text: '營業用', value: 'COMMERCIAL' },
        { text: '好運', value: 'HAOYUN' },
        { text: '瓶安', value: 'PINGAN' },
        { text: '幸福', value: 'XINGFU' },
        { text: '特殊', value: 'SPECIAL' },
      ],
      onFilter: (value, record) => record.attribute === value,
    },
    {
      title: '單價',
      dataIndex: 'unit_price',
      key: 'unit_price',
      width: 100,
      render: (price) => `NT$ ${price.toLocaleString()}`,
      sorter: (a, b) => a.unit_price - b.unit_price,
    },
    {
      title: '押金',
      dataIndex: 'deposit_amount',
      key: 'deposit_amount',
      width: 100,
      render: (amount) => (amount > 0 ? `NT$ ${amount.toLocaleString()}` : '-'),
      sorter: (a, b) => a.deposit_amount - b.deposit_amount,
    },
    {
      title: '庫存追蹤',
      dataIndex: 'track_inventory',
      key: 'track_inventory',
      width: 100,
      align: 'center',
      render: (track) => (
        <Tag color={track ? 'success' : 'default'}>{track ? '是' : '否'}</Tag>
      ),
    },
    {
      title: '低庫存警示',
      dataIndex: 'low_stock_threshold',
      key: 'low_stock_threshold',
      width: 100,
      align: 'center',
      render: (threshold, record) =>
        record.track_inventory ? threshold : '-',
    },
    {
      title: '狀態',
      key: 'status',
      width: 140,
      fixed: 'right',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Space>
            <span>啟用:</span>
            <Switch
              size="small"
              checked={record.is_active}
              onChange={() => handleToggleActive(record)}
            />
          </Space>
          <Space>
            <span>可訂:</span>
            <Switch
              size="small"
              checked={record.is_available}
              onChange={() => handleToggleAvailable(record)}
              disabled={!record.is_active}
            />
          </Space>
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="編輯">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
            />
          </Tooltip>
          <Tooltip title="刪除">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const tableProps: TableProps<GasProduct> = {
    columns,
    dataSource: filteredProducts,
    loading,
    rowKey: 'id',
    scroll: { x: 1500 },
    pagination: {
      pageSize: 20,
      showSizeChanger: true,
      showTotal: (total) => `共 ${total} 個產品`,
    },
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜尋產品名稱或編號"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 300 }}
          allowClear
        />
      </div>
      <Table {...tableProps} />
    </div>
  );
};

export default ProductList;