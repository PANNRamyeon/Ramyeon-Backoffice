import { ref } from 'vue'
import apiNotifications from '@/services/apiNotifications'

export function useNotifications() {
  const notifications = ref([])
  const unreadCount = ref(0)
  const isLoading = ref(false)
  const error = ref(null)

  async function fetchRecent(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const res = await apiNotifications.getRecent(params)
      notifications.value = res.data ?? res
      return res
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchList(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const res = await apiNotifications.getList(params)
      notifications.value = res.data ?? res
      return res
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAll(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const res = await apiNotifications.DisplayNotifs(params)
      notifications.value = res.data ?? res
      return res
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchById(id, includeArchived = false) {
    try {
      return await apiNotifications.getById(id, includeArchived)
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function fetchUnreadCount() {
    try {
      const res = await apiNotifications.getUnreadCount()
      unreadCount.value = res.unread_count ?? res.count ?? 0
      return res
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function markAsRead(id) {
    try {
      const res = await apiNotifications.MarkAsRead(id)
      const target = notifications.value.find((n) => n.notification_id === id || n.sk === id)
      if (target) target.is_read = true
      return res
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function markAsUnread(id) {
    try {
      const res = await apiNotifications.MarkAsUnread(id)
      const target = notifications.value.find((n) => n.notification_id === id || n.sk === id)
      if (target) target.is_read = false
      return res
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function markAllAsRead() {
    try {
      const res = await apiNotifications.MarkAllAsRead()
      notifications.value.forEach((n) => { n.is_read = true })
      unreadCount.value = 0
      return res
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function archive(id) {
    try {
      const res = await apiNotifications.Archive(id)
      notifications.value = notifications.value.filter(
        (n) => n.notification_id !== id && n.sk !== id
      )
      return res
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function unarchive(id) {
    try {
      return await apiNotifications.Unarchive(id)
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function deleteNotification(id) {
    try {
      const res = await apiNotifications.Delete(id)
      notifications.value = notifications.value.filter(
        (n) => n.notification_id !== id && n.sk !== id
      )
      return res
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function createNotification(data) {
    try {
      return await apiNotifications.createNotification(data)
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function createInventoryAlert(data) {
    try {
      return await apiNotifications.createInventoryAlert(data)
    } catch (err) {
      error.value = err
      throw err
    }
  }

  return {
    notifications,
    unreadCount,
    isLoading,
    error,
    fetchRecent,
    fetchList,
    fetchAll,
    fetchById,
    fetchUnreadCount,
    markAsRead,
    markAsUnread,
    markAllAsRead,
    archive,
    unarchive,
    deleteNotification,
    createNotification,
    createInventoryAlert,
  }
}
