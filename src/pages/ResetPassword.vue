<template>
  <div class="reset-password-page">
    <div class="reset-password-container surface-card border-theme">
      <div class="reset-password-header">
        <h1 class="reset-password-title">Reset Password</h1>
        <p class="reset-password-subtitle">Enter your new password below.</p>
      </div>

      <!-- Loading State -->
      <div v-if="verifying" class="text-center py-4">
        <div class="spinner-border text-accent" role="status">
          <span class="visually-hidden">Verifying token...</span>
        </div>
        <p class="mt-3 text-tertiary">Verifying reset link...</p>
      </div>

      <!-- Invalid Token -->
      <div v-else-if="!tokenValid && !verifying" class="alert alert-danger">
        <div class="d-flex align-items-start">
          <AlertCircle :size="20" class="me-2 flex-shrink-0 mt-1" />
          <div>
            <strong>Invalid or Expired Link</strong>
            <p class="mb-0">{{ tokenError || 'This password reset link is invalid or has expired. Please request a new one.' }}</p>
          </div>
        </div>
        <div class="mt-3 text-center">
          <router-link to="/forgot-password" class="btn btn-outline-secondary">
            Request New Link
          </router-link>
        </div>
      </div>

      <!-- Success Message -->
      <div v-else-if="resetSuccess" class="alert alert-success">
        <div class="d-flex align-items-start">
          <CheckCircle :size="20" class="me-2 flex-shrink-0 mt-1" />
          <div>
            <strong>Password Reset Successfully!</strong>
            <p class="mb-0">Your password has been reset. You can now log in with your new password.</p>
          </div>
        </div>
        <div class="mt-3 text-center">
          <router-link to="/login" class="btn btn-submit">
            Go to Login
          </router-link>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="error && !resetSuccess" class="alert alert-danger">
        <div class="d-flex align-items-start">
          <AlertCircle :size="20" class="me-2 flex-shrink-0 mt-1" />
          <div>
            <strong>Error</strong>
            <p class="mb-0">{{ error }}</p>
          </div>
        </div>
      </div>

      <!-- Reset Form -->
      <form v-if="tokenValid && !resetSuccess && !verifying" @submit.prevent="handleSubmit" class="reset-password-form">
        <div class="mb-3">
          <label for="email" class="form-label">Email</label>
          <input
            id="email"
            v-model="userEmail"
            type="email"
            class="form-control input-theme"
            disabled
            readonly
          />
        </div>

        <div class="mb-3">
          <label for="password" class="form-label">New Password</label>
          <div class="position-relative">
            <input
              id="password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              class="form-control input-theme"
              placeholder="Enter new password"
              required
              minlength="8"
              :disabled="loading"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="btn btn-link position-absolute end-0 top-50 translate-middle-y"
              @click="showPassword = !showPassword"
              tabindex="-1"
            >
              <Eye v-if="!showPassword" :size="18" />
              <EyeOff v-else :size="18" />
            </button>
          </div>
          <small class="form-text text-muted">Must be at least 8 characters long</small>
        </div>

        <div class="mb-4">
          <label for="confirmPassword" class="form-label">Confirm Password</label>
          <div class="position-relative">
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              class="form-control input-theme"
              placeholder="Confirm new password"
              required
              :disabled="loading"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="btn btn-link position-absolute end-0 top-50 translate-middle-y"
              @click="showConfirmPassword = !showConfirmPassword"
              tabindex="-1"
            >
              <Eye v-if="!showConfirmPassword" :size="18" />
              <EyeOff v-else :size="18" />
            </button>
          </div>
          <small v-if="confirmPassword && password !== confirmPassword" class="form-text text-danger">
            Passwords do not match
          </small>
        </div>

        <button
          type="submit"
          class="btn btn-submit w-100 mb-3"
          :disabled="loading || !password || !confirmPassword || password !== confirmPassword"
        >
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          {{ loading ? 'Resetting...' : 'Reset Password' }}
        </button>

        <div class="text-center">
          <router-link to="/login" class="back-link text-decoration-none">
            <ArrowLeft :size="16" class="me-1" />
            Back to Login
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-vue-next'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

const token = ref('')
const userEmail = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const verifying = ref(true)
const tokenValid = ref(false)
const tokenError = ref('')
const resetSuccess = ref(false)
const error = ref('')

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

onMounted(async () => {
  // Get token from URL query parameter
  token.value = route.query.token

  if (!token.value) {
    tokenValid.value = false
    tokenError.value = 'No reset token provided.'
    verifying.value = false
    return
  }

  // Verify the token
  try {
    const response = await axios.post(`${API_URL}/auth/verify-reset-token/`, {
      token: token.value
    })

    if (response.data.valid) {
      tokenValid.value = true
      userEmail.value = response.data.email || ''
    } else {
      tokenValid.value = false
      tokenError.value = response.data.error || 'Invalid reset token.'
    }
  } catch (err) {
    console.error('Token verification error:', err)
    tokenValid.value = false
    tokenError.value = err.response?.data?.error || 'Failed to verify reset token.'
  } finally {
    verifying.value = false
  }
})

const handleSubmit = async () => {
  if (!password.value || !confirmPassword.value) return
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match.'
    return
  }
  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters long.'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await axios.post(`${API_URL}/auth/reset-password/`, {
      token: token.value,
      new_password: password.value
    })

    if (response.data.success) {
      resetSuccess.value = true
      // Redirect to login after 3 seconds
      setTimeout(() => {
        router.push('/login')
      }, 3000)
    } else {
      error.value = response.data.error || 'An error occurred. Please try again.'
    }
  } catch (err) {
    console.error('Password reset error:', err)
    error.value = err.response?.data?.error || 'An error occurred. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.reset-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: linear-gradient(135deg, var(--gradient-start, #667eea) 0%, var(--gradient-end, #764ba2) 100%);
}

.reset-password-container {
  max-width: 480px;
  width: 100%;
  padding: 2.5rem;
  border-radius: 1rem;
  box-shadow: var(--shadow-2xl);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.reset-password-header {
  text-align: center;
  margin-bottom: 2rem;
}

.reset-password-title {
  font-size: 1.875rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.reset-password-subtitle {
  font-size: 0.9375rem;
  line-height: 1.5;
  color: var(--text-secondary);
}

.reset-password-form {
  margin-top: 1.5rem;
}

.form-label {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.text-muted {
  color: var(--text-tertiary);
}

.back-link {
  color: var(--text-primary);
  font-weight: 500;
  transition: color 0.2s ease;
}

.back-link:hover {
  color: var(--accent);
}

.form-control {
  padding: 0.75rem 1rem;
  font-size: 1rem;
  border-radius: 0.5rem;
}

.position-relative .btn-link {
  border: none;
  background: none;
  padding: 0.5rem;
  color: var(--text-secondary);
}

.position-relative .btn-link:hover {
  color: var(--text-primary);
}

.alert {
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
}

.spinner-border-sm {
  width: 1rem;
  height: 1rem;
  border-width: 0.15em;
}

@media (max-width: 576px) {
  .reset-password-page {
    padding: 1rem;
  }

  .reset-password-container {
    padding: 1.5rem;
  }

  .reset-password-header h1 {
    font-size: 1.5rem;
  }
}
</style>

