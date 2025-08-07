/**
 * Creates a debounced function that delays invoking func until after wait milliseconds
 * have elapsed since the last time the debounced function was invoked.
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  options?: {
    leading?: boolean;
    trailing?: boolean;
    maxWait?: number;
  }
): (...args: Parameters<T>) => void {
  const { leading = false, trailing = true, maxWait } = options || {};
  
  let timeout: number | null = null;
  let result: any;
  let lastArgs: Parameters<T> | null = null;
  let lastThis: any;
  let lastCallTime: number | null = null;
  let lastInvokeTime = 0;
  
  function invokeFunc(time: number) {
    const args = lastArgs;
    const thisArg = lastThis;
    
    lastArgs = lastThis = null;
    lastInvokeTime = time;
    result = func.apply(thisArg, args!);
    return result;
  }
  
  function leadingEdge(time: number) {
    // Reset any `maxWait` timer.
    lastInvokeTime = time;
    // Start the timer for the trailing edge.
    timeout = window.setTimeout(timerExpired, wait);
    // Invoke the leading edge.
    return leading ? invokeFunc(time) : result;
  }
  
  function timerExpired() {
    const time = Date.now();
    if (shouldInvoke(time)) {
      return trailingEdge(time);
    }
    // Restart the timer.
    const remaining = remainingWait(time);
    timeout = window.setTimeout(timerExpired, remaining);
  }
  
  function trailingEdge(time: number) {
    timeout = null;
    
    // Only invoke if we have `lastArgs` which means `func` has been
    // debounced at least once.
    if (trailing && lastArgs) {
      return invokeFunc(time);
    }
    lastArgs = lastThis = null;
    return result;
  }
  
  function cancel() {
    if (timeout !== null) {
      clearTimeout(timeout);
    }
    lastInvokeTime = 0;
    lastArgs = lastCallTime = lastThis = timeout = null;
  }
  
  function flush() {
    return timeout === null ? result : trailingEdge(Date.now());
  }
  
  function shouldInvoke(time: number) {
    const timeSinceLastCall = lastCallTime === null ? 0 : time - lastCallTime;
    const timeSinceLastInvoke = time - lastInvokeTime;
    
    // Either this is the first call, activity has stopped and we're at the
    // trailing edge, the system time has gone backwards and we're treating
    // it as the trailing edge, or we've hit the `maxWait` limit.
    return (
      lastCallTime === null ||
      timeSinceLastCall >= wait ||
      timeSinceLastCall < 0 ||
      (maxWait !== undefined && timeSinceLastInvoke >= maxWait)
    );
  }
  
  function remainingWait(time: number) {
    const timeSinceLastCall = lastCallTime === null ? 0 : time - lastCallTime;
    const timeSinceLastInvoke = time - lastInvokeTime;
    const timeWaiting = wait - timeSinceLastCall;
    
    return maxWait !== undefined
      ? Math.min(timeWaiting, maxWait - timeSinceLastInvoke)
      : timeWaiting;
  }
  
  function debounced(this: any, ...args: Parameters<T>) {
    const time = Date.now();
    const isInvoking = shouldInvoke(time);
    
    lastArgs = args;
    lastThis = this;
    lastCallTime = time;
    
    if (isInvoking) {
      if (timeout === null) {
        return leadingEdge(lastCallTime);
      }
      if (maxWait !== undefined) {
        // Handle invocations in a tight loop.
        timeout = window.setTimeout(timerExpired, wait);
        return invokeFunc(lastCallTime);
      }
    }
    if (timeout === null) {
      timeout = window.setTimeout(timerExpired, wait);
    }
    return result;
  }
  
  debounced.cancel = cancel;
  debounced.flush = flush;
  
  return debounced;
}

/**
 * Creates a throttled function that only invokes func at most once per
 * every wait milliseconds.
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  options?: {
    leading?: boolean;
    trailing?: boolean;
  }
): (...args: Parameters<T>) => void {
  return debounce(func, wait, {
    leading: options?.leading ?? true,
    trailing: options?.trailing ?? true,
    maxWait: wait,
  });
}