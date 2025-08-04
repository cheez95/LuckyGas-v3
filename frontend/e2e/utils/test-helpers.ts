import { Page, expect } from '@playwright/test';
import { testUsers, setupTestData, cleanupTestData } from '../fixtures/test-data';

// Authentication helpers
export async function loginAs(page: Page, role: 'admin' | 'manager' | 'officeStaff' | 'driver') {
  const user = testUsers[role];
  await page.goto('/login');
  await page.fill('[data-testid="username-input"]', user.username);
  await page.fill('[data-testid="password-input"]', user.password);
  await page.click('[data-testid="login-button"]');
  await page.waitForURL(/.*\/dashboard|.*\/driver/);
}

export async function logout(page: Page) {
  await page.click('[data-testid="user-menu"]');
  await page.click('[data-testid="logout-btn"]');
  await page.waitForURL(/.*\/login/);
}

// Wait helpers
export async function waitForApiResponse(page: Page, urlPattern: string | RegExp) {
  return page.waitForResponse(
    response => {
      const url = response.url();
      const matches = typeof urlPattern === 'string' 
        ? url.includes(urlPattern)
        : urlPattern.test(url);
      return matches && response.status() === 200;
    },
    { timeout: 10000 }
  );
}

export async function waitForLoadingComplete(page: Page) {
  // Wait for any loading spinners to disappear
  const loadingSpinner = page.locator('[data-testid="loading-spinner"], .ant-spin');
  await expect(loadingSpinner).toHaveCount(0, { timeout: 10000 });
}

// Network helpers
export async function mockApiEndpoint(page: Page, endpoint: string, response: unknown, status: number = 200) {
  await page.route(`**/api/v1/${endpoint}`, route => {
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(response)
    });
  });
}

export async function simulateSlowNetwork(page: Page, delay: number = 2000) {
  await page.route('**/*', async route => {
    await new Promise(resolve => setTimeout(resolve, delay));
    await route.continue();
  });
}

export async function simulateOffline(page: Page) {
  await page.context().setOffline(true);
}

export async function simulateOnline(page: Page) {
  await page.context().setOffline(false);
}

// Mobile testing helpers
export async function setMobileViewport(page: Page, device: 'iPhone12' | 'Pixel5' | 'iPadMini' = 'iPhone12') {
  const viewports = {
    iPhone12: { width: 390, height: 844 },
    Pixel5: { width: 393, height: 851 },
    iPadMini: { width: 768, height: 1024 }
  };
  
  await page.setViewportSize(viewports[device]);
}

export async function grantPermissions(page: Page, permissions: string[] = ['camera', 'geolocation']) {
  await page.context().grantPermissions(permissions, { origin: 'http://localhost:5173' });
}

// Form helpers
export async function fillFormField(page: Page, fieldName: string, value: string) {
  const field = page.locator(`[data-testid="${fieldName}-input"], [name="${fieldName}"]`);
  await field.fill(value);
}

export async function selectDropdownOption(page: Page, dropdownTestId: string, optionText: string) {
  await page.click(`[data-testid="${dropdownTestId}"]`);
  await page.click(`[role="option"]:has-text("${optionText}")`);
}

export async function uploadFile(page: Page, inputSelector: string, filePath: string) {
  const fileInput = page.locator(inputSelector);
  await fileInput.setInputFiles(filePath);
}

// Validation helpers
export async function checkValidationError(page: Page, fieldName: string): Promise<string | null> {
  const errorElement = page.locator(`[data-testid="${fieldName}-error"]`);
  if (await errorElement.isVisible()) {
    return await errorElement.textContent();
  }
  return null;
}

export async function checkToastMessage(page: Page, type: 'success' | 'error' | 'warning' | 'info'): Promise<string | null> {
  const toast = page.locator(`.ant-message-${type}`);
  if (await toast.isVisible()) {
    return await toast.textContent();
  }
  return null;
}

// Table helpers
export async function getTableRowCount(page: Page, tableTestId: string = 'data-table'): Promise<number> {
  const rows = page.locator(`[data-testid="${tableTestId}"] tbody tr`);
  return await rows.count();
}

export async function clickTableAction(page: Page, rowIndex: number, action: 'edit' | 'delete' | 'view') {
  const actionButton = page.locator(`[data-testid="table-row-${rowIndex}"] [data-testid="${action}-btn"]`);
  await actionButton.click();
}

export async function sortTable(page: Page, columnName: string) {
  const columnHeader = page.locator(`th:has-text("${columnName}")`);
  await columnHeader.click();
}

// Pagination helpers
export async function goToPage(page: Page, pageNumber: number) {
  await page.click(`[data-testid="pagination-${pageNumber}"]`);
  await waitForLoadingComplete(page);
}

export async function changePageSize(page: Page, size: number) {
  await selectDropdownOption(page, 'page-size-select', `${size} / 頁`);
  await waitForLoadingComplete(page);
}

// Search and filter helpers
export async function searchTable(page: Page, searchTerm: string) {
  const searchInput = page.locator('[data-testid="search-input"]');
  await searchInput.fill(searchTerm);
  await page.keyboard.press('Enter');
  await waitForLoadingComplete(page);
}

export async function applyDateFilter(page: Page, startDate: string, endDate: string) {
  await page.click('[data-testid="date-range-picker"]');
  await page.fill('[data-testid="start-date-input"]', startDate);
  await page.fill('[data-testid="end-date-input"]', endDate);
  await page.click('[data-testid="apply-filter-btn"]');
  await waitForLoadingComplete(page);
}

// Modal helpers
export async function waitForModal(page: Page, modalTestId: string = 'modal') {
  const modal = page.locator(`[data-testid="${modalTestId}"]`);
  await expect(modal).toBeVisible({ timeout: 5000 });
}

export async function closeModal(page: Page, method: 'cancel' | 'close' | 'confirm' = 'close') {
  if (method === 'cancel') {
    await page.click('[data-testid="modal-cancel-btn"]');
  } else if (method === 'confirm') {
    await page.click('[data-testid="modal-confirm-btn"]');
  } else {
    await page.click('[data-testid="modal-close-btn"], .ant-modal-close');
  }
  
  const modal = page.locator('[data-testid="modal"]');
  await expect(modal).toBeHidden();
}

// Screenshot helpers
export async function takeScreenshot(page: Page, name: string, fullPage: boolean = false) {
  await page.screenshot({
    path: `e2e/screenshots/${name}-${new Date().getTime()}.png`,
    fullPage
  });
}

export async function takeElementScreenshot(page: Page, selector: string, name: string) {
  const element = page.locator(selector);
  await element.screenshot({
    path: `e2e/screenshots/${name}-${new Date().getTime()}.png`
  });
}

// Localization helpers
export async function checkChineseText(page: Page, selector: string): Promise<boolean> {
  const element = page.locator(selector);
  const text = await element.textContent();
  return /[\u4e00-\u9fa5]/.test(text || '');
}

export async function switchLanguage(page: Page, language: 'zh-TW' | 'en') {
  await page.click('[data-testid="language-selector"]');
  await page.click(`[data-testid="language-${language}"]`);
  await page.waitForTimeout(500); // Wait for language change
}

// Performance helpers
export async function measurePageLoadTime(page: Page, url: string): Promise<number> {
  const startTime = Date.now();
  await page.goto(url);
  await waitForLoadingComplete(page);
  return Date.now() - startTime;
}

export async function checkPageSpeed(page: Page, maxLoadTime: number = 3000): Promise<boolean> {
  const loadTime = await page.evaluate(() => {
    const perfData = window.performance.timing;
    return perfData.loadEventEnd - perfData.navigationStart;
  });
  return loadTime <= maxLoadTime;
}

// Accessibility helpers
export async function checkAccessibility(page: Page) {
  // Check for basic accessibility attributes
  const buttons = await page.$$('button:not([aria-label]):not([aria-labelledby])');
  const inputs = await page.$$('input:not([aria-label]):not([aria-labelledby]):not([placeholder])');
  const images = await page.$$('img:not([alt])');
  
  return {
    buttonsWithoutLabels: buttons.length,
    inputsWithoutLabels: inputs.length,
    imagesWithoutAlt: images.length,
    isAccessible: buttons.length === 0 && inputs.length === 0 && images.length === 0
  };
}

// Test setup and teardown
export async function setupTest(page: Page) {
  await setupTestData(page);
  // Clear any existing auth tokens
  await page.evaluate(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  });
}

export async function teardownTest(page: Page) {
  await cleanupTestData(page);
  // Clear any test data created during the test
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

// Retry helper for flaky operations
export async function retryOperation<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError;
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await operation();
    } catch (_error) {
      lastError = error;
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError;
}

// Debug helpers
export async function pauseTest(page: Page, message: string = 'Test paused') {
  console.log(`⏸️  ${message}`);
  await page.pause();
}

export async function logTestInfo(page: Page, info: string) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${info}`);
  
  // Also log to page console for debugging
  await page.evaluate((msg) => {
    console.log(`[TEST] ${msg}`);
  }, info);
}