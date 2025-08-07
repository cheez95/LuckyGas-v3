/**
 * Accessible form components with ARIA support and keyboard navigation
 */

import React, { forwardRef, useId, useState, useEffect } from 'react';
import { Form, Input, Select, DatePicker, Radio, Checkbox, Button, InputNumber } from 'antd';
import type { FormItemProps, InputProps, SelectProps } from 'antd';
import { InfoCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useFormErrorAnnouncement } from '../../hooks/useAccessibility';
import { generateId, AriaUtils, focusStyles } from '../../utils/accessibility';

interface AccessibleFormItemProps extends FormItemProps {
  helpText?: string;
  errorText?: string;
  required?: boolean;
  showRequiredIndicator?: boolean;
}

/**
 * Accessible form item with proper ARIA attributes
 */
export const AccessibleFormItem: React.FC<AccessibleFormItemProps> = ({
  children,
  label,
  name,
  helpText,
  errorText,
  required = false,
  showRequiredIndicator = true,
  ...props
}) => {
  const id = useId();
  const helpId = helpText ? `${id}-help` : undefined;
  const errorId = errorText ? `${id}-error` : undefined;

  return (
    <Form.Item
      {...props}
      label={
        label && (
          <span>
            {label}
            {required && showRequiredIndicator && (
              <span 
                className="required-indicator" 
                aria-label="必填欄位"
                style={{ color: '#ff4d4f', marginLeft: '4px' }}
              >
                *
              </span>
            )}
          </span>
        )
      }
      name={name}
      required={required}
    >
      {React.cloneElement(children as React.ReactElement, {
        id,
        'aria-required': required,
        'aria-invalid': !!errorText,
        'aria-describedby': AriaUtils.describedBy(helpId, errorId),
      })}
      
      {helpText && (
        <div 
          id={helpId} 
          className="form-help-text"
          style={{ color: '#8c8c8c', fontSize: '12px', marginTop: '4px' }}
        >
          <InfoCircleOutlined /> {helpText}
        </div>
      )}
      
      {errorText && (
        <div 
          id={errorId} 
          className="form-error-text"
          role="alert"
          style={{ color: '#ff4d4f', fontSize: '12px', marginTop: '4px' }}
        >
          <ExclamationCircleOutlined /> {errorText}
        </div>
      )}
    </Form.Item>
  );
};

interface AccessibleInputProps extends InputProps {
  label?: string;
  helpText?: string;
  errorText?: string;
  showCharCount?: boolean;
}

/**
 * Accessible input with character count and ARIA support
 */
export const AccessibleInput = forwardRef<HTMLInputElement, AccessibleInputProps>(
  ({ label, helpText, errorText, showCharCount, maxLength, ...props }, ref) => {
    const id = useId();
    const [charCount, setCharCount] = useState(0);
    const helpId = helpText ? `${id}-help` : undefined;
    const errorId = errorText ? `${id}-error` : undefined;
    const countId = showCharCount ? `${id}-count` : undefined;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setCharCount(e.target.value.length);
      props.onChange?.(e);
    };

    return (
      <div className="accessible-input-wrapper">
        {label && (
          <label htmlFor={id} className="input-label">
            {label}
            {props.required && <span aria-label="必填">*</span>}
          </label>
        )}
        
        <Input
          {...props}
          ref={ref}
          id={id}
          onChange={handleChange}
          maxLength={maxLength}
          aria-required={props.required}
          aria-invalid={!!errorText}
          aria-describedby={AriaUtils.describedBy(helpId, errorId, countId)}
          style={{
            ...props.style,
            ...(!errorText ? {} : { borderColor: '#ff4d4f' }),
          }}
        />
        
        {showCharCount && maxLength && (
          <div 
            id={countId}
            aria-live="polite"
            aria-atomic="true"
            style={{ fontSize: '12px', color: '#8c8c8c', textAlign: 'right' }}
          >
            {charCount} / {maxLength} 字元
          </div>
        )}
        
        {helpText && (
          <div id={helpId} className="help-text" style={{ fontSize: '12px', color: '#8c8c8c' }}>
            {helpText}
          </div>
        )}
        
        {errorText && (
          <div id={errorId} role="alert" className="error-text" style={{ fontSize: '12px', color: '#ff4d4f' }}>
            {errorText}
          </div>
        )}
      </div>
    );
  }
);

AccessibleInput.displayName = 'AccessibleInput';

interface AccessibleSelectProps extends SelectProps {
  label?: string;
  helpText?: string;
  errorText?: string;
  options: Array<{ label: string; value: string | number; disabled?: boolean }>;
}

/**
 * Accessible select with keyboard navigation
 */
export const AccessibleSelect: React.FC<AccessibleSelectProps> = ({
  label,
  helpText,
  errorText,
  options,
  ...props
}) => {
  const id = useId();
  const helpId = helpText ? `${id}-help` : undefined;
  const errorId = errorText ? `${id}-error` : undefined;

  return (
    <div className="accessible-select-wrapper">
      {label && (
        <label htmlFor={id} className="select-label">
          {label}
          {props.required && <span aria-label="必填">*</span>}
        </label>
      )}
      
      <Select
        {...props}
        id={id}
        aria-required={props.required}
        aria-invalid={!!errorText}
        aria-describedby={AriaUtils.describedBy(helpId, errorId)}
        style={{
          ...props.style,
          width: '100%',
          ...(!errorText ? {} : { borderColor: '#ff4d4f' }),
        }}
      >
        {options.map(option => (
          <Select.Option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
            aria-selected={props.value === option.value}
          >
            {option.label}
          </Select.Option>
        ))}
      </Select>
      
      {helpText && (
        <div id={helpId} className="help-text" style={{ fontSize: '12px', color: '#8c8c8c' }}>
          {helpText}
        </div>
      )}
      
      {errorText && (
        <div id={errorId} role="alert" className="error-text" style={{ fontSize: '12px', color: '#ff4d4f' }}>
          {errorText}
        </div>
      )}
    </div>
  );
};

interface AccessibleRadioGroupProps {
  label: string;
  options: Array<{ label: string; value: string | number; disabled?: boolean }>;
  value?: string | number;
  onChange?: (value: string | number) => void;
  required?: boolean;
  helpText?: string;
  errorText?: string;
  orientation?: 'horizontal' | 'vertical';
}

/**
 * Accessible radio group with proper ARIA roles
 */
export const AccessibleRadioGroup: React.FC<AccessibleRadioGroupProps> = ({
  label,
  options,
  value,
  onChange,
  required,
  helpText,
  errorText,
  orientation = 'vertical',
}) => {
  const id = useId();
  const groupId = `${id}-group`;
  const helpId = helpText ? `${id}-help` : undefined;
  const errorId = errorText ? `${id}-error` : undefined;

  return (
    <div 
      role="radiogroup" 
      aria-labelledby={`${id}-label`}
      aria-required={required}
      aria-invalid={!!errorText}
      aria-describedby={AriaUtils.describedBy(helpId, errorId)}
      style={{ marginBottom: '16px' }}
    >
      <div id={`${id}-label`} className="radio-group-label" style={{ marginBottom: '8px' }}>
        {label}
        {required && <span aria-label="必填" style={{ color: '#ff4d4f' }}>*</span>}
      </div>
      
      <Radio.Group
        id={groupId}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        style={{ display: orientation === 'vertical' ? 'block' : 'inline-flex' }}
      >
        {options.map((option) => (
          <Radio
            key={option.value}
            value={option.value}
            disabled={option.disabled}
            style={{ 
              display: orientation === 'vertical' ? 'block' : 'inline-block',
              marginBottom: orientation === 'vertical' ? '8px' : 0,
              marginRight: orientation === 'horizontal' ? '16px' : 0,
            }}
          >
            {option.label}
          </Radio>
        ))}
      </Radio.Group>
      
      {helpText && (
        <div id={helpId} className="help-text" style={{ fontSize: '12px', color: '#8c8c8c', marginTop: '4px' }}>
          {helpText}
        </div>
      )}
      
      {errorText && (
        <div id={errorId} role="alert" className="error-text" style={{ fontSize: '12px', color: '#ff4d4f', marginTop: '4px' }}>
          {errorText}
        </div>
      )}
    </div>
  );
};

interface AccessibleCheckboxProps {
  label: string;
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  required?: boolean;
  helpText?: string;
  errorText?: string;
  indeterminate?: boolean;
}

/**
 * Accessible checkbox with proper ARIA states
 */
export const AccessibleCheckbox: React.FC<AccessibleCheckboxProps> = ({
  label,
  checked,
  onChange,
  required,
  helpText,
  errorText,
  indeterminate,
}) => {
  const id = useId();
  const helpId = helpText ? `${id}-help` : undefined;
  const errorId = errorText ? `${id}-error` : undefined;

  return (
    <div className="accessible-checkbox-wrapper" style={{ marginBottom: '16px' }}>
      <Checkbox
        id={id}
        checked={checked}
        indeterminate={indeterminate}
        onChange={(e) => onChange?.(e.target.checked)}
        aria-required={required}
        aria-invalid={!!errorText}
        aria-describedby={AriaUtils.describedBy(helpId, errorId)}
        aria-checked={indeterminate ? 'mixed' : checked}
      >
        {label}
        {required && <span aria-label="必填" style={{ color: '#ff4d4f' }}>*</span>}
      </Checkbox>
      
      {helpText && (
        <div id={helpId} className="help-text" style={{ fontSize: '12px', color: '#8c8c8c', marginTop: '4px' }}>
          {helpText}
        </div>
      )}
      
      {errorText && (
        <div id={errorId} role="alert" className="error-text" style={{ fontSize: '12px', color: '#ff4d4f', marginTop: '4px' }}>
          {errorText}
        </div>
      )}
    </div>
  );
};

interface AccessibleButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  type?: 'primary' | 'default' | 'dashed' | 'text' | 'link';
  loading?: boolean;
  disabled?: boolean;
  ariaLabel?: string;
  ariaPressed?: boolean;
  ariaExpanded?: boolean;
  icon?: React.ReactNode;
  size?: 'small' | 'middle' | 'large';
}

/**
 * Accessible button with loading states and ARIA attributes
 */
export const AccessibleButton: React.FC<AccessibleButtonProps> = ({
  children,
  onClick,
  type = 'default',
  loading = false,
  disabled = false,
  ariaLabel,
  ariaPressed,
  ariaExpanded,
  icon,
  size = 'middle',
}) => {
  return (
    <Button
      type={type}
      onClick={onClick}
      loading={loading}
      disabled={disabled || loading}
      aria-label={ariaLabel}
      aria-pressed={ariaPressed}
      aria-expanded={ariaExpanded}
      aria-busy={loading}
      icon={icon}
      size={size}
      style={{
        ...focusStyles.default,
        minWidth: '44px',
        minHeight: '44px', // WCAG touch target size
      }}
    >
      {children}
      {loading && <span className="sr-only">載入中...</span>}
    </Button>
  );
};

/**
 * Accessible form with error announcement
 */
export const AccessibleForm: React.FC<{
  children: React.ReactNode;
  onSubmit?: (values: any) => void;
  onError?: (errors: any) => void;
}> = ({ children, onSubmit, onError }) => {
  const [form] = Form.useForm();
  const { announceErrors, errorAnnouncerProps } = useFormErrorAnnouncement();

  const handleFinish = (values: any) => {
    onSubmit?.(values);
  };

  const handleFinishFailed = (errorInfo: any) => {
    const errors: Record<string, string> = {};
    errorInfo.errorFields.forEach((field: any) => {
      errors[field.name[0]] = field.errors[0];
    });
    announceErrors(errors);
    onError?.(errors);
  };

  return (
    <>
      <div {...errorAnnouncerProps} />
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        onFinishFailed={handleFinishFailed}
        aria-label="表單"
      >
        {children}
      </Form>
    </>
  );
};

export default {
  AccessibleFormItem,
  AccessibleInput,
  AccessibleSelect,
  AccessibleRadioGroup,
  AccessibleCheckbox,
  AccessibleButton,
  AccessibleForm,
};