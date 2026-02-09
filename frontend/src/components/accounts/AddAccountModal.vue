<template>
  <div v-if="isVisible" class="modal-overlay" @click="handleOverlayClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>
          {{ modalTitle }}
        </h2>
        <button 
          type="button" 
          class="btn-close" 
          @click="handleClose"
          :disabled="isLoading"
        >
          <X :size="20" />
        </button>
      </div>

      <!-- View Mode -->
      <div v-if="mode === 'view'" class="modal-body">
        <div class="user-details">
          <div class="detail-row">
            <strong>ID:</strong>
            <span>{{ formData._id }}</span>
          </div>
          <div class="detail-row">
            <strong>Username:</strong>
            <span>{{ formData.username }}</span>
          </div>
          <div class="detail-row">
            <strong>Full Name:</strong>
            <span>{{ formData.full_name }}</span>
          </div>
          <div class="detail-row">
            <strong>Email:</strong>
            <span>{{ formData.email }}</span>
          </div>
          <div class="detail-row">
            <strong>Role:</strong>
            <span class="badge" :class="formData.role === 'admin' ? 'bg-warning' : 'bg-info'">
              {{ formData.role }}
            </span>
          </div>
          <div class="detail-row">
            <strong>Status:</strong>
            <span class="badge" :class="formData.status === 'active' ? 'bg-success' : 'bg-secondary'">
              {{ formData.status }}
            </span>
          </div>
          <div class="detail-row">
            <strong>Last Login:</strong>
            <span>{{ formatDate(formData.last_login) }}</span>
          </div>
          <div class="detail-row">
            <strong>Date Created:</strong>
            <span>{{ formatDate(formData.date_created) }}</span>
          </div>
          <div class="detail-row">
            <strong>Last Updated:</strong>
            <span>{{ formatDate(formData.last_updated) }}</span>
          </div>
        </div>

        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-cancel"
            @click="handleClose"
          >
            Close
          </button>
          <button
            type="button"
            class="btn btn-edit"
            @click="switchToEditMode"
          >
            <Edit :size="16" />
            Edit User
          </button>
        </div>
      </div>

      <!-- Edit/Add Mode -->
      <form v-else @submit.prevent="handleSubmit" class="modal-body">
        <div class="form-group">
          <label for="username">Username *</label>
          <input
            id="username"
            v-model="formData.username"
            type="text"
            class="form-control"
            :class="{ 'is-invalid': validationErrors.username }"
            :disabled="mode === 'edit' || isLoading"
            placeholder="Enter username"
            required
            @blur="validateField('username')"
          />
          <div v-if="validationErrors.username" class="invalid-feedback">
            {{ validationErrors.username }}
          </div>
        </div>

        <div class="form-group">
          <label for="email">Email *</label>
          <input
            id="email"
            v-model="formData.email"
            type="email"
            class="form-control"
            :class="{ 'is-invalid': validationErrors.email }"
            :disabled="isLoading"
            placeholder="Enter email address"
            required
            @blur="validateField('email')"
          />
          <div v-if="validationErrors.email" class="invalid-feedback">
            {{ validationErrors.email }}
          </div>
        </div>

        <div class="form-group">
          <label for="full_name">Full Name *</label>
          <input
            id="full_name"
            v-model="formData.full_name"
            type="text"
            class="form-control"
            :class="{ 'is-invalid': validationErrors.full_name }"
            :disabled="isLoading"
            placeholder="Enter full name"
            required
            @blur="validateField('full_name')"
          />
          <div v-if="validationErrors.full_name" class="invalid-feedback">
            {{ validationErrors.full_name }}
          </div>
        </div>

        <div v-if="mode === 'add'" class="form-group">
          <label for="password">Password *</label>
          <input
            id="password"
            v-model="formData.password"
            type="password"
            class="form-control"
            :class="{ 'is-invalid': validationErrors.password }"
            :disabled="isLoading"
            placeholder="Minimum 6 characters"
            required
            minlength="6"
            @blur="validateField('password')"
          />
          <div v-if="validationErrors.password" class="invalid-feedback">
            {{ validationErrors.password }}
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="role">Role *</label>
            <select
              id="role"
              v-model="formData.role"
              class="form-control"
              :class="{ 'is-invalid': validationErrors.role }"
              :disabled="isLoading"
              required
              @change="validateField('role')"
            >
              <option value="">Select Role</option>
              <option value="admin">Admin</option>
              <option value="employee">Employee</option>
            </select>
            <div v-if="validationErrors.role" class="invalid-feedback">
              {{ validationErrors.role }}
            </div>
          </div>

          <div class="form-group">
            <label for="status">Status *</label>
            <select
              id="status"
              v-model="formData.status"
              class="form-control"
              :disabled="isLoading"
              required
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>

        <div v-if="error" class="alert alert-danger">
          {{ error }}
        </div>

        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-cancel"
            @click="handleClose"
            :disabled="isLoading"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="btn btn-save"
            :disabled="isLoading || hasValidationErrors"
          >
            {{ isLoading ? 'Saving...' : (mode === 'edit' ? 'Update User' : 'Create User') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useModal } from '@/composables/ui/useModal'

// Emits
const emit = defineEmits(['submit', 'close'])

// Composable
const { isVisible, isLoading, error, show, hide, setLoading, setError, clearError } = useModal()

// Mode: 'add', 'edit', 'view'
const mode = ref('add')

// Form data
const formData = ref({
  _id: '',
  username: '',
  email: '',
  full_name: '',
  password: '',
  role: '',
  status: 'active',
  last_login: null,
  date_created: null,
  last_updated: null
})

// Validation errors
const validationErrors = ref({})

// Computed
const modalTitle = computed(() => {
  switch (mode.value) {
    case 'view':
      return 'User Account Details'
    case 'edit':
      return 'Edit User Account'
    case 'add':
    default:
      return 'Add New User Account'
  }
})

const hasValidationErrors = computed(() => {
  return Object.keys(validationErrors.value).length > 0
})

// Methods
const validateField = (fieldName) => {
  const errors = { ...validationErrors.value }

  switch (fieldName) {
    case 'username':
      if (!formData.value.username) {
        errors.username = 'Username is required'
      } else if (formData.value.username.length < 3) {
        errors.username = 'Username must be at least 3 characters'
      } else if (!/^[a-zA-Z0-9_]+$/.test(formData.value.username)) {
        errors.username = 'Username can only contain letters, numbers, and underscores'
      } else {
        delete errors.username
      }
      break

    case 'email':
      if (!formData.value.email) {
        errors.email = 'Email is required'
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.value.email)) {
        errors.email = 'Please enter a valid email address'
      } else {
        delete errors.email
      }
      break

    case 'full_name':
      if (!formData.value.full_name) {
        errors.full_name = 'Full name is required'
      } else if (formData.value.full_name.length < 2) {
        errors.full_name = 'Full name must be at least 2 characters'
      } else {
        delete errors.full_name
      }
      break

    case 'password':
      if (mode.value === 'add') {
        if (!formData.value.password) {
          errors.password = 'Password is required'
        } else if (formData.value.password.length < 6) {
          errors.password = 'Password must be at least 6 characters'
        } else {
          delete errors.password
        }
      }
      break

    case 'role':
      if (!formData.value.role) {
        errors.role = 'Role is required'
      } else {
        delete errors.role
      }
      break
  }

  validationErrors.value = errors
}

const validateForm = () => {
  validationErrors.value = {}
  
  const fields = ['username', 'email', 'full_name', 'role']
  if (mode.value === 'add') {
    fields.push('password')
  }
  
  fields.forEach(field => validateField(field))
  
  return Object.keys(validationErrors.value).length === 0
}

const resetForm = () => {
  formData.value = {
    _id: '',
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: '',
    status: 'active',
    last_login: null,
    date_created: null,
    last_updated: null
  }
  validationErrors.value = {}
  clearError()
}

const handleSubmit = async () => {
  if (!validateForm()) {
    return
  }

  setLoading(true)
  clearError()

  try {
    const submitData = { ...formData.value }
    // Remove password field if empty in edit mode
    if (mode.value === 'edit' && !submitData.password) {
      delete submitData.password
    }
    
    await emit('submit', submitData, mode.value)
    hide()
    resetForm()
  } catch (err) {
    setError(err.message || 'Failed to save user')
  } finally {
    setLoading(false)
  }
}

const handleClose = () => {
  if (!isLoading.value) {
    hide()
    resetForm()
    emit('close')
  }
}

const handleOverlayClick = () => {
  if (!isLoading.value) {
    handleClose()
  }
}

const switchToEditMode = () => {
  mode.value = 'edit'
}

const openModal = (modalMode = 'add', userData = null) => {
  mode.value = modalMode
  
  if (userData) {
    formData.value = {
      _id: userData._id || '',
      username: userData.username || '',
      email: userData.email || '',
      full_name: userData.full_name || '',
      password: '',
      role: userData.role || '',
      status: userData.status || 'active',
      last_login: userData.last_login || null,
      date_created: userData.date_created || null,
      last_updated: userData.last_updated || null
    }
  } else {
    resetForm()
  }
  
  show()
}

const formatDate = (dateString) => {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleString()
}

// Expose methods
defineExpose({
  show: openModal,
  hide: handleClose
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--surface-primary);
  border-radius: 0.75rem;
  box-shadow: var(--shadow-2xl);
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-secondary);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  padding: 0.5rem;
  cursor: pointer;
  color: var(--text-tertiary);
  border-radius: 0.375rem;
  transition: all 0.2s ease;
}

.btn-close:hover:not(:disabled) {
  background: var(--state-hover);
  color: var(--text-primary);
}

.btn-close:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

/* View Mode Styles */
.user-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.detail-row {
  display: flex;
  gap: 1rem;
  padding: 0.75rem;
  background: var(--surface-secondary);
  border-radius: 0.375rem;
  align-items: center;
}

.detail-row strong {
  min-width: 140px;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.875rem;
}

.detail-row span {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.bg-warning {
  background: var(--status-warning-bg);
  color: var(--status-warning);
}

.badge.bg-info {
  background: var(--status-info-bg);
  color: var(--status-info);
}

.badge.bg-success {
  background: var(--status-success-bg);
  color: var(--status-success);
}

.badge.bg-secondary {
  background: var(--surface-tertiary);
  color: var(--text-tertiary);
}

/* Form Styles */
.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.form-control {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  background: var(--input-bg);
  color: var(--input-text);
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.form-control:focus {
  outline: none;
  border-color: var(--border-accent);
  box-shadow: 0 0 0 3px rgba(160, 123, 227, 0.25);
}

.form-control::placeholder {
  color: var(--input-placeholder);
}

.form-control:disabled {
  background: var(--surface-tertiary);
  cursor: not-allowed;
  opacity: 0.6;
}

.form-control.is-invalid {
  border-color: var(--border-error);
}

.form-control.is-invalid:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.25);
}

.invalid-feedback {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: var(--status-error);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.modal-footer {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid var(--border-secondary);
}

.alert {
  padding: 0.75rem 1rem;
  border-radius: 0.375rem;
  margin-bottom: 1rem;
}

.alert-danger {
  background: var(--status-error-bg);
  color: var(--status-error);
  border: 1px solid var(--status-error);
}

@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 95vh;
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .detail-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .detail-row strong {
    min-width: auto;
  }
}
</style>