/**
 * usePagination Hook
 * Provides efficient pagination for large datasets
 * Prevents loading all data at once to reduce memory usage
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useCleanup } from './useCleanup';

export interface PaginationConfig {
  pageSize?: number;
  initialPage?: number;
  cachePages?: boolean;
  maxCachedPages?: number;
}

export interface PaginationState<T> {
  data: T[];
  currentPage: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  loading: boolean;
  error: Error | null;
}

export interface PaginationControls {
  nextPage: () => void;
  prevPage: () => void;
  goToPage: (page: number) => void;
  setPageSize: (size: number) => void;
  refresh: () => void;
}

interface CachedPage<T> {
  page: number;
  data: T[];
  timestamp: number;
}

const DEFAULT_PAGE_SIZE = 20;
const DEFAULT_MAX_CACHED_PAGES = 5;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export function usePagination<T>(
  fetchFunction: (page: number, pageSize: number, signal?: AbortSignal) => Promise<{
    data: T[];
    total: number;
  }>,
  config: PaginationConfig = {}
): [PaginationState<T>, PaginationControls] {
  const cleanup = useCleanup();
  
  const {
    pageSize: initialPageSize = DEFAULT_PAGE_SIZE,
    initialPage = 1,
    cachePages = true,
    maxCachedPages = DEFAULT_MAX_CACHED_PAGES,
  } = config;

  const [data, setData] = useState<T[]>([]);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [pageCache, setPageCache] = useState<Map<string, CachedPage<T>>>(new Map());

  // Calculate total pages
  const totalPages = useMemo(
    () => Math.ceil(totalItems / pageSize),
    [totalItems, pageSize]
  );

  // Generate cache key
  const getCacheKey = useCallback(
    (page: number, size: number) => `${page}-${size}`,
    []
  );

  // Clean expired cache entries
  const cleanCache = useCallback(() => {
    if (!cachePages) return;

    const now = Date.now();
    const newCache = new Map<string, CachedPage<T>>();
    
    pageCache.forEach((cached, key) => {
      if (now - cached.timestamp < CACHE_TTL) {
        newCache.set(key, cached);
      }
    });

    // Limit cache size
    if (newCache.size > maxCachedPages) {
      const entries = Array.from(newCache.entries());
      entries.sort((a, b) => b[1].timestamp - a[1].timestamp);
      const limited = entries.slice(0, maxCachedPages);
      setPageCache(new Map(limited));
    } else if (newCache.size !== pageCache.size) {
      setPageCache(newCache);
    }
  }, [pageCache, cachePages, maxCachedPages]);

  // Fetch page data
  const fetchPage = useCallback(
    async (page: number, size: number) => {
      // Check cache first
      if (cachePages) {
        const cacheKey = getCacheKey(page, size);
        const cached = pageCache.get(cacheKey);
        
        if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
          // console.log(`[usePagination] Using cached data for page ${page}`);
          setData(cached.data);
          return;
        }
      }

      setLoading(true);
      setError(null);

      try {
        const signal = cleanup.getSignal();
        const result = await fetchFunction(page, size, signal);

        // Only update state if still mounted
        if (cleanup.isMounted()) {
          setData(result.data);
          setTotalItems(result.total);

          // Cache the page if enabled
          if (cachePages) {
            const cacheKey = getCacheKey(page, size);
            const newCache = new Map(pageCache);
            newCache.set(cacheKey, {
              page,
              data: result.data,
              timestamp: Date.now(),
            });
            setPageCache(newCache);
          }
        }
      } catch (err: any) {
        // Don't update state for aborted requests
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          return;
        }

        console.error('[usePagination] Fetch error:', err);
        if (cleanup.isMounted()) {
          setError(err);
          setData([]);
        }
      } finally {
        if (cleanup.isMounted()) {
          setLoading(false);
        }
      }
    },
    [fetchFunction, cleanup, pageCache, cachePages, getCacheKey]
  );

  // Fetch data when page or pageSize changes
  useEffect(() => {
    fetchPage(currentPage, pageSize);
  }, [currentPage, pageSize]);

  // Clean cache periodically
  useEffect(() => {
    if (!cachePages) return;

    const interval = cleanup.setInterval(() => {
      cleanCache();
    }, 60000); // Clean every minute

    return () => {
      cleanup.clearInterval(interval);
    };
  }, [cleanCache, cleanup, cachePages]);

  // Pagination controls
  const controls: PaginationControls = useMemo(
    () => ({
      nextPage: () => {
        if (currentPage < totalPages) {
          setCurrentPage(prev => prev + 1);
        }
      },
      prevPage: () => {
        if (currentPage > 1) {
          setCurrentPage(prev => prev - 1);
        }
      },
      goToPage: (page: number) => {
        if (page >= 1 && page <= totalPages) {
          setCurrentPage(page);
        }
      },
      setPageSize: (size: number) => {
        if (size > 0 && size !== pageSize) {
          setPageSize(size);
          setCurrentPage(1); // Reset to first page
          setPageCache(new Map()); // Clear cache on page size change
        }
      },
      refresh: () => {
        // Clear cache for current page
        if (cachePages) {
          const cacheKey = getCacheKey(currentPage, pageSize);
          const newCache = new Map(pageCache);
          newCache.delete(cacheKey);
          setPageCache(newCache);
        }
        fetchPage(currentPage, pageSize);
      },
    }),
    [currentPage, totalPages, pageSize, pageCache, cachePages, getCacheKey, fetchPage]
  );

  // State object
  const state: PaginationState<T> = {
    data,
    currentPage,
    pageSize,
    totalItems,
    totalPages,
    loading,
    error,
  };

  return [state, controls];
}

// Export helper for table integration
export function getPaginationProps(state: PaginationState<any>, controls: PaginationControls) {
  return {
    pagination: {
      current: state.currentPage,
      pageSize: state.pageSize,
      total: state.totalItems,
      showSizeChanger: true,
      showQuickJumper: true,
      pageSizeOptions: ['10', '20', '50', '100'],
      onChange: (page: number, pageSize?: number) => {
        if (pageSize && pageSize !== state.pageSize) {
          controls.setPageSize(pageSize);
        } else {
          controls.goToPage(page);
        }
      },
      onShowSizeChange: (_: number, size: number) => {
        controls.setPageSize(size);
      },
    },
    loading: state.loading,
    dataSource: state.data,
  };
}