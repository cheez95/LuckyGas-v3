import { test, expect, devices, BrowserContext, Page } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';

// Mobile device configurations
const MOBILE_DEVICES = {
  'iPhone 13': devices['iPhone 13'],
  'iPhone SE': devices['iPhone SE'],
  'Pixel 5': devices['Pixel 5'],
  'Galaxy S21': devices['Galaxy S9+'] // Using S9+ as S21 might not be available
};

// Helper to simulate touch gestures
async function swipeGesture(page: Page, startX: number, startY: number, endX: number, endY: number) {
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(endX, endY, { steps: 10 });
  await page.mouse.up();
}

// Helper to simulate pull-to-refresh
async function pullToRefresh(page: Page) {
  const viewport = page.viewportSize();
  if (viewport) {
    await swipeGesture(page, viewport.width / 2, 100, viewport.width / 2, 300);
  }
}

// Helper to check PWA features
async function checkPWAFeatures(page: Page) {
  // Check manifest
  const manifest = await page.evaluate(() => {
    const link = document.querySelector('link[rel="manifest"]');
    return link ? link.getAttribute('href') : null;
  });
  expect(manifest).toBeTruthy();

  // Check service worker
  const hasServiceWorker = await page.evaluate(() => 'serviceWorker' in navigator);
  expect(hasServiceWorker).toBeTruthy();
}

test.describe('Comprehensive Mobile Testing', () => {
  test.describe('Multi-device Compatibility', () => {
    Object.entries(MOBILE_DEVICES).forEach(([deviceName, deviceConfig]) => {
      test(`${deviceName} - Complete user flow`, async ({ browser }) => {
        const context = await browser.newContext({
          ...deviceConfig,
          permissions: ['geolocation'],
          geolocation: { latitude: 25.0330, longitude: 121.5654 }
        });
        const page = await context.newPage();

        // Test login
        const loginPage = new LoginPage(page);
        await loginPage.goto();
        
        // Check responsive layout
        await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
        const formWidth = await page.locator('[data-testid="login-form"]').boundingBox();
        expect(formWidth?.width).toBeLessThanOrEqual(deviceConfig.viewport.width);

        // Login as driver
        await loginPage.login('driver1', 'driver123');
        await expect(page).toHaveURL(/driver/);

        // Check mobile navigation
        await expect(page.locator('[data-testid="mobile-nav"]')).toBeVisible();
        
        // Test route view
        await page.locator('[data-testid="route-card"]').first().tap();
        await expect(page).toHaveURL(/route/);

        await context.close();
      });
    });
  });

  test.describe('Touch Gestures and Interactions', () => {
    let context: BrowserContext;
    let page: Page;

    test.beforeEach(async ({ browser }) => {
      context = await browser.newContext({
        ...devices['iPhone 13'],
        permissions: ['geolocation', 'camera'],
        geolocation: { latitude: 25.0330, longitude: 121.5654 }
      });
      page = await context.newPage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');
    });

    test.afterEach(async () => {
      await context.close();
    });

    test('Swipe navigation between deliveries', async () => {
      await page.goto('/driver/route/1');
      
      // Get initial delivery
      const initialDelivery = await page.locator('[data-testid="current-delivery"]').textContent();
      
      // Swipe left to next delivery
      const viewport = page.viewportSize()!;
      await swipeGesture(page, viewport.width - 50, viewport.height / 2, 50, viewport.height / 2);
      
      // Check delivery changed
      await page.waitForTimeout(500);
      const nextDelivery = await page.locator('[data-testid="current-delivery"]').textContent();
      expect(nextDelivery).not.toBe(initialDelivery);

      // Swipe right to previous
      await swipeGesture(page, 50, viewport.height / 2, viewport.width - 50, viewport.height / 2);
      await page.waitForTimeout(500);
      const prevDelivery = await page.locator('[data-testid="current-delivery"]').textContent();
      expect(prevDelivery).toBe(initialDelivery);
    });

    test('Pull to refresh functionality', async () => {
      await page.goto('/driver');
      
      // Monitor network requests
      let refreshRequested = false;
      page.on('request', request => {
        if (request.url().includes('/api/driver/routes')) {
          refreshRequested = true;
        }
      });

      // Perform pull to refresh
      await pullToRefresh(page);
      await page.waitForTimeout(1000);

      expect(refreshRequested).toBeTruthy();
      await expect(page.locator('[data-testid="refresh-indicator"]')).toBeVisible();
    });

    test('Long press context menu', async () => {
      await page.goto('/driver/route/1');
      
      const deliveryCard = page.locator('[data-testid="delivery-card"]').first();
      const box = await deliveryCard.boundingBox();
      
      if (box) {
        // Simulate long press
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        await page.waitForTimeout(1000); // Long press duration
        await page.mouse.up();

        // Check context menu appears
        await expect(page.locator('[data-testid="context-menu"]')).toBeVisible();
        await expect(page.locator('[data-testid="call-customer"]')).toBeVisible();
        await expect(page.locator('[data-testid="view-directions"]')).toBeVisible();
      }
    });

    test('Pinch to zoom on map', async () => {
      await page.goto('/driver/navigation');
      
      // Get initial map zoom
      const initialZoom = await page.evaluate(() => {
        return (window as any).mapInstance?.getZoom() || 15;
      });

      // Simulate pinch zoom
      const viewport = page.viewportSize()!;
      const centerX = viewport.width / 2;
      const centerY = viewport.height / 2;

      // Start two fingers close together
      await page.mouse.move(centerX - 20, centerY);
      await page.mouse.down();
      await page.mouse.move(centerX - 100, centerY, { steps: 10 });
      await page.mouse.up();

      // Check zoom changed
      const newZoom = await page.evaluate(() => {
        return (window as any).mapInstance?.getZoom() || 15;
      });
      expect(newZoom).not.toBe(initialZoom);
    });

    test('Signature capture with touch', async () => {
      await page.goto('/driver/delivery/1/0');
      
      await page.locator('[data-testid="complete-delivery-btn"]').tap();
      await expect(page.locator('[data-testid="signature-pad"]')).toBeVisible();

      const canvas = page.locator('[data-testid="signature-pad"] canvas');
      const box = await canvas.boundingBox();

      if (box) {
        // Draw signature
        await page.mouse.move(box.x + 50, box.y + 50);
        await page.mouse.down();
        await page.mouse.move(box.x + 150, box.y + 50, { steps: 5 });
        await page.mouse.move(box.x + 150, box.y + 100, { steps: 5 });
        await page.mouse.up();

        // Check signature detected
        const isEmpty = await page.evaluate(() => {
          const pad = (window as any).signaturePad;
          return pad ? pad.isEmpty() : true;
        });
        expect(isEmpty).toBeFalsy();
      }
    });
  });

  test.describe('Offline Functionality', () => {
    test('Complete offline workflow', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13'],
        permissions: ['geolocation']
      });
      const page = await context.newPage();

      // Login while online
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      // Navigate to route
      await page.goto('/driver/route/1');
      await page.waitForLoadState('networkidle');

      // Go offline
      await context.setOffline(true);
      
      // Check offline indicator
      await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();

      // Complete delivery offline
      await page.locator('[data-testid="delivery-card"]').first().tap();
      await page.locator('[data-testid="complete-delivery-btn"]').tap();
      
      // Fill completion form
      await page.locator('[data-testid="delivered-cylinders"]').fill('2');
      await page.locator('[data-testid="collected-cylinders"]').fill('2');
      
      // Add photo (mock)
      await page.locator('[data-testid="add-photo-btn"]').tap();
      
      // Add signature
      const signaturePad = page.locator('[data-testid="signature-pad"]');
      await signaturePad.tap({ position: { x: 50, y: 50 } });
      
      await page.locator('[data-testid="save-delivery-btn"]').tap();

      // Check saved locally
      await expect(page.locator('[data-testid="sync-pending-badge"]')).toBeVisible();
      await expect(page.locator('[data-testid="sync-pending-badge"]')).toContainText('1');

      // Go back online
      await context.setOffline(false);

      // Check sync starts
      await expect(page.locator('[data-testid="sync-in-progress"]')).toBeVisible({ timeout: 5000 });
      
      // Check sync completes
      await expect(page.locator('[data-testid="sync-complete"]')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('[data-testid="sync-pending-badge"]')).not.toBeVisible();

      await context.close();
    });

    test('Offline data persistence', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13']
      });
      const page = await context.newPage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      // Go offline and make changes
      await context.setOffline(true);
      
      await page.goto('/driver/route/1');
      await page.locator('[data-testid="add-note-btn"]').tap();
      await page.locator('[data-testid="note-input"]').fill('客戶不在家');
      await page.locator('[data-testid="save-note-btn"]').tap();

      // Close and reopen app (simulate)
      await page.reload();

      // Check data persisted
      await expect(page.locator('[data-testid="delivery-note"]')).toContainText('客戶不在家');

      await context.close();
    });
  });

  test.describe('Camera and Media', () => {
    test('Photo capture for delivery proof', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13'],
        permissions: ['camera']
      });
      const page = await context.newPage();

      // Mock camera API
      await page.addInitScript(() => {
        (window as any).mockCamera = true;
        navigator.mediaDevices.getUserMedia = async () => {
          const canvas = document.createElement('canvas');
          canvas.width = 640;
          canvas.height = 480;
          const ctx = canvas.getContext('2d');
          ctx!.fillStyle = 'gray';
          ctx!.fillRect(0, 0, 640, 480);
          
          const stream = canvas.captureStream();
          return stream;
        };
      });

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      await page.goto('/driver/delivery/1/0');
      await page.locator('[data-testid="complete-delivery-btn"]').tap();

      // Open camera
      await page.locator('[data-testid="add-photo-btn"]').tap();
      await expect(page.locator('[data-testid="camera-view"]')).toBeVisible();

      // Take photo
      await page.locator('[data-testid="capture-btn"]').tap();
      
      // Check preview
      await expect(page.locator('[data-testid="photo-preview"]')).toBeVisible();
      
      // Accept photo
      await page.locator('[data-testid="accept-photo-btn"]').tap();
      await expect(page.locator('[data-testid="photo-thumbnail"]')).toBeVisible();

      await context.close();
    });

    test('Multiple photo management', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13'],
        permissions: ['camera']
      });
      const page = await context.newPage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      await page.goto('/driver/delivery/1/0');
      await page.locator('[data-testid="complete-delivery-btn"]').tap();

      // Add multiple photos
      for (let i = 0; i < 3; i++) {
        await page.locator('[data-testid="add-photo-btn"]').tap();
        await page.setInputFiles('[data-testid="file-input"]', {
          name: `photo${i}.jpg`,
          mimeType: 'image/jpeg',
          buffer: Buffer.from('fake image data')
        });
      }

      // Check all photos displayed
      await expect(page.locator('[data-testid="photo-thumbnail"]')).toHaveCount(3);

      // Delete a photo
      await page.locator('[data-testid="photo-thumbnail"]').first().press('Delete');
      await expect(page.locator('[data-testid="photo-thumbnail"]')).toHaveCount(2);

      await context.close();
    });
  });

  test.describe('Performance on Mobile', () => {
    test('Page load performance', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13']
      });
      const page = await context.newPage();

      // Enable performance metrics
      await page.coverage.startJSCoverage();
      await page.coverage.startCSSCoverage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      
      // Measure login page load
      const loginMetrics = await page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        return {
          domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
          loadComplete: navigation.loadEventEnd - navigation.fetchStart
        };
      });

      expect(loginMetrics.domContentLoaded).toBeLessThan(2000); // 2s for mobile
      expect(loginMetrics.loadComplete).toBeLessThan(3000); // 3s for mobile

      // Login and measure dashboard
      await loginPage.login('driver1', 'driver123');
      
      const dashboardMetrics = await page.evaluate(() => {
        const entries = performance.getEntriesByType('navigation');
        const latest = entries[entries.length - 1] as PerformanceNavigationTiming;
        return {
          firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0,
          firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0
        };
      });

      expect(dashboardMetrics.firstContentfulPaint).toBeLessThan(1500); // 1.5s FCP

      // Check JS/CSS coverage
      const jsCoverage = await page.coverage.stopJSCoverage();
      const cssCoverage = await page.coverage.stopCSSCoverage();

      // Calculate unused bytes
      let totalJSBytes = 0;
      let usedJSBytes = 0;
      
      for (const entry of jsCoverage) {
        totalJSBytes += entry.text.length;
        for (const range of entry.ranges) {
          usedJSBytes += range.end - range.start;
        }
      }

      const jsUsagePercent = (usedJSBytes / totalJSBytes) * 100;
      expect(jsUsagePercent).toBeGreaterThan(50); // At least 50% JS utilization

      await context.close();
    });

    test('Smooth scrolling and animations', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13']
      });
      const page = await context.newPage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      await page.goto('/driver/route/1');

      // Measure scroll performance
      const scrollMetrics = await page.evaluate(async () => {
        const startTime = performance.now();
        const fps: number[] = [];
        let lastTime = startTime;

        const measureFPS = () => {
          const currentTime = performance.now();
          const delta = currentTime - lastTime;
          if (delta > 0) {
            fps.push(1000 / delta);
          }
          lastTime = currentTime;
        };

        // Scroll down
        for (let i = 0; i < 10; i++) {
          window.scrollBy(0, 100);
          measureFPS();
          await new Promise(resolve => setTimeout(resolve, 16)); // ~60fps
        }

        return {
          avgFPS: fps.reduce((a, b) => a + b, 0) / fps.length,
          minFPS: Math.min(...fps)
        };
      });

      expect(scrollMetrics.avgFPS).toBeGreaterThan(30); // Smooth scrolling
      expect(scrollMetrics.minFPS).toBeGreaterThan(20); // No major jank

      await context.close();
    });
  });

  test.describe('PWA Features', () => {
    test('PWA installation prompt', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13']
      });
      const page = await context.newPage();

      await page.goto('/');
      
      // Check PWA features
      await checkPWAFeatures(page);

      // Check for install prompt (mock)
      const canInstall = await page.evaluate(() => {
        return 'BeforeInstallPromptEvent' in window;
      });

      if (canInstall) {
        // Trigger install
        await page.evaluate(() => {
          const event = new Event('beforeinstallprompt');
          window.dispatchEvent(event);
        });

        await expect(page.locator('[data-testid="install-prompt"]')).toBeVisible();
      }

      await context.close();
    });

    test('Service worker caching', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13']
      });
      const page = await context.newPage();

      await page.goto('/');

      // Wait for service worker
      await page.evaluate(() => {
        return navigator.serviceWorker.ready;
      });

      // Check cache
      const cachedResources = await page.evaluate(async () => {
        const cacheNames = await caches.keys();
        const resources: string[] = [];
        
        for (const name of cacheNames) {
          const cache = await caches.open(name);
          const requests = await cache.keys();
          resources.push(...requests.map(r => r.url));
        }
        
        return resources;
      });

      expect(cachedResources.length).toBeGreaterThan(0);
      expect(cachedResources.some(url => url.includes('.js'))).toBeTruthy();
      expect(cachedResources.some(url => url.includes('.css'))).toBeTruthy();

      await context.close();
    });
  });

  test.describe('Battery and Resource Optimization', () => {
    test('GPS battery optimization', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13'],
        permissions: ['geolocation']
      });
      const page = await context.newPage();

      // Monitor GPS calls
      let gpsCallCount = 0;
      await page.addInitScript(() => {
        const original = navigator.geolocation.getCurrentPosition;
        navigator.geolocation.getCurrentPosition = function(...args) {
          (window as any).gpsCallCount = ((window as any).gpsCallCount || 0) + 1;
          return original.apply(this, args);
        };
      });

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      await page.goto('/driver/navigation');
      
      // Wait for initial GPS
      await page.waitForTimeout(2000);

      // Get GPS call count
      gpsCallCount = await page.evaluate(() => (window as any).gpsCallCount || 0);

      // Should use intelligent polling, not constant GPS
      expect(gpsCallCount).toBeLessThan(5); // Not excessive in 2 seconds

      // Check for battery saver mode
      await page.locator('[data-testid="settings-btn"]').tap();
      await expect(page.locator('[data-testid="battery-saver-toggle"]')).toBeVisible();

      await context.close();
    });

    test('Background sync optimization', async ({ browser }) => {
      const context = await browser.newContext({
        ...devices['iPhone 13']
      });
      const page = await context.newPage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('driver1', 'driver123');

      // Monitor network requests
      const requests: string[] = [];
      page.on('request', request => {
        if (request.url().includes('/api/')) {
          requests.push(request.url());
        }
      });

      // Simulate background mode
      await page.evaluate(() => {
        document.dispatchEvent(new Event('visibilitychange'));
        Object.defineProperty(document, 'visibilityState', {
          value: 'hidden',
          configurable: true
        });
      });

      await page.waitForTimeout(3000);

      // Should reduce API calls in background
      const backgroundRequests = requests.filter(r => !r.includes('critical'));
      expect(backgroundRequests.length).toBeLessThan(2);

      await context.close();
    });
  });
});