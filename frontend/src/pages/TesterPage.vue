<template>
  <div class="p-8 max-w-4xl mx-auto page-container">
    <h1 class="text-3xl font-bold mb-8 text-center text-primary">🔍 Auth Debug & Test</h1>
    
    <!-- Login Test Form -->
    <div class="surface-card border-theme rounded-lg p-6 shadow-md mb-6">
      <h2 class="text-xl font-semibold mb-4 text-primary">Login Test</h2>
      
      <form @submit.prevent="testLogin" class="mb-4">
        <div class="row g-3">
          <div class="col-md-4">
            <input 
              type="email" 
              class="form-control" 
              placeholder="Email"
              v-model="testForm.email"
              :disabled="isLoading"
            />
          </div>
          <div class="col-md-4">
            <input 
              type="password" 
              class="form-control" 
              placeholder="Password"
              v-model="testForm.password"
              :disabled="isLoading"
            />
          </div>
          <div class="col-md-4">
            <button 
              type="submit" 
              class="btn btn-submit w-100"
              :disabled="isLoading || !testForm.email || !testForm.password"
            >
              {{ isLoading ? 'Testing Login...' : 'Test Login' }}
            </button>
          </div>
        </div>
      </form>

            <!-- Add this new section after the Login Test Form -->
      <div class="surface-card border-theme rounded-lg p-6 shadow-md mb-6">
        <h2 class="text-xl font-semibold mb-4 text-primary">Initialization Status</h2>
        
        <div class="row g-3">
          <div class="col-md-6">
            <div class="p-3 surface-secondary rounded">
              <div class="text-sm text-tertiary mb-2">Auth Composable Status</div>
              <div class="text-sm">
                <div>Loading: <span :class="isLoading ? 'text-warning' : 'text-success'">
                  {{ isLoading ? 'YES' : 'NO' }}
                </span></div>
                <div>Error: <span :class="error ? 'text-error' : 'text-success'">
                  {{ error || 'None' }}
                </span></div>
                <div>User Initialized: <span :class="user ? 'text-success' : 'text-tertiary'">
                  {{ user ? 'YES' : 'NO' }}
                </span></div>
              </div>
            </div>
          </div>
          
          <div class="col-md-6">
            <div class="p-3 surface-secondary rounded">
              <div class="text-sm text-tertiary mb-2">Quick Actions</div>
              <div class="d-flex gap-2 flex-wrap">
                <button 
                  @click="testTokenValidation"
                  :disabled="!token || isLoading"
                  class="btn btn-sm btn-view"
                >
                  Validate Token
                </button>
                <button 
                  @click="forceInitialize"
                  :disabled="isLoading"
                  class="btn btn-sm btn-refresh"
                >
                  Force Initialize
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Login Result -->
      <div v-if="loginResult" class="p-3 rounded mb-4" 
          :class="loginResult.success ? 'status-success' : 'status-error'">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <strong>Login Result:</strong> 
          <span class="badge" :class="loginResult.success ? 'bg-success' : 'bg-danger'">
            {{ loginResult.success ? 'SUCCESS' : 'FAILED' }}
          </span>
        </div>
        
        <div v-if="loginResult.error" class="mt-2 text-sm">
          <strong>Error:</strong> {{ loginResult.error }}
        </div>
        
        <div v-if="loginResult.success && loginResult.data" class="mt-2 text-sm">
          <div class="row">
            <div class="col-md-6">
              <strong>Tokens:</strong>
              <ul class="list-unstyled mb-0 text-xs">
                <li>Access: {{ loginResult.data.hasToken ? '✅ Received' : '❌ Missing' }}</li>
                <li>Refresh: {{ loginResult.data.hasRefreshToken ? '✅ Received' : '❌ Missing' }}</li>
              </ul>
            </div>
            <div class="col-md-6">
              <strong>User Data:</strong>
              <ul class="list-unstyled mb-0 text-xs">
                <li>ID: {{ loginResult.data.user?.id || 'N/A' }}</li>
                <li>Role: {{ loginResult.data.user?.role || 'N/A' }}</li>
                <li>Email: {{ loginResult.data.user?.email || 'N/A' }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Current Auth Status -->
    <div class="surface-card border-theme rounded-lg p-6 shadow-md mb-6">
      <h2 class="text-xl font-semibold mb-6 text-primary">Authentication Status</h2>
      
      <!-- Status Grid -->
      <div class="row g-4 mb-6">
        <div class="col-md-4 text-center">
          <div class="p-4 surface-secondary rounded">
            <div class="text-sm text-tertiary mb-2">Is Authenticated</div>
            <div :class="isAuthenticated ? 'text-success' : 'text-error'" class="text-2xl font-bold">
              {{ isAuthenticated ? 'YES' : 'NO' }}
            </div>
          </div>
        </div>
        
        <div class="col-md-4 text-center">
          <div class="p-4 surface-secondary rounded">
            <div class="text-sm text-tertiary mb-2">Has User Data</div>
            <div :class="!!user ? 'text-success' : 'text-error'" class="text-2xl font-bold">
              {{ !!user ? 'YES' : 'NO' }}
            </div>
          </div>
        </div>
        
        <div class="col-md-4 text-center">
          <div class="p-4 surface-secondary rounded">
            <div class="text-sm text-tertiary mb-2">Has Token</div>
            <div :class="!!token ? 'text-success' : 'text-error'" class="text-2xl font-bold">
              {{ !!token ? 'YES' : 'NO' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Detailed Debug Info -->
      <div class="row g-4">
        <!-- User Data -->
        <div class="col-md-6">
          <div class="p-4 surface-tertiary rounded">
            <h3 class="font-semibold mb-3 text-primary">User Data</h3>
            <div v-if="user" class="text-sm space-y-2">
              <div><strong>ID:</strong> {{ user.id || 'N/A' }}</div>
              <div><strong>Email:</strong> {{ user.email || 'N/A' }}</div>
              <div><strong>Role:</strong> 
                <span class="badge" :class="getRoleBadgeClass(user.role)">
                  {{ user.role || 'N/A' }}
                </span>
              </div>
              <div><strong>Name:</strong> {{ user.name || 'N/A' }}</div>
              <div><strong>Username:</strong> {{ user.username || 'N/A' }}</div>
              <div><strong>Status:</strong> {{ user.status || 'N/A' }}</div>
            </div>
            <div v-else class="text-tertiary">
              No user data available
            </div>
          </div>
        </div>

        <!-- Token Data -->
        <div class="col-md-6">
          <div class="p-4 surface-tertiary rounded">
            <h3 class="font-semibold mb-3 text-primary">Token Data</h3>
            <div class="text-sm space-y-2">
              <div><strong>Access Token:</strong> 
                <span :class="!!token ? 'text-success' : 'text-error'">
                  {{ token ? 'EXISTS' : 'MISSING' }}
                </span>
              </div>
              <div><strong>Refresh Token:</strong> 
                <span :class="!!refreshToken ? 'text-success' : 'text-error'">
                  {{ refreshToken ? 'EXISTS' : 'MISSING' }}
                </span>
              </div>
              <div v-if="token"><strong>Token Preview:</strong> 
                <code class="text-xs">{{ token.substring(0, 30) }}...</code>
              </div>
              <div><strong>LocalStorage Check:</strong> 
                <span :class="localStorageToken ? 'text-success' : 'text-error'">
                  {{ localStorageToken ? 'EXISTS' : 'MISSING' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Manual Actions -->
    <div class="surface-card border-theme rounded-lg p-6 shadow-md">
      <h2 class="text-xl font-semibold mb-4 text-primary">Debug Actions</h2>
      
      <div class="d-flex gap-3 flex-wrap mb-4">
        <button 
          @click="debugGetCurrentUser"
          :disabled="!token || isLoading"
          class="btn btn-view"
        >
          {{ isLoading ? 'Loading...' : 'Get Current User' }}
        </button>
        <button 
          @click="checkTokenInStorage"
          class="btn btn-export"
        >
          Check Token Storage
        </button>
        <button 
          @click="clearAllData"
          class="btn btn-delete"
        >
          Clear All Data
        </button>
        <button 
          @click="refreshAuthState"
          class="btn btn-refresh"
        >
          Refresh State
        </button>
      </div>

      <!-- Debug Console -->
      <div v-if="debugMessages.length > 0" class="p-4 surface-tertiary rounded">
        <h3 class="font-semibold mb-3 text-primary">Debug Console</h3>
        <div class="debug-console" style="max-height: 200px; overflow-y: auto;">
          <div v-for="(msg, index) in debugMessages" :key="index" 
               class="text-xs font-mono mb-1" :class="getDebugMessageClass(msg.type)">
            <span class="text-tertiary-medium">[{{ msg.time }}]</span> {{ msg.message }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuth } from '@/composables/auth/useAuth.js'
import apiService from '@/services/api.js'

// Auth composable
const { 
  user, 
  token, 
  refreshToken,
  isAuthenticated, 
  isLoading,
  error,
  login,
  getCurrentUser,
  clearAuth,
  validateToken
} = useAuth()

// Local state
const testForm = ref({
  email: '',
  password: ''
})

const loginResult = ref(null)
const debugMessages = ref([])
const localStorageToken = ref(null)

// Debug methods
const addDebugMessage = (message, type = 'info') => {
  debugMessages.value.unshift({
    message,
    type,
    time: new Date().toLocaleTimeString()
  })
  
  // Keep only last 50 messages
  if (debugMessages.value.length > 50) {
    debugMessages.value = debugMessages.value.slice(0, 50)
  }
}

const testLogin = async () => {
  addDebugMessage('🔐 Starting login test...', 'info')
  loginResult.value = null
  
  try {
    addDebugMessage(`📧 Email: ${testForm.value.email}`, 'info')
    addDebugMessage(`🔑 Password length: ${testForm.value.password.length}`, 'info')
    
    // Call the login method from useAuth
    const success = await login(testForm.value.email, testForm.value.password)
    
    if (success) {
      addDebugMessage('✅ Login successful!', 'success')
      addDebugMessage(`👤 User data: ${user.value ? 'RECEIVED' : 'MISSING'}`, user.value ? 'success' : 'error')
      addDebugMessage(`🎫 Token: ${token.value ? 'RECEIVED' : 'MISSING'}`, token.value ? 'success' : 'error')
      
      loginResult.value = {
        success: true,
        data: {
          user: user.value,
          hasToken: !!token.value,
          hasRefreshToken: !!refreshToken.value
        }
      }
    } else {
      addDebugMessage('❌ Login failed', 'error')
      addDebugMessage(`Error: ${error.value}`, 'error')
      
      loginResult.value = {
        success: false,
        error: error.value
      }
    }
    
    // Update localStorage check
    localStorageToken.value = localStorage.getItem('access_token')
    addDebugMessage(`🗃️ Token in localStorage: ${localStorageToken.value ? 'YES' : 'NO'}`, localStorageToken.value ? 'success' : 'error')
    
  } catch (err) {
    addDebugMessage(`💥 Login exception: ${err.message}`, 'error')
    loginResult.value = {
      success: false,
      error: err.message
    }
  }
}

const debugGetCurrentUser = async () => {
  addDebugMessage('👤 Testing getCurrentUser...', 'info')
  
  try {
    const userData = await getCurrentUser()
    addDebugMessage('✅ getCurrentUser successful', 'success')
    addDebugMessage(`User: ${JSON.stringify(userData)}`, 'info')
  } catch (err) {
    addDebugMessage(`❌ getCurrentUser failed: ${err.message}`, 'error')
  }
}

const checkTokenInStorage = () => {
  const accessToken = localStorage.getItem('access_token')
  const refresh = localStorage.getItem('refresh_token')
  
  addDebugMessage(`🗃️ Access token in localStorage: ${accessToken ? 'EXISTS' : 'MISSING'}`, accessToken ? 'success' : 'error')
  addDebugMessage(`🗃️ Refresh token in localStorage: ${refresh ? 'EXISTS' : 'MISSING'}`, refresh ? 'success' : 'error')
  
  if (accessToken) {
    addDebugMessage(`🎫 Token preview: ${accessToken.substring(0, 30)}...`, 'info')
  }
  
  localStorageToken.value = accessToken
}

const clearAllData = () => {
  clearAuth()
  localStorage.clear()
  loginResult.value = null
  localStorageToken.value = null
  addDebugMessage('🧹 All auth data cleared', 'info')
}

const refreshAuthState = () => {
  localStorageToken.value = localStorage.getItem('access_token')
  addDebugMessage('🔄 Auth state refreshed', 'info')
}

// Helper methods
const getRoleBadgeClass = (role) => {
  return role === 'admin' ? 'bg-success' : 'bg-secondary'
}

const getDebugMessageClass = (type) => {
  switch (type) {
    case 'success': return 'text-success'
    case 'error': return 'text-error'
    case 'warning': return 'text-warning'
    default: return 'text-tertiary'
  }
}

const testTokenValidation = async () => {
  addDebugMessage('🎫 Testing token validation...', 'info')
  
  try {
    const isValid = await validateToken()
    addDebugMessage(`Token validation result: ${isValid ? 'VALID' : 'INVALID'}`, isValid ? 'success' : 'error')
  } catch (err) {
    addDebugMessage(`Token validation error: ${err.message}`, 'error')
  }
}

const forceInitialize = () => {
  addDebugMessage('🔄 Force reinitializing auth...', 'info')
  // The auth composable will auto-initialize, we just need to refresh our local state
  refreshAuthState()
}

onMounted(() => {
  checkTokenInStorage()
  addDebugMessage('🚀 Auth debug page loaded', 'info')
})
</script>

<style scoped>
/* Existing styles plus additions... */
.debug-console {
  background-color: #1a1a1a;
  border-radius: 4px;
  padding: 1rem;
}

.space-y-2 > * + * {
  margin-top: 0.5rem;
}
</style>