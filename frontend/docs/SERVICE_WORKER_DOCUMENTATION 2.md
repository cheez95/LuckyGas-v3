# Lucky Gas PWA Service Worker Documentation

## Overview

The Lucky Gas PWA service worker provides comprehensive offline support for drivers, enabling them to continue deliveries even without network connectivity. This document details the enhanced service worker implementation and its features.

## Key Features

### 1. **Multi-Cache Strategy**
- **Static Cache**: Core app shell files (HTML, CSS, JS)
- **API Cache**: API responses with 5-minute expiration
- **Media Cache**: Images and photos with 30-day expiration
- **Runtime Cache**: Dynamic content and navigation

### 2. **Network Strategies**
- **Network First with Timeout**: API requests (5-second timeout)
- **Cache First**: Images and media files
- **Stale While Revalidate**: CSS and JavaScript files
- **Network First with Offline Fallback**: Navigation requests

### 3. **Background Sync**
- Automatic sync when network is restored
- Priority-based queue processing
- Retry logic with exponential backoff
- Conflict resolution for concurrent updates

### 4. **Offline Data Storage**
- IndexedDB for structured data
- Photo blob storage
- Location tracking queue
- Delivery completion records

## Architecture

### Cache Configuration
```javascript
const CACHE_CONFIG = {
  STATIC_CACHE: 'lucky-gas-static-v3',
  API_CACHE: 'lucky-gas-api-v3',
  MEDIA_CACHE: 'lucky-gas-media-v3',
  RUNTIME_CACHE: 'lucky-gas-runtime-v3',
};
```

### Supported Offline Endpoints
- `/api/v1/routes/driver` - Driver's assigned routes
- `/api/v1/routes/{id}` - Specific route details
- `/api/v1/routes/{id}/stops` - Route stops
- `/api/v1/orders/{id}` - Order details
- `/api/v1/customers/{id}` - Customer information
- `/api/v1/products` - Product catalog
- `/api/v1/driver/profile` - Driver profile
- `/api/v1/driver/stats` - Driver statistics

## Installation & Activation

### Installation Process
1. Caches essential static files
2. Pre-caches driver profile and product catalog
3. Sets up IndexedDB for offline storage
4. Registers for background sync

### Activation Process
1. Cleans up old cache versions
2. Claims control of all open tabs
3. Initializes sync queue
4. Sets up periodic sync (if supported)

## Offline Functionality

### Data Storage
```javascript
// Save delivery completion offline
await offlineStorage.saveOrder({
  id: `${stopId}-${orderId}`,
  orderId,
  customerName,
  signature,
  photos,
  timestamp: Date.now(),
  synced: false,
});
```

### Photo Management
- Photos are stored as blobs in IndexedDB
- Compressed before storage
- Uploaded when connection is restored
- Automatic cleanup after successful sync

### Location Tracking
- GPS coordinates queued for batch upload
- Sent every 10 locations or 5 minutes
- Low priority to preserve battery

## Sync Process

### Sync Queue Processing
1. **High Priority**: Delivery completions, route status updates
2. **Normal Priority**: Order updates, customer changes
3. **Low Priority**: Location updates, analytics data

### Conflict Resolution
- Last-write-wins for order updates
- Server validation for delivery completions
- Manual review queue for unresolvable conflicts

### Retry Logic
```javascript
const retryDelays = [
  1000,   // 1 second
  5000,   // 5 seconds
  15000,  // 15 seconds
  30000,  // 30 seconds
  60000,  // 1 minute
];
```

## User Experience

### Offline Indicators
- Visual badge showing offline status
- Queue counter for pending operations
- Storage usage meter
- Last sync timestamp

### Offline Page Features
- Real-time connection monitoring
- Manual sync trigger
- Storage management
- Feature availability grid

## API Integration

### Request Handling
```javascript
// POST/PUT requests are queued when offline
if (request.method !== 'GET') {
  await queueRequestForSync(request);
  return new Response(
    JSON.stringify({ 
      success: true, 
      offline: true, 
      message: '資料已儲存，將在連線後同步' 
    }),
    { status: 202 }
  );
}
```

### Response Headers
- `X-Offline-Mode`: Indicates offline response
- `X-Cache-Age`: Age of cached response in seconds
- `X-Cached-At`: Original cache timestamp

## Message Communication

### Client to Service Worker
```javascript
// Trigger manual sync
navigator.serviceWorker.controller.postMessage({
  type: 'TRIGGER_SYNC',
  data: { tag: 'manual-sync' }
});

// Cache route data
navigator.serviceWorker.controller.postMessage({
  type: 'CACHE_ROUTE',
  data: { url: '/api/v1/routes/123', routeId: 123 }
});
```

### Service Worker to Client
```javascript
// Sync progress updates
client.postMessage({
  type: 'SYNC_PROGRESS',
  data: {
    total: 10,
    completed: 5,
    failed: 0
  }
});
```

## Performance Optimization

### Cache Expiration
- API responses: 5 minutes
- Static assets: 7 days
- Media files: 30 days
- Automatic cleanup during activation

### Network Timeout
- Default: 5 seconds for API calls
- Configurable per request type
- Immediate cache fallback on timeout

## Testing

### Manual Testing
1. Enable offline mode in DevTools
2. Perform delivery operations
3. Re-enable network
4. Verify sync completion

### Debugging
```javascript
// Check cache status
const cacheStatus = await getCacheStatus();
console.log('Cache contents:', cacheStatus);

// Monitor sync events
self.addEventListener('sync', (event) => {
  console.log('Sync event:', event.tag);
});
```

## Browser Support

### Required APIs
- Service Worker API
- Cache API
- IndexedDB
- Background Sync API (optional)
- Periodic Background Sync API (optional)

### Fallback Behavior
- No service worker: Standard online-only operation
- No background sync: Manual sync on app open
- No IndexedDB: LocalStorage fallback (limited)

## Security Considerations

### Data Protection
- All offline data encrypted at rest
- Sensitive data cleared after sync
- No credentials stored offline
- HTTPS required for service worker

### Cache Security
- Origin isolation enforced
- No cross-origin data cached
- Cache headers respected
- Regular cache cleanup

## Maintenance

### Version Updates
1. Increment cache version numbers
2. Update offline file list
3. Test migration process
4. Deploy with cache-busting

### Monitoring
- Track sync success rates
- Monitor cache hit rates
- Measure offline usage
- Alert on sync failures

## Troubleshooting

### Common Issues

1. **Service Worker Not Installing**
   - Check HTTPS requirement
   - Verify manifest.json
   - Clear browser cache

2. **Sync Not Working**
   - Check IndexedDB quota
   - Verify network detection
   - Review sync permissions

3. **Cache Growing Too Large**
   - Implement aggressive cleanup
   - Reduce cache expiration times
   - Limit photo storage

### Debug Commands
```javascript
// Force cache cleanup
await cleanExpiredCacheEntries();

// Clear all offline data
await offlineStorage.clearAllData();

// Trigger immediate sync
await performBackgroundSync('debug-sync');
```

## Future Enhancements

### Planned Features
1. Selective route pre-caching
2. Predictive content caching
3. P2P sync between drivers
4. Offline analytics collection
5. Voice command support offline

### Performance Goals
- < 1 second cache response time
- < 10 MB average cache size
- > 95% sync success rate
- < 30 second sync completion

## Code Examples

### Saving Delivery Offline
```javascript
const { saveDeliveryOffline } = useOfflineSync();

await saveDeliveryOffline(stopId, orderId, {
  signature: signatureDataUrl,
  photos: photoBlobs,
  notes: deliveryNotes,
  customerName: customer.name,
  customerPhone: customer.phone,
  address: customer.address,
  products: orderProducts,
});
```

### Manual Sync Trigger
```javascript
const { triggerSync, syncProgress } = useOfflineSync();

const handleManualSync = async () => {
  try {
    await triggerSync();
    message.success('同步已開始');
  } catch (error) {
    message.error('無法在離線狀態下同步');
  }
};
```

### Storage Management
```javascript
const { storageQuota, cleanupOldData } = useOfflineSync();

// Check storage usage
if (storageQuota.status === 'warning') {
  // Clean up data older than 3 days
  await cleanupOldData(3);
}
```

## Conclusion

The Lucky Gas PWA service worker provides a robust offline experience for drivers, ensuring business continuity even in areas with poor network coverage. The implementation prioritizes reliability, performance, and user experience while maintaining data integrity and security.