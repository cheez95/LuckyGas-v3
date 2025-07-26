# Taiwan-Specific Validation Rules

## 🇹🇼 Localization Requirements

This document details all Taiwan-specific validation rules, formats, and business logic that must be implemented in the Lucky Gas customer management system.

## 📱 Phone Number Validation

### Mobile Phone Numbers
```javascript
// Taiwan mobile number validation
const validateTaiwanMobile = (phone) => {
  // Remove all non-digits
  const cleaned = phone.replace(/\D/g, '');
  
  // Check if starts with 09 and has 10 digits total
  const mobileRegex = /^09\d{8}$/;
  
  if (!mobileRegex.test(cleaned)) {
    return {
      valid: false,
      error: "手機號碼格式錯誤，應為 09XX-XXX-XXX"
    };
  }
  
  // Format for display
  const formatted = `${cleaned.substr(0, 4)}-${cleaned.substr(4, 3)}-${cleaned.substr(7, 3)}`;
  
  return {
    valid: true,
    formatted: formatted,
    raw: cleaned
  };
};

// Valid mobile prefixes in Taiwan
const VALID_MOBILE_PREFIXES = [
  '0900', '0901', '0902', '0903', '0904', '0905', '0906', '0907', '0908', '0909',
  '0910', '0911', '0912', '0913', '0914', '0915', '0916', '0917', '0918', '0919',
  '0920', '0921', '0922', '0923', '0924', '0925', '0926', '0927', '0928', '0929',
  '0930', '0931', '0932', '0933', '0934', '0935', '0936', '0937', '0938', '0939',
  '0952', '0953', '0954', '0955', '0956', '0958',
  '0960', '0961', '0963', '0965', '0966', '0968',
  '0970', '0971', '0972', '0973', '0974', '0975', '0976', '0977', '0978', '0979',
  '0980', '0981', '0982', '0983', '0984', '0985', '0986', '0987', '0988', '0989'
];
```

### Landline Phone Numbers
```javascript
// Taiwan landline validation
const validateTaiwanLandline = (phone) => {
  const cleaned = phone.replace(/\D/g, '');
  
  // Area codes and their digit requirements
  const areaCodeRules = {
    '02': 8,   // Taipei, Keelung
    '03': 8,   // Taoyuan, Hsinchu, Yilan, Hualien
    '037': 7,  // Miaoli
    '04': 8,   // Taichung, Changhua
    '049': 7,  // Nantou
    '05': 8,   // Chiayi, Yunlin
    '06': 8,   // Tainan
    '07': 8,   // Kaohsiung
    '08': 8,   // Pingtung, Taitung
    '082': 6,  // Kinmen
    '0826': 5, // Wuqiu
    '0836': 5, // Matsu
    '089': 7   // Taitung
  };
  
  // Find matching area code
  let areaCode = '';
  let localNumber = '';
  let totalDigits = 0;
  
  for (const code of Object.keys(areaCodeRules).sort((a, b) => b.length - a.length)) {
    if (cleaned.startsWith(code)) {
      areaCode = code;
      localNumber = cleaned.substr(code.length);
      totalDigits = areaCodeRules[code];
      break;
    }
  }
  
  if (!areaCode || localNumber.length !== totalDigits) {
    return {
      valid: false,
      error: "市話號碼格式錯誤"
    };
  }
  
  // Format for display
  const formatted = totalDigits === 8 
    ? `${areaCode}-${localNumber.substr(0, 4)}-${localNumber.substr(4, 4)}`
    : `${areaCode}-${localNumber}`;
  
  return {
    valid: true,
    formatted: formatted,
    raw: cleaned,
    areaCode: areaCode,
    region: getRegionName(areaCode)
  };
};

// Get region name from area code
const getRegionName = (areaCode) => {
  const regions = {
    '02': '台北/基隆',
    '03': '桃園/新竹/宜蘭/花蓮',
    '037': '苗栗',
    '04': '台中/彰化',
    '049': '南投',
    '05': '嘉義/雲林',
    '06': '台南',
    '07': '高雄',
    '08': '屏東/台東',
    '082': '金門',
    '0826': '烏坵',
    '0836': '馬祖',
    '089': '台東'
  };
  return regions[areaCode] || '未知地區';
};
```

## 🏢 Tax ID Validation (統一編號)

### Business Tax ID Validation
```javascript
// Taiwan Business Tax ID (統一編號) validation
const validateTaxId = (taxId) => {
  // Remove any formatting
  const cleaned = taxId.replace(/\D/g, '');
  
  // Must be exactly 8 digits
  if (!/^\d{8}$/.test(cleaned)) {
    return {
      valid: false,
      error: "統一編號必須為8位數字"
    };
  }
  
  // Validation algorithm
  const weights = [1, 2, 1, 2, 1, 2, 4, 1];
  let sum = 0;
  
  for (let i = 0; i < 8; i++) {
    const digit = parseInt(cleaned[i]);
    const product = digit * weights[i];
    
    // If product is two digits, add them separately
    sum += Math.floor(product / 10) + (product % 10);
  }
  
  // Special case: if 7th digit is 7 and sum % 10 = 0, add 1
  if (cleaned[6] === '7' && sum % 10 === 0) {
    sum = 1;
  }
  
  const isValid = sum % 10 === 0;
  
  return {
    valid: isValid,
    formatted: cleaned,
    error: isValid ? null : "統一編號檢查碼錯誤"
  };
};

// Common test Tax IDs (for development only)
const TEST_TAX_IDS = [
  '53212539', // Google Taiwan
  '23525229', // Microsoft Taiwan
  '11111111', // Test pattern (invalid)
  '12345678'  // Test pattern (invalid)
];
```

## 🆔 National ID Validation (身分證字號)

### ROC National ID Validation
```javascript
// Taiwan National ID validation
const validateNationalId = (id) => {
  const cleaned = id.toUpperCase().trim();
  
  // Format: 1 letter + 1 digit (1/2 for gender) + 8 digits
  if (!/^[A-Z][12]\d{8}$/.test(cleaned)) {
    return {
      valid: false,
      error: "身分證字號格式錯誤"
    };
  }
  
  // Letter to number mapping
  const letterMap = {
    'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17,
    'I': 34, 'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'O': 35, 'P': 23,
    'Q': 24, 'R': 25, 'S': 26, 'T': 27, 'U': 28, 'V': 29, 'W': 32, 'X': 30,
    'Y': 31, 'Z': 33
  };
  
  // Convert letter to number
  const letterNum = letterMap[cleaned[0]];
  const n1 = Math.floor(letterNum / 10);
  const n2 = letterNum % 10;
  
  // Calculate checksum
  let sum = n1 + n2 * 9;
  
  // Add weighted digits
  for (let i = 1; i < 9; i++) {
    sum += parseInt(cleaned[i]) * (9 - i);
  }
  
  // Add check digit
  sum += parseInt(cleaned[9]);
  
  const isValid = sum % 10 === 0;
  
  // Extract information
  const gender = cleaned[1] === '1' ? '男' : '女';
  const birthPlace = getBirthPlace(cleaned[0]);
  
  return {
    valid: isValid,
    formatted: cleaned,
    gender: gender,
    birthPlace: birthPlace,
    error: isValid ? null : "身分證字號檢查碼錯誤"
  };
};

// Get birth place from ID letter
const getBirthPlace = (letter) => {
  const places = {
    'A': '台北市', 'B': '台中市', 'C': '基隆市', 'D': '台南市', 'E': '高雄市',
    'F': '新北市', 'G': '宜蘭縣', 'H': '桃園市', 'I': '嘉義市', 'J': '新竹縣',
    'K': '苗栗縣', 'L': '台中縣', 'M': '南投縣', 'N': '彰化縣', 'O': '新竹市',
    'P': '雲林縣', 'Q': '嘉義縣', 'R': '台南縣', 'S': '高雄縣', 'T': '屏東縣',
    'U': '花蓮縣', 'V': '台東縣', 'W': '金門縣', 'X': '澎湖縣', 'Y': '陽明山',
    'Z': '連江縣'
  };
  return places[letter] || '未知';
};
```

## 📮 Address Validation

### Postal Code Validation
```javascript
// Taiwan postal code data structure
const POSTAL_CODES = {
  '台北市': {
    '中正區': ['100'],
    '大同區': ['103'],
    '中山區': ['104'],
    '松山區': ['105'],
    '大安區': ['106'],
    '萬華區': ['108'],
    '信義區': ['110'],
    '士林區': ['111'],
    '北投區': ['112'],
    '內湖區': ['114'],
    '南港區': ['115'],
    '文山區': ['116']
  },
  '新北市': {
    '板橋區': ['220'],
    '三重區': ['241'],
    '中和區': ['235'],
    '永和區': ['234'],
    '新莊區': ['242'],
    '新店區': ['231'],
    '樹林區': ['238'],
    '鶯歌區': ['239'],
    '三峽區': ['237'],
    '淡水區': ['251'],
    '汐止區': ['221'],
    '瑞芳區': ['224'],
    '土城區': ['236'],
    '蘆洲區': ['247'],
    '五股區': ['248'],
    '泰山區': ['243'],
    '林口區': ['244'],
    '深坑區': ['222'],
    '石碇區': ['223'],
    '坪林區': ['232'],
    '三芝區': ['252'],
    '石門區': ['253'],
    '八里區': ['249'],
    '平溪區': ['226'],
    '雙溪區': ['227'],
    '貢寮區': ['228'],
    '金山區': ['208'],
    '萬里區': ['207'],
    '烏來區': ['233']
  }
  // ... more cities and districts
};

// Validate postal code with city/district
const validatePostalCode = (postalCode, city, district) => {
  const cleaned = postalCode.replace(/\D/g, '');
  
  // Must be 3 or 5 digits (3 is old format, 5 is new with +2)
  if (!/^\d{3}$/.test(cleaned) && !/^\d{5}$/.test(cleaned)) {
    return {
      valid: false,
      error: "郵遞區號必須為3或5位數字"
    };
  }
  
  // Extract base code (first 3 digits)
  const baseCode = cleaned.substr(0, 3);
  
  // Validate against city/district if provided
  if (city && district) {
    const validCodes = POSTAL_CODES[city]?.[district] || [];
    if (!validCodes.includes(baseCode)) {
      return {
        valid: false,
        error: `${city}${district}的郵遞區號應為 ${validCodes.join(' 或 ')}`
      };
    }
  }
  
  return {
    valid: true,
    formatted: cleaned,
    baseCode: baseCode,
    isNewFormat: cleaned.length === 5
  };
};
```

### Address Format Validation
```javascript
// Taiwan address format validation
const validateAddress = (address) => {
  // Common patterns in Taiwan addresses
  const patterns = {
    road: /[路街巷弄]/,
    number: /\d+號/,
    floor: /\d+[樓F]/,
    room: /[室房]/,
    building: /[大樓棟]/
  };
  
  // Check for minimum required components
  const hasRoad = patterns.road.test(address);
  const hasNumber = patterns.number.test(address);
  
  if (!hasRoad || !hasNumber) {
    return {
      valid: false,
      error: "地址必須包含路名和門牌號碼"
    };
  }
  
  // Extract components
  const components = {
    hasFloor: patterns.floor.test(address),
    hasRoom: patterns.room.test(address),
    hasBuilding: patterns.building.test(address)
  };
  
  // Normalize address format
  let normalized = address;
  
  // Ensure spacing around numbers
  normalized = normalized.replace(/(\d+)號/g, '$1號');
  normalized = normalized.replace(/(\d+)樓/g, '$1樓');
  
  return {
    valid: true,
    normalized: normalized,
    components: components
  };
};
```

## 💰 Currency and Number Formatting

### Taiwan Dollar Formatting
```javascript
// Format numbers as TWD currency
const formatTWD = (amount) => {
  // Round to whole number (no cents in TWD)
  const rounded = Math.round(amount);
  
  // Add thousand separators
  const formatted = rounded.toLocaleString('zh-TW');
  
  return {
    display: `NT$ ${formatted}`,
    displayShort: `$${formatted}`,
    raw: rounded,
    chinese: numberToChinese(rounded) + '元'
  };
};

// Convert number to Chinese characters
const numberToChinese = (num) => {
  const digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
  const units = ['', '十', '百', '千', '萬', '十萬', '百萬', '千萬', '億'];
  
  // Simplified conversion for display
  if (num === 0) return '零';
  
  // Convert to string and process
  const str = num.toString();
  let result = '';
  
  // Basic implementation - can be enhanced
  for (let i = 0; i < str.length; i++) {
    const digit = parseInt(str[i]);
    result += digits[digit];
    
    const position = str.length - i - 1;
    if (position > 0 && digit !== 0) {
      if (position === 4) result += '萬';
      else if (position === 8) result += '億';
      else if (position % 4 === 0) result += '萬';
      else result += units[position % 4];
    }
  }
  
  // Clean up
  result = result.replace(/零+/g, '零');
  result = result.replace(/零+$/, '');
  
  return result;
};
```

## 📅 Date and Time Formatting

### Taiwan Calendar (民國年) Support
```javascript
// Convert between Western and ROC calendar
const dateConversion = {
  // Convert AD to ROC year
  toROC: (date) => {
    const year = date.getFullYear();
    const rocYear = year - 1911;
    
    if (rocYear < 1) {
      return {
        valid: false,
        error: "日期必須在民國元年（1912年）之後"
      };
    }
    
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    
    return {
      valid: true,
      rocYear: rocYear,
      formatted: `民國${rocYear}年${month}月${day}日`,
      short: `${rocYear}/${month}/${day}`,
      iso: date.toISOString().split('T')[0]
    };
  },
  
  // Convert ROC to AD year
  fromROC: (rocYear, month, day) => {
    const adYear = rocYear + 1911;
    const date = new Date(adYear, month - 1, day);
    
    return {
      valid: !isNaN(date),
      date: date,
      formatted: date.toLocaleDateString('zh-TW'),
      iso: date.toISOString().split('T')[0]
    };
  }
};

// Format date for display
const formatDate = (date, format = 'full') => {
  const roc = dateConversion.toROC(date);
  
  const formats = {
    'full': roc.formatted,
    'short': roc.short,
    'iso': roc.iso,
    'chinese': `${roc.rocYear}年${date.getMonth() + 1}月${date.getDate()}日`,
    'display': `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}`
  };
  
  return formats[format] || formats['full'];
};
```

## 🏪 Business-Specific Validations

### Gas Cylinder Types
```javascript
const CYLINDER_TYPES = {
  '20KG': {
    name: '20公斤桶裝',
    deposit: 1500,
    maxQuantity: 10,
    commonUse: ['家庭', '小吃店']
  },
  '50KG': {
    name: '50公斤桶裝',
    deposit: 3000,
    maxQuantity: 5,
    commonUse: ['餐廳', '工廠']
  },
  '16KG': {
    name: '16公斤桶裝',
    deposit: 1200,
    maxQuantity: 10,
    commonUse: ['家庭', '露營']
  }
};
```

### Delivery Time Slots
```javascript
const DELIVERY_SLOTS = {
  'MORNING': {
    code: '01',
    name: '上午',
    timeRange: '08:00-12:00',
    capacity: 50
  },
  'AFTERNOON': {
    code: '02',
    name: '下午',
    timeRange: '13:00-17:00',
    capacity: 50
  },
  'EVENING': {
    code: '03',
    name: '晚間',
    timeRange: '17:00-20:00',
    capacity: 30,
    surcharge: 50
  },
  'ANYTIME': {
    code: '04',
    name: '不限',
    timeRange: '08:00-17:00',
    capacity: 999
  }
};
```

## 🔍 Common Validation Helpers

### Input Sanitization
```javascript
// Remove common input issues
const sanitizeInput = (input, type = 'text') => {
  let cleaned = input.trim();
  
  switch (type) {
    case 'phone':
      // Remove all non-digits except +
      cleaned = cleaned.replace(/[^\d+]/g, '');
      // Convert +886 to 0
      cleaned = cleaned.replace(/^\+886/, '0');
      break;
      
    case 'taxId':
      // Remove all non-digits
      cleaned = cleaned.replace(/\D/g, '');
      break;
      
    case 'chinese':
      // Remove non-Chinese characters except punctuation
      cleaned = cleaned.replace(/[^\u4e00-\u9fa5\s，。！？、]/g, '');
      break;
      
    case 'address':
      // Normalize full-width numbers to half-width
      cleaned = cleaned.replace(/[０-９]/g, (match) => 
        String.fromCharCode(match.charCodeAt(0) - 0xFEE0)
      );
      break;
  }
  
  return cleaned;
};
```

### Error Messages
```javascript
const ERROR_MESSAGES = {
  'zh-TW': {
    required: '此欄位為必填',
    invalidFormat: '格式錯誤',
    taxIdInvalid: '統一編號檢查碼錯誤',
    taxIdDuplicate: '此統一編號已存在',
    phoneInvalid: '電話號碼格式錯誤',
    mobileInvalid: '手機號碼必須為09開頭的10位數字',
    addressIncomplete: '請輸入完整地址',
    postalCodeMismatch: '郵遞區號與地區不符',
    creditLimitExceeded: '超過信用額度上限',
    deliveryAreaNotServiced: '此地區暫不提供服務'
  }
};
```

---

These Taiwan-specific validation rules ensure the Lucky Gas system properly handles local formats, business rules, and cultural requirements. All validations must be implemented in both client-side JavaScript and server-side API validation.