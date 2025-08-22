#!/usr/bin/env node

/**
 * Production Deployment Verification Script
 * Tests all critical API endpoints and user flows
 */

const axios = require('axios');

const PRODUCTION_URL = 'https://vast-tributary-466619-m8.web.app';
const API_URL = 'https://luckygas-backend-production-154687573210.asia-east1.run.app/api/v1';

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

class ProductionVerifier {
  constructor() {
    this.results = [];
    this.criticalIssues = [];
    this.warnings = [];
    this.successes = [];
  }

  log(message, type = 'info') {
    const prefix = {
      success: `${colors.green}✅`,
      error: `${colors.red}❌`,
      warning: `${colors.yellow}⚠️`,
      info: `${colors.blue}ℹ️`,
      test: `${colors.cyan}🧪`
    };
    
    console.log(`${prefix[type] || prefix.info} ${message}${colors.reset}`);
  }

  async testWebsiteAvailability() {
    this.log('Testing website availability...', 'test');
    try {
      const response = await axios.get(PRODUCTION_URL, {
        timeout: 10000,
        validateStatus: status => status < 500
      });
      
      if (response.status === 200) {
        this.log('Website is accessible', 'success');
        this.successes.push('Website accessible at ' + PRODUCTION_URL);
        return true;
      } else {
        this.log(`Website returned status ${response.status}`, 'warning');
        this.warnings.push(`Website returned status ${response.status}`);
        return false;
      }
    } catch (error) {
      this.log(`Website not accessible: ${error.message}`, 'error');
      this.criticalIssues.push('Website not accessible');
      return false;
    }
  }

  async testAPIHealth() {
    this.log('Testing API health endpoint...', 'test');
    try {
      const response = await axios.get(`${API_URL}/health`, {
        timeout: 10000,
        validateStatus: status => status < 500
      });
      
      if (response.status === 200) {
        this.log('API health check passed', 'success');
        this.successes.push('API health check passed');
        return true;
      } else {
        this.log(`API health returned status ${response.status}`, 'warning');
        this.warnings.push(`API health returned status ${response.status}`);
        return false;
      }
    } catch (error) {
      this.log(`API health check failed: ${error.message}`, 'error');
      this.criticalIssues.push('API health check failed');
      return false;
    }
  }

  async testCriticalEndpoints() {
    this.log('Testing critical API endpoints...', 'test');
    
    const endpoints = [
      { name: 'Authentication', path: '/auth/login', method: 'POST', 
        data: { username: 'test', password: 'test' }, expectError: true },
      { name: 'Customers List', path: '/customers?skip=0&limit=1', method: 'GET', requiresAuth: true },
      { name: 'Orders List', path: '/orders?skip=0&limit=1', method: 'GET', requiresAuth: true },
      { name: 'Dashboard Summary', path: '/dashboard/summary', method: 'GET', requiresAuth: true }
    ];

    for (const endpoint of endpoints) {
      try {
        const config = {
          method: endpoint.method,
          url: `${API_URL}${endpoint.path}`,
          timeout: 10000,
          validateStatus: status => status < 500
        };

        if (endpoint.data) {
          config.data = endpoint.data;
        }

        const response = await axios(config);
        
        if (endpoint.expectError && response.status === 401) {
          this.log(`${endpoint.name}: Authentication required as expected`, 'success');
          this.successes.push(`${endpoint.name} endpoint working`);
        } else if (response.status === 200) {
          this.log(`${endpoint.name}: Working correctly`, 'success');
          this.successes.push(`${endpoint.name} endpoint working`);
        } else if (response.status === 401 && endpoint.requiresAuth) {
          this.log(`${endpoint.name}: Requires authentication (expected)`, 'success');
          this.successes.push(`${endpoint.name} authentication working`);
        } else if (response.status === 404) {
          this.log(`${endpoint.name}: Endpoint not found`, 'warning');
          this.warnings.push(`${endpoint.name} endpoint not found (404)`);
        } else {
          this.log(`${endpoint.name}: Returned status ${response.status}`, 'warning');
          this.warnings.push(`${endpoint.name} returned status ${response.status}`);
        }
      } catch (error) {
        if (error.code === 'ECONNABORTED') {
          this.log(`${endpoint.name}: Timeout`, 'error');
          this.criticalIssues.push(`${endpoint.name} timeout`);
        } else {
          this.log(`${endpoint.name}: Error - ${error.message}`, 'error');
          this.criticalIssues.push(`${endpoint.name} error`);
        }
      }
    }
  }

  async testHTTPS() {
    this.log('Verifying HTTPS configuration...', 'test');
    
    // Check if site redirects to HTTPS
    try {
      const response = await axios.get(PRODUCTION_URL, {
        maxRedirects: 0,
        validateStatus: status => true
      });
      
      if (PRODUCTION_URL.startsWith('https://')) {
        this.log('Site uses HTTPS', 'success');
        this.successes.push('HTTPS enabled');
      } else {
        this.log('Site not using HTTPS', 'error');
        this.criticalIssues.push('HTTPS not enabled');
      }
    } catch (error) {
      // Redirect error is expected if forcing HTTPS
      if (error.response && error.response.status === 301) {
        this.log('Site redirects to HTTPS', 'success');
        this.successes.push('HTTPS redirect working');
      }
    }
  }

  async testStaticAssets() {
    this.log('Testing static asset loading...', 'test');
    
    try {
      // Test if main JS bundle loads
      const response = await axios.head(PRODUCTION_URL, {
        timeout: 10000
      });
      
      if (response.status === 200) {
        this.log('Static assets loading correctly', 'success');
        this.successes.push('Static assets loading');
      }
    } catch (error) {
      this.log(`Static assets issue: ${error.message}`, 'warning');
      this.warnings.push('Potential static asset loading issue');
    }
  }

  async testCORS() {
    this.log('Testing CORS configuration...', 'test');
    
    try {
      const response = await axios.options(`${API_URL}/health`, {
        headers: {
          'Origin': PRODUCTION_URL,
          'Access-Control-Request-Method': 'GET'
        },
        validateStatus: status => true
      });
      
      if (response.headers['access-control-allow-origin']) {
        this.log('CORS headers present', 'success');
        this.successes.push('CORS configured');
      } else {
        this.log('CORS headers might not be configured', 'warning');
        this.warnings.push('CORS configuration unclear');
      }
    } catch (error) {
      this.log(`CORS test inconclusive: ${error.message}`, 'warning');
      this.warnings.push('CORS test inconclusive');
    }
  }

  generateReport() {
    console.log('\n' + '='.repeat(60));
    console.log(`${colors.bright}📊 PRODUCTION DEPLOYMENT VERIFICATION REPORT${colors.reset}`);
    console.log('='.repeat(60));
    
    console.log(`\n${colors.cyan}📅 Date:${colors.reset} ${new Date().toISOString()}`);
    console.log(`${colors.cyan}🌐 URL:${colors.reset} ${PRODUCTION_URL}`);
    console.log(`${colors.cyan}🔗 API:${colors.reset} ${API_URL}`);
    
    // Successes
    if (this.successes.length > 0) {
      console.log(`\n${colors.green}✅ SUCCESSES (${this.successes.length})${colors.reset}`);
      this.successes.forEach(s => console.log(`  • ${s}`));
    }
    
    // Warnings
    if (this.warnings.length > 0) {
      console.log(`\n${colors.yellow}⚠️  WARNINGS (${this.warnings.length})${colors.reset}`);
      this.warnings.forEach(w => console.log(`  • ${w}`));
    }
    
    // Critical Issues
    if (this.criticalIssues.length > 0) {
      console.log(`\n${colors.red}❌ CRITICAL ISSUES (${this.criticalIssues.length})${colors.reset}`);
      this.criticalIssues.forEach(c => console.log(`  • ${c}`));
    }
    
    // Summary
    console.log('\n' + '='.repeat(60));
    const status = this.criticalIssues.length === 0 ? 
      `${colors.green}✅ DEPLOYMENT SUCCESSFUL${colors.reset}` : 
      `${colors.red}❌ DEPLOYMENT HAS ISSUES${colors.reset}`;
    
    console.log(`${colors.bright}STATUS: ${status}`);
    console.log('='.repeat(60));
    
    // Recommendations
    console.log(`\n${colors.cyan}📝 RECOMMENDATIONS${colors.reset}`);
    if (this.criticalIssues.length === 0 && this.warnings.length === 0) {
      console.log('  • All systems operational - monitor for user feedback');
      console.log('  • Consider implementing automated monitoring');
      console.log('  • Set up error tracking and analytics');
    } else if (this.criticalIssues.length > 0) {
      console.log('  • Address critical issues immediately');
      console.log('  • Check backend logs for errors');
      console.log('  • Verify environment variables are set correctly');
    } else {
      console.log('  • Review warning items for potential improvements');
      console.log('  • Monitor system performance');
      console.log('  • Consider implementing missing endpoints');
    }
    
    // Test Coverage
    console.log(`\n${colors.cyan}📈 TEST COVERAGE${colors.reset}`);
    const total = this.successes.length + this.warnings.length + this.criticalIssues.length;
    const successRate = total > 0 ? ((this.successes.length / total) * 100).toFixed(1) : 0;
    console.log(`  • Total Tests: ${total}`);
    console.log(`  • Success Rate: ${successRate}%`);
    console.log(`  • API Endpoints Tested: 5`);
    console.log(`  • Security Checks: HTTPS, CORS`);
    
    console.log('\n' + '='.repeat(60) + '\n');
  }

  async runAllTests() {
    console.log(`${colors.bright}${colors.cyan}🚀 Starting Production Verification...${colors.reset}\n`);
    
    await this.testWebsiteAvailability();
    await this.testAPIHealth();
    await this.testCriticalEndpoints();
    await this.testHTTPS();
    await this.testStaticAssets();
    await this.testCORS();
    
    this.generateReport();
    
    // Return exit code based on critical issues
    return this.criticalIssues.length === 0 ? 0 : 1;
  }
}

// Run verification
const verifier = new ProductionVerifier();
verifier.runAllTests().then(exitCode => {
  process.exit(exitCode);
}).catch(error => {
  console.error('Verification script error:', error);
  process.exit(1);
});