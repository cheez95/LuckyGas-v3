import React, { useState } from 'react';
import { Form, Input, Button, Card, Alert, Typography, Result } from 'antd';
import { MailOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/auth.service';

const { Title, Text } = Typography;

const ForgotPassword: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [form] = Form.useForm();

  const onFinish = async (values: { email: string }) => {
    setLoading(true);
    setError(null);
    
    try {
      await authService.requestPasswordReset(values.email);
      setSuccess(true);
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          '發送重設密碼郵件失敗，請稍後再試';
      setError(errorMessage);
    }
    
    setLoading(false);
  };

  if (success) {
    return (
      <div className="login-container">
        <Card className="login-box">
          <Result
            status="success"
            title="重設密碼郵件已發送"
            subTitle="請檢查您的電子郵件信箱，並按照郵件中的指示重設密碼"
            extra={[
              <Button key="back" onClick={() => navigate('/login')}>
                返回登入頁面
              </Button>
            ]}
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="login-container">
      <Card className="login-box">
        <div className="login-logo">
          <Title level={2}>{t('app.title')}</Title>
          <Title level={5} type="secondary">忘記密碼</Title>
        </div>
        
        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            closable
            onClose={() => setError(null)}
            style={{ marginBottom: 16 }}
          />
        )}
        
        <Form
          form={form}
          name="forgot-password"
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
          size="large"
        >
          <Form.Item
            label="電子郵件"
            name="email"
            rules={[
              { required: true, message: '請輸入您的電子郵件' },
              { type: 'email', message: '請輸入有效的電子郵件地址' }
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="請輸入註冊時使用的電子郵件"
              autoComplete="email"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              發送重設密碼郵件
            </Button>
          </Form.Item>

          <Form.Item>
            <Button
              type="link"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/login')}
              block
            >
              返回登入頁面
            </Button>
          </Form.Item>
        </Form>
        
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Text type="secondary">
            如果您沒有收到郵件，請檢查垃圾郵件資料夾或聯絡系統管理員
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default ForgotPassword;