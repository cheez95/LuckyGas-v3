import { chromium, FullConfig } from '@playwright/test';
import { APIHelper } from './api-helper';
import testData from '../fixtures/test-data.json';
import users from '../fixtures/users.json';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global test setup...');
  
  // Create browser context for setup
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  const request = context.request;
  
  // Initialize API helper
  const apiHelper = new APIHelper(request);
  
  // Wait for services to be ready
  console.log('⏳ Waiting for services to be ready...');
  let retries = 30;
  while (retries > 0) {
    const isHealthy = await apiHelper.healthCheck();
    if (isHealthy) {
      console.log('✅ Backend service is ready');
      break;
    }
    retries--;
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  if (retries === 0) {
    throw new Error('Backend service failed to start');
  }
  
  // Check frontend service
  try {
    await page.goto('http://localhost:3001', { timeout: 30000 });
    console.log('✅ Frontend service is ready');
  } catch (error) {
    console.error('❌ Frontend service failed to start:', error);
    throw error;
  }
  
  // Login as admin to set up test data
  console.log('🔐 Logging in as admin...');
  await apiHelper.login('admin');
  
  // Create test users if they don't exist
  console.log('👥 Setting up test users...');
  for (const [key, user] of Object.entries(users)) {
    if (key !== 'admin' && key !== 'invalidUser') {
      try {
        await apiHelper.post('/api/v1/users/', {
          username: user.username,
          password: user.password,
          full_name: user.fullName,
          role: user.role,
          is_active: true
        });
        console.log(`✅ Created user: ${user.username}`);
      } catch (error: any) {
        if (error.message.includes('already exists')) {
          console.log(`ℹ️ User ${user.username} already exists`);
        } else {
          console.error(`❌ Failed to create user ${user.username}:`, error);
        }
      }
    }
  }
  
  // Create test customers
  console.log('🏢 Setting up test customers...');
  for (const customer of testData.customers) {
    try {
      await apiHelper.createCustomer(customer);
      console.log(`✅ Created customer: ${customer.簡稱}`);
    } catch (error: any) {
      if (error.message.includes('already exists')) {
        console.log(`ℹ️ Customer ${customer.簡稱} already exists`);
      } else {
        console.error(`❌ Failed to create customer ${customer.簡稱}:`, error);
      }
    }
  }
  
  // Store auth tokens for different user roles
  const authTokens: Record<string, string> = {};
  for (const [key, user] of Object.entries(users)) {
    if (key !== 'invalidUser') {
      try {
        const token = await apiHelper.login(key as keyof typeof users);
        authTokens[key] = token;
      } catch (error) {
        console.error(`❌ Failed to get token for ${key}:`, error);
      }
    }
  }
  
  // Save auth tokens for use in tests
  process.env.AUTH_TOKENS = JSON.stringify(authTokens);
  
  await browser.close();
  console.log('✅ Global setup completed successfully');
}

export default globalSetup;