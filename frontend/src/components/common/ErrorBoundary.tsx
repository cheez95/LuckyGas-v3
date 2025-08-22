import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Result, Button, Typography, Space } from 'antd';
import { CloseCircleOutlined, ReloadOutlined, HomeOutlined } from '@ant-design/icons';
import { logReactError } from '../../services/safeErrorMonitor';

const { Paragraph, Text } = Typography;

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId?: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): State {
    // Generate error ID for tracking
    const errorId = `ERR-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    return { hasError: true, error, errorInfo: null, errorId };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { errorId } = this.state;
    
    // Log error with context
    console.error('ErrorBoundary caught error:', {
      errorId,
      error: error.toString(),
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    });
    
    // Use safe error monitoring with circuit breaker protection
    logReactError(error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });
  }


  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, errorId: undefined });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const isDevelopment = import.meta.env.DEV;
      const { error, errorInfo, errorId } = this.state;

      return (
        <div data-testid="error-boundary" style={{ 
          minHeight: '100vh', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          padding: '20px',
          backgroundColor: '#f0f2f5'
        }}>
          <Result
            status="error"
            icon={<CloseCircleOutlined style={{ fontSize: 72, color: '#ff4d4f' }} />}
            title="系統發生錯誤"
            subTitle={
              <Space direction="vertical" align="center">
                <Text>很抱歉，系統遇到了預期之外的錯誤。</Text>
                <Text type="secondary">錯誤代碼：{errorId}</Text>
              </Space>
            }
            extra={
              <Space>
                <Button 
                  type="primary" 
                  icon={<ReloadOutlined />}
                  onClick={this.handleReload}
                  data-testid="reload-page-btn"
                >
                  重新整理頁面
                </Button>
                <Button 
                  icon={<HomeOutlined />}
                  onClick={this.handleHome}
                  data-testid="go-home-btn"
                >
                  返回首頁
                </Button>
                <Button 
                  onClick={this.handleReset}
                  data-testid="retry-btn"
                >
                  重試
                </Button>
              </Space>
            }
          >
            {errorId && (
              <Paragraph type="secondary" style={{ marginTop: 20 }}>
                請將錯誤代碼 <Text code copyable>{errorId}</Text> 提供給技術支援人員
              </Paragraph>
            )}
            
            {isDevelopment && error && (
              <div className="error-details" style={{ marginTop: 24, textAlign: 'left' }}>
                <details style={{ whiteSpace: 'pre-wrap' }}>
                  <summary style={{ cursor: 'pointer', marginBottom: 10 }}>
                    <Text strong>錯誤詳情（開發模式）</Text>
                  </summary>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text type="secondary">錯誤訊息：</Text>
                      <Paragraph code style={{ marginTop: 5 }}>
                        {error.toString()}
                      </Paragraph>
                    </div>
                    {error.stack && (
                      <div>
                        <Text type="secondary">堆疊追蹤：</Text>
                        <Paragraph code style={{ marginTop: 5, fontSize: 12 }}>
                          {error.stack}
                        </Paragraph>
                      </div>
                    )}
                    {errorInfo?.componentStack && (
                      <div>
                        <Text type="secondary">元件堆疊：</Text>
                        <Paragraph code style={{ marginTop: 5, fontSize: 12 }}>
                          {errorInfo.componentStack}
                        </Paragraph>
                      </div>
                    )}
                  </Space>
                </details>
              </div>
            )}
          </Result>
        </div>
      );
    }

    return this.props.children;
  }
}

// Type declaration for error reporting service
declare global {
  interface Window {
    errorReporting?: {
      logError: (error: Error, context?: any) => void;
    };
  }
}

export default ErrorBoundary;