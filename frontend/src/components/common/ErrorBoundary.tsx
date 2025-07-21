import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Result, Button } from 'antd';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error('ErrorBoundary caught error:', error, errorInfo);
    this.setState({
      error,
      errorInfo
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div data-testid="error-boundary">
          <Result
            status="error"
            title="發生錯誤"
            subTitle="很抱歉，應用程式發生錯誤。請重新載入頁面。"
            extra={
              <Button 
                type="primary" 
                onClick={this.handleReset}
                data-testid="reload-page-btn"
              >
                重新載入頁面
              </Button>
            }
          >
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div className="error-details" style={{ marginTop: 24, textAlign: 'left' }}>
                <details style={{ whiteSpace: 'pre-wrap' }}>
                  <summary>錯誤詳情</summary>
                  {this.state.error.toString()}
                  <br />
                  {this.state.errorInfo?.componentStack}
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

export default ErrorBoundary;