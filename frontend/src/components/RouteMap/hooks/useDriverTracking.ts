import { useState, useEffect, useCallback } from 'react';
import type { Driver, Route, DriverLocationMessage } from '../../../types/maps.types';

interface UseDriverTrackingReturn {
  drivers: Driver[];
  updateDriverLocation: (driverId: string, position: { lat: number; lng: number }) => void;
}

export function useDriverTracking(routes: Route[]): UseDriverTrackingReturn {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  
  // Initialize drivers from routes
  useEffect(() => {
    const driversMap = new Map<string, Driver>();
    
    routes.forEach(route => {
      if (!driversMap.has(route.driverId)) {
        driversMap.set(route.driverId, {
          id: route.driverId,
          name: route.driverName,
          vehicleId: route.vehicleId,
          status: route.status === 'in-progress' ? 'on-route' : 'available',
          assignedRouteId: route.id,
        });
      }
    });
    
    setDrivers(Array.from(driversMap.values()));
  }, [routes]);
  
  // Subscribe to driver location updates
  useEffect(() => {
    const ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/ws/drivers`);
    
    ws.onmessage = (event) => {
      try {
        const message: DriverLocationMessage = JSON.parse(event.data);
        
        if (message.type === 'driver-location') {
          setDrivers(prevDrivers => 
            prevDrivers.map(driver => 
              driver.id === message.driverId
                ? {
                    ...driver,
                    currentPosition: message.position,
                    lastUpdate: message.timestamp,
                  }
                : driver
            )
          );
        }
      } catch (err) {
        console.error('WebSocket message error:', err);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return () => {
      ws.close();
    };
  }, []);
  
  const updateDriverLocation = useCallback((
    driverId: string, 
    position: { lat: number; lng: number }
  ) => {
    setDrivers(prevDrivers => 
      prevDrivers.map(driver => 
        driver.id === driverId
          ? {
              ...driver,
              currentPosition: position,
              lastUpdate: new Date(),
            }
          : driver
      )
    );
  }, []);
  
  return {
    drivers,
    updateDriverLocation,
  };
}