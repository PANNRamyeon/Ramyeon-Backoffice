<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content modern-modal" @click.stop>
        <!-- Modal Header -->
        <div class="modal-header">
          <div class="d-flex align-items-center">
            <div class="modal-icon me-3">
              <Package :size="24" />
            </div>
            <div class="modal-heading">
              <h4 class="modal-title mb-1 receive-stock-title">Receive Pending Stock</h4>
              <p class="modal-subtitle mb-0">
                Select pending orders from <strong>{{ supplier?.name }}</strong> to receive
              </p>
            </div>
          </div>
          <button 
            type="button" 
            class="btn-close" 
            @click="handleClose"
            aria-label="Close"
          ></button>
        </div>

        <!-- Modal Body -->
        <div class="modal-body pt-4">
          <!-- Loading State -->
          <div v-if="loading" class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 loading-text">Loading pending stock...</p>
          </div>

          <!-- Pending Stock List -->
          <div v-else-if="pendingBatches.length > 0">
            <div class="alert alert-info mb-4">
              <Clock :size="16" class="me-2" />
              <strong>{{ pendingBatches.length }}</strong> pending batch(es) awaiting receipt
            </div>

            <div class="table-responsive">
              <table class="table table-hover receive-stock-table">
                <thead class="table-header-theme">
                  <tr>
                    <th style="width: 40px;">
                      <input 
                        type="checkbox" 
                        class="form-check-input" 
                        v-model="selectAll"
                        @change="toggleSelectAll"
                      >
                    </th>
                    <th>Batch Number</th>
                    <th>Product</th>
                    <th>Order Date</th>
                    <th>Expected Date</th>
                    <th>Quantity</th>
                    <th>Est. Cost</th>
                    <th>Total</th>
                    <th>Days Pending</th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="batch in pendingBatches" 
                    :key="batch._id"
                    :class="{ 'table-warning': isOverdue(batch), 'table-active': selectedBatches.includes(batch._id) }"
                  >
                    <td>
                      <input 
                        type="checkbox" 
                        class="form-check-input" 
                        :value="batch._id"
                        v-model="selectedBatches"
                      >
                    </td>
                    <td>
                      <code class="batch-number-text">{{ batch.batch_number }}</code>
                    </td>
                    <td>
                      <div>
                        <strong class="product-name-text">{{ getProductName(batch) }}</strong>
                        <br>
                        <small class="product-id-text">{{ batch.product_id }}</small>
                      </div>
                    </td>
                    <td class="table-cell-text">{{ formatDate(batch.created_at) }}</td>
                    <td>
                      <div class="table-cell-text">
                        {{ formatDate(batch.expected_delivery_date) }}
                        <br>
                        <small v-if="isOverdue(batch)" class="text-danger">
                          <AlertTriangle :size="12" class="me-1" />
                          Overdue
                        </small>
                        <small v-else class="date-status-text">
                          {{ getDaysUntil(batch.expected_delivery_date) }}
                        </small>
                      </div>
                    </td>
                    <td class="text-center">
                      <span class="badge quantity-badge">{{ batch.quantity_received }}</span>
                    </td>
                    <td class="table-cell-text">₱{{ formatCurrency(batch.cost_price || 0) }}</td>
                    <td class="fw-bold table-cell-text">₱{{ formatCurrency((batch.cost_price || 0) * batch.quantity_received) }}</td>
                    <td class="text-center">
                      <span class="badge" :class="getDaysPendingClass(batch)">
                        {{ getDaysPending(batch) }} days
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else class="text-center py-5">
            <Package :size="64" class="empty-state-icon mb-3" />
            <h5 class="empty-state-text">No Pending Stock</h5>
            <p class="empty-state-text">All orders from this supplier have been received.</p>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer border-0 pt-4">
          <div class="d-flex justify-content-between align-items-center w-100">
            <div class="footer-info small">
              <span v-if="selectedBatches.length > 0">
                {{ selectedBatches.length }} batch(es) selected
              </span>
            </div>
            
            <div class="d-flex gap-3">
              <button 
                type="button" 
                class="btn btn-outline-secondary px-4"
                @click="handleClose"
              >
                Cancel
              </button>
              <button 
                type="button" 
                class="btn btn-success px-4"
                @click="receiveSelected"
                :disabled="selectedBatches.length === 0 || receiving"
              >
                <div v-if="receiving" class="spinner-border spinner-border-sm me-2"></div>
                <Package :size="16" class="me-1" />
                Receive {{ selectedBatches.length }} Batch(es)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { 
  Package,
  Clock,
  AlertTriangle
} from 'lucide-vue-next'
import { useToast } from '@/composables/ui/useToast'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export default {
  name: 'ReceiveStockModal',
  components: {
    Package,
    Clock,
    AlertTriangle
  },
  emits: ['close', 'received'],
  props: {
    show: {
      type: Boolean,
      default: false
    },
    supplier: {
      type: Object,
      required: true
    }
  },
  setup(props, { emit }) {
    const { success: showSuccess, error: showError } = useToast()
    
    const loading = ref(false)
    const receiving = ref(false)
    const pendingBatches = ref([])
    const selectedBatches = ref([])
    const selectAll = ref(false)
    
    // ================ COMPUTED ================
    
    const selectedBatchObjects = computed(() => {
      return pendingBatches.value.filter(batch => selectedBatches.value.includes(batch._id))
    })
    
    // ================ METHODS ================
    
    async function loadPendingBatches() {
      loading.value = true
      
      try {
        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('authToken') || sessionStorage.getItem('authToken')
        
        const response = await axios.get(
          `${API_BASE_URL}/batches/by-supplier/${props.supplier.id}/`,
          {
            params: { status: 'pending' },
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        )
        
        // Handle response structure: {success: true, data: [...]}
        if (response.data.success && response.data.data) {
          pendingBatches.value = response.data.data
        } else if (Array.isArray(response.data)) {
          pendingBatches.value = response.data
        } else {
          pendingBatches.value = []
        }
        
        
      } catch (error) {
        console.error('Error loading pending batches:', error)
        showError('Failed to load pending stock')
      } finally {
        loading.value = false
      }
    }
    
    function toggleSelectAll() {
      if (selectAll.value) {
        selectedBatches.value = pendingBatches.value.map(b => b._id)
      } else {
        selectedBatches.value = []
      }
    }
    
    async function receiveSelected() {
      if (selectedBatches.value.length === 0) return
      
      receiving.value = true
      
      try {
        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('authToken') || sessionStorage.getItem('authToken')
        const results = {
          successful: [],
          failed: []
        }
        
        // Activate each selected batch
        for (const batch of selectedBatchObjects.value) {
          try {
            const response = await axios.post(
              `${API_BASE_URL}/batches/activate/`,
              {
                batch_number: batch.batch_number,
                product_id: batch.product_id,
                supplier_id: props.supplier.id,
                // date_received will be set automatically by backend to current time
                notes: `Received via batch activation on ${new Date().toLocaleDateString()}`
              },
              {
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                }
              }
            )
            
            results.successful.push({
              batch: batch.batch_number,
              product: batch.product_id
            })
            
          } catch (error) {
            console.error('Error activating batch:', batch.batch_number, error)
            results.failed.push({
              batch: batch.batch_number,
              error: error.message
            })
          }
        }
        
        // ✅ Don't show toast here - let parent handle it to avoid duplicates
        // Parent (SupplierDetails) will show the success/error toast
        
        // Emit event
        emit('received', results)
        
        // Close modal
        handleClose()
        
      } catch (error) {
        console.error('Error receiving batches:', error)
        showError('Failed to process stock receipt')
      } finally {
        receiving.value = false
      }
    }
    
    function getProductName(batch) {
      // Try to get product name from batch data
      // Check various possible field names
      if (batch.product_name) return batch.product_name
      if (batch.productName) return batch.productName
      if (batch.product_info && batch.product_info.product_name) return batch.product_info.product_name
      if (batch.product_id) return batch.product_id
      return 'Unknown Product'
    }
    
    function formatDate(dateString) {
      if (!dateString) return 'N/A'
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }
    
    function formatCurrency(amount) {
      return new Intl.NumberFormat('en-PH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount || 0)
    }
    
    function isOverdue(batch) {
      if (!batch.expected_delivery_date) return false
      const expectedDate = new Date(batch.expected_delivery_date)
      const today = new Date()
      return expectedDate < today
    }
    
    function getDaysUntil(dateString) {
      if (!dateString) return 'No date set'
      const expectedDate = new Date(dateString)
      const today = new Date()
      const diffTime = expectedDate - today
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays < 0) {
        return `${Math.abs(diffDays)} days overdue`
      } else if (diffDays === 0) {
        return 'Due today'
      } else if (diffDays === 1) {
        return 'Due tomorrow'
      } else {
        return `${diffDays} days remaining`
      }
    }
    
    function getDaysPending(batch) {
      const createdDate = new Date(batch.created_at)
      const today = new Date()
      const diffTime = Math.abs(today - createdDate)
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    }
    
    function getDaysPendingClass(batch) {
      const days = getDaysPending(batch)
      if (days <= 3) return 'bg-success'
      if (days <= 7) return 'bg-warning'
      return 'bg-danger'
    }
    
    function handleClose() {
      emit('close')
      selectedBatches.value = []
      selectAll.value = false
    }
    
    function handleOverlayClick() {
      if (!receiving.value) {
        handleClose()
      }
    }
    
    // ================ LIFECYCLE ================
    
    watch(() => props.show, (newVal) => {
      if (newVal) {
        loadPendingBatches()
      }
    })
    
    onMounted(() => {
      if (props.show) {
        loadPendingBatches()
      }
    })
    
    return {
      loading,
      receiving,
      pendingBatches,
      selectedBatches,
      selectAll,
      toggleSelectAll,
      receiveSelected,
      getProductName,
      formatDate,
      formatCurrency,
      isOverdue,
      getDaysUntil,
      getDaysPending,
      getDaysPendingClass,
      handleClose,
      handleOverlayClick
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';

.modern-modal {
  border-radius: 16px;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-2xl);
  overflow: hidden;
  background-color: var(--surface-elevated);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

.modal-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--success-light), var(--success));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--success-dark);
}

.modal-header {
  padding: 1.5rem 1.75rem 0.9rem 1.75rem;
  background: linear-gradient(135deg, var(--surface-tertiary), var(--surface-secondary));
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.modal-heading {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.receive-stock-title {
  color: var(--text-primary);
}

.modal-subtitle {
  color: var(--text-secondary);
  font-size: 0.9rem;
  letter-spacing: 0.01em;
}

.modal-header .btn-close {
  opacity: 0.7;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.modal-header .btn-close:hover {
  opacity: 1;
  transform: scale(1.05);
}

.dark-theme .modal-header .btn-close {
  filter: invert(1);
}

.modal-body {
  padding: 1.5rem 2rem;
  overflow-y: auto;
  background-color: var(--surface-elevated);
  flex: 1;
  min-height: 0;
}

.modal-footer {
  padding: 1.5rem 2rem;
  background-color: var(--surface-tertiary);
  border-top: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.table-hover tbody tr {
  cursor: pointer;
  transition: all 0.2s ease;
}

.table-hover tbody tr:hover {
  background-color: var(--state-hover);
}

/* Table header styling */
.table-header-theme {
  background-color: var(--surface-tertiary) !important;
}

.table-header-theme th {
  color: var(--text-primary) !important;
  font-weight: 600;
  border-bottom: 2px solid var(--border-primary);
  border-top: 1px solid var(--border-primary);
  border-left: 1px solid var(--border-primary);
  border-right: 1px solid var(--border-primary);
}

.table-header-theme th:first-child {
  border-left: 1px solid var(--border-primary);
}

.table-header-theme th:last-child {
  border-right: 1px solid var(--border-primary);
}

/* Table row styling */
.receive-stock-table tbody tr {
  background-color: var(--surface-primary);
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.receive-stock-table tbody td {
  color: var(--text-secondary);
  border-color: var(--border-primary);
  border-left: 1px solid var(--border-primary);
  border-right: 1px solid var(--border-primary);
  background-color: var(--surface-primary);
}

.receive-stock-table tbody td:first-child {
  border-left: 1px solid var(--border-primary);
}

.receive-stock-table tbody td:last-child {
  border-right: 1px solid var(--border-primary);
}

.receive-stock-table tbody tr:last-child td {
  border-bottom: 1px solid var(--border-primary);
}

.receive-stock-table tbody tr:not(.table-active):not(.table-warning) {
  background-color: var(--surface-primary);
}

.table-active {
  background-color: var(--state-selected) !important;
}

.table-active td {
  color: var(--text-primary) !important;
}

.table-warning {
  background-color: var(--surface-tertiary) !important;
  border-left: 3px solid #f59e0b !important;
}

.dark-theme .table-warning {
  background-color: var(--surface-secondary) !important;
  border-left: 3px solid #fbbf24 !important;
}

.table-warning td {
  color: var(--text-secondary) !important;
}

/* Text colors for table cells */
.table-cell-text {
  color: var(--text-secondary);
}

.batch-number-text {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 0.875rem;
  color: var(--text-accent);
  background-color: transparent;
  padding: 0;
}

.product-name-text {
  color: var(--text-primary);
}

.product-id-text {
  color: var(--text-tertiary);
}

.date-status-text {
  color: var(--text-tertiary);
}

.quantity-badge {
  background-color: var(--surface-tertiary) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-primary);
}

/* Alert styling */
.alert-info {
  background-color: var(--surface-tertiary);
  border: 1px solid var(--border-accent);
  color: var(--text-secondary);
}

.alert-info strong {
  color: var(--text-primary);
}

code {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 0.875rem;
}

/* Modal Overlay */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background-color: rgba(0, 0, 0, 0.5) !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  z-index: 9999 !important;
  animation: fadeIn 0.3s ease;
  backdrop-filter: blur(4px);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Modal Content */
.modal-content {
  position: relative !important;
  max-width: 1200px;
  width: 95%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
  z-index: 10000 !important;
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

/* Responsive Styles */
@media (max-width: 768px) {
  .modal-content {
    margin: 1rem;
    max-height: calc(100vh - 2rem);
    width: calc(100% - 2rem);
  }

  .modal-header {
    padding: 1.5rem 1.5rem 1rem 1.5rem !important;
  }

  .modal-header h4 {
    font-size: 1.25rem;
  }

  .modal-body {
    padding: 1rem 1.5rem !important;
    max-height: calc(100vh - 250px);
  }

  .modal-footer {
    padding: 1rem 1.5rem 1.5rem 1.5rem !important;
  }

  /* Make table scrollable on mobile */
  .table-responsive {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .table {
    font-size: 0.85rem;
  }

  .table th,
  .table td {
    padding: 0.5rem 0.5rem;
    white-space: nowrap;
  }
}

@media (max-width: 480px) {
  .modal-content {
    margin: 0.5rem;
    max-height: calc(100vh - 1rem);
    width: calc(100% - 1rem);
    border-radius: 8px;
  }

  .modal-header {
    padding: 1rem 1rem 0.75rem 1rem !important;
  }

  .modal-header h4 {
    font-size: 1.1rem;
  }

  .modal-icon {
    width: 40px !important;
    height: 40px !important;
  }

  .modal-body {
    padding: 0.75rem 1rem !important;
    max-height: calc(100vh - 200px);
  }

  .modal-footer {
    padding: 0.75rem 1rem 1rem 1rem !important;
    flex-direction: column;
    gap: 0.75rem;
  }

  .modal-footer .d-flex {
    flex-direction: column;
    gap: 0.75rem;
  }

  .modal-footer .d-flex.justify-content-between {
    flex-direction: column;
    align-items: stretch !important;
  }

  .btn {
    width: 100%;
    margin: 0 !important;
  }

  .table {
    font-size: 0.8rem;
  }

  .table th,
  .table td {
    padding: 0.375rem 0.25rem;
    font-size: 0.75rem;
  }

  .badge {
    font-size: 0.7rem;
    padding: 0.25rem 0.5rem;
  }
}

/* Custom scrollbar for modal */
.modal-content::-webkit-scrollbar {
  width: 8px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--surface-tertiary);
  border-radius: 4px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 4px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--border-accent);
}

/* Prevent body scroll when modal is open */
body:has(.modal-overlay) {
  overflow: hidden !important;
}

/* Dark mode text classes */
.modal-subtitle {
  color: var(--text-secondary);
}

.loading-text {
  color: var(--text-secondary);
}

.footer-info {
  color: var(--text-secondary);
}

.empty-state-icon {
  color: var(--text-tertiary);
  opacity: 0.6;
}

.empty-state-text {
  color: var(--text-secondary);
}
</style>
