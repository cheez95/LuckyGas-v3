export const mockData = {
  users: [
    { 
      id: 1, 
      username: 'admin', 
      password: 'admin123', 
      role: 'admin', 
      display_name: '系統管理員',
      email: 'admin@luckygas.com.tw',
      full_name: '系統管理員',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    },
    { 
      id: 2, 
      username: 'driver1', 
      password: 'driver123', 
      role: 'driver', 
      display_name: '司機一號',
      email: 'driver1@luckygas.com.tw',
      full_name: '王大明',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    },
    { 
      id: 3, 
      username: 'office1', 
      password: 'office123', 
      role: 'office_staff', 
      display_name: '辦公室人員',
      email: 'office1@luckygas.com.tw',
      full_name: '李小華',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    },
    { 
      id: 4, 
      username: 'manager1', 
      password: 'manager123', 
      role: 'manager', 
      display_name: '經理',
      email: 'manager1@luckygas.com.tw',
      full_name: '張經理',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    }
  ],

  customers: [
    { 
      id: 1, 
      customer_code: 'C001',
      name: '王大明商行',
      short_name: '王大明',
      invoice_title: '王大明商行',
      tax_id: '12345678',
      address: '台北市大安區忠孝東路四段1號',
      area: 'A-瑞光',
      phone: '02-2771-2171',
      mobile: '0912-345-678',
      email: 'wang@example.com',
      contact_person: '王大明',
      delivery_time_start: '09:00',
      delivery_time_end: '18:00',
      avg_daily_usage: 15,
      payment_method: '月結',
      customer_type: '商業',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    },
    { 
      id: 2,
      customer_code: 'C002', 
      name: '小華餐廳',
      short_name: '李小華',
      invoice_title: '小華餐廳',
      tax_id: '23456789',
      address: '新北市板橋區文化路一段100號',
      area: 'B-四維',
      phone: '02-2968-4321',
      mobile: '0923-456-789',
      email: 'lee@example.com',
      contact_person: '李小華',
      delivery_time_start: '10:00',
      delivery_time_end: '17:00',
      avg_daily_usage: 20,
      payment_method: '現金',
      customer_type: '餐飲',
      is_active: true,
      created_at: '2024-01-05T00:00:00Z'
    },
    { 
      id: 3,
      customer_code: 'C003',
      name: '美玲食品行',
      short_name: '張美玲',
      invoice_title: '美玲食品行',
      tax_id: '34567890',
      address: '台中市西屯區台灣大道三段99號',
      area: 'C-漢中',
      phone: '04-2358-1234',
      mobile: '0934-567-890',
      email: 'zhang@example.com',
      contact_person: '張美玲',
      delivery_time_start: '08:00',
      delivery_time_end: '16:00',
      avg_daily_usage: 25,
      payment_method: '轉帳',
      customer_type: '餐飲',
      is_active: true,
      created_at: '2024-01-10T00:00:00Z'
    },
    { 
      id: 4,
      customer_code: 'C004',
      name: '建國工業',
      short_name: '陳建國',
      invoice_title: '建國工業股份有限公司',
      tax_id: '45678901',
      address: '高雄市前鎮區中山二路2號',
      area: 'D-東方大鎮',
      phone: '07-334-5678',
      mobile: '0945-678-901',
      email: 'chen@example.com',
      contact_person: '陳建國',
      delivery_time_start: '09:00',
      delivery_time_end: '17:00', 
      avg_daily_usage: 30,
      payment_method: '月結',
      customer_type: '工業',
      is_active: true,
      created_at: '2024-01-15T00:00:00Z'
    },
    { 
      id: 5,
      customer_code: 'C005',
      name: '淑芬小吃店',
      short_name: '林淑芬',
      invoice_title: '淑芬小吃店',
      tax_id: '56789012',
      address: '台南市東區大學路1號',
      area: 'E-其他',
      phone: '06-235-6789',
      mobile: '0956-789-012',
      email: 'lin@example.com',
      contact_person: '林淑芬',
      delivery_time_start: '11:00',
      delivery_time_end: '20:00',
      avg_daily_usage: 10,
      payment_method: '現金',
      customer_type: '餐飲',
      is_active: true,
      created_at: '2024-01-20T00:00:00Z'
    }
  ],

  orders: [
    { 
      id: 1, 
      customer_id: 1, 
      customer_name: '王大明商行',
      customer_code: 'C001',
      order_date: new Date().toISOString(),
      delivery_date: new Date(Date.now() + 86400000).toISOString(),
      status: 'pending',
      payment_status: 'unpaid',
      payment_method: '月結',
      total_amount: 800,
      order_items: [{
        id: 1,
        order_id: 1,
        product_id: 1,
        product_name: '16公斤鋼瓶',
        quantity: 1,
        unit_price: 800,
        total_price: 800
      }],
      created_by: 3,
      created_at: new Date().toISOString()
    },
    { 
      id: 2, 
      customer_id: 2, 
      customer_name: '小華餐廳',
      customer_code: 'C002',
      order_date: new Date().toISOString(),
      delivery_date: new Date(Date.now() + 172800000).toISOString(),
      status: 'pending',
      payment_status: 'unpaid',
      payment_method: '現金',
      total_amount: 1600,
      order_items: [{
        id: 2,
        order_id: 2,
        product_id: 1,
        product_name: '16公斤鋼瓶',
        quantity: 2,
        unit_price: 800,
        total_price: 1600
      }],
      created_by: 3,
      created_at: new Date().toISOString()
    },
    { 
      id: 3, 
      customer_id: 3, 
      customer_name: '美玲食品行',
      customer_code: 'C003',
      order_date: new Date(Date.now() - 86400000).toISOString(),
      delivery_date: new Date().toISOString(),
      status: 'in_progress',
      payment_status: 'unpaid',
      payment_method: '轉帳',
      total_amount: 800,
      order_items: [{
        id: 3,
        order_id: 3,
        product_id: 1,
        product_name: '16公斤鋼瓶',
        quantity: 1,
        unit_price: 800,
        total_price: 800
      }],
      created_by: 3,
      created_at: new Date(Date.now() - 86400000).toISOString()
    }
  ],

  routes: [
    {
      id: 1,
      route_number: 'R001',
      name: '北區路線A',
      date: new Date().toISOString().split('T')[0],
      route_date: new Date().toISOString(),
      driver_id: 2,
      driver_name: '王大明',
      vehicle_id: 1,
      vehicle_number: 'TPE-1234',
      status: 'in_progress',
      total_orders: 2,
      completed_orders: 0,
      total_distance: 15.5,
      estimated_duration: 120,
      actual_start_time: new Date(Date.now() - 3600000).toISOString(),
      actual_end_time: null,
      stops: [
        { 
          id: 1,
          route_id: 1,
          customer_id: 1, 
          customer_name: '王大明商行',
          customer_code: 'C001',
          address: '台北市大安區忠孝東路四段1號',
          sequence: 1, 
          estimated_arrival: '09:00',
          actual_arrival: null,
          status: 'pending',
          delivery_items: [{
            product_name: '16公斤鋼瓶',
            quantity: 1
          }]
        },
        { 
          id: 2,
          route_id: 1,
          customer_id: 2, 
          customer_name: '小華餐廳',
          customer_code: 'C002',
          address: '新北市板橋區文化路一段100號',
          sequence: 2, 
          estimated_arrival: '10:00',
          actual_arrival: null,
          status: 'pending',
          delivery_items: [{
            product_name: '16公斤鋼瓶',
            quantity: 2
          }]
        }
      ],
      created_at: new Date(Date.now() - 86400000).toISOString()
    }
  ],

  deliveries: [
    {
      id: 1,
      order_id: 3,
      route_id: 1,
      customer_id: 3,
      customer_name: '美玲食品行',
      delivery_date: new Date().toISOString(),
      status: 'pending',
      driver_id: 2,
      driver_name: '王大明'
    }
  ],

  predictions: [],

  notifications: [
    {
      id: 1,
      user_id: null, // Broadcast to all
      type: 'system',
      title: '系統公告',
      message: '系統將於今晚11點進行例行維護',
      priority: 'low',
      read: false,
      created_at: new Date(Date.now() - 3600000).toISOString()
    },
    {
      id: 2,
      user_id: 3, // Office staff
      type: 'order',
      title: '新訂單通知',
      message: '您有3筆新訂單待處理',
      priority: 'normal',
      read: false,
      created_at: new Date(Date.now() - 7200000).toISOString()
    }
  ],

  products: [
    { id: 1, name: '16公斤鋼瓶', size: '16kg', unit_price: 800 },
    { id: 2, name: '20公斤鋼瓶', size: '20kg', unit_price: 1000 },
    { id: 3, name: '50公斤鋼瓶', size: '50kg', unit_price: 2500 }
  ],

  areas: [
    { id: 1, code: 'A', name: 'A-瑞光' },
    { id: 2, code: 'B', name: 'B-四維' },
    { id: 3, code: 'C', name: 'C-漢中' },
    { id: 4, code: 'D', name: 'D-東方大鎮' },
    { id: 5, code: 'E', name: 'E-其他' }
  ]
};