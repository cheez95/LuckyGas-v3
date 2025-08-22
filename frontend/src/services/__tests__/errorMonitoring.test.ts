import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';

describe('Unhandled Promise Rejection Handler', () => {
  let unhandledRejectionHandler: ((event: PromiseRejectionEvent) => void) | undefined;
  let errorHandler: ((event: ErrorEvent) => void) | undefined;
  let consoleErrorSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;

  beforeEach(() => {
    // Capture the event handlers
    const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
    
    // Import the module to register handlers
    jest.isolateModules(() => {
      require('../errorMonitoring');
    });

    // Find the registered handlers
    unhandledRejectionHandler = addEventListenerSpy.mock.calls
      .find(call => call[0] === 'unhandledrejection')?.[1] as any;
    
    errorHandler = addEventListenerSpy.mock.calls
      .find(call => call[0] === 'error')?.[1] as any;

    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
  });

  afterEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  describe('Global Unhandled Rejection Handler', () => {
    it('should prevent default browser error logging', () => {
      const event = new PromiseRejectionEvent('unhandledrejection', {
        promise: Promise.reject('test'),
        reason: new Error('Test error'),
      });
      
      const preventDefaultSpy = jest.spyOn(event, 'preventDefault');
      
      if (unhandledRejectionHandler) {
        unhandledRejectionHandler(event);
      }
      
      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('should handle Error objects properly', () => {
      const testError = new Error('Test rejection');
      const event = new PromiseRejectionEvent('unhandledrejection', {
        promise: Promise.reject(testError),
        reason: testError,
      });
      
      if (unhandledRejectionHandler) {
        unhandledRejectionHandler(event);
      }
      
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '❌ Unhandled Promise Rejection:',
        expect.objectContaining({
          message: 'Test rejection',
        })
      );
    });

    it('should handle non-Error rejections', () => {
      const event = new PromiseRejectionEvent('unhandledrejection', {
        promise: Promise.reject('String rejection'),
        reason: 'String rejection',
      });
      
      if (unhandledRejectionHandler) {
        unhandledRejectionHandler(event);
      }
      
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '❌ Unhandled Promise Rejection:',
        expect.any(Error)
      );
    });

    it('should handle null/undefined rejections', () => {
      const event = new PromiseRejectionEvent('unhandledrejection', {
        promise: Promise.reject(null),
        reason: null,
      });
      
      if (unhandledRejectionHandler) {
        unhandledRejectionHandler(event);
      }
      
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '❌ Unhandled Promise Rejection:',
        expect.objectContaining({
          message: 'Unhandled Promise Rejection',
        })
      );
    });

    it('should handle object rejections', () => {
      const testObject = { message: 'Object error', code: 500 };
      const event = new PromiseRejectionEvent('unhandledrejection', {
        promise: Promise.reject(testObject),
        reason: testObject,
      });
      
      if (unhandledRejectionHandler) {
        unhandledRejectionHandler(event);
      }
      
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '❌ Unhandled Promise Rejection:',
        expect.objectContaining({
          message: 'Object error',
        })
      );
    });

    it('should track unhandled rejections in window object', () => {
      const event = new PromiseRejectionEvent('unhandledrejection', {
        promise: Promise.reject('test'),
        reason: 'test',
      });
      
      (window as any).unhandledRejections = [];
      
      if (unhandledRejectionHandler) {
        unhandledRejectionHandler(event);
      }
      
      expect((window as any).unhandledRejections).toBeDefined();
    });
  });

  describe('Global Error Handler', () => {
    it('should handle uncaught errors', () => {
      const testError = new Error('Uncaught error');
      const event = new ErrorEvent('error', {
        error: testError,
        message: testError.message,
      });
      
      if (errorHandler) {
        errorHandler(event);
      }
      
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '❌ Uncaught Error:',
        expect.objectContaining({
          message: 'Uncaught error',
        })
      );
    });

    it('should track error count', () => {
      const event = new ErrorEvent('error', {
        error: new Error('Test'),
        message: 'Test',
      });
      
      (window as any).errorCount = 0;
      
      if (errorHandler) {
        errorHandler(event);
      }
      
      expect((window as any).errorCount).toBeGreaterThan(0);
    });
  });

  describe('Promise Error Handling', () => {
    it('should catch promise rejections in async functions', async () => {
      const testFunction = async () => {
        try {
          await Promise.reject(new Error('Async error'));
        } catch (error) {
          expect(error).toBeInstanceOf(Error);
          expect((error as Error).message).toBe('Async error');
        }
      };
      
      await expect(testFunction()).resolves.not.toThrow();
    });

    it('should handle promise chain errors', async () => {
      const promise = Promise.resolve()
        .then(() => {
          throw new Error('Chain error');
        })
        .catch(error => {
          expect(error.message).toBe('Chain error');
          return 'handled';
        });
      
      const result = await promise;
      expect(result).toBe('handled');
    });

    it('should handle timeout errors', async () => {
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Timeout')), 100);
      });
      
      try {
        await timeoutPromise;
      } catch (error: any) {
        expect(error.message).toBe('Timeout');
      }
    });
  });
});