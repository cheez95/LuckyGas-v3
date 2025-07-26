/**
 * Test data fixtures for LuckyGas E2E tests
 * Contains user credentials, sample data, and Taiwan-specific formats
 */

export const TestUsers = {
  superAdmin: {
    email: 'admin@luckygas.com.tw',
    password: 'Admin123!@#',
    role: 'super_admin',
    name: '系統管理員'
  },
  manager: {
    email: 'manager@luckygas.com.tw',
    password: 'Manager123!',
    role: 'manager',
    name: '王經理'
  },
  officeStaff: {
    email: 'staff@luckygas.com.tw',
    password: 'Staff123!',
    role: 'office_staff',
    name: '李小姐'
  },
  driver: {
    email: 'driver@luckygas.com.tw',
    password: 'Driver123!',
    role: 'driver',
    name: '陳師傅',
    vehicleId: 'LG-001'
  },
  customer: {
    email: 'customer@example.com',
    password: 'Customer123!',
    role: 'customer',
    name: '張先生',
    phone: '0912-345-678'
  }
};

export const TestCustomers = {
  residential: {
    name: '林太太',
    phone: '0923-456-789',
    address: '台北市大安區忠孝東路四段100號5樓',
    type: 'residential',
    defaultProduct: '20kg 家用桶裝瓦斯',
    contactPerson: '林太太',
    notes: '週末送貨，需事先電話聯絡'
  },
  commercial: {
    name: '幸福小吃店',
    phone: '0923456789',
    address: '台北市信義區基隆路二段50號',
    type: 'commercial',
    defaultProduct: '50kg 營業用桶裝瓦斯',
    contactPerson: '王老闆',
    notes: '每週一、四固定送貨'
  },
  industrial: {
    name: '台灣精密工業股份有限公司',
    phone: '0934567890',
    address: '桃園市龜山區工業路123號',
    type: 'commercial',
    defaultProduct: '50kg 工業用液化石油氣',
    contactPerson: '採購部 陳經理',
    notes: '需開立三聯式發票'
  }
};

export const TestOrders = {
  standard: {
    customer: '林太太',
    product: '20kg 家用桶裝瓦斯',
    quantity: 1,
    deliveryDate: new Date(Date.now() + 86400000).toISOString().split('T')[0], // Tomorrow
    deliveryTime: '14:00-18:00',
    notes: '請按門鈴',
    price: 800
  },
  urgent: {
    customer: '幸福小吃店',
    product: '50kg 營業用桶裝瓦斯',
    quantity: 2,
    deliveryDate: new Date().toISOString().split('T')[0], // Today
    deliveryTime: '09:00-12:00',
    notes: '緊急！瓦斯快用完了',
    price: 2400,
    isUrgent: true
  },
  bulk: {
    customer: '台灣精密工業股份有限公司',
    products: [
      { name: '工業用液化石油氣', quantity: 10, price: 15000 },
      { name: '50kg 營業用桶裝瓦斯', quantity: 5, price: 6000 }
    ],
    deliveryDate: new Date(Date.now() + 172800000).toISOString().split('T')[0], // Day after tomorrow
    deliveryTime: '08:00-12:00',
    notes: '請先聯絡陳經理確認卸貨地點',
    totalPrice: 21000
  }
};

export const TestProducts = {
  residential: [
    { name: '16kg 家用桶裝瓦斯', price: 650, weight: 16 },
    { name: '20kg 家用桶裝瓦斯', price: 800, weight: 20 }
  ],
  commercial: [
    { name: '50kg 營業用桶裝瓦斯', price: 1200, weight: 50 },
    { name: '20kg 營業用桶裝瓦斯', price: 850, weight: 20 }
  ],
  industrial: [
    { name: '工業用液化石油氣', price: 1500, unit: '每100公斤' },
    { name: '叉車用瓦斯', price: 900, weight: 18 }
  ]
};

export const TestAddresses = {
  taipei: [
    '台北市中正區重慶南路一段122號',
    '台北市大安區敦化南路二段100號3樓',
    '台北市信義區松仁路89號',
    '台北市士林區中山北路六段88號',
    '台北市內湖區瑞光路588號'
  ],
  newTaipei: [
    '新北市板橋區文化路一段100號',
    '新北市中和區中山路二段299號',
    '新北市三重區重新路四段200號',
    '新北市新店區北新路三段88號',
    '新北市淡水區中正東路100號'
  ],
  taoyuan: [
    '桃園市桃園區中正路50號',
    '桃園市中壢區中央西路二段100號',
    '桃園市平鎮區環南路199號',
    '桃園市龜山區文化二路88號',
    '桃園市楊梅區大成路100號'
  ]
};

export const TestRoutes = {
  morning: {
    name: '早班路線 - 大安信義區',
    driver: '陳師傅',
    vehicle: 'LG-001',
    startTime: '08:00',
    orders: 5,
    estimatedDuration: '4小時',
    totalDistance: '25公里'
  },
  afternoon: {
    name: '午班路線 - 士林北投區',
    driver: '李師傅',
    vehicle: 'LG-002',
    startTime: '13:00',
    orders: 7,
    estimatedDuration: '5小時',
    totalDistance: '35公里'
  },
  industrial: {
    name: '工業區專送',
    driver: '王師傅',
    vehicle: 'LG-003',
    startTime: '06:00',
    orders: 3,
    estimatedDuration: '6小時',
    totalDistance: '80公里'
  }
};

export const ErrorMessages = {
  invalidCredentials: '帳號或密碼錯誤',
  sessionExpired: '登入逾時，請重新登入',
  networkError: '網路連線失敗，請稍後再試',
  requiredField: '此欄位為必填',
  invalidPhone: '請輸入有效的電話號碼',
  invalidEmail: '請輸入有效的電子郵件',
  duplicateOrder: '此客戶今日已有訂單',
  stockInsufficient: '庫存不足'
};

export const SuccessMessages = {
  loginSuccess: '登入成功',
  orderCreated: '訂單建立成功',
  orderUpdated: '訂單更新成功',
  deliveryCompleted: '配送完成',
  customerSaved: '客戶資料儲存成功',
  routeOptimized: '路線優化完成'
};

export const ValidationPatterns = {
  phone: /^0[2-9]-?\d{3,4}-?\d{4}$|^09\d{2}-?\d{3}-?\d{3}$/,
  taiwanId: /^[A-Z][12]\d{8}$/,
  uniformNumber: /^\d{8}$/,
  postalCode: /^\d{3,5}$/
};

// Helper functions for generating test data
export function generateOrderNumber(): string {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
  return `LG${year}${month}${day}${random}`;
}

export function generateInvoiceNumber(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const prefix = chars[Math.floor(Math.random() * chars.length)] + 
                 chars[Math.floor(Math.random() * chars.length)];
  const number = Math.floor(Math.random() * 100000000).toString().padStart(8, '0');
  return `${prefix}${number}`;
}

export function formatTaiwanDate(date: Date): string {
  const year = date.getFullYear() - 1911; // Convert to ROC year
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `民國${year}年${month}月${day}日`;
}

export function formatCurrency(amount: number): string {
  return `NT$ ${amount.toLocaleString('zh-TW')}`;
}

// Additional test data for payment processing
export const TestPayments = {
  customerWithCredit: {
    id: 'cust_001',
    name: '信用客戶公司',
    creditLimit: 50000,
    currentCredit: 30000
  },
  customerWithLowCredit: {
    id: 'cust_002',
    name: '小額信用客戶',
    creditLimit: 5000,
    currentCredit: 4000
  },
  generateBankResponseFile: () => {
    // Generate mock bank response file for testing
    const content = `H01,20240120,812,1234567890123
D01,INV20240101001,2400,Y,20240120
D01,INV20240101002,3600,Y,20240120
D01,INV20240101003,1200,N,20240120,NSF
T01,3,7200,2`;
    
    return {
      name: 'ACH_20240120_response.txt',
      content: Buffer.from(content),
      mimeType: 'text/plain'
    };
  }
};

// Additional test data for invoice management
export const TestInvoices = {
  sampleInvoice: {
    invoiceNumber: 'AB12345678',
    orderNumber: 'ORD20240101001',
    customerName: '林太太',
    amount: 840,
    tax: 40,
    total: 880,
    status: 'active'
  },
  b2bInvoice: {
    invoiceNumber: 'CD98765432',
    orderNumber: 'ORD20240101002',
    customerName: '幸福小吃店',
    customerTaxId: '12345678',
    amount: 2800,
    tax: 140,
    total: 2940,
    status: 'active',
    type: 'triplicate'
  }
};

// Taiwan-specific data formats
export const TaiwanData = {
  phoneFormats: [
    '09XX-XXX-XXX',  // Mobile
    '02-XXXX-XXXX',  // Taipei
    '03-XXX-XXXX',   // Hsinchu/Hualien
    '04-XXXX-XXXX',  // Taichung
    '06-XXX-XXXX',   // Tainan
    '07-XXX-XXXX'    // Kaohsiung
  ],
  addressFormat: {
    example: '100台北市中正區重慶南路一段122號',
    pattern: /^\d{3,5}[^\d]+[市縣][^\d]+[區鄉鎮市][^\d]+[路街道巷弄]\d+[號樓]/
  },
  taxIdFormat: {
    length: 8,
    pattern: /^\d{8}$/
  },
  invoiceFormat: {
    pattern: /^[A-Z]{2}\d{8}$/,
    example: 'AB12345678'
  },
  bankCodes: {
    '004': '台灣銀行',
    '005': '土地銀行',
    '006': '合作金庫',
    '007': '第一銀行',
    '008': '華南銀行',
    '009': '彰化銀行',
    '012': '台北富邦',
    '013': '國泰世華',
    '812': '台新銀行',
    '822': '中國信託'
  }
};