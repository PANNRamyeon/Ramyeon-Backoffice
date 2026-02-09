import { api } from './api.js';

class BatchService {
  constructor() {
    this.baseEndpoint = '/batches';
  }


  // ================================================================
  // IMPORTANT USAGE NOTE:
  // ================================================================
  // 
  // When creating products with initial stock, DO NOT manually create batches.
  // The backend automatically creates initial batches when:
  // 1. Creating a single product with stock > 0 (via createProduct)
  // 2. Bulk creating products with stock > 0 (via bulkCreateProducts)
  // 3. Importing products with stock > 0 (via importProducts)
  //
  // Use createBatch() ONLY for:
  // - Adding new batches to existing products (restocking)
  // - Manual batch creation for special cases
  //
  // ================================================================

  // Helper method to handle responses
  handleResponse(response) {
    return response.data;
  }

  // Helper method to handle errors
  handleError(error) {
    const message = error.response?.data?.error || 
                   error.response?.data?.message || 
                   error.response?.data?.detail ||
                   error.message || 
                   'An unexpected error occurred';
    
    console.error('Batch API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message
    });
    
    throw new Error(message);
  }

  // ================================================================
  // BATCH CRUD OPERATIONS
  // ================================================================

  async createBatch(batchData) {
    try {
      const response = await api.post(`${this.baseEndpoint}/create/`, batchData);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getAllBatches(filters = {}) {
    try {
      const response = await api.get(`${this.baseEndpoint}/`, { params: filters });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getBatchById(batchId) {
    try {
      const response = await api.get(`${this.baseEndpoint}/${batchId}/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async updateBatchQuantity(batchId, quantityUsed, adjustmentType = 'correction', adjustedBy = null, notes = null) {
    try {
      const response = await api.put(`${this.baseEndpoint}/${batchId}/update-quantity/`, {
        quantity_used: quantityUsed,
        adjustment_type: adjustmentType,
        adjusted_by: adjustedBy,
        notes: notes
      });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async processBatchAdjustment(productId, quantityUsed, adjustmentType = 'correction', adjustedBy = null, notes = null) {
    try {
      const response = await api.post(`${this.baseEndpoint}/adjust/`, {
        product_id: productId,
        quantity_used: quantityUsed,
        adjustment_type: adjustmentType,
        adjusted_by: adjustedBy,
        notes: notes
      });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ================================================================
  // BATCH QUERIES AND REPORTS
  // ================================================================

  async getBatchesByProduct(productId, status = null) {
    try {
      const params = status ? { status } : {};
      const response = await api.get(`/products/${productId}/batches/`, { params });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getBatchesBySupplier(supplierId, filters = {}) {
    try {
      const params = {};
      
      if (filters.status) params.status = filters.status;
      if (filters.product_id) params.product_id = filters.product_id;
      if (filters.expiring_soon) {
        params.expiring_soon = 'true';
        params.days_ahead = filters.days_ahead || 30;
      }

      const response = await api.get(`${this.baseEndpoint}/by-supplier/${supplierId}/`, { params });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getExpiringBatches(daysAhead = 30) {
    try {
      const response = await api.get(`${this.baseEndpoint}/expiring/`, {
        params: { days_ahead: daysAhead }
      });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getProductsWithExpirySummary() {
    try {
      const response = await api.get('/products/expiry-summary/');
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getBatchStatistics() {
    try {
      const response = await api.get(`${this.baseEndpoint}/statistics/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ================================================================
  // BATCH OPERATIONS FOR SALES
  // ================================================================

  async processSaleFIFO(productId, quantitySold) {
    try {
      const response = await api.post(`${this.baseEndpoint}/process-sale/`, {
        product_id: productId,
        quantity_sold: quantitySold
      });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getProductWithBatches(productId) {
    try {
      const response = await api.get(`/products/${productId}/with-batches/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async restockWithBatch(productId, restockData) {
    try {
      const response = await api.post(`/products/${productId}/restock-batch/`, restockData);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ================================================================
  // BATCH MAINTENANCE AND ALERTS
  // ================================================================

  async checkExpiryAlerts(daysAhead = 7) {
    try {
      const response = await api.post(`${this.baseEndpoint}/check-expiry-alerts/`, {
        days_ahead: daysAhead
      });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async markExpiredBatches() {
    try {
      const response = await api.post(`${this.baseEndpoint}/mark-expired/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ================================================================
  // CONVENIENCE METHODS
  // ================================================================

  async getActiveBatchesByProduct(productId) {
    return this.getBatchesByProduct(productId, 'active');
  }

  async getDeplettedBatchesByProduct(productId) {
    return this.getBatchesByProduct(productId, 'depleted');
  }

  async getExpiredBatchesByProduct(productId) {
    return this.getBatchesByProduct(productId, 'expired');
  }

  async getExpiringBatchesThisWeek() {
    return this.getExpiringBatches(7);
  }

  async getExpiringBatchesThisMonth() {
    return this.getExpiringBatches(30);
  }

  // ================================================================
  // BATCH FILTERING HELPERS
  // ================================================================

  async getBatchesWithFilters(filters) {
    const validFilters = {};
    
    if (filters.productId) validFilters.product_id = filters.productId;
    if (filters.status) validFilters.status = filters.status;
    if (filters.supplierId) validFilters.supplier_id = filters.supplierId;
    if (filters.expiringSoon) {
      validFilters.expiring_soon = true;
      validFilters.days_ahead = filters.daysAhead || 30;
    }

    return this.getAllBatches(validFilters);
  }

  // ================================================================
  // ERROR HANDLING UTILITIES
  // ================================================================

  async safeApiCall(apiMethod, defaultValue = null) {
    try {
      return await apiMethod();
    } catch (error) {
      console.warn('Batch API call failed, returning default value:', error.message);
      return defaultValue;
    }
  }

  // ================================================================
  // BATCH DATA TRANSFORMATION HELPERS
  // ================================================================

  formatBatchForDisplay(batch) {
    return {
      id: batch._id,
      batchNumber: batch.batch_number,
      productId: batch.product_id,
      quantityReceived: batch.quantity_received,
      quantityRemaining: batch.quantity_remaining,
      costPrice: batch.cost_price,
      expiryDate: batch.expiry_date ? new Date(batch.expiry_date) : null,
      dateReceived: new Date(batch.date_received),
      supplierId: batch.supplier_id,
      status: batch.status,
      createdAt: new Date(batch.created_at),
      updatedAt: new Date(batch.updated_at)
    };
  }

  formatBatchesForDisplay(batches) {
    return batches.map(batch => this.formatBatchForDisplay(batch));
  }

  // ================================================================
  // VALIDATION HELPERS
  // ================================================================

  validateBatchData(batchData) {
    const errors = [];

    if (!batchData.product_id) {
      errors.push('Product ID is required');
    }

    if (!batchData.quantity_received || batchData.quantity_received <= 0) {
      errors.push('Quantity received must be greater than 0');
    }

    if (batchData.cost_price !== undefined && batchData.cost_price < 0) {
      errors.push('Cost price cannot be negative');
    }

    if (batchData.expiry_date) {
      const expiryDate = new Date(batchData.expiry_date);
      const today = new Date();
      
      if (expiryDate <= today) {
        errors.push('Expiry date must be in the future');
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }
}

// Create and export singleton instance
const batchService = new BatchService();

export default batchService;