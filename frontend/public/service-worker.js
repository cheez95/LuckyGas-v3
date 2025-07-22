// Service Worker for Lucky Gas PWA
const CACHE_NAME = 'lucky-gas-v1';
const OFFLINE_URL = '/offline.html';

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

// Install event - cache resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Opened cache');
      return cache.addAll(urlsToCache);
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
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Network first strategy for API calls
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Clone the response before caching
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
          return response;
        })
        .catch(() => {
          // Return cached response if available
          return caches.match(event.request);
        })
    );
    return;
  }

  // Cache first strategy for static assets
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request).catch(() => {
        // Return offline page for navigation requests
        if (event.request.mode === 'navigate') {
          return caches.match(OFFLINE_URL);
        }
      });
    })
  );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-deliveries') {
    event.waitUntil(syncDeliveries());
  }
});

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

// Helper function to sync offline deliveries
async function syncDeliveries() {
  try {
    const cache = await caches.open(CACHE_NAME);
    const requests = await cache.keys();
    
    const deliveryRequests = requests.filter(req => 
      req.url.includes('/api/v1/deliveries') && req.method === 'POST'
    );

    for (const request of deliveryRequests) {
      try {
        const response = await fetch(request.clone());
        if (response.ok) {
          await cache.delete(request);
        }
      } catch (error) {
        console.error('Failed to sync delivery:', error);
      }
    }
  } catch (error) {
    console.error('Sync failed:', error);
  }
}