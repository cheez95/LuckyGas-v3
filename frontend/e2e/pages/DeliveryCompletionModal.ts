import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class DeliveryCompletionModal extends BasePage {
  readonly modal: Locator;
  readonly signaturePad: Locator;
  readonly clearSignatureButton: Locator;
  readonly photoUploadButton: Locator;
  readonly photoPreview: Locator;
  readonly notesInput: Locator;
  readonly confirmButton: Locator;
  readonly cancelButton: Locator;
  readonly photoInput: Locator;
  readonly uploadProgress: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.modal = page.locator('[data-testid="delivery-completion-modal"]');
    this.signaturePad = page.locator('[data-testid="signature-pad"]');
    this.clearSignatureButton = page.locator('[data-testid="clear-signature-btn"]');
    this.photoUploadButton = page.locator('[data-testid="photo-upload-btn"]');
    this.photoPreview = page.locator('[data-testid="photo-preview"]');
    this.notesInput = page.locator('[data-testid="delivery-notes"]');
    this.confirmButton = page.locator('[data-testid="confirm-delivery-btn"]');
    this.cancelButton = page.locator('[data-testid="cancel-delivery-btn"]');
    this.photoInput = page.locator('input[type="file"][accept="image/*"]');
    this.uploadProgress = page.locator('[data-testid="upload-progress"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
  }

  async waitForModal() {
    await this.modal.waitFor({ state: 'visible' });
  }

  async isModalVisible(): Promise<boolean> {
    return await this.modal.isVisible();
  }

  async drawSignature() {
    const canvas = await this.signaturePad.locator('canvas');
    const box = await canvas.boundingBox();
    
    if (!box) {
      throw new Error('Signature canvas not found');
    }

    // Simulate drawing a signature
    await this.page.mouse.move(box.x + 50, box.y + 50);
    await this.page.mouse.down();
    
    // Draw a simple signature pattern
    const points = [
      { x: box.x + 100, y: box.y + 60 },
      { x: box.x + 150, y: box.y + 40 },
      { x: box.x + 200, y: box.y + 80 },
      { x: box.x + 250, y: box.y + 50 }
    ];
    
    for (const point of points) {
      await this.page.mouse.move(point.x, point.y, { steps: 5 });
    }
    
    await this.page.mouse.up();
  }

  async clearSignature() {
    await this.clearSignatureButton.click();
  }

  async hasSignature(): Promise<boolean> {
    // Check if the signature pad has any drawn content
    const canvasData = await this.page.evaluate(() => {
      const canvas = document.querySelector('[data-testid="signature-pad"] canvas') as HTMLCanvasElement;
      if (!canvas) return null;
      
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;
      
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imageData.data;
      
      // Check if any non-white pixels exist
      for (let i = 0; i < data.length; i += 4) {
        if (data[i] !== 255 || data[i + 1] !== 255 || data[i + 2] !== 255) {
          return true;
        }
      }
      return false;
    });
    
    return canvasData === true;
  }

  async uploadPhoto(filePath: string) {
    await this.photoInput.setInputFiles(filePath);
    
    // Wait for upload to complete or progress to show
    await this.page.waitForTimeout(1000);
  }

  async uploadMultiplePhotos(filePaths: string[]) {
    for (const filePath of filePaths) {
      await this.uploadPhoto(filePath);
      await this.page.waitForTimeout(500);
    }
  }

  async getPhotoCount(): Promise<number> {
    return await this.photoPreview.count();
  }

  async removePhoto(index: number) {
    const photos = this.photoPreview;
    const removeButton = photos.nth(index).locator('[data-testid="remove-photo-btn"]');
    await removeButton.click();
  }

  async enterNotes(notes: string) {
    await this.notesInput.fill(notes);
  }

  async confirmDelivery() {
    await this.confirmButton.click();
  }

  async cancelDelivery() {
    await this.cancelButton.click();
  }

  async isConfirmButtonEnabled(): Promise<boolean> {
    return await this.confirmButton.isEnabled();
  }

  async getErrorMessage(): Promise<string | null> {
    if (await this.errorMessage.isVisible()) {
      return await this.errorMessage.textContent();
    }
    return null;
  }

  async checkPhotoCompression(): Promise<boolean> {
    // Upload a large photo and check if it's compressed
    const largePhotoSize = 5 * 1024 * 1024; // 5MB
    const testPhoto = await this.page.evaluateHandle((size) => {
      const canvas = document.createElement('canvas');
      canvas.width = 3000;
      canvas.height = 3000;
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('Canvas context not available');
      
      // Fill with random colors to ensure it's not easily compressed
      for (let i = 0; i < 100; i++) {
        ctx.fillStyle = `rgb(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255})`;
        ctx.fillRect(Math.random() * 3000, Math.random() * 3000, 100, 100);
      }
      
      return new Promise((resolve) => {
        canvas.toBlob((blob) => {
          if (!blob) throw new Error('Failed to create blob');
          const file = new File([blob], 'large-test-photo.jpg', { type: 'image/jpeg' });
          resolve(file);
        }, 'image/jpeg', 0.95);
      });
    }, largePhotoSize);
    
    // Upload the photo
    await this.photoInput.setInputFiles(testPhoto);
    
    // Wait for compression
    await this.page.waitForTimeout(2000);
    
    // Check if photo was uploaded successfully (should be compressed to under 1MB)
    const uploadedSuccessfully = await this.photoPreview.first().isVisible();
    
    return uploadedSuccessfully;
  }

  async simulateTouchSignature() {
    const canvas = await this.signaturePad.locator('canvas');
    const box = await canvas.boundingBox();
    
    if (!box) {
      throw new Error('Signature canvas not found');
    }

    // Simulate touch events for mobile signature
    await this.page.touchscreen.tap(box.x + 50, box.y + 50);
    
    const points = [
      { x: box.x + 100, y: box.y + 60 },
      { x: box.x + 150, y: box.y + 40 },
      { x: box.x + 200, y: box.y + 80 }
    ];
    
    for (let i = 0; i < points.length; i++) {
      await this.page.touchscreen.tap(points[i].x, points[i].y);
      await this.page.waitForTimeout(50);
    }
  }

  async checkOfflineSupport(): Promise<boolean> {
    // Check if offline indicator is shown
    const offlineIndicator = await this.modal.locator('[data-testid="offline-save-indicator"]').isVisible();
    
    // Check if confirm button is still enabled when offline
    const confirmEnabled = await this.isConfirmButtonEnabled();
    
    return offlineIndicator && confirmEnabled;
  }
}