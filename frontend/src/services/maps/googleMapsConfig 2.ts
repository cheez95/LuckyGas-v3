/**
 * Google Maps configuration for Taiwan
 */

export const DEFAULT_MAP_CONFIG = {
  // Default center point (Taipei)
  defaultCenter: { lat: 25.0330, lng: 121.5654 },
  // Default zoom level
  defaultZoom: 12,
  // Map options
  mapOptions: {
    mapTypeControl: true,
    streetViewControl: false,
    fullscreenControl: true,
    zoomControl: true,
    scaleControl: true,
    rotateControl: false,
    // Disable POI to reduce clutter
    styles: [
      {
        featureType: 'poi.business',
        elementType: 'labels',
        stylers: [{ visibility: 'off' }],
      },
    ],
  },
  // Taiwan-specific bounds
  taiwanBounds: {
    north: 25.3,
    south: 21.9,
    east: 122.0,
    west: 120.0,
  },
};

// Route visualization colors
export const ROUTE_COLORS = {
  // Status-based colors
  onTime: '#52c41a',      // Green
  slightDelay: '#fadb14', // Yellow
  moderateDelay: '#fa8c16', // Orange
  severeDelay: '#f5222d',  // Red
  notStarted: '#1890ff',   // Blue
  priority: '#722ed1',     // Purple
  
  // Route polyline colors
  active: '#1890ff',
  inactive: '#d9d9d9',
  optimized: '#52c41a',
  manual: '#fa8c16',
};

// Marker configurations
export const MARKER_CONFIGS = {
  driver: {
    scale: 12,
    fillColor: '#1890ff',
    strokeColor: '#fff',
    strokeWeight: 2,
    animation: 'DROP',
  },
  customer: {
    scale: 10,
    fillColor: '#52c41a',
    strokeColor: '#fff',
    strokeWeight: 2,
  },
  depot: {
    scale: 14,
    fillColor: '#fa8c16',
    strokeColor: '#fff',
    strokeWeight: 3,
  },
  priority: {
    scale: 12,
    fillColor: '#722ed1',
    strokeColor: '#fff',
    strokeWeight: 2,
    animation: 'BOUNCE',
  },
};

// Clustering options
export const CLUSTER_OPTIONS = {
  imagePath: 'https://developers.google.com/maps/documentation/javascript/examples/markerclusterer/m',
  gridSize: 60,
  maxZoom: 15,
  minimumClusterSize: 3,
  styles: [
    {
      textColor: '#fff',
      url: '',
      height: 53,
      width: 53,
      anchorText: [-3, 0],
      textSize: 12,
      backgroundPosition: 'center',
    },
  ],
};

// Animation durations (ms)
export const ANIMATION_DURATIONS = {
  markerMove: 500,
  routeUpdate: 300,
  panTo: 500,
};

// Map control positions
export const CONTROL_POSITIONS = {
  routeControl: 'TOP_LEFT',
  searchBox: 'TOP_CENTER',
  legendControl: 'RIGHT_BOTTOM',
};

// Helper function to get route color by status
export function getRouteColorByStatus(status: string): string {
  const statusMap: { [key: string]: string } = {
    'on-time': ROUTE_COLORS.onTime,
    'slight-delay': ROUTE_COLORS.slightDelay,
    'moderate-delay': ROUTE_COLORS.moderateDelay,
    'severe-delay': ROUTE_COLORS.severeDelay,
    'not-started': ROUTE_COLORS.notStarted,
    'priority': ROUTE_COLORS.priority,
  };
  
  return statusMap[status] || ROUTE_COLORS.inactive;
}

// Helper function to calculate delay status
export function calculateDelayStatus(
  estimatedArrival: Date,
  actualArrival?: Date
): string {
  if (!actualArrival) {
    return 'not-started';
  }
  
  const delayMinutes = Math.floor(
    (actualArrival.getTime() - estimatedArrival.getTime()) / 60000
  );
  
  if (delayMinutes <= 0) return 'on-time';
  if (delayMinutes <= 15) return 'slight-delay';
  if (delayMinutes <= 30) return 'moderate-delay';
  return 'severe-delay';
}

// Taiwan address formatter
export function formatTaiwanAddress(address: string): string {
  // Remove country name if present
  const cleanAddress = address.replace(/, Taiwan$|, 台灣$|, 臺灣$/, '');
  
  // Format common patterns
  return cleanAddress
    .replace(/Taiwan /gi, '')
    .replace(/台灣省/g, '')
    .replace(/臺灣省/g, '');
}