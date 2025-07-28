// Service Worker for Lucky Gas PWA with Enhanced Offline Support
const CACHE_NAME = 'lucky-gas-v2';
const OFFLINE_URL = '/offline.html';
const SYNC_TAG = 'luckygas-sync';

// Files to cache for offline functionality
const urlsToCache = [
  '/',
  '/driver',
  '/driver/routes',
  '/driver/deliveries',
  '/offline.html',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

// API endpoints that support offline mode
const OFFLINE_API_PATTERNS = [
  /\/api\/v1\/routes\/driver/,
  /\/api\/v1\/orders\/\d+$/,
  /\/api\/v1\/customers\/\d+$/,
  /\/api\/v1\/stops\/\d+$/,
];

// Install event - cache resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Service Worker: Caching files for offline use');
      return cache.addAll(urlsToCache.map(url => 
        new Request(url, { cache: 'no-cache' })
      ));
    })
  );
  // Force the service worker to become active
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  // Take control of all pages immediately
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
  
  // Skip cross-origin requests except for allowed domains
  if (!request.url.startsWith(self.location.origin)) {
    return;
  }

  // Handle API requests with offline support
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  // Cache first strategy for static assets
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        // Return cached version and update in background
        fetchAndCache(request);
        return cachedResponse;
      }
      
      return fetchAndCache(request).catch(() => {
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
          return caches.match(OFFLINE_URL);
        }
      });
    })
  );
});

// Handle API requests with offline support
async function handleApiRequest(request) {
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
        console.log('Service Worker: Serving API response from cache:', request.url);
        // Add offline header to response
        const headers = new Headers(cachedResponse.headers);
        headers.set('X-Offline-Mode', 'true');
        return new Response(cachedResponse.body, {
          status: cachedResponse.status,
          statusText: cachedResponse.statusText,
          headers: headers
        });
      }
    }
    
    // Return offline response for supported endpoints
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
async function fetchAndCache(request) {
  const response = await fetch(request);
  
  // Only cache successful responses
  if (response.ok && request.method === 'GET') {
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
  }
  
  return response;
}

// Check if request supports offline mode
function isOfflineSupported(request) {
  const url = new URL(request.url);
  return OFFLINE_API_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// Create offline response
function createOfflineResponse(request) {
  const url = new URL(request.url);
  
  // Return empty data for driver route endpoint
  if (url.pathname.includes('/routes/driver')) {
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

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('Service Worker: Background sync triggered:', event.tag);
  
  if (event.tag === 'sync-deliveries' || event.tag === SYNC_TAG) {
    event.waitUntil(performBackgroundSync());
  }
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'luckygas-periodic-sync') {
    event.waitUntil(performBackgroundSync());
  }
});

// Perform background sync
async function performBackgroundSync() {
  try {
    // Send message to all clients to trigger sync
    const clients = await self.clients.matchAll();
    
    for (const client of clients) {
      client.postMessage({
        type: 'BACKGROUND_SYNC',
        timestamp: Date.now(),
      });
    }
    
    // Also sync any cached POST requests
    await syncCachedRequests();
    
    console.log('Service Worker: Background sync completed');
  } catch (error) {
    console.error('Service Worker: Background sync failed:', error);
    throw error; // Retry later
  }
}

// Push notification handling
self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : '您有新的配送任務',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'view',
        title: '查看',
        icon: '/icons/checkmark.png'
      },
      {
        action: 'close',
        title: '關閉',
        icon: '/icons/xmark.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('幸福氣配送通知', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/driver/routes')
    );
  }
});

// Helper function to sync cached requests
async function syncCachedRequests() {
  try {
    const cache = await caches.open(CACHE_NAME);
    const requests = await cache.keys();
    
    // Find all POST/PUT requests that need syncing
    const syncRequests = requests.filter(req => 
      (req.method === 'POST' || req.method === 'PUT') &&
      req.url.includes('/api/v1/')
    );

    console.log(`Service Worker: Found ${syncRequests.length} requests to sync`);

    for (const request of syncRequests) {
      try {
        const cachedResponse = await cache.match(request);
        if (cachedResponse) {
          // Get the cached request body
          const body = await cachedResponse.text();
          
          // Retry the request
          const response = await fetch(request.url, {
            method: request.method,
            headers: request.headers,
            body: body,
          });
          
          if (response.ok) {
            // Remove from cache if successful
            await cache.delete(request);
            console.log(`Service Worker: Successfully synced ${request.url}`);
          }
        }
      } catch (error) {
        console.error('Service Worker: Failed to sync request:', error);
      }
    }
  } catch (error) {
    console.error('Service Worker: Sync failed:', error);
  }
}

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