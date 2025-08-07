/**
 * Accessibility utilities for WCAG 2.1 AA compliance
 */

/**
 * Calculate relative luminance of a color
 * Based on WCAG formula: https://www.w3.org/WAI/GL/wiki/Relative_luminance
 */
function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Parse color string to RGB values
 */
function parseColor(color: string): { r: number; g: number; b: number } | null {
  // Handle hex colors
  if (color.startsWith('#')) {
    const hex = color.slice(1);
    if (hex.length === 3) {
      const [r, g, b] = hex.split('').map(c => parseInt(c + c, 16));
      return { r, g, b };
    } else if (hex.length === 6) {
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return { r, g, b };
    }
  }
  
  // Handle rgb/rgba colors
  const rgbMatch = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (rgbMatch) {
    return {
      r: parseInt(rgbMatch[1]),
      g: parseInt(rgbMatch[2]),
      b: parseInt(rgbMatch[3]),
    };
  }
  
  return null;
}

/**
 * Calculate contrast ratio between two colors
 * Returns a value between 1 and 21 (higher is better)
 */
export function getContrastRatio(color1: string, color2: string): number {
  const rgb1 = parseColor(color1);
  const rgb2 = parseColor(color2);
  
  if (!rgb1 || !rgb2) {
    console.warn('Invalid color format');
    return 1;
  }
  
  const lum1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);
  
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if color contrast meets WCAG requirements
 */
export function meetsWCAG(
  foreground: string,
  background: string,
  level: 'AA' | 'AAA' = 'AA',
  isLargeText = false
): boolean {
  const ratio = getContrastRatio(foreground, background);
  
  if (level === 'AA') {
    return isLargeText ? ratio >= 3 : ratio >= 4.5;
  } else {
    return isLargeText ? ratio >= 4.5 : ratio >= 7;
  }
}

/**
 * Suggest a better color if current doesn't meet WCAG
 */
export function suggestAccessibleColor(
  foreground: string,
  background: string,
  targetRatio = 4.5
): string {
  const currentRatio = getContrastRatio(foreground, background);
  
  if (currentRatio >= targetRatio) {
    return foreground;
  }
  
  const bgRgb = parseColor(background);
  const fgRgb = parseColor(foreground);
  
  if (!bgRgb || !fgRgb) {
    return foreground;
  }
  
  const bgLum = getLuminance(bgRgb.r, bgRgb.g, bgRgb.b);
  
  // Determine if we need a lighter or darker color
  const needsLighter = bgLum < 0.5;
  
  if (needsLighter) {
    // Suggest white or very light color
    return '#FFFFFF';
  } else {
    // Suggest black or very dark color
    return '#000000';
  }
}

/**
 * Format time for screen readers
 */
export function formatTimeForScreenReader(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  const time = dateObj.toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
  });
  
  const dateStr = dateObj.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  
  return `${dateStr} ${time}`;
}

/**
 * Generate unique ID for form elements
 */
export function generateId(prefix = 'element'): string {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Focus management utilities
 */
export const FocusManager = {
  /**
   * Save current focus and restore later
   */
  saveFocus(): HTMLElement | null {
    return document.activeElement as HTMLElement;
  },
  
  /**
   * Restore focus to previously saved element
   */
  restoreFocus(element: HTMLElement | null) {
    if (element && document.body.contains(element)) {
      element.focus();
    }
  },
  
  /**
   * Move focus to first focusable element in container
   */
  focusFirst(container: HTMLElement) {
    const focusable = this.getFocusableElements(container);
    if (focusable.length > 0) {
      focusable[0].focus();
    }
  },
  
  /**
   * Get all focusable elements within a container
   */
  getFocusableElements(container: HTMLElement): HTMLElement[] {
    const selector = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled]):not([type="hidden"])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
    ].join(', ');
    
    return Array.from(container.querySelectorAll<HTMLElement>(selector));
  },
};

/**
 * Screen reader utility functions
 */
export const ScreenReaderUtils = {
  /**
   * Create screen reader only text
   */
  srOnly(text: string): React.CSSProperties {
    return {
      position: 'absolute',
      left: '-10000px',
      top: 'auto',
      width: '1px',
      height: '1px',
      overflow: 'hidden',
    };
  },
  
  /**
   * Format number for screen readers (with proper language)
   */
  formatNumber(num: number, locale = 'zh-TW'): string {
    return new Intl.NumberFormat(locale).format(num);
  },
  
  /**
   * Format currency for screen readers
   */
  formatCurrency(amount: number, currency = 'TWD'): string {
    return new Intl.NumberFormat('zh-TW', {
      style: 'currency',
      currency,
    }).format(amount);
  },
  
  /**
   * Format percentage for screen readers
   */
  formatPercentage(value: number): string {
    return `${Math.round(value)}%`;
  },
};

/**
 * Keyboard navigation utilities
 */
export const KeyboardUtils = {
  /**
   * Check if key is navigation key
   */
  isNavigationKey(key: string): boolean {
    return [
      'ArrowUp',
      'ArrowDown',
      'ArrowLeft',
      'ArrowRight',
      'Home',
      'End',
      'PageUp',
      'PageDown',
    ].includes(key);
  },
  
  /**
   * Check if key is action key
   */
  isActionKey(key: string): boolean {
    return ['Enter', ' ', 'Space'].includes(key);
  },
  
  /**
   * Check if key is escape key
   */
  isEscapeKey(key: string): boolean {
    return key === 'Escape' || key === 'Esc';
  },
  
  /**
   * Get next index in a list with wrapping
   */
  getNextIndex(current: number, total: number, direction: 'next' | 'prev', wrap = true): number {
    if (direction === 'next') {
      const next = current + 1;
      if (next >= total) {
        return wrap ? 0 : current;
      }
      return next;
    } else {
      const prev = current - 1;
      if (prev < 0) {
        return wrap ? total - 1 : current;
      }
      return prev;
    }
  },
};

/**
 * Touch target size validator
 */
export function validateTouchTarget(element: HTMLElement): boolean {
  const rect = element.getBoundingClientRect();
  const minSize = 44; // WCAG 2.1 AA requirement
  
  return rect.width >= minSize && rect.height >= minSize;
}

/**
 * Add visual focus indicator styles
 */
export const focusStyles = {
  default: {
    outline: '2px solid #1890ff',
    outlineOffset: '2px',
  },
  highContrast: {
    outline: '3px solid #000000',
    outlineOffset: '3px',
    boxShadow: '0 0 0 3px #FFFFFF',
  },
};

/**
 * ARIA attribute helpers
 */
export const AriaUtils = {
  /**
   * Generate describedby IDs
   */
  describedBy(...ids: (string | undefined)[]): string | undefined {
    const validIds = ids.filter(Boolean);
    return validIds.length > 0 ? validIds.join(' ') : undefined;
  },
  
  /**
   * Generate labelledby IDs
   */
  labelledBy(...ids: (string | undefined)[]): string | undefined {
    const validIds = ids.filter(Boolean);
    return validIds.length > 0 ? validIds.join(' ') : undefined;
  },
  
  /**
   * Set live region attributes
   */
  liveRegion(mode: 'polite' | 'assertive' | 'off' = 'polite') {
    return {
      'aria-live': mode,
      'aria-atomic': 'true',
      'aria-relevant': 'additions text',
    };
  },
};

/**
 * Color blind safe color palettes
 */
export const colorBlindSafePalette = {
  // Using colors that are distinguishable for all types of color blindness
  primary: '#0173B2',    // Blue
  success: '#029E73',    // Teal
  warning: '#DE8F05',    // Orange
  danger: '#CC3311',     // Red-orange
  info: '#56B4E9',       // Light blue
  secondary: '#949494',  // Gray
};

/**
 * Generate accessible color scheme
 */
export function generateAccessibleColors(baseColor: string) {
  // This would typically use a color theory library
  // For now, return a simple scheme
  return {
    text: meetsWCAG('#000000', baseColor, 'AA') ? '#000000' : '#FFFFFF',
    textLight: meetsWCAG('#666666', baseColor, 'AA') ? '#666666' : '#F0F0F0',
    border: meetsWCAG('#CCCCCC', baseColor, 'AA', true) ? '#CCCCCC' : '#333333',
  };
}

export default {
  getContrastRatio,
  meetsWCAG,
  suggestAccessibleColor,
  formatTimeForScreenReader,
  generateId,
  FocusManager,
  ScreenReaderUtils,
  KeyboardUtils,
  validateTouchTarget,
  focusStyles,
  AriaUtils,
  colorBlindSafePalette,
  generateAccessibleColors,
};