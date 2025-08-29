/**
 * useCleanup Hook
 * Provides consistent cleanup patterns for React components
 * Prevents memory leaks from uncancelled requests, timers, and listeners
 */

import { useEffect, useRef, useCallback } from 'react';

interface CleanupManager {
  abortController: AbortController;
  timers: Set<NodeJS.Timeout>;
  intervals: Set<NodeJS.Timeout>;
  listeners: Array<{ target: any; event: string; handler: any }>;
  subscriptions: Array<() => void>;
  cancelled: boolean;
}

export function useCleanup() {
  const cleanupRef = useRef<CleanupManager>({
    abortController: new AbortController(),
    timers: new Set(),
    intervals: new Set(),
    listeners: [],
    subscriptions: [],
    cancelled: false,
  });

  // Create a new AbortController for each component instance
  useEffect(() => {
    const manager = cleanupRef.current;
    manager.abortController = new AbortController();
    manager.cancelled = false;

    return () => {
      // Mark as cancelled
      manager.cancelled = true;

      // Abort all fetch requests
      if (!manager.abortController.signal.aborted) {
        manager.abortController.abort();
      }

      // Clear all timers
      manager.timers.forEach(timer => clearTimeout(timer));
      manager.timers.clear();

      // Clear all intervals
      manager.intervals.forEach(interval => clearInterval(interval));
      manager.intervals.clear();

      // Remove all event listeners
      manager.listeners.forEach(({ target, event, handler }) => {
        if (target && typeof target.removeEventListener === 'function') {
          target.removeEventListener(event, handler);
        }
      });
      manager.listeners = [];

      // Call all subscription cleanup functions
      manager.subscriptions.forEach(cleanup => {
        try {
          cleanup();
        } catch (error) {
          console.error('[useCleanup] Error during subscription cleanup:', error);
        }
      });
      manager.subscriptions = [];

      // Log cleanup in development
      if (process.env.NODE_ENV === 'development') {
        // console.log('[useCleanup] Component cleanup completed');
      }
    };
  }, []);

  /**
   * Get AbortSignal for fetch requests
   */
  const getSignal = useCallback(() => {
    return cleanupRef.current.abortController.signal;
  }, []);

  /**
   * Check if component is still mounted
   */
  const isMounted = useCallback(() => {
    return !cleanupRef.current.cancelled;
  }, []);

  /**
   * Safe setTimeout that auto-cleans on unmount
   */
  const setTimeout = useCallback((callback: () => void, delay: number): NodeJS.Timeout => {
    const manager = cleanupRef.current;
    const timer = window.setTimeout(() => {
      manager.timers.delete(timer);
      if (isMounted()) {
        callback();
      }
    }, delay);
    manager.timers.add(timer);
    return timer;
  }, [isMounted]);

  /**
   * Safe setInterval that auto-cleans on unmount
   */
  const setInterval = useCallback((callback: () => void, interval: number): NodeJS.Timeout => {
    const manager = cleanupRef.current;
    const intervalId = window.setInterval(() => {
      if (isMounted()) {
        callback();
      }
    }, interval);
    manager.intervals.add(intervalId);
    return intervalId;
  }, [isMounted]);

  /**
   * Clear a timer created with our setTimeout
   */
  const clearTimeout = useCallback((timer: NodeJS.Timeout) => {
    const manager = cleanupRef.current;
    window.clearTimeout(timer);
    manager.timers.delete(timer);
  }, []);

  /**
   * Clear an interval created with our setInterval
   */
  const clearInterval = useCallback((interval: NodeJS.Timeout) => {
    const manager = cleanupRef.current;
    window.clearInterval(interval);
    manager.intervals.delete(interval);
  }, []);

  /**
   * Safe addEventListener that auto-removes on unmount
   */
  const addEventListener = useCallback(
    (target: any, event: string, handler: any, options?: any) => {
      const manager = cleanupRef.current;
      target.addEventListener(event, handler, options);
      manager.listeners.push({ target, event, handler });
    },
    []
  );

  /**
   * Remove event listener and update tracking
   */
  const removeEventListener = useCallback(
    (target: any, event: string, handler: any) => {
      const manager = cleanupRef.current;
      target.removeEventListener(event, handler);
      manager.listeners = manager.listeners.filter(
        l => !(l.target === target && l.event === event && l.handler === handler)
      );
    },
    []
  );

  /**
   * Add a subscription cleanup function
   */
  const addSubscription = useCallback((cleanup: () => void) => {
    cleanupRef.current.subscriptions.push(cleanup);
  }, []);

  /**
   * Safe fetch with automatic abort on unmount
   */
  const safeFetch = useCallback(
    async (url: string, options?: RequestInit) => {
      const signal = getSignal();
      
      try {
        const response = await fetch(url, {
          ...options,
          signal,
        });

        // Check if still mounted before processing
        if (!isMounted()) {
          throw new Error('Component unmounted');
        }

        return response;
      } catch (error: any) {
        // Don't log abort errors
        if (error.name === 'AbortError') {
          // console.log('[useCleanup] Request aborted due to component unmount');
          throw error;
        }
        
        // Log other errors
        console.error('[useCleanup] Fetch error:', error);
        throw error;
      }
    },
    [getSignal, isMounted]
  );

  /**
   * Create a safe callback that only runs if mounted
   */
  const safeCallback = useCallback(
    <T extends (...args: any[]) => any>(callback: T): T => {
      return ((...args: Parameters<T>) => {
        if (isMounted()) {
          return callback(...args);
        }
        // console.log('[useCleanup] Callback skipped - component unmounted');
      }) as T;
    },
    [isMounted]
  );

  /**
   * Safe state update that only runs if mounted
   */
  const safeSetState = useCallback(
    <T>(setState: React.Dispatch<React.SetStateAction<T>>) => {
      return (value: React.SetStateAction<T>) => {
        if (isMounted()) {
          setState(value);
        } else {
          // console.log('[useCleanup] State update skipped - component unmounted');
        }
      };
    },
    [isMounted]
  );

  return {
    // Core utilities
    getSignal,
    isMounted,
    
    // Timer management
    setTimeout,
    setInterval,
    clearTimeout,
    clearInterval,
    
    // Event management
    addEventListener,
    removeEventListener,
    
    // Subscription management
    addSubscription,
    
    // Safe operations
    safeFetch,
    safeCallback,
    safeSetState,
  };
}

// Export type for better TypeScript support
export type CleanupHook = ReturnType<typeof useCleanup>;