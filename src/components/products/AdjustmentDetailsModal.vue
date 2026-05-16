<template>
  <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2 class="text-tertiary-dark">Adjustment Details</h2>
        <button class="btn-close" @click="closeModal" aria-label="Close">
          ✕
        </button>
      </div>

      <div v-if="adjustment" class="modal-body">
        <div class="detail-section">
          <h6 class="text-primary mb-3">Basic Information</h6>
          
          <div class="row mb-2">
            <div class="col-6">
              <small class="text-tertiary-medium d-block">Batch Number</small>
              <span class="text-secondary fw-semibold">{{ adjustment.batch_number }}</span>
            </div>
            <div class="col-6">
              <small class="text-tertiary-medium d-block">Date & Time</small>
              <span class="text-secondary">{{ formatDateTime(adjustment.timestamp) }}</span>
            </div>
          </div>

          <div class="row mb-2">
            <div class="col-6">
              <small class="text-tertiary-medium d-block">Adjustment Type</small>
              <span :class="getTypeBadgeClass(adjustment.adjustment_type)">
                {{ formatType(adjustment.adjustment_type) }}
              </span>
            </div>
            <div class="col-6">
              <small class="text-tertiary-medium d-block">Source</small>
              <span class="text-secondary">{{ formatSource(adjustment.source) }}</span>
            </div>
          </div>
        </div>

        <div class="divider-theme my-3"></div>

        <div class="detail-section">
          <h6 class="text-primary mb-3">Quantity Changes</h6>
          
          <div class="row mb-2">
            <div class="col-6">
              <small class="text-tertiary-medium d-block">Quantity Adjusted</small>
              <span class="badge bg-danger fs-6">-{{ adjustment.quantity_used }}</span>
            </div>
            <div class="col-6">
              <small class="text-tertiary-medium d-block">Remaining After</small>
              <span class="text-success fw-semibold fs-6">{{ adjustment.remaining_after }}</span>
            </div>
          </div>
        </div>

        <div class="divider-theme my-3"></div>

        <div class="detail-section">
          <h6 class="text-primary mb-3">Tracking Information</h6>
          
          <div class="row mb-2">
            <div class="col-6">
              <small class="text-tertiary-medium d-block">Adjusted By</small>
              <span class="text-secondary">{{ adjustment.adjusted_by || 'System' }}</span>
            </div>
            <div class="col-6">
              <small class="text-tertiary-medium d-block">Approved By</small>
              <span class="text-secondary">{{ adjustment.approved_by || 'N/A' }}</span>
            </div>
          </div>

          <div class="row">
            <div class="col-12">
              <small class="text-tertiary-medium d-block">Notes</small>
              <p class="text-secondary mb-0">{{ adjustment.notes || 'No additional notes' }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="closeModal" class="btn btn-cancel">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'AdjustmentDetailsModal',
  emits: ['close'],
  
  setup(props, { emit }) {
    const show = ref(false)
    const adjustment = ref(null)

    const open = (adjustmentData) => {
      adjustment.value = adjustmentData
      show.value = true
    }

    const closeModal = () => {
      show.value = false
      adjustment.value = null
      emit('close')
    }

    const handleOverlayClick = () => {
      closeModal()
    }

    const formatDateTime = (dateString) => {
      if (!dateString) return 'N/A'
      return new Date(dateString).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const formatType = (type) => {
      if (!type) return 'Unknown'
      return type.charAt(0).toUpperCase() + type.slice(1)
    }

    const formatSource = (source) => {
      if (!source) return 'Unknown'
      return source.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
      ).join(' ')
    }

    const getTypeBadgeClass = (type) => {
      const typeClasses = {
        'sale': 'badge bg-success',
        'damage': 'badge bg-danger',
        'theft': 'badge bg-danger',
        'spoilage': 'badge bg-warning',
        'return': 'badge bg-info',
        'shrinkage': 'badge bg-warning',
        'correction': 'badge bg-secondary'
      }
      return typeClasses[type] || 'badge bg-secondary'
    }

    return {
      show,
      adjustment,
      open,
      closeModal,
      handleOverlayClick,
      formatDateTime,
      formatType,
      formatSource,
      getTypeBadgeClass
    }
  }
}
</script>

<style scoped>
/* Copy modal styles from StockUpdateModal.vue */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  max-width: 600px;
  width: 95%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from { 
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--neutral);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--tertiary-medium);
  padding: 0.25rem;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background-color: var(--neutral-light);
  color: var(--tertiary-dark);
}

.modal-body {
  padding: 1.5rem 2rem;
}

.modal-footer {
  padding: 1rem 2rem;
  border-top: 1px solid var(--neutral);
  display: flex;
  justify-content: flex-end;
}

.detail-section {
  margin-bottom: 1rem;
}

.text-tertiary-dark {
  color: var(--tertiary-dark) !important;
}

.text-tertiary-medium {
  color: var(--tertiary-medium) !important;
}
</style>