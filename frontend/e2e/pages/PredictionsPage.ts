import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class PredictionsPage extends BasePage {
  readonly pageTitle: Locator;
  readonly generateButton: Locator;
  readonly predictionsList: Locator;
  readonly predictionCards: Locator;
  readonly loadingSpinner: Locator;
  readonly errorAlert: Locator;
  readonly dateFilter: Locator;
  readonly customerFilter: Locator;
  readonly exportButton: Locator;
  readonly refreshButton: Locator;
  readonly confidenceIndicator: Locator;
  readonly demandChart: Locator;
  readonly placeholderNotice: Locator;

  constructor(page: Page) {
    super(page);
    this.pageTitle = page.locator('[data-testid="predictions-title"]');
    this.generateButton = page.locator('[data-testid="generate-predictions-btn"]');
    this.predictionsList = page.locator('[data-testid="predictions-list"]');
    this.predictionCards = page.locator('[data-testid="prediction-card"]');
    this.loadingSpinner = page.locator('[data-testid="loading-spinner"]');
    this.errorAlert = page.locator('[data-testid="error-alert"]');
    this.dateFilter = page.locator('[data-testid="date-filter"]');
    this.customerFilter = page.locator('[data-testid="customer-filter"]');
    this.exportButton = page.locator('[data-testid="export-predictions-btn"]');
    this.refreshButton = page.locator('[data-testid="refresh-predictions-btn"]');
    this.confidenceIndicator = page.locator('[data-testid="confidence-indicator"]');
    this.demandChart = page.locator('[data-testid="demand-chart"]');
    this.placeholderNotice = page.locator('[data-testid="placeholder-notice"]');
  }

  async navigateToPredictions() {
    await this.navigateTo('/predictions');
  }

  async generatePredictions() {
    await this.generateButton.click();
    
    // Wait for loading to complete
    await this.loadingSpinner.waitFor({ state: 'visible' });
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 30000 });
  }

  async getPredictionCount(): Promise<number> {
    return await this.predictionCards.count();
  }

  async selectDate(date: string) {
    await this.dateFilter.click();
    await this.page.locator(`[data-date="${date}"]`).click();
  }

  async filterByCustomer(customerName: string) {
    await this.customerFilter.fill(customerName);
    await this.page.waitForTimeout(500); // Debounce
  }

  async exportPredictions() {
    await this.exportButton.click();
  }

  async refreshPredictions() {
    await this.refreshButton.click();
    await this.waitForPredictionsLoad();
  }

  async waitForPredictionsLoad() {
    await this.page.waitForSelector('[data-testid="predictions-list"]', {
      state: 'visible',
      timeout: 10000
    });
  }

  async getPredictionDetails(index: number): Promise<{
    customerName: string;
    predictedDemand: string;
    confidence: string;
    lastDelivery: string;
  }> {
    const card = this.predictionCards.nth(index);
    
    return {
      customerName: await card.locator('[data-testid="customer-name"]').textContent() || '',
      predictedDemand: await card.locator('[data-testid="predicted-demand"]').textContent() || '',
      confidence: await card.locator('[data-testid="confidence-level"]').textContent() || '',
      lastDelivery: await card.locator('[data-testid="last-delivery"]').textContent() || ''
    };
  }

  async isPlaceholderServiceActive(): Promise<boolean> {
    // Check if placeholder notice is shown (indicating Google API is not configured)
    return await this.placeholderNotice.isVisible();
  }

  async checkConfidenceColors(): Promise<boolean> {
    const confidenceElements = await this.confidenceIndicator.all();
    
    for (const element of confidenceElements) {
      const confidence = await element.getAttribute('data-confidence');
      const className = await element.getAttribute('class');
      
      if (!confidence || !className) continue;
      
      const confidenceValue = parseFloat(confidence);
      
      // Check color coding
      if (confidenceValue >= 0.8 && !className.includes('high-confidence')) {
        return false;
      } else if (confidenceValue >= 0.6 && confidenceValue < 0.8 && !className.includes('medium-confidence')) {
        return false;
      } else if (confidenceValue < 0.6 && !className.includes('low-confidence')) {
        return false;
      }
    }
    
    return true;
  }

  async isDemandChartVisible(): Promise<boolean> {
    return await this.demandChart.isVisible();
  }

  async checkChartInteractivity(): Promise<boolean> {
    if (!await this.isDemandChartVisible()) {
      return false;
    }
    
    // Hover over chart to check tooltips
    const chartArea = await this.demandChart.boundingBox();
    if (!chartArea) return false;
    
    await this.page.mouse.move(chartArea.x + chartArea.width / 2, chartArea.y + chartArea.height / 2);
    await this.page.waitForTimeout(500);
    
    // Check if tooltip appears
    const tooltip = await this.page.locator('[data-testid="chart-tooltip"]').isVisible();
    
    return tooltip;
  }

  async verifyPredictionsWithoutGoogleAPI(): Promise<boolean> {
    // Generate predictions
    await this.generatePredictions();
    
    // Check if placeholder notice is shown
    const isPlaceholder = await this.isPlaceholderServiceActive();
    
    // Verify predictions are still generated (even if placeholder)
    const predictionCount = await this.getPredictionCount();
    
    // Check that confidence levels are reasonable for placeholder data
    const firstPrediction = await this.getPredictionDetails(0);
    const confidence = parseFloat(firstPrediction.confidence.replace('%', ''));
    
    return isPlaceholder && predictionCount > 0 && confidence >= 50 && confidence <= 80;
  }

  async checkErrorHandling(): Promise<boolean> {
    // Simulate API error by setting invalid date range
    await this.page.evaluate(() => {
      // Inject error condition
      window.localStorage.setItem('force-prediction-error', 'true');
    });
    
    await this.generatePredictions();
    
    // Check if error is displayed
    const errorVisible = await this.errorAlert.isVisible();
    const errorMessage = await this.errorAlert.textContent();
    
    // Clean up
    await this.page.evaluate(() => {
      window.localStorage.removeItem('force-prediction-error');
    });
    
    return errorVisible && errorMessage !== null && errorMessage.length > 0;
  }

  async checkLocalization(): Promise<boolean> {
    // Check if all UI elements are in Traditional Chinese
    const title = await this.pageTitle.textContent();
    const generateText = await this.generateButton.textContent();
    const exportText = await this.exportButton.textContent();
    
    // Check for Chinese characters
    const hasChineseTitle = /[\u4e00-\u9fa5]/.test(title || '');
    const hasChineseGenerate = /[\u4e00-\u9fa5]/.test(generateText || '');
    const hasChineseExport = /[\u4e00-\u9fa5]/.test(exportText || '');
    
    return hasChineseTitle && hasChineseGenerate && hasChineseExport;
  }
}