// services/apiCustomers.js - Updated to match backend CustomerService
import { api } from './api.js';

class CustomerApiService {
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
    
    console.error('Customer API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message
    });
    
    throw new Error(message);
  }

  // CUSTOMER CRUD OPERATIONS

  /**
   * Get all customers with pagination and filters
   * @param {Object} params - Query parameters (page, limit, status, etc.)
   * @returns {Promise<Object>} Customers data with pagination
   */
  async getCustomers(params = {}) {
    try {
      const response = await api.get('/customers/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching customers:', error);
      this.handleError(error);
    }
  }

  /**
   * Get customer by ID
   * @param {string} customerId - Customer ID (CUST-##### format)
   * @returns {Promise<Object>} Customer data
   */
  async getCustomer(customerId) {
    try {
      const response = await api.get(`/customers/${customerId}/`);
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error fetching customer ${customerId}:`, error);
      this.handleError(error);
    }
  }

  /**
   * Create new customer
   * @param {Object} customerData - Customer data
   * @returns {Promise<Object>} Created customer
   */
  async createCustomer(customerData) {
    try {
      const response = await api.post('/customers/', customerData);
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error creating customer:', error);
      this.handleError(error);
    }
  }

  /**
   * Update customer
   * @param {string} customerId - Customer ID
   * @param {Object} customerData - Updated customer data
   * @returns {Promise<Object>} Updated customer
   */
  async updateCustomer(customerId, customerData) {
    try {
      const response = await api.put(`/customers/${customerId}/`, customerData);
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error updating customer ${customerId}:`, error);
      this.handleError(error);
    }
  }

  /**
   * Delete customer (soft delete - sets isDeleted: true)
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} Deletion confirmation
   */
  async deleteCustomer(customerId) {
    try {
      // Try using DELETE on the main endpoint (same pattern as create but with DELETE)
      const response = await api.delete(`/customers/${customerId}/`);
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error soft deleting customer ${customerId}:`, error);
      this.handleError(error);
    }
  }

  /**
   * Restore soft deleted customer
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} Restored customer
   */
  async restoreCustomer(customerId) {
    try {
      const response = await api.patch(`/customers/${customerId}/restore/`);
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error restoring customer ${customerId}:`, error);
      this.handleError(error);
    }
  }

  /**
   * Get deleted customers (for admin to view soft-deleted customers)
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Deleted customers data
   */
  async getDeletedCustomers(params = {}) {
    try {
      const response = await api.get('/customers/deleted/', { params });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching deleted customers:', error);
      this.handleError(error);
    }
  }

  // SEARCH AND FILTERING

  /**
   * Search customers by query
   * @param {string} query - Search query
   * @returns {Promise<Array>} Filtered customers
   */
  async searchCustomers(query) {
    try {
      const response = await api.get('/customers/search/', {
        params: { search: query }
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error searching customers:', error);
      this.handleError(error);
    }
  }

  /**
   * Get customers by status
   * @param {string} status - Customer status (active, inactive)
   * @returns {Promise<Object>} Customers with specified status
   */
  async getCustomersByStatus(status) {
    try {
      const response = await api.get('/customers/', {
        params: { status }
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error fetching customers by status ${status}:`, error);
      this.handleError(error);
    }
  }

  // LOYALTY POINTS MANAGEMENT

  /**
   * Update customer loyalty points
   * @param {string} customerId - Customer ID
   * @param {number} points - Points to add
   * @param {string} reason - Reason for point addition
   * @returns {Promise<Object>} Updated customer
   */
  async updateLoyaltyPoints(customerId, points, reason = 'Manual adjustment') {
    try {
      const response = await api.patch(`/customers/${customerId}/loyalty/`, {
        points_to_add: points,
        reason: reason
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error updating loyalty points for customer ${customerId}:`, error);
      this.handleError(error);
    }
  }

  // CUSTOMER ANALYTICS

  /**
   * Get customer statistics
   * @returns {Promise<Object>} Customer statistics
   */
  async getCustomerStatistics() {
    try {
      const response = await api.get('/customers/statistics/');
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching customer statistics:', error);
      this.handleError(error);
    }
  }

  // RESTORE AND HARD DELETE (for admin functions)

  /**
   * Restore deleted customer
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} Restored customer
   */
  async restoreCustomer(customerId) {
    try {
      const response = await api.patch(`/customers/${customerId}/restore/`);
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error restoring customer ${customerId}:`, error);
      this.handleError(error);
    }
  }

  /**
   * Permanently delete customer
   * @param {string} customerId - Customer ID
   * @param {string} confirmationToken - Confirmation token
   * @returns {Promise<Object>} Deletion confirmation
   */
  async hardDeleteCustomer(customerId, confirmationToken) {
    try {
      const response = await api.delete(`/customers/${customerId}/hard/`, {
        data: { confirmation_token: confirmationToken }
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error permanently deleting customer ${customerId}:`, error);
      this.handleError(error);
    }
  }

  // BULK OPERATIONS

  /**
   * Delete multiple customers
   * @param {Array} customerIds - Array of customer IDs
   * @returns {Promise<Object>} Deletion results
   */
  async deleteMultipleCustomers(customerIds) {
    try {
      const response = await api.delete('/customers/bulk/', {
        data: { customer_ids: customerIds }
      });
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error deleting multiple customers:', error);
      this.handleError(error);
    }
  }


  /**
   * Export customers as a CSV file
   * @param {boolean} includeDeleted - Whether to include deleted customers
   * @returns {Promise<Blob>} CSV file blob
   */
  async exportCustomers(includeDeleted = false) {
    try {
      const response = await api.get('/customers/import-export/', {
        params: { include_deleted: includeDeleted },
        responseType: 'blob', // important for file downloads
      });
      return response.data;
    } catch (error) {
      console.error('Error exporting customers:', error);
      this.handleError(error);
    }
  }

  /**
   * Import customers from a CSV file
   * @param {File} file - CSV file to upload
   * @returns {Promise<Object>} Import summary
   */
  async importCustomers(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/customers/import-export/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      return this.handleResponse(response);
    } catch (error) {
      console.error('Error importing customers:', error);
      this.handleError(error);
    }
  }
}

// Create and export singleton instance
const customerApiService = new CustomerApiService();

export default customerApiService;