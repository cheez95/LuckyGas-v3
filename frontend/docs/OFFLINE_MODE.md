# Driver Offline Mode Documentation

## Overview
The LuckyGas v3 Driver Interface includes comprehensive offline functionality that allows drivers to continue their delivery operations even when network connectivity is poor or unavailable.

## Key Features

### 1. **IndexedDB Local Storage**
- All delivery data is stored locally using IndexedDB
- Supports storing orders, customer information, photos, signatures, and location data
- Automatic storage quota management with warnings at 80% usage
- Old synced data is automatically cleaned up after 7 days

### 2. **Sync Queue Management**
- Intelligent queue system for pending operations
- Priority-based sync (high, normal, low)
- Exponential backoff retry mechanism
- Conflict resolution with last-write-wins strategy
- Manual review option for conflicts

### 3. **Visual Offline Indicator**
- Real-time online/offline status display
- Shows pending sync count
- Displays last sync timestamp
- Manual sync trigger button
- Storage usage indicator

### 4. **Service Worker Implementation**
- Background sync for automatic data synchronization
- Caches critical resources for offline use
- Periodic sync attempts when online
- Push notification support

### 5. **Offline Capabilities**
- Complete deliveries with photos and signatures
- Update delivery notes and status
- Track GPS location continuously
- Start and complete routes
- View cached customer and order information

## Technical Implementation

### Service Worker
```javascript
// Registered in main.tsx
serviceWorkerRegistration.register({
  onSuccess: () => console.log('Service Worker registered'),
  onUpdate: () => console.log('New version available'),
});
```

### IndexedDB Schema
- **orders**: Delivery order information
- **syncQueue**: Pending sync operations
- **locations**: GPS location history
- **photos**: Delivery photos as blobs
- **cache**: General data cache

### Offline Storage Service
Located at `/frontend/src/services/offline/offlineStorage.ts`
- Singleton pattern for consistent access
- Type-safe operations with TypeScript
- Automatic cleanup of old data

### Sync Queue Manager
Located at `/frontend/src/services/offline/syncQueue.ts`
- Manages sync operations
- Handles conflict resolution
- Provides sync progress updates

### React Hook
`useOfflineSync()` hook provides:
- Online/offline status
- Save operations for offline data
- Sync progress monitoring
- Manual sync triggering

## Usage

### For Drivers

1. **Working Offline**
   - The app automatically detects when you're offline
   - Continue working normally - all data is saved locally
   - A red "離線模式" (Offline Mode) indicator appears

2. **Completing Deliveries Offline**
   - Take photos, capture signatures
   - Add delivery notes
   - Mark deliveries as complete
   - All data is queued for sync

3. **When Connection Returns**
   - Data automatically syncs in the background
   - Progress indicator shows sync status
   - Any conflicts are highlighted for resolution

### For Developers

1. **Saving Data Offline**
```typescript
const { saveDeliveryOffline } = useOfflineSync();

await saveDeliveryOffline(stopId, orderId, {
  signature: signatureData,
  photos: photoIds,
  notes: deliveryNotes,
});
```

2. **Monitoring Sync Status**
```typescript
const { syncProgress, isOnline } = useOfflineSync();

// Display sync progress
<OfflineIndicator showDetails={true} />
```

3. **Manual Sync Trigger**
```typescript
const { triggerSync } = useOfflineSync();

await triggerSync(); // Manually trigger sync
```

## Testing

Run offline mode tests:
```bash
npm run test:e2e offline-mode.spec.ts
```

Test scenarios include:
- Offline indicator display
- Saving deliveries offline
- Sync on reconnection
- Conflict resolution
- Service worker caching

## Best Practices

1. **Always Handle Both Online and Offline Cases**
   - Check `isOnline` status before API calls
   - Provide appropriate user feedback

2. **Optimize Storage Usage**
   - Clean up old data regularly
   - Compress photos before storing
   - Monitor storage quota

3. **Test Offline Scenarios**
   - Use browser DevTools to simulate offline
   - Test with real network interruptions
   - Verify data consistency after sync

## Troubleshooting

### Common Issues

1. **Service Worker Not Registering**
   - Check browser compatibility
   - Ensure HTTPS is enabled
   - Clear browser cache

2. **Storage Quota Exceeded**
   - Implement cleanup strategies
   - Compress data before storing
   - Alert users to clear old data

3. **Sync Failures**
   - Check network connectivity
   - Verify API endpoints
   - Review conflict resolution logic

### Debug Tools
- Chrome DevTools > Application > IndexedDB
- Chrome DevTools > Application > Service Workers
- Network tab to monitor sync requests

## Future Enhancements

1. **Selective Sync**
   - Allow users to prioritize certain data
   - Implement bandwidth-aware sync

2. **Advanced Conflict Resolution**
   - Three-way merge for complex conflicts
   - User-defined resolution strategies

3. **Offline Analytics**
   - Track offline usage patterns
   - Optimize caching strategies

4. **Progressive Web App Features**
   - Add to home screen
   - Full offline app experience