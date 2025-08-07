/**
 * Route helper utilities for map operations
 */

import { ROUTE_COLORS } from './googleMapsConfig';

export interface RoutePoint {
  lat: number;
  lng: number;
}

export interface RouteSegment {
  start: RoutePoint;
  end: RoutePoint;
  duration: number;
  distance: number;
}

/**
 * Decode Google's encoded polyline string
 * @param encoded The encoded polyline string
 * @returns Array of lat/lng points
 */
export function decodePolyline(encoded: string): RoutePoint[] {
  const points: RoutePoint[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte: number;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const dlat = (result & 1) ? ~(result >> 1) : (result >> 1);
    lat += dlat;

    shift = 0;
    result = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const dlng = (result & 1) ? ~(result >> 1) : (result >> 1);
    lng += dlng;

    points.push({
      lat: lat / 1e5,
      lng: lng / 1e5,
    });
  }

  return points;
}

/**
 * Calculate total distance of a route
 * @param points Array of route points
 * @returns Total distance in kilometers
 */
export function calculateRouteDistance(points: RoutePoint[]): number {
  if (points.length < 2) return 0;

  let totalDistance = 0;

  for (let i = 0; i < points.length - 1; i++) {
    totalDistance += haversineDistance(points[i], points[i + 1]);
  }

  return totalDistance;
}

/**
 * Calculate distance between two points using Haversine formula
 * @param point1 First point
 * @param point2 Second point
 * @returns Distance in kilometers
 */
export function haversineDistance(point1: RoutePoint, point2: RoutePoint): number {
  const R = 6371; // Earth's radius in kilometers
  const dLat = toRad(point2.lat - point1.lat);
  const dLng = toRad(point2.lng - point1.lng);
  
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(point1.lat)) * Math.cos(toRad(point2.lat)) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  
  return R * c;
}

function toRad(degrees: number): number {
  return degrees * (Math.PI / 180);
}

/**
 * Smooth route points for better visualization
 * @param points Original route points
 * @param factor Smoothing factor (0-1)
 * @returns Smoothed route points
 */
export function smoothRoute(points: RoutePoint[], factor: number = 0.5): RoutePoint[] {
  if (points.length < 3) return points;

  const smoothed: RoutePoint[] = [points[0]];

  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const next = points[i + 1];

    smoothed.push({
      lat: curr.lat * (1 - factor) + (prev.lat + next.lat) * factor / 2,
      lng: curr.lng * (1 - factor) + (prev.lng + next.lng) * factor / 2,
    });
  }

  smoothed.push(points[points.length - 1]);
  return smoothed;
}

/**
 * Create bounds for a route
 * @param points Route points
 * @returns LatLngBounds that contains all points
 */
export function createRouteBounds(
  points: RoutePoint[]
): google.maps.LatLngBoundsLiteral | null {
  if (points.length === 0) return null;

  let north = points[0].lat;
  let south = points[0].lat;
  let east = points[0].lng;
  let west = points[0].lng;

  points.forEach(point => {
    north = Math.max(north, point.lat);
    south = Math.min(south, point.lat);
    east = Math.max(east, point.lng);
    west = Math.min(west, point.lng);
  });

  // Add padding
  const latPadding = (north - south) * 0.1;
  const lngPadding = (east - west) * 0.1;

  return {
    north: north + latPadding,
    south: south - latPadding,
    east: east + lngPadding,
    west: west - lngPadding,
  };
}

/**
 * Animate marker movement along a path
 * @param marker Google Maps marker
 * @param path Array of points to move along
 * @param duration Total animation duration in ms
 */
export function animateMarkerAlongPath(
  marker: google.maps.Marker,
  path: RoutePoint[],
  duration: number
): Promise<void> {
  return new Promise((resolve) => {
    if (path.length === 0) {
      resolve();
      return;
    }

    let currentIndex = 0;
    const stepDuration = duration / path.length;

    const animateStep = () => {
      if (currentIndex >= path.length) {
        resolve();
        return;
      }

      marker.setPosition(path[currentIndex]);
      currentIndex++;

      setTimeout(animateStep, stepDuration);
    };

    animateStep();
  });
}

/**
 * Create route polyline options
 * @param status Route status for color
 * @param isActive Whether route is currently selected
 * @returns Polyline options
 */
export function createRoutePolylineOptions(
  status: string,
  isActive: boolean = false
): google.maps.PolylineOptions {
  const color = getRouteColor(status);
  
  return {
    strokeColor: color,
    strokeOpacity: isActive ? 1.0 : 0.7,
    strokeWeight: isActive ? 6 : 4,
    geodesic: true,
    clickable: true,
    zIndex: isActive ? 1000 : 100,
  };
}

function getRouteColor(status: string): string {
  const statusColorMap: { [key: string]: string } = {
    'completed': ROUTE_COLORS.onTime,
    'in-progress': ROUTE_COLORS.active,
    'delayed': ROUTE_COLORS.moderateDelay,
    'not-started': ROUTE_COLORS.notStarted,
    'optimized': ROUTE_COLORS.optimized,
  };
  
  return statusColorMap[status] || ROUTE_COLORS.inactive;
}

/**
 * Calculate ETA based on current position and remaining route
 * @param currentPosition Current position
 * @param remainingPoints Remaining route points
 * @param averageSpeed Average speed in km/h
 * @returns Estimated time of arrival
 */
export function calculateETA(
  currentPosition: RoutePoint,
  remainingPoints: RoutePoint[],
  averageSpeed: number = 30
): Date {
  if (remainingPoints.length === 0) {
    return new Date();
  }

  // Calculate remaining distance
  const allPoints = [currentPosition, ...remainingPoints];
  const remainingDistance = calculateRouteDistance(allPoints);

  // Calculate time in hours
  const remainingHours = remainingDistance / averageSpeed;
  
  // Convert to milliseconds and add to current time
  const eta = new Date();
  eta.setTime(eta.getTime() + remainingHours * 60 * 60 * 1000);
  
  return eta;
}

/**
 * Find nearest point on route to a given position
 * @param position Position to check
 * @param routePoints Route points
 * @returns Index of nearest point and distance
 */
export function findNearestRoutePoint(
  position: RoutePoint,
  routePoints: RoutePoint[]
): { index: number; distance: number } {
  let minDistance = Infinity;
  let nearestIndex = 0;

  routePoints.forEach((point, index) => {
    const distance = haversineDistance(position, point);
    if (distance < minDistance) {
      minDistance = distance;
      nearestIndex = index;
    }
  });

  return {
    index: nearestIndex,
    distance: minDistance,
  };
}