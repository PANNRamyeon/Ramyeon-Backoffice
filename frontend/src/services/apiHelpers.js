// services/apiHelpers.js
import api from './api';

export const apiHelpers = {
  // GET request
  get: (url, params = {}) => api.get(url, { params }),
  
  // POST request
  post: (url, data = {}) => api.post(url, data),
  
  // PUT request
  put: (url, data = {}) => api.put(url, data),
  
  // PATCH request
  patch: (url, data = {}) => api.patch(url, data),
  
  // DELETE request
  delete: (url) => api.delete(url),
  
  // File upload with progress tracking
  uploadFile: (url, formData, onUploadProgress) => {
    return api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onUploadProgress(percentCompleted);
        }
      },
    });
  },
  
  // Set auth token
  setAuthToken: (token) => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('authToken', token);
    } else {
      delete api.defaults.headers.common['Authorization'];
      localStorage.removeItem('authToken');
    }
  },
  
  // For handling offline requests (to be synced later)
  queueOfflineRequest: (request) => {
    const offlineQueue = JSON.parse(localStorage.getItem('offlineQueue') || '[]');
    offlineQueue.push({
      ...request,
      timestamp: Date.now()
    });
    localStorage.setItem('offlineQueue', JSON.stringify(offlineQueue));
  },
  
  // Sync offline requests when back online
  syncOfflineRequests: async () => {
    const offlineQueue = JSON.parse(localStorage.getItem('offlineQueue') || '[]');
    
    for (const request of offlineQueue) {
      try {
        await api(request);
      } catch (error) {
        console.error('Failed to sync offline request:', error);
      }
    }
    
    localStorage.removeItem('offlineQueue');
  }
};

// Listen for online/offline events
window.addEventListener('online', () => {
  apiHelpers.syncOfflineRequests();
});

window.addEventListener('offline', () => {
  // Requests will be queued
});

export default apiHelpers;