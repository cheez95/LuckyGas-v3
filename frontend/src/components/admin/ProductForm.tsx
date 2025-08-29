import React, { useEffect } from 'react';
import { Modal, Form, Input, Select, InputNumber, Switch, Row, Col } from 'antd';
import { GasProduct, GasProductCreate, GasProductUpdate, DeliveryMethod, ProductAttribute } from '../../types/product';
import { useTranslation } from 'react-i18next';

const { Option } = Select;
const { TextArea } = Input;

interface ProductFormProps {
  visible: boolean;
  product: GasProduct | null;
  onSubmit: (values: GasProductCreate | GasProductUpdate) => void;
  onCancel: () => void;
}

const ProductForm: React.FC<ProductFormProps> = ({
  visible,
  product,
  onSubmit,
  onCancel,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();

  useEffect(() => {
    if (visible) {
      if (product) {
        // Edit mode - set form values
        form.setFieldsValue({
          delivery_method: product.delivery_method,
          size_kg: product.size_kg,
          attribute: product.attribute,
          sku: product.sku,
          name_zh: product.name_zh,
          name_en: product.name_en,
          description: product.description,
          unit_price: product.unit_price,
          deposit_amount: product.deposit_amount,
          is_active: product.is_active,
          is_available: product.is_available,
          track_inventory: product.track_inventory,
          low_stock_threshold: product.low_stock_threshold,
        });
      } else {
        // Add mode - reset form with defaults
        form.resetFields();
        form.setFieldsValue({
          delivery_method: DeliveryMethod.CYLINDER,
          attribute: ProductAttribute.REGULAR,
          is_active: true,
          is_available: true,
          track_inventory: true,
          low_stock_threshold: 10,
          deposit_amount: 0,
        });
      }
    }
  }, [visible, product, form]);

  const handleSubmit = () => {
    form
      .validateFields()
      .then((values) => {
        // Generate SKU if not provided
        if (!values.sku && !product) {
          const method = values.delivery_method === DeliveryMethod.FLOW ? 'F' : 'C';
          const attr = values.attribute.substring(0, 3).toUpperCase();
          values.sku = `${method}-${values.size_kg}KG-${attr}`;
        }
        
        onSubmit(values);
        form.resetFields();
      })
      .catch((error) => {
        console.error('Form validation failed:', error);
      });
  };

  return (
    <Modal
      title={product ? '編輯產品' : '新增產品'}
      open={visible}
      onOk={handleSubmit}
      onCancel={() => {
        form.resetFields();
        onCancel();
      }}
      width={800}
      okText="儲存"
      cancelText="取消"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          delivery_method: DeliveryMethod.CYLINDER,
          attribute: ProductAttribute.REGULAR,
          is_active: true,
          is_available: true,
          track_inventory: true,
          low_stock_threshold: 10,
          deposit_amount: 0,
        }}
      >
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="delivery_method"
              label="配送方式"
              rules={[{ required: true, message: '請選擇配送方式' }]}
            >
              <Select disabled={!!product}>
                <Option value={DeliveryMethod.CYLINDER}>桶裝</Option>
                <Option value={DeliveryMethod.FLOW}>流量</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="size_kg"
              label="規格 (公斤)"
              rules={[{ required: true, message: '請輸入規格' }]}
            >
              <Select disabled={!!product}>
                <Option value={4}>4 公斤</Option>
                <Option value={10}>10 公斤</Option>
                <Option value={16}>16 公斤</Option>
                <Option value={20}>20 公斤</Option>
                <Option value={50}>50 公斤</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="attribute"
              label="屬性"
              rules={[{ required: true, message: '請選擇屬性' }]}
            >
              <Select disabled={!!product}>
                <Option value={ProductAttribute.REGULAR}>一般</Option>
                <Option value={ProductAttribute.COMMERCIAL}>營業用</Option>
                <Option value={ProductAttribute.HAOYUN}>好運</Option>
                <Option value={ProductAttribute.PINGAN}>瓶安</Option>
                <Option value={ProductAttribute.XINGFU}>幸福</Option>
                <Option value={ProductAttribute.SPECIAL}>特殊</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="sku"
              label="產品編號"
              tooltip="留空將自動產生"
              rules={[
                { max: 50, message: '產品編號最多50個字' },
                { pattern: /^[A-Z0-9\-_]+$/i, message: '只能包含英文、數字、橫線和底線' },
              ]}
            >
              <Input placeholder="例: C-20KG-REG" disabled={!!product} />
            </Form.Item>
          </Col>
          <Col span={16}>
            <Form.Item
              name="name_zh"
              label="中文名稱"
              rules={[{ required: true, message: '請輸入中文名稱' }]}
            >
              <Input placeholder="例: 20公斤桶裝瓦斯" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="name_en"
              label="英文名稱 (選填)"
            >
              <Input placeholder="例: 20kg Cylinder Gas" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="description"
              label="產品描述 (選填)"
            >
              <TextArea rows={2} placeholder="產品詳細描述" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="unit_price"
              label="單價 (NT$)"
              rules={[
                { required: true, message: '請輸入單價' },
                { type: 'number', min: 0, message: '單價必須大於0' },
              ]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={999999}
                formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(value) => value!.replace(/\$\s?|(,*)/g, '')}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="deposit_amount"
              label="押金 (NT$)"
              rules={[
                { type: 'number', min: 0, message: '押金必須大於等於0' },
              ]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={999999}
                formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(value) => value!.replace(/\$\s?|(,*)/g, '')}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="low_stock_threshold"
              label="低庫存警示值"
              tooltip="當庫存低於此數量時發出警告"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={9999}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="is_active"
              label="啟用狀態"
              valuePropName="checked"
            >
              <Switch checkedChildren="啟用" unCheckedChildren="停用" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="is_available"
              label="可訂購"
              valuePropName="checked"
            >
              <Switch checkedChildren="可訂" unCheckedChildren="不可訂" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="track_inventory"
              label="追蹤庫存"
              valuePropName="checked"
            >
              <Switch checkedChildren="追蹤" unCheckedChildren="不追蹤" />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  );
};

export default ProductForm;