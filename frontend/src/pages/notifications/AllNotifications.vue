.notification-item.archived {
  opacity: 0.8;
  background-color: #fafafa;
  border-left: 3px solid #f59e0b;
}

.notification-item.archived:hover {
  background-color: #f3f4f6;
}

.notification-item.archived.unread {
  background-color: #f0f9ff;
}

.notification-item.archived.unread:hover {
  background-color: #e0f2fe;
}

.archived-badge {
  font-size: 0.75rem;
  opacity: 0.8;
  color: #f59e0b;
}

.unarchive-btn {
  color: #f59e0b;
  border-color: #f59e0b;
}

.unarchive-btn:hover:not(:disabled) {
  color: white;
  background: #f59e0b;
  transform: scale(1.05);
}

.delete-btn {
  color: #dc2626;
  border-color: #dc2626;
}

.delete-btn:hover:not(:disabled) {
  color: white;
  background: #dc2626;
  transform: scale(1.05);
}<template>
  <div class="allNotifications-page">
    <!-- Header Section -->
    <div class="page-header">
      <h1 class="page-title">All Notifications</h1>
      <div class="header-actions">
        <!-- Bulk Actions for Unread Notifications -->
        <button 
          v-if="unreadCount > 0"
          @click="markAllAsRead"
          class="bulk-action-btn mark-all-read-btn"
          :disabled="markingAllAsRead"
        >
          <span v-if="!markingAllAsRead">✓</span>
          <span v-else class="spinner-sm"></span>
          {{ markingAllAsRead ? 'Marking...' : `Mark all ${unreadCount} as read` }}
        </button>
        
        <!-- Refresh Button -->
        <button @click="fetchAllNotifications" class="refresh-btn" :disabled="loading">
          <span :class="{ 'spinning': loading }">🔄</span>
          Refresh
        </button>
      </div>
    </div>

    <!-- Filters Section -->
    <div class="filters-section">
      <div class="filter-group">
        <label for="modalFilter">Filter:</label>
        <select id="modalFilter" v-model="modalFilter" @change="applyModalFilters" :disabled="loading">
          <option value="all">All Notifications</option>
          <option value="unread">Unread Only</option>
          <option value="today">Today</option>
          <option value="week">This Week</option>
        </select>
      </div>
      
      <div class="filter-group">
        <label for="priorityFilter">Priority:</label>
        <select id="priorityFilter" v-model="priorityFilter" @change="applyModalFilters" :disabled="loading">
          <option value="">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="typeFilter">Type:</label>
        <select id="typeFilter" v-model="typeFilter" @change="applyModalFilters" :disabled="loading">
          <option value="">All Types</option>
          <option value="system">System</option>
          <option value="inventory">Inventory</option>
          <option value="order">Order</option>
          <option value="payment">Payment</option>
          <option value="promotion">Promotion</option>
          <option value="alert">Alert</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="archiveFilter">Archive Status:</label>
        <select id="archiveFilter" v-model="archiveFilter" @change="applyModalFilters" :disabled="loading">
          <option value="">All Notifications</option>
          <option value="active">Active Only</option>
          <option value="archived">Archived Only</option>
        </select>
      </div>
    </div>

    <!-- Stats Section -->
    <div class="stats-section">
      <div class="stat-card">
        <div class="stat-number">{{ pagination.total_count || 0 }}</div>
        <div class="stat-label">Total</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ unreadCount }}</div>
        <div class="stat-label">Unread</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ archivedCount }}</div>
        <div class="stat-label">Archived</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ filteredModalNotifications.length }}</div>
        <div class="stat-label">Showing</div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading notifications...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredModalNotifications.length === 0" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" class="empty-icon">
          <path d="M12 2C13.1 2 14 2.9 14 4C14 4.74 13.6 5.39 13 5.73V7C13 10.97 16.03 14 20 14V16C16.03 16 13 19.03 13 23H11C11 19.03 7.97 16 4 16V14C7.97 14 11 10.97 11 7V5.73C10.4 5.39 10 4.74 10 4C10 2.9 10.9 2 12 2Z" fill="#d1d5db"/>
        </svg>
        <h3>No notifications found</h3>
        <p>{{ getEmptyStateMessage() }}</p>
      </div>

      <!-- Notifications List -->
      <div v-else class="notifications-list">
        <!-- Pagination Info -->
        <div v-if="pagination.total_count > 0" class="pagination-info">
          Showing {{ filteredModalNotifications.length }} of {{ pagination.total_count }} notifications
          <span v-if="pagination.total_pages > 1">
            (Page {{ pagination.current_page }} of {{ pagination.total_pages }})
          </span>
        </div>

        <!-- Notification Items -->
        <div 
          v-for="notification in filteredModalNotifications" 
          :key="notification.id || notification._id"
          class="notification-item"
          :class="{ 
            'unread': !notification.is_read,
            'archived': notification.archived,
            [`priority-${notification.priority}`]: true,
            'archiving': notification.isArchiving
          }"
        >
          <!-- Priority Indicator -->
          <div class="priority-indicator" :class="`priority-${notification.priority}`"></div>
          
          <!-- Notification Content -->
          <div class="notification-content">
            <div class="notification-header">
              <h4>{{ notification.title }}</h4>
              <div class="notification-actions">
                <span class="time-ago">{{ formatTimeAgo(notification.created_at) }}</span>
                <span v-if="notification.archived" class="archived-badge" title="Archived">📁</span>
                <button 
                  v-if="!notification.is_read"
                  @click="markAsRead(notification)"
                  class="action-btn mark-read-btn"
                  title="Mark as read"
                  :disabled="notification.isMarkingRead"
                >
                  <span v-if="!notification.isMarkingRead">✓</span>
                  <span v-else class="spinner-xs"></span>
                </button>
                <!-- Archive/Unarchive Button -->
                <button 
                  v-if="!notification.archived"
                  @click="archiveNotification(notification)"
                  class="action-btn archive-btn"
                  title="Archive notification"
                  :disabled="notification.isArchiving"
                >
                  <span v-if="!notification.isArchiving">📁</span>
                  <span v-else class="spinner-xs"></span>
                </button>
                <!-- Unarchive Button -->
                <button 
                  v-else
                  @click="unarchiveNotification(notification)"
                  class="action-btn unarchive-btn"
                  title="Unarchive notification"
                  :disabled="notification.isArchiving"
                >
                  <span v-if="!notification.isArchiving">📂</span>
                  <span v-else class="spinner-xs"></span>
                </button>
                <!-- Delete Button (only for archived notifications) -->
                <button 
                  v-if="notification.archived && archiveFilter === 'archived'"
                  @click="deleteNotification(notification)"
                  class="action-btn delete-btn"
                  title="Delete notification permanently"
                  :disabled="notification.isDeleting"
                >
                  <span v-if="!notification.isDeleting">🗑️</span>
                  <span v-else class="spinner-xs"></span>
                </button>
              </div>
            </div>
            
            <p class="notification-message">{{ notification.message }}</p>
            
            <div class="notification-meta">
              <span class="notification-type">{{ notification.notification_type || 'System' }}</span>
              <span class="priority-badge" :class="`priority-${notification.priority}`">
                {{ formatPriority(notification.priority) }}
              </span>
              <span v-if="notification.metadata && notification.metadata.source" class="notification-source">
                {{ notification.metadata.source }}
              </span>
            </div>
          </div>
        </div>

        <!-- Load More Button -->
        <div v-if="pagination.has_next" class="load-more-container">
          <button @click="loadMoreNotifications" class="load-more-btn" :disabled="loadingMore">
            <span v-if="loadingMore" class="spinner-sm"></span>
            {{ loadingMore ? 'Loading...' : 'Load More' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import apiNotif from '@/services/apiNotifications'

export default {
  name: 'AllNotifications',
  data() {
    return {
      modalFilter: 'all',
      priorityFilter: '',
      typeFilter: '',
      archiveFilter: '', 
      allNotifications: [],
      filteredModalNotifications: [],
      loading: false,
      loadingMore: false,
      markingAllAsRead: false,
      pagination: {
        current_page: 1,
        total_pages: 1,
        total_count: 0,
        per_page: 50,
        has_next: false,
        has_previous: false
      }
    }
  },
  
  computed: {
    
  unreadCount() {
    return this.allNotifications.filter(n => !n.is_read).length;
  },
  
  archivedCount() {
    return this.allNotifications.filter(n => n.archived).length;
  }

  },
  
  mounted() {
    this.fetchAllNotifications();
  },
  
  methods: {
    // ================================================================
    // DATA FETCHING METHODS
    // ================================================================
    
    async fetchAllNotifications() {
      this.loading = true;
      try {
        const response = await apiNotif.DisplayNotifs();

        // FIX: DisplayNotifs returns array, not { data: [], pagination: {} }
        this.allNotifications = Array.isArray(response)
          ? response
          : (response.data || []);

        // FIX: pagination is not included in response → compute manually
        this.pagination = {
          current_page: 1,
          total_pages: 1,
          total_count: this.allNotifications.length,
          per_page: this.allNotifications.length,
          has_next: false,
          has_previous: false
        };

        this.applyModalFilters();
      } catch (error) {
        console.error("Error fetching notifications:", error);
        this.allNotifications = [];
        this.filteredModalNotifications = [];
      } finally {
        this.loading = false;
      }
    },


    async loadMoreNotifications() {
      if (!this.pagination.has_next || this.loadingMore) return;
      
      this.loadingMore = true;
      try {
        const nextPage = this.pagination.current_page + 1;
        const response = await fetch(`http://localhost:8000/api/v1/notifications/all/?page=${nextPage}&limit=50`, {
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const result = await response.json();
          
          if (result.success) {
            this.allNotifications = [...this.allNotifications, ...(result.data || [])];
            this.pagination = result.pagination || this.pagination;
            this.applyModalFilters();
          }
        }
      } catch (error) {
        console.error('Error loading more notifications:', error);
      } finally {
        this.loadingMore = false;
      }
    },

    // ================================================================
    // NOTIFICATION ACTIONS
    // ================================================================
    
    async markAsRead(notification) {
      if (notification.is_read) return;

      notification.isMarkingRead = true;
      const id = notification.id || notification._id;

      try {
        await apiNotif.MarkAsRead(id);
        notification.is_read = true;
        this.applyModalFilters();
      } catch (error) {
        console.error("Error marking read:", error);
      } finally {
        notification.isMarkingRead = false;
      }
    },


    async archiveNotification(notification) {
      const notificationId = notification.id || notification._id;
      
      if (!notificationId) {
        console.error('No valid ID found for notification');
        return;
      }

      notification.isArchiving = true;

      try {
        const response = await fetch(`http://localhost:8000/api/v1/notifications/${notificationId}/archive/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          // Update the notification status instead of removing
          notification.archived = true;
          
          // Update in allNotifications array
          const allNotificationIndex = this.allNotifications.findIndex(n => (n.id || n._id) === notificationId);
          if (allNotificationIndex !== -1) {
            this.allNotifications[allNotificationIndex].archived = true;
          }
          
          this.applyModalFilters();
        } else {
          console.error('Archive failed:', await response.text());
        }
      } catch (error) {
        console.error('Archive error:', error);
      } finally {
        notification.isArchiving = false;
      }
    },

    async unarchiveNotification(notification) {
      const notificationId = notification.id || notification._id;
      
      if (!notificationId) {
        console.error('No valid ID found for notification');
        return;
      }

      notification.isArchiving = true;

      try {
        const response = await fetch(`http://localhost:8000/api/v1/notifications/${notificationId}/unarchive/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          // Update the notification status
          notification.archived = false;
          
          // Update in allNotifications array
          const allNotificationIndex = this.allNotifications.findIndex(n => (n.id || n._id) === notificationId);
          if (allNotificationIndex !== -1) {
            this.allNotifications[allNotificationIndex].archived = false;
          }
          
          this.applyModalFilters();
        } else {
          console.error('Unarchive failed:', await response.text());
        }
      } catch (error) {
        console.error('Unarchive error:', error);
      } finally {
        notification.isArchiving = false;
      }
    },

    async deleteNotification(notification) {
      const notificationId = notification.id || notification._id;
      
      if (!notificationId) {
        console.error('No valid ID found for notification');
        return;
      }

      // Confirm deletion
      if (!confirm('Are you sure you want to permanently delete this notification? This action cannot be undone.')) {
        return;
      }

      notification.isDeleting = true;

      try {
        const response = await fetch(`http://localhost:8000/api/v1/notifications/${notificationId}/delete/`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          // Remove from both arrays
          this.allNotifications = this.allNotifications.filter(n => (n.id || n._id) !== notificationId);
          this.applyModalFilters();
        } else {
          console.error('Delete failed:', await response.text());
        }
      } catch (error) {
        console.error('Delete error:', error);
      } finally {
        notification.isDeleting = false;
      }
    },

    async markAllAsRead() {
      if (this.unreadCount === 0) return;

      this.markingAllAsRead = true;
      try {
        await apiNotif.MarkAllAsRead();

        // update local state
        this.allNotifications.forEach(n => n.is_read = true);

        this.applyModalFilters();
      } catch (error) {
        console.error("Failed mark all read:", error);
      } finally {
        this.markingAllAsRead = false;
      }
    },


    // ================================================================
    // FALLBACK METHODS
    // ================================================================
    
    async deleteNotificationFallback(notification) {
      try {
        const notificationId = notification.id || notification._id;
        const response = await fetch(`http://localhost:8000/api/notifications/${notificationId}/delete/`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          this.allNotifications = this.allNotifications.filter(n => (n.id || n._id) !== notificationId);
          this.applyModalFilters();
        } else {
          console.error('Delete fallback also failed:', await response.text());
        }
      } catch (error) {
        console.error('Delete fallback error:', error);
      }
    },

    // ================================================================
    // FILTERING METHODS
    // ================================================================
    
    applyModalFilters() {
      let filtered = [...this.allNotifications];

      // Apply archive filter first
      if (this.archiveFilter === 'active') {
        filtered = filtered.filter(n => !n.archived);
      } else if (this.archiveFilter === 'archived') {
        filtered = filtered.filter(n => n.archived);
      }
      // If archiveFilter is empty, show all (archived and non-archived)

      // Apply read/unread filter
      if (this.modalFilter === 'unread') {
        filtered = filtered.filter(n => !n.is_read);
      } else if (this.modalFilter === 'today') {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        filtered = filtered.filter(n => {
          const notificationDate = new Date(n.created_at);
          return notificationDate >= today;
        });
      } else if (this.modalFilter === 'week') {
        const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        filtered = filtered.filter(n => {
          const notificationDate = new Date(n.created_at);
          return notificationDate >= weekAgo;
        });
      }

      // Apply priority filter
      if (this.priorityFilter) {
        filtered = filtered.filter(n => n.priority === this.priorityFilter);
      }

      // Apply type filter
      if (this.typeFilter) {
        filtered = filtered.filter(n => n.notification_type === this.typeFilter);
      }

      this.filteredModalNotifications = filtered;
    },

    // ================================================================
    // UTILITY METHODS
    // ================================================================
    
    formatTimeAgo(dateString) {
      const now = new Date();
      const notificationDate = new Date(dateString);
      const diffInSeconds = Math.floor((now - notificationDate) / 1000);

      if (diffInSeconds < 60) {
        return 'Just now';
      } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes}m ago`;
      } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours}h ago`;
      } else {
        const days = Math.floor(diffInSeconds / 86400);
        return `${days}d ago`;
      }
    },

    formatPriority(priority) {
      const priorities = {
        low: 'Low',
        medium: 'Medium',
        high: 'High',
        urgent: 'Urgent'
      };
      return priorities[priority] || priority;
    },

    getEmptyStateMessage() {
      if (this.archiveFilter === 'active') {
        return "No active notifications found.";
      } else if (this.archiveFilter === 'archived') {
        return "No archived notifications found.";
      } else if (this.modalFilter === 'unread') {
        return "You're all caught up! No unread notifications.";
      } else if (this.modalFilter === 'today') {
        return "No notifications from today.";
      } else if (this.modalFilter === 'week') {
        return "No notifications from this week.";
      } else if (this.priorityFilter) {
        return `No ${this.priorityFilter} priority notifications found.`;
      } else if (this.typeFilter) {
        return `No ${this.typeFilter} notifications found.`;
      }
      return "You're all caught up!";
    }
  }
}
</script>

<style scoped>
.allNotifications-page {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.bulk-action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.mark-all-read-btn {
  background: #10b981;
  color: white;
}

.mark-all-read-btn:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
}

.mark-all-read-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.filters-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  margin-bottom: 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  align-items: end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-group label {
  font-weight: 500;
  color: #374151;
  font-size: 0.875rem;
}

.filter-group select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.filter-group select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  text-align: center;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  text-transform: uppercase;
  font-weight: 500;
  letter-spacing: 0.05em;
}

.main-content {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #6b7280;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-xs {
  width: 12px;
  height: 12px;
  border: 1px solid #e5e7eb;
  border-top: 1px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.empty-icon {
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: #374151;
}

.pagination-info {
  padding: 1rem 1.5rem;
  font-size: 0.875rem;
  color: #6b7280;
  border-bottom: 1px solid #f3f4f6;
}

.notifications-list {
  padding: 0;
}

.notification-item {
  display: flex;
  padding: 1.5rem;
  border-bottom: 1px solid #f3f4f6;
  transition: all 0.2s;
  position: relative;
}

.notification-item:hover {
  background-color: #f9fafb;
}

.notification-item.unread {
  background-color: #eff6ff;
}

.notification-item.unread:hover {
  background-color: #dbeafe;
}

.notification-item.archiving {
  opacity: 0.6;
  transform: scale(0.98);
}

.priority-indicator {
  width: 4px;
  border-radius: 2px;
  margin-right: 1rem;
  flex-shrink: 0;
}

.priority-indicator.priority-low {
  background-color: #10b981;
}

.priority-indicator.priority-medium {
  background-color: #f59e0b;
}

.priority-indicator.priority-high {
  background-color: #ef4444;
}

.priority-indicator.priority-urgent {
  background-color: #dc2626;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 0.75rem;
}

.notification-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.notification-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.time-ago {
  font-size: 0.75rem;
  color: #6b7280;
  flex-shrink: 0;
}

.action-btn {
  background: none;
  border: 1px solid;
  border-radius: 6px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
  font-weight: 500;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mark-read-btn {
  color: #10b981;
  border-color: #10b981;
}

.mark-read-btn:hover:not(:disabled) {
  color: white;
  background: #10b981;
  transform: scale(1.05);
}

.archive-btn {
  color: #ef4444;
  border-color: #ef4444;
}

.archive-btn:hover:not(:disabled) {
  color: white;
  background: #ef4444;
  transform: scale(1.05);
}

.notification-message {
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
  color: #4b5563;
  line-height: 1.5;
}

.notification-meta {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.notification-type {
  font-size: 0.75rem;
  color: #6b7280;
  text-transform: capitalize;
}

.priority-badge {
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-weight: 500;
}

.priority-badge.priority-low {
  background-color: #d1fae5;
  color: #065f46;
}

.priority-badge.priority-medium {
  background-color: #fef3c7;
  color: #92400e;
}

.priority-badge.priority-high {
  background-color: #fee2e2;
  color: #991b1b;
}

.priority-badge.priority-urgent {
  background-color: #fecaca;
  color: #7f1d1d;
}

.notification-source {
  font-size: 0.75rem;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
}

.load-more-container {
  text-align: center;
  padding: 2rem;
  border-top: 1px solid #f3f4f6;
}

.load-more-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin: 0 auto;
}

.load-more-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

.load-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.notification-item.archived {
  opacity: 0.8;
  background-color: #fafafa;
  border-left: 3px solid #f59e0b;
}

.notification-item.archived:hover {
  background-color: #f3f4f6;
}

.notification-item.archived.unread {
  background-color: #f0f9ff;
}

.notification-item.archived.unread:hover {
  background-color: #e0f2fe;
}

.archived-badge {
  font-size: 0.75rem;
  opacity: 0.8;
  color: #f59e0b;
}

.unarchive-btn {
  color: #f59e0b;
  border-color: #f59e0b;
}

.unarchive-btn:hover:not(:disabled) {
  color: white;
  background: #f59e0b;
  transform: scale(1.05);
}

.delete-btn {
  color: #dc2626;
  border-color: #dc2626;
}

.delete-btn:hover:not(:disabled) {
  color: white;
  background: #dc2626;
  transform: scale(1.05);
}

@media (max-width: 768px) {
  .allNotifications-page {
    padding: 1rem;
  }
  
  .page-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .header-actions {
    justify-content: space-between;
  }
  
  .filters-section {
    grid-template-columns: 1fr;
  }
  
  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .notification-actions {
    flex-direction: column;
    gap: 0.25rem;
  }
  
  .bulk-action-btn {
    font-size: 0.875rem;
    padding: 0.5rem 1rem;
  }
}</style>