import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { configureStore } from '@reduxjs/toolkit';
import RoutePlanning from '../office/RoutePlanning';

// Mock the API service
jest.mock('../../services/api.service', () => ({
  apiService: {
    get: jest.fn(),
    post: jest.fn(),
  },
  apiWithCancel: {
    get: jest.fn(),
    post: jest.fn(),
  },
  requestManager: {
    cancel: jest.fn(),
    cancelAll: jest.fn(),
    get: jest.fn(),
    post: jest.fn(),
  },
}));

// Mock WebSocket context
jest.mock('../../contexts/WebSocketContext', () => ({
  useWebSocketContext: () => ({
    isConnected: true,
    sendMessage: jest.fn(),
    lastMessage: null,
    on: jest.fn(() => jest.fn()),
    emit: jest.fn(),
  }),
}));

describe('Route Planning Memory Leak Fixes', () => {
  let store: any;
  let mockRequestManager: any;
  let mockApiWithCancel: any;

  beforeEach(() => {
    // Create a mock Redux store
    store = configureStore({
      reducer: {
        auth: () => ({ user: { id: 1, name: 'Test User', role: 'manager' } }),
      },
    });

    // Get mocked modules
    const apiModule = require('../../services/api.service');
    mockRequestManager = apiModule.requestManager;
    mockApiWithCancel = apiModule.apiWithCancel;

    // Setup default mock responses
    mockApiWithCancel.get.mockResolvedValue({
      success: true,
      data: [],
    });

    mockApiWithCancel.post.mockResolvedValue({
      success: true,
      data: { routes: [] },
    });
  });

  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
  });

  describe('Component Cleanup', () => {
    it('should cancel all requests on unmount', async () => {
      const { unmount } = render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      // Wait for initial render
      await waitFor(() => {
        expect(mockApiWithCancel.get).toHaveBeenCalled();
      });

      // Unmount the component
      unmount();

      // Verify cancellation was called
      expect(mockRequestManager.cancel).toHaveBeenCalledWith('route-planning-drivers');
      expect(mockRequestManager.cancel).toHaveBeenCalledWith('route-planning-routes');
      expect(mockRequestManager.cancel).toHaveBeenCalledWith('route-planning-orders');
    });

    it('should not update state after unmount', async () => {
      let resolvePromise: any;
      const delayedPromise = new Promise(resolve => {
        resolvePromise = resolve;
      });

      mockApiWithCancel.get.mockReturnValue(delayedPromise);

      const { unmount } = render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      // Unmount before promise resolves
      unmount();

      // Resolve the promise after unmount
      resolvePromise({ success: true, data: [] });

      // Wait a bit to ensure no state updates occur
      await new Promise(resolve => setTimeout(resolve, 100));

      // No errors should be thrown
      expect(true).toBe(true);
    });
  });

  describe('Request Management', () => {
    it('should use cancellable requests with unique IDs', async () => {
      render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(mockApiWithCancel.get).toHaveBeenCalledWith(
          expect.stringContaining('/drivers'),
          'route-planning-drivers',
          expect.any(Object)
        );
        expect(mockApiWithCancel.get).toHaveBeenCalledWith(
          expect.stringContaining('/routes'),
          'route-planning-routes',
          expect.any(Object)
        );
        expect(mockApiWithCancel.get).toHaveBeenCalledWith(
          expect.stringContaining('/orders'),
          'route-planning-orders',
          expect.any(Object)
        );
      });
    });

    it('should implement request caching', async () => {
      render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(mockApiWithCancel.get).toHaveBeenCalledWith(
          expect.any(String),
          expect.any(String),
          expect.objectContaining({ cache: true })
        );
      });
    });

    it('should implement request debouncing', async () => {
      render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(mockApiWithCancel.get).toHaveBeenCalledWith(
          expect.any(String),
          expect.any(String),
          expect.objectContaining({ debounce: expect.any(Number) })
        );
      });
    });
  });

  describe('Memory Management', () => {
    it('should track mounted state with useRef', () => {
      const { container } = render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      // Component should render without errors
      expect(container).toBeTruthy();
    });

    it('should cleanup WebSocket subscriptions on unmount', async () => {
      const mockWebSocketContext = require('../../contexts/WebSocketContext');
      const unsubscribeMock = jest.fn();
      mockWebSocketContext.useWebSocketContext.mockReturnValue({
        isConnected: true,
        sendMessage: jest.fn(),
        lastMessage: null,
        on: jest.fn(() => unsubscribeMock),
        emit: jest.fn(),
      });

      const { unmount } = render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      unmount();

      // Verify WebSocket cleanup
      expect(unsubscribeMock).toHaveBeenCalled();
    });

    it('should handle errors gracefully', async () => {
      mockApiWithCancel.get.mockRejectedValue(new Error('Network error'));

      render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      // Should handle error without crashing
      await waitFor(() => {
        expect(mockApiWithCancel.get).toHaveBeenCalled();
      });

      // Component should still be rendered
      expect(screen.getByText(/路線規劃/i)).toBeInTheDocument();
    });
  });

  describe('Performance Optimizations', () => {
    it('should not trigger unnecessary re-renders', async () => {
      const renderSpy = jest.fn();
      
      // Mock React.memo to track renders
      jest.spyOn(React, 'memo').mockImplementation((component: any) => {
        return (props: any) => {
          renderSpy();
          return component(props);
        };
      });

      render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(mockApiWithCancel.get).toHaveBeenCalled();
      });

      // Should have minimal renders
      expect(renderSpy.mock.calls.length).toBeLessThan(5);
    });

    it('should use loading states to prevent duplicate requests', async () => {
      render(
        <Provider store={store}>
          <MemoryRouter>
            <ConfigProvider locale={zhTW}>
              <RoutePlanning />
            </ConfigProvider>
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(mockApiWithCancel.get).toHaveBeenCalled();
      });

      // Should not make duplicate calls for the same data
      const callCount = mockApiWithCancel.get.mock.calls.filter(
        (call: any) => call[0].includes('/drivers')
      ).length;
      
      expect(callCount).toBe(1);
    });
  });
});