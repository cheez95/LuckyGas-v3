import { formatInTimeZone } from 'date-fns-tz';
import { zhTW } from 'date-fns/locale';

/**
 * Taiwan-specific localization service
 * Handles:
 * - Date formatting (民國年 and Western)
 * - Phone number formatting
 * - Currency formatting (NT$)
 * - Address formatting
 * - Number formatting
 */
export class LocalizationService {
  private static readonly TW_TIMEZONE = 'Asia/Taipei';
  private static readonly MINGUO_OFFSET = 1911;

  /**
   * Format date to Taiwan format (民國年)
   */
  static formatMinguoDate(date: Date | string | number): string {
    const d = new Date(date);
    const year = d.getFullYear();
    const minguoYear = year - this.MINGUO_OFFSET;
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    
    return `民國${minguoYear}年${month}月${day}日`;
  }

  /**
   * Format date to Taiwan Western format (YYYY/MM/DD)
   */
  static formatWesternDate(date: Date | string | number): string {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    
    return `${year}/${month}/${day}`;
  }

  /**
   * Format date with time in Taiwan timezone
   */
  static formatDateTime(date: Date | string | number): string {
    return formatInTimeZone(
      new Date(date),
      this.TW_TIMEZONE,
      'yyyy/MM/dd HH:mm',
      { locale: zhTW }
    );
  }

  /**
   * Format currency to NT$
   */
  static formatCurrency(amount: number): string {
    return new Intl.NumberFormat('zh-TW', {
      style: 'currency',
      currency: 'TWD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  }

  /**
   * Format Taiwan phone number
   */
  static formatPhoneNumber(phone: string): string {
    // Remove all non-numeric characters
    const cleaned = phone.replace(/\D/g, '');
    
    // Mobile number (09XX-XXX-XXX)
    if (cleaned.startsWith('09') && cleaned.length === 10) {
      return `${cleaned.slice(0, 4)}-${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
    }
    
    // Landline with area code (0X-XXXX-XXXX or 0XX-XXX-XXXX)
    if (cleaned.startsWith('0') && cleaned.length >= 9) {
      const areaCode = cleaned.slice(0, 2);
      const isShortAreaCode = ['02', '03', '04', '05', '06', '07', '08'].includes(areaCode);
      
      if (isShortAreaCode) {
        // 02-XXXX-XXXX format
        return `${areaCode}-${cleaned.slice(2, 6)}-${cleaned.slice(6)}`;
      } else if (cleaned.length === 10) {
        // 0XX-XXX-XXXX format
        const longAreaCode = cleaned.slice(0, 3);
        return `${longAreaCode}-${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
      }
    }
    
    // Return original if format not recognized
    return phone;
  }

  /**
   * Validate Taiwan phone number
   */
  static isValidPhoneNumber(phone: string): boolean {
    const cleaned = phone.replace(/\D/g, '');
    
    // Mobile: 09XXXXXXXX
    if (/^09\d{8}$/.test(cleaned)) {
      return true;
    }
    
    // Landline: 0X-XXXXXXXX or 0XX-XXXXXXX
    if (/^0[2-8]\d{7,8}$/.test(cleaned)) {
      return true;
    }
    
    return false;
  }

  /**
   * Format Taiwan address
   */
  static formatAddress(address: {
    postalCode?: string;
    city?: string;
    district?: string;
    street?: string;
    number?: string;
    floor?: string;
    room?: string;
  }): string {
    const parts: string[] = [];
    
    if (address.postalCode) {
      parts.push(address.postalCode);
    }
    
    if (address.city) {
      parts.push(address.city);
    }
    
    if (address.district) {
      parts.push(address.district);
    }
    
    if (address.street) {
      parts.push(address.street);
    }
    
    if (address.number) {
      parts.push(address.number + '號');
    }
    
    if (address.floor) {
      parts.push(address.floor + '樓');
    }
    
    if (address.room) {
      parts.push(address.room + '室');
    }
    
    return parts.join('');
  }

  /**
   * Parse Taiwan address string
   */
  static parseAddress(addressString: string): {
    postalCode?: string;
    city?: string;
    district?: string;
    street?: string;
    fullAddress: string;
  } {
    // Extract postal code (3 or 5 digits at the beginning)
    const postalCodeMatch = addressString.match(/^(\d{3,5})/);
    const postalCode = postalCodeMatch ? postalCodeMatch[1] : undefined;
    
    // Remove postal code from address
    const addressWithoutPostal = postalCode 
      ? addressString.slice(postalCode.length).trim()
      : addressString;
    
    // Common Taiwan cities
    const cities = [
      '台北市', '臺北市', '新北市', '桃園市', '台中市', '臺中市',
      '台南市', '臺南市', '高雄市', '基隆市', '新竹市', '嘉義市',
      '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣', '嘉義縣',
      '屏東縣', '宜蘭縣', '花蓮縣', '台東縣', '臺東縣', '澎湖縣',
      '金門縣', '連江縣'
    ];
    
    let city: string | undefined;
    let remainingAddress = addressWithoutPostal;
    
    // Find city in address
    for (const c of cities) {
      if (addressWithoutPostal.includes(c)) {
        city = c;
        remainingAddress = addressWithoutPostal.replace(c, '').trim();
        break;
      }
    }
    
    // Extract district (區/鄉/鎮/市)
    const districtMatch = remainingAddress.match(/^([^區鄉鎮市]+[區鄉鎮市])/);
    const district = districtMatch ? districtMatch[1] : undefined;
    
    if (district) {
      remainingAddress = remainingAddress.replace(district, '').trim();
    }
    
    return {
      postalCode,
      city,
      district,
      street: remainingAddress,
      fullAddress: addressString
    };
  }

  /**
   * Format number with thousand separators
   */
  static formatNumber(num: number, decimals: number = 0): string {
    return new Intl.NumberFormat('zh-TW', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(num);
  }

  /**
   * Format percentage
   */
  static formatPercentage(num: number, decimals: number = 1): string {
    return new Intl.NumberFormat('zh-TW', {
      style: 'percent',
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(num / 100);
  }

  /**
   * Get Taiwan holidays
   */
  static getTaiwanHolidays(year: number): { date: Date; name: string }[] {
    // This is a simplified version - in production, you'd want to use a proper holiday API
    // or library that handles lunar calendar calculations
    return [
      { date: new Date(year, 0, 1), name: '元旦' },
      { date: new Date(year, 1, 28), name: '和平紀念日' },
      { date: new Date(year, 3, 4), name: '兒童節' },
      { date: new Date(year, 3, 5), name: '清明節' },
      { date: new Date(year, 4, 1), name: '勞動節' },
      { date: new Date(year, 9, 10), name: '國慶日' },
      // Lunar calendar holidays would need special calculation
      // { date: calculateLunarDate(year, '春節'), name: '春節' },
      // { date: calculateLunarDate(year, '端午節'), name: '端午節' },
      // { date: calculateLunarDate(year, '中秋節'), name: '中秋節' },
    ];
  }

  /**
   * Format weight (kg)
   */
  static formatWeight(kg: number): string {
    return `${this.formatNumber(kg, 1)} 公斤`;
  }

  /**
   * Format distance (km)
   */
  static formatDistance(km: number): string {
    if (km < 1) {
      return `${Math.round(km * 1000)} 公尺`;
    }
    return `${this.formatNumber(km, 1)} 公里`;
  }

  /**
   * Format duration
   */
  static formatDuration(minutes: number): string {
    if (minutes < 60) {
      return `${Math.round(minutes)} 分鐘`;
    }
    
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    
    if (mins === 0) {
      return `${hours} 小時`;
    }
    
    return `${hours} 小時 ${mins} 分鐘`;
  }

  /**
   * Get greeting based on time of day
   */
  static getTimeGreeting(): string {
    const hour = new Date().getHours();
    
    if (hour < 6) {
      return '凌晨好';
    } else if (hour < 12) {
      return '早安';
    } else if (hour < 18) {
      return '午安';
    } else {
      return '晚安';
    }
  }

  /**
   * Format invoice number (Taiwan format)
   */
  static formatInvoiceNumber(prefix: string, number: number): string {
    // Taiwan invoice format: XX-12345678
    const paddedNumber = String(number).padStart(8, '0');
    return `${prefix}-${paddedNumber}`;
  }

  /**
   * Validate Taiwan ID number (company tax ID)
   */
  static isValidTaxId(taxId: string): boolean {
    // Taiwan company tax ID is 8 digits
    return /^\d{8}$/.test(taxId);
  }

  /**
   * Format order number with date prefix
   */
  static formatOrderNumber(date: Date, sequence: number): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const seq = String(sequence).padStart(4, '0');
    
    return `${year}${month}${day}-${seq}`;
  }
}

// Export convenience functions
export const {
  formatMinguoDate,
  formatWesternDate,
  formatDateTime,
  formatCurrency,
  formatPhoneNumber,
  isValidPhoneNumber,
  formatAddress,
  parseAddress,
  formatNumber,
  formatPercentage,
  getTaiwanHolidays,
  formatWeight,
  formatDistance,
  formatDuration,
  getTimeGreeting,
  formatInvoiceNumber,
  isValidTaxId,
  formatOrderNumber
} = LocalizationService;