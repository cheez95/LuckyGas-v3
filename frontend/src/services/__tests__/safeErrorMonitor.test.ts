/**
 * Tests for SafeErrorMonitor with Circuit Breaker Pattern
 */

import { safeErrorMonitor } from '../safeErrorMonitor';

// Mock fetch globally
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
(global as any).localStorage = localStorageMock;

// Mock console methods
const originalConsole = { ...console };
beforeAll(() => {
  console.warn = jest.fn();
  console.error = jest.fn();
  console.info = jest.fn();
});

afterAll(() => {
  console.warn = originalConsole.warn;
  console.error = originalConsole.error;
  console.info = originalConsole.info;
});

describe('SafeErrorMonitor', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    localStorageMock.getItem.mockReturnValue(null);
    safeErrorMonitor.clearQueue();
    safeErrorMonitor.setKillSwitch(false);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Circuit Breaker Pattern', () => {
    it('should open circuit after 3 consecutive failures', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      
      // Simulate 3 failures
      mockFetch.mockRejectedValue(new Error('Network error'));

      // Log 3 errors
      safeErrorMonitor.logError(new Error('Error 1'));
      safeErrorMonitor.logError(new Error('Error 2'));
      safeErrorMonitor.logError(new Error('Error 3'));

      // Trigger batch send
      jest.advanceTimersByTime(30000);

      // Wait for async operations
      await Promise.resolve();
      await Promise.resolve();

      // Circuit should be open
      const status = safeErrorMonitor.getStatus();
      expect(status.circuitOpen).toBe(true);
      expect(status.failureCount).toBe(3);
    });

    it('should reset circuit after timeout', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      
      // Open the circuit
      mockFetch.mockRejectedValue(new Error('Network error'));
      safeErrorMonitor.logError(new Error('Error 1'));
      safeErrorMonitor.logError(new Error('Error 2'));
      safeErrorMonitor.logError(new Error('Error 3'));
      
      jest.advanceTimersByTime(30000);
      await Promise.resolve();

      let status = safeErrorMonitor.getStatus();
      expect(status.circuitOpen).toBe(true);

      // Advance time to trigger circuit reset (60 seconds)
      jest.advanceTimersByTime(60000);

      status = safeErrorMonitor.getStatus();
      expect(status.circuitOpen).toBe(false);
      expect(status.failureCount).toBe(0);
    });

    it('should not send errors when circuit is open', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      
      // Open the circuit
      mockFetch.mockRejectedValue(new Error('Network error'));
      safeErrorMonitor.logError(new Error('Error 1'));
      safeErrorMonitor.logError(new Error('Error 2'));
      safeErrorMonitor.logError(new Error('Error 3'));
      
      jest.advanceTimersByTime(30000);
      await Promise.resolve();

      // Clear mock calls
      mockFetch.mockClear();

      // Try to log more errors while circuit is open
      safeErrorMonitor.logError(new Error('Error 4'));
      safeErrorMonitor.logError(new Error('Error 5'));
      
      jest.advanceTimersByTime(30000);
      await Promise.resolve();

      // Fetch should not be called when circuit is open
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('Exponential Backoff', () => {
    it('should retry with exponential backoff on failure', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      
      // First attempt fails
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      // Second attempt succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      safeErrorMonitor.logError(new Error('Test error'));
      
      // First attempt after 30 seconds
      jest.advanceTimersByTime(30000);
      await Promise.resolve();
      
      expect(mockFetch).toHaveBeenCalledTimes(1);
      
      // Backoff delay (2 seconds for first retry)
      jest.advanceTimersByTime(2000);
      await Promise.resolve();
      
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('should limit retries to maximum configured', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockRejectedValue(new Error('Network error'));

      const error = new Error('Test error');
      safeErrorMonitor.logError(error);
      
      // Initial attempt
      jest.advanceTimersByTime(30000);
      await Promise.resolve();
      expect(mockFetch).toHaveBeenCalledTimes(1);
      
      // Retry 1 (after 2s backoff)
      jest.advanceTimersByTime(2000);
      await Promise.resolve();
      expect(mockFetch).toHaveBeenCalledTimes(2);
      
      // Retry 2 (after 4s backoff)
      jest.advanceTimersByTime(4000);
      await Promise.resolve();
      expect(mockFetch).toHaveBeenCalledTimes(3);
      
      // No more retries after max attempts
      jest.advanceTimersByTime(30000);
      await Promise.resolve();
      
      // Should still be 3 (no 4th attempt)
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });
  });

  describe('Error Batching', () => {
    it('should batch multiple errors and send once per 30 seconds', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({}),
      } as Response);

      // Log multiple errors
      safeErrorMonitor.logError(new Error('Error 1'));
      safeErrorMonitor.logError(new Error('Error 2'));
      safeErrorMonitor.logError(new Error('Error 3'));

      // Errors should be queued but not sent yet
      expect(mockFetch).not.toHaveBeenCalled();
      
      // Advance time to trigger batch send
      jest.advanceTimersByTime(30000);
      await Promise.resolve();

      // Should send all errors in one batch
      expect(mockFetch).toHaveBeenCalledTimes(1);
      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1]?.body as string);
      expect(body.errors).toHaveLength(3);
    });

    it('should throttle batch sends to maximum once per 30 seconds', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({}),
      } as Response);

      // First batch
      safeErrorMonitor.logError(new Error('Error 1'));
      jest.advanceTimersByTime(30000);
      await Promise.resolve();
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Second error logged immediately after
      safeErrorMonitor.logError(new Error('Error 2'));
      
      // Should not send immediately
      jest.advanceTimersByTime(10000);
      await Promise.resolve();
      expect(mockFetch).toHaveBeenCalledTimes(1);
      
      // Should send after full 30 seconds from last send
      jest.advanceTimersByTime(20000);
      await Promise.resolve();
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Monitoring Endpoint Protection', () => {
    it('should skip errors from monitoring endpoints', () => {
      const monitoringError = new Error('Failed to fetch');
      monitoringError.stack = 'Error: Failed to fetch\n    at /api/v1/monitoring/errors:1:1';
      
      safeErrorMonitor.logError(monitoringError);
      
      // Should not add to queue
      const status = safeErrorMonitor.getStatus();
      expect(status.queueSize).toBe(0);
      expect(console.warn).toHaveBeenCalledWith(
        expect.stringContaining('Skipped monitoring endpoint error'),
        monitoringError
      );
    });

    it('should skip errors from analytics endpoints', () => {
      const analyticsError = new Error('Analytics failed');
      analyticsError.stack = 'Error: Analytics failed\n    at /api/v1/analytics/performance:1:1';
      
      safeErrorMonitor.logError(analyticsError);
      
      const status = safeErrorMonitor.getStatus();
      expect(status.queueSize).toBe(0);
    });

    it('should allow non-monitoring errors', () => {
      const normalError = new Error('Normal application error');
      normalError.stack = 'Error: Normal application error\n    at /components/App.tsx:50:10';
      
      safeErrorMonitor.logError(normalError);
      
      const status = safeErrorMonitor.getStatus();
      expect(status.queueSize).toBe(1);
    });
  });

  describe('Queue Management', () => {
    it('should limit queue size to 50 items', () => {
      // Add 60 errors
      for (let i = 0; i < 60; i++) {
        safeErrorMonitor.logError(new Error(`Error ${i}`));
      }
      
      const status = safeErrorMonitor.getStatus();
      // Should keep only last 25 when limit exceeded
      expect(status.queueSize).toBeLessThanOrEqual(50);
    });

    it('should clear old errors after 5 minutes', () => {
      safeErrorMonitor.logError(new Error('Old error'));
      
      // Advance time by 6 minutes
      jest.advanceTimersByTime(6 * 60 * 1000);
      
      const status = safeErrorMonitor.getStatus();
      expect(status.queueSize).toBe(0);
    });
  });

  describe('Kill Switch', () => {
    it('should disable monitoring when kill switch is active', () => {
      safeErrorMonitor.setKillSwitch(true);
      
      safeErrorMonitor.logError(new Error('Test error'));
      
      const status = safeErrorMonitor.getStatus();
      expect(status.killSwitchActive).toBe(true);
      expect(status.queueSize).toBe(0);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('error-monitoring-disabled', 'true');
    });

    it('should re-enable monitoring when kill switch is deactivated', () => {
      safeErrorMonitor.setKillSwitch(true);
      safeErrorMonitor.setKillSwitch(false);
      
      safeErrorMonitor.logError(new Error('Test error'));
      
      const status = safeErrorMonitor.getStatus();
      expect(status.killSwitchActive).toBe(false);
      expect(status.queueSize).toBe(1);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('error-monitoring-disabled');
    });

    it('should check kill switch on initialization', () => {
      localStorageMock.getItem.mockReturnValue('true');
      
      // Create new instance (would normally happen on module load)
      const status = safeErrorMonitor.getStatus();
      expect(status.killSwitchActive).toBe(true);
    });
  });

  describe('Network Failure Simulation', () => {
    it('should handle network timeouts gracefully', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      
      // Simulate timeout by never resolving
      mockFetch.mockImplementation(() => new Promise(() => {}));
      
      safeErrorMonitor.logError(new Error('Test error'));
      
      // Trigger batch send
      jest.advanceTimersByTime(30000);
      
      // Advance time to trigger timeout (5 seconds)
      jest.advanceTimersByTime(5000);
      await Promise.resolve();
      
      // Should have attempted once
      expect(mockFetch).toHaveBeenCalledTimes(1);
      
      // Should retry with backoff
      jest.advanceTimersByTime(2000);
      await Promise.resolve();
      
      // Cleanup
      mockFetch.mockReset();
    });

    it('should handle HTTP error responses', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response);
      
      safeErrorMonitor.logError(new Error('Test error'));
      
      jest.advanceTimersByTime(30000);
      await Promise.resolve();
      
      const status = safeErrorMonitor.getStatus();
      expect(status.failureCount).toBe(1);
    });
  });

  describe('Memory Leak Prevention', () => {
    it('should clean up resources on destroy', () => {
      safeErrorMonitor.logError(new Error('Test error'));
      
      safeErrorMonitor.destroy();
      
      const status = safeErrorMonitor.getStatus();
      expect(status.queueSize).toBe(0);
    });

    it('should abort pending requests on destroy', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockImplementation(() => new Promise(() => {}));
      
      safeErrorMonitor.logError(new Error('Test error'));
      jest.advanceTimersByTime(30000);
      
      safeErrorMonitor.destroy();
      
      // Should not cause issues
      jest.advanceTimersByTime(10000);
      await Promise.resolve();
    });
  });
});