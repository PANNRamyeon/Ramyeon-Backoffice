<template>
  <div class="allNotifications-page">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">All Notifications</h1>
      <div class="header-actions">
        <button
          v-if="unreadCount > 0"
          class="bulk-action-btn mark-all-read-btn"
          :disabled="markingAllAsRead"
          @click="markAllAsRead"
        >
          <div v-if="markingAllAsRead" class="spinner-sm"></div>
          <CheckIcon v-else :size="16" />
          {{ markingAllAsRead ? 'Marking...' : `Mark all ${unreadCount} as read` }}
        </button>

        <button class="refresh-btn" :disabled="loading" @click="fetchAllNotifications">
          <RefreshCwIcon :size="16" :class="{ spinning: loading }" />
          Refresh
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-section">
      <div class="filter-group">
        <label for="modalFilter">Filter:</label>
        <select id="modalFilter" v-model="modalFilter" :disabled="loading" @change="applyFilters">
          <option value="all">All Notifications</option>
          <option value="unread">Unread Only</option>
          <option value="today">Today</option>
          <option value="week">This Week</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="priorityFilter">Priority:</label>
        <select id="priorityFilter" v-model="priorityFilter" :disabled="loading" @change="applyFilters">
          <option value="">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="typeFilter">Type:</label>
        <select id="typeFilter" v-model="typeFilter" :disabled="loading" @change="applyFilters">
          <option value="">All Types</option>
          <option value="system">System</option>
          <option value="inventory">Inventory</option>
          <option value="order">Order</option>
          <option value="promotion">Promotion</option>
          <option value="alert">Alert</option>
          <option value="security">Security</option>
          <option value="reminder">Reminder</option>
          <option value="user">User</option>
          <option value="maintenance">Maintenance</option>
          <option value="update">Update</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="archiveFilter">Archive Status:</label>
        <select id="archiveFilter" v-model="archiveFilter" :disabled="loading" @change="applyFilters">
          <option value="">All Notifications</option>
          <option value="active">Active Only</option>
          <option value="archived">Archived Only</option>
        </select>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-section">
      <div class="stat-card">
        <div class="stat-number">{{ allNotifications.length }}</div>
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
        <div class="stat-number">{{ filtered.length }}</div>
        <div class="stat-label">Showing</div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading notifications...</p>
      </div>

      <div v-else-if="filtered.length === 0" class="empty-state">
        <BellOffIcon :size="56" class="empty-icon" />
        <h3>No notifications found</h3>
        <p>{{ emptyStateMessage }}</p>
      </div>

      <div v-else class="notifications-list">
        <div class="pagination-info">
          Showing {{ filtered.length }} of {{ allNotifications.length }} notifications
        </div>

        <div
          v-for="notification in filtered"
          :key="notification.notification_id"
          class="notification-item"
          :class="{
            unread: !notification.is_read,
            archived: notification.archived,
            archiving: notification._busy
          }"
        >
          <div class="priority-indicator" :class="`priority-${notification.priority}`"></div>

          <div class="notification-content">
            <div class="notification-header">
              <h4>{{ notification.title }}</h4>
              <div class="notification-actions">
                <span class="time-ago">{{ formatTimeAgo(notification.created_at) }}</span>

                <span v-if="notification.archived" class="archived-badge" title="Archived">
                  <ArchiveIcon :size="13" />
                </span>

                <button
                  v-if="!notification.is_read"
                  class="action-btn mark-read-btn"
                  title="Mark as read"
                  :disabled="notification._busy"
                  @click="markAsRead(notification)"
                >
                  <div v-if="notification._busy" class="spinner-xs"></div>
                  <CheckIcon v-else :size="14" />
                </button>

                <button
                  v-if="!notification.archived"
                  class="action-btn archive-btn"
                  title="Archive"
                  :disabled="notification._busy"
                  @click="archiveNotification(notification)"
                >
                  <div v-if="notification._busy" class="spinner-xs"></div>
                  <ArchiveIcon v-else :size="14" />
                </button>

                <button
                  v-else
                  class="action-btn unarchive-btn"
                  title="Unarchive"
                  :disabled="notification._busy"
                  @click="unarchiveNotification(notification)"
                >
                  <div v-if="notification._busy" class="spinner-xs"></div>
                  <ArchiveRestoreIcon v-else :size="14" />
                </button>

                <button
                  v-if="notification.archived && archiveFilter === 'archived'"
                  class="action-btn delete-btn"
                  title="Delete permanently"
                  :disabled="notification._busy"
                  @click="deleteNotification(notification)"
                >
                  <div v-if="notification._busy" class="spinner-xs"></div>
                  <Trash2Icon v-else :size="14" />
                </button>
              </div>
            </div>

            <p class="notification-message">{{ notification.message }}</p>

            <div class="notification-meta">
              <span class="notification-type">{{ notification.notification_type }}</span>
              <span class="priority-badge" :class="`priority-${notification.priority}`">
                {{ formatPriority(notification.priority) }}
              </span>
              <span v-if="notification.metadata?.source" class="notification-source">
                {{ notification.metadata.source }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <DeleteConfirmationModal ref="confirmModal" @confirm="handleConfirm" />
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  CheckIcon, RefreshCwIcon, BellOffIcon,
  ArchiveIcon, ArchiveRestoreIcon, Trash2Icon
} from 'lucide-vue-next'
import apiNotifications from '@/services/apiNotifications'
import DeleteConfirmationModal from '@/components/common/DeleteConfirmationModal.vue'

// ── State ─────────────────────────────────────────────────────────

const allNotifications = ref([])
const filtered = ref([])
const loading = ref(false)
const markingAllAsRead = ref(false)
const confirmModal = ref(null)
const pendingAction = ref(null)

const openConfirm = (options, action) => {
  pendingAction.value = action
  confirmModal.value?.openModal(options)
}

const handleConfirm = async () => {
  await pendingAction.value?.()
  pendingAction.value = null
  confirmModal.value?.closeModal()
}

const modalFilter = ref('all')
const priorityFilter = ref('')
const typeFilter = ref('')
const archiveFilter = ref('')

// ── Computed ──────────────────────────────────────────────────────

const unreadCount = computed(() => allNotifications.value.filter(n => !n.is_read).length)
const archivedCount = computed(() => allNotifications.value.filter(n => n.archived).length)

const emptyStateMessage = computed(() => {
  if (archiveFilter.value === 'active') return 'No active notifications found.'
  if (archiveFilter.value === 'archived') return 'No archived notifications found.'
  if (modalFilter.value === 'unread') return "You're all caught up! No unread notifications."
  if (modalFilter.value === 'today') return 'No notifications from today.'
  if (modalFilter.value === 'week') return 'No notifications from this week.'
  if (priorityFilter.value) return `No ${priorityFilter.value} priority notifications found.`
  if (typeFilter.value) return `No ${typeFilter.value} notifications found.`
  return "You're all caught up!"
})

// ── Fetching ──────────────────────────────────────────────────────

async function fetchAllNotifications() {
  loading.value = true
  try {
    const response = await apiNotifications.DisplayNotifs()
    allNotifications.value = response?.data || []
    applyFilters()
  } catch (error) {
    console.error('Error fetching notifications:', error)
    allNotifications.value = []
    filtered.value = []
  } finally {
    loading.value = false
  }
}

// ── Filtering ─────────────────────────────────────────────────────

function applyFilters() {
  let result = [...allNotifications.value]

  if (archiveFilter.value === 'active') result = result.filter(n => !n.archived)
  else if (archiveFilter.value === 'archived') result = result.filter(n => n.archived)

  if (modalFilter.value === 'unread') {
    result = result.filter(n => !n.is_read)
  } else if (modalFilter.value === 'today') {
    const today = new Date(); today.setHours(0, 0, 0, 0)
    result = result.filter(n => new Date(n.created_at) >= today)
  } else if (modalFilter.value === 'week') {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    result = result.filter(n => new Date(n.created_at) >= weekAgo)
  }

  if (priorityFilter.value) result = result.filter(n => n.priority === priorityFilter.value)
  if (typeFilter.value) result = result.filter(n => n.notification_type === typeFilter.value)

  filtered.value = result
}

// ── Actions ───────────────────────────────────────────────────────

async function markAsRead(notification) {
  if (notification.is_read || notification._busy) return
  notification._busy = true
  try {
    await apiNotifications.MarkAsRead(notification.notification_id)
    notification.is_read = true
    applyFilters()
  } catch (error) {
    console.error('Error marking read:', error)
  } finally {
    notification._busy = false
  }
}

async function markAllAsRead() {
  if (unreadCount.value === 0) return
  markingAllAsRead.value = true
  try {
    await apiNotifications.MarkAllAsRead()
    allNotifications.value.forEach(n => { n.is_read = true })
    applyFilters()
  } catch (error) {
    console.error('Error marking all read:', error)
  } finally {
    markingAllAsRead.value = false
  }
}

async function archiveNotification(notification) {
  if (notification._busy) return
  notification._busy = true
  try {
    await apiNotifications.Archive(notification.notification_id)
    notification.archived = true
    applyFilters()
  } catch (error) {
    console.error('Error archiving:', error)
  } finally {
    notification._busy = false
  }
}

async function unarchiveNotification(notification) {
  if (notification._busy) return
  notification._busy = true
  try {
    await apiNotifications.Unarchive(notification.notification_id)
    notification.archived = false
    applyFilters()
  } catch (error) {
    console.error('Error unarchiving:', error)
  } finally {
    notification._busy = false
  }
}

function deleteNotification(notification) {
  if (notification._busy) return
  openConfirm({
    title: 'Delete Notification',
    message: 'Permanently delete this notification? This action cannot be undone.',
    confirmText: 'Delete',
    confirmClass: 'btn-delete'
  }, async () => {
    notification._busy = true
    try {
      await apiNotifications.Delete(notification.notification_id)
      allNotifications.value = allNotifications.value.filter(
        n => n.notification_id !== notification.notification_id
      )
      applyFilters()
    } catch (error) {
      console.error('Error deleting:', error)
    } finally {
      notification._busy = false
    }
  })
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

onMounted(fetchAllNotifications)
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

.refresh-btn:hover:not(:disabled) { background: #e5e7eb; }
.refresh-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.spinning { animation: spin 1s linear infinite; }

@keyframes spin { to { transform: rotate(360deg); } }

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

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #6b7280;
}

.empty-icon { margin-bottom: 1rem; color: #d1d5db; }

.empty-state h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: #374151;
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
  border: 2px solid rgba(255,255,255,0.4);
  border-top: 2px solid white;
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

.pagination-info {
  padding: 1rem 1.5rem;
  font-size: 0.875rem;
  color: #6b7280;
  border-bottom: 1px solid #f3f4f6;
}

.notifications-list { padding: 0; }

.notification-item {
  display: flex;
  padding: 1.5rem;
  border-bottom: 1px solid #f3f4f6;
  transition: all 0.2s;
}

.notification-item:hover { background-color: #f9fafb; }
.notification-item.unread { background-color: #eff6ff; }
.notification-item.unread:hover { background-color: #dbeafe; }

.notification-item.archived {
  opacity: 0.8;
  background-color: #fafafa;
  border-left: 3px solid #f59e0b;
}

.notification-item.archived:hover { background-color: #f3f4f6; }
.notification-item.archived.unread { background-color: #f0f9ff; }
.notification-item.archived.unread:hover { background-color: #e0f2fe; }

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

.notification-content { flex: 1; min-width: 0; }

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
  flex-shrink: 0;
}

.time-ago {
  font-size: 0.75rem;
  color: #6b7280;
}

.archived-badge {
  color: #f59e0b;
  display: flex;
  align-items: center;
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
  transition: all 0.2s;
}

.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.mark-read-btn  { color: #10b981; border-color: #10b981; }
.archive-btn    { color: #6366f1; border-color: #6366f1; }
.unarchive-btn  { color: #f59e0b; border-color: #f59e0b; }
.delete-btn     { color: #dc2626; border-color: #dc2626; }

.mark-read-btn:hover:not(:disabled)  { color: white; background: #10b981; transform: scale(1.05); }
.archive-btn:hover:not(:disabled)    { color: white; background: #6366f1; transform: scale(1.05); }
.unarchive-btn:hover:not(:disabled)  { color: white; background: #f59e0b; transform: scale(1.05); }
.delete-btn:hover:not(:disabled)     { color: white; background: #dc2626; transform: scale(1.05); }

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

.priority-badge.priority-low      { background-color: #d1fae5; color: #065f46; }
.priority-badge.priority-medium   { background-color: #fef3c7; color: #92400e; }
.priority-badge.priority-high     { background-color: #fee2e2; color: #991b1b; }
.priority-badge.priority-critical { background-color: #fecaca; color: #7f1d1d; }

.notification-source {
  font-size: 0.75rem;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
}

@media (max-width: 768px) {
  .allNotifications-page { padding: 1rem; }

  .page-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .header-actions { justify-content: space-between; }
  .filters-section { grid-template-columns: 1fr; }
  .stats-section { grid-template-columns: repeat(2, 1fr); }

  .notification-actions {
    flex-direction: column;
    gap: 0.25rem;
  }

  .bulk-action-btn {
    font-size: 0.875rem;
    padding: 0.5rem 1rem;
  }
}
</style>
