/**
 * API Test Utility
 * Tests all API endpoints and reports any errors
 */

import apiFixesService from '../services/api-fixes.service';
import api from '../services/api';
import { apiClient } from '../services/api.service';
import moment from 'moment';

interface TestResult {
  endpoint: string;
  status: 'success' | 'error' | 'warning';
  message: string;
  responseTime?: number;
  error?: any;
}

export class ApiTester {
  private results: TestResult[] = [];

  /**
   * Run all API tests
   */
  async runAllTests(): Promise<TestResult[]> {
    console.log('🧪 Starting API tests...');
    this.results = [];

    // Test health endpoint
    await this.testEndpoint('Health Check', '/health', async () => {
      return await apiFixesService.healthCheck();
    });

    // Test customer statistics with dates
    await this.testEndpoint('Customer Statistics', '/customers/statistics', async () => {
      return await apiFixesService.getCustomerStatistics();
    });

    // Test order search with proper params
    await this.testEndpoint('Order Search', '/orders/search', async () => {
      return await apiFixesService.searchOrders('', 'all');
    });

    // Test deliveries endpoint
    await this.testEndpoint('Deliveries', '/deliveries', async () => {
      return await apiFixesService.getDeliveries();
    });

    // Test delivery stats
    await this.testEndpoint('Delivery Stats', '/deliveries/stats', async () => {
      return await apiFixesService.getDeliveryStats();
    });

    // Test authentication endpoint
    await this.testEndpoint('Auth Check', '/api/v1/auth/me', async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No auth token found');
      }
      return await api.get('/auth/me');
    });

    // Test customers endpoint
    await this.testEndpoint('Customers List', '/customers', async () => {
      return await api.get('/customers', { 
        params: { 
          skip: 0, 
          limit: 10 
        } 
      });
    });

    // Test orders endpoint
    await this.testEndpoint('Orders List', '/orders', async () => {
      return await api.get('/orders', { 
        params: { 
          skip: 0, 
          limit: 10 
        } 
      });
    });

    // Test dashboard summary
    await this.testEndpoint('Dashboard Summary', '/dashboard/summary', async () => {
      return await apiClient.get('/dashboard/summary');
    });

    this.printResults();
    return this.results;
  }

  /**
   * Test a single endpoint
   */
  private async testEndpoint(
    name: string, 
    endpoint: string, 
    testFunction: () => Promise<any>
  ): Promise<void> {
    const startTime = Date.now();
    
    try {
      const result = await testFunction();
      const responseTime = Date.now() - startTime;
      
      this.results.push({
        endpoint: name,
        status: 'success',
        message: `✅ ${name} working (${responseTime}ms)`,
        responseTime
      });
    } catch (error: any) {
      const responseTime = Date.now() - startTime;
      const status = error.response?.status;
      
      if (status === 404) {
        this.results.push({
          endpoint: name,
          status: 'warning',
          message: `⚠️ ${name} - Endpoint not found (404)`,
          responseTime,
          error: error.response?.data
        });
      } else if (status === 401) {
        this.results.push({
          endpoint: name,
          status: 'warning',
          message: `⚠️ ${name} - Authentication required (401)`,
          responseTime,
          error: error.response?.data
        });
      } else if (status === 422) {
        this.results.push({
          endpoint: name,
          status: 'error',
          message: `❌ ${name} - Validation error (422): ${JSON.stringify(error.response?.data?.detail)}`,
          responseTime,
          error: error.response?.data
        });
      } else if (status === 500) {
        this.results.push({
          endpoint: name,
          status: 'error',
          message: `❌ ${name} - Server error (500)`,
          responseTime,
          error: error.response?.data
        });
      } else {
        this.results.push({
          endpoint: name,
          status: 'error',
          message: `❌ ${name} - ${error.message}`,
          responseTime,
          error: error
        });
      }
    }
  }

  /**
   * Print test results to console
   */
  private printResults(): void {
    console.log('\n📊 API Test Results\n' + '='.repeat(50));
    
    const successCount = this.results.filter(r => r.status === 'success').length;
    const warningCount = this.results.filter(r => r.status === 'warning').length;
    const errorCount = this.results.filter(r => r.status === 'error').length;
    
    this.results.forEach(result => {
      console.log(result.message);
      if (result.error && result.status === 'error') {
        console.error('  Error details:', result.error);
      }
    });
    
    console.log('\n' + '='.repeat(50));
    console.log(`Summary: ${successCount} passed, ${warningCount} warnings, ${errorCount} errors`);
    
    if (errorCount === 0) {
      console.log('✅ All critical endpoints are working!');
    } else {
      console.log('❌ Some endpoints have errors that need fixing');
    }
  }
}

// Export singleton instance
export const apiTester = new ApiTester();

// Auto-run tests in development
if (import.meta.env.DEV) {
  // Run tests after a delay to allow app initialization
  setTimeout(() => {
    console.log('Running API tests in development mode...');
    apiTester.runAllTests().then(results => {
      // Store results globally for debugging
      (window as any).__API_TEST_RESULTS__ = results;
      console.log('Test results stored in window.__API_TEST_RESULTS__');
    });
  }, 3000);
}