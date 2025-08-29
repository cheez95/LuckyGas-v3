import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Form,
  Input,
  Button,
  Card,
  Row,
  Col,
  Select,
  InputNumber,
  Switch,
  message,
  Spin,
  Typography,
  Space,
  TimePicker
} from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { customerService } from '../../services/customer.service';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const CustomerForm: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const isEditMode = !!id;

  // Load customer data if in edit mode
  useEffect(() => {
    if (isEditMode && id) {
      loadCustomer(id);
    }
  }, [id, isEditMode]);

  const loadCustomer = async (customerId: string) => {
    setLoading(true);
    try {
      const customer = await customerService.getCustomer(customerId);
      form.setFieldsValue({
        ...customer,
        delivery_time: customer.delivery_time_start && customer.delivery_time_end
          ? [dayjs(customer.delivery_time_start, 'HH:mm'), dayjs(customer.delivery_time_end, 'HH:mm')]
          : undefined,
      });
    } catch (error) {
      message.error('無法載入客戶資料');
      navigate('/customers');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      const customerData = {
        ...values,
        delivery_time_start: values.delivery_time?.[0]?.format('HH:mm'),
        delivery_time_end: values.delivery_time?.[1]?.format('HH:mm'),
      };
      delete customerData.delivery_time;

      if (isEditMode && id) {
        await customerService.updateCustomer(id, customerData);
        message.success('客戶資料已更新');
      } else {
        await customerService.createCustomer(customerData);
        message.success('客戶已新增');
      }
      navigate('/customers');
    } catch (error) {
      message.error(isEditMode ? '更新失敗' : '新增失敗');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" tip="載入中..." />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={2}>{isEditMode ? '編輯客戶' : '新增客戶'}</Title>
            </Col>
            <Col>
              <Space>
                <Button 
                  icon={<ArrowLeftOutlined />}
                  onClick={() => navigate('/customers')}
                >
                  返回列表
                </Button>
              </Space>
            </Col>
          </Row>

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            autoComplete="off"
          >
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="customer_code"
                  label="客戶編號"
                  rules={[{ required: true, message: '請輸入客戶編號' }]}
                >
                  <Input disabled={isEditMode} placeholder="輸入客戶編號" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="short_name"
                  label="客戶簡稱"
                  rules={[{ required: true, message: '請輸入客戶簡稱' }]}
                >
                  <Input placeholder="輸入客戶簡稱" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="full_name"
                  label="客戶全名"
                >
                  <Input placeholder="輸入客戶全名" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="invoice_title"
                  label="發票抬頭"
                >
                  <Input placeholder="輸入發票抬頭" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="address"
              label="地址"
              rules={[{ required: true, message: '請輸入地址' }]}
            >
              <TextArea rows={2} placeholder="輸入詳細地址" />
            </Form.Item>

            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="phone"
                  label="電話"
                  rules={[{ pattern: /^(0[2-9]-?\d{4}-?\d{4}|09\d{2}-?\d{3}-?\d{3})$/, message: '請輸入有效的電話號碼' }]}
                >
                  <Input placeholder="02-1234-5678 或 0912-345-678" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="email"
                  label="電子郵件"
                  rules={[{ type: 'email', message: '請輸入有效的電子郵件' }]}
                >
                  <Input type="email" placeholder="輸入電子郵件" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="customer_type"
                  label="客戶類型"
                >
                  <Select placeholder="選擇客戶類型">
                    <Option value="school">學校</Option>
                    <Option value="commercial">商業</Option>
                    <Option value="market">市場</Option>
                    <Option value="night_market">夜市</Option>
                    <Option value="food_truck">餐車</Option>
                    <Option value="catering">辦桌</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="area"
                  label="配送區域"
                >
                  <Select placeholder="選擇區域">
                    <Option value="A-瑞光">A-瑞光</Option>
                    <Option value="B-四維">B-四維</Option>
                    <Option value="C-漢中">C-漢中</Option>
                    <Option value="D-東方大鎮">D-東方大鎮</Option>
                    <Option value="E-力國">E-力國</Option>
                    <Option value="Y-富岡">Y-富岡</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="delivery_time"
                  label="配送時段"
                >
                  <TimePicker.RangePicker format="HH:mm" style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="payment_method"
                  label="付款方式"
                >
                  <Select placeholder="選擇付款方式">
                    <Option value="MONTHLY">月結</Option>
                    <Option value="CASH">現金</Option>
                    <Option value="TRANSFER">轉帳</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Title level={4}>瓦斯桶配置</Title>
            <Row gutter={16}>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="cylinders_50kg"
                  label="50kg瓦斯桶"
                  initialValue={0}
                >
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="cylinders_20kg"
                  label="20kg瓦斯桶"
                  initialValue={0}
                >
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="cylinders_16kg"
                  label="16kg瓦斯桶"
                  initialValue={0}
                >
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="cylinders_4kg"
                  label="4kg瓦斯桶"
                  initialValue={0}
                >
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Title level={4}>使用量設定</Title>
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="avg_daily_usage"
                  label="平均日使用量(kg)"
                  initialValue={0}
                >
                  <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="max_cycle_days"
                  label="最大週期(天)"
                  initialValue={30}
                >
                  <InputNumber min={1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="can_delay_days"
                  label="可延後天數"
                  initialValue={0}
                >
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Title level={4}>其他設定</Title>
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="is_active"
                  label="啟用狀態"
                  valuePropName="checked"
                  initialValue={true}
                >
                  <Switch checkedChildren="啟用" unCheckedChildren="停用" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="is_subscription"
                  label="訂閱式會員"
                  valuePropName="checked"
                  initialValue={false}
                >
                  <Switch />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="needs_same_day_delivery"
                  label="需要當天配送"
                  valuePropName="checked"
                  initialValue={false}
                >
                  <Switch />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="notes"
              label="備註"
            >
              <TextArea rows={3} placeholder="輸入備註資訊" />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  loading={submitting}
                  size="large"
                >
                  {isEditMode ? '更新' : '新增'}
                </Button>
                <Button
                  onClick={() => navigate('/customers')}
                  size="large"
                >
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Space>
      </Card>
    </div>
  );
};

export default CustomerForm;