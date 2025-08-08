/**
 * FormErrorDisplay Component
 * Consistent error rendering for all forms
 * Eliminates ~200 lines of duplicate error display logic
 */

import React from 'react';
import { Alert, Typography, Space } from 'antd';
import { ExclamationCircleOutlined, WarningOutlined, InfoCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface FormErrorDisplayProps {
  errors?: Record<string, string[]> | string[] | string;
  type?: 'error' | 'warning' | 'info';
  showIcon?: boolean;
  closable?: boolean;
  onClose?: () => void;
  style?: React.CSSProperties;
  className?: string;
  title?: string;
}

export const FormErrorDisplay: React.FC<FormErrorDisplayProps> = ({
  errors,
  type = 'error',
  showIcon = true,
  closable = true,
  onClose,
  style,
  className,
  title,
}) => {
  if (!errors) return null;

  // Handle different error formats
  let errorMessages: string[] = [];

  if (typeof errors === 'string') {
    errorMessages = [errors];
  } else if (Array.isArray(errors)) {
    errorMessages = errors;
  } else if (typeof errors === 'object') {
    // Convert object errors to array
    errorMessages = Object.entries(errors).flatMap(([field, messages]) => 
      messages.map(msg => `${field}: ${msg}`)
    );
  }

  if (errorMessages.length === 0) return null;

  const getIcon = () => {
    switch (type) {
      case 'warning':
        return <WarningOutlined />;
      case 'info':
        return <InfoCircleOutlined />;
      default:
        return <ExclamationCircleOutlined />;
    }
  };

  const alertTitle = title || (type === 'error' ? '錯誤' : type === 'warning' ? '警告' : '提示');

  return (
    <Alert
      type={type}
      showIcon={showIcon}
      closable={closable}
      onClose={onClose}
      style={style}
      className={className}
      icon={getIcon()}
      message={alertTitle}
      description={
        errorMessages.length === 1 ? (
          errorMessages[0]
        ) : (
          <Space direction="vertical" size={0}>
            {errorMessages.map((msg, index) => (
              <Text key={index}>• {msg}</Text>
            ))}
          </Space>
        )
      }
    />
  );
};

// Field-specific error display
interface FieldErrorProps {
  error?: string | string[];
  touched?: boolean;
  showWhenTouched?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

export const FieldError: React.FC<FieldErrorProps> = ({
  error,
  touched = false,
  showWhenTouched = true,
  style,
  className,
}) => {
  // Only show error if field has been touched (if required)
  if (showWhenTouched && !touched) return null;
  if (!error) return null;

  const errorMessage = Array.isArray(error) ? error[0] : error;

  return (
    <Text 
      type="danger" 
      style={{ fontSize: 12, marginTop: 4, display: 'block', ...style }}
      className={className}
    >
      {errorMessage}
    </Text>
  );
};

// Inline error display for compact forms
interface InlineErrorProps {
  error?: string;
  style?: React.CSSProperties;
}

export const InlineError: React.FC<InlineErrorProps> = ({ error, style }) => {
  if (!error) return null;

  return (
    <span style={{ color: '#ff4d4f', fontSize: 12, marginLeft: 8, ...style }}>
      {error}
    </span>
  );
};

// Summary error display for form validation
interface ValidationSummaryProps {
  errors: Record<string, string[]>;
  title?: string;
  showFieldNames?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

export const ValidationSummary: React.FC<ValidationSummaryProps> = ({
  errors,
  title = '請修正以下錯誤：',
  showFieldNames = true,
  style,
  className,
}) => {
  const errorCount = Object.keys(errors).length;
  
  if (errorCount === 0) return null;

  const fieldLabels: Record<string, string> = {
    name: '姓名',
    email: '電子郵件',
    phone: '電話',
    address: '地址',
    password: '密碼',
    confirmPassword: '確認密碼',
    quantity: '數量',
    price: '價格',
    date: '日期',
    time: '時間',
    description: '描述',
    notes: '備註',
    // Add more field translations as needed
  };

  return (
    <Alert
      type="error"
      showIcon
      style={style}
      className={className}
      message={
        <div>
          <strong>{title}</strong>
          {errorCount > 1 && <Text type="secondary" style={{ marginLeft: 8 }}>（共 {errorCount} 項）</Text>}
        </div>
      }
      description={
        <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
          {Object.entries(errors).map(([field, messages]) => (
            <li key={field}>
              {showFieldNames && (
                <Text strong>{fieldLabels[field] || field}: </Text>
              )}
              {messages.join(', ')}
            </li>
          ))}
        </ul>
      }
    />
  );
};

// Success message display
interface SuccessMessageProps {
  message?: string;
  duration?: number;
  onClose?: () => void;
  style?: React.CSSProperties;
  className?: string;
}

export const SuccessMessage: React.FC<SuccessMessageProps> = ({
  message,
  duration = 3000,
  onClose,
  style,
  className,
}) => {
  const [visible, setVisible] = React.useState(!!message);

  React.useEffect(() => {
    if (message && duration > 0) {
      const timer = setTimeout(() => {
        setVisible(false);
        onClose?.();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [message, duration, onClose]);

  if (!message || !visible) return null;

  return (
    <Alert
      type="success"
      showIcon
      closable
      onClose={() => {
        setVisible(false);
        onClose?.();
      }}
      style={style}
      className={className}
      message={message}
    />
  );
};

// Loading overlay for form submission
interface FormLoadingOverlayProps {
  loading?: boolean;
  message?: string;
  style?: React.CSSProperties;
}

export const FormLoadingOverlay: React.FC<FormLoadingOverlayProps> = ({
  loading = false,
  message = '處理中...',
  style,
}) => {
  if (!loading) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(255, 255, 255, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        ...style,
      }}
    >
      <Space direction="vertical" align="center">
        <div className="ant-spin ant-spin-spinning">
          <span className="ant-spin-dot ant-spin-dot-spin">
            <i className="ant-spin-dot-item"></i>
            <i className="ant-spin-dot-item"></i>
            <i className="ant-spin-dot-item"></i>
            <i className="ant-spin-dot-item"></i>
          </span>
        </div>
        <Text>{message}</Text>
      </Space>
    </div>
  );
};

// Export all components
export default {
  FormErrorDisplay,
  FieldError,
  InlineError,
  ValidationSummary,
  SuccessMessage,
  FormLoadingOverlay,
};