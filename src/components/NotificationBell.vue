<!-- components/NotificationBell.vue -->
<template>
  <div class="notification-container">
    <!-- Bell button -->
    <button
      class="notification-bell"
      :class="{ 'has-notifications': unreadCount > 0 }"
      @click="toggleDropdown"
    >
      <BellIcon :size="22" />
      <span v-if="unreadCount > 0" class="notification-badge">
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- Dropdown -->
    <div v-if="showDropdown" class="notification-dropdown" @click.stop>
      <!-- Header -->
      <div class="dropdown-header">
        <h3>Notifications</h3>
        <div class="header-actions">
          <button
            v-if="unreadCount > 0"
            class="mark-all-read"
            :disabled="markingAllAsRead"
            @click="markAllAsRead"
          >
            {{ markingAllAsRead ? 'Marking...' : 'Mark all read' }}
          </button>
          <button class="close-btn" @click="showDropdown = false">
            <XIcon :size="16" />
          </button>
        </div>
      </div>

      <!-- List -->
      <div class="notification-list">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>Loading...</p>
        </div>

        <div v-else-if="notifications.length === 0" class="empty-state">
          <BellOffIcon :size="40" class="empty-icon" />
          <p>No recent notifications</p>
        </div>

        <div v-else>
          <div
            v-for="notification in notifications"
            :key="notification.notification_id"
            class="notification-item"
            :class="{
              unread: !notification.is_read,
              [`priority-${notification.priority}`]: true
            }"
            @click="handleItemClick(notification)"
          >
            <div class="priority-indicator" :class="`priority-${notification.priority}`"></div>

            <div class="notification-content">
              <div class="notification-header">
                <h4>{{ notification.title }}</h4>
                <span class="time-ago">{{ formatTimeAgo(notification.created_at) }}</span>
              </div>
              <p class="notification-message">{{ notification.message }}</p>
              <div class="notification-meta">
                <span class="notification-type">{{ notification.notification_type }}</span>
                <span class="priority-badge" :class="`priority-${notification.priority}`">
                  {{ formatPriority(notification.priority) }}
                </span>
              </div>
            </div>

            <!-- Per-item actions, shown on hover via CSS -->
            <div class="item-actions" @click.stop>
              <button
                v-if="!notification.is_read"
                class="action-btn"
                title="Mark as read"
                @click="markAsRead(notification)"
              >
                <CheckIcon :size="14" />
              </button>
              <button
                class="action-btn"
                title="Archive"
                @click="archiveNotification(notification)"
              >
                <ArchiveIcon :size="14" />
              </button>
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

    <!-- Click-outside overlay -->
    <div
      v-if="showDropdown"
      class="notification-overlay"
      @click="showDropdown = false"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { BellIcon, BellOffIcon, XIcon, CheckIcon, ArchiveIcon } from 'lucide-vue-next'
import apiNotifications from '../services/apiNotifications'

const notifications = ref([])
const unreadCount = ref(0)
const showDropdown = ref(false)
const loading = ref(false)
const markingAllAsRead = ref(false)
let pollInterval = null

// ── Fetching ──────────────────────────────────────────────────────

async function fetchUnreadCount() {
  try {
    const result = await apiNotifications.getUnreadCount()
    if (result?.success) unreadCount.value = result.data?.unread_count ?? 0
  } catch {
    // badge holds last known value until next poll
  }
}

async function fetchNotifications() {
  loading.value = true
  try {
    const result = await apiNotifications.getRecent({ limit: 10 })
    notifications.value = result?.success ? (result.data || []) : []
  } catch {
    notifications.value = []
  } finally {
    loading.value = false
  }
}

// ── UI state ──────────────────────────────────────────────────────

async function toggleDropdown() {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value) {
    await fetchNotifications()
    await fetchUnreadCount()
  }
}

function closeDropdown() {
  showDropdown.value = false
}

// ── Actions ───────────────────────────────────────────────────────

async function handleItemClick(notification) {
  if (!notification.is_read) await markAsRead(notification)
}

async function markAsRead(notification) {
  if (notification.is_read) return
  try {
    await apiNotifications.MarkAsRead(notification.notification_id)
    notification.is_read = true
    if (unreadCount.value > 0) unreadCount.value--
  } catch {
    // next poll will resync badge
  }
}

async function markAllAsRead() {
  if (unreadCount.value === 0) return
  markingAllAsRead.value = true
  try {
    await apiNotifications.MarkAllAsRead()
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
  } catch {
    const unread = notifications.value.filter(n => !n.is_read)
    for (const n of unread) await markAsRead(n)
  } finally {
    markingAllAsRead.value = false
  }
}

async function archiveNotification(notification) {
  try {
    await apiNotifications.Archive(notification.notification_id)
    notifications.value = notifications.value.filter(
      n => n.notification_id !== notification.notification_id
    )
    if (!notification.is_read && unreadCount.value > 0) unreadCount.value--
  } catch {
    // silent — item stays in list until next refresh
  }
}

// ── Polling ───────────────────────────────────────────────────────

function startPolling() {
  // Poll only the lightweight unread count; list refreshes on dropdown open
  pollInterval = setInterval(() => {
    if (!showDropdown.value) fetchUnreadCount()
  }, 30000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

// ── Formatters ────────────────────────────────────────────────────

function formatTimeAgo(dateString) {
  const diff = Math.floor((Date.now() - new Date(dateString)) / 1000)
  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function formatPriority(priority) {
  return { low: 'Low', medium: 'Medium', high: 'High', critical: 'Critical' }[priority] ?? priority
}

// ── Lifecycle ─────────────────────────────────────────────────────

onMounted(() => {
  fetchUnreadCount()
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})
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
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-bell:hover {
  background-color: #f3f4f6;
  color: #374151;
}

.notification-bell.has-notifications {
  color: #6366f1;
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
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  width: 28px;
  height: 28px;
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

.loading-state,
.empty-state {
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
  color: #d1d5db;
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

.notification-item:hover .item-actions {
  opacity: 1;
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

.priority-indicator.priority-low      { background-color: #10b981; }
.priority-indicator.priority-medium   { background-color: #f59e0b; }
.priority-indicator.priority-high     { background-color: #ef4444; }
.priority-indicator.priority-critical {
  background-color: #dc2626;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
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

.priority-badge.priority-low      { background-color: #d1fae5; color: #065f46; }
.priority-badge.priority-medium   { background-color: #fef3c7; color: #92400e; }
.priority-badge.priority-high     { background-color: #fee2e2; color: #991b1b; }
.priority-badge.priority-critical { background-color: #fecaca; color: #7f1d1d; }

.item-actions {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.15s ease;
  margin-left: 0.5rem;
  flex-shrink: 0;
}

.action-btn {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, background-color 0.15s;
}

.action-btn:hover {
  color: #6366f1;
  background-color: #e0e7ff;
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
