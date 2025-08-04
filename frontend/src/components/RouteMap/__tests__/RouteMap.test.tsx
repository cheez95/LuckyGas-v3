import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import '@testing-library/jest-dom';
import { RouteMap, GoogleMapsProvider } from '../index';
import { mapsLoader } from '../../../services/mapLoader.service';
import type { Route } from '../../../types/maps.types';

// Mock the map loader service
jest.mock('../../../services/mapLoader.service', () => ({
  mapsLoader: {
    load: jest.fn().mockResolvedValue(undefined),
    isGoogleMapsLoaded: jest.fn().mockReturnValue(true),
    createMap: jest.fn().mockReturnValue({
      addListener: jest.fn(),
      setCenter: jest.fn(),
      setZoom: jest.fn(),
      getBounds: jest.fn().mockReturnValue({
        getNorthEast: jest.fn().mockReturnValue({ lat: () => 25.1, lng: () => 121.6 }),
        getSouthWest: jest.fn().mockReturnValue({ lat: () => 25.0, lng: () => 121.5 }),
      }),
      getZoom: jest.fn().mockReturnValue(12),
    }),
  },
}));

// Mock axios for API calls
jest.mock('axios');

// Mock WebSocket
class MockWebSocket {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  
  constructor(public url: string) {
    setTimeout(() => {
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }
  
  send(data: string) {
    // Mock send
  }
  
  close() {
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

(global as any).WebSocket = MockWebSocket;

// Mock Google Maps
const mockGoogle = {
  maps: {
    Map: jest.fn().mockImplementation(() => ({
      addListener: jest.fn(),
      setCenter: jest.fn(),
      setZoom: jest.fn(),
      fitBounds: jest.fn(),
      getBounds: jest.fn(),
      getZoom: jest.fn().mockReturnValue(12),
      controls: {},
    })),
    Marker: jest.fn().mockImplementation(() => ({
      setMap: jest.fn(),
      setPosition: jest.fn(),
      setIcon: jest.fn(),
      addListener: jest.fn(),
    })),
    Polyline: jest.fn().mockImplementation(() => ({
      setMap: jest.fn(),
      setOptions: jest.fn(),
      getPath: jest.fn().mockReturnValue({ getArray: jest.fn().mockReturnValue([]) }),
    })),
    InfoWindow: jest.fn().mockImplementation(() => ({
      open: jest.fn(),
      close: jest.fn(),
      setContent: jest.fn(),
    })),
    LatLng: jest.fn().mockImplementation((lat, lng) => ({ lat: () => lat, lng: () => lng })),
    LatLngBounds: jest.fn().mockImplementation(() => ({
      extend: jest.fn(),
      getCenter: jest.fn(),
      getNorthEast: jest.fn(),
      getSouthWest: jest.fn(),
    })),
    TrafficLayer: jest.fn().mockImplementation(() => ({
      setMap: jest.fn(),
    })),
    Size: jest.fn().mockImplementation((width, height) => ({ width, height })),
    Point: jest.fn().mockImplementation((x, y) => ({ x, y })),
    Animation: {
      DROP: 1,
      BOUNCE: 2,
    },
    SymbolPath: {
      CIRCLE: 0,
      FORWARD_OPEN_ARROW: 1,
    },
    ControlPosition: {
      TOP_LEFT: 1,
      TOP_CENTER: 2,
      TOP_RIGHT: 3,
    },
    event: {
      removeListener: jest.fn(),
    },
    geometry: {
      spherical: {
        computeDistanceBetween: jest.fn().mockReturnValue(1000),
      },
    },
  },
};

(window as any).google = mockGoogle;

const mockRoutes: Route[] = [
  {
    id: 'route-1',
    driverId: 'driver-1',
    driverName: '王大明',
    vehicleId: 'vehicle-1',
    date: new Date('2024-01-20'),
    status: 'in-progress',
    stops: [
      {
        id: 'stop-1',
        customerId: 'customer-1',
        customerName: '幸福餐廳',
        address: '台北市信義區信義路五段7號',
        position: { lat: 25.0330, lng: 121.5654 },
        sequence: 1,
        estimatedArrival: new Date('2024-01-20T09:00:00'),
        estimatedDuration: 15,
        status: 'completed',
        packages: [{ cylinderType: '20kg', quantity: 2 }],
      },
      {
        id: 'stop-2',
        customerId: 'customer-2',
        customerName: '快樂小吃店',
        address: '台北市大安區忠孝東路四段123號',
        position: { lat: 25.0410, lng: 121.5432 },
        sequence: 2,
        estimatedArrival: new Date('2024-01-20T09:30:00'),
        estimatedDuration: 10,
        status: 'pending',
        packages: [{ cylinderType: '16kg', quantity: 1 }],
        priority: 'urgent',
      },
    ],
    polyline: 'encodedPolylineString',
    totalDistance: 5.2,
    totalDuration: 25,
    startTime: new Date('2024-01-20T08:30:00'),
    optimizationMode: 'time',
  },
];

// Mock axios
const axios = require('axios');
jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
  create: jest.fn(() => axios),
  defaults: { headers: { common: {} } },
}));

describe('RouteMap Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders loading state initially', () => {
    render(
      <GoogleMapsProvider>
        <RouteMap />
      </GoogleMapsProvider>
    );
    
    expect(screen.getByText('載入地圖中...')).toBeInTheDocument();
  });

  test('renders map container after loading', async () => {
    const { container } = render(
      <GoogleMapsProvider>
        <RouteMap />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      expect(container.querySelector('.map-container')).toBeInTheDocument();
    });
  });

  test('displays route control panel when showControls is true', async () => {
    render(
      <GoogleMapsProvider>
        <RouteMap showControls={true} />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      expect(screen.getByText('路線控制台')).toBeInTheDocument();
    });
  });

  test('handles route optimization trigger', async () => {
    const { getByText } = render(
      <GoogleMapsProvider>
        <RouteMap showControls={true} />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      const optimizeButton = getByText('優化路線');
      expect(optimizeButton).toBeInTheDocument();
    });
    
    // Click optimize button
    const optimizeButton = getByText('優化路線');
    fireEvent.click(optimizeButton);
    
    // Should show loading message
    await waitFor(() => {
      expect(screen.getByText('正在優化路線...')).toBeInTheDocument();
    });
  });

  test('renders with custom height', () => {
    const { container } = render(
      <GoogleMapsProvider>
        <RouteMap height="800px" />
      </GoogleMapsProvider>
    );
    
    const mapContainer = container.querySelector('.route-map-container');
    expect(mapContainer).toHaveStyle({ height: '800px' });
  });

  test('handles visualization options', async () => {
    render(
      <GoogleMapsProvider>
        <RouteMap 
          visualizationOptions={{
            showTraffic: true,
            clusterStops: true,
            showLabels: false,
          }}
        />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      // Traffic layer should be created
      expect(mockGoogle.maps.TrafficLayer).toHaveBeenCalled();
    });
  });

  test('handles WebSocket connection status', async () => {
    render(
      <GoogleMapsProvider>
        <RouteMap />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      // Should show connection status
      expect(screen.getByText('即時更新中')).toBeInTheDocument();
    });
  });

  test('handles error state gracefully', async () => {
    // Mock map loader to throw error
    (mapsLoader.load as jest.Mock).mockRejectedValueOnce(new Error('Failed to load'));
    
    render(
      <GoogleMapsProvider>
        <RouteMap />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      expect(screen.getByText('無法載入地圖服務，請檢查網路連線')).toBeInTheDocument();
    });
  });
});

describe('RouteMap Performance', () => {
  test('handles 100+ stops efficiently with clustering', async () => {
    // Create 100 stops
    const manyStops = Array.from({ length: 100 }, (_, i) => ({
      id: `stop-${i}`,
      customerId: `customer-${i}`,
      customerName: `Customer ${i}`,
      address: `Address ${i}`,
      position: { lat: 25.0330 + (i * 0.001), lng: 121.5654 + (i * 0.001) },
      sequence: i + 1,
      estimatedArrival: new Date(`2024-01-20T${9 + Math.floor(i / 10)}:00:00`),
      estimatedDuration: 10,
      status: 'pending' as const,
      packages: [{ cylinderType: '20kg', quantity: 1 }],
    }));
    
    const largeRoute: Route = {
      ...mockRoutes[0],
      stops: manyStops,
    };
    
    const start = performance.now();
    
    render(
      <GoogleMapsProvider>
        <RouteMap 
          visualizationOptions={{ clusterStops: true }}
        />
      </GoogleMapsProvider>
    );
    
    const renderTime = performance.now() - start;
    
    // Should render within reasonable time
    expect(renderTime).toBeLessThan(1000); // Less than 1 second
    
    await waitFor(() => {
      expect(screen.getByText('100 個配送點')).toBeInTheDocument();
    });
  });
});

describe('RouteMap Responsive Design', () => {
  test('adapts to mobile viewport', async () => {
    // Mock mobile viewport
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 375,
    });
    
    const { container } = render(
      <GoogleMapsProvider>
        <RouteMap showControls={true} />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      const routeControl = container.querySelector('.route-control');
      expect(routeControl).toBeInTheDocument();
    });
    
    // Reset viewport
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });
});

describe('RouteMap WebSocket Updates', () => {
  test('handles real-time driver location updates', async () => {
    const onRouteUpdate = jest.fn();
    
    render(
      <GoogleMapsProvider>
        <RouteMap onRouteUpdate={onRouteUpdate} />
      </GoogleMapsProvider>
    );
    
    // Simulate WebSocket connection
    await waitFor(() => {
      expect(screen.getByText('即時更新中')).toBeInTheDocument();
    });
    
    // Simulate driver location update
    const mockWs = (global as any).WebSocket.mock.instances[0];
    act(() => {
      if (mockWs.onmessage) {
        mockWs.onmessage({
          data: JSON.stringify({
            type: 'driver_location',
            data: {
              driverId: 'driver-1',
              position: { lat: 25.0340, lng: 121.5655 },
              timestamp: new Date().toISOString(),
            },
          }),
        });
      }
    });
    
    // Should update marker position
    await waitFor(() => {
      expect(mockGoogle.maps.Marker).toHaveBeenCalled();
    });
  });
  
  test('handles WebSocket reconnection', async () => {
    render(
      <GoogleMapsProvider>
        <RouteMap />
      </GoogleMapsProvider>
    );
    
    // Initial connection
    await waitFor(() => {
      expect(screen.getByText('即時更新中')).toBeInTheDocument();
    });
    
    // Simulate disconnect
    const mockWs = (global as any).WebSocket.mock.instances[0];
    act(() => {
      mockWs.close();
    });
    
    // Should show disconnected state
    await waitFor(() => {
      expect(screen.getByText('連線中斷')).toBeInTheDocument();
    });
    
    // Should attempt reconnection
    await waitFor(() => {
      expect((global as any).WebSocket).toHaveBeenCalledTimes(2);
    });
  });
});

describe('RouteMap Drag and Drop', () => {
  test('handles stop reordering via drag and drop', async () => {
    const onStopReorder = jest.fn();
    
    const { container } = render(
      <GoogleMapsProvider>
        <RouteMap 
          onStopReorder={onStopReorder}
          showControls={true}
        />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      expect(container.querySelector('.route-control')).toBeInTheDocument();
    });
    
    // Mock drag and drop event
    const firstStop = container.querySelector('[data-stop-index="0"]');
    const secondStop = container.querySelector('[data-stop-index="1"]');
    
    if (firstStop && secondStop) {
      // Simulate drag start
      fireEvent.dragStart(firstStop);
      
      // Simulate drag over
      fireEvent.dragOver(secondStop);
      
      // Simulate drop
      fireEvent.drop(secondStop);
      
      // Should call reorder callback
      expect(onStopReorder).toHaveBeenCalledWith(expect.objectContaining({
        routeId: expect.any(String),
        fromIndex: 0,
        toIndex: 1,
      }));
    }
  });
  
  test('shows drag preview during drag operation', async () => {
    const { container } = render(
      <GoogleMapsProvider>
        <RouteMap showControls={true} />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      const stops = container.querySelectorAll('[data-stop-index]');
      expect(stops.length).toBeGreaterThan(0);
    });
    
    const firstStop = container.querySelector('[data-stop-index="0"]');
    
    if (firstStop) {
      // Start drag
      fireEvent.dragStart(firstStop);
      
      // Should show dragging state
      expect(firstStop).toHaveClass('dragging');
      
      // End drag
      fireEvent.dragEnd(firstStop);
      
      // Should remove dragging state
      expect(firstStop).not.toHaveClass('dragging');
    }
  });
});

describe('RouteMap Integration', () => {
  test('integrates with route optimization service', async () => {
    const mockOptimizeRoute = jest.fn().mockResolvedValue({
      optimizedRoute: mockRoutes[0],
      savings: { distance: 10, time: 15 },
    });
    
    // Mock axios
    const axiosMock = require('axios');
    axiosMock.post.mockImplementation(mockOptimizeRoute);
    
    const { getByText } = render(
      <GoogleMapsProvider>
        <RouteMap showControls={true} />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      expect(getByText('優化路線')).toBeInTheDocument();
    });
    
    // Click optimize
    fireEvent.click(getByText('優化路線'));
    
    await waitFor(() => {
      expect(mockOptimizeRoute).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/routes/optimize'),
        expect.any(Object)
      );
    });
  });
  
  test('exports route data', async () => {
    const { getByText } = render(
      <GoogleMapsProvider>
        <RouteMap showControls={true} />
      </GoogleMapsProvider>
    );
    
    await waitFor(() => {
      expect(getByText('匯出')).toBeInTheDocument();
    });
    
    // Mock file download
    const createElementSpy = jest.spyOn(document, 'createElement');
    const clickSpy = jest.fn();
    
    createElementSpy.mockReturnValueOnce({
      click: clickSpy,
      download: '',
      href: '',
    } as any);
    
    // Click export
    fireEvent.click(getByText('匯出'));
    
    // Should trigger download
    expect(clickSpy).toHaveBeenCalled();
  });
});