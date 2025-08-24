/**
 * Iterative Test Runner
 * Orchestrates the test-fix-verify loop for comprehensive application testing
 */

import { test, Browser, BrowserContext, Page, chromium, firefox, webkit } from '@playwright/test';
import { ErrorMonitor, ErrorSeverity, CapturedError } from './ErrorMonitor';
import { AutoFixer, FixSuggestion } from './AutoFixer';
import { PerformanceMonitor } from './PerformanceMonitor';
import * as fs from 'fs';
import * as path from 'path';

export interface TestScenario {
  name: string;
  description: string;
  steps: TestStep[];
  critical: boolean;
  expectedOutcome?: string;
}

export interface TestStep {
  action: string;
  selector?: string;
  value?: string;
  waitFor?: string;
  screenshot?: boolean;
  expectation?: string;
}

export interface IterationResult {
  iteration: number;
  testsRun: number;
  testsPassed: number;
  testsFailed: number;
  errorsFound: number;
  criticalErrors: number;
  fixesApplied: number;
  performanceMetrics: any;
  duration: number;
  improved: boolean;
}

export interface TestReport {
  sessionId: string;
  startTime: Date;
  endTime: Date;
  iterations: IterationResult[];
  totalErrors: number;
  totalFixes: number;
  finalStatus: 'success' | 'partial' | 'failed';
  recommendations: string[];
  browserResults: Map<string, any>;
}

export class IterativeTestRunner {
  private errorMonitor: ErrorMonitor | null = null;
  private autoFixer: AutoFixer;
  private performanceMonitor: PerformanceMonitor | null = null;
  private iterations: IterationResult[] = [];
  private sessionId: string;
  private maxIterations: number;
  private targetErrorThreshold: number;
  private browsers: string[] = ['chromium', 'firefox', 'webkit'];
  private testScenarios: TestScenario[] = [];

  constructor(
    maxIterations: number = 5,
    targetErrorThreshold: number = 0
  ) {
    this.maxIterations = maxIterations;
    this.targetErrorThreshold = targetErrorThreshold;
    this.sessionId = `test_${Date.now()}`;
    this.autoFixer = new AutoFixer();
    this.initializeTestScenarios();
  }

  /**
   * Initialize comprehensive test scenarios
   */
  private initializeTestScenarios(): void {
    this.testScenarios = [
      // Critical Path: Login Flow
      {
        name: 'login_flow',
        description: 'User authentication and session management',
        critical: true,
        steps: [
          { action: 'navigate', value: '/login' },
          { action: 'fill', selector: 'input[name="username"]', value: 'admin@luckygas.com' },
          { action: 'fill', selector: 'input[name="password"]', value: 'admin123' },
          { action: 'click', selector: 'button[type="submit"]' },
          { action: 'waitFor', waitFor: 'navigation' },
          { expectation: 'url.includes("/dashboard")' },
          { screenshot: true },
        ],
      },
      
      // Critical Path: Dashboard Loading
      {
        name: 'dashboard_load',
        description: 'Dashboard components and data loading',
        critical: true,
        steps: [
          { action: 'navigate', value: '/dashboard' },
          { action: 'waitFor', selector: '.statistics-card' },
          { action: 'waitFor', selector: '.recent-orders-table' },
          { expectation: 'visible(".total-orders")' },
          { expectation: 'visible(".pending-orders")' },
          { expectation: 'visible(".active-drivers")' },
          { screenshot: true },
        ],
      },
      
      // Order Management
      {
        name: 'order_management',
        description: 'Order CRUD operations',
        critical: true,
        steps: [
          { action: 'navigate', value: '/orders' },
          { action: 'click', selector: 'button.new-order' },
          { action: 'fill', selector: 'input[name="customer"]', value: '王小明' },
          { action: 'fill', selector: 'input[name="quantity"]', value: '2' },
          { action: 'select', selector: 'select[name="product"]', value: '20kg' },
          { action: 'click', selector: 'button.submit-order' },
          { expectation: 'visible(".success-message")' },
          { screenshot: true },
        ],
      },
      
      // Customer Search
      {
        name: 'customer_search',
        description: 'Customer search functionality',
        critical: false,
        steps: [
          { action: 'navigate', value: '/customers' },
          { action: 'fill', selector: 'input.search', value: '王' },
          { action: 'wait', value: '1000' }, // Wait for debounce
          { expectation: 'count(".customer-row") > 0' },
          { action: 'fill', selector: 'input.search', value: '0912' },
          { action: 'wait', value: '1000' },
          { expectation: 'count(".customer-row") > 0' },
        ],
      },
      
      // Route Planning
      {
        name: 'route_planning',
        description: 'Route optimization and map display',
        critical: true,
        steps: [
          { action: 'navigate', value: '/routes' },
          { action: 'waitFor', selector: '#map' },
          { action: 'click', selector: 'button.optimize-routes' },
          { action: 'waitFor', selector: '.optimization-complete' },
          { expectation: 'visible(".route-marker")' },
          { screenshot: true },
        ],
      },
      
      // Mobile Responsiveness
      {
        name: 'mobile_responsive',
        description: 'Mobile view functionality',
        critical: false,
        steps: [
          { action: 'setViewport', value: '375,667' }, // iPhone size
          { action: 'navigate', value: '/dashboard' },
          { expectation: 'visible(".mobile-menu-toggle")' },
          { action: 'click', selector: '.mobile-menu-toggle' },
          { expectation: 'visible(".mobile-navigation")' },
          { screenshot: true },
        ],
      },
      
      // WebSocket Real-time Updates
      {
        name: 'websocket_updates',
        description: 'Real-time data synchronization',
        critical: false,
        steps: [
          { action: 'navigate', value: '/dashboard' },
          { action: 'evaluate', value: 'window.testWebSocket = true' },
          { action: 'wait', value: '5000' }, // Wait for WebSocket connection
          { expectation: 'evaluate("window.wsConnected === true")' },
        ],
      },
      
      // Error Recovery
      {
        name: 'error_recovery',
        description: 'Application error handling',
        critical: true,
        steps: [
          { action: 'navigate', value: '/dashboard' },
          { action: 'evaluate', value: 'throw new Error("Test error")' },
          { action: 'wait', value: '1000' },
          { expectation: 'not(".white-screen-of-death")' },
          { expectation: 'visible(".error-boundary-message")' },
        ],
      },
      
      // Performance Test
      {
        name: 'performance_test',
        description: 'Page load performance',
        critical: false,
        steps: [
          { action: 'navigate', value: '/dashboard' },
          { action: 'evaluate', value: 'performance.mark("dashboard-start")' },
          { action: 'waitFor', selector: '.dashboard-loaded' },
          { action: 'evaluate', value: 'performance.mark("dashboard-end")' },
          { expectation: 'evaluate("performance.measure(\'dashboard-load\', \'dashboard-start\', \'dashboard-end\').duration < 3000")' },
        ],
      },
      
      // Data Export
      {
        name: 'data_export',
        description: 'Excel export functionality',
        critical: false,
        steps: [
          { action: 'navigate', value: '/orders' },
          { action: 'click', selector: 'button.export-excel' },
          { action: 'wait', value: '2000' },
          { expectation: 'download(".xlsx")' },
        ],
      },
    ];
  }

  /**
   * Main execution loop
   */
  public async run(): Promise<TestReport> {
    const report: TestReport = {
      sessionId: this.sessionId,
      startTime: new Date(),
      endTime: new Date(),
      iterations: [],
      totalErrors: 0,
      totalFixes: 0,
      finalStatus: 'failed',
      recommendations: [],
      browserResults: new Map(),
    };

    console.log(`🚀 Starting Iterative Test Runner - Session: ${this.sessionId}`);
    console.log(`Configuration: Max Iterations: ${this.maxIterations}, Error Threshold: ${this.targetErrorThreshold}`);

    for (let iteration = 1; iteration <= this.maxIterations; iteration++) {
      console.log(`\n📍 Iteration ${iteration}/${this.maxIterations}`);
      
      const iterationResult = await this.runIteration(iteration);
      this.iterations.push(iterationResult);
      report.iterations.push(iterationResult);
      report.totalErrors += iterationResult.errorsFound;
      report.totalFixes += iterationResult.fixesApplied;

      // Check if we've reached our goal
      if (iterationResult.criticalErrors <= this.targetErrorThreshold) {
        console.log(`✅ Target error threshold reached! Critical errors: ${iterationResult.criticalErrors}`);
        report.finalStatus = 'success';
        break;
      }

      // Check if we're making progress
      if (iteration > 1) {
        const previousIteration = this.iterations[iteration - 2];
        if (iterationResult.criticalErrors >= previousIteration.criticalErrors) {
          console.log(`⚠️ No improvement detected. Critical errors: ${iterationResult.criticalErrors}`);
          if (iteration >= 3) {
            console.log(`🛑 Stopping after ${iteration} iterations - no progress`);
            break;
          }
        }
      }
    }

    // Generate final report
    report.endTime = new Date();
    report.recommendations = this.generateRecommendations(report);
    
    if (report.totalErrors > 0 && report.totalFixes > report.totalErrors * 0.5) {
      report.finalStatus = 'partial';
    }

    await this.saveReport(report);
    return report;
  }

  /**
   * Run a single iteration of tests
   */
  private async runIteration(iterationNumber: number): Promise<IterationResult> {
    const startTime = Date.now();
    const result: IterationResult = {
      iteration: iterationNumber,
      testsRun: 0,
      testsPassed: 0,
      testsFailed: 0,
      errorsFound: 0,
      criticalErrors: 0,
      fixesApplied: 0,
      performanceMetrics: {},
      duration: 0,
      improved: false,
    };

    // Run tests across all browsers
    for (const browserType of this.browsers) {
      console.log(`\n🌐 Testing on ${browserType}`);
      
      const browser = await this.launchBrowser(browserType);
      const context = await browser.newContext({
        locale: 'zh-TW',
        timezoneId: 'Asia/Taipei',
      });
      const page = await context.newPage();

      // Initialize monitors
      this.errorMonitor = new ErrorMonitor(page);
      this.performanceMonitor = new PerformanceMonitor(page);

      // Run test scenarios
      for (const scenario of this.testScenarios) {
        if (!scenario.critical && iterationNumber > 1) {
          // Skip non-critical tests in later iterations for speed
          continue;
        }

        console.log(`  📝 Running: ${scenario.name}`);
        result.testsRun++;

        try {
          await this.runTestScenario(page, scenario);
          result.testsPassed++;
          console.log(`    ✅ Passed`);
        } catch (error) {
          result.testsFailed++;
          console.log(`    ❌ Failed: ${error.message}`);
        }
      }

      // Collect errors and performance metrics
      const errors = this.errorMonitor.getErrors();
      const criticalErrors = this.errorMonitor.getCriticalErrors();
      const performanceData = await this.performanceMonitor.getMetrics();

      result.errorsFound += errors.length;
      result.criticalErrors += criticalErrors.length;
      result.performanceMetrics[browserType] = performanceData;

      // Generate and apply fixes if errors found
      if (errors.length > 0 && iterationNumber < this.maxIterations) {
        console.log(`\n🔧 Generating fixes for ${errors.length} errors...`);
        const fixes = this.autoFixer.generateFixes(errors);
        
        if (fixes.length > 0) {
          console.log(`  📝 Generated ${fixes.length} fix suggestions`);
          const fixResult = await this.autoFixer.applyFixes(fixes);
          result.fixesApplied += fixResult.fixesApplied.length;
          console.log(`  ✅ Applied ${fixResult.fixesApplied.length} fixes`);
        }
      }

      // Generate error report
      if (errors.length > 0) {
        const errorReport = this.errorMonitor.generateReport();
        await this.saveErrorReport(iterationNumber, browserType, errorReport);
      }

      await context.close();
      await browser.close();
    }

    result.duration = Date.now() - startTime;
    
    // Check if this iteration improved
    if (iterationNumber > 1) {
      const previous = this.iterations[iterationNumber - 2];
      result.improved = result.criticalErrors < previous.criticalErrors;
    }

    return result;
  }

  /**
   * Run a specific test scenario
   */
  private async runTestScenario(page: Page, scenario: TestScenario): Promise<void> {
    this.errorMonitor?.setUserAction(scenario.name);

    for (const step of scenario.steps) {
      await this.executeTestStep(page, step);
    }
  }

  /**
   * Execute a single test step
   */
  private async executeTestStep(page: Page, step: TestStep): Promise<void> {
    switch (step.action) {
      case 'navigate':
        await page.goto(step.value!, { waitUntil: 'networkidle' });
        break;
      
      case 'click':
        await page.click(step.selector!);
        break;
      
      case 'fill':
        await page.fill(step.selector!, step.value!);
        break;
      
      case 'select':
        await page.selectOption(step.selector!, step.value!);
        break;
      
      case 'waitFor':
        if (step.selector) {
          await page.waitForSelector(step.selector, { timeout: 10000 });
        } else if (step.waitFor === 'navigation') {
          await page.waitForLoadState('networkidle');
        }
        break;
      
      case 'wait':
        await page.waitForTimeout(parseInt(step.value!));
        break;
      
      case 'evaluate':
        await page.evaluate(step.value!);
        break;
      
      case 'setViewport':
        const [width, height] = step.value!.split(',').map(Number);
        await page.setViewportSize({ width, height });
        break;
      
      case 'screenshot':
        if (step.screenshot) {
          await page.screenshot({ 
            path: `screenshots/${this.sessionId}_${Date.now()}.png`,
            fullPage: true,
          });
        }
        break;
    }

    // Check expectation if provided
    if (step.expectation) {
      await this.checkExpectation(page, step.expectation);
    }
  }

  /**
   * Check test expectation
   */
  private async checkExpectation(page: Page, expectation: string): Promise<void> {
    if (expectation.startsWith('visible(')) {
      const selector = expectation.match(/visible\("(.+)"\)/)?.[1];
      if (selector) {
        await page.waitForSelector(selector, { state: 'visible', timeout: 5000 });
      }
    } else if (expectation.startsWith('count(')) {
      const match = expectation.match(/count\("(.+)"\) ([><=]+) (\d+)/);
      if (match) {
        const [, selector, operator, count] = match;
        const elements = await page.$$(selector);
        const actualCount = elements.length;
        const expectedCount = parseInt(count);
        
        switch (operator) {
          case '>':
            if (actualCount <= expectedCount) {
              throw new Error(`Expected count > ${expectedCount}, got ${actualCount}`);
            }
            break;
          case '>=':
            if (actualCount < expectedCount) {
              throw new Error(`Expected count >= ${expectedCount}, got ${actualCount}`);
            }
            break;
          case '=':
          case '==':
            if (actualCount !== expectedCount) {
              throw new Error(`Expected count = ${expectedCount}, got ${actualCount}`);
            }
            break;
        }
      }
    } else if (expectation.startsWith('url.includes(')) {
      const expected = expectation.match(/url\.includes\("(.+)"\)/)?.[1];
      if (expected && !page.url().includes(expected)) {
        throw new Error(`URL does not include "${expected}"`);
      }
    } else if (expectation.startsWith('evaluate(')) {
      const code = expectation.match(/evaluate\("(.+)"\)/)?.[1];
      if (code) {
        const result = await page.evaluate(code);
        if (!result) {
          throw new Error(`Evaluation failed: ${code}`);
        }
      }
    }
  }

  /**
   * Launch browser based on type
   */
  private async launchBrowser(browserType: string): Promise<Browser> {
    const options = {
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    };

    switch (browserType) {
      case 'firefox':
        return await firefox.launch(options);
      case 'webkit':
        return await webkit.launch(options);
      default:
        return await chromium.launch(options);
    }
  }

  /**
   * Generate recommendations based on test results
   */
  private generateRecommendations(report: TestReport): string[] {
    const recommendations: string[] = [];

    // Analyze error patterns
    const errorCategories = new Map<string, number>();
    report.iterations.forEach(iteration => {
      // Count errors by category (simplified for this example)
      if (iteration.criticalErrors > 0) {
        errorCategories.set('critical', (errorCategories.get('critical') || 0) + iteration.criticalErrors);
      }
    });

    // Generate recommendations
    if (errorCategories.get('critical')) {
      recommendations.push('🔴 Critical errors detected - immediate attention required');
      recommendations.push('Review error logs and apply suggested fixes');
    }

    // Performance recommendations
    report.iterations.forEach(iteration => {
      Object.entries(iteration.performanceMetrics).forEach(([browser, metrics]: [string, any]) => {
        if (metrics?.loadTime > 3000) {
          recommendations.push(`⚡ Optimize load time for ${browser} (current: ${metrics.loadTime}ms)`);
        }
        if (metrics?.memoryUsage > 100 * 1024 * 1024) {
          recommendations.push(`💾 High memory usage in ${browser}: ${(metrics.memoryUsage / 1024 / 1024).toFixed(2)}MB`);
        }
      });
    });

    // Test coverage recommendations
    const avgPassRate = report.iterations.reduce((sum, i) => sum + (i.testsPassed / i.testsRun), 0) / report.iterations.length;
    if (avgPassRate < 0.8) {
      recommendations.push(`📊 Low test pass rate (${(avgPassRate * 100).toFixed(0)}%) - review failing tests`);
    }

    // Fix effectiveness
    if (report.totalFixes > 0) {
      const fixEffectiveness = report.iterations[report.iterations.length - 1].criticalErrors === 0 ? 'High' : 'Low';
      recommendations.push(`🔧 Fix effectiveness: ${fixEffectiveness} (${report.totalFixes} fixes applied)`);
    }

    return recommendations;
  }

  /**
   * Save test report to file
   */
  private async saveReport(report: TestReport): Promise<void> {
    const reportPath = path.join('test-results', `report_${this.sessionId}.json`);
    
    // Ensure directory exists
    if (!fs.existsSync('test-results')) {
      fs.mkdirSync('test-results', { recursive: true });
    }

    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n📄 Report saved to: ${reportPath}`);

    // Generate markdown report
    const markdownReport = this.generateMarkdownReport(report);
    const mdPath = path.join('test-results', `report_${this.sessionId}.md`);
    fs.writeFileSync(mdPath, markdownReport);
    console.log(`📄 Markdown report saved to: ${mdPath}`);
  }

  /**
   * Save error report
   */
  private async saveErrorReport(iteration: number, browser: string, report: string): Promise<void> {
    const errorPath = path.join('test-results', `errors_${this.sessionId}_${iteration}_${browser}.md`);
    
    if (!fs.existsSync('test-results')) {
      fs.mkdirSync('test-results', { recursive: true });
    }

    fs.writeFileSync(errorPath, report);
  }

  /**
   * Generate markdown report
   */
  private generateMarkdownReport(report: TestReport): string {
    const duration = (report.endTime.getTime() - report.startTime.getTime()) / 1000;
    
    return `
# Iterative Test Report

**Session ID**: ${report.sessionId}  
**Duration**: ${duration.toFixed(2)} seconds  
**Status**: ${report.finalStatus.toUpperCase()}  
**Total Errors Found**: ${report.totalErrors}  
**Total Fixes Applied**: ${report.totalFixes}  

## Iterations Summary

| Iteration | Tests Run | Passed | Failed | Errors | Critical | Fixes | Duration | Improved |
|-----------|-----------|--------|--------|--------|----------|-------|----------|----------|
${report.iterations.map(i => 
  `| ${i.iteration} | ${i.testsRun} | ${i.testsPassed} | ${i.testsFailed} | ${i.errorsFound} | ${i.criticalErrors} | ${i.fixesApplied} | ${(i.duration/1000).toFixed(2)}s | ${i.improved ? '✅' : '❌'} |`
).join('\n')}

## Performance Metrics

${Object.entries(report.iterations[0]?.performanceMetrics || {}).map(([browser, metrics]: [string, any]) => `
### ${browser}
- Load Time: ${metrics?.loadTime || 'N/A'}ms
- Memory Usage: ${metrics?.memoryUsage ? (metrics.memoryUsage / 1024 / 1024).toFixed(2) + 'MB' : 'N/A'}
- DOM Nodes: ${metrics?.domNodes || 'N/A'}
`).join('\n')}

## Recommendations

${report.recommendations.map(r => `- ${r}`).join('\n')}

## Test Scenarios

${this.testScenarios.map(s => `
### ${s.name}
- **Description**: ${s.description}
- **Critical**: ${s.critical ? 'Yes' : 'No'}
- **Steps**: ${s.steps.length}
`).join('\n')}

---
*Generated: ${new Date().toISOString()}*
`;
  }
}