import { Router } from 'express';
import { mockData } from '../mock-data';
import { verifyToken } from './auth';

const router = Router();

// Apply auth middleware to all routes
router.use(verifyToken);

// Get notifications for current user
router.get('/', (req, res) => {
  const unread_only = req.query.unread_only === 'true';
  const limit = parseInt(req.query.limit as string) || 20;
  const skip = parseInt(req.query.skip as string) || 0;
  
  // Filter notifications for current user or broadcast
  let filtered = mockData.notifications.filter(n => 
    n.user_id === null || n.user_id === req.user.user_id
  );
  
  // Filter by unread if requested
  if (unread_only) {
    filtered = filtered.filter(n => !n.read);
  }
  
  // Sort by created_at descending
  filtered.sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
  
  // Apply pagination
  const items = filtered.slice(skip, skip + limit);
  
  res.json({
    items,
    total: filtered.length,
    unread_count: filtered.filter(n => !n.read).length
  });
});

// Get notification statistics
router.get('/statistics', (req, res) => {
  const userNotifications = mockData.notifications.filter(n => 
    n.user_id === null || n.user_id === req.user.user_id
  );
  
  res.json({
    total: userNotifications.length,
    unread: userNotifications.filter(n => !n.read).length,
    by_type: {
      system: userNotifications.filter(n => n.type === 'system').length,
      order: userNotifications.filter(n => n.type === 'order').length,
      route: userNotifications.filter(n => n.type === 'route').length,
      alert: userNotifications.filter(n => n.type === 'alert').length
    },
    by_priority: {
      high: userNotifications.filter(n => n.priority === 'high').length,
      normal: userNotifications.filter(n => n.priority === 'normal').length,
      low: userNotifications.filter(n => n.priority === 'low').length
    }
  });
});

// Mark notification as read
router.put('/:id/read', (req, res) => {
  const notification = mockData.notifications.find(n => n.id === parseInt(req.params.id));
  
  if (!notification) {
    return res.status(404).json({ detail: '通知不存在' });
  }
  
  // Check permissions
  if (notification.user_id !== null && notification.user_id !== req.user.user_id) {
    return res.status(403).json({ detail: '無權操作此通知' });
  }
  
  notification.read = true;
  notification.read_at = new Date().toISOString();
  
  res.json(notification);
});

// Mark all notifications as read
router.post('/mark-all-read', (req, res) => {
  const userNotifications = mockData.notifications.filter(n => 
    n.user_id === null || n.user_id === req.user.user_id
  );
  
  let updatedCount = 0;
  userNotifications.forEach(n => {
    if (!n.read) {
      n.read = true;
      n.read_at = new Date().toISOString();
      updatedCount++;
    }
  });
  
  res.json({
    updated: updatedCount,
    message: `已將 ${updatedCount} 個通知標記為已讀`
  });
});

// Delete notification
router.delete('/:id', (req, res) => {
  const index = mockData.notifications.findIndex(n => n.id === parseInt(req.params.id));
  
  if (index === -1) {
    return res.status(404).json({ detail: '通知不存在' });
  }
  
  const notification = mockData.notifications[index];
  
  // Check permissions
  if (notification.user_id !== null && notification.user_id !== req.user.user_id) {
    return res.status(403).json({ detail: '無權刪除此通知' });
  }
  
  mockData.notifications.splice(index, 1);
  res.status(204).send();
});

// Create notification (for testing)
router.post('/', (req, res) => {
  const newNotification = {
    id: Math.max(...mockData.notifications.map(n => n.id)) + 1,
    user_id: req.body.user_id || null,
    type: req.body.type || 'system',
    title: req.body.title,
    message: req.body.message,
    priority: req.body.priority || 'normal',
    read: false,
    created_at: new Date().toISOString(),
    data: req.body.data || {}
  };
  
  mockData.notifications.push(newNotification);
  
  // If WebSocket is available, emit notification
  if (global.io) {
    if (newNotification.user_id) {
      global.io.to(`user:${newNotification.user_id}`).emit('notification', newNotification);
    } else {
      global.io.emit('notification', newNotification);
    }
  }
  
  res.status(201).json(newNotification);
});

// Get notification preferences
router.get('/preferences', (req, res) => {
  // Mock preferences
  res.json({
    email_notifications: {
      order_updates: true,
      route_assignments: true,
      system_alerts: true,
      marketing: false
    },
    push_notifications: {
      order_updates: true,
      route_assignments: true,
      system_alerts: true,
      marketing: false
    },
    sms_notifications: {
      urgent_alerts: true,
      delivery_confirmations: false
    },
    quiet_hours: {
      enabled: true,
      start: '22:00',
      end: '08:00'
    }
  });
});

// Update notification preferences
router.put('/preferences', (req, res) => {
  // Mock update
  res.json({
    ...req.body,
    updated_at: new Date().toISOString()
  });
});

export { router as notificationRoutes };