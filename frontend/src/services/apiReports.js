// services/apiSales.js - Organized Sales API Service
import { api } from './api.js';

class SalesAPIService {
  // ====================================================================
  // CORE HELPER METHODS
  // ====================================================================

  /**
   * Handle responses consistently with existing pattern
   * @param {Object} response - API response object
   * @returns {Object} Response data
   */
  handleResponse(response) {
    return response.data;
  }

  /**
   * Handle errors consistently with existing pattern
   * @param {Object} error - Error object
   * @throws {Error} Formatted error message
   */
  handleError(error) {
    const message = error.response?.data?.error || 
                   error.response?.data?.message || 
                   error.message || 
                   'An unexpected error occurred';
    throw new Error(message);
  }

  // ====================================================================
  // INVOICE CRUD OPERATIONS
  // ====================================================================

  /**
   * Get all invoices/sales transactions with optional query parameters
   * @param {Object} params - Query parameters (page, limit, customer_id, sales_type, status, etc.)
   * @returns {Promise<Object>} Invoices list with pagination info
   */
  async getAllInvoices(params = {}) {
    try {
      const response = await api.get('/invoices/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching invoices:", error);
      this.handleError(error);
    }
  }

  /**
   * Get a single invoice by ID
   * @param {string} invoiceId - Invoice ID
   * @returns {Promise<Object>} Invoice details
   */
  async getInvoiceById(invoiceId) {
    try {
      const response = await api.get(`/invoices/${invoiceId}/`);
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching invoice:", error);
      this.handleError(error);
    }
  }

  /**
   * Create a new invoice
   * @param {Object} invoiceData - Invoice data to create
   * @returns {Promise<Object>} Created invoice
   */
  async createInvoice(invoiceData) {
    try {
      const response = await api.post('/invoices/', invoiceData);
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error creating invoice:", error);
      this.handleError(error);
    }
  }

  /**
   * Update an existing invoice
   * @param {string} invoiceId - Invoice ID to update
   * @param {Object} updateData - Data to update
   * @returns {Promise<Object>} Updated invoice
   */
  async updateInvoice(invoiceId, updateData) {
    try {
      const response = await api.put(`/invoices/${invoiceId}/`, updateData);
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error updating invoice:", error);
      this.handleError(error);
    }
  }

  /**
   * Delete an invoice
   * @param {string} invoiceId - Invoice ID to delete
   * @returns {Promise<Object>} Delete confirmation
   */
  async deleteInvoice(invoiceId) {
    try {
      const response = await api.delete(`/invoices/${invoiceId}/`);
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error deleting invoice:", error);
      this.handleError(error);
    }
  }

  // ====================================================================
  // REPORTS & ANALYTICS - TOP ITEMS
  // ====================================================================

  /**
   * Get top selling items
   * @param {Object} params - Query parameters (limit, etc.)
   * @returns {Promise<Object>} Top items data
   */
  async getTopItems(params = {}) {
    try {
      const queryParams = {
        limit: params.limit || 5,
        ...params
      };

      const response = await api.get('reports/top-item/', {
        params: queryParams
      });

      return response.data;
    } catch (error) {
      console.error("Error fetching top items:", error);
      throw error;
    }
  }

  /**
   * Get top Chart selling items with date filtering
   * @param {Object} params - Query parameters (limit, start_date, end_date, frequency, etc.)
   * @returns {Promise<Object>} Top items data with enhanced information
   */
  async getTopChartItems(params = {}) {
    try {
      const queryParams = {
        limit: params.limit || 10,
        ...params
      };

      const response = await api.get('reports/top-chart-item/', {
        params: queryParams
      });

      return response.data;
    } catch (error) {
      console.error("Error fetching top chart items:", error);
      throw error;
    }
  }

  /**
   * Get sales item history with pagination
   * @param {Object} params - Query parameters (page, page_size)
   * @returns {Promise<Object>} Item history data with pagination
   */
  async getSalesItemHistory(params = {}) {
    try {
      const queryParams = {
        page: params.page || 1,
        page_size: params.page_size || 10,
        ...params
      };

      const response = await api.get('reports/item-history/', { params: queryParams });
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching sales item history:", error);
      this.handleError(error);
    }
  }

  // ====================================================================
  // SALES STATISTICS AND REPORTS
  // ====================================================================

  /**
   * Get sales statistics
   * @param {Object} params - Query parameters (start_date, end_date, sales_type, etc.)
   * @returns {Promise<Object>} Sales statistics
   */
  async getSalesStatistics(params = {}) {
    try {
      const response = await api.get('/invoices/stats/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching sales statistics:", error);
      this.handleError(error);
    }
  }

  /**
   * Get top selling items (alternative endpoint)
   * @param {Object} params - Query parameters (limit, date_range, etc.)
   * @returns {Promise<Object>} Top selling items data
   */
  async getTopSellingItems(params = {}) {
    try {
      const response = await api.get('/invoices/top-items/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching top selling items:", error);
      this.handleError(error);
    }
  }

  /**
   * Get sales chart data for different frequencies
   * @param {Object} params - Query parameters (frequency: daily/weekly/monthly/yearly, date_range, etc.)
   * @returns {Promise<Object>} Chart data
   */
  async getSalesChartData(params = {}) {
    try {
      const response = await api.get('/invoices/chart-data/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching sales chart data:", error);
      this.handleError(error);
    }
  }

  // ====================================================================
  // SALES BREAKDOWN ANALYTICS
  // ====================================================================

  /**
   * Get sales by payment method breakdown
   * @param {Object} params - Query parameters (date_range, etc.)
   * @returns {Promise<Object>} Payment method breakdown
   */
  async getSalesByPaymentMethod(params = {}) {
    try {
      const response = await api.get('/invoices/by-payment-method/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching sales by payment method:", error);
      this.handleError(error);
    }
  }

  /**
   * Get sales by type breakdown (dine-in, takeout, delivery)
   * @param {Object} params - Query parameters (date_range, etc.)
   * @returns {Promise<Object>} Sales type breakdown
   */
  async getSalesByType(params = {}) {
    try {
      const response = await api.get('/invoices/by-sales-type/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching sales by type:", error);
      this.handleError(error);
    }
  }

  /**
   * Get sales display by item
   * @param {Object} params - Query parameters (date_range, item_id, etc.)
   * @returns {Promise<Object>} Sales display by item data
   */
  async getSalesDisplayByItem(params = {}) {
    try {
      const response = await api.get('/sales-display/by-item/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching sales display by item:', error);
      this.handleError(error);
    }
  }

  async getSalesDisplayPosSales(params = {}) {
    try {
      const response = await api.get('/sales-display/pos-sales/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching POS sales:', error);
      this.handleError(error);
    }
  }

  async getSalesDisplayOnlineTransactions(params = {}) {
    try {
      const response = await api.get('/sales-display/online-transactions/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching online transactions:', error);
      this.handleError(error);
    }
  }

  /**
   * Get recent sales transactions
   * @param {Object} params - Query parameters (limit, etc.)
   * @returns {Promise<Object>} Recent sales transactions
   */
  async getRecentSales(params = {}) {
    try {
      const queryParams = {
        limit: params.limit || 20,
        ...params
      };
      const response = await api.get('/sales/recent/', { params: queryParams });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching recent sales:', error);
      this.handleError(error);
    }
  }

  /**
   * Get sales by period (daily, weekly, monthly)
   * @param {Object} params - Query parameters (start_date, end_date, period: 'daily'|'weekly'|'monthly', source, etc.)
   * @returns {Promise<Object>} Sales data grouped by period
   */
  async getSalesByPeriod(params = {}) {
    try {
      if (!params.start_date || !params.end_date) {
        throw new Error('start_date and end_date are required');
      }
      const queryParams = {
        period: params.period || 'monthly',
        ...params
      };
      const response = await api.get('/sales-report/by-period/', { params: queryParams });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching sales by period:', error);
      this.handleError(error);
    }
  }

  // ====================================================================
  // BULK IMPORT OPERATIONS - CSV ONLY
  // ====================================================================

  /**
   * Bulk import sales transactions from CSV file
   * @param {File} file - CSV file to upload
   * @param {Function} onProgress - Optional progress callback
   * @returns {Promise<Object>} Import results
   */
  async bulkImportCSV(file, onProgress = null) {
    try {
      // Validate file before upload
      if (!this._validateFileType(file, ['.csv'])) {
        throw new Error('Invalid file type. Please upload a CSV file.');
      }

      if (!this._validateFileSize(file, 50)) { // 50MB limit
        throw new Error('File size too large. Please upload a file smaller than 50MB.');
      }

      // Create FormData for file upload
      const formData = new FormData();
      formData.append('file', file);

      // Make the API call
      const response = await api.post('/invoices/bulk-import/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes timeout for large files
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(percentCompleted);
          }
        }
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error("Error in CSV bulk import:", error);
      console.error("Error details:", {
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        url: error.config?.url
      });

      // Handle specific error cases
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        throw new Error('Import is taking longer than expected. The file might be too large or the server is busy. Please try with a smaller file or try again later.');
      }

      if (error.response?.status === 413) {
        throw new Error('File is too large for the server. Please try a smaller file.');
      }

      if (error.response?.status === 400) {
        const errorMsg = error.response?.data?.error || 'Invalid CSV file format or content.';
        throw new Error(errorMsg);
      }

      this.handleError(error);
    }
  }

  /**
   * Download CSV template for bulk import
   * @returns {Promise<boolean>} Success status
   */
  async downloadCSVTemplate() {
    try {
      const response = await api.get('/invoices/template/', {
        responseType: 'blob',
        timeout: 60000,
      });

      // Create download
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'sales_import_template.csv');

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      link.remove();
      window.URL.revokeObjectURL(url);

      return true;
    } catch (error) {
      console.error("Error downloading CSV template:", error);

      if (error.response?.status === 404) {
        throw new Error('CSV template endpoint not found. Please contact support.');
      }

      this.handleError(error);
    }
  }

  /**
   * Get import status/history
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Import history
   */
  async getImportHistory(params = {}) {
    try {
      const response = await api.get('/invoices/import-history/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error("Error fetching import history:", error);
      this.handleError(error);
    }
  }

  // ====================================================================
  // EXPORT OPERATIONS
  // ====================================================================

  /**
   * Export sales transactions to CSV
   * @param {Object} filters - Export filters (date range, customer, etc.)
   * @returns {Promise<boolean>} Success status
   */
  async exportTransactions(filters = {}) {
    try {
      const response = await api.get('/invoices/export/', {
        params: filters,
        responseType: 'blob',
        timeout: 120000, // 2 minutes for large exports
      });

      // Create download
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;

      // Generate filename with timestamp
      const timestamp = this._generateTimestamp();
      link.setAttribute('download', `sales_export_${timestamp}.csv`);

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      link.remove();
      window.URL.revokeObjectURL(url);

      return true;
    } catch (error) {
      console.error("Error exporting transactions:", error);
      this.handleError(error);
    }
  }

  // ====================================================================
  // UTILITY METHODS
  // ====================================================================

  /**
   * Generate timestamp for file names
   * @returns {string} Formatted timestamp
   */
  _generateTimestamp() {
    return new Date().toISOString().slice(0, 19).replace(/:/g, '-');
  }

  /**
   * Validate file type
   * @param {File} file - File to validate
   * @param {Array} allowedTypes - Array of allowed file extensions
   * @returns {boolean} Validation result
   */
  _validateFileType(file, allowedTypes = ['.csv']) {
    if (!file) return false;
    
    const fileName = file.name.toLowerCase();
    return allowedTypes.some(type => fileName.endsWith(type));
  }

  /**
   * Validate file size
   * @param {File} file - File to validate
   * @param {number} maxSizeMB - Maximum size in MB (default: 10MB)
   * @returns {boolean} Validation result
   */
  _validateFileSize(file, maxSizeMB = 10) {
    if (!file) return false;
    
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    return file.size <= maxSizeBytes;
  }

  /**
   * Create a download link and trigger download
   * @param {Blob} blob - File blob to download
   * @param {string} filename - Name of the file
   * @returns {boolean} Success status
   */
  _triggerDownload(blob, filename) {
    try {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      return true;
    } catch (error) {
      console.error('Error triggering download:', error);
      return false;
    }
  }
}

// ====================================================================
// EXPORT CONFIGURATION
// ====================================================================

// Create and export singleton instance
const salesAPIService = new SalesAPIService();
export default salesAPIService;

// Also export the class if needed for multiple instances
export { SalesAPIService };