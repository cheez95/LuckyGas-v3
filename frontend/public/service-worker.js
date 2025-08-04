// Service Worker for Lucky Gas PWA with Enhanced Offline Support
const CACHE_NAME = 'lucky-gas-v3';
const OFFLINE_URL = '/offline.html';
const SYNC_TAG = 'luckygas-sync';
const PERIODIC_SYNC_TAG = 'luckygas-periodic-sync';

// Cache configuration
const CACHE_CONFIG = {
  // Core app shell files
  STATIC_CACHE: 'lucky-gas-static-v3',
  // API responses
  API_CACHE: 'lucky-gas-api-v3',
  // Images and media
  MEDIA_CACHE: 'lucky-gas-media-v3',
  // Runtime data
  RUNTIME_CACHE: 'lucky-gas-runtime-v3',
};

// Files to cache for offline functionality
const urlsToCache = [
  '/',
  '/driver',
  '/driver/routes',
  '/driver/deliveries',
  '/driver/navigation',
  '/driver/scan',
  '/offline.html',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/icons/icon-72x72.png',
  '/icons/icon-96x96.png',
  '/icons/icon-128x128.png',
  '/icons/icon-144x144.png',
  '/icons/icon-152x152.png',
  '/icons/icon-384x384.png',
];

// API endpoints that support offline mode
const OFFLINE_API_PATTERNS = [
  /\/api\/v1\/routes\/driver/,
  /\/api\/v1\/routes\/\d+$/,
  /\/api\/v1\/routes\/\d+\/stops/,
  /\/api\/v1\/orders\/\d+$/,
  /\/api\/v1\/customers\/\d+$/,
  /\/api\/v1\/stops\/\d+$/,
  /\/api\/v1\/products$/,
  /\/api\/v1\/driver\/profile$/,
  /\/api\/v1\/driver\/stats$/,
];

// Network timeout configuration (ms)
const NETWORK_TIMEOUT = 5000;

// Cache expiration times (ms)
const CACHE_EXPIRATION = {
  API: 5 * 60 * 1000, // 5 minutes for API responses
  STATIC: 7 * 24 * 60 * 60 * 1000, // 7 days for static assets
  MEDIA: 30 * 24 * 60 * 60 * 1000, // 30 days for media
};

// Install event - cache resources
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing version', CACHE_NAME);
  
  event.waitUntil(
    Promise.all([
      // Cache static assets
      caches.open(CACHE_CONFIG.STATIC_CACHE).then((cache) => {
        console.log('Service Worker: Caching static files');
        return cache.addAll(urlsToCache.map(url => 
          new Request(url, { cache: 'no-cache' })
        ));
      }),
      // Pre-cache important API endpoints
      caches.open(CACHE_CONFIG.API_CACHE).then((cache) => {
        console.log('Service Worker: Pre-caching API endpoints');
        // Pre-cache driver profile and products
        return Promise.all([
          fetch('/api/v1/driver/profile').then(response => {
            if (response.ok) cache.put('/api/v1/driver/profile', response);
          }).catch(() => {}),
          fetch('/api/v1/products').then(response => {
            if (response.ok) cache.put('/api/v1/products', response);
          }).catch(() => {}),
        ]);
      }),
    ])
  );
  
  // Force the service worker to become active
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating version', CACHE_NAME);
  
  const currentCaches = Object.values(CACHE_CONFIG);
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (!currentCaches.includes(cacheName)) {
              console.log('Service Worker: Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Clean expired entries from current caches
      cleanExpiredCacheEntries(),
    ])
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
  if (!request.url.startsWith(self.location.origin) && 
      !url.hostname.includes('googleapis.com') &&
      !url.hostname.includes('gstatic.com')) {
    return;
  }

  // Handle different request types with appropriate strategies
  if (url.pathname.startsWith('/api/')) {
    // Network first with cache fallback for API requests
    event.respondWith(handleApiRequest(request));
  } else if (request.destination === 'image' || url.pathname.match(/\.(jpg|jpeg|png|gif|svg|webp)$/i)) {
    // Cache first for images
    event.respondWith(handleImageRequest(request));
  } else if (url.pathname.match(/\.(js|css)$/i)) {
    // Stale while revalidate for scripts and styles
    event.respondWith(handleStaticAsset(request));
  } else {
    // Network first with offline fallback for navigation
    event.respondWith(handleNavigationRequest(request));
  }
});

// Handle API requests with network timeout and offline support
async function handleApiRequest(request) {
  const cache = await caches.open(CACHE_CONFIG.API_CACHE);
  
  // For POST/PUT requests, queue for sync if offline
  if (request.method !== 'GET') {
    try {
      const response = await fetchWithTimeout(request.clone(), NETWORK_TIMEOUT);
      return response;
    } catch (error) {
      // Queue for background sync
      await queueRequestForSync(request);
      return new Response(
        JSON.stringify({ 
          success: true, 
          offline: true, 
          message: '資料已儲存，將在連線後同步' 
        }),
        {
          status: 202,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  }
  
  // GET requests - try network with timeout, fallback to cache
  try {
    const response = await fetchWithTimeout(request.clone(), NETWORK_TIMEOUT);
    
    if (response.ok) {
      // Clone response before caching
      const responseToCache = response.clone();
      // Add timestamp to cached response
      const headers = new Headers(responseToCache.headers);
      headers.set('X-Cached-At', new Date().toISOString());
      
      const timestampedResponse = new Response(responseToCache.body, {
        status: responseToCache.status,
        statusText: responseToCache.statusText,
        headers: headers,
      });
      
      cache.put(request, timestampedResponse);
    }
    
    return response;
  } catch (error) {
    // Network failed, try cache
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      // Check cache age
      const cachedAt = cachedResponse.headers.get('X-Cached-At');
      const cacheAge = cachedAt ? Date.now() - new Date(cachedAt).getTime() : 0;
      
      // Add offline headers
      const headers = new Headers(cachedResponse.headers);
      headers.set('X-Offline-Mode', 'true');
      headers.set('X-Cache-Age', Math.floor(cacheAge / 1000).toString());
      
      console.log('Service Worker: Serving cached API response:', request.url);
      
      return new Response(cachedResponse.body, {
        status: cachedResponse.status,
        statusText: cachedResponse.statusText,
        headers: headers,
      });
    }
    
    // No cache available, return offline response
    if (isOfflineSupported(request)) {
      return createOfflineResponse(request);
    }
    
    // Return error response
    return new Response(
      JSON.stringify({ 
        error: '網路連線失敗', 
        offline: true,
        message: '無法連接伺服器，請檢查網路連線'
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// Handle image requests - cache first strategy
async function handleImageRequest(request) {
  const cache = await caches.open(CACHE_CONFIG.MEDIA_CACHE);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    // Update cache in background
    fetchAndUpdateCache(request, CACHE_CONFIG.MEDIA_CACHE);
    return cachedResponse;
  }
  
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Return placeholder image if available
    const placeholderResponse = await cache.match('/images/placeholder.png');
    return placeholderResponse || new Response('', { status: 404 });
  }
}

// Handle static assets - stale while revalidate
async function handleStaticAsset(request) {
  const cache = await caches.open(CACHE_CONFIG.STATIC_CACHE);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    // Return cached version immediately
    fetchAndUpdateCache(request, CACHE_CONFIG.STATIC_CACHE);
    return cachedResponse;
  }
  
  // No cache, fetch from network
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    return new Response('', { status: 503 });
  }
}

// Handle navigation requests
async function handleNavigationRequest(request) {
  try {
    // Try network first with timeout
    const response = await fetchWithTimeout(request, NETWORK_TIMEOUT);
    
    if (response.ok) {
      const cache = await caches.open(CACHE_CONFIG.RUNTIME_CACHE);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    // Try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline page for navigation
    if (request.mode === 'navigate') {
      return caches.match(OFFLINE_URL);
    }
    
    return new Response('', { status: 503 });
  }
}

// Fetch with timeout helper
function fetchWithTimeout(request, timeout) {
  return Promise.race([
    fetch(request),
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Request timeout')), timeout)
    ),
  ]);
}

// Fetch and update cache in background
async function fetchAndUpdateCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response);
    }
  } catch (error) {
    // Silent fail - we already returned cached version
  }
}

// Check if request supports offline mode
function isOfflineSupported(request) {
  const url = new URL(request.url);
  return OFFLINE_API_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// Create offline response with more comprehensive data
function createOfflineResponse(request) {
  const url = new URL(request.url);
  
  // Driver routes endpoint
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
          assigned_driver: {
            id: 0,
            name: '離線模式',
            phone: '',
          },
        },
        offline: true,
        message: '目前為離線模式，顯示快取資料',
      }),
      {
        status: 200,
        headers: { 
          'Content-Type': 'application/json',
          'X-Offline-Mode': 'true',
        },
      }
    );
  }
  
  // Products endpoint
  if (url.pathname.includes('/products')) {
    return new Response(
      JSON.stringify({
        data: [
          { id: 1, name: '20公斤桶裝瓦斯', size_kg: 20, price: 800 },
          { id: 2, name: '16公斤桶裝瓦斯', size_kg: 16, price: 640 },
          { id: 3, name: '10公斤桶裝瓦斯', size_kg: 10, price: 400 },
        ],
        offline: true,
        message: '顯示預設產品清單',
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
  
  // Driver profile endpoint
  if (url.pathname.includes('/driver/profile')) {
    return new Response(
      JSON.stringify({
        data: {
          id: 0,
          name: '司機',
          phone: '',
          employee_id: 'OFFLINE',
          status: 'offline',
        },
        offline: true,
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
  
  // Default offline response
  return new Response(
    JSON.stringify({ 
      data: null, 
      offline: true,
      message: '離線模式 - 資料暫時無法取得',
    }),
    {
      status: 200,
      headers: { 
        'Content-Type': 'application/json',
        'X-Offline-Mode': 'true',
      },
    }
  );
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('Service Worker: Background sync triggered:', event.tag);
  
  if (event.tag === SYNC_TAG || event.tag.startsWith('sync-')) {
    event.waitUntil(performBackgroundSync(event.tag));
  }
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', (event) => {
  console.log('Service Worker: Periodic sync triggered:', event.tag);
  
  if (event.tag === PERIODIC_SYNC_TAG) {
    event.waitUntil(
      Promise.all([
        performBackgroundSync(),
        cleanExpiredCacheEntries(),
        syncOfflineData(),
      ])
    );
  }
});

// Perform background sync
async function performBackgroundSync(tag) {
  console.log('Service Worker: Starting background sync for tag:', tag);
  
  try {
    // Get all clients
    const clients = await self.clients.matchAll({ includeUncontrolled: true });
    
    // Notify clients about sync
    const syncPromises = clients.map(client => 
      client.postMessage({
        type: 'BACKGROUND_SYNC',
        tag: tag,
        timestamp: Date.now(),
      })
    );
    
    await Promise.all(syncPromises);
    
    // Sync queued requests
    await syncQueuedRequests();
    
    // Update sync status
    await updateSyncStatus({
      lastSync: Date.now(),
      success: true,
    });
    
    console.log('Service Worker: Background sync completed successfully');
  } catch (error) {
    console.error('Service Worker: Background sync failed:', error);
    
    await updateSyncStatus({
      lastSync: Date.now(),
      success: false,
      error: error.message,
    });
    
    // Re-throw to trigger retry
    throw error;
  }
}

// Sync offline data from IndexedDB
async function syncOfflineData() {
  try {
    // Open IndexedDB
    const db = await openSyncDatabase();
    
    if (!db) return;
    
    // Get all pending sync items
    const tx = db.transaction(['syncQueue'], 'readonly');
    const store = tx.objectStore('syncQueue');
    const items = await store.getAll();
    
    console.log(`Service Worker: Found ${items.length} items to sync`);
    
    // Process each item
    for (const item of items) {
      try {
        await processSyncItem(item);
        // Remove from queue after successful sync
        await removeSyncItem(db, item.id);
      } catch (error) {
        console.error(`Failed to sync item ${item.id}:`, error);
        // Update retry count
        await updateSyncItem(db, item.id, {
          retries: (item.retries || 0) + 1,
          lastError: error.message,
        });
      }
    }
  } catch (error) {
    console.error('Service Worker: Failed to sync offline data:', error);
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

// Queue request for background sync
async function queueRequestForSync(request) {
  try {
    // Clone request to read body
    const clonedRequest = request.clone();
    const body = await clonedRequest.text();
    
    // Store in IndexedDB for sync
    const db = await openSyncDatabase();
    if (!db) return;
    
    const tx = db.transaction(['syncQueue'], 'readwrite');
    const store = tx.objectStore('syncQueue');
    
    await store.add({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      body: body,
      timestamp: Date.now(),
      retries: 0,
    });
    
    // Register for sync
    await self.registration.sync.register(SYNC_TAG);
  } catch (error) {
    console.error('Service Worker: Failed to queue request:', error);
  }
}

// Sync queued requests
async function syncQueuedRequests() {
  const cache = await caches.open('sync-queue');
  const requests = await cache.keys();
  
  console.log(`Service Worker: Processing ${requests.length} queued requests`);
  
  const results = [];
  
  for (const request of requests) {
    try {
      const cachedResponse = await cache.match(request);
      if (!cachedResponse) continue;
      
      // Get request data
      const requestData = await cachedResponse.json();
      
      // Retry the request
      const response = await fetch(requestData.url, {
        method: requestData.method,
        headers: requestData.headers,
        body: requestData.body,
      });
      
      if (response.ok) {
        // Remove from queue
        await cache.delete(request);
        results.push({ url: requestData.url, success: true });
      } else {
        results.push({ 
          url: requestData.url, 
          success: false, 
          status: response.status 
        });
      }
    } catch (error) {
      console.error('Service Worker: Failed to sync request:', error);
      results.push({ 
        url: request.url, 
        success: false, 
        error: error.message 
      });
    }
  }
  
  // Notify clients about sync results
  const clients = await self.clients.matchAll();
  for (const client of clients) {
    client.postMessage({
      type: 'SYNC_COMPLETE',
      results: results,
      timestamp: Date.now(),
    });
  }
  
  return results;
}

// Clean expired cache entries
async function cleanExpiredCacheEntries() {
  const cacheNames = Object.values(CACHE_CONFIG);
  
  for (const cacheName of cacheNames) {
    try {
      const cache = await caches.open(cacheName);
      const requests = await cache.keys();
      
      for (const request of requests) {
        const response = await cache.match(request);
        if (!response) continue;
        
        // Check cache age
        const cachedAt = response.headers.get('X-Cached-At');
        if (!cachedAt) continue;
        
        const age = Date.now() - new Date(cachedAt).getTime();
        const maxAge = getMaxAgeForCache(cacheName);
        
        if (age > maxAge) {
          await cache.delete(request);
          console.log(`Service Worker: Deleted expired cache entry: ${request.url}`);
        }
      }
    } catch (error) {
      console.error(`Service Worker: Error cleaning cache ${cacheName}:`, error);
    }
  }
}

// Get max age for cache type
function getMaxAgeForCache(cacheName) {
  switch (cacheName) {
    case CACHE_CONFIG.API_CACHE:
      return CACHE_EXPIRATION.API;
    case CACHE_CONFIG.STATIC_CACHE:
      return CACHE_EXPIRATION.STATIC;
    case CACHE_CONFIG.MEDIA_CACHE:
      return CACHE_EXPIRATION.MEDIA;
    default:
      return CACHE_EXPIRATION.API;
  }
}

// Message event - handle messages from clients
self.addEventListener('message', (event) => {
  const { type, data } = event.data;
  
  console.log('Service Worker: Received message:', type);
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'TRIGGER_SYNC':
      // Register sync event
      self.registration.sync.register(data?.tag || SYNC_TAG)
        .then(() => {
          event.ports[0]?.postMessage({ success: true });
        })
        .catch((error) => {
          console.error('Failed to register sync:', error);
          event.ports[0]?.postMessage({ success: false, error: error.message });
        });
      break;
      
    case 'CACHE_ROUTE':
      // Pre-cache route data
      if (data?.url) {
        cacheRouteData(data.url, data.routeId);
      }
      break;
      
    case 'CACHE_RESOURCES':
      // Cache multiple resources
      if (data?.urls && Array.isArray(data.urls)) {
        cacheResources(data.urls, data.cacheName);
      }
      break;
      
    case 'CLEAR_CACHE':
      // Clear specific or all caches
      clearCaches(data?.cacheName)
        .then(() => {
          event.ports[0]?.postMessage({ success: true });
        })
        .catch((error) => {
          event.ports[0]?.postMessage({ success: false, error: error.message });
        });
      break;
      
    case 'GET_CACHE_STATUS':
      // Return cache status
      getCacheStatus()
        .then((status) => {
          event.ports[0]?.postMessage({ success: true, data: status });
        })
        .catch((error) => {
          event.ports[0]?.postMessage({ success: false, error: error.message });
        });
      break;
      
    case 'ENABLE_OFFLINE_MODE':
      // Enable enhanced offline mode
      enableOfflineMode(data);
      break;
  }
});

// Helper functions for message handlers
async function cacheRouteData(url, routeId) {
  try {
    const cache = await caches.open(CACHE_CONFIG.API_CACHE);
    const response = await fetch(url);
    
    if (response.ok) {
      await cache.put(url, response);
      console.log(`Service Worker: Cached route data for route ${routeId}`);
      
      // Also cache related endpoints
      const relatedUrls = [
        `/api/v1/routes/${routeId}/stops`,
        `/api/v1/routes/${routeId}/customers`,
      ];
      
      for (const relatedUrl of relatedUrls) {
        try {
          const relatedResponse = await fetch(relatedUrl);
          if (relatedResponse.ok) {
            await cache.put(relatedUrl, relatedResponse);
          }
        } catch (error) {
          console.error(`Failed to cache ${relatedUrl}:`, error);
        }
      }
    }
  } catch (error) {
    console.error('Service Worker: Failed to cache route data:', error);
  }
}

async function cacheResources(urls, cacheName = CACHE_CONFIG.STATIC_CACHE) {
  try {
    const cache = await caches.open(cacheName);
    await cache.addAll(urls);
    console.log(`Service Worker: Cached ${urls.length} resources`);
  } catch (error) {
    console.error('Service Worker: Failed to cache resources:', error);
  }
}

async function clearCaches(cacheName) {
  if (cacheName) {
    await caches.delete(cacheName);
  } else {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(name => caches.delete(name)));
  }
  console.log('Service Worker: Caches cleared');
}

async function getCacheStatus() {
  const status = {};
  const cacheNames = await caches.keys();
  
  for (const cacheName of cacheNames) {
    const cache = await caches.open(cacheName);
    const requests = await cache.keys();
    status[cacheName] = {
      count: requests.length,
      urls: requests.map(r => r.url),
    };
  }
  
  return status;
}

// Helper functions for sync operations
async function openSyncDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('luckygas-offline', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('syncQueue')) {
        db.createObjectStore('syncQueue', { keyPath: 'id' });
      }
    };
  });
}

async function processSyncItem(item) {
  const response = await fetch(item.url, {
    method: item.method,
    headers: item.headers,
    body: item.body,
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  return response;
}

async function removeSyncItem(db, id) {
  const tx = db.transaction(['syncQueue'], 'readwrite');
  const store = tx.objectStore('syncQueue');
  await store.delete(id);
}

async function updateSyncItem(db, id, updates) {
  const tx = db.transaction(['syncQueue'], 'readwrite');
  const store = tx.objectStore('syncQueue');
  const item = await store.get(id);
  
  if (item) {
    Object.assign(item, updates);
    await store.put(item);
  }
}

async function updateSyncStatus(status) {
  // Store sync status for client access
  const cache = await caches.open('sync-status');
  await cache.put(
    new Request('sync-status'),
    new Response(JSON.stringify(status), {
      headers: { 'Content-Type': 'application/json' },
    })
  );
}