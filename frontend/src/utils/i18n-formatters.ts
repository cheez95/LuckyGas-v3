import i18n from '../i18n';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-tw';
import 'dayjs/locale/en';

/**
 * Locale-aware formatting utilities
 */

/**
 * Get current locale from i18n
 */
function getCurrentLocale(): string {
  return i18n.language || 'zh-TW';
}

/**
 * Format date based on current locale
 * @param date - Date to format
 * @param format - Optional format string
 * @returns Formatted date string
 */
export function formatDate(date: Date | string | null, format?: string): string {
  if (!date) return '';
  
  const locale = getCurrentLocale();
  const d = dayjs(date).locale(locale === 'zh-TW' ? 'zh-tw' : 'en');
  
  if (format) {
    return d.format(format);
  }
  
  // Default formats for different locales
  if (locale === 'zh-TW') {
    return d.format('YYYY/MM/DD');
  }
  return d.format('MM/DD/YYYY');
}

/**
 * Format date with time based on current locale
 * @param date - Date to format
 * @param showSeconds - Whether to show seconds
 * @returns Formatted date time string
 */
export function formatDateTime(date: Date | string | null, showSeconds = false): string {
  if (!date) return '';
  
  const locale = getCurrentLocale();
  const d = dayjs(date).locale(locale === 'zh-TW' ? 'zh-tw' : 'en');
  
  if (locale === 'zh-TW') {
    return showSeconds ? d.format('YYYY/MM/DD HH:mm:ss') : d.format('YYYY/MM/DD HH:mm');
  }
  return showSeconds ? d.format('MM/DD/YYYY h:mm:ss A') : d.format('MM/DD/YYYY h:mm A');
}

/**
 * Format currency based on current locale
 * @param amount - Amount to format
 * @param showCents - Whether to show cents
 * @returns Formatted currency string
 */
export function formatCurrency(amount: number | null | undefined, showCents = false): string {
  if (amount === null || amount === undefined) return formatCurrency(0, showCents);
  
  const locale = getCurrentLocale();
  const options: Intl.NumberFormatOptions = {
    style: 'currency',
    currency: locale === 'zh-TW' ? 'TWD' : 'USD',
    minimumFractionDigits: showCents ? 2 : 0,
    maximumFractionDigits: showCents ? 2 : 0,
  };
  
  const formatter = new Intl.NumberFormat(locale === 'zh-TW' ? 'zh-TW' : 'en-US', options);
  return formatter.format(amount);
}

/**
 * Format phone number based on current locale
 * @param phone - Phone number to format
 * @returns Formatted phone number
 */
export function formatPhone(phone: string | null | undefined): string {
  if (!phone) return '';
  
  const locale = getCurrentLocale();
  const cleaned = phone.replace(/\D/g, '');
  
  if (locale === 'zh-TW') {
    // Taiwan format
    if (cleaned.startsWith('09') && cleaned.length === 10) {
      return `${cleaned.slice(0, 4)}-${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
    }
    // Handle area codes...
    const areaCodes = ['02', '03', '04', '05', '06', '07', '08', '037', '049', '082', '0826', '0836', '089'];
    for (const areaCode of areaCodes) {
      if (cleaned.startsWith(areaCode)) {
        const remaining = cleaned.slice(areaCode.length);
        if (remaining.length === 8) {
          return `${areaCode}-${remaining.slice(0, 4)}-${remaining.slice(4)}`;
        }
        if (remaining.length === 7) {
          return `${areaCode}-${remaining.slice(0, 3)}-${remaining.slice(3)}`;
        }
      }
    }
  } else {
    // US format
    if (cleaned.length === 10) {
      return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
    }
  }
  
  return phone;
}

/**
 * Get relative time based on current locale
 * @param date - Date to compare
 * @returns Relative time string
 */
export function getRelativeTime(date: Date | string | null): string {
  if (!date) return '';
  
  const locale = getCurrentLocale();
  const d = dayjs(date);
  const now = dayjs();
  const diffInMinutes = now.diff(d, 'minute');
  const diffInHours = now.diff(d, 'hour');
  const diffInDays = now.diff(d, 'day');
  
  if (locale === 'zh-TW') {
    if (diffInMinutes < 1) {
      return '剛剛';
    } else if (diffInMinutes < 60) {
      return `${diffInMinutes}分鐘前`;
    } else if (diffInHours < 24) {
      return `${diffInHours}小時前`;
    } else if (diffInDays < 7) {
      return `${diffInDays}天前`;
    } else if (diffInDays < 30) {
      const weeks = Math.floor(diffInDays / 7);
      return `${weeks}週前`;
    } else if (diffInDays < 365) {
      const months = Math.floor(diffInDays / 30);
      return `${months}個月前`;
    } else {
      const years = Math.floor(diffInDays / 365);
      return `${years}年前`;
    }
  } else {
    if (diffInMinutes < 1) {
      return 'just now';
    } else if (diffInMinutes < 60) {
      return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    } else if (diffInDays < 7) {
      return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    } else if (diffInDays < 30) {
      const weeks = Math.floor(diffInDays / 7);
      return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
    } else if (diffInDays < 365) {
      const months = Math.floor(diffInDays / 30);
      return `${months} month${months > 1 ? 's' : ''} ago`;
    } else {
      const years = Math.floor(diffInDays / 365);
      return `${years} year${years > 1 ? 's' : ''} ago`;
    }
  }
}

/**
 * Format number with locale-specific separators
 * @param num - Number to format
 * @param decimals - Number of decimal places
 * @returns Formatted number
 */
export function formatNumber(num: number | null | undefined, decimals = 0): string {
  if (num === null || num === undefined) return '0';
  
  const locale = getCurrentLocale();
  const formatter = new Intl.NumberFormat(locale === 'zh-TW' ? 'zh-TW' : 'en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  
  return formatter.format(num);
}

/**
 * Format percentage
 * @param value - Value to format (0-100)
 * @param decimals - Number of decimal places
 * @returns Formatted percentage
 */
export function formatPercentage(value: number | null | undefined, decimals = 0): string {
  if (value === null || value === undefined) return '0%';
  
  const locale = getCurrentLocale();
  const formatter = new Intl.NumberFormat(locale === 'zh-TW' ? 'zh-TW' : 'en-US', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  
  // Intl.NumberFormat expects decimal values for percentages (0.5 = 50%)
  return formatter.format(value / 100);
}