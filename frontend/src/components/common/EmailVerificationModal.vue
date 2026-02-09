<template>
  <!-- Modal Backdrop -->
  <div 
    v-if="isVisible" 
    class="modal-backdrop"
    @click="handleBackdropClick"
  >
    <!-- Modal Container -->
    <div 
      class="modal-container modal-sm"
      @click.stop
    >
      <!-- Modal Header -->
      <div class="modal-header">
        <h4 class="modal-title">
          <Mail :size="20" class="me-2" />
          Email Verification
        </h4>
        <button 
          type="button" 
          class="btn-close-modal"
          @click="handleClose"
          :disabled="isLoading"
        >
          <X :size="20" />
        </button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        <div v-if="!verificationToken" class="verification-step">
          <p class="verification-message">
            We'll send a 6-digit verification code to your email address:
          </p>
          <p class="email-address">{{ email }}</p>
          <button 
            class="btn btn-primary w-100" 
            @click="handleSendCode"
            :disabled="isLoading"
          >
            <Mail :size="16" v-if="!isLoading" class="me-2" />
            <span v-if="isLoading">Sending...</span>
            <span v-else>Send Verification Code</span>
          </button>
        </div>

        <div v-else class="verification-step">
          <p class="verification-message">
            Enter the 6-digit code sent to <strong>{{ email }}</strong>
          </p>
          
          <div class="code-input-group">
            <input
              type="text"
              class="form-control code-input"
              v-model="code"
              placeholder="000000"
              maxlength="6"
              @input="handleCodeInput"
              :disabled="isLoading"
              ref="codeInputRef"
            />
          </div>

          <div v-if="error" class="alert alert-danger mt-3">
            <AlertCircle :size="16" class="me-2" />
            <span>{{ error }}</span>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer" v-if="verificationToken">
        <div class="d-flex justify-content-end gap-2 w-100">
          <button
            type="button"
            class="btn btn-secondary"
            @click="handleResendCode"
            :disabled="isLoading"
          >
            <Mail :size="14" v-if="!isLoading" class="me-2" />
            <span v-if="isLoading">Resending...</span>
            <span v-else>Resend Code</span>
          </button>
          <button
            type="button"
            class="btn btn-primary"
            @click="handleVerifyCode"
            :disabled="!canVerify || isLoading"
          >
            <CheckCircle :size="14" v-if="!isLoading" class="me-2" />
            <span v-if="isLoading">Verifying...</span>
            <span v-else>Verify Email</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useModal } from '@/composables/ui/useModal.js'
import { Mail, X, CheckCircle, AlertCircle } from 'lucide-vue-next'

// Props
const props = defineProps({
  email: {
    type: String,
    required: true
  }
})

// Emits
const emit = defineEmits(['verify', 'close'])

// Composables
const { isVisible, isLoading, error, show, hide, setLoading, setError, clearError } = useModal()

// State
const verificationToken = ref(null)
const code = ref('')
const codeInputRef = ref(null)

// Computed
const canVerify = computed(() => {
  return code.value.length === 6 && /^\d{6}$/.test(code.value)
})

// Methods
const handleCodeInput = (event) => {
  // Only allow numbers
  code.value = event.target.value.replace(/\D/g, '')
  clearError()
}

const handleSendCode = async () => {
  setLoading(true)
  clearError()
  emit('send-code', handleCodeSent)
}

const handleCodeSent = (token) => {
  setLoading(false)
  if (token) {
    verificationToken.value = token
    nextTick(() => {
      codeInputRef.value?.focus()
    })
  } else {
    setError('Failed to send verification code')
  }
}

const handleVerifyCode = async () => {
  if (!canVerify.value) return
  
  if (!verificationToken.value) {
    setError('Verification token is missing. Please request a new code.')
    return
  }
  
  setLoading(true)
  clearError()
  emit('verify-code', verificationToken.value, code.value, handleVerificationResult)
}

const handleVerificationResult = (success, errorMessage) => {
  setLoading(false)
  if (success) {
    handleClose()
    emit('verify')
  } else {
    setError(errorMessage || 'Invalid verification code. Please try again.')
  }
}

const handleResendCode = async () => {
  setLoading(true)
  clearError()
  code.value = ''
  emit('resend-code', handleCodeSent)
}

const handleClose = () => {
  hide()
  verificationToken.value = null
  code.value = ''
  clearError()
  emit('close')
}

const handleBackdropClick = () => {
  if (!isLoading.value) {
    handleClose()
  }
}

// Watch for visibility changes
watch(isVisible, (visible) => {
  if (visible) {
    verificationToken.value = null
    code.value = ''
    clearError()
  }
})

// Expose methods for parent component
defineExpose({
  show,
  hide,
  handleClose
})
</script>

<style scoped>
/* Modal Backdrop - Fixed positioning */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1050;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  animation: fadeIn 0.2s ease-out;
}

/* Modal Container */
.modal-container {
  background-color: var(--surface-elevated, #ffffff);
  border: 1px solid var(--border-primary, #e5e7eb);
  border-radius: 0.75rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  width: 100%;
  max-width: 450px;
  max-height: 90vh;
  overflow: hidden;
  animation: slideUp 0.3s ease-out;
  position: relative;
}

.modal-sm {
  max-width: 400px;
}

/* Modal Header */
.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-secondary, #f3f4f6);
  background-color: var(--surface-primary, #ffffff);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  margin: 0;
  display: flex;
  align-items: center;
}

.btn-close-modal {
  background: none;
  border: none;
  padding: 0.25rem;
  cursor: pointer;
  color: var(--text-secondary, #6b7280);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.btn-close-modal:hover {
  background-color: var(--state-hover, #f3f4f6);
  color: var(--text-primary, #1f2937);
}

.btn-close-modal:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal Body */
.modal-body {
  padding: 1.5rem;
  background-color: var(--surface-primary, #ffffff);
}

.verification-step {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.verification-message {
  color: var(--text-secondary, #6b7280);
  margin: 0;
  line-height: 1.5;
}

.email-address {
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  margin: 0;
  padding: 0.75rem;
  background-color: var(--surface-secondary, #f9fafb);
  border-radius: 0.5rem;
  text-align: center;
}

.code-input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.code-input {
  font-size: 1.5rem;
  font-weight: 600;
  text-align: center;
  letter-spacing: 0.5rem;
  font-family: 'Courier New', monospace;
  padding: 1rem;
  border: 2px solid var(--border-primary, #e5e7eb);
  border-radius: 0.5rem;
  transition: all 0.2s;
}

.code-input:focus {
  outline: none;
  border-color: var(--border-accent, #667eea);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.code-input:disabled {
  background-color: var(--state-disabled, #f3f4f6);
  cursor: not-allowed;
}

/* Modal Footer */
.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid var(--border-secondary, #f3f4f6);
  background-color: var(--surface-secondary, #f9fafb);
}

/* Alert */
.alert {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
}

.alert-danger {
  background-color: var(--status-error-bg, #fef2f2);
  color: var(--status-error, #dc2626);
  border: 1px solid var(--status-error, #dc2626);
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Button styles */
.btn {
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--primary, #667eea);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--primary-dark, #5568d3);
}

.btn-secondary {
  background-color: var(--secondary, #6b7280);
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--secondary-dark, #4b5563);
}

.w-100 {
  width: 100%;
}

.me-2 {
  margin-right: 0.5rem;
}

.mt-3 {
  margin-top: 1rem;
}

.gap-2 {
  gap: 0.5rem;
}
</style>

