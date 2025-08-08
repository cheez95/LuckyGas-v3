import React, { ReactNode, useEffect, useState } from 'react';
import {
  Modal,
  Button,
  Form,
  Alert,
  Space,
  Spin,
  Typography,
  Divider,
} from 'antd';
import {
  ExclamationCircleOutlined,
  CloseOutlined,
  CheckOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { FormInstance } from 'antd/es/form';
import { useTranslation } from 'react-i18next';

const { Title } = Typography;

export interface BaseModalAction {
  key: string;
  label: string;
  type?: 'primary' | 'default' | 'dashed' | 'text' | 'link';
  danger?: boolean;
  icon?: ReactNode;
  loading?: boolean;
  disabled?: boolean;
  onClick: () => void | Promise<void>;
}

export interface BaseModalProps {
  // Basic modal props
  open: boolean;
  onClose: () => void;
  title: string | ReactNode;
  width?: number | string;
  centered?: boolean;
  closable?: boolean;
  maskClosable?: boolean;
  keyboard?: boolean;
  
  // Content
  children: ReactNode;
  
  // Loading states
  loading?: boolean;
  submitting?: boolean;
  
  // Form integration
  form?: FormInstance;
  onSubmit?: (values: any) => void | Promise<void>;
  validateOnSubmit?: boolean;
  resetFormOnClose?: boolean;
  
  // Actions/Footer
  showFooter?: boolean;
  actions?: BaseModalAction[];
  okText?: string;
  cancelText?: string;
  onOk?: () => void | Promise<void>;
  onCancel?: () => void;
  showOkButton?: boolean;
  showCancelButton?: boolean;
  okButtonProps?: any;
  cancelButtonProps?: any;
  
  // Error handling
  error?: string | null;
  showErrorAlert?: boolean;
  onErrorDismiss?: () => void;
  
  // Success handling
  success?: string | null;
  showSuccessAlert?: boolean;
  onSuccessDismiss?: () => void;
  
  // Confirmation
  requireConfirmation?: boolean;
  confirmationTitle?: string;
  confirmationContent?: string;
  
  // Validation
  validationErrors?: Record<string, string[]>;
  showValidationSummary?: boolean;
  
  // Sizing presets
  size?: 'small' | 'medium' | 'large' | 'extra-large';
  
  // Custom styling
  className?: string;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
  
  // Advanced features
  destroyOnClose?: boolean;
  forceRender?: boolean;
  getContainer?: string | HTMLElement | (() => HTMLElement) | false;
  
  // Header customization
  showCloseIcon?: boolean;
  headerActions?: ReactNode;
  subtitle?: string | ReactNode;
  
  // Footer customization
  footerActions?: ReactNode;
  
  // Lifecycle hooks
  onAfterOpen?: () => void;
  onAfterClose?: () => void;
}

const BaseModal: React.FC<BaseModalProps> = ({
  open,
  onClose,
  title,
  width,
  centered = true,
  closable = true,
  maskClosable = false,
  keyboard = true,
  children,
  loading = false,
  submitting = false,
  form,
  onSubmit,
  validateOnSubmit = true,
  resetFormOnClose = true,
  showFooter = true,
  actions = [],
  okText,
  cancelText,
  onOk,
  onCancel,
  showOkButton = true,
  showCancelButton = true,
  okButtonProps = {},
  cancelButtonProps = {},
  error,
  showErrorAlert = true,
  onErrorDismiss,
  success,
  showSuccessAlert = true,
  onSuccessDismiss,
  requireConfirmation = false,
  confirmationTitle = 'Confirm Action',
  confirmationContent = 'Are you sure you want to proceed?',
  validationErrors,
  showValidationSummary = true,
  size = 'medium',
  className,
  style,
  bodyStyle,
  destroyOnClose = false,
  forceRender = false,
  getContainer,
  showCloseIcon = true,
  headerActions,
  subtitle,
  footerActions,
  onAfterOpen,
  onAfterClose,
}) => {
  const { t } = useTranslation();
  const [internalSubmitting, setInternalSubmitting] = useState(false);
  
  // Size mapping
  const sizeMapping = {
    small: 400,
    medium: 600,
    large: 800,
    'extra-large': 1000,
  };
  
  const modalWidth = width || sizeMapping[size];
  
  // Handle form submission
  const handleSubmit = async () => {
    if (!form || !onSubmit) return;
    
    try {
      setInternalSubmitting(true);
      
      if (validateOnSubmit) {
        const values = await form.validateFields();
        await onSubmit(values);
      } else {
        const values = form.getFieldsValue();
        await onSubmit(values);
      }
    } catch (error) {
      console.error('Form submission error:', error);
      // Error handling is managed by parent component through error prop
    } finally {
      setInternalSubmitting(false);
    }
  };
  
  // Handle OK button click
  const handleOk = async () => {
    if (form && onSubmit) {
      await handleSubmit();
    } else if (onOk) {
      if (requireConfirmation) {
        Modal.confirm({
          title: confirmationTitle,
          content: confirmationContent,
          icon: <ExclamationCircleOutlined />,
          okText: t('common.confirm', 'Confirm'),
          cancelText: t('common.cancel', 'Cancel'),
          onOk: async () => {
            await onOk();
          },
        });
      } else {
        await onOk();
      }
    }
  };
  
  // Handle cancel/close
  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      onClose();
    }
    
    if (resetFormOnClose && form) {
      form.resetFields();
    }
  };
  
  // Reset form when modal opens
  useEffect(() => {
    if (open && form && resetFormOnClose) {
      // Don't reset immediately when opening, only when closing
      return;
    }
  }, [open, form, resetFormOnClose]);
  
  // Render header with custom actions
  const renderTitle = () => {
    if (typeof title === 'string') {
      return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {title}
            </Title>
            {subtitle && (
              <div style={{ fontSize: '14px', color: '#666', marginTop: '4px' }}>
                {subtitle}
              </div>
            )}
          </div>
          {headerActions && (
            <div style={{ marginLeft: '16px' }}>
              {headerActions}
            </div>
          )}
        </div>
      );
    }
    
    return title;
  };
  
  // Render validation errors summary
  const renderValidationSummary = () => {
    if (!validationErrors || !showValidationSummary || Object.keys(validationErrors).length === 0) {
      return null;
    }
    
    const errorMessages = Object.values(validationErrors).flat();
    
    return (
      <Alert
        type="error"
        message="Validation Errors"
        description={
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {errorMessages.map((message, index) => (
              <li key={index}>{message}</li>
            ))}
          </ul>
        }
        style={{ marginBottom: 16 }}
        showIcon
      />
    );
  };
  
  // Render error alert
  const renderErrorAlert = () => {
    if (!error || !showErrorAlert) return null;
    
    return (
      <Alert
        type="error"
        message="Error"
        description={error}
        style={{ marginBottom: 16 }}
        showIcon
        closable={!!onErrorDismiss}
        onClose={onErrorDismiss}
      />
    );
  };
  
  // Render success alert
  const renderSuccessAlert = () => {
    if (!success || !showSuccessAlert) return null;
    
    return (
      <Alert
        type="success"
        message="Success"
        description={success}
        style={{ marginBottom: 16 }}
        showIcon
        closable={!!onSuccessDismiss}
        onClose={onSuccessDismiss}
      />
    );
  };
  
  // Render footer
  const renderFooter = () => {
    if (!showFooter) return null;
    
    const defaultActions: BaseModalAction[] = [];
    
    if (showCancelButton) {
      defaultActions.push({
        key: 'cancel',
        label: cancelText || t('common.cancel', 'Cancel'),
        onClick: handleCancel,
        ...cancelButtonProps,
      });
    }
    
    if (showOkButton) {
      defaultActions.push({
        key: 'ok',
        label: okText || (form && onSubmit ? t('common.save', 'Save') : t('common.ok', 'OK')),
        type: 'primary',
        loading: submitting || internalSubmitting,
        onClick: handleOk,
        ...okButtonProps,
      });
    }
    
    const allActions = [...actions, ...defaultActions];
    
    return (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>{footerActions}</div>
        <Space>
          {allActions.map((action) => (
            <Button
              key={action.key}
              type={action.type}
              danger={action.danger}
              icon={action.icon}
              loading={action.loading}
              disabled={action.disabled}
              onClick={action.onClick}
              {...(action.key === 'ok' ? okButtonProps : {})}
              {...(action.key === 'cancel' ? cancelButtonProps : {})}
            >
              {action.label}
            </Button>
          ))}
        </Space>
      </div>
    );
  };
  
  return (
    <Modal
      title={renderTitle()}
      open={open}
      onCancel={handleCancel}
      width={modalWidth}
      centered={centered}
      closable={closable && showCloseIcon}
      maskClosable={maskClosable}
      keyboard={keyboard}
      footer={renderFooter()}
      className={className}
      style={style}
      bodyStyle={bodyStyle}
      destroyOnClose={destroyOnClose}
      forceRender={forceRender}
      getContainer={getContainer}
      afterClose={onAfterClose}
      afterOpenChange={(open) => {
        if (open && onAfterOpen) {
          onAfterOpen();
        }
      }}
    >
      <Spin spinning={loading} indicator={<LoadingOutlined style={{ fontSize: 24 }} />}>
        <div className="base-modal-content">
          {renderSuccessAlert()}
          {renderErrorAlert()}
          {renderValidationSummary()}
          
          {children}
        </div>
      </Spin>
    </Modal>
  );
};

export default BaseModal;