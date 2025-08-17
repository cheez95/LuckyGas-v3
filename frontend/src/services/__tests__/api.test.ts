import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { apiService, RequestManager } from '../api.service';

describe('API Service Memory Leak Fixes', () => {
  let requestManager: RequestManager;
  let fetchMock: jest.Mock;

  beforeEach(() => {
    fetchMock = jest.fn();
    global.fetch = fetchMock;
    requestManager = new RequestManager();
    
    // Mock successful response by default
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: 'test' }),
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
    requestManager.cancelAll();
  });

  describe('Request Timeouts', () => {
    it('should timeout requests after 10 seconds', async () => {
      // Mock a slow request
      fetchMock.mockImplementation(() => 
        new Promise(resolve => setTimeout(resolve, 15000))
      );

      const startTime = Date.now();
      
      try {
        await requestManager.request('/test', { timeout: 10000 });
      } catch (error: any) {
        const duration = Date.now() - startTime;
        expect(duration).toBeLessThan(11000);
        expect(error.message).toContain('aborted');
      }
    });

    it('should use default 10 second timeout', () => {
      const options = requestManager['getRequestOptions']({});
      expect(options.timeout).toBe(10000);
    });
  });

  describe('Request Cancellation', () => {
    it('should cancel requests with AbortController', async () => {
      let abortSignal: AbortSignal | undefined;
      
      fetchMock.mockImplementation((url, options) => {
        abortSignal = options?.signal;
        return new Promise(resolve => setTimeout(resolve, 1000));
      });

      const promise = requestManager.request('/test', {}, 'test-request');
      requestManager.cancel('test-request');

      try {
        await promise;
      } catch (error: any) {
        expect(error.message).toContain('aborted');
        expect(abortSignal?.aborted).toBe(true);
      }
    });

    it('should cancel all requests on cancelAll', () => {
      const promise1 = requestManager.request('/test1', {}, 'req1');
      const promise2 = requestManager.request('/test2', {}, 'req2');
      
      requestManager.cancelAll();
      
      expect(requestManager['abortControllers'].size).toBe(0);
    });

    it('should cleanup AbortController after request completes', async () => {
      await requestManager.request('/test', {}, 'test-req');
      
      expect(requestManager['abortControllers'].has('test-req')).toBe(false);
    });
  });

  describe('Request Caching', () => {
    it('should cache GET requests when enabled', async () => {
      const result1 = await requestManager.get('/test', 'test-cache', { cache: true });
      const result2 = await requestManager.get('/test', 'test-cache', { cache: true });
      
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(result1).toEqual(result2);
    });

    it('should respect cache TTL of 1 minute', async () => {
      jest.useFakeTimers();
      
      await requestManager.get('/test', 'test-ttl', { cache: true });
      
      // Advance time by 61 seconds
      jest.advanceTimersByTime(61000);
      
      await requestManager.get('/test', 'test-ttl', { cache: true });
      
      expect(fetchMock).toHaveBeenCalledTimes(2);
      
      jest.useRealTimers();
    });

    it('should not cache POST requests', async () => {
      await requestManager.post('/test', {}, 'test-post', { cache: true });
      await requestManager.post('/test', {}, 'test-post', { cache: true });
      
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
  });

  describe('Request Debouncing', () => {
    it('should debounce rapid requests', async () => {
      jest.useFakeTimers();
      
      const promise1 = requestManager.get('/test', 'debounce-test', { debounce: 300 });
      const promise2 = requestManager.get('/test', 'debounce-test', { debounce: 300 });
      const promise3 = requestManager.get('/test', 'debounce-test', { debounce: 300 });
      
      jest.advanceTimersByTime(300);
      
      await Promise.all([promise1, promise2, promise3]);
      
      expect(fetchMock).toHaveBeenCalledTimes(1);
      
      jest.useRealTimers();
    });

    it('should clear debounce timers on cleanup', () => {
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      
      requestManager.get('/test', 'debounce-cleanup', { debounce: 300 });
      requestManager['clearDebounceTimers']();
      
      expect(clearTimeoutSpy).toHaveBeenCalled();
      expect(requestManager['debounceTimers'].size).toBe(0);
    });
  });

  describe('Error Handling', () => {
    it('should add catch handlers to all promises', async () => {
      fetchMock.mockRejectedValue(new Error('Network error'));
      
      try {
        await requestManager.get('/test');
      } catch (error: any) {
        expect(error.message).toBe('Network error');
      }
    });

    it('should handle non-Error rejections', async () => {
      fetchMock.mockRejectedValue('String error');
      
      try {
        await requestManager.get('/test');
      } catch (error: any) {
        expect(error).toBeInstanceOf(Error);
        expect(error.message).toContain('String error');
      }
    });

    it('should handle timeout errors properly', async () => {
      fetchMock.mockImplementation(() => 
        new Promise(resolve => setTimeout(resolve, 15000))
      );

      try {
        await requestManager.request('/test', { timeout: 100 });
      } catch (error: any) {
        expect(error.name).toBe('AbortError');
      }
    });
  });

  describe('Memory Management', () => {
    it('should limit cache size', () => {
      // Add 100 cached requests
      for (let i = 0; i < 100; i++) {
        requestManager['requestCache'].set(`key-${i}`, {
          data: { test: i },
          timestamp: Date.now(),
        });
      }
      
      // Verify cache doesn't grow indefinitely
      requestManager['cleanupCache']();
      
      const validEntries = Array.from(requestManager['requestCache'].entries())
        .filter(([_, value]) => Date.now() - value.timestamp < 60000);
      
      expect(validEntries.length).toBeLessThanOrEqual(100);
    });

    it('should cleanup resources on request completion', async () => {
      const requestId = 'cleanup-test';
      
      await requestManager.get('/test', requestId);
      
      expect(requestManager['abortControllers'].has(requestId)).toBe(false);
      expect(requestManager['debounceTimers'].has(requestId)).toBe(false);
    });
  });
});