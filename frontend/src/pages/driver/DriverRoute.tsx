import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, Typography, List, Tag, Modal, Form, Input, Select, Upload, message, Divider, Progress } from 'antd';
import {
  ArrowLeftOutlined,
  EnvironmentOutlined,
  PhoneOutlined,
  CheckCircleOutlined,
  CameraOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  MessageOutlined,
  AimOutlined
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import SignaturePad from 'react-signature-canvas';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface Delivery {
  id: string;
  customerName: string;
  address: string;
  phone: string;
  products: Array<{
    name: string;
    quantity: number;
  }>;
  notes?: string;
  status: 'pending' | 'arrived' | 'delivered' | 'failed';
  sequence: number;
}

interface RouteDetails {
  id: string;
  name: string;
  totalDeliveries: number;
  completedDeliveries: number;
  estimatedDuration: string;
  totalDistance: number;
  deliveries: Delivery[];
}

const DriverRoute: React.FC = () => {
  const { routeId } = useParams<{ routeId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  
  const [route, setRoute] = useState<RouteDetails | null>(null);
  const [currentDeliveryIndex, setCurrentDeliveryIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [completionModalVisible, setCompletionModalVisible] = useState(false);
  const [issueModalVisible, setIssueModalVisible] = useState(false);
  const [signaturePad, setSignaturePad] = useState<any>(null);
  const [deliveryPhoto, setDeliveryPhoto] = useState<UploadFile[]>([]);
  const [form] = Form.useForm();
  const [issueForm] = Form.useForm();
  const [isNavigating, setIsNavigating] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);

  useEffect(() => {
    fetchRouteDetails();
  }, [routeId]);

  const fetchRouteDetails = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/driver/routes/${routeId}`);
      setRoute(response.data);
    } catch (error) {
      console.error('Failed to fetch route:', error);
      message.error('無法載入路線資料');
    } finally {
      setLoading(false);
    }
  };

  const currentDelivery = route?.deliveries[currentDeliveryIndex];

  const handleArrive = async () => {
    if (!currentDelivery) return;
    
    try {
      await api.post(`/deliveries/status/${currentDelivery.id}`, {
        status: 'arrived'
      });
      
      // Update local state
      if (route) {
        const updatedDeliveries = [...route.deliveries];
        updatedDeliveries[currentDeliveryIndex].status = 'arrived';
        setRoute({ ...route, deliveries: updatedDeliveries });
      }
      
      message.success('已抵達客戶位置');
    } catch (error) {
      message.error('更新狀態失敗');
    }
  };

  const handleDeliveryComplete = () => {
    setCompletionModalVisible(true);
  };

  const handleCompletionSubmit = async (values: any) => {
    if (!currentDelivery) return;
    
    try {
      const formData = new FormData();
      formData.append('recipient_name', values.recipientName || currentDelivery.customerName);
      formData.append('notes', values.notes || '');
      
      // Add signature if available
      if (signaturePad && !signaturePad.isEmpty()) {
        formData.append('signature', signaturePad.toDataURL());
      }
      
      // Add photo if available
      if (deliveryPhoto.length > 0 && deliveryPhoto[0].originFileObj) {
        formData.append('photo', deliveryPhoto[0].originFileObj);
      }
      
      await api.post(`/deliveries/confirm/${currentDelivery.id}`, formData);
      
      message.success('配送完成');
      setCompletionModalVisible(false);
      
      // Move to next delivery or complete route
      if (currentDeliveryIndex < route!.deliveries.length - 1) {
        setCurrentDeliveryIndex(currentDeliveryIndex + 1);
      } else {
        Modal.success({
          title: '路線完成',
          content: '您已完成所有配送！',
          onOk: () => navigate('/driver')
        });
      }
    } catch (error) {
      message.error('確認配送失敗');
    }
  };

  const handleReportIssue = () => {
    setIssueModalVisible(true);
  };

  const handleIssueSubmit = async (values: any) => {
    if (!currentDelivery) return;
    
    try {
      await api.post(`/deliveries/status/${currentDelivery.id}`, {
        status: 'failed',
        notes: values.notes,
        issue_type: values.issueType
      });
      
      message.warning('已回報問題');
      setIssueModalVisible(false);
      
      // Move to next delivery
      if (currentDeliveryIndex < route!.deliveries.length - 1) {
        setCurrentDeliveryIndex(currentDeliveryIndex + 1);
      }
    } catch (error) {
      message.error('回報失敗');
    }
  };

  const handleCallCustomer = () => {
    if (currentDelivery?.phone) {
      window.location.href = `tel:${currentDelivery.phone}`;
    }
  };

  const handleSendSMS = async (template: string) => {
    if (!currentDelivery) return;
    
    try {
      await api.post('/communications/sms', {
        phone: currentDelivery.phone,
        template: template,
        order_id: currentDelivery.id
      });
      
      message.success('簡訊已發送');
    } catch (error) {
      message.error('簡訊發送失敗');
    }
  };

  const handleStartNavigation = () => {
    setIsNavigating(true);
    // In real app, this would integrate with maps API
    message.info('導航已開始');
  };

  const handleVoiceToggle = () => {
    setVoiceEnabled(!voiceEnabled);
    message.info(voiceEnabled ? '語音導航已關閉' : '語音導航已開啟');
  };

  if (!route || !currentDelivery) {
    return <div>載入中...</div>;
  }

  const progress = ((currentDeliveryIndex + 1) / route.deliveries.length) * 100;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f0f2f5' }}>
      {/* Header */}
      <Card size="small" style={{ borderRadius: 0 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate('/driver')}
          >
            返回
          </Button>
          <Title level={5} style={{ margin: 0 }}>{route.name}</Title>
          <Tag color="blue">
            {currentDeliveryIndex + 1} / {route.totalDeliveries}
          </Tag>
        </Space>
        <Progress percent={progress} showInfo={false} style={{ marginTop: 8 }} />
      </Card>

      {/* Navigation Controls */}
      {isNavigating && (
        <Card size="small" style={{ margin: '8px 16px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div data-testid="navigation-instruction">
              <Text strong>300公尺後左轉進入忠孝東路</Text>
            </div>
            <Space>
              <Text type="secondary" data-testid="distance-to-turn">300公尺</Text>
              <Divider type="vertical" />
              <Text type="secondary" data-testid="eta">預計 5 分鐘</Text>
            </Space>
            <Button 
              size="small"
              onClick={handleVoiceToggle}
              data-testid="voice-navigation-toggle"
            >
              {voiceEnabled ? '關閉語音' : '開啟語音'}
            </Button>
            {voiceEnabled && (
              <Tag color="green" data-testid="voice-enabled-indicator">
                語音導航中
              </Tag>
            )}
          </Space>
        </Card>
      )}

      {/* Current Delivery */}
      <Card 
        style={{ margin: 16 }}
        data-testid="current-delivery"
        title={
          <Space>
            <EnvironmentOutlined />
            <span data-testid="customer-name">{currentDelivery.customerName}</span>
            {currentDelivery.status === 'arrived' && (
              <Tag color="orange">已抵達</Tag>
            )}
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Paragraph data-testid="delivery-address">
            {currentDelivery.address}
          </Paragraph>
          
          <div data-testid="delivery-products">
            <Text strong>配送商品：</Text>
            <List
              size="small"
              dataSource={currentDelivery.products}
              renderItem={item => (
                <List.Item>
                  {item.name} x {item.quantity}
                </List.Item>
              )}
            />
          </div>
          
          {currentDelivery.notes && (
            <div>
              <Text strong>備註：</Text>
              <Paragraph>{currentDelivery.notes}</Paragraph>
            </div>
          )}
          
          {/* Action Buttons */}
          <Space wrap style={{ width: '100%' }}>
            <Button 
              icon={<PhoneOutlined />}
              onClick={handleCallCustomer}
              data-testid="call-customer-button"
            >
              撥打電話
            </Button>
            <Button 
              icon={<MessageOutlined />}
              onClick={() => handleSendSMS('arriving')}
              data-testid="sms-customer-button"
            >
              發送簡訊
            </Button>
            {!isNavigating && (
              <Button
                icon={<AimOutlined />}
                onClick={handleStartNavigation}
                data-testid="start-navigation-button"
              >
                開始導航
              </Button>
            )}
          </Space>
          
          <Divider />
          
          {/* Delivery Actions */}
          {currentDelivery.status === 'pending' && (
            <Button 
              type="primary" 
              size="large" 
              block
              onClick={handleArrive}
              data-testid="arrived-button"
            >
              抵達客戶位置
            </Button>
          )}
          
          {currentDelivery.status === 'arrived' && (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button 
                type="primary" 
                size="large" 
                block
                icon={<CheckCircleOutlined />}
                onClick={handleDeliveryComplete}
                data-testid="delivered-button"
              >
                確認送達
              </Button>
              <Button 
                danger 
                size="large" 
                block
                icon={<ExclamationCircleOutlined />}
                onClick={handleReportIssue}
                data-testid="report-issue-button"
              >
                回報問題
              </Button>
            </Space>
          )}
        </Space>
      </Card>

      {/* Completion Modal */}
      <Modal
        title="確認配送完成"
        open={completionModalVisible}
        onCancel={() => setCompletionModalVisible(false)}
        footer={null}
        data-testid="delivery-completion-modal"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCompletionSubmit}
        >
          <Form.Item
            label="收件人姓名"
            name="recipientName"
            initialValue={currentDelivery?.customerName}
          >
            <Input />
          </Form.Item>
          
          <Form.Item label="簽名">
            <div style={{ border: '1px solid #d9d9d9', borderRadius: 4 }}>
              <SignaturePad
                ref={(ref: any) => setSignaturePad(ref)}
                canvasProps={{
                  width: 400,
                  height: 200,
                  className: 'signature-canvas',
                  'data-testid': 'signature-canvas'
                }}
              />
            </div>
            <Button 
              size="small" 
              onClick={() => signaturePad?.clear()}
              style={{ marginTop: 8 }}
            >
              清除
            </Button>
          </Form.Item>
          
          <Form.Item label="拍照存證">
            <Upload
              listType="picture-card"
              fileList={deliveryPhoto}
              onChange={({ fileList }) => setDeliveryPhoto(fileList)}
              beforeUpload={() => false}
              maxCount={1}
            >
              <div>
                <CameraOutlined />
                <div style={{ marginTop: 8 }}>拍照</div>
              </div>
            </Upload>
          </Form.Item>
          
          <Form.Item
            label="配送備註"
            name="notes"
          >
            <TextArea 
              rows={3} 
              data-testid="delivery-notes"
              placeholder="例如：已交付給警衛室"
            />
          </Form.Item>
          
          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Button onClick={() => setCompletionModalVisible(false)}>
                取消
              </Button>
              <Button 
                type="primary" 
                htmlType="submit"
                data-testid="confirm-delivery-button"
              >
                確認完成
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Issue Modal */}
      <Modal
        title="回報配送問題"
        open={issueModalVisible}
        onCancel={() => setIssueModalVisible(false)}
        footer={null}
      >
        <Form
          form={issueForm}
          layout="vertical"
          onFinish={handleIssueSubmit}
        >
          <Form.Item
            label="問題類型"
            name="issueType"
            rules={[{ required: true, message: '請選擇問題類型' }]}
          >
            <Select data-testid="issue-type">
              <Select.Option value="absent" data-testid="issue-type-absent">
                客戶不在
              </Select.Option>
              <Select.Option value="rejected" data-testid="issue-type-rejected">
                客戶拒收
              </Select.Option>
              <Select.Option value="wrong_address">地址錯誤</Select.Option>
              <Select.Option value="access_issue">無法進入</Select.Option>
              <Select.Option value="other">其他</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="問題說明"
            name="notes"
            rules={[{ required: true, message: '請說明問題詳情' }]}
          >
            <TextArea 
              rows={4} 
              data-testid="issue-notes"
              placeholder="請詳細說明遇到的問題"
            />
          </Form.Item>
          
          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Button onClick={() => setIssueModalVisible(false)}>
                取消
              </Button>
              <Button 
                type="primary" 
                htmlType="submit"
                data-testid="submit-issue-button"
              >
                提交
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DriverRoute;