// Taiwan-specific test data fixtures

export const testUsers = {
  admin: {
    username: 'admin',
    password: 'admin123',
    role: 'admin',
    displayName: '系統管理員'
  },
  manager: {
    username: 'manager1',
    password: 'manager123',
    role: 'manager',
    displayName: '經理'
  },
  officeStaff: {
    username: 'office1',
    password: 'office123',
    role: 'office_staff',
    displayName: '辦公室人員'
  },
  driver: {
    username: 'driver1',
    password: 'driver123',
    role: 'driver',
    displayName: '司機一號'
  }
};

export const testCustomers = [
  {
    name: '王大明',
    phone: '0912345678',
    address: '台北市大安區忠孝東路四段1號',
    postalCode: '106',
    contact: '王太太',
    notes: '週末不在家',
    gasType: '桶裝瓦斯',
    cylinderSize: '20公斤'
  },
  {
    name: '李小華',
    phone: '0923456789',
    address: '新北市板橋區文化路一段100號',
    postalCode: '220',
    contact: '李先生',
    notes: '請打電話通知',
    gasType: '桶裝瓦斯',
    cylinderSize: '16公斤'
  },
  {
    name: '張美玲',
    phone: '0934567890',
    address: '台中市西屯區台灣大道三段99號',
    postalCode: '407',
    contact: '張小姐',
    notes: '管理員代收',
    gasType: '桶裝瓦斯',
    cylinderSize: '20公斤'
  },
  {
    name: '陳建國',
    phone: '0945678901',
    address: '高雄市前鎮區中山二路2號',
    postalCode: '806',
    contact: '陳太太',
    notes: '後門進入',
    gasType: '桶裝瓦斯',
    cylinderSize: '50公斤'
  },
  {
    name: '林淑芬',
    phone: '0956789012',
    address: '台南市東區大學路1號',
    postalCode: '701',
    contact: '林小姐',
    notes: '早上9點後送貨',
    gasType: '桶裝瓦斯',
    cylinderSize: '20公斤'
  }
];

export const testOrders = [
  {
    customerName: '王大明',
    quantity: 1,
    deliveryDate: new Date().toISOString().split('T')[0],
    urgency: 'normal',
    notes: '請按門鈴',
    paymentMethod: '現金',
    amount: 800
  },
  {
    customerName: '李小華',
    quantity: 2,
    deliveryDate: new Date(Date.now() + 86400000).toISOString().split('T')[0], // Tomorrow
    urgency: 'urgent',
    notes: '急件，請優先處理',
    paymentMethod: '轉帳',
    amount: 1600
  },
  {
    customerName: '張美玲',
    quantity: 1,
    deliveryDate: new Date(Date.now() + 172800000).toISOString().split('T')[0], // Day after tomorrow
    urgency: 'normal',
    notes: '管理室代收',
    paymentMethod: '現金',
    amount: 800
  }
];

export const testRoutes = [
  {
    name: '北區路線A',
    date: new Date().toISOString().split('T')[0],
    driver: 'driver1',
    stops: [
      { customer: '王大明', sequence: 1, estimatedTime: '09:00' },
      { customer: '李小華', sequence: 2, estimatedTime: '10:00' }
    ],
    estimatedDistance: '15.5 km',
    estimatedDuration: '2小時'
  },
  {
    name: '中區路線B',
    date: new Date().toISOString().split('T')[0],
    driver: 'driver2',
    stops: [
      { customer: '張美玲', sequence: 1, estimatedTime: '09:30' },
      { customer: '陳建國', sequence: 2, estimatedTime: '11:00' }
    ],
    estimatedDistance: '25.3 km',
    estimatedDuration: '3小時'
  }
];

export const testAddresses = {
  taipei: [
    '台北市信義區市府路1號',
    '台北市中正區凱達格蘭大道1號',
    '台北市大安區羅斯福路四段1號',
    '台北市松山區敦化北路100號',
    '台北市內湖區瑞光路188號'
  ],
  newTaipei: [
    '新北市板橋區中山路一段161號',
    '新北市三重區新北大道一段1號',
    '新北市新店區北新路三段200號',
    '新北市淡水區中正路1號',
    '新北市永和區永和路一段1號'
  ],
  taichung: [
    '台中市西屯區台灣大道三段99號',
    '台中市北區三民路三段129號',
    '台中市南屯區公益路二段51號',
    '台中市豐原區中正路1號',
    '台中市大里區中興路二段478號'
  ],
  kaohsiung: [
    '高雄市苓雅區四維三路2號',
    '高雄市前鎮區成功二路39號',
    '高雄市左營區博愛二路757號',
    '高雄市三民區九如一路777號',
    '高雄市鳳山區光復路二段132號'
  ]
};

export const testPhoneNumbers = [
  '0912345678',
  '0923456789',
  '0934567890',
  '0945678901',
  '0956789012',
  '0967890123',
  '0978901234',
  '0989012345',
  '0228825252',
  '0223456789',
  '0422345678',
  '0423456789',
  '072345678',
  '073456789'
];

// Helper functions for generating test data
export function generateCustomer(index: number = 0) {
  const surnames = ['王', '李', '張', '陳', '林', '黃', '吳', '劉', '蔡', '楊'];
  const givenNames = ['大明', '小華', '美玲', '建國', '淑芬', '志明', '淑惠', '家豪', '雅婷', '俊傑'];
  const cities = Object.keys(testAddresses);
  const city = cities[index % cities.length];
  const addresses = testAddresses[city as keyof typeof testAddresses];
  
  return {
    name: surnames[index % surnames.length] + givenNames[index % givenNames.length],
    phone: testPhoneNumbers[index % testPhoneNumbers.length],
    address: addresses[index % addresses.length],
    contact: `聯絡人${index + 1}`,
    notes: `測試備註 ${index + 1}`,
    gasType: '桶裝瓦斯',
    cylinderSize: index % 3 === 0 ? '50公斤' : '20公斤'
  };
}

export function generateOrder(customerName: string, daysFromNow: number = 0) {
  const deliveryDate = new Date();
  deliveryDate.setDate(deliveryDate.getDate() + daysFromNow);
  
  return {
    customerName,
    quantity: Math.floor(Math.random() * 3) + 1,
    deliveryDate: deliveryDate.toISOString().split('T')[0],
    urgency: Math.random() > 0.8 ? 'urgent' : 'normal',
    notes: '測試訂單',
    paymentMethod: Math.random() > 0.5 ? '現金' : '轉帳',
    amount: 800 * (Math.floor(Math.random() * 3) + 1)
  };
}

export function generateRoute(driverUsername: string, customers: string[], date: Date = new Date()) {
  return {
    name: `測試路線-${date.toLocaleDateString('zh-TW')}`,
    date: date.toISOString().split('T')[0],
    driver: driverUsername,
    stops: customers.map((customer, index) => ({
      customer,
      sequence: index + 1,
      estimatedTime: `${9 + index}:${index * 15 % 60 === 0 ? '00' : index * 15 % 60}`
    })),
    estimatedDistance: `${customers.length * 5 + Math.random() * 10} km`,
    estimatedDuration: `${customers.length * 0.5}小時`
  };
}

// Date helpers for Taiwan
export function formatTaiwanDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}/${month}/${day}`;
}

export function formatROCDate(date: Date): string {
  const rocYear = date.getFullYear() - 1911;
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `民國${rocYear}年${month}月${day}日`;
}

// Mock file generation for photo uploads
export async function generateMockPhoto(filename: string = 'test-photo.jpg'): Promise<File> {
  const canvas = document.createElement('canvas');
  canvas.width = 800;
  canvas.height = 600;
  const ctx = canvas.getContext('2d');
  
  if (!ctx) throw new Error('Could not create canvas context');
  
  // Draw a simple test pattern
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(0, 0, 800, 600);
  
  ctx.fillStyle = '#333';
  ctx.font = '48px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('測試照片', 400, 300);
  
  // Add timestamp
  ctx.font = '24px sans-serif';
  ctx.fillText(new Date().toLocaleString('zh-TW'), 400, 350);
  
  return new Promise((resolve) => {
    canvas.toBlob((blob) => {
      if (!blob) throw new Error('Could not create blob');
      const file = new File([blob], filename, { type: 'image/jpeg' });
      resolve(file);
    }, 'image/jpeg', 0.8);
  });
}

// API response mocks
export const mockApiResponses = {
  login: {
    access_token: 'mock-jwt-token',
    refresh_token: 'mock-refresh-token',
    token_type: 'bearer',
    user: {
      id: 1,
      username: 'admin',
      role: 'admin',
      display_name: '系統管理員'
    }
  },
  
  customerList: {
    items: testCustomers.slice(0, 10),
    total: 50,
    page: 1,
    size: 10,
    pages: 5
  },
  
  orderList: {
    items: testOrders,
    total: testOrders.length,
    page: 1,
    size: 10,
    pages: 1
  },
  
  routeList: {
    items: testRoutes,
    total: testRoutes.length
  },
  
  predictions: {
    predictions: testCustomers.map((customer, index) => ({
      customer_id: index + 1,
      customer_name: customer.name,
      predicted_demand: Math.floor(Math.random() * 3) + 1,
      confidence: 0.5 + Math.random() * 0.3,
      last_delivery_date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
      recommendation: '建議配送'
    })),
    generated_at: new Date().toISOString(),
    using_placeholder: true
  }
};

// Test environment setup
export async function setupTestData(page: unknown) {
  // Set up localStorage with test data if needed
  await page.evaluate(() => {
    // Set feature flags
    localStorage.setItem('feature_flags', JSON.stringify({
      offline_mode: true,
      placeholder_services: true,
      debug_mode: true
    }));
    
    // Set test mode
    localStorage.setItem('test_mode', 'true');
  });
}

export async function cleanupTestData(page: unknown) {
  await page.evaluate(() => {
    // Clear test data
    localStorage.removeItem('feature_flags');
    localStorage.removeItem('test_mode');
    localStorage.removeItem('offline_queue');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  });
}