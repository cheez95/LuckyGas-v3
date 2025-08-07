import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../../utils/storage';
import { AuthResponse } from '../../types/auth';

// Create axios instance with base configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Queue to hold requests while token is being refreshed
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: any) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: AxiosError | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
};

// Request interceptor to add JWT token
apiClient.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor for token refresh
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest: any = error.config;

    // If error is 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        }).catch((err) => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();
      
      if (!refreshToken) {
        // No refresh token, clear tokens and redirect to login
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        // Call refresh endpoint
        const response = await axios.post<AuthResponse>(
          `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;
        
        // Update tokens
        setTokens(access_token, newRefreshToken);
        
        // Process queued requests
        processQueue(null, access_token);
        
        // Retry original request
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect
        processQueue(refreshError as AxiosError, null);
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // For other errors, implement exponential backoff for network failures
    if (!error.response && originalRequest._retryCount < 3) {
      originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;
      const backoffDelay = Math.min(1000 * Math.pow(2, originalRequest._retryCount), 10000);
      
      return new Promise((resolve) => {
        setTimeout(() => resolve(apiClient(originalRequest)), backoffDelay);
      });
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// Utility function to handle API errors
export const handleApiError = (error: AxiosError): string => {
  if (error.response) {
    // Server responded with error
    const data: any = error.response.data;
    return data.message || data.detail || '發生錯誤，請稍後再試';
  } else if (error.request) {
    // Request made but no response
    return '網路連線異常，請檢查您的網路連線';
  } else {
    // Something else happened
    return error.message || '發生未知錯誤';
  }
};