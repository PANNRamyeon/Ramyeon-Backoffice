// composables/auth/useAuth.js
import { ref, computed, watch, readonly, nextTick } from 'vue'
import apiService from '@/services/api.js'

export function useAuth() {
  // Reactive state
  const user = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  const tokenRef = ref(localStorage.getItem('access_token'))
 
  // Computed properties
  const token = computed(() => tokenRef.value)
  const refreshToken = computed(() => localStorage.getItem('refresh_token'))
  const isAdmin = computed(() => user.value?.role === 'admin')

  const isAuthenticated = computed(() => {
    const token = localStorage.getItem('access_token')
    return !!token
  })

  // Sync token function
  const syncToken = () => {
    tokenRef.value = localStorage.getItem('access_token')
  }
 
  // Clear authentication state
  const clearAuth = () => {
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    tokenRef.value = null
    error.value = null
  }

  // ✅ NEW: Fetch current user from /auth/me/
  const fetchCurrentUser = async () => {
    if (!token.value) {
      return false
    }

    try {
      const userData = await apiService.getCurrentUser()
      user.value = userData
      return true
    } catch (err) {
      console.error('❌ useAuth: Failed to fetch user:', err.message)
      error.value = err.message
      clearAuth()
      return false
    }
  }

  // Initialize user from token on composable creation
  const initializeAuth = async () => {
    if (token.value && !user.value) {
      await fetchCurrentUser() // ✅ Fetch user data
    }
  }
 
  // Login method
  const login = async (email, password) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await apiService.login(email, password)

      // Sync token
      syncToken()
      await nextTick()

      // ✅ Fetch full user data after login
      await fetchCurrentUser()

      return true
    } catch (err) {
      console.error('❌ useAuth: Login failed:', err.message)
      error.value = err.message || 'Login failed'
      clearAuth()
      return false
    } finally {
      isLoading.value = false
    }
  }
 
  // Logout method
  const logout = async () => {
    isLoading.value = true
    error.value = null

    try {
      await apiService.logout()
    } catch (err) {
      // Log error but still clear local state
      console.error('⚠️ useAuth: Logout API error (continuing anyway):', err.message)
      error.value = err.message
    } finally {
      clearAuth()
      isLoading.value = false
    }
  }
 
  // Refresh token method
  const refresh = async () => {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }

    try {
      await apiService.refreshToken()
      syncToken() // Sync after refresh
      return true
    } catch (err) {
      console.error('❌ useAuth: Token refresh failed:', err.message)
      error.value = err.message || 'Token refresh failed'
      clearAuth()
      throw err
    }
  }
 
  // Validate current token
  const validateToken = async () => {
    if (!token.value) {
      return false
    }

    try {
      await apiService.validateToken()
      return true
    } catch (err) {
      console.error('❌ useAuth: Token validation failed:', err.message)
      clearAuth()
      return false
    }
  }
 
  // Watch for token changes and initialize user
  watch(token, async (newToken, oldToken) => {
    if (newToken && !user.value) {
      await nextTick()
      await initializeAuth()
    } else if (!newToken && user.value) {
      user.value = null
    }
  }, { immediate: true })
 
  // Initialize on composable creation
  nextTick(() => {
    initializeAuth()
  })
 
  return {
    // State (readonly to prevent direct mutation)
    user: readonly(user),
    isLoading: readonly(isLoading),
    error: readonly(error),
   
    // Computed
    token,
    refreshToken,
    isAuthenticated,
    isAdmin,
   
    // Methods
    login,
    logout,
    refresh,
    validateToken,
    clearAuth,
    fetchCurrentUser // ✅ Export this in case you need it elsewhere
  }
}