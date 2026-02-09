// composables/api/useUsers.js
import { ref, computed } from 'vue'
import userApiService from '@/services/apiUsers'

export function useUsers() {
  // State
  const users = ref([])
  const selectedUser = ref(null)
  const deletedUsers = ref([])
  const loading = ref(false)
  const error = ref(null)
  const pagination = ref({
    page: 1,
    limit: 50,
    total: 0,
    hasMore: false
  })

  // Computed
  const activeUsers = computed(() => 
    users.value.filter(user => user.status === 'active' && !user.isDeleted)
  )

  const disabledUsers = computed(() => 
    users.value.filter(user => user.status === 'disabled' && !user.isDeleted)
  )

  const totalUsers = computed(() => pagination.value.total)

  const hasUsers = computed(() => users.value.length > 0)

  // Methods

  /**
   * Fetch all users with optional filters
   * @param {Object} params - Query parameters
   */
  const fetchUsers = async (params = {}) => {
    loading.value = true
    error.value = null

    try {
      const response = await userApiService.getAll({
        page: params.page || pagination.value.page,
        limit: params.limit || pagination.value.limit,
        status: params.status,
        role: params.role,        // ✅ added role filter
        search: params.search,    // ✅ added search filter
        include_deleted: params.include_deleted || false
      })

      users.value = response.users || []

      pagination.value = {
        page: response.page || 1,
        limit: response.limit || 50,
        total: response.total || 0,
        hasMore: response.has_more || false
      }

      return response
    } catch (err) {
      error.value = err.message
      console.error('❌ useUsers: Error fetching users:', err)
      throw err
    } finally {
      loading.value = false
    }
  }


  /**
   * Fetch user by ID
   * @param {string} userId - User ID (USER-####)
   * @param {boolean} includeDeleted - Include if soft-deleted
   */
  const fetchUserById = async (userId, includeDeleted = false) => {
    loading.value = true
    error.value = null

    try {
      const user = await userApiService.getById(userId, includeDeleted)
      selectedUser.value = user
      return user
    } catch (err) {
      error.value = err.message
      console.error(`❌ useUsers: Error fetching user ${userId}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch user by email
   * @param {string} email - User email
   */
  const fetchUserByEmail = async (email, includeDeleted = false) => {
    loading.value = true
    error.value = null

    try {
      const user = await userApiService.getByEmail(email, includeDeleted)
      selectedUser.value = user
      return user
    } catch (err) {
      error.value = err.message
      console.error('❌ useUsers: Error fetching user by email:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch user by username
   * @param {string} username - Username
   */
  const fetchUserByUsername = async (username, includeDeleted = false) => {
    loading.value = true
    error.value = null

    try {
      const user = await userApiService.getByUsername(username, includeDeleted)
      selectedUser.value = user
      return user
    } catch (err) {
      error.value = err.message
      console.error('❌ useUsers: Error fetching user by username:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch all deleted users
   * @param {Object} params - Query parameters
   */
  const fetchDeletedUsers = async (params = {}) => {
    loading.value = true
    error.value = null

    try {
      const response = await userApiService.getDeleted(params)
      deletedUsers.value = response.users || []
      return response
    } catch (err) {
      error.value = err.message
      console.error('❌ useUsers: Error fetching deleted users:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Create new user
   * @param {Object} userData - User data
   */
  const createUser = async (userData) => {
    loading.value = true
    error.value = null

    try {
      const newUser = await userApiService.create(userData)

      // Add to local state
      users.value.unshift(newUser)
      pagination.value.total += 1

      return newUser
    } catch (err) {
      error.value = err.message
      console.error('❌ useUsers: Error creating user:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update user
   * @param {string} userId - User ID (USER-####)
   * @param {Object} userData - Updated user data
   */
  const updateUser = async (userId, userData) => {
    loading.value = true
    error.value = null

    try {
      const updatedUser = await userApiService.update(userId, userData)

      // Update in local state
      const index = users.value.findIndex(u => u._id === userId)
      if (index !== -1) {
        users.value[index] = updatedUser
      }

      // Update selected user if it's the same one
      if (selectedUser.value?._id === userId) {
        selectedUser.value = updatedUser
      }

      return updatedUser
    } catch (err) {
      error.value = err.message
      console.error(`❌ useUsers: Error updating user ${userId}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Soft delete user (can be restored)
   * @param {string} userId - User ID (USER-####)
   */
  const deleteUser = async (userId) => {
    loading.value = true
    error.value = null

    try {
      const response = await userApiService.softDelete(userId)

      // Remove from local state
      users.value = users.value.filter(u => u._id !== userId)
      pagination.value.total -= 1

      return response
    } catch (err) {
      error.value = err.message
      console.error(`❌ useUsers: Error deleting user ${userId}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Restore soft-deleted user
   * @param {string} userId - User ID (USER-####)
   */
  const restoreUser = async (userId) => {
    loading.value = true
    error.value = null

    try {
      const response = await userApiService.restore(userId)

      // Remove from deleted users list
      deletedUsers.value = deletedUsers.value.filter(u => u._id !== userId)

      // Optionally refetch all users to show restored user
      // await fetchUsers()

      return response
    } catch (err) {
      error.value = err.message
      console.error(`❌ useUsers: Error restoring user ${userId}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Permanently delete user (IRREVERSIBLE)
   * @param {string} userId - User ID (USER-####)
   */
  const hardDeleteUser = async (userId) => {
    loading.value = true
    error.value = null

    try {
      const response = await userApiService.hardDelete(userId)

      // Remove from both local states
      users.value = users.value.filter(u => u._id !== userId)
      deletedUsers.value = deletedUsers.value.filter(u => u._id !== userId)
      pagination.value.total -= 1

      return response
    } catch (err) {
      error.value = err.message
      console.error(`❌ useUsers: Error hard deleting user ${userId}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear error state
   */
  const clearError = () => {
    error.value = null
  }

  /**
   * Reset all state
   */
  const resetState = () => {
    users.value = []
    selectedUser.value = null
    deletedUsers.value = []
    loading.value = false
    error.value = null
    pagination.value = {
      page: 1,
      limit: 50,
      total: 0,
      hasMore: false
    }
  }

  // Return public API
  return {
    // State
    users,
    selectedUser,
    deletedUsers,
    loading,
    error,
    pagination,

    // Computed
    activeUsers,
    disabledUsers,
    totalUsers,
    hasUsers,

    // Methods
    fetchUsers,
    fetchUserById,
    fetchUserByEmail,
    fetchUserByUsername,
    fetchDeletedUsers,
    createUser,
    updateUser,
    deleteUser,
    restoreUser,
    hardDeleteUser,
    clearError,
    resetState
  }
}