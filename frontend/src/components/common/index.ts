// Base components for consolidating common functionality
export { default as BaseListComponent } from './BaseListComponent';
export { default as BaseModal } from './BaseModal';

// Re-export types for easier importing
export type {
  BaseListComponentProps,
  BaseListFilter,
  BaseListStats,
  BaseListAction,
  BaseBulkAction,
} from './BaseListComponent';

export type {
  BaseModalProps,
  BaseModalAction,
} from './BaseModal';

// Existing exports
export { default as AccessibilityChecker } from './AccessibilityChecker';
export { default as AccessibleForm } from './AccessibleForm';
export { default as AccessibleNavigation } from './AccessibleNavigation';
export { default as ErrorBoundary } from './ErrorBoundary';
export { default as GoogleMapsPlaceholder } from './GoogleMapsPlaceholder';
export { default as NotificationBell } from './NotificationBell';
export { default as OfflineIndicator } from './OfflineIndicator';
export { default as SecureGoogleMap } from './SecureGoogleMap';
export { default as SessionManager } from './SessionManager';
export { default as WebSocketManager } from './WebSocketManager';
export { default as WebSocketStatus } from './WebSocketStatus';