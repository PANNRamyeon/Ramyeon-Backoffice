<template>
  <div class="forgot-password-page">
    <div class="forgot-password-container surface-card border-theme">
      <div class="forgot-password-header">
        <h1 class="forgot-password-title">Forgot Password?</h1>
        <p class="forgot-password-subtitle">Enter your email address and we'll send you instructions to reset your password.</p>
      </div>

      <!-- Success Message -->
      <div v-if="submitted && !error" class="alert alert-success">
        <div class="d-flex align-items-start">
          <CheckCircle :size="20" class="me-2 flex-shrink-0 mt-1" />
          <div>
            <strong>Email Sent!</strong>
            <p class="mb-0">If an account exists with this email, you will receive password reset instructions shortly. Please check your inbox and spam folder.</p>
          </div>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="alert alert-danger">
        <div class="d-flex align-items-start">
          <AlertCircle :size="20" class="me-2 flex-shrink-0 mt-1" />
          <div>
            <strong>Error</strong>
            <p class="mb-0">{{ error }}</p>
          </div>
        </div>
      </div>

      <!-- Form -->
      <form v-if="!submitted" @submit.prevent="handleSubmit" class="forgot-password-form">
        <div class="mb-4">
          <label for="email" class="form-label">Email Address</label>
          <input
            id="email"
            v-model="email"
            type="email"
            class="form-control input-theme"
            placeholder="Enter your email"
            required
            :disabled="loading"
            autocomplete="email"
          />
        </div>

        <button
          type="submit"
          class="btn btn-submit w-100 mb-3"
          :disabled="loading || !email"
        >
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          {{ loading ? 'Sending...' : 'Send Reset Link' }}
        </button>

        <div class="text-center">
          <router-link to="/login" class="back-link text-decoration-none">
            <ArrowLeft :size="16" class="me-1" />
            Back to Login
          </router-link>
        </div>
      </form>

      <!-- After Submission -->
      <div v-else class="text-center">
        <button @click="resetForm" class="btn btn-outline-secondary mb-3">
          Send Another Email
        </button>
        <div>
          <router-link to="/login" class="back-link text-decoration-none">
            <ArrowLeft :size="16" class="me-1" />
            Back to Login
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ArrowLeft, CheckCircle, AlertCircle } from 'lucide-vue-next'
import axios from 'axios'

const email = ref('')
const loading = ref(false)
const submitted = ref(false)
const error = ref('')

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const handleSubmit = async () => {
  if (!email.value) return

  loading.value = true
  error.value = ''

  try {
    const response = await axios.post(`${API_URL}/auth/forgot-password/`, {
      email: email.value
    })

    if (response.data.success) {
      submitted.value = true
    } else {
      error.value = response.data.error || 'An error occurred. Please try again.'
    }
  } catch (err) {
    console.error('Forgot password error:', err)
    error.value = err.response?.data?.error || 'An error occurred. Please try again.'
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  email.value = ''
  submitted.value = false
  error.value = ''
}
</script>

<style scoped>
.forgot-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: linear-gradient(135deg, var(--gradient-start, #667eea) 0%, var(--gradient-end, #764ba2) 100%);
}

.forgot-password-container {
  max-width: 480px;
  width: 100%;
  padding: 2.5rem;
  border-radius: 1rem;
  background-color: white;
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

.forgot-password-header {
  text-align: center;
  margin-bottom: 2rem;
}

.forgot-password-title {
  font-size: 1.875rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.forgot-password-subtitle {
  font-size: 0.9375rem;
  line-height: 1.5;
  color: var(--text-secondary);
}

.forgot-password-form {
  margin-top: 1.5rem;
}

.form-label {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
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
  .forgot-password-page {
    padding: 1rem;
  }

  .forgot-password-container {
    padding: 1.5rem;
  }

  .forgot-password-header h1 {
    font-size: 1.5rem;
  }
}
</style>

