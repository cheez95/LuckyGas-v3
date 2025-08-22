/**
 * API Service with Cleanup Support
 * Provides automatic request cancellation on component unmount
 */

import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';
import api from './api';

export interface CleanupConfig extends AxiosRequestConfig {
  abortSignal?: AbortSignal;
}

class ApiWithCleanup {
  /**
   * Create a cancellable request
   */
  createCancellableRequest<T = any>(
    method: 'get' | 'post' | 'put' | 'delete' | 'patch',
    url: string,
    config?: CleanupConfig,
    data?: any
  ): { request: Promise<AxiosResponse<T>>; cancel: () => void } {
    const abortController = new AbortController();
    
    const requestConfig: AxiosRequestConfig = {
      ...config,
      signal: config?.abortSignal || abortController.signal,
    };

    let request: Promise<AxiosResponse<T>>;
    
    switch (method) {
      case 'get':
        request = api.get<T>(url, requestConfig);
        break;
      case 'post':
        request = api.post<T>(url, data, requestConfig);
        break;
      case 'put':
        request = api.put<T>(url, data, requestConfig);
        break;
      case 'delete':
        request = api.delete<T>(url, requestConfig);
        break;
      case 'patch':
        request = api.patch<T>(url, data, requestConfig);
        break;
      default:
        throw new Error(`Unsupported method: ${method}`);
    }

    return {
      request: request.catch(error => {
        if (axios.isCancel(error)) {
          console.log('Request cancelled:', url);
        }
        throw error;
      }),
      cancel: () => abortController.abort(),
    };
  }

  /**
   * GET request with cleanup
   */
  get<T = any>(url: string, signal?: AbortSignal): Promise<AxiosResponse<T>> {
    return api.get<T>(url, { signal });
  }

  /**
   * POST request with cleanup
   */
  post<T = any>(url: string, data?: any, signal?: AbortSignal): Promise<AxiosResponse<T>> {
    return api.post<T>(url, data, { signal });
  }

  /**
   * PUT request with cleanup
   */
  put<T = any>(url: string, data?: any, signal?: AbortSignal): Promise<AxiosResponse<T>> {
    return api.put<T>(url, data, { signal });
  }

  /**
   * DELETE request with cleanup
   */
  delete<T = any>(url: string, signal?: AbortSignal): Promise<AxiosResponse<T>> {
    return api.delete<T>(url, { signal });
  }

  /**
   * PATCH request with cleanup
   */
  patch<T = any>(url: string, data?: any, signal?: AbortSignal): Promise<AxiosResponse<T>> {
    return api.patch<T>(url, data, { signal });
  }
}

export const apiWithCleanup = new ApiWithCleanup();

/**
 * Hook for using API with automatic cleanup
 */
export function useApiWithCleanup() {
  const abortController = new AbortController();

  // Cleanup on unmount
  if (typeof window !== 'undefined') {
    const cleanup = () => abortController.abort();
    
    // For React, this should be called in useEffect cleanup
    return {
      signal: abortController.signal,
      cleanup,
      get: <T = any>(url: string) => apiWithCleanup.get<T>(url, abortController.signal),
      post: <T = any>(url: string, data?: any) => apiWithCleanup.post<T>(url, data, abortController.signal),
      put: <T = any>(url: string, data?: any) => apiWithCleanup.put<T>(url, data, abortController.signal),
      delete: <T = any>(url: string) => apiWithCleanup.delete<T>(url, abortController.signal),
      patch: <T = any>(url: string, data?: any) => apiWithCleanup.patch<T>(url, data, abortController.signal),
    };
  }

  return {
    signal: abortController.signal,
    cleanup: () => {},
    get: apiWithCleanup.get,
    post: apiWithCleanup.post,
    put: apiWithCleanup.put,
    delete: apiWithCleanup.delete,
    patch: apiWithCleanup.patch,
  };
}