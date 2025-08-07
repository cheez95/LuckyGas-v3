// Mock implementation of useWebSocket hooks

export const useWebSocket = () => ({
  isConnected: true,
  ws: null,
  sendMessage: jest.fn(),
  lastMessage: null,
  reconnect: jest.fn(),
  disconnect: jest.fn(),
  error: null,
  readyState: 1, // WebSocket.OPEN
});

export const useDriverWebSocket = () => ({
  on: jest.fn(),
  off: jest.fn(),
  emit: jest.fn(),
  updateLocation: jest.fn(),
  updateDeliveryStatus: jest.fn(),
  completedDelivery: jest.fn(),
  isConnected: true,
  error: null,
});

export const useOfficeWebSocket = () => ({
  on: jest.fn(),
  off: jest.fn(),
  emit: jest.fn(),
  subscribeToCustomerUpdates: jest.fn(),
  unsubscribeFromCustomerUpdates: jest.fn(),
  subscribeToOrderUpdates: jest.fn(),
  unsubscribeFromOrderUpdates: jest.fn(),
  subscribeToRouteUpdates: jest.fn(),
  unsubscribeFromRouteUpdates: jest.fn(),
  isConnected: true,
  error: null,
});

export default useWebSocket;