import { faker } from '@faker-js/faker';

export class TestDataFactory {
  private static customerCounter = 0;
  private static orderCounter = 0;
  private static driverCounter = 0;

  /**
   * Create a unique customer with valid Taiwan-specific data
   */
  static createCustomer(overrides?: Partial<CustomerData>) {
    const timestamp = Date.now();
    const counter = ++this.customerCounter;
    
    const defaultData: CustomerData = {
      customerCode: `TEST${timestamp}${counter}`,
      shortName: `測試客戶${counter}`,
      invoiceTitle: `測試公司${counter}`,
      phone: this.generateTaiwanPhone(),
      mobile: this.generateTaiwanMobile(),
      address: this.generateTaiwanAddress(),
      area: this.randomArea(),
      deliveryTimeStart: '09:00',
      deliveryTimeEnd: '18:00',
      avgDailyUsage: faker.number.int({ min: 5, max: 20 }),
      maxCycleDays: faker.number.int({ min: 20, max: 40 }),
      canDelayDays: faker.number.int({ min: 1, max: 5 }),
      paymentMethod: this.randomPaymentMethod(),
      status: 'active'
    };

    return { ...defaultData, ...overrides };
  }

  /**
   * Create a unique order with valid data
   */
  static createOrder(overrides?: Partial<OrderData>) {
    const timestamp = Date.now();
    const counter = ++this.orderCounter;
    
    const defaultData: OrderData = {
      orderNumber: `ORD${timestamp}${counter}`,
      customerCode: `CUST${faker.number.int({ min: 1, max: 100 })}`,
      orderDate: new Date().toISOString().split('T')[0],
      deliveryDate: faker.date.future({ days: 7 }).toISOString().split('T')[0],
      status: this.randomOrderStatus(),
      products: [
        {
          productCode: '20KG',
          productName: '20公斤瓦斯桶',
          quantity: faker.number.int({ min: 1, max: 5 }),
          unitPrice: 800,
          subtotal: 0
        }
      ],
      totalAmount: 0,
      deliveryAddress: this.generateTaiwanAddress(),
      deliveryTime: `${faker.number.int({ min: 9, max: 17 })}:00`,
      notes: faker.lorem.sentence()
    };

    // Calculate totals
    defaultData.products.forEach(product => {
      product.subtotal = product.quantity * product.unitPrice;
    });
    defaultData.totalAmount = defaultData.products.reduce((sum, p) => sum + p.subtotal, 0);

    return { ...defaultData, ...overrides };
  }

  /**
   * Create a unique driver with valid data
   */
  static createDriver(overrides?: Partial<DriverData>) {
    const counter = ++this.driverCounter;
    
    const defaultData: DriverData = {
      driverCode: `DRV${counter.toString().padStart(3, '0')}`,
      name: `測試司機${counter}`,
      mobile: this.generateTaiwanMobile(),
      vehicleNumber: this.generateVehicleNumber(),
      status: 'available',
      currentLocation: {
        lat: 25.0330 + faker.number.float({ min: -0.1, max: 0.1, precision: 0.0001 }),
        lng: 121.5654 + faker.number.float({ min: -0.1, max: 0.1, precision: 0.0001 })
      },
      assignedRoutes: [],
      maxCapacity: faker.number.int({ min: 30, max: 50 })
    };

    return { ...defaultData, ...overrides };
  }

  // Helper methods
  private static generateTaiwanPhone(): string {
    const areaCodes = ['02', '03', '04', '05', '06', '07', '08'];
    const areaCode = faker.helpers.arrayElement(areaCodes);
    const number = faker.number.int({ min: 1000000, max: 9999999 });
    return `${areaCode}-${number}`;
  }

  private static generateTaiwanMobile(): string {
    const prefix = faker.helpers.arrayElement(['0910', '0911', '0912', '0919', '0921', '0922', '0933', '0955']);
    const suffix = faker.number.int({ min: 100000, max: 999999 });
    return `${prefix}-${suffix}`;
  }

  private static generateTaiwanAddress(): string {
    const cities = ['台北市', '新北市', '桃園市', '台中市', '台南市', '高雄市'];
    const districts = ['信義區', '大安區', '中山區', '中正區', '萬華區'];
    const roads = ['忠孝東路', '信義路', '中山北路', '民生東路', '南京東路'];
    const sections = ['一段', '二段', '三段', '四段', '五段'];
    
    const city = faker.helpers.arrayElement(cities);
    const district = faker.helpers.arrayElement(districts);
    const road = faker.helpers.arrayElement(roads);
    const section = faker.helpers.arrayElement(sections);
    const number = faker.number.int({ min: 1, max: 500 });
    const floor = faker.number.int({ min: 1, max: 20 });
    
    return `${city}${district}${road}${section}${number}號${floor}樓`;
  }

  private static generateVehicleNumber(): string {
    const letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
    const prefix = faker.helpers.arrayElements(letters.split(''), 3).join('');
    const suffix = faker.number.int({ min: 1000, max: 9999 });
    return `${prefix}-${suffix}`;
  }

  private static randomArea(): string {
    const areas = ['A-瑞光', 'B-內湖', 'C-南港', 'D-信義', 'E-大安'];
    return faker.helpers.arrayElement(areas);
  }

  private static randomPaymentMethod(): string {
    const methods = ['cash', 'monthly', 'credit'];
    return faker.helpers.arrayElement(methods);
  }

  private static randomOrderStatus(): string {
    const statuses = ['pending', 'confirmed', 'in_delivery', 'delivered', 'cancelled'];
    return faker.helpers.arrayElement(statuses);
  }
}

// Type definitions
interface CustomerData {
  customerCode: string;
  shortName: string;
  invoiceTitle: string;
  phone: string;
  mobile: string;
  address: string;
  area: string;
  deliveryTimeStart: string;
  deliveryTimeEnd: string;
  avgDailyUsage: number;
  maxCycleDays: number;
  canDelayDays: number;
  paymentMethod: string;
  status: string;
}

interface OrderData {
  orderNumber: string;
  customerCode: string;
  orderDate: string;
  deliveryDate: string;
  status: string;
  products: ProductData[];
  totalAmount: number;
  deliveryAddress: string;
  deliveryTime: string;
  notes: string;
}

interface ProductData {
  productCode: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  subtotal: number;
}

interface DriverData {
  driverCode: string;
  name: string;
  mobile: string;
  vehicleNumber: string;
  status: string;
  currentLocation: {
    lat: number;
    lng: number;
  };
  assignedRoutes: string[];
  maxCapacity: number;
}

export type { CustomerData, OrderData, DriverData, ProductData };