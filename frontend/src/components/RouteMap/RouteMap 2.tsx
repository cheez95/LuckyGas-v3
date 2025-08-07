import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Card, Spin, Alert, message } from 'antd';
import { useGoogleMaps } from './GoogleMapsProvider';
import RouteLayer from './RouteLayer';
import DriverMarker from './DriverMarker';
import StopMarker from './StopMarker';
import RouteControl from './RouteControl';
import RouteInfoPanel from './RouteInfoPanel';
import { useRouteData } from './hooks/useRouteData';
import { useDriverTracking } from './hooks/useDriverTracking';
import { useMapControls } from './hooks/useMapControls';
import { DEFAULT_MAP_CONFIG } from '../../services/maps/googleMapsConfig';
import { createRouteBounds } from '../../services/maps/routeHelpers';
import type { 
  Route, 
  Driver, 
  RouteStop, 
  MapCallbacks,
  RouteVisualizationOptions,
  RouteFilter,
  DragDropEvent 
} from '../../types/maps.types';
import './styles/RouteMap.module.css';

interface RouteMapProps {
  date?: Date;
  height?: string | number;
  showControls?: boolean;
  visualizationOptions?: Partial<RouteVisualizationOptions>;
  onRouteUpdate?: (routeId: string, updates: Partial<Route>) => void;
  onStopReorder?: (event: DragDropEvent) => void;
}

const defaultVisualizationOptions: RouteVisualizationOptions = {
  showStops: true,
  showDrivers: true,
  showLabels: true,
  showInfoWindows: true,
  clusterStops: true,
  animateDrivers: true,
  showTraffic: false,
};

const RouteMap: React.FC<RouteMapProps> = ({
  date = new Date(),
  height = '600px',
  showControls = true,
  visualizationOptions = {},
  onRouteUpdate,
  onStopReorder,
}) => {
  const { isLoaded, loadError, google } = useGoogleMaps();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [selectedStop, setSelectedStop] = useState<RouteStop | null>(null);
  const [hoveredRoute, setHoveredRoute] = useState<Route | null>(null);
  const [filter, setFilter] = useState<RouteFilter>({});
  
  const options = { ...defaultVisualizationOptions, ...visualizationOptions };
  
  // Custom hooks
  const { routes, loading: routesLoading, error: routesError, refetch } = useRouteData(date, filter);
  const { drivers, updateDriverLocation } = useDriverTracking(routes);
  const { fitBounds, panToLocation } = useMapControls(mapRef.current);
  
  // Initialize map
  useEffect(() => {
    if (!isLoaded || !mapContainerRef.current || mapRef.current) return;
    
    const map = new google.maps.Map(mapContainerRef.current, {
      ...DEFAULT_MAP_CONFIG.mapOptions,
      center: DEFAULT_MAP_CONFIG.defaultCenter,
      zoom: DEFAULT_MAP_CONFIG.defaultZoom,
    });
    
    mapRef.current = map;
    
    // Add traffic layer if enabled
    if (options.showTraffic) {
      const trafficLayer = new google.maps.TrafficLayer();
      trafficLayer.setMap(map);
    }
    
    // Add map click handler
    map.addListener('click', () => {
      setSelectedRoute(null);
      setSelectedStop(null);
    });
  }, [isLoaded, google, options.showTraffic]);
  
  // Fit bounds when routes change
  useEffect(() => {
    if (!mapRef.current || routes.length === 0) return;
    
    const allPoints = routes.flatMap(route => 
      route.stops.map(stop => stop.position)
    );
    
    const bounds = createRouteBounds(allPoints);
    if (bounds) {
      fitBounds(bounds);
    }
  }, [routes, fitBounds]);
  
  // Map callbacks
  const mapCallbacks: MapCallbacks = {
    onRouteClick: (route) => {
      setSelectedRoute(route);
      setSelectedStop(null);
    },
    onMarkerClick: (marker) => {
      const stop = routes
        .flatMap(r => r.stops)
        .find(s => s.id === marker.id);
      
      if (stop) {
        setSelectedStop(stop);
        const route = routes.find(r => r.stops.some(s => s.id === stop.id));
        if (route) {
          setSelectedRoute(route);
        }
      }
    },
    onStopDragEnd: (event) => {
      if (onStopReorder) {
        onStopReorder(event);
      }
    },
    onRouteHover: (route) => {
      setHoveredRoute(route);
    },
  };
  
  const handleFilterChange = (newFilter: RouteFilter) => {
    setFilter(newFilter);
  };
  
  const handleRouteOptimize = async () => {
    try {
      message.loading('正在優化路線...', 0);
      await refetch();
      message.destroy();
      message.success('路線優化完成');
    } catch (error) {
      message.destroy();
      message.error('路線優化失敗');
    }
  };
  
  const handleCenterOnDriver = (driverId: string) => {
    const driver = drivers.find(d => d.id === driverId);
    if (driver?.currentPosition) {
      panToLocation(driver.currentPosition);
    }
  };
  
  if (loadError) {
    return (
      <Alert
        message="地圖載入失敗"
        description={loadError.message}
        type="error"
        showIcon
      />
    );
  }
  
  if (!isLoaded) {
    return (
      <Card style={{ height }}>
        <div className="map-loading">
          <Spin size="large" tip="載入地圖中..." />
        </div>
      </Card>
    );
  }
  
  return (
    <div className="route-map-container" style={{ height }}>
      {showControls && (
        <RouteControl
          routes={routes}
          filter={filter}
          onFilterChange={handleFilterChange}
          onOptimize={handleRouteOptimize}
          onCenterDriver={handleCenterOnDriver}
        />
      )}
      
      <div className="map-wrapper">
        <div ref={mapContainerRef} className="map-container" />
        
        {mapRef.current && (
          <>
            {/* Route polylines */}
            {routes.map((route) => (
              <RouteLayer
                key={route.id}
                map={mapRef.current!}
                route={route}
                isSelected={selectedRoute?.id === route.id}
                isHovered={hoveredRoute?.id === route.id}
                options={options}
                onClick={() => mapCallbacks.onRouteClick?.(route)}
                onHover={(hovered) => mapCallbacks.onRouteHover?.(hovered ? route : null)}
              />
            ))}
            
            {/* Driver markers */}
            {options.showDrivers && drivers.map((driver) => (
              <DriverMarker
                key={driver.id}
                map={mapRef.current!}
                driver={driver}
                route={routes.find(r => r.driverId === driver.id)}
                animate={options.animateDrivers}
                onClick={() => handleCenterOnDriver(driver.id)}
              />
            ))}
            
            {/* Stop markers */}
            {options.showStops && routes.map((route) => 
              route.stops.map((stop) => (
                <StopMarker
                  key={stop.id}
                  map={mapRef.current!}
                  stop={stop}
                  route={route}
                  isSelected={selectedStop?.id === stop.id}
                  showLabel={options.showLabels}
                  showInfoWindow={options.showInfoWindows}
                  draggable={selectedRoute?.id === route.id}
                  onDragEnd={mapCallbacks.onStopDragEnd}
                  onClick={() => mapCallbacks.onMarkerClick?.({
                    id: stop.id,
                    position: stop.position,
                    type: stop.priority === 'urgent' ? 'priority' : 'customer',
                    title: stop.customerName,
                  })}
                />
              ))
            )}
          </>
        )}
        
        {selectedRoute && (
          <RouteInfoPanel
            route={selectedRoute}
            selectedStop={selectedStop}
            onClose={() => {
              setSelectedRoute(null);
              setSelectedStop(null);
            }}
            onStopClick={(stop) => setSelectedStop(stop)}
            onUpdate={onRouteUpdate}
          />
        )}
      </div>
      
      {routesError && (
        <Alert
          message="載入路線失敗"
          description={routesError}
          type="error"
          showIcon
          closable
          style={{ position: 'absolute', top: 16, right: 16, zIndex: 1000 }}
        />
      )}
    </div>
  );
};

export default RouteMap;