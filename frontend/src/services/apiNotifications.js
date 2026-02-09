import { api } from './api.js';

class NotificationsAPI {

  // Get recent notifications
  async getRecent(params = {}) {
    try {
      const response = await api.get('/notifications/recent/', {
        params: { limit: 10, ...params }
      });
      return response.data;
    } catch (error) {
      console.error("Error fetching recent notifications:", error);
      throw error;
    }
  }

  // Get ALL notifications (active + archived)
  async DisplayNotifs(params = {}) {
    try {
      const response = await api.get('/notifications/all/', {
        params: { include_archived: true, ...params }
      });
      return response.data;
    } catch (error) {
      console.error("Error fetching all notifications:", error);
      throw error;
    }
  }

  // ================================
  // 🔔 NOTIFICATION ACTIONS
  // ================================

  // Mark a single notification as read
  async MarkAsRead(id) {
    try {
      const response = await api.patch(`/notifications/${id}/mark-read/`);
      return response.data;
    } catch (error) {
      console.error("Error marking read:", error);
      throw error;
    }
  }

  // Mark all notifications as read
  async MarkAllAsRead() {
    try {
      const response = await api.patch('/notifications/mark-all-read/');
      return response.data;
    } catch (error) {
      console.error("Error marking all as read:", error);
      throw error;
    }
  }

  // Archive a notification
  async Archive(id) {
    try {
      const response = await api.patch(`/notifications/${id}/archive/`);
      return response.data;
    } catch (error) {
      console.error("Error archiving:", error);
      throw error;
    }
  }

  // Unarchive a notification
  async Unarchive(id) {
    try {
      const response = await api.patch(`/notifications/${id}/unarchive/`);
      return response.data;
    } catch (error) {
      console.error("Error unarchiving:", error);
      throw error;
    }
  }

  // Delete a notification
  async Delete(id) {
    try {
      const response = await api.delete(`/notifications/${id}/delete/`);
      return response.data;
    } catch (error) {
      console.error("Error deleting:", error);
      throw error;
    }
  }
}

// Export singleton instance
const apiNotifications = new NotificationsAPI();
export default apiNotifications;
