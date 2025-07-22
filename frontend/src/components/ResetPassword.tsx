import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Alert, Typography, Result } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authService } from '../services/auth.service';

const { Title } = Typography;

interface ResetPasswordForm {
  password: string;
  confirmPassword: string;
}

const ResetPassword: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [form] = Form.useForm();

  const token = searchParams.get('token');

  useEffect(() => {
    // Redirect to login if no token provided
    if (!token) {
      navigate('/login');
    }
  }, [token, navigate]);

  const onFinish = async (values: ResetPasswordForm) => {
    if (!token) {
      setError('無效的重設密碼連結');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      await authService.resetPassword(token, values.password);
      setSuccess(true);
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          '重設密碼失敗，請稍後再試';
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
            title="密碼重設成功"
            subTitle="您的密碼已成功重設，請使用新密碼登入"
            extra={[
              <Button key="login" type="primary" onClick={() => navigate('/login')}>
                前往登入頁面
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
          <Title level={5} type="secondary">重設密碼</Title>
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
          name="reset-password"
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
          size="large"
        >
          <Form.Item
            label="新密碼"
            name="password"
            rules={[
              { required: true, message: '請輸入新密碼' },
              { min: 8, message: '密碼長度至少8個字元' },
              {
                pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                message: '密碼必須包含大小寫字母、數字和特殊符號'
              }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="請輸入新密碼"
              autoComplete="new-password"
            />
          </Form.Item>

          <Form.Item
            label="確認新密碼"
            name="confirmPassword"
            dependencies={['password']}
            rules={[
              { required: true, message: '請確認新密碼' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('兩次輸入的密碼不一致'));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="請再次輸入新密碼"
              autoComplete="new-password"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              重設密碼
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default ResetPassword;