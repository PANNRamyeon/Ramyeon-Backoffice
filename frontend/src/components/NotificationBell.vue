<!-- components/NotificationBell.vue -->
<template>
  <div class="notification-container">
    <!-- Notification Bell Icon -->
    <button 
      class="notification-bell"
      @click="toggleDropdown"
      :class="{ 'has-notifications': unreadCount > 0 }"
    >
      <span class="bell-icon">
        🔔
      </span>
      
      <!-- Notification Badge -->   
      <span 
        v-if="unreadCount > 0" 
        class="notification-badge"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- Notification Dropdown -->
    <div 
      v-if="showDropdown" 
      class="notification-dropdown"
      @click.stop
    >
      <!-- Header -->
      <div class="dropdown-header">
        <h3>Recent Notifications</h3>
        <div class="header-actions">
          <button 
            v-if="unreadCount > 0"
            @click="markAllAsRead"
            class="mark-all-read"
            :disabled="markingAllAsRead"
          >
            {{ markingAllAsRead ? 'Marking...' : 'Mark all read' }}
          </button>
          <button @click="showDropdown = false" class="close-btn">
            ✕
          </button>
        </div>
      </div>

      <!-- Notification List -->
      <div class="notification-list">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>Loading notifications...</p>
        </div>

        <div v-else-if="notifications.length === 0" class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" class="empty-icon">
            <path d="M12 2C13.1 2 14 2.9 14 4C14 4.74 13.6 5.39 13 5.73V7C13 10.97 16.03 14 20 14V16C20 16.55 19.55 17 19 17H5C4.45 17 4 16.55 4 16V14C7.97 14 11 10.97 11 7V5.73C10.4 5.39 10 4.74 10 4C10 2.9 10.9 2 12 2Z" fill="#d1d5db"/>
          </svg>
          <p>No recent notifications</p>
        </div>

        <div v-else>
          <div 
            v-for="notification in notifications" 
            :key="notification.id"
            class="notification-item"
            :class="{ 
              'unread': !notification.is_read,
              [`priority-${notification.priority}`]: true 
            }"
            @click="markAsRead(notification)"
          >
            <!-- Priority Indicator -->
            <div class="priority-indicator" :class="`priority-${notification.priority}`"></div>
            
            <!-- Notification Content -->
            <div class="notification-content">
              <div class="notification-header">
                <h4>{{ notification.title }}</h4>
                <span class="time-ago">{{ formatTimeAgo(notification.created_at) }}</span>
              </div>
              <p class="notification-message">{{ notification.message }}</p>
              <div class="notification-meta">
                <span class="notification-type">{{ notification.notification_type || 'System' }}</span>
                <span class="priority-badge" :class="`priority-${notification.priority}`">
                  {{ formatPriority(notification.priority) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="dropdown-footer">
        <router-link to="/allNotifications" class="view-all-btn" @click="closeDropdown">
          View All Notifications
        </router-link>
      </div>
    </div>

    <!-- Overlay to close dropdown -->
    <div 
      v-if="showDropdown" 
      class="notification-overlay"
      @click="showDropdown = false"
    ></div>
  </div>
</template>

<script>
import apiNotifications from '../services/apiNotifications'
export default {
  name: 'NotificationBell',
  data() {
    return {
      notifications: [],
      unreadCount: 0,
      showDropdown: false,
      loading: false,
      markingAllAsRead: false,
      pollInterval: null
    }
  },
  
  mounted() {
    this.fetchNotifications()
    this.startPolling()
  },
  
  beforeUnmount() {
    this.stopPolling()
  },
  
  methods: {
    // ================================================================
    // DATA FETCHING METHODS
    // ================================================================
    
    async fetchNotifications() {
      this.loading = true
      try {
        const result = await apiNotifications.getRecent()
        
        if (result.success) {
          this.notifications = result.data || []
          this.updateUnreadCount()
        } else {
          this.notifications = []
        }
      } catch (error) {
        this.notifications = []
      } finally {
        this.loading = false
      }
    },

    // ================================================================
    // UI STATE MANAGEMENT
    // ================================================================
    
    updateUnreadCount() {
      this.unreadCount = this.notifications.filter(n => !n.is_read).length
    },

    toggleDropdown() {
      this.showDropdown = !this.showDropdown
      if (this.showDropdown) {
        this.fetchNotifications() // Always fetch fresh data when opening dropdown
      }
    },

    closeDropdown() {
      this.showDropdown = false
    },

    // ================================================================
    // NOTIFICATION ACTIONS
    // ================================================================
    
    async markAsRead(notification) {
      if (notification.is_read) return

      const notificationId = notification.id || notification._id;
      
      // Vue 3 way - direct assignment
      notification.isMarkingRead = true;

      try {
        await apiNotifications.MarkAsRead(notificationId)
        notification.is_read = true
        this.updateUnreadCount()
      } catch (error) {
        // Error marking notification as read
      } finally {
        // Vue 3 way - direct assignment
        notification.isMarkingRead = false;
      }
    },

    async markAllAsRead() {
      if (this.unreadCount === 0) return
      
      this.markingAllAsRead = true
      try {
        await apiNotifications.MarkAllAsRead()
        
        // Update all notifications to read status
        this.notifications.forEach(notification => {
          notification.is_read = true
        })
        
        // Update counts
        this.unreadCount = 0
      } catch (error) {
        await this.fallbackMarkAllAsRead()
      } finally {
        this.markingAllAsRead = false
      }
    },

    async fallbackMarkAllAsRead() {
      const unreadNotifications = this.notifications.filter(n => !n.is_read)
      for (const notification of unreadNotifications) {
        await this.markAsRead(notification)
      }
    },

    // ================================================================
    // POLLING AND BACKGROUND UPDATES
    // ================================================================
    
    startPolling() {
      // Poll for new notifications every 30 seconds
      this.pollInterval = setInterval(() => {
        if (!this.showDropdown) {
          this.fetchNotifications()
        }
      }, 30000)
    },

    stopPolling() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },

    // ================================================================
    // UTILITY METHODS
    // ================================================================
    
    formatTimeAgo(dateString) {
      const now = new Date()
      const notificationDate = new Date(dateString)
      const diffInSeconds = Math.floor((now - notificationDate) / 1000)

      if (diffInSeconds < 60) {
        return 'Just now'
      } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60)
        return `${minutes}m ago`
      } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600)
        return `${hours}h ago`
      } else {
        const days = Math.floor(diffInSeconds / 86400)
        return `${days}d ago`
      }
    },

    formatPriority(priority) {
      const priorities = {
        low: 'Low',
        medium: 'Medium',
        high: 'High',
        urgent: 'Urgent'
      }
      return priorities[priority] || priority
    }
  }
}
</script>

<style scoped>
.notification-container {
  position: relative;
}

.notification-bell {
  position: relative;
  background: none;
  border: none;
  padding: 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #6b7280;
}

.notification-bell:hover {
  background-color: #f3f4f6;
  color: #374151;
}

.notification-bell.has-notifications {
  color: #6366f1;
}

.bell-icon {
  font-size: 24px;
}

.notification-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  background-color: #ef4444;
  color: white;
  border-radius: 10px;
  padding: 2px 6px;
  font-size: 0.75rem;
  font-weight: 600;
  min-width: 18px;
  text-align: center;
  line-height: 1.2;
}

.notification-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  border: 1px solid #e5e7eb;
  width: 400px;
  max-height: 500px;
  z-index: 1000;
  overflow: hidden;
}

.notification-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.dropdown-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.mark-all-read {
  background: none;
  border: none;
  color: #6366f1;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.mark-all-read:hover:not(:disabled) {
  background-color: #e0e7ff;
}

.mark-all-read:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.close-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background-color: #f3f4f6;
  color: #374151;
}

.notification-list {
  max-height: 350px;
  overflow-y: auto;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #6b7280;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 0.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  margin-bottom: 0.5rem;
}

.notification-item {
  display: flex;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  transition: background-color 0.2s;
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

.priority-indicator {
  width: 4px;
  border-radius: 2px;
  margin-right: 0.75rem;
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
  margin-bottom: 0.5rem;
}

.notification-header h4 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.time-ago {
  font-size: 0.75rem;
  color: #6b7280;
  flex-shrink: 0;
  margin-left: 0.5rem;
}

.notification-message {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: #4b5563;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notification-meta {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.notification-type {
  font-size: 0.75rem;
  color: #6b7280;
  text-transform: capitalize;
}

.priority-badge {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
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

.dropdown-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.view-all-btn {
  display: block;
  width: 100%;
  background-color: #6366f1;
  color: white;
  border: none;
  padding: 0.75rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  text-decoration: none;
  text-align: center;
}

.view-all-btn:hover {
  background-color: #4f46e5;
  color: white;
  text-decoration: none;
}

@media (max-width: 768px) {
  .notification-dropdown {
    width: 350px;
    max-width: 90vw;
  }
}
</style>