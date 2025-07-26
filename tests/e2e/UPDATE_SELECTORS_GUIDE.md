# Test Selector Update Guide

## Problem
Tests are looking for elements with `data-testid` attributes that don't exist in the actual UI implementation.

## Solution Patterns

### 1. Navigation Elements
```typescript
// ❌ OLD: Using data-testid
await page.click('[data-testid="nav-customers"]');

// ✅ NEW: Using text content
await page.getByText('客戶管理').click();

// ✅ NEW: Using role with name
await page.getByRole('menuitem', { name: '客戶管理' }).click();

// ✅ NEW: Using icon + text combination
await page.locator('li:has-text("客戶管理")').click();
```

### 2. Form Elements
```typescript
// ❌ OLD: Using data-testid
await page.fill('[data-testid="username-input"]', 'user@example.com');

// ✅ NEW: Using label association
await page.getByLabel('用戶名').fill('user@example.com');

// ✅ NEW: Using placeholder
await page.getByPlaceholder('請輸入用戶名').fill('user@example.com');
```

### 3. Buttons
```typescript
// ❌ OLD: Using data-testid
await page.click('[data-testid="login-button"]');

// ✅ NEW: Using button text
await page.getByRole('button', { name: '登 入' }).click();

// ✅ NEW: Using exact text
await page.getByText('登 入', { exact: true }).click();
```

### 4. Error Messages
```typescript
// ❌ OLD: Using data-testid
await expect(page.locator('[data-testid="error-alert"]')).toBeVisible();

// ✅ NEW: Using alert role
await expect(page.getByRole('alert')).toBeVisible();

// ✅ NEW: Using error text
await expect(page.getByText('帳號或密碼錯誤')).toBeVisible();
```

### 5. Dashboard Elements
```typescript
// ❌ OLD: Using data-testid
await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();

// ✅ NEW: Using complementary role (for sidebars)
await expect(page.getByRole('complementary')).toBeVisible();

// ✅ NEW: Using navigation role
await expect(page.getByRole('navigation')).toBeVisible();
```

## Quick Fixes for Common Tests

### Login Page Updates
```typescript
// In LoginPage.ts
export class LoginPage {
  // Update selectors
  readonly emailInput = 'input[type="text"]'; // or use getByLabel
  readonly passwordInput = 'input[type="password"]';
  readonly loginButton = 'button:has-text("登 入")';
  readonly errorMessage = '[role="alert"]';
  
  async login(email: string, password: string) {
    // Use the actual form structure
    await this.page.getByLabel('用戶名').fill(email);
    await this.page.getByLabel('密碼').fill(password);
    await this.page.getByRole('button', { name: '登 入' }).click();
  }
}
```

### Dashboard Navigation Updates
```typescript
// In DashboardPage.ts
async navigateTo(section: string) {
  const sectionNames = {
    customers: '客戶管理',
    orders: '訂單管理',
    routes: '路線規劃',
    predictions: '需求預測',
    reports: '報表分析',
    settings: '系統設定'
  };
  
  await this.page.getByRole('menuitem', { name: sectionNames[section] }).click();
  await this.page.waitForURL(new RegExp(`/${section}`));
}
```

## Testing Strategy

### Phase 1: Critical Path (Immediate)
1. Update login tests to use actual selectors
2. Fix navigation to enable customer journey tests
3. Update role-based access tests

### Phase 2: Enhanced Coverage
1. Add accessibility attributes to frontend
2. Use ARIA labels for better test stability
3. Implement visual regression tests

### Phase 3: Long-term Improvements
1. Add strategic data-testid attributes
2. Create custom test helpers
3. Implement component testing

## Benefits of Text-Based Selectors
- More resilient to UI changes
- Better represents user behavior
- Works with internationalization
- No frontend changes needed

## Example Implementation
```typescript
// Complete working example
test('should complete customer order flow', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.getByLabel('用戶名').fill('staff@luckygas.com.tw');
  await page.getByLabel('密碼').fill('Staff123!');
  await page.getByRole('button', { name: '登 入' }).click();
  
  // Wait for dashboard
  await expect(page.getByRole('heading', { name: '儀表板' })).toBeVisible();
  
  // Navigate to customers
  await page.getByRole('menuitem', { name: '客戶管理' }).click();
  
  // Continue with customer operations...
});
```