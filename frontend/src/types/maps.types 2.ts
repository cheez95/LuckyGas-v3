/**
 * Type definitions for map-related components
 */

export interface MapPosition {
  lat: number;
  lng: number;
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface RouteStop {
  id: string;
  customerId: string;
  customerName: string;
  address: string;
  position: MapPosition;
  sequence: number;
  estimatedArrival: Date;
  actualArrival?: Date;
  estimatedDuration: number;
  status: 'pending' | 'in-progress' | 'completed' | 'skipped';
  packages: {
    cylinderType: string;
    quantity: number;
  }[];
  notes?: string;
  priority?: 'normal' | 'high' | 'urgent';
}

export interface Route {
  id: string;
  driverId: string;
  driverName: string;
  vehicleId: string;
  date: Date;
  status: 'not-started' | 'in-progress' | 'completed' | 'delayed';
  stops: RouteStop[];
  polyline?: string;
  totalDistance: number;
  totalDuration: number;
  startTime: Date;
  endTime?: Date;
  optimizationMode?: 'time' | 'distance' | 'fuel';
  color?: string;
}

export interface Driver {
  id: string;
  name: string;
  vehicleId: string;
  currentPosition?: MapPosition;
  lastUpdate?: Date;
  status: 'offline' | 'available' | 'on-route' | 'break';
  assignedRouteId?: string;
  phoneNumber?: string;
}

export interface MapMarker {
  id: string;
  position: MapPosition;
  type: 'driver' | 'customer' | 'depot' | 'priority';
  title: string;
  info?: string;
  icon?: string;
  color?: string;
  draggable?: boolean;
  animation?: 'DROP' | 'BOUNCE';
}

export interface RouteOptimizationRequest {
  date: Date;
  vehicleIds?: string[];
  constraints?: {
    maxRouteDistance?: number;
    maxRouteDuration?: number;
    timeWindows?: boolean;
  };
  mode: 'time' | 'distance' | 'balanced';
}

export interface RouteUpdateRequest {
  routeId: string;
  stops: {
    stopId: string;
    sequence: number;
  }[];
}

export interface MapControl {
  position: google.maps.ControlPosition;
  element: HTMLElement;
}

export interface RouteFilter {
  driverIds?: string[];
  statuses?: Route['status'][];
  dateRange?: {
    start: Date;
    end: Date;
  };
  area?: MapBounds;
}

export interface MapEvent {
  type: 'marker-click' | 'route-click' | 'map-click' | 'bounds-changed';
  data: any;
  position?: MapPosition;
}

export interface DragDropEvent {
  stopId: string;
  fromRouteId: string;
  toRouteId: string;
  fromIndex: number;
  toIndex: number;
}

export interface RouteVisualizationOptions {
  showStops: boolean;
  showDrivers: boolean;
  showLabels: boolean;
  showInfoWindows: boolean;
  clusterStops: boolean;
  animateDrivers: boolean;
  showTraffic: boolean;
}

export interface MapTheme {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  danger: string;
  info: string;
}

// WebSocket message types for real-time updates
export interface RouteUpdateMessage {
  type: 'route-update';
  routeId: string;
  updates: Partial<Route>;
}

export interface DriverLocationMessage {
  type: 'driver-location';
  driverId: string;
  position: MapPosition;
  speed?: number;
  heading?: number;
  timestamp: Date;
}

export interface StopStatusMessage {
  type: 'stop-status';
  routeId: string;
  stopId: string;
  status: RouteStop['status'];
  actualArrival?: Date;
}

export type WebSocketMessage = 
  | RouteUpdateMessage 
  | DriverLocationMessage 
  | StopStatusMessage;

// Map interaction callbacks
export interface MapCallbacks {
  onMarkerClick?: (marker: MapMarker) => void;
  onRouteClick?: (route: Route) => void;
  onMapClick?: (position: MapPosition) => void;
  onBoundsChanged?: (bounds: MapBounds) => void;
  onStopDragEnd?: (event: DragDropEvent) => void;
  onRouteHover?: (route: Route | null) => void;
}

// Route statistics
export interface RouteStats {
  totalRoutes: number;
  completedRoutes: number;
  inProgressRoutes: number;
  delayedRoutes: number;
  totalStops: number;
  completedStops: number;
  averageDelay: number;
  totalDistance: number;
  fuelSaved: number;
}