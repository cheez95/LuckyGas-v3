/**
 * Fetch with exponential backoff retry logic
 * Automatically retries failed requests with increasing delays
 */

interface RetryOptions {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffFactor?: number;
  retryCondition?: (error: any) => boolean;
}

const DEFAULT_OPTIONS: RetryOptions = {
  maxRetries: 3,
  initialDelay: 1000, // 1 second
  maxDelay: 10000,   // 10 seconds
  backoffFactor: 2,
  retryCondition: (error) => {
    // Retry on network errors or 5xx server errors
    if (!error.response) return true; // Network error
    const status = error.response?.status;
    return status >= 500 && status < 600;
  }
};

/**
 * Sleep for a specified duration
 */
const sleep = (ms: number): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms));

/**
 * Calculate delay with jitter to prevent thundering herd
 */
const calculateDelay = (
  attempt: number, 
  initialDelay: number, 
  maxDelay: number, 
  backoffFactor: number
): number => {
  const exponentialDelay = initialDelay * Math.pow(backoffFactor, attempt);
  const delayWithJitter = exponentialDelay * (0.5 + Math.random() * 0.5);
  return Math.min(delayWithJitter, maxDelay);
};

/**
 * Fetch with retry logic using exponential backoff
 */
export async function fetchWithRetry<T>(
  fetchFn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  let lastError: any;

  for (let attempt = 0; attempt <= opts.maxRetries!; attempt++) {
    try {
      // Log retry attempt in development
      if (attempt > 0 && import.meta.env.DEV) {
        // console.log(`🔄 Retry attempt ${attempt}/${opts.maxRetries}`);
      }

      const result = await fetchFn();
      
      // Success - return result
      if (attempt > 0 && import.meta.env.DEV) {
        // console.log(`✅ Request succeeded after ${attempt} retries`);
      }
      
      return result;
    } catch (error: any) {
      lastError = error;

      // Check if we should retry
      const shouldRetry = opts.retryCondition!(error);
      const isLastAttempt = attempt === opts.maxRetries;

      if (!shouldRetry || isLastAttempt) {
        // Don't retry - throw the error
        if (import.meta.env.DEV) {
          console.error(`❌ Request failed, not retrying:`, error.message);
        }
        throw error;
      }

      // Calculate delay for next retry
      const delay = calculateDelay(
        attempt,
        opts.initialDelay!,
        opts.maxDelay!,
        opts.backoffFactor!
      );

      if (import.meta.env.DEV) {
        // console.log(`⏳ Waiting ${Math.round(delay)}ms before retry...`);
      }

      // Wait before retrying
      await sleep(delay);
    }
  }

  // Should never reach here, but throw last error just in case
  throw lastError;
}

/**
 * Wrapper for axios requests with retry logic
 */
export function withRetry<T = any>(
  axiosCall: () => Promise<T>,
  options?: RetryOptions
): Promise<T> {
  return fetchWithRetry(axiosCall, options);
}

/**
 * Check if an error is retryable
 */
export function isRetryableError(error: any): boolean {
  // Network errors
  if (!error.response) return true;
  
  // Server errors (5xx)
  const status = error.response?.status;
  if (status >= 500 && status < 600) return true;
  
  // Rate limiting (429)
  if (status === 429) return true;
  
  // Request timeout (408)
  if (status === 408) return true;
  
  return false;
}

/**
 * Create a retry wrapper for API client methods
 */
export function createRetryWrapper(options?: RetryOptions) {
  return function <T>(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      return fetchWithRetry(
        () => originalMethod.apply(this, args),
        options
      );
    };

    return descriptor;
  };
}