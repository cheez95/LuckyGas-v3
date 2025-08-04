// Token storage utilities with security considerations
// In production, consider using httpOnly cookies for better security

import { User } from '../types/auth';

const ACCESS_TOKEN_KEY = 'lucky_gas_access_token';
const REFRESH_TOKEN_KEY = 'lucky_gas_refresh_token';
const USER_DATA_KEY = 'lucky_gas_user_data';

// Check if we're in a secure context (HTTPS)
const isSecureContext = () => {
  return window.location.protocol === 'https:' || window.location.hostname === 'localhost';
};

// Token management functions
export const getAccessToken = (): string | null => {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch (error) {
    console.error('Error reading access token:', error);
    return null;
  }
};

export const getRefreshToken = (): string | null => {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch (error) {
    console.error('Error reading refresh token:', error);
    return null;
  }
};

export const setTokens = (accessToken: string, refreshToken: string): void => {
  try {
    // In production, implement additional security measures
    if (!isSecureContext()) {
      console.warn('Storing tokens in non-secure context!');
    }
    
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  } catch (error) {
    console.error('Error storing tokens:', error);
  }
};

export const clearTokens = (): void => {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_DATA_KEY);
  } catch (error) {
    console.error('Error clearing tokens:', error);
  }
};

// User data management
export const getUserData = (): User | null => {
  try {
    const data = localStorage.getItem(USER_DATA_KEY);
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error('Error reading user data:', error);
    return null;
  }
};

export const setUserData = (userData: User): void => {
  try {
    localStorage.setItem(USER_DATA_KEY, JSON.stringify(userData));
  } catch (error) {
    console.error('Error storing user data:', error);
  }
};

// Token validation utilities
export const isTokenExpired = (token: string): boolean => {
  try {
    // Decode JWT token (basic implementation)
    const payload = JSON.parse(atob(token.split('.')[1]));
    const expirationTime = payload.exp * 1000; // Convert to milliseconds
    return Date.now() >= expirationTime;
  } catch (error) {
    console.error('Error decoding token:', error);
    return true; // Assume expired if can't decode
  }
};

export const getTokenExpiration = (token: string): Date | null => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return new Date(payload.exp * 1000);
  } catch (error) {
    console.error('Error getting token expiration:', error);
    return null;
  }
};

// Session management
export const isAuthenticated = (): boolean => {
  const token = getAccessToken();
  if (!token) return false;
  
  return !isTokenExpired(token);
};

// Security utilities
export const sanitizeUserInput = (input: string): string => {
  // Basic XSS prevention
  return input
    .replace(/[<>]/g, '')
    .trim();
};

// Storage event listener for multi-tab synchronization
export const setupStorageListener = (callback: (event: StorageEvent) => void): void => {
  window.addEventListener('storage', (event) => {
    if (event.key === ACCESS_TOKEN_KEY || event.key === REFRESH_TOKEN_KEY || event.key === USER_DATA_KEY) {
      callback(event);
    }
  });
};

export const removeStorageListener = (callback: (event: StorageEvent) => void): void => {
  window.removeEventListener('storage', callback);
};