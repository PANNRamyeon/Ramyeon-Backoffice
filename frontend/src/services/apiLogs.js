// services/apiProducts.js - UPDATED VERSION
import { api } from './api.js';

class SessionLogsAPI {
  // Helper method to handle responses
   handleResponse(response) {
    if (response?.data) {
      return response.data;
    }
    return response;
  }

  // Helper method to handle errors consistently
  handleError(error) {
    console.error('API Error:', error);
    const message = error.response?.data?.error || 
                   error.response?.data?.message || 
                   error.message || 
                   'An unexpected error occurred';
    throw new Error(message);
  }

  /**
   * Get combined session and audit logs (FIXED)
   * @param {Object} params - Query parameters (limit, type)
   * @returns {Promise<Object>} Combined logs data
   */
  async DisplayCombinedLogs(params = {}) {
    try {
        const queryParams = new URLSearchParams();
        if (params.limit) queryParams.append('limit', params.limit);
        if (params.type) queryParams.append('type', params.type);

        const url = `/session-logs/combined/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

        const response = await api.get(url);

        return this.handleResponse(response);

    } catch (error) {
        console.error("Error fetching combined logs:", error);
        this.handleError(error);
    }
  }

  /**
   * Get all session logs (original functionality preserved)
   */
  async DisplayLogs(params = {}) {
    try {
        const response = await api.get('/session-logs/display/');
        return this.handleResponse(response);
    } catch (error) {
        console.error("Error fetching session logs:", error);
        this.handleError(error);
    }
  }

  /**
   * Get only session logs
   */
  async DisplaySessionLogsOnly(params = {}) {
    try {
        return await this.DisplayCombinedLogs({ ...params, type: 'session' });
    } catch (error) {
        console.error("Error fetching session logs:", error);
        this.handleError(error);
    }
  }

  /**
   * Get only audit logs
   */
  async DisplayAuditLogsOnly(params = {}) {
    try {
        return await this.DisplayCombinedLogs({ ...params, type: 'audit' });
    } catch (error) {
        console.error("Error fetching audit logs:", error);
        this.handleError(error);
    }
  }

  /**
   * Search specific logs (placeholder for future implementation)
   */
  async SearchLogs(params = {}) {
    try {
        // This endpoint doesn't exist in your URLs yet
        const response = await api.get('/session-logs/search/', { params });
        return this.handleResponse(response);
    } catch (error) {
        console.error("Error searching logs:", error);
        this.handleError(error);
    }
  }

}

// Create and export singleton instance
const apiLogs = new SessionLogsAPI();

export default apiLogs;