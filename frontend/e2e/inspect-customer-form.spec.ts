import { test} from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { CustomerPage } from './pages/CustomerPage';

test('inspect customer form structure', async ({ page }) => {
  const loginPage = new LoginPage(page);
  const customerPage = new CustomerPage(page);

  // Login
  await loginPage.goto();
  await loginPage.login('admin', 'admin123');
  await loginPage.waitForLoginSuccess();

  // Navigate to customers
  await customerPage.navigateToCustomers();
  
  // Open create form
  await customerPage.clickAddCustomer();
  
  // Wait for modal to be fully loaded
  await page.waitForTimeout(2000);
  
  // Get all input elements in the modal
  const inputs = await page.locator('.ant-modal-content input').all();
  console.log(`Found ${inputs.length} input elements`);
  
  for (let i = 0; i < inputs.length; i++) {
    const input = inputs[i];
    const id = await input.getAttribute('id');
    const name = await input.getAttribute('name');
    const placeholder = await input.getAttribute('placeholder');
    const type = await input.getAttribute('type');
    console.log(`Input ${i}: id="${id}", name="${name}", placeholder="${placeholder}", type="${type}"`);
  }
  
  // Get all textarea elements
  const textareas = await page.locator('.ant-modal-content textarea').all();
  console.log(`\nFound ${textareas.length} textarea elements`);
  
  for (let i = 0; i < textareas.length; i++) {
    const textarea = textareas[i];
    const id = await textarea.getAttribute('id');
    const name = await textarea.getAttribute('name');
    console.log(`Textarea ${i}: id="${id}", name="${name}"`);
  }
  
  // Take a screenshot with dev tools open
  await page.screenshot({ path: 'customer-form-inspect.png', fullPage: true });
});