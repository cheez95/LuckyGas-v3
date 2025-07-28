import { Server, Socket } from 'socket.io';
import { mockData } from './mock-data';

export class WebSocketManager {
  private io: Server;
  private locationUpdateInterval: NodeJS.Timeout | null = null;

  constructor(io: Server) {
    this.io = io;
    this.startSimulations();
  }

  startSimulations() {
    // Simulate driver location updates every 30 seconds
    this.locationUpdateInterval = setInterval(() => {
      this.simulateDriverLocationUpdates();
    }, 30000);

    // Simulate random notifications
    setInterval(() => {
      this.simulateRandomNotification();
    }, 60000);
  }

  simulateDriverLocationUpdates() {
    const activeRoutes = mockData.routes.filter(r => r.status === 'in_progress');
    
    activeRoutes.forEach(route => {
      const location = {
        route_id: route.id,
        driver_id: route.driver_id,
        latitude: 25.0330 + (Math.random() - 0.5) * 0.1,
        longitude: 121.5654 + (Math.random() - 0.5) * 0.1,
        speed: Math.floor(Math.random() * 60),
        heading: Math.floor(Math.random() * 360),
        accuracy: 10,
        timestamp: new Date().toISOString()
      };

      this.io.to(`route:${route.id}`).emit('driver-location', location);
    });
  }

  simulateRandomNotification() {
    const notifications = [
      {
        type: 'order',
        title: '新訂單',
        message: '您有一筆新訂單待處理',
        priority: 'normal'
      },
      {
        type: 'route',
        title: '路線優化完成',
        message: '明日配送路線已完成優化',
        priority: 'normal'
      },
      {
        type: 'alert',
        title: '庫存警告',
        message: '16公斤鋼瓶庫存低於安全水位',
        priority: 'high'
      },
      {
        type: 'system',
        title: '系統維護通知',
        message: '系統將於今晚11點進行例行維護',
        priority: 'low'
      }
    ];

    const notification = notifications[Math.floor(Math.random() * notifications.length)];
    const fullNotification = {
      id: Date.now(),
      ...notification,
      created_at: new Date().toISOString(),
      read: false
    };

    // Send to all connected admin and manager users
    this.io.to('role:admin').to('role:manager').emit('notification', fullNotification);
  }

  broadcastLocationUpdate(driverId: number, locationData: any) {
    const driver = mockData.users.find(u => u.id === driverId);
    if (!driver) return;

    // Find active route for this driver
    const activeRoute = mockData.routes.find(
      r => r.driver_id === driverId && r.status === 'in_progress'
    );

    if (activeRoute) {
      const update = {
        route_id: activeRoute.id,
        driver_id: driverId,
        driver_name: driver.display_name,
        ...locationData,
        timestamp: new Date().toISOString()
      };

      // Broadcast to all users watching this route
      this.io.to(`route:${activeRoute.id}`).emit('driver-location', update);
      
      // Also broadcast to all managers and admins
      this.io.to('role:admin').to('role:manager').emit('driver-location', update);
    }
  }

  sendUserNotifications(socket: Socket, userId: number) {
    // Send unread notifications for the user
    const userNotifications = mockData.notifications
      .filter(n => n.user_id === userId || n.user_id === null)
      .map(n => ({
        ...n,
        id: Date.now() + Math.random(),
        created_at: new Date(Date.now() - Math.random() * 86400000).toISOString()
      }));

    socket.emit('notifications', userNotifications);
  }

  sendOrderUpdate(orderId: number, status: string) {
    const order = mockData.orders.find(o => o.id === orderId);
    if (!order) return;

    const update = {
      order_id: orderId,
      status,
      updated_at: new Date().toISOString(),
      customer_name: order.customer_name
    };

    // Send to all office staff, managers, and admins
    this.io.to('role:office_staff')
      .to('role:manager')
      .to('role:admin')
      .emit('order-update', update);
  }

  sendDeliveryComplete(deliveryId: number, driverId: number) {
    const delivery = mockData.deliveries.find(d => d.id === deliveryId);
    if (!delivery) return;

    const update = {
      delivery_id: deliveryId,
      driver_id: driverId,
      completed_at: new Date().toISOString(),
      customer_name: delivery.customer_name,
      signature_url: 'mock://signature.png',
      photo_urls: ['mock://photo1.jpg']
    };

    // Send to all relevant users
    this.io.emit('delivery-complete', update);
  }

  sendRouteUpdate(routeId: number, update: any) {
    this.io.to(`route:${routeId}`).emit('route-update', {
      route_id: routeId,
      ...update,
      updated_at: new Date().toISOString()
    });
  }

  sendSystemAlert(alert: any) {
    this.io.emit('system-alert', {
      id: Date.now(),
      ...alert,
      created_at: new Date().toISOString()
    });
  }

  cleanup() {
    if (this.locationUpdateInterval) {
      clearInterval(this.locationUpdateInterval);
    }
  }
}