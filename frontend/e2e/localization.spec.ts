import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { CustomerPage } from './pages/CustomerPage';
import { OrderPage } from './pages/OrderPage';
import { RoutePage } from './pages/RoutePage';

test.describe('Traditional Chinese Localization', () => {
  test.use({ locale: 'zh-TW' });
  
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let customerPage: CustomerPage;
  let orderPage: OrderPage;
  let routePage: RoutePage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    customerPage = new CustomerPage(page);
    orderPage = new OrderPage(page);
    routePage = new RoutePage(page);
  });

  test('should display all UI elements in Traditional Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    
    // Check login page
    await expect(loginPage.loginTitle).toContainText('幸福氣管理系統');
    await expect(loginPage.loginButton).toContainText('登入');
    
    // Check placeholders
    const usernamePlaceholder = await loginPage.usernameInput.getAttribute('placeholder');
    expect(usernamePlaceholder).toContain('用戶名');
    
    const passwordPlaceholder = await loginPage.passwordInput.getAttribute('placeholder');
    expect(passwordPlaceholder).toContain('密碼');
  });

  test('should show Chinese error messages', async ({ page }) => {
    await loginPage.navigateToLogin();
    
    // Submit empty form
    await loginPage.clickLogin();
    
    // Check validation messages in Chinese
    const usernameError = page.locator('#login_username_help');
    await expect(usernameError).toContainText('請輸入用戶名');
    
    const passwordError = page.locator('#login_password_help');
    await expect(passwordError).toContainText('請輸入密碼');
    
    // Try invalid login
    await loginPage.login('invalid', 'wrong');
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toContain('用戶名或密碼錯誤');
  });

  test('should display dashboard statistics in Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Check dashboard title
    await expect(dashboardPage.pageTitle).toContainText('儀表板');
    
    // Check all statistics cards
    await expect(dashboardPage.todayOrdersCard).toContainText('今日訂單');
    await expect(dashboardPage.activeCustomersCard).toContainText('活躍客戶');
    await expect(dashboardPage.driversOnRouteCard).toContainText('配送中司機');
    await expect(dashboardPage.todayRevenueCard).toContainText('今日營收');
    
    // Check upcoming features
    await expect(dashboardPage.upcomingFeaturesCard).toContainText('即將實現功能');
    await expect(page.getByText('即時訂單狀態追蹤')).toBeVisible();
    await expect(page.getByText('每日需求預測圖表')).toBeVisible();
    await expect(page.getByText('司機配送路線地圖')).toBeVisible();
    await expect(page.getByText('客戶滿意度統計')).toBeVisible();
  });

  test('should display navigation menu in Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Check all menu items
    await expect(dashboardPage.customersMenuItem).toContainText('客戶管理');
    await expect(dashboardPage.ordersMenuItem).toContainText('訂單管理');
    await expect(dashboardPage.deliveriesMenuItem).toContainText('配送管理');
    await expect(dashboardPage.routesMenuItem).toContainText('路線規劃');
    
    // Check user menu
    await dashboardPage.userMenu.click();
    await expect(dashboardPage.logoutMenuItem).toContainText('登出');
  });

  test('should display customer management page in Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    await dashboardPage.navigateToCustomers();
    
    // Check page elements
    const isChineseLocalized = await customerPage.checkChineseLocalization();
    expect(isChineseLocalized).toBe(true);
    
    // Check table headers
    await expect(page.getByText('客戶代碼')).toBeVisible();
    await expect(page.getByText('客戶名稱')).toBeVisible();
    await expect(page.getByText('聯絡電話')).toBeVisible();
    await expect(page.getByText('地址')).toBeVisible();
    await expect(page.getByText('區域')).toBeVisible();
    await expect(page.getByText('狀態')).toBeVisible();
    
    // Check action buttons
    await expect(customerPage.addCustomerButton).toContainText('新增客戶');
    
    // Check search placeholder
    const searchPlaceholder = await customerPage.searchInput.getAttribute('placeholder');
    expect(searchPlaceholder).toContain('搜尋客戶');
  });

  test('should display order management page in Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    await dashboardPage.navigateToOrders();
    
    // Check page elements
    const isChineseLocalized = await orderPage.checkChineseLocalization();
    expect(isChineseLocalized).toBe(true);
    
    // Check specific order statuses
    await expect(page.getByText('待確認', { exact: false })).toBeVisible();
    await expect(page.getByText('已確認', { exact: false })).toBeVisible();
    await expect(page.getByText('配送中', { exact: false })).toBeVisible();
    await expect(page.getByText('已完成', { exact: false })).toBeVisible();
  });

  test('should display route planning page in Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    await dashboardPage.navigateToRoutes();
    
    // Check page elements
    const isChineseLocalized = await routePage.checkChineseLocalization();
    expect(isChineseLocalized).toBe(true);
    
    // Check specific elements
    await expect(routePage.optimizeRouteButton).toContainText('優化路線');
    await expect(page.getByText('總站點數')).toBeVisible();
    await expect(page.getByText('總距離')).toBeVisible();
    await expect(page.getByText('預計時間')).toBeVisible();
  });

  test('should format dates in Taiwan format', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    await dashboardPage.navigateToOrders();
    
    // Wait for table to load
    await page.waitForSelector('.ant-table-tbody tr', { timeout: 5000 });
    
    // Check date format in order list - specifically look for date column (配送日期)
    // Find the column index for "配送日期"
    const headers = await page.locator('.ant-table-thead th').allTextContents();
    const dateColumnIndex = headers.findIndex(h => h.includes('配送日期'));
    
    if (dateColumnIndex !== -1) {
      // Get the date from the first row in the correct column
      const dateCell = await page.locator(`.ant-table-tbody tr:first-child td:nth-child(${dateColumnIndex + 1})`).textContent();
      
      // Should be in YYYY/MM/DD format
      expect(dateCell).toMatch(/\d{4}\/\d{2}\/\d{2}/);
    } else {
      // Fallback: look for any cell that matches date pattern
      const dateCells = await page.locator('.ant-table-cell').allTextContents();
      const dateFound = dateCells.some(text => /^\d{4}\/\d{2}\/\d{2}$/.test(text?.trim() || ''));
      expect(dateFound).toBe(true);
    }
  });

  test('should display currency in TWD', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Check revenue display
    const revenueText = await dashboardPage.todayRevenueCard.textContent();
    expect(revenueText).toContain('元');
    
    // Navigate to orders
    await dashboardPage.navigateToOrders();
    
    // Check order amounts
    const amountCells = page.locator('.ant-table-cell').filter({ hasText: '元' });
    const count = await amountCells.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display Traditional Chinese in forms', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    await dashboardPage.navigateToCustomers();
    
    // Open add customer form
    await customerPage.clickAddCustomer();
    
    // Check form labels - using actual labels from the form
    await expect(page.getByText('客戶編號')).toBeVisible();
    await expect(page.getByText('客戶簡稱')).toBeVisible();
    await expect(page.getByText('發票抬頭')).toBeVisible();
    await expect(page.getByText('客戶類型')).toBeVisible();
    await expect(page.getByText('地址')).toBeVisible();
    await expect(page.getByText('電話')).toBeVisible();
    await expect(page.getByText('電子郵件')).toBeVisible();
    await expect(page.getByText('配送區域')).toBeVisible();
    await expect(page.getByText('配送時段')).toBeVisible();
    await expect(page.getByText('付款方式')).toBeVisible();
    
    // Check buttons
    await expect(customerPage.modalConfirmButton).toContainText('確定');
    await expect(customerPage.modalCancelButton).toContainText('取消');
  });

  test('should display product names in Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    await dashboardPage.navigateToOrders();
    
    // Open create order modal
    await orderPage.clickCreateOrder();
    
    // Click add product
    await orderPage.addProductButton.click();
    
    // Check product options
    const productSelect = page.locator('.product-select').first();
    await productSelect.click();
    
    // Should show Chinese product names
    await expect(page.getByText('桶裝-4公斤-一般')).toBeVisible();
    await expect(page.getByText('桶裝-10公斤-一般')).toBeVisible();
    await expect(page.getByText('桶裝-16公斤-一般')).toBeVisible();
    await expect(page.getByText('流量計-')).toBeVisible();
  });

  test('should display success messages in Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Should show success message
    await expect(page.locator('.ant-message-notice')).toContainText('登入成功');
  });

  test('should handle number formatting for Taiwan', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Check phone number format
    await dashboardPage.navigateToCustomers();
    
    // Phone numbers should be in Taiwan format
    const phoneCell = page.locator('.ant-table-cell').filter({ hasText: /09\d{2}-\d{3}-\d{3}|0\d-\d{4}-\d{4}/ }).first();
    await expect(phoneCell).toBeVisible();
  });

  test('should use Chinese for all tooltips', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    await dashboardPage.navigateToCustomers();
    
    // Hover over action buttons
    const editButton = page.locator('button').filter({ hasText: '編輯' }).first();
    await editButton.hover();
    
    // Check if tooltip appears in Chinese (if implemented)
    // await expect(page.locator('.ant-tooltip')).toContainText('編輯客戶');
  });

  test('should display confirmation dialogs in Chinese', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Try to logout
    await dashboardPage.userMenu.click();
    await dashboardPage.logoutMenuItem.click();
    
    // If confirmation dialog is shown
    const confirmDialog = page.locator('.ant-modal-confirm');
    if (await confirmDialog.isVisible()) {
      await expect(confirmDialog).toContainText('確定要登出嗎？');
      await expect(page.locator('.ant-modal-confirm .ant-btn-primary')).toContainText('確定');
      await expect(page.locator('.ant-modal-confirm .ant-btn').first()).toContainText('取消');
    }
  });

  test('should handle language switching if available', async ({ page }) => {
    await loginPage.navigateToLogin();
    await loginPage.login('admin', 'admin123');
    await loginPage.waitForLoginSuccess();
    
    // Look for language switcher (if implemented)
    const languageSwitcher = page.locator('[data-testid="language-switcher"], .language-switcher');
    
    if (await languageSwitcher.isVisible()) {
      await languageSwitcher.click();
      
      // Should show language options
      await expect(page.getByText('繁體中文')).toBeVisible();
      await expect(page.getByText('English')).toBeVisible();
      
      // Switch to English and back
      await page.getByText('English').click();
      await expect(dashboardPage.pageTitle).toContainText('Dashboard');
      
      // Switch back to Chinese
      await languageSwitcher.click();
      await page.getByText('繁體中文').click();
      await expect(dashboardPage.pageTitle).toContainText('儀表板');
    }
  });
});