import api from './api';
import {
  GasProduct,
  GasProductList,
  ProductFilters,
  CustomerInventory,
  CustomerInventoryList,
} from '../types/product';
import i18n from '../utils/i18n';

export class ProductService {
  private static readonly BASE_URL = '/products';

  /**
   * Get all products with optional filters
   */
  static async getProducts(params?: {
    skip?: number;
    limit?: number;
    filters?: ProductFilters;
  }): Promise<GasProductList> {
    const queryParams = new URLSearchParams();
    
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    if (params?.filters) {
      if (params.filters.delivery_method) {
        queryParams.append('delivery_method', params.filters.delivery_method);
      }
      if (params.filters.size_kg) {
        queryParams.append('size_kg', params.filters.size_kg.toString());
      }
      if (params.filters.attribute) {
        queryParams.append('attribute', params.filters.attribute);
      }
      if (params.filters.is_available !== undefined) {
        queryParams.append('is_available', params.filters.is_available.toString());
      }
      if (params.filters.is_active !== undefined) {
        queryParams.append('is_active', params.filters.is_active.toString());
      }
    }

    const response = await api.get<GasProductList>(
      `${this.BASE_URL}?${queryParams.toString()}`
    );
    return response.data;
  }

  /**
   * Get a single product by ID
   */
  static async getProduct(id: number): Promise<GasProduct> {
    const response = await api.get<GasProduct>(`${this.BASE_URL}/${id}`);
    return response.data;
  }

  /**
   * Get available products (active and available for ordering)
   */
  static async getAvailableProducts(): Promise<GasProduct[]> {
    const response = await api.get<GasProductList>(`${this.BASE_URL}/available`);
    return response.data.items;
  }

  /**
   * Create a new product (admin only)
   */
  static async createProduct(product: Omit<GasProduct, 'id' | 'display_name'>): Promise<GasProduct> {
    const response = await api.post<GasProduct>(this.BASE_URL, product);
    return response.data;
  }

  /**
   * Update a product (admin only)
   */
  static async updateProduct(
    id: number,
    updates: Partial<GasProduct>
  ): Promise<GasProduct> {
    const response = await api.put<GasProduct>(`${this.BASE_URL}/${id}`, updates);
    return response.data;
  }

  /**
   * Delete a product (admin only)
   */
  static async deleteProduct(id: number): Promise<void> {
    await api.delete(`${this.BASE_URL}/${id}`);
  }

  /**
   * Get customer inventory for a specific customer
   */
  static async getCustomerInventory(
    customerId: number,
    params?: { skip?: number; limit?: number }
  ): Promise<CustomerInventoryList> {
    const queryParams = new URLSearchParams();
    
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());

    const response = await api.get<CustomerInventoryList>(
      `/customers/${customerId}/inventory?${queryParams.toString()}`
    );
    return response.data;
  }

  /**
   * Update customer inventory
   */
  static async updateCustomerInventory(
    customerId: number,
    productId: number,
    updates: {
      quantity_owned?: number;
      quantity_rented?: number;
    }
  ): Promise<CustomerInventory> {
    const response = await api.put<CustomerInventory>(
      `/customers/${customerId}/inventory/${productId}`,
      updates
    );
    return response.data;
  }

  /**
   * Get product display name by size and method
   */
  static getProductDisplayName(product: GasProduct): string {
    const sizeDisplay = i18n.t(`product.sizes.${product.size_kg}kg`);
    const methodDisplay = i18n.t(`product.deliveryMethods.${product.delivery_method}`);
    const attributeDisplay = product.attribute !== 'regular' 
      ? i18n.t(`product.attributes.${product.attribute}`)
      : '';

    const parts = [sizeDisplay, methodDisplay];
    if (attributeDisplay) parts.push(attributeDisplay);
    
    return parts.join(' ');
  }

  /**
   * Get product price display
   */
  static getProductPriceDisplay(product: GasProduct): string {
    return `NT$ ${product.unit_price.toLocaleString()}`;
  }

  /**
   * Check if product requires meter reading (flow products)
   */
  static isFlowProduct(product: GasProduct): boolean {
    return product.delivery_method === 'flow';
  }

  /**
   * Get available sizes
   */
  static getAvailableSizes(): number[] {
    return [4, 10, 16, 20, 50];
  }

  /**
   * Get size display text
   */
  static getSizeDisplay(size: number): string {
    return `${size}公斤`;
  }

  /**
   * Import products from Excel file (admin only)
   */
  static async importProducts(file: File): Promise<{
    imported_count: number;
    skipped_count: number;
    errors: string[];
    message: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post(`${this.BASE_URL}/import`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * Export products to Excel file
   */
  static async exportProducts(): Promise<Blob> {
    const response = await api.get(`${this.BASE_URL}/export`, {
      responseType: 'blob',
    });
    return response.data;
  }
}

export default ProductService;