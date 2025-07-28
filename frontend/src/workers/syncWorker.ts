/// <reference lib="webworker" />

// Service Worker for offline sync and caching
declare const self: ServiceWorkerGlobalScope;

const CACHE_NAME = 'luckygas-v1';
const SYNC_TAG = 'luckygas-sync';

// URLs to cache for offline use
const STATIC_CACHE_URLS = [
  '/',
  '/driver',
  '/manifest.json',
  '/favicon.ico',
];

// API endpoints that should work offline
const OFFLINE_API_PATTERNS = [
  /\/api\/v1\/routes\/driver/,
  /\/api\/v1\/orders\/\d+$/,
  /\/api\/v1\/customers\/\d+$/,
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Caching static assets');
      return cache.addAll(STATIC_CACHE_URLS);
    })
  );
  
  // Skip waiting to activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => cacheName !== CACHE_NAME)
          .map((cacheName) => caches.delete(cacheName))
      );
    })
  );
  
  // Take control of all clients immediately
  self.clients.claim();
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-HTTP(S) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }
  
  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }
  
  // Handle static assets
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        // Return cached version and update in background
        fetchAndCache(request);
        return cachedResponse;
      }
      
      return fetchAndCache(request);
    })
  );
});

// Handle API requests with offline support
async function handleApiRequest(request: Request): Promise<Response> {
  try {
    // Try network first
    const response = await fetch(request.clone());
    
    // Cache successful GET requests
    if (request.method === 'GET' && response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    // Network failed, check if we have a cached version
    if (request.method === 'GET') {
      const cachedResponse = await caches.match(request);
      if (cachedResponse) {
        console.log('Serving API response from cache:', request.url);
        return cachedResponse;
      }
    }
    
    // Return offline response for certain endpoints
    if (isOfflineSupported(request)) {
      return createOfflineResponse(request);
    }
    
    // Return error response
    return new Response(
      JSON.stringify({ error: 'Network error', offline: true }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// Fetch and cache helper
async function fetchAndCache(request: Request): Promise<Response> {
  try {
    const response = await fetch(request);
    
    // Only cache successful responses
    if (response.ok && request.method === 'GET') {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    // Try to return cached version
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      const cache = await caches.open(CACHE_NAME);
      const offlinePage = await cache.match('/');
      if (offlinePage) {
        return offlinePage;
      }
    }
    
    throw error;
  }
}

// Check if request supports offline mode
function isOfflineSupported(request: Request): boolean {
  const url = new URL(request.url);
  return OFFLINE_API_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// Create offline response
function createOfflineResponse(request: Request): Response {
  const url = new URL(request.url);
  
  // Return empty data for list endpoints
  if (url.pathname.includes('/driver')) {
    return new Response(
      JSON.stringify({
        data: {
          id: 0,
          route_number: 'OFFLINE',
          status: 'offline',
          stops: [],
          total_stops: 0,
          completed_stops: 0,
        },
        offline: true,
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
  
  return new Response(
    JSON.stringify({ data: null, offline: true }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }
  );
}

// Background sync event
self.addEventListener('sync', (event) => {
  console.log('Background sync triggered:', event.tag);
  
  if (event.tag === SYNC_TAG) {
    event.waitUntil(performBackgroundSync());
  }
});

// Perform background sync
async function performBackgroundSync(): Promise<void> {
  try {
    // Send message to all clients to trigger sync
    const clients = await self.clients.matchAll();
    
    for (const client of clients) {
      client.postMessage({
        type: 'BACKGROUND_SYNC',
        timestamp: Date.now(),
      });
    }
    
    console.log('Background sync completed');
  } catch (error) {
    console.error('Background sync failed:', error);
    throw error; // Retry later
  }
}

// Periodic background sync (if supported)
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'luckygas-periodic-sync') {
    event.waitUntil(performBackgroundSync());
  }
});

// Message event - handle messages from clients
self.addEventListener('message', (event) => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'TRIGGER_SYNC':
      // Register sync event
      self.registration.sync.register(SYNC_TAG).catch((error) => {
        console.error('Failed to register sync:', error);
      });
      break;
      
    case 'CACHE_ROUTE':
      // Pre-cache route data
      if (data && data.url) {
        caches.open(CACHE_NAME).then((cache) => {
          cache.add(data.url);
        });
      }
      break;
      
    case 'CLEAR_CACHE':
      // Clear all caches
      caches.keys().then((cacheNames) => {
        Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName)));
      });
      break;
  }
});

// Push event - handle push notifications
self.addEventListener('push', (event) => {
  if (!event.data) return;
  
  const payload = event.data.json();
  const { title, body, tag, data } = payload;
  
  const options: NotificationOptions = {
    body,
    tag,
    data,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [200, 100, 200],
    requireInteraction: tag === 'route-assignment',
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  const { data } = event.notification;
  let url = '/';
  
  if (data) {
    switch (data.type) {
      case 'route-assignment':
        url = '/driver';
        break;
      case 'delivery-reminder':
        url = `/driver/delivery/${data.deliveryId}`;
        break;
    }
  }
  
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clientList) => {
      // Check if there's already a window open
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      
      // Open new window if needed
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    })
  );
});

// Export for TypeScript
export {};