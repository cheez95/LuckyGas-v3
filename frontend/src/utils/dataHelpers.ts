/**
 * Universal data helpers for safe array handling
 * Prevents "map is not a function" errors by ensuring data is always an array
 */

// Universal helper to safely extract arrays from any response format
export const toArray = <T = any>(data: any, fieldName: string | null = null): T[] => {
  // Log for debugging in development
  if (process.env.NODE_ENV === 'development') {
    // console.log(`[toArray] called with:`, data, `fieldName:`, fieldName);
  }
  
  // If already an array, return it
  if (Array.isArray(data)) {
    return data as T[];
  }
  
  // If null/undefined, return empty array
  if (data === null || data === undefined) {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[toArray] Data is null/undefined, returning empty array');
    }
    return [];
  }
  
  // If it's an object, try common patterns
  if (typeof data === 'object') {
    // Try specific field name if provided
    if (fieldName && Array.isArray(data[fieldName])) {
      if (process.env.NODE_ENV === 'development') {
        // console.log(`[toArray] Found array in field: ${fieldName}`);
      }
      return data[fieldName] as T[];
    }
    
    // Try common field names used in the API responses
    const commonFields = [
      'data', 
      'items', 
      'results', 
      'list', 
      'drivers', 
      'customers', 
      'orders', 
      'routes',
      'users',
      'deliveries',
      'products',
      'analytics',
      'reports',
      'notifications',
      'stops',
      'metrics'
    ];
    
    for (const field of commonFields) {
      if (data.hasOwnProperty(field) && Array.isArray(data[field])) {
        if (process.env.NODE_ENV === 'development') {
          // console.log(`[toArray] Found array in common field: ${field}`);
        }
        return data[field] as T[];
      }
    }
    
    // Check for paginated responses
    if (data.content && Array.isArray(data.content)) {
      if (process.env.NODE_ENV === 'development') {
        // console.log('[toArray] Found array in paginated response (content field)');
      }
      return data.content as T[];
    }
    
    // If object has exactly one property that's an array, use it
    const keys = Object.keys(data);
    if (keys.length === 1 && Array.isArray(data[keys[0]])) {
      if (process.env.NODE_ENV === 'development') {
        // console.log(`[toArray] Found array in single field: ${keys[0]}`);
      }
      return data[keys[0]] as T[];
    }
    
    // Check if it's a single item that should be wrapped in an array
    if (data.id || data._id || data.uuid) {
      if (process.env.NODE_ENV === 'development') {
        // console.log('[toArray] Wrapping single object in array');
      }
      return [data] as T[];
    }
  }
  
  // Last resort - return empty array
  if (process.env.NODE_ENV === 'development') {
    console.warn('[toArray] Could not extract array from:', data);
  }
  return [];
};

// Safe map function that always works
export const safeMap = <T, R>(
  data: any, 
  mapFn: (item: T, index: number, array: T[]) => R, 
  fieldName: string | null = null
): R[] => {
  const array = toArray<T>(data, fieldName);
  return array.map(mapFn);
};

// Ensure value is always an array (simpler version for inline use)
export const ensureArray = <T = any>(value: any): T[] => {
  if (Array.isArray(value)) return value;
  if (!value) return [];
  return [value];
};

// Safe filter function
export const safeFilter = <T>(
  data: any,
  filterFn: (item: T, index: number, array: T[]) => boolean,
  fieldName: string | null = null
): T[] => {
  const array = toArray<T>(data, fieldName);
  return array.filter(filterFn);
};

// Safe find function
export const safeFind = <T>(
  data: any,
  findFn: (item: T, index: number, array: T[]) => boolean,
  fieldName: string | null = null
): T | undefined => {
  const array = toArray<T>(data, fieldName);
  return array.find(findFn);
};

// Safe reduce function
export const safeReduce = <T, R>(
  data: any,
  reduceFn: (acc: R, item: T, index: number, array: T[]) => R,
  initialValue: R,
  fieldName: string | null = null
): R => {
  const array = toArray<T>(data, fieldName);
  return array.reduce(reduceFn, initialValue);
};

// Safe some function - checks if at least one element passes the test
export const safeSome = <T>(
  data: any,
  someFn: (item: T, index: number, array: T[]) => boolean,
  fieldName: string | null = null
): boolean => {
  const array = toArray<T>(data, fieldName);
  return array.some(someFn);
};

// Safe every function - checks if all elements pass the test
export const safeEvery = <T>(
  data: any,
  everyFn: (item: T, index: number, array: T[]) => boolean,
  fieldName: string | null = null
): boolean => {
  const array = toArray<T>(data, fieldName);
  if (array.length === 0) return true; // Empty array returns true for every()
  return array.every(everyFn);
};

// Safe includes function - checks if array includes a value
export const safeIncludes = <T>(
  data: any,
  searchElement: T,
  fieldName: string | null = null
): boolean => {
  const array = toArray<T>(data, fieldName);
  return array.includes(searchElement);
};

// Safe forEach function
export const safeForEach = <T>(
  data: any,
  forEachFn: (item: T, index: number, array: T[]) => void,
  fieldName: string | null = null
): void => {
  const array = toArray<T>(data, fieldName);
  array.forEach(forEachFn);
};

// Safe length check
export const safeLength = (data: any, fieldName: string | null = null): number => {
  const array = toArray(data, fieldName);
  return array.length;
};

// Check if data has items
export const hasItems = (data: any, fieldName: string | null = null): boolean => {
  return safeLength(data, fieldName) > 0;
};

// Get first item safely
export const safeFirst = <T>(data: any, fieldName: string | null = null): T | undefined => {
  const array = toArray<T>(data, fieldName);
  return array[0];
};

// Get last item safely
export const safeLast = <T>(data: any, fieldName: string | null = null): T | undefined => {
  const array = toArray<T>(data, fieldName);
  return array[array.length - 1];
};

// Safe slice
export const safeSlice = <T>(
  data: any,
  start?: number,
  end?: number,
  fieldName: string | null = null
): T[] => {
  const array = toArray<T>(data, fieldName);
  return array.slice(start, end);
};

// Safe sort
export const safeSort = <T>(
  data: any,
  compareFn?: (a: T, b: T) => number,
  fieldName: string | null = null
): T[] => {
  const array = toArray<T>(data, fieldName);
  return [...array].sort(compareFn);
};

// Export all functions as a namespace for convenience
export const SafeArray = {
  toArray,
  map: safeMap,
  filter: safeFilter,
  find: safeFind,
  reduce: safeReduce,
  some: safeSome,
  every: safeEvery,
  includes: safeIncludes,
  forEach: safeForEach,
  length: safeLength,
  hasItems,
  first: safeFirst,
  last: safeLast,
  slice: safeSlice,
  sort: safeSort,
  ensure: ensureArray
};

export default SafeArray;