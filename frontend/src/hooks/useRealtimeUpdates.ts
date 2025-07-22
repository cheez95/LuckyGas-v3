import { useEffect, useCallback } from 'react';
import { notification } from 'antd';
import { useWebSocketContext } from '../contexts/WebSocketContext';

interface RealtimeUpdateOptions {
  onOrderUpdate?: (order: any) => void;
  onRouteUpdate?: (route: any) => void;
  onDriverLocation?: (location: any) => void;
  onDeliveryUpdate?: (delivery: any) => void;
  enableNotifications?: boolean;
}

export const useRealtimeUpdates = ({
  onOrderUpdate,
  onRouteUpdate,
  onDriverLocation,
  onDeliveryUpdate,
  enableNotifications = true,
}: RealtimeUpdateOptions) => {
  const { lastMessage, subscribeToOrderUpdates, subscribeToRouteUpdates } = useWebSocketContext();

  const handleMessage = useCallback((message: any) => {
    if (!message) return;

    switch (message.type) {
      case 'order.created':
      case 'order.updated':
      case 'order.assigned':
      case 'order.delivered':
      case 'order.cancelled':
        if (onOrderUpdate) {
          onOrderUpdate(message.data);
        }
        if (enableNotifications) {
          showOrderNotification(message);
        }
        break;

      case 'route.created':
      case 'route.updated':
      case 'route.assigned':
      case 'route.published':
      case 'route.started':
      case 'route.completed':
        if (onRouteUpdate) {
          onRouteUpdate(message.data);
        }
        if (enableNotifications) {
          showRouteNotification(message);
        }
        break;

      case 'driver.location':
        if (onDriverLocation) {
          onDriverLocation(message.data);
        }
        break;

      case 'delivery.update':
      case 'driver.arrived':
        if (onDeliveryUpdate) {
          onDeliveryUpdate(message.data);
        }
        if (enableNotifications) {
          showDeliveryNotification(message);
        }
        break;
    }
  }, [onOrderUpdate, onRouteUpdate, onDriverLocation, onDeliveryUpdate, enableNotifications]);

  useEffect(() => {
    if (lastMessage) {
      handleMessage(lastMessage);
    }
  }, [lastMessage, handleMessage]);

  const showOrderNotification = (message: any) => {
    const { type, data } = message;
    
    switch (type) {
      case 'order.created':
        notification.info({
          message: '新訂單',
          description: `訂單 ${data.order_id} 已建立`,
          placement: 'topRight',
        });
        break;
      
      case 'order.assigned':
        notification.success({
          message: '訂單指派',
          description: `訂單 ${data.order_id} 已指派給司機`,
          placement: 'topRight',
        });
        break;
      
      case 'order.delivered':
        notification.success({
          message: '訂單完成',
          description: `訂單 ${data.order_id} 已送達`,
          placement: 'topRight',
        });
        break;
      
      case 'order.cancelled':
        notification.warning({
          message: '訂單取消',
          description: `訂單 ${data.order_id} 已取消`,
          placement: 'topRight',
        });
        break;
    }
  };

  const showRouteNotification = (message: any) => {
    const { type, data } = message;
    
    switch (type) {
      case 'route.published':
        notification.info({
          message: '路線發布',
          description: `路線 ${data.route_id} 已發布`,
          placement: 'topRight',
        });
        break;
      
      case 'route.started':
        notification.info({
          message: '路線開始',
          description: `司機已開始執行路線 ${data.route_id}`,
          placement: 'topRight',
        });
        break;
      
      case 'route.completed':
        notification.success({
          message: '路線完成',
          description: `路線 ${data.route_id} 已完成所有配送`,
          placement: 'topRight',
        });
        break;
    }
  };

  const showDeliveryNotification = (message: any) => {
    const { type, data } = message;
    
    switch (type) {
      case 'driver.arrived':
        notification.info({
          message: '司機已到達',
          description: `司機已到達 ${data.customer_name} 的配送地點`,
          placement: 'topRight',
        });
        break;
      
      case 'delivery.update':
        notification.info({
          message: '配送更新',
          description: data.message || '配送狀態已更新',
          placement: 'topRight',
        });
        break;
    }
  };

  return {
    subscribeToOrder: (orderId: string) => subscribeToOrderUpdates(orderId),
    subscribeToRoute: (routeId: string) => subscribeToRouteUpdates(routeId),
  };
};