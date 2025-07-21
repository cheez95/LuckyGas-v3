import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Alert, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { LoginRequest } from '../types/auth';

const { Title } = Typography;

const Login: React.FC = () => {
  const { t } = useTranslation();
  const { login, error, clearError } = useAuth();
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  // Navigation is handled by AuthContext after successful login
  // const from = location.state?.from?.pathname || '/dashboard';

  useEffect(() => {
    // Clear error when component unmounts
    return () => {
      clearError();
    };
  }, [clearError]);

  const onFinish = async (values: LoginRequest) => {
    setLoading(true);
    setLocalError(null);
    try {
      await login(values);
    } catch (error: any) {
      // Handle error locally if login throws
      const errorMessage = error?.response?.data?.detail || 
                          error?.message || 
                          '登入失敗，請稍後再試';
      setLocalError(errorMessage);
    }
    setLoading(false);
  };

  return (
    <div className="login-container">
      <Card className="login-box">
        <div className="login-logo">
          <Title level={2} data-testid="login-title">{t('app.title')}</Title>
          <Title level={5} type="secondary">{t('app.shortTitle')}</Title>
        </div>
        
        {(error || localError) && (
          <Alert
            data-testid="error-alert"
            message={error || localError}
            type="error"
            showIcon
            closable
            onClose={() => {
              clearError();
              setLocalError(null);
            }}
            style={{ marginBottom: 16 }}
          />
        )}
        
        <Form
          name="login"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
          size="large"
        >
          <Form.Item
            label={t('auth.username')}
            name="username"
            rules={[{ required: true, message: t('validation.username.required') }]}
          >
            <Input
              data-testid="username-input"
              prefix={<UserOutlined />}
              placeholder={t('auth.username')}
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            label={t('auth.password')}
            name="password"
            rules={[{ required: true, message: t('validation.password.required') }]}
          >
            <Input.Password
              data-testid="password-input"
              prefix={<LockOutlined />}
              placeholder={t('auth.password')}
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item>
            <Button
              data-testid="login-button"
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              {t('auth.login')}
            </Button>
          </Form.Item>
        </Form>
        
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Typography.Text type="secondary">
            © 2025 {t('app.shortTitle')} - {t('app.title')}
          </Typography.Text>
        </div>
      </Card>
    </div>
  );
};

export default Login;