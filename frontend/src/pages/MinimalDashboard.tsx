import React, { useState, useEffect } from 'react';
import { Card, Alert, Button, Space, Typography } from 'antd';
import { CheckCircleOutlined, WarningOutlined } from '@ant-design/icons';
import api from '../services/api';

const { Title, Text } = Typography;

const MinimalDashboard: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    if (token) {
      // Decode token to get user info (basic implementation)
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser({
          email: payload.sub,
          role: payload.role,
        });
      } catch (err) {
        console.error('Failed to decode token:', err);
        setError('無法解析用戶資訊');
      }
    } else {
      setError('未登入');
    }
  }, []);
  
  const testAPI = async () => {
    setIsLoading(true);
    setError(null);
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      setError('請先登入');
      setIsLoading(false);
      return;
    }
    
    try {
      const response = await api.get('/auth/me');
      
      if (response.ok) {
        const data = await response.json();
        setUser(data);
        setError(null);
      } else {
        setError(`API 錯誤: ${response.status}`);
      }
    } catch (err: any) {
      setError(`網絡錯誤: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Title level={2}>最小化儀表板</Title>
      
      {error && (
        <Alert
          message="錯誤"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}
      
      <Card title="系統狀態" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            <Text>前端已部署</Text>
          </div>
          
          <div>
            {localStorage.getItem('access_token') ? (
              <>
                <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                <Text>已登入</Text>
              </>
            ) : (
              <>
                <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
                <Text>未登入</Text>
              </>
            )}
          </div>
          
          {user && (
            <div style={{ marginTop: 16, padding: 16, background: '#f0f2f5', borderRadius: 8 }}>
              <Title level={5}>用戶資訊</Title>
              <div>Email: {user.email || user.username}</div>
              <div>角色: {user.role}</div>
              <div>姓名: {user.full_name || 'N/A'}</div>
            </div>
          )}
        </Space>
      </Card>
      
      <Card title="測試功能" style={{ marginBottom: 16 }}>
        <Space>
          <Button 
            type="primary" 
            onClick={testAPI}
            loading={isLoading}
          >
            測試 API 連接
          </Button>
          
          <Button 
            onClick={() => {
              localStorage.removeItem('access_token');
              window.location.reload();
            }}
          >
            登出
          </Button>
        </Space>
      </Card>
      
      <Card title="偵錯資訊">
        <pre style={{ fontSize: 12, overflow: 'auto' }}>
          {JSON.stringify({
            hasToken: !!localStorage.getItem('access_token'),
            tokenLength: localStorage.getItem('access_token')?.length || 0,
            currentUrl: window.location.href,
            apiUrl: api.defaults.baseURL || 'http://localhost:8000/api/v1',
          }, null, 2)}
        </pre>
      </Card>
    </div>
  );
};

export default MinimalDashboard;