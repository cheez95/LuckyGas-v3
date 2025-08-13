import React, { lazy, Suspense, ComponentType, LazyExoticComponent } from 'react';
import { Spin, Result, Button } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

interface LazyLoadComponentProps {
  fallback?: React.ReactNode;
  errorFallback?: React.ComponentType<{ error: Error; resetError: () => void }>;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

// Error Boundary Component
class ErrorBoundary extends React.Component<
  {
    children: React.ReactNode;
    fallback?: React.ComponentType<{ error: Error; resetError: () => void }>;
  },
  ErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Component Error:', error, errorInfo);
  }

  resetError = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback;
      
      if (FallbackComponent && this.state.error) {
        return <FallbackComponent error={this.state.error} resetError={this.resetError} />;
      }

      // Default error fallback
      return (
        <Result
          status="error"
          title="載入失敗"
          subTitle="組件載入時發生錯誤，請重新整理頁面或稍後再試。"
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              重新整理頁面
            </Button>
          }
        />
      );
    }

    return this.props.children;
  }
}

// Default Loading Component
const DefaultLoadingComponent: React.FC = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '400px',
    width: '100%'
  }}>
    <Spin
      indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />}
      tip="載入中..."
      size="large"
    />
  </div>
);

// Lazy Load Wrapper Function
export function lazyLoadComponent<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  options?: LazyLoadComponentProps
): LazyExoticComponent<T> {
  const LazyComponent = lazy(importFunc);

  const WrappedComponent = (props: any) => (
    <ErrorBoundary fallback={options?.errorFallback}>
      <Suspense fallback={options?.fallback || <DefaultLoadingComponent />}>
        <LazyComponent {...props} />
      </Suspense>
    </ErrorBoundary>
  );

  // Set display name for debugging
  WrappedComponent.displayName = `LazyLoad(${LazyComponent.displayName || 'Component'})`;

  return WrappedComponent as any;
}

// Retry mechanism for failed imports
export function lazyLoadWithRetry<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  retries = 3,
  delay = 1000
): () => Promise<{ default: T }> {
  return async () => {
    let lastError;
    
    for (let i = 0; i < retries; i++) {
      try {
        return await importFunc();
      } catch (error) {
        lastError = error;
        console.warn(`Failed to load component (attempt ${i + 1}/${retries}):`, error);
        
        if (i < retries - 1) {
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    
    throw lastError;
  };
}

// Export convenience function for dashboard components
export function lazyLoadDashboard<T extends ComponentType<any>>(
  componentPath: string
): LazyExoticComponent<T> {
  return lazyLoadComponent<T>(
    lazyLoadWithRetry(() => import(componentPath)),
    {
      fallback: <DefaultLoadingComponent />,
    }
  );
}

export default lazyLoadComponent;