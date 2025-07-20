import React, { useState, useEffect } from 'react';
import { Select, Form, InputNumber, Button, Space, Card, Tag, Tooltip, Row, Col, Checkbox, Input } from 'antd';
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ProductService from '../../services/product.service';
import { GasProduct, OrderItemCreate, DeliveryMethod, ProductAttribute } from '../../types/product';

const { Option } = Select;
const { TextArea } = Input;

interface ProductSelectorProps {
  onProductsChange: (items: OrderItemCreate[]) => void;
  initialItems?: OrderItemCreate[];
  disabled?: boolean;
}

interface ProductItemForm extends OrderItemCreate {
  tempId?: string;
}

const ProductSelector: React.FC<ProductSelectorProps> = ({ 
  onProductsChange, 
  initialItems = [],
  disabled = false 
}) => {
  const { t } = useTranslation();
  const [products, setProducts] = useState<GasProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedItems, setSelectedItems] = useState<ProductItemForm[]>(
    initialItems.map(item => ({ ...item, tempId: Math.random().toString(36) }))
  );

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    // Remove tempId before passing to parent
    const itemsWithoutTempId = selectedItems.map(({ tempId, ...item }) => item);
    onProductsChange(itemsWithoutTempId);
  }, [selectedItems, onProductsChange]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const availableProducts = await ProductService.getAvailableProducts();
      setProducts(availableProducts);
    } catch (error) {
      console.error('Failed to load products:', error);
    } finally {
      setLoading(false);
    }
  };

  const addProduct = () => {
    const newItem: ProductItemForm = {
      tempId: Math.random().toString(36),
      gas_product_id: 0,
      quantity: 1,
      is_exchange: true,
      empty_received: 0,
      is_flow_delivery: false,
      discount_percentage: 0,
      discount_amount: 0,
    };
    setSelectedItems([...selectedItems, newItem]);
  };

  const removeProduct = (tempId: string) => {
    setSelectedItems(selectedItems.filter(item => item.tempId !== tempId));
  };

  const updateProduct = (tempId: string, updates: Partial<ProductItemForm>) => {
    setSelectedItems(selectedItems.map(item => 
      item.tempId === tempId ? { ...item, ...updates } : item
    ));
  };

  const getProductById = (id: number) => {
    return products.find(p => p.id === id);
  };

  const getDeliveryMethodText = (method: DeliveryMethod) => {
    return t(`product.deliveryMethods.${method}`);
  };

  const getAttributeText = (attribute: ProductAttribute) => {
    return t(`product.attributes.${attribute}`);
  };

  const getSizeText = (size: number) => {
    return t(`product.sizes.${size}kg`);
  };

  return (
    <div className="product-selector">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {selectedItems.map((item, index) => {
          const product = item.gas_product_id ? getProductById(item.gas_product_id) : null;
          const isFlow = product?.delivery_method === DeliveryMethod.FLOW;

          return (
            <Card 
              key={item.tempId} 
              size="small"
              title={`${t('order.items')} ${index + 1}`}
              extra={
                !disabled && (
                  <Button
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => removeProduct(item.tempId!)}
                  >
                    {t('order.removeProduct')}
                  </Button>
                )
              }
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item label={t('order.selectProduct')} required>
                    <Select
                      value={item.gas_product_id || undefined}
                      onChange={(value) => {
                        const selectedProduct = getProductById(value);
                        updateProduct(item.tempId!, {
                          gas_product_id: value,
                          unit_price: selectedProduct?.unit_price,
                          is_flow_delivery: selectedProduct?.delivery_method === DeliveryMethod.FLOW,
                        });
                      }}
                      placeholder={t('order.selectProduct')}
                      disabled={disabled}
                      loading={loading}
                      showSearch
                      filterOption={(input, option) => {
                        const label = option?.children as any;
                        return typeof label === 'string' && label.toLowerCase().includes(input.toLowerCase());
                      }}
                    >
                      {products.map(product => (
                        <Option key={product.id} value={product.id}>
                          {product.display_name} - NT$ {product.unit_price}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>

                <Col xs={24} md={6}>
                  <Form.Item label={t('order.quantity')} required>
                    <InputNumber
                      min={1}
                      value={item.quantity}
                      onChange={(value) => updateProduct(item.tempId!, { quantity: value || 1 })}
                      disabled={disabled}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} md={6}>
                  <Form.Item label={t('order.unitPrice')}>
                    <InputNumber
                      min={0}
                      value={item.unit_price || product?.unit_price}
                      onChange={(value) => updateProduct(item.tempId!, { unit_price: value || 0 })}
                      disabled={disabled}
                      prefix="NT$"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>

                {!isFlow && (
                  <>
                    <Col xs={24} md={12}>
                      <Form.Item>
                        <Checkbox
                          checked={item.is_exchange}
                          onChange={(e) => updateProduct(item.tempId!, { is_exchange: e.target.checked })}
                          disabled={disabled}
                        >
                          {t('order.isExchange')}
                          <Tooltip title="是否收回空瓶">
                            <InfoCircleOutlined style={{ marginLeft: 4 }} />
                          </Tooltip>
                        </Checkbox>
                      </Form.Item>
                    </Col>

                    {item.is_exchange && (
                      <Col xs={24} md={12}>
                        <Form.Item label={t('order.emptyReceived')}>
                          <InputNumber
                            min={0}
                            value={item.empty_received}
                            onChange={(value) => updateProduct(item.tempId!, { empty_received: value || 0 })}
                            disabled={disabled}
                            style={{ width: '100%' }}
                          />
                        </Form.Item>
                      </Col>
                    )}
                  </>
                )}

                {isFlow && (
                  <>
                    <Col xs={24} md={8}>
                      <Form.Item label={t('order.meterReadingStart')}>
                        <InputNumber
                          min={0}
                          value={item.meter_reading_start}
                          onChange={(value) => updateProduct(item.tempId!, { meter_reading_start: value || undefined })}
                          disabled={disabled}
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                    </Col>

                    <Col xs={24} md={8}>
                      <Form.Item label={t('order.meterReadingEnd')}>
                        <InputNumber
                          min={item.meter_reading_start || 0}
                          value={item.meter_reading_end}
                          onChange={(value) => updateProduct(item.tempId!, { meter_reading_end: value || undefined })}
                          disabled={disabled}
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                    </Col>

                    <Col xs={24} md={8}>
                      <Form.Item label={t('order.actualQuantity')}>
                        <InputNumber
                          min={0}
                          value={item.actual_quantity}
                          onChange={(value) => updateProduct(item.tempId!, { actual_quantity: value || undefined })}
                          disabled={disabled}
                          suffix="kg"
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                    </Col>
                  </>
                )}

                <Col xs={24} md={12}>
                  <Form.Item label={t('order.discountPercentage')}>
                    <InputNumber
                      min={0}
                      max={100}
                      value={item.discount_percentage}
                      onChange={(value) => updateProduct(item.tempId!, { discount_percentage: value || 0 })}
                      disabled={disabled}
                      suffix="%"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} md={12}>
                  <Form.Item label={t('order.discountAmount')}>
                    <InputNumber
                      min={0}
                      value={item.discount_amount}
                      onChange={(value) => updateProduct(item.tempId!, { discount_amount: value || 0 })}
                      disabled={disabled}
                      prefix="NT$"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>

                <Col span={24}>
                  <Form.Item label={t('notes')}>
                    <TextArea
                      rows={2}
                      value={item.notes}
                      onChange={(e) => updateProduct(item.tempId!, { notes: e.target.value })}
                      disabled={disabled}
                      placeholder={t('order.deliveryNotes')}
                    />
                  </Form.Item>
                </Col>

                {product && (
                  <Col span={24}>
                    <Space size="small" wrap>
                      <Tag color="blue">{getDeliveryMethodText(product.delivery_method)}</Tag>
                      <Tag color="green">{getSizeText(product.size_kg)}</Tag>
                      {product.attribute !== ProductAttribute.REGULAR && (
                        <Tag color="gold">{getAttributeText(product.attribute)}</Tag>
                      )}
                      {product.deposit_amount > 0 && (
                        <Tag>押金: NT$ {product.deposit_amount}</Tag>
                      )}
                    </Space>
                  </Col>
                )}
              </Row>
            </Card>
          );
        })}

        {!disabled && (
          <Button
            type="dashed"
            onClick={addProduct}
            icon={<PlusOutlined />}
            block
          >
            {t('order.addProduct')}
          </Button>
        )}

        {selectedItems.length === 0 && (
          <Card>
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <p>{t('order.noProductsSelected')}</p>
              {!disabled && (
                <Button type="primary" onClick={addProduct} icon={<PlusOutlined />}>
                  {t('order.addProduct')}
                </Button>
              )}
            </div>
          </Card>
        )}
      </Space>
    </div>
  );
};

export default ProductSelector;