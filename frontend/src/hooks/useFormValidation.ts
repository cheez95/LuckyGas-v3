/**
 * Form validation hook for common validation patterns
 * Eliminates ~300 lines of duplicate validation logic
 */

import { useState, useCallback, useRef } from 'react';
import { Form, FormInstance } from 'antd';
import { RuleObject } from 'antd/es/form';

// Validation result type
interface ValidationResult {
  valid: boolean;
  errors: Record<string, string[]>;
}

// Common validation rules for Taiwan
export const ValidationRules = {
  // Required field
  required: (message: string = '此欄位為必填'): RuleObject => ({
    required: true,
    message,
  }),

  // Email validation
  email: (message: string = '請輸入有效的電子郵件'): RuleObject => ({
    type: 'email',
    message,
  }),

  // Taiwan phone number
  phoneNumber: (message: string = '請輸入有效的電話號碼'): RuleObject => ({
    pattern: /^09\d{8}$|^0[2-8]\d{7,8}$/,
    message,
  }),

  // Taiwan mobile number only
  mobileNumber: (message: string = '請輸入有效的手機號碼'): RuleObject => ({
    pattern: /^09\d{8}$/,
    message,
  }),

  // Positive number
  positiveNumber: (message: string = '請輸入大於0的數字'): RuleObject => ({
    validator: (_, value) => {
      if (value && value > 0) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message));
    },
  }),

  // Min value
  minValue: (min: number, message?: string): RuleObject => ({
    validator: (_, value) => {
      if (value >= min) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message || `數值必須大於或等於 ${min}`));
    },
  }),

  // Max value
  maxValue: (max: number, message?: string): RuleObject => ({
    validator: (_, value) => {
      if (value <= max) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message || `數值必須小於或等於 ${max}`));
    },
  }),

  // Range
  range: (min: number, max: number, message?: string): RuleObject => ({
    validator: (_, value) => {
      if (value >= min && value <= max) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message || `數值必須在 ${min} 到 ${max} 之間`));
    },
  }),

  // Min length
  minLength: (min: number, message?: string): RuleObject => ({
    min,
    message: message || `長度至少為 ${min} 個字元`,
  }),

  // Max length
  maxLength: (max: number, message?: string): RuleObject => ({
    max,
    message: message || `長度不能超過 ${max} 個字元`,
  }),

  // Taiwan address
  taiwanAddress: (message: string = '請輸入完整的台灣地址'): RuleObject => ({
    validator: (_, value) => {
      if (!value) return Promise.resolve();
      
      const requiredChars = ['市', '區', '路', '街', '巷', '號'];
      const hasRequiredChar = requiredChars.some(char => value.includes(char));
      
      if (value.length >= 6 && hasRequiredChar) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message));
    },
  }),

  // Future date
  futureDate: (message: string = '日期必須是未來的日期'): RuleObject => ({
    validator: (_, value) => {
      if (!value) return Promise.resolve();
      
      const selectedDate = new Date(value);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      if (selectedDate > today) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message));
    },
  }),

  // Past date
  pastDate: (message: string = '日期必須是過去的日期'): RuleObject => ({
    validator: (_, value) => {
      if (!value) return Promise.resolve();
      
      const selectedDate = new Date(value);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      if (selectedDate < today) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message));
    },
  }),

  // Date range
  dateRange: (startDate: Date, endDate: Date, message?: string): RuleObject => ({
    validator: (_, value) => {
      if (!value) return Promise.resolve();
      
      const selectedDate = new Date(value);
      if (selectedDate >= startDate && selectedDate <= endDate) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message || '日期超出允許範圍'));
    },
  }),

  // Taiwan ID number
  taiwanId: (message: string = '請輸入有效的身分證字號'): RuleObject => ({
    pattern: /^[A-Z][12]\d{8}$/,
    message,
  }),

  // URL
  url: (message: string = '請輸入有效的網址'): RuleObject => ({
    type: 'url',
    message,
  }),

  // Percentage (0-100)
  percentage: (message: string = '請輸入 0 到 100 之間的數值'): RuleObject => ({
    validator: (_, value) => {
      if (value >= 0 && value <= 100) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message));
    },
  }),

  // Custom regex
  pattern: (pattern: RegExp, message: string): RuleObject => ({
    pattern,
    message,
  }),

  // Custom validator
  custom: (validator: (value: any) => boolean, message: string): RuleObject => ({
    validator: (_, value) => {
      if (validator(value)) {
        return Promise.resolve();
      }
      return Promise.reject(new Error(message));
    },
  }),
};

// Form validation hook
export function useFormValidation<T = any>(initialValues?: Partial<T>) {
  const [form] = Form.useForm();
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const [isValidating, setIsValidating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const validationCache = useRef<Map<string, ValidationResult>>(new Map());

  // Set initial values
  if (initialValues) {
    form.setFieldsValue(initialValues);
  }

  // Validate single field
  const validateField = useCallback(async (fieldName: string): Promise<boolean> => {
    try {
      await form.validateFields([fieldName]);
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[fieldName];
        return newErrors;
      });
      return true;
    } catch (error: any) {
      if (error.errorFields) {
        const fieldError = error.errorFields.find((e: any) => e.name[0] === fieldName);
        if (fieldError) {
          setErrors(prev => ({
            ...prev,
            [fieldName]: fieldError.errors,
          }));
        }
      }
      return false;
    }
  }, [form]);

  // Validate all fields
  const validateAll = useCallback(async (): Promise<ValidationResult> => {
    setIsValidating(true);
    try {
      const values = await form.validateFields();
      setErrors({});
      const result = { valid: true, errors: {} };
      validationCache.current.set(JSON.stringify(values), result);
      return result;
    } catch (error: any) {
      const errorMap: Record<string, string[]> = {};
      if (error.errorFields) {
        error.errorFields.forEach((field: any) => {
          errorMap[field.name[0]] = field.errors;
        });
      }
      setErrors(errorMap);
      const result = { valid: false, errors: errorMap };
      return result;
    } finally {
      setIsValidating(false);
    }
  }, [form]);

  // Clear field error
  const clearFieldError = useCallback((fieldName: string) => {
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[fieldName];
      return newErrors;
    });
  }, []);

  // Clear all errors
  const clearAllErrors = useCallback(() => {
    setErrors({});
    form.resetFields();
  }, [form]);

  // Mark field as touched
  const markFieldTouched = useCallback((fieldName: string) => {
    setTouched(prev => new Set(prev).add(fieldName));
  }, []);

  // Check if field has error
  const hasFieldError = useCallback((fieldName: string): boolean => {
    return !!errors[fieldName]?.length;
  }, [errors]);

  // Get field error message
  const getFieldError = useCallback((fieldName: string): string | undefined => {
    return errors[fieldName]?.[0];
  }, [errors]);

  // Check if field is touched
  const isFieldTouched = useCallback((fieldName: string): boolean => {
    return touched.has(fieldName);
  }, [touched]);

  // Set field value
  const setFieldValue = useCallback((fieldName: string, value: any) => {
    form.setFieldValue(fieldName, value);
    markFieldTouched(fieldName);
  }, [form, markFieldTouched]);

  // Get field value
  const getFieldValue = useCallback((fieldName: string) => {
    return form.getFieldValue(fieldName);
  }, [form]);

  // Set multiple field values
  const setFieldsValue = useCallback((values: Partial<T>) => {
    form.setFieldsValue(values);
    Object.keys(values).forEach(key => markFieldTouched(key));
  }, [form, markFieldTouched]);

  // Get all field values
  const getFieldsValue = useCallback((): T => {
    return form.getFieldsValue();
  }, [form]);

  // Reset form
  const resetForm = useCallback(() => {
    form.resetFields();
    setErrors({});
    setTouched(new Set());
    validationCache.current.clear();
  }, [form]);

  // Check if form is valid
  const isFormValid = useCallback((): boolean => {
    return Object.keys(errors).length === 0;
  }, [errors]);

  // Submit handler wrapper
  const handleSubmit = useCallback(
    (onSubmit: (values: T) => Promise<void> | void) => {
      return async () => {
        setIsSubmitting(true);
        try {
          const result = await validateAll();
          if (result.valid) {
            const values = getFieldsValue();
            await onSubmit(values);
          }
        } finally {
          setIsSubmitting(false);
        }
      };
    },
    [validateAll, getFieldsValue]
  );

  return {
    form,
    errors,
    touched,
    isValidating,
    isSubmitting,
    validateField,
    validateAll,
    clearFieldError,
    clearAllErrors,
    markFieldTouched,
    hasFieldError,
    getFieldError,
    isFieldTouched,
    setFieldValue,
    getFieldValue,
    setFieldsValue,
    getFieldsValue,
    resetForm,
    isFormValid,
    handleSubmit,
    ValidationRules,
  };
}

// Export individual validators for standalone use
export const Validators = {
  isEmail: (email: string): boolean => {
    const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return pattern.test(email);
  },

  isPhoneNumber: (phone: string): boolean => {
    const pattern = /^09\d{8}$|^0[2-8]\d{7,8}$/;
    return pattern.test(phone.replace(/-/g, '').replace(/ /g, ''));
  },

  isTaiwanId: (id: string): boolean => {
    const pattern = /^[A-Z][12]\d{8}$/;
    return pattern.test(id);
  },

  isTaiwanAddress: (address: string): boolean => {
    const requiredChars = ['市', '區', '路', '街', '巷', '號'];
    return address.length >= 6 && requiredChars.some(char => address.includes(char));
  },

  isPositiveNumber: (value: number): boolean => {
    return value > 0;
  },

  isPercentage: (value: number): boolean => {
    return value >= 0 && value <= 100;
  },

  isFutureDate: (date: Date | string): boolean => {
    const selectedDate = new Date(date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return selectedDate > today;
  },

  isPastDate: (date: Date | string): boolean => {
    const selectedDate = new Date(date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return selectedDate < today;
  },
};