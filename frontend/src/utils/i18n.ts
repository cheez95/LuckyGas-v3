import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import zhTW from '../locales/zh-TW.json';

// Enhanced i18n configuration with pluralization and interpolation
i18next
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      'zh-TW': {
        translation: zhTW
      }
    },
    lng: 'zh-TW',
    fallbackLng: 'zh-TW',
    debug: false,
    
    interpolation: {
      escapeValue: false, // React already escapes values
      format: function(value, format, lng) {
        // Custom formatting functions
        if (format === 'currency') {
          return new Intl.NumberFormat('zh-TW', {
            style: 'currency',
            currency: 'TWD',
            minimumFractionDigits: 0
          }).format(value);
        }
        
        if (format === 'number') {
          return new Intl.NumberFormat('zh-TW').format(value);
        }
        
        if (format === 'percent') {
          return new Intl.NumberFormat('zh-TW', {
            style: 'percent',
            minimumFractionDigits: 1
          }).format(value / 100);
        }
        
        if (format === 'date') {
          return new Intl.DateTimeFormat('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
          }).format(new Date(value));
        }
        
        if (format === 'datetime') {
          return new Intl.DateTimeFormat('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          }).format(new Date(value));
        }
        
        return value;
      }
    },
    
    // Pluralization rules for Chinese
    pluralSeparator: '_',
    contextSeparator: '_',
    
    react: {
      useSuspense: false, // Disable suspense for better error handling
      bindI18n: 'languageChanged loaded',
      bindI18nStore: 'added removed',
      transEmptyNodeValue: '',
      transSupportBasicHtmlNodes: true,
      transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'p']
    }
  });

// Helper function for dynamic translations
export const translateWithCount = (key: string, count: number, options?: any) => {
  return i18next.t(key, { count, ...options });
};

// Helper function for translations with context
export const translateWithContext = (key: string, context: string, options?: any) => {
  return i18next.t(`${key}_${context}`, options);
};

// Helper function for safe translation with fallback
export const safeTranslate = (key: string, fallback: string, options?: any) => {
  const translation = i18next.t(key, options);
  return translation === key ? fallback : translation;
};

// Dynamic content translation functions
export const translateStatus = (status: string, type: 'order' | 'payment' | 'delivery' | 'customer') => {
  const key = `${type}.status.${status}`;
  return i18next.exists(key) ? i18next.t(key) : status;
};

export const translatePaymentMethod = (method: string) => {
  const key = `orders.paymentMethod.${method}`;
  return i18next.exists(key) ? i18next.t(key) : method;
};

export const translatePriority = (priority: string) => {
  const key = `orders.priority.${priority}`;
  return i18next.exists(key) ? i18next.t(key) : priority;
};

export const translateCustomerType = (type: string) => {
  const key = `customers.type.${type}`;
  return i18next.exists(key) ? i18next.t(key) : type;
};

export const translateCylinderSize = (size: string) => {
  const key = `product.sizes.${size}`;
  return i18next.exists(key) ? i18next.t(key) : size;
};

export const translateProductAttribute = (attribute: string) => {
  const key = `product.attributes.${attribute}`;
  return i18next.exists(key) ? i18next.t(key) : attribute;
};

export const translateDeliveryMethod = (method: string) => {
  const key = `product.deliveryMethods.${method}`;
  return i18next.exists(key) ? i18next.t(key) : method;
};

export const translateRole = (role: string) => {
  const roleMap: Record<string, string> = {
    super_admin: '超級管理員',
    manager: '經理',
    office_staff: '辦公室人員',
    driver: '司機',
    customer: '客戶'
  };
  return roleMap[role] || role;
};

export const translateWeekday = (day: number) => {
  const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  return i18next.t(`common.weekdays.${days[day]}`);
};

export const translateMonth = (month: number) => {
  const months = [
    '一月', '二月', '三月', '四月', '五月', '六月',
    '七月', '八月', '九月', '十月', '十一月', '十二月'
  ];
  return months[month];
};

// Validation message helpers
export const getValidationMessage = (type: string, params?: any) => {
  const key = `validation.${type}`;
  return i18next.t(key, params);
};

export const getErrorMessage = (error: string) => {
  const key = `message.error.${error}`;
  return i18next.exists(key) ? i18next.t(key) : i18next.t('message.error.general');
};

export const getSuccessMessage = (action: string) => {
  const key = `message.success.${action}`;
  return i18next.exists(key) ? i18next.t(key) : i18next.t('message.success.saved');
};

// Time-based greetings
export const getGreeting = () => {
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
};

// Export the i18n instance
export default i18next;