// services/apiCustomers.js
import { api } from './api.js';

class CustomerApiService {
  handleResponse(response) {
    return response.data;
  }

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

  // ==================== CRUD ====================

  async getCustomers(params = {}) {
    try {
      const response = await api.get('/customers/', { params });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getCustomer(customerId) {
    try {
      const response = await api.get(`/customers/${customerId}/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async createCustomer(customerData) {
    try {
      const response = await api.post('/customers/', customerData);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async updateCustomer(customerId, customerData) {
    try {
      const response = await api.put(`/customers/${customerId}/`, customerData);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // Soft delete — sets isDeleted: true
  async deleteCustomer(customerId) {
    try {
      const response = await api.delete(`/customers/${customerId}/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // Restore a soft-deleted customer
  async restoreCustomer(customerId) {
    try {
      const response = await api.post(`/customers/${customerId}/restore/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // Permanently delete — requires ?confirm=yes
  async hardDeleteCustomer(customerId) {
    try {
      const response = await api.delete(`/customers/${customerId}/hard-delete/?confirm=yes`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ==================== AUTH ====================

  async registerCustomer(customerData) {
    try {
      const response = await api.post('/customers/register/', customerData);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async loginCustomer(email, password) {
    try {
      const response = await api.post('/customers/login/', { email, password });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getCurrentCustomer() {
    try {
      const response = await api.get('/customers/me/');
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ==================== SEARCH & LOOKUP ====================

  // Search by name, email, username, or phone — param must be 'q'
  async searchCustomers(query) {
    try {
      const response = await api.get('/customers/search/', { params: { q: query } });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getCustomerByEmail(email) {
    try {
      const response = await api.get('/customers/by-email/', { params: { email } });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getCustomersByStatus(status) {
    try {
      const response = await api.get('/customers/', { params: { status } });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ==================== LOYALTY ====================

  // Add loyalty points — payload key must be 'points'
  async updateLoyaltyPoints(customerId, points, reason = 'Manual adjustment') {
    try {
      const response = await api.post(`/customers/${customerId}/loyalty/`, { points, reason });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ==================== EXPORT / IMPORT ====================

  // Download all customers as a CSV file (triggers browser download)
  async exportCustomers(params = {}) {
    try {
      const response = await api.get('/customers/export/', {
        params,
        responseType: 'blob',
      });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      const date = new Date().toISOString().slice(0, 10);
      link.download = `customers_export_${date}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      this.handleError(error);
    }
  }

  // Import customers from a CSV File object (multipart/form-data)
  async importCustomers(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.post('/customers/import/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ==================== STATISTICS ====================

  async getCustomerStatistics() {
    try {
      const response = await api.get('/customers/statistics/');
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // ==================== QR CODE ====================

  // Generate a QR token for a customer (default 720h / 30 days)
  async generateQRToken(customerId, expiryHours = 720) {
    try {
      const response = await api.get(`/customers/${customerId}/qr/`, {
        params: { expiry_hours: expiryHours }
      });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  // Verify a scanned QR token and return customer data
  async verifyQRToken(token) {
    try {
      const response = await api.post('/qr/verify/', { token });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }
}

const customerApiService = new CustomerApiService();
export default customerApiService;
