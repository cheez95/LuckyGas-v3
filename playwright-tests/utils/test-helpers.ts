import { Page, expect } from '@playwright/test';
import { readFileSync } from 'fs';
import { join } from 'path';

export class TestHelpers {
  static loadFixture(fixtureName: string): any {
    const fixturePath = join(__dirname, '..', 'fixtures', `${fixtureName}.json`);
    return JSON.parse(readFileSync(fixturePath, 'utf-8'));
  }

  static generateUniqueId(prefix: string = ''): string {
    return `${prefix}${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  static async waitForAPIResponse(page: Page, urlPattern: string | RegExp): Promise<any> {
    const responsePromise = page.waitForResponse(
      response => {
        if (typeof urlPattern === 'string') {
          return response.url().includes(urlPattern);
        }
        return urlPattern.test(response.url());
      }
    );
    return responsePromise;
  }

  static async takeScreenshot(page: Page, name: string): Promise<void> {
    await page.screenshot({ 
      path: join(__dirname, '..', 'reports', 'screenshots', `${name}.png`),
      fullPage: true 
    });
  }

  static async fillForm(page: Page, formData: Record<string, any>): Promise<void> {
    for (const [selector, value] of Object.entries(formData)) {
      const element = await page.locator(selector);
      const tagName = await element.evaluate(el => el.tagName.toLowerCase());
      
      if (tagName === 'select') {
        await element.selectOption(value);
      } else if (tagName === 'input') {
        const type = await element.getAttribute('type');
        if (type === 'checkbox' || type === 'radio') {
          if (value) await element.check();
          else await element.uncheck();
        } else {
          await element.fill(value.toString());
        }
      } else if (tagName === 'textarea') {
        await element.fill(value.toString());
      }
    }
  }

  static async checkToast(page: Page, message: string, type: 'success' | 'error' | 'info' = 'success'): Promise<void> {
    const toast = page.locator(`.toast.toast-${type}`, { hasText: message });
    await expect(toast).toBeVisible({ timeout: 5000 });
    await expect(toast).not.toBeVisible({ timeout: 10000 });
  }

  static async loginUI(page: Page, username: string, password: string): Promise<void> {
    await page.goto('/login');
    await page.fill('input[name="username"]', username);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  }

  static async checkAccessibility(page: Page): Promise<void> {
    // Basic accessibility checks
    const missingAltTexts = await page.$$eval('img:not([alt])', imgs => imgs.length);
    expect(missingAltTexts).toBe(0);

    const missingLabels = await page.$$eval('input:not([aria-label]):not([id])', inputs => inputs.length);
    expect(missingLabels).toBe(0);

    // Check for keyboard navigation
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).not.toBe('BODY');
  }

  static async measurePerformance(page: Page): Promise<any> {
    const performanceMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0,
      };
    });
    return performanceMetrics;
  }

  static formatTaiwanDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  static async checkTableData(page: Page, tableSelector: string, expectedData: any[]): Promise<void> {
    const rows = await page.$$eval(`${tableSelector} tbody tr`, rows => 
      rows.map(row => Array.from(row.querySelectorAll('td')).map(td => td.textContent?.trim() || ''))
    );
    
    expect(rows.length).toBeGreaterThanOrEqual(expectedData.length);
    
    for (let i = 0; i < expectedData.length; i++) {
      const row = rows[i];
      const expected = expectedData[i];
      
      if (Array.isArray(expected)) {
        expect(row).toEqual(expected);
      } else {
        for (const [key, value] of Object.entries(expected)) {
          expect(row).toContain(value.toString());
        }
      }
    }
  }

  static async waitForLoadingComplete(page: Page): Promise<void> {
    // Wait for any loading spinners to disappear
    const loadingSelectors = [
      '.loading',
      '.spinner',
      '[data-loading="true"]',
      '.ant-spin',
      '.el-loading-mask'
    ];
    
    for (const selector of loadingSelectors) {
      const loading = page.locator(selector);
      if (await loading.count() > 0) {
        await expect(loading).not.toBeVisible({ timeout: 30000 });
      }
    }
  }

  static async checkResponseTime(responsePromise: Promise<any>, maxTime: number = 2000): Promise<void> {
    const start = Date.now();
    await responsePromise;
    const duration = Date.now() - start;
    expect(duration).toBeLessThan(maxTime);
  }

  static async simulateSlowNetwork(page: Page): Promise<void> {
    const client = await page.context().newCDPSession(page);
    await client.send('Network.enable');
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: (1.5 * 1024 * 1024) / 8, // 1.5 Mbps
      uploadThroughput: (750 * 1024) / 8, // 750 Kbps
      latency: 40 // 40ms
    });
  }

  static async clearAllData(page: Page): Promise<void> {
    // Clear local storage
    await page.evaluate(() => localStorage.clear());
    
    // Clear session storage
    await page.evaluate(() => sessionStorage.clear());
    
    // Clear cookies
    await page.context().clearCookies();
  }
}