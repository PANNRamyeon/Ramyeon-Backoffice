<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-card">
        <!-- Left Side - Logo Section -->
        <div class="logo-section">
          <div class="logo-placeholder">
              <img src="../assets/Logo_1.png" alt="PANN Logo" class="logo-image" />
          </div>
          <h2 class="brand-title">Back Office</h2>
          <p class="brand-subtitle">Inventory and User Management</p>
        </div>

        <!-- Right Side - Login Form -->
        <div class="form-section">
          <div class="form-container">
            <h1 class="sign-in-title">Sign In</h1>
            
            <form @submit.prevent="handleLogin" class="login-form">
              <!-- Email Field -->
              <div class="form-group">
                <label for="email" class="form-label">Email:</label>
                <input
                  id="email"
                  v-model="loginForm.email"
                  type="email"
                  class="form-input"
                  placeholder="Enter your email"
                  required
                  :disabled="isLoading"
                />
              </div>

              <!-- Password Field -->
              <div class="form-group">
                <label for="password" class="form-label">Password:</label>
                <div class="password-input-wrapper">
                  <input
                    id="password"
                    v-model="loginForm.password"
                    :type="showPassword ? 'text' : 'password'"
                    class="form-input password-input"
                    placeholder="Enter your password"
                    required
                    :disabled="isLoading"
                  />
                  <button
                    type="button"
                    class="password-toggle-btn"
                    @click="togglePasswordVisibility"
                    :disabled="isLoading"
                    tabindex="-1"
                  >
                    <Eye v-if="showPassword" :size="20" />
                    <EyeOff v-else :size="20" />
                  </button>
                </div>
              </div>

              <!-- Success Message -->
              <div v-if="successMessage" class="success-message">
                {{ successMessage }}
              </div>

              <!-- Failure Message -->
              <div v-if="error" class="failure-message">
                {{ error }}
              </div>

              <!-- Login Button -->
              <button
                type="submit"
                class="login-button"
                :disabled="isLoading || !loginForm.email || !loginForm.password"
              >
                {{ isLoading ? 'Signing In...' : 'Login' }}
              </button>
            </form>

            <!-- Additional Options -->
            <div class="form-footer">
              <a href="#" class="forgot-password" @click.prevent="handleForgotPassword">
                Forgot Password?
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/auth/useAuth.js'
import { Eye, EyeOff } from 'lucide-vue-next'

const router = useRouter()

// Use the auth composable
const { 
  login, 
  user,
  token,
  isAuthenticated,
  isLoading, 
  error: authError 
} = useAuth()

// Form data
const loginForm = ref({
  email: '',
  password: ''
})

const showPassword = ref(false)
const successMessage = ref(null)
const localError = ref(null)

// Toggle password visibility
const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}

// Computed - combine local error with auth error
const error = computed(() => localError.value || authError.value)

// Computed
const apiBaseUrl = computed(() => import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1')
const isDev = computed(() => import.meta.env.DEV)

// Clear error when user starts typing
watch(() => loginForm.value.email, () => {
  if (localError.value) {
    localError.value = null
  }
})

watch(() => loginForm.value.password, () => {
  if (localError.value) {
    localError.value = null
  }
})

// Watch for auth errors and sync to local error for better control
watch(authError, (newError) => {
  if (newError) {
    // Format error message to be more user-friendly
    if (newError.includes('Invalid email') || newError.includes('Invalid password') || newError.includes('email or password')) {
      localError.value = 'Invalid email or password. Please check your credentials and try again.'
    } else if (newError.includes('Network') || newError.includes('timeout')) {
      localError.value = 'Network error. Please check your connection and try again.'
    } else {
      localError.value = newError
    }
  }
})

// Enhanced login handler with debugging
const handleLogin = async () => {
  // Clear previous messages
  successMessage.value = null
  localError.value = null
  
  try {
    // Client-side validation
    if (!loginForm.value.email || !loginForm.value.password) {
      localError.value = 'Please fill in all fields'
      return
    }

    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(loginForm.value.email)) {
      localError.value = 'Please enter a valid email address'
      return
    }

    const success = await login(loginForm.value.email, loginForm.value.password)

    if (success) {
      await handleLoginSuccess()
    } else {
      // If login returns false, check if there's an auth error
      // If not, set a generic error message
      if (!authError.value) {
        localError.value = 'Invalid email or password. Please try again.'
      }
    }
  } catch (err) {
    console.error('LOGIN PAGE: Login exception:', err)
    // Set error message from exception or use a default
    localError.value = err.message || 'Invalid email or password. Please try again.'
  }
}

const handleLoginSuccess = async () => {
  // Clear any previous errors
  localError.value = null
  
  // Wait a bit more for reactivity to settle
  await new Promise(resolve => setTimeout(resolve, 100))

  successMessage.value = 'Login successful! Redirecting...'

  // Proceed with redirect even if isAuthenticated is still false
  // The router guard will handle the final token check
  setTimeout(() => {
    router.push('/dashboard')
      .catch((error) => {
        console.error('LOGIN PAGE: Navigation error:', error)
        router.push('/home')
      })
  }, 1000)
}

const handleForgotPassword = () => {
  router.push('/forgot-password')
}

// Enhanced onMounted with debugging
onMounted(() => {
  // Check if already authenticated
  if (isAuthenticated.value) {
    router.push('/dashboard')
  }
})
</script>

<style scoped>
/* All your existing styles remain exactly the same */
.login-page {
  min-height: 100vh;
  background-color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  padding: 2rem;
  width: 100vw;
}

.login-container {
  width: 100vw;
  max-width: 900px;
}

.login-card {
  background: white;
  border-radius: 1.5rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 500px;
  animation: fadeIn 0.6s ease-out;
}

/* Left Side - Logo Section */
.logo-section {
  background: white;
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: white;
}

.logo-placeholder {
  margin-bottom: 2rem;
}

.logo-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  border: 3px solid rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
  margin: 0 auto;
}

.logo-text {
  font-size: 2rem;
  font-weight: 700;
  color: white;
  letter-spacing: 3px;
}

.brand-title {
  font-size: 1.75rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
 color: rgb(68, 68, 68);
}

.brand-subtitle {
  font-size: 1rem;
  opacity: 0.9;
  margin: 0;
  color: grey;
}

/* Right Side - Form Section */
.form-section {
  padding: 3rem 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-container {
  width: 100%;
  max-width: 350px;
}

.sign-in-title {
  font-size: 2.25rem;
  font-weight: 700;
  color: #1f2937;
  text-align: center;
  margin: 0 0 2rem 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.form-input {
  padding: 0.875rem 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 1rem;
  transition: all 0.2s ease;
  background: white;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input:disabled {
  background-color: #f9fafb;
  cursor: not-allowed;
  opacity: 0.6;
}

.form-input::placeholder {
  color: #9ca3af;
}

/* Password Input Wrapper */
.password-input-wrapper {
  position: relative;
  width: 100%;
}

.password-input {
  width: 100%;
  padding-right: 3rem;
}

.password-toggle-btn {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: color 0.2s ease;
  z-index: 1;
}

.password-toggle-btn:hover:not(:disabled) {
  color: #667eea;
}

.password-toggle-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.password-toggle-btn:focus {
  outline: none;
  color: #667eea;
}

.error-message {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  text-align: center;
}

.success-message {
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #16a34a;
  padding: 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  text-align: center;
}

.failure-message {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  text-align: center;
}

.login-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 1rem;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-top: 0.5rem;
}

.login-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.login-button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.form-footer {
  text-align: center;
  margin-top: 1.5rem;
}

.forgot-password {
  color: #667eea;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: color 0.2s ease;
}

.forgot-password:hover {
  color: #764ba2;
  text-decoration: underline;
}

/* Animation */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .login-page {
    padding: 1rem;
  }
  
  .login-card {
    grid-template-columns: 1fr;
    max-width: 480px;
  }
  
  .logo-section {
    padding: 2rem 1.5rem;
  }
  
  .logo-circle {
    width: 100px;
    height: 100px;
  }
  
  .logo-text {
    font-size: 1.5rem;
  }
  
  .brand-title {
    font-size: 1.5rem;
  }
  
  .form-section {
    padding: 2rem 1.5rem;
  }
  
  .sign-in-title {
    font-size: 1.75rem;
  }
}

@media (max-width: 480px) {
  .login-page {
    padding: 0.5rem;
  }
  
  .form-section {
    padding: 1.5rem 1rem;
  }
  
  .logo-section {
    padding: 1.5rem 1rem;
  }
  
  .form-container {
    max-width: none;
  }
}
</style>