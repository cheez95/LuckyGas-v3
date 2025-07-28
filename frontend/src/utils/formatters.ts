import dayjs from 'dayjs';
import 'dayjs/locale/zh-tw';

/**
 * Taiwan-specific formatting utilities
 */

/**
 * Format date to Taiwan format (民國年 or YYYY/MM/DD)
 * @param date - Date to format
 * @param useROC - Whether to use ROC calendar (民國年)
 * @returns Formatted date string
 */
export function formatTaiwanDate(date: Date | string | null, useROC = false): string {
  if (!date) return '';
  
  const d = dayjs(date).locale('zh-tw');
  
  if (useROC) {
    // Convert to Republic of China calendar (民國年)
    const rocYear = d.year() - 1911;
    return `民國${rocYear}年${d.format('M月D日')}`;
  }
  
  return d.format('YYYY/MM/DD');
}

/**
 * Format date with time for Taiwan
 * @param date - Date to format
 * @param showSeconds - Whether to show seconds
 * @returns Formatted date time string
 */
export function formatTaiwanDateTime(date: Date | string | null, showSeconds = false): string {
  if (!date) return '';
  
  const d = dayjs(date).locale('zh-tw');
  const format = showSeconds ? 'YYYY/MM/DD HH:mm:ss' : 'YYYY/MM/DD HH:mm';
  return d.format(format);
}

/**
 * Format currency for Taiwan (NT$)
 * @param amount - Amount to format
 * @param showCents - Whether to show cents
 * @returns Formatted currency string
 */
export function formatTaiwanCurrency(amount: number | null | undefined, showCents = false): string {
  if (amount === null || amount === undefined) return 'NT$0';
  
  const formatter = new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    minimumFractionDigits: showCents ? 2 : 0,
    maximumFractionDigits: showCents ? 2 : 0,
  });
  
  return formatter.format(amount);
}

/**
 * Format phone number for Taiwan
 * @param phone - Phone number to format
 * @returns Formatted phone number
 */
export function formatTaiwanPhone(phone: string | null | undefined): string {
  if (!phone) return '';
  
  // Remove all non-numeric characters
  const cleaned = phone.replace(/\D/g, '');
  
  // Handle mobile numbers (09XX-XXX-XXX)
  if (cleaned.startsWith('09') && cleaned.length === 10) {
    return `${cleaned.slice(0, 4)}-${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
  }
  
  // Handle landline numbers with area code
  if (cleaned.length >= 9) {
    // Common area codes in Taiwan
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
  }
  
  // Handle international format (+886)
  if (cleaned.startsWith('886')) {
    const withoutCountry = cleaned.slice(3);
    // Remove leading 0 if present
    const localNumber = withoutCountry.startsWith('0') ? withoutCountry.slice(1) : withoutCountry;
    
    if (localNumber.startsWith('9') && localNumber.length === 9) {
      return `+886-${localNumber.slice(0, 3)}-${localNumber.slice(3, 6)}-${localNumber.slice(6)}`;
    }
  }
  
  // Return original if no formatting rules match
  return phone;
}

/**
 * Format address for Taiwan (with postal code)
 * @param postalCode - Postal code
 * @param city - City/County
 * @param district - District/Township
 * @param address - Street address
 * @returns Formatted address
 */
export function formatTaiwanAddress(
  postalCode?: string | null,
  city?: string | null,
  district?: string | null,
  address?: string | null
): string {
  const parts = [];
  
  if (postalCode) {
    parts.push(postalCode);
  }
  
  if (city) {
    parts.push(city);
  }
  
  if (district) {
    parts.push(district);
  }
  
  if (address) {
    parts.push(address);
  }
  
  return parts.join(' ');
}

/**
 * Get relative time in Chinese
 * @param date - Date to compare
 * @returns Relative time string
 */
export function getRelativeTime(date: Date | string | null): string {
  if (!date) return '';
  
  const d = dayjs(date);
  const now = dayjs();
  const diffInMinutes = now.diff(d, 'minute');
  const diffInHours = now.diff(d, 'hour');
  const diffInDays = now.diff(d, 'day');
  
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
}

/**
 * Format large numbers with Chinese units
 * @param num - Number to format
 * @returns Formatted number with units
 */
export function formatChineseNumber(num: number): string {
  if (num >= 100000000) {
    return `${(num / 100000000).toFixed(1)}億`;
  } else if (num >= 10000) {
    return `${(num / 10000).toFixed(1)}萬`;
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}千`;
  }
  return num.toString();
}