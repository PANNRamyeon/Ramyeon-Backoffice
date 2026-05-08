import axios from 'axios';

// Notifications are mounted at /api/v1/notifications/, not under /admin/
const NOTIF_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1')
  .replace(/\/admin\/?$/, '') + '/notifications';

const notifApi = axios.create({
  baseURL: NOTIF_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  }
});

notifApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

class NotificationsAPI {

  // ─── Retrieval ──────────────────────────────────────────────────

  async getRecent(params = {}) {
    try {
      const response = await notifApi.get('/recent/', { params: { limit: 10, ...params } });
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) return { success: true, data: [] };
      console.error('Error fetching recent notifications:', error);
      throw error;
    }
  }

  async getList(params = {}) {
    try {
      const response = await notifApi.get('/list/', { params });
      return response.data;
    } catch (error) {
      console.error('Error listing notifications:', error);
      throw error;
    }
  }

  async getById(id, includeArchived = false) {
    try {
      const response = await notifApi.get(`/get/${id}/`, {
        params: includeArchived ? { include_archived: 'true' } : {}
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching notification ${id}:`, error);
      throw error;
    }
  }

  // Get ALL notifications (active + archived) — include_archived now forwarded by backend
  async DisplayNotifs(params = {}) {
    try {
      const response = await notifApi.get('/all/', {
        params: { include_archived: 'true', ...params }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching all notifications:', error);
      throw error;
    }
  }

  async getUnreadCount() {
    try {
      const response = await notifApi.get('/unread-count/');
      return response.data;
    } catch (error) {
      console.error('Error fetching unread count:', error);
      throw error;
    }
  }

  // ─── Creation ───────────────────────────────────────────────────

  async createNotification(data) {
    try {
      const response = await notifApi.post('/create/', data);
      return response.data;
    } catch (error) {
      console.error('Error creating notification:', error);
      throw error;
    }
  }

  async createInventoryAlert(data) {
    try {
      const response = await notifApi.post('/create-inventory-alert/', data);
      return response.data;
    } catch (error) {
      console.error('Error creating inventory alert:', error);
      throw error;
    }
  }

  // ─── Status updates ─────────────────────────────────────────────

  async MarkAsRead(id) {
    try {
      const response = await notifApi.patch(`/mark-read/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error marking read:', error);
      throw error;
    }
  }

  async MarkAsUnread(id) {
    try {
      const response = await notifApi.patch(`/mark-unread/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error marking unread:', error);
      throw error;
    }
  }

  async MarkAllAsRead() {
    try {
      const response = await notifApi.patch('/mark-all-read/');
      return response.data;
    } catch (error) {
      console.error('Error marking all as read:', error);
      throw error;
    }
  }

  // ─── Archive ────────────────────────────────────────────────────

  async Archive(id) {
    try {
      const response = await notifApi.patch(`/archive/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error archiving:', error);
      throw error;
    }
  }

  async Unarchive(id) {
    try {
      const response = await notifApi.patch(`/unarchive/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error unarchiving:', error);
      throw error;
    }
  }

  // ─── Deletion ───────────────────────────────────────────────────

  async Delete(id) {
    try {
      const response = await notifApi.delete(`/delete/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error deleting:', error);
      throw error;
    }
  }
}

const apiNotifications = new NotificationsAPI();
export default apiNotifications;
