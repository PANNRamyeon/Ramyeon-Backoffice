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
        <h4 class="text-error mb-0 fw-semibold d-flex align-items-center gap-2">
          <AlertTriangle :size="20" />
          {{ config.title }}
        </h4>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        <p class="text-secondary mb-4">{{ config.message }}</p>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        <div class="d-flex justify-content-end gap-3">
          <button
            type="button"
            class="btn btn-cancel"
            @click="handleCancel"
            :disabled="isLoading"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-with-icon"
            :class="config.confirmClass || 'btn-delete'"
            @click="handleConfirm"
            :disabled="isLoading"
          >
            <div v-if="isLoading" class="spinner-border spinner-border-sm me-2"></div>
            {{ isLoading ? 'Deleting...' : config.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useModal } from '@/composables/ui/useModal.js'

// Props
const props = defineProps({
  isLoading: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['confirm', 'cancel'])

// Composables
const { isVisible, show, hide } = useModal()

// State
const config = ref({
  title: 'Confirm Delete',
  message: 'Are you sure you want to delete this item?',
  confirmText: 'Delete',
  confirmClass: 'btn-delete'
})

// Methods
const openModal = (options = {}) => {
  config.value = {
    ...config.value,
    ...options
  }
  show()
}

const closeModal = () => {
  hide()
}

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  emit('cancel')
  closeModal()
}

const handleBackdropClick = () => {
  if (!props.isLoading) {
    handleCancel()
  }
}

// Expose methods for parent component
defineExpose({
  openModal,
  closeModal
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
  background-color: var(--surface-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  box-shadow: var(--shadow-2xl);
  width: 100%;
  max-width: 500px;
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
  border-bottom: 1px solid var(--border-secondary);
  background-color: var(--surface-primary);
}

/* Modal Body */
.modal-body {
  padding: 1.5rem;
  background-color: var(--surface-primary);
}

/* Modal Footer */
.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid var(--border-secondary);
  background-color: var(--surface-secondary);
}

/* Loading spinner */
.spinner-border-sm {
  width: 0.875rem;
  height: 0.875rem;
  border-width: 0.125em;
  animation: spin 0.75s linear infinite;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(1rem) scale(0.95);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Utility classes */
.d-flex { display: flex; }
.justify-content-end { justify-content: flex-end; }
.align-items-center { align-items: center; }
.gap-2 { gap: 0.5rem; }
.gap-3 { gap: 0.75rem; }
.mb-0 { margin-bottom: 0; }
.mb-4 { margin-bottom: 1rem; }
.me-2 { margin-right: 0.5rem; }
.fw-semibold { font-weight: 600; }

/* Responsive adjustments */
@media (max-width: 640px) {
  .modal-container {
    margin: 0.5rem;
    max-height: 95vh;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }
}
</style>