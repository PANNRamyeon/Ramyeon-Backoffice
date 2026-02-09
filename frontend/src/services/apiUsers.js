// services/apiUsers.js
import { api } from './api'

class UserApiService {
  handleResponse(response) {
    return response.data;
  }

  handleError(error) {
    const message = error.response?.data?.error || 
                   error.response?.data?.message || 
                   error.response?.data?.detail ||
                   error.message || 
                   'An unexpected error occurred';

    console.error('User API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message
    });

    throw new Error(message);
  }

  /**
   * Get all users with pagination + filters
   */
  async getAll(params = {}) {
    try {
      const response = await api.get('/users/', { params });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getById(userId, includeDeleted = false) {
    try {
      const params = includeDeleted ? { include_deleted: true } : {};
      const response = await api.get(`/users/${userId}/`, { params });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getByEmail(email, includeDeleted = false) {
    try {
      const params = includeDeleted ? { include_deleted: true } : {};
      const response = await api.get(`/users/email/${email}/`, { params });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getByUsername(username, includeDeleted = false) {
    try {
      const params = includeDeleted ? { include_deleted: true } : {};
      const response = await api.get(`/users/username/${username}/`, { params });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async getDeleted(params = {}) {
    try {
      const response = await api.get('/users/deleted/', { params });
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async create(userData) {
    try {
      const response = await api.post('/users/', userData);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async update(userId, userData) {
    try {
      const response = await api.put(`/users/${userId}/`, userData);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async softDelete(userId) {
    try {
      const response = await api.delete(`/users/${userId}/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async restore(userId) {
    try {
      const response = await api.post(`/users/${userId}/restore/`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async hardDelete(userId) {
    try {
      const response = await api.delete(`/users/${userId}/hard-delete/?confirm=yes`);
      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }
}

const userApiService = new UserApiService();
export default userApiService;
