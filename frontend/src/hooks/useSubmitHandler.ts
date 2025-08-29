/**
 * useSubmitHandler Hook
 * Standardized form submission handling
 * Eliminates ~300 lines of duplicate submission logic
 */

import { useState, useCallback, useRef } from 'react';
import { message } from 'antd';
import { AxiosError } from 'axios';

interface SubmitOptions<T, R = any> {
  onSubmit: (values: T) => Promise<R>;
  onSuccess?: (result: R, values: T) => void;
  onError?: (error: any, values: T) => void;
  onFinally?: () => void;
  successMessage?: string | ((result: R) => string);
  errorMessage?: string | ((error: any) => string);
  showSuccessMessage?: boolean;
  showErrorMessage?: boolean;
  resetOnSuccess?: boolean;
  preventDuplicateSubmission?: boolean;
  validationFn?: (values: T) => Promise<boolean> | boolean;
  transformValues?: (values: T) => T | Promise<T>;
  retryOnFailure?: boolean;
  maxRetries?: number;
  retryDelay?: number;
}

interface SubmitState<R = any> {
  isSubmitting: boolean;
  isSuccess: boolean;
  isError: boolean;
  error: any;
  data: R | null;
  submitCount: number;
}

export function useSubmitHandler<T = any, R = any>(options: SubmitOptions<T, R>) {
  const {
    onSubmit,
    onSuccess,
    onError,
    onFinally,
    successMessage = '操作成功',
    errorMessage = '操作失敗',
    showSuccessMessage = true,
    showErrorMessage = true,
    resetOnSuccess = false,
    preventDuplicateSubmission = true,
    validationFn,
    transformValues,
    retryOnFailure = false,
    maxRetries = 3,
    retryDelay = 1000,
  } = options;

  const [state, setState] = useState<SubmitState<R>>({
    isSubmitting: false,
    isSuccess: false,
    isError: false,
    error: null,
    data: null,
    submitCount: 0,
  });

  const submissionInProgress = useRef(false);
  const retryCount = useRef(0);

  // Extract error message from various error formats
  const extractErrorMessage = useCallback((error: any): string => {
    if (typeof error === 'string') {
      return error;
    }

    if (error instanceof AxiosError) {
      // Handle Axios errors
      if (error.response?.data?.detail) {
        return error.response.data.detail;
      }
      if (error.response?.data?.message) {
        return error.response.data.message;
      }
      if (error.response?.data?.error) {
        return error.response.data.error;
      }
      if (error.message) {
        return error.message;
      }
    }

    if (error instanceof Error) {
      return error.message;
    }

    if (error?.detail) {
      return error.detail;
    }

    if (error?.message) {
      return error.message;
    }

    return '發生未知錯誤';
  }, []);

  // Reset state
  const reset = useCallback(() => {
    setState({
      isSubmitting: false,
      isSuccess: false,
      isError: false,
      error: null,
      data: null,
      submitCount: 0,
    });
    submissionInProgress.current = false;
    retryCount.current = 0;
  }, []);

  // Handle submission with retry logic
  const handleSubmitWithRetry = useCallback(async (values: T): Promise<R | null> => {
    try {
      const result = await onSubmit(values);
      retryCount.current = 0;
      return result;
    } catch (error) {
      if (retryOnFailure && retryCount.current < maxRetries) {
        retryCount.current++;
        // console.log(`Retry attempt ${retryCount.current} of ${maxRetries}`);
        
        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, retryDelay * retryCount.current));
        
        // Recursive retry
        return handleSubmitWithRetry(values);
      }
      throw error;
    }
  }, [onSubmit, retryOnFailure, maxRetries, retryDelay]);

  // Main submit handler
  const handleSubmit = useCallback(async (values: T) => {
    // Prevent duplicate submissions
    if (preventDuplicateSubmission && submissionInProgress.current) {
      console.warn('Submission already in progress');
      return;
    }

    try {
      submissionInProgress.current = true;
      
      setState(prev => ({
        ...prev,
        isSubmitting: true,
        isSuccess: false,
        isError: false,
        error: null,
      }));

      // Run custom validation if provided
      if (validationFn) {
        const isValid = await validationFn(values);
        if (!isValid) {
          throw new Error('驗證失敗');
        }
      }

      // Transform values if transformer provided
      let finalValues = values;
      if (transformValues) {
        finalValues = await transformValues(values);
      }

      // Submit with retry logic
      const result = await handleSubmitWithRetry(finalValues);

      // Success handling
      setState(prev => ({
        ...prev,
        isSubmitting: false,
        isSuccess: true,
        isError: false,
        error: null,
        data: result,
        submitCount: prev.submitCount + 1,
      }));

      // Show success message
      if (showSuccessMessage) {
        const msg = typeof successMessage === 'function' 
          ? successMessage(result as R)
          : successMessage;
        message.success(msg);
      }

      // Call success callback
      onSuccess?.(result as R, finalValues);

      // Reset form if needed
      if (resetOnSuccess) {
        reset();
      }

      return result;
    } catch (error) {
      // Error handling
      const errorMsg = extractErrorMessage(error);
      
      setState(prev => ({
        ...prev,
        isSubmitting: false,
        isSuccess: false,
        isError: true,
        error: errorMsg,
        submitCount: prev.submitCount + 1,
      }));

      // Show error message
      if (showErrorMessage) {
        const msg = typeof errorMessage === 'function'
          ? errorMessage(error)
          : errorMsg || errorMessage;
        message.error(msg);
      }

      // Call error callback
      onError?.(error, values);

      throw error;
    } finally {
      submissionInProgress.current = false;
      onFinally?.();
    }
  }, [
    preventDuplicateSubmission,
    validationFn,
    transformValues,
    handleSubmitWithRetry,
    showSuccessMessage,
    successMessage,
    onSuccess,
    resetOnSuccess,
    reset,
    extractErrorMessage,
    showErrorMessage,
    errorMessage,
    onError,
    onFinally,
  ]);

  // Create a debounced submit handler
  const handleDebouncedSubmit = useCallback((delay: number = 300) => {
    let timeoutId: NodeJS.Timeout;
    
    return (values: T) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        handleSubmit(values);
      }, delay);
    };
  }, [handleSubmit]);

  // Create a throttled submit handler  
  const handleThrottledSubmit = useCallback((limit: number = 1000) => {
    let lastCall = 0;
    
    return (values: T) => {
      const now = Date.now();
      if (now - lastCall >= limit) {
        lastCall = now;
        handleSubmit(values);
      }
    };
  }, [handleSubmit]);

  return {
    ...state,
    handleSubmit,
    handleDebouncedSubmit,
    handleThrottledSubmit,
    reset,
    setError: (error: any) => setState(prev => ({ ...prev, error, isError: true })),
    clearError: () => setState(prev => ({ ...prev, error: null, isError: false })),
  };
}

// Preset configurations for common scenarios
export const SubmitPresets = {
  // Standard form submission
  standard: <T, R = any>(
    onSubmit: (values: T) => Promise<R>
  ): SubmitOptions<T, R> => ({
    onSubmit,
    showSuccessMessage: true,
    showErrorMessage: true,
    preventDuplicateSubmission: true,
  }),

  // Create operation
  create: <T, R = any>(
    onSubmit: (values: T) => Promise<R>,
    successMessage?: string
  ): SubmitOptions<T, R> => ({
    onSubmit,
    successMessage: successMessage || '建立成功',
    showSuccessMessage: true,
    showErrorMessage: true,
    resetOnSuccess: true,
    preventDuplicateSubmission: true,
  }),

  // Update operation
  update: <T, R = any>(
    onSubmit: (values: T) => Promise<R>,
    successMessage?: string
  ): SubmitOptions<T, R> => ({
    onSubmit,
    successMessage: successMessage || '更新成功',
    showSuccessMessage: true,
    showErrorMessage: true,
    preventDuplicateSubmission: true,
  }),

  // Delete operation
  delete: <T, R = any>(
    onSubmit: (values: T) => Promise<R>,
    successMessage?: string
  ): SubmitOptions<T, R> => ({
    onSubmit,
    successMessage: successMessage || '刪除成功',
    errorMessage: '刪除失敗',
    showSuccessMessage: true,
    showErrorMessage: true,
    preventDuplicateSubmission: true,
  }),

  // Search operation
  search: <T, R = any>(
    onSubmit: (values: T) => Promise<R>
  ): SubmitOptions<T, R> => ({
    onSubmit,
    showSuccessMessage: false,
    showErrorMessage: true,
    preventDuplicateSubmission: false,
  }),

  // Login operation
  login: <T, R = any>(
    onSubmit: (values: T) => Promise<R>,
    onSuccess?: (result: R, values: T) => void
  ): SubmitOptions<T, R> => ({
    onSubmit,
    onSuccess,
    successMessage: '登入成功',
    errorMessage: '登入失敗，請檢查帳號密碼',
    showSuccessMessage: true,
    showErrorMessage: true,
    preventDuplicateSubmission: true,
    retryOnFailure: true,
    maxRetries: 2,
  }),

  // File upload
  upload: <T, R = any>(
    onSubmit: (values: T) => Promise<R>,
    onSuccess?: (result: R, values: T) => void
  ): SubmitOptions<T, R> => ({
    onSubmit,
    onSuccess,
    successMessage: '上傳成功',
    errorMessage: '上傳失敗',
    showSuccessMessage: true,
    showErrorMessage: true,
    preventDuplicateSubmission: true,
    retryOnFailure: true,
    maxRetries: 3,
    retryDelay: 2000,
  }),
};

// Export types for external use
export type { SubmitOptions, SubmitState };