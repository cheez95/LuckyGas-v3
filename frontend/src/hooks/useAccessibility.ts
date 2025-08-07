/**
 * Accessibility hooks and utilities for WCAG 2.1 AA compliance
 */

import { useEffect, useRef, useCallback, useState } from 'react';

/**
 * Hook for managing ARIA live region announcements
 * Used for dynamic content updates that should be announced to screen readers
 */
export function useAriaLive(mode: 'polite' | 'assertive' = 'polite') {
  const [announcement, setAnnouncement] = useState('');
  const timeoutRef = useRef<NodeJS.Timeout>();

  const announce = useCallback((message: string, clearAfter = 1000) => {
    setAnnouncement(message);
    
    // Clear the announcement after a delay to allow for repeated announcements
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    timeoutRef.current = setTimeout(() => {
      setAnnouncement('');
    }, clearAfter);
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    announce,
    ariaLiveProps: {
      'aria-live': mode,
      'aria-atomic': 'true',
      'aria-relevant': 'additions text',
      style: {
        position: 'absolute' as const,
        left: '-10000px',
        width: '1px',
        height: '1px',
        overflow: 'hidden',
      },
      children: announcement,
    },
  };
}

/**
 * Hook for managing focus trap within a container
 * Used for modals, dropdowns, and other overlay components
 */
export function useFocusTrap(isActive = true) {
  const containerRef = useRef<HTMLElement>(null);
  const initialFocusRef = useRef<HTMLElement>();

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const container = containerRef.current;
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    // Store the initially focused element
    initialFocusRef.current = document.activeElement as HTMLElement;

    // Focus first focusable element
    if (firstFocusable) {
      firstFocusable.focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable?.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable?.focus();
        }
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Return focus to initial element
        initialFocusRef.current?.focus();
      }
    };

    container.addEventListener('keydown', handleKeyDown);
    container.addEventListener('keydown', handleEscape);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      container.removeEventListener('keydown', handleEscape);
      
      // Return focus to initial element on cleanup
      if (initialFocusRef.current && document.body.contains(initialFocusRef.current)) {
        initialFocusRef.current.focus();
      }
    };
  }, [isActive]);

  return containerRef;
}

/**
 * Hook for keyboard navigation in lists and grids
 * Supports arrow keys, Home, End, Enter, and Space
 */
export function useKeyboardNavigation<T extends HTMLElement>({
  onSelect,
  orientation = 'vertical',
  wrap = false,
}: {
  onSelect?: (index: number, element: T) => void;
  orientation?: 'vertical' | 'horizontal' | 'grid';
  wrap?: boolean;
}) {
  const containerRef = useRef<HTMLElement>(null);
  const [focusedIndex, setFocusedIndex] = useState(0);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!containerRef.current) return;

    const items = containerRef.current.querySelectorAll<T>('[role="option"], [role="menuitem"], [role="tab"], [role="gridcell"]');
    const currentIndex = Array.from(items).findIndex(item => item === document.activeElement);
    
    if (currentIndex === -1) return;

    let nextIndex = currentIndex;

    switch (e.key) {
      case 'ArrowDown':
        if (orientation === 'vertical' || orientation === 'grid') {
          e.preventDefault();
          nextIndex = wrap
            ? (currentIndex + 1) % items.length
            : Math.min(currentIndex + 1, items.length - 1);
        }
        break;

      case 'ArrowUp':
        if (orientation === 'vertical' || orientation === 'grid') {
          e.preventDefault();
          nextIndex = wrap
            ? (currentIndex - 1 + items.length) % items.length
            : Math.max(currentIndex - 1, 0);
        }
        break;

      case 'ArrowRight':
        if (orientation === 'horizontal' || orientation === 'grid') {
          e.preventDefault();
          nextIndex = wrap
            ? (currentIndex + 1) % items.length
            : Math.min(currentIndex + 1, items.length - 1);
        }
        break;

      case 'ArrowLeft':
        if (orientation === 'horizontal' || orientation === 'grid') {
          e.preventDefault();
          nextIndex = wrap
            ? (currentIndex - 1 + items.length) % items.length
            : Math.max(currentIndex - 1, 0);
        }
        break;

      case 'Home':
        e.preventDefault();
        nextIndex = 0;
        break;

      case 'End':
        e.preventDefault();
        nextIndex = items.length - 1;
        break;

      case 'Enter':
      case ' ':
        e.preventDefault();
        if (onSelect) {
          onSelect(currentIndex, items[currentIndex]);
        }
        break;

      default:
        return;
    }

    if (nextIndex !== currentIndex) {
      items[nextIndex].focus();
      setFocusedIndex(nextIndex);
    }
  }, [orientation, wrap, onSelect]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('keydown', handleKeyDown as any);
    return () => container.removeEventListener('keydown', handleKeyDown as any);
  }, [handleKeyDown]);

  return {
    containerRef,
    focusedIndex,
    keyboardNavigationProps: {
      role: orientation === 'grid' ? 'grid' : 'listbox',
      'aria-orientation': orientation === 'horizontal' ? 'horizontal' : 'vertical',
    },
  };
}

/**
 * Hook for skip navigation links
 * Provides keyboard shortcuts to skip to main content
 */
export function useSkipLinks() {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Alt + 1: Skip to main content
      if (e.altKey && e.key === '1') {
        e.preventDefault();
        const main = document.querySelector('main') || document.querySelector('[role="main"]');
        if (main instanceof HTMLElement) {
          main.focus();
          main.scrollIntoView({ behavior: 'smooth' });
        }
      }
      
      // Alt + 2: Skip to navigation
      if (e.altKey && e.key === '2') {
        e.preventDefault();
        const nav = document.querySelector('nav') || document.querySelector('[role="navigation"]');
        if (nav instanceof HTMLElement) {
          nav.focus();
        }
      }
      
      // Alt + 3: Skip to search
      if (e.altKey && e.key === '3') {
        e.preventDefault();
        const search = document.querySelector('[role="search"] input, [type="search"]');
        if (search instanceof HTMLElement) {
          search.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);
}

/**
 * Hook for managing roving tabindex in composite widgets
 * Only one item in the group has tabindex="0" at a time
 */
export function useRovingTabIndex(itemCount: number, defaultIndex = 0) {
  const [activeIndex, setActiveIndex] = useState(defaultIndex);

  const getRovingProps = useCallback((index: number) => ({
    tabIndex: index === activeIndex ? 0 : -1,
    onFocus: () => setActiveIndex(index),
  }), [activeIndex]);

  return {
    activeIndex,
    setActiveIndex,
    getRovingProps,
  };
}

/**
 * Hook for detecting and announcing form validation errors
 */
export function useFormErrorAnnouncement() {
  const { announce, ariaLiveProps } = useAriaLive('assertive');
  const previousErrorsRef = useRef<string[]>([]);

  const announceErrors = useCallback((errors: Record<string, string>) => {
    const errorMessages = Object.values(errors).filter(Boolean);
    const newErrors = errorMessages.filter(
      error => !previousErrorsRef.current.includes(error)
    );

    if (newErrors.length > 0) {
      const message = newErrors.length === 1
        ? `錯誤: ${newErrors[0]}`
        : `發現 ${newErrors.length} 個錯誤. ${newErrors.join('. ')}`;
      
      announce(message);
    }

    previousErrorsRef.current = errorMessages;
  }, [announce]);

  return {
    announceErrors,
    errorAnnouncerProps: ariaLiveProps,
  };
}

/**
 * Hook for managing loading states with screen reader announcements
 */
export function useLoadingAnnouncement() {
  const { announce, ariaLiveProps } = useAriaLive('polite');
  const [isLoading, setIsLoading] = useState(false);

  const startLoading = useCallback((message = '載入中...') => {
    setIsLoading(true);
    announce(message);
  }, [announce]);

  const stopLoading = useCallback((message = '載入完成') => {
    setIsLoading(false);
    announce(message);
  }, [announce]);

  return {
    isLoading,
    startLoading,
    stopLoading,
    loadingAnnouncerProps: ariaLiveProps,
  };
}

/**
 * Hook for detecting user's preferred motion settings
 */
export function useReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    // Check if addEventListener is supported
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      // Fallback for older browsers
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  return prefersReducedMotion;
}

/**
 * Hook for high contrast mode detection
 */
export function useHighContrast() {
  const [prefersHighContrast, setPrefersHighContrast] = useState(
    () => window.matchMedia('(prefers-contrast: high)').matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: high)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersHighContrast(e.matches);
    };

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  return prefersHighContrast;
}

export default {
  useAriaLive,
  useFocusTrap,
  useKeyboardNavigation,
  useSkipLinks,
  useRovingTabIndex,
  useFormErrorAnnouncement,
  useLoadingAnnouncement,
  useReducedMotion,
  useHighContrast,
};