<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content modern-modal" @click.stop>
        <!-- Modal Header -->
        <div class="modal-header">
          <div class="d-flex align-items-center">
            <div class="modal-icon me-3">
              <FileText :size="24" />
            </div>
            <div class="modal-heading">
              <h4 class="modal-title mb-1">Order Details</h4>
              <p class="modal-subtitle mb-0">
                Order ID: <strong>{{ receipt?.id }}</strong>
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
          <div v-if="receipt">
            <!-- Receipt Summary -->
            <div class="receipt-header card mb-4">
              <div class="card-body">
                <div class="row">
                  <div class="col-md-6">
                    <h6 class="text-muted mb-3">Order Information</h6>
                    <div class="info-row">
                      <span class="label">Order ID:</span>
                      <strong>{{ receipt.id }}</strong>
                    </div>
                    <div class="info-row">
                      <span class="label">Order Date:</span>
                      <span>{{ formatDate(receipt.date) }}</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Expected Delivery:</span>
                      <span>{{ formatDate(receipt.expectedDate) }}</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Date Received:</span>
                      <span v-if="receipt.receivedDate" class="text-success">
                        {{ formatDate(receipt.receivedDate) }}
                      </span>
                      <span v-else class="text-warning">
                        <em>Not yet received</em>
                      </span>
                    </div>
                    <div class="info-row">
                      <span class="label">Status:</span>
                      <span :class="['badge', getStatusClass(receipt.status)]">
                        {{ receipt.status }}
                      </span>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <h6 class="text-muted mb-3">Summary</h6>
                    <div class="info-row">
                      <span class="label">Total Items:</span>
                      <strong>{{ receipt.items?.length || 0 }}</strong>
                    </div>
                    <div class="info-row">
                      <span class="label">Total Quantity:</span>
                      <strong>{{ receipt.quantity }}</strong>
                    </div>
                    <div class="info-row">
                      <span class="label">Subtotal:</span>
                      <span>₱{{ formatCurrency(receipt.subtotal || receipt.total) }}</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Total Cost:</span>
                      <strong class="text-primary fs-5">₱{{ formatCurrency(receipt.total) }}</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Items List -->
            <div class="card mb-4">
              <div class="card-header bg-light">
                <h6 class="mb-0">
                  <Package :size="18" class="me-2" />
                  Items Received
                </h6>
              </div>
              <div class="card-body p-0">
                <div class="table-responsive">
                  <table class="table table-hover mb-0">
                    <thead class="table-light">
                      <tr>
                        <th>#</th>
                        <th>Product</th>
                        <th>Batch Number</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Total Price</th>
                        <th>Expiry Date</th>
                        <th>Remaining</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(item, index) in receipt.items" :key="index">
                        <td>{{ index + 1 }}</td>
                        <td>
                          <strong>{{ item.name }}</strong>
                          <br>
                          <small class="text-muted">{{ item.productId }}</small>
                        </td>
                        <td>
                          <code class="text-primary">{{ item.batchNumber }}</code>
                        </td>
                        <td class="text-center">
                          <span class="badge bg-secondary">{{ item.quantity }}</span>
                        </td>
                        <td>₱{{ formatCurrency(item.unitPrice) }}</td>
                        <td class="fw-bold">₱{{ formatCurrency(item.totalPrice) }}</td>
                        <td>
                          <span v-if="item.expiryDate">
                            {{ formatDate(item.expiryDate) }}
                            <br>
                            <small :class="['text-muted', { 'text-danger': isExpiringSoon(item.expiryDate) }]">
                              {{ getExpiryStatus(item.expiryDate) }}
                            </small>
                          </span>
                          <span v-else class="text-muted">N/A</span>
                        </td>
                        <td class="text-center">
                          <span class="badge" :class="getStockClass(item.quantityRemaining, item.quantity)">
                            {{ item.quantityRemaining || 0 }} / {{ item.quantity }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                    <tfoot class="table-light">
                      <tr>
                        <td colspan="3" class="text-end"><strong>Total:</strong></td>
                        <td class="text-center">
                          <strong>{{ getTotalQuantity() }}</strong>
                        </td>
                        <td colspan="2" class="text-end">
                          <strong class="text-primary">₱{{ formatCurrency(receipt.total) }}</strong>
                        </td>
                        <td colspan="2"></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            </div>

            <!-- Notes Section -->
            <div v-if="receipt.notes" class="card">
              <div class="card-header bg-light">
                <h6 class="mb-0">
                  <FileText :size="18" class="me-2" />
                  Notes
                </h6>
              </div>
              <div class="card-body">
                <p class="mb-0">{{ receipt.notes }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer border-0 pt-4">
          <button type="button" class="btn btn-outline-secondary" @click="handleClose">
            Close
          </button>
          <!--<button type="button" class="btn btn-primary" @click="printReceipt">
            <Printer :size="16" class="me-1" />
            Print Receipt
          </button> -->
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { FileText, Package, Printer } from 'lucide-vue-next'
import { useToast } from '@/composables/ui/useToast'

export default {
  name: 'BatchDetailsModal',
  components: {
    FileText,
    Package,
    Printer
  },
  emits: ['close'],
  props: {
    show: {
      type: Boolean,
      default: false
    },
    receipt: {
      type: Object,
      default: null
    }
  },
  setup(props, { emit }) {
    const { success: showSuccess } = useToast()
    
    function handleClose() {
      emit('close')
    }

    function handleOverlayClick(event) {
      if (event.target === event.currentTarget) {
        handleClose()
      }
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
    
    function getStatusClass(status) {
      const classes = {
        'Received': 'bg-success',
        'Pending Delivery': 'bg-warning',
        'Partially Received': 'bg-info',
        'Depleted': 'bg-secondary'
      }
      return classes[status] || 'bg-secondary'
    }
    
    function getStockClass(remaining, total) {
      const percentage = (remaining / total) * 100
      if (percentage === 0) return 'bg-secondary'
      if (percentage < 25) return 'bg-danger'
      if (percentage < 50) return 'bg-warning'
      return 'bg-success'
    }
    
    function isExpiringSoon(expiryDate) {
      if (!expiryDate) return false
      const expiry = new Date(expiryDate)
      const today = new Date()
      const daysUntilExpiry = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24))
      return daysUntilExpiry <= 30 && daysUntilExpiry > 0
    }
    
    function getExpiryStatus(expiryDate) {
      if (!expiryDate) return ''
      const expiry = new Date(expiryDate)
      const today = new Date()
      const daysUntilExpiry = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24))
      
      if (daysUntilExpiry < 0) return 'Expired'
      if (daysUntilExpiry === 0) return 'Expires today'
      if (daysUntilExpiry === 1) return 'Expires tomorrow'
      if (daysUntilExpiry <= 30) return `Expires in ${daysUntilExpiry} days`
      return `${daysUntilExpiry} days until expiry`
    }
    
    function getTotalQuantity() {
      return props.receipt?.items?.reduce((sum, item) => sum + (item.quantity || 0), 0) || 0
    }
    
    function printReceipt() {
      showSuccess('Print functionality coming soon')
      // TODO: Implement print functionality
    }
    
    return {
      handleClose,
      handleOverlayClick,
      formatDate,
      formatCurrency,
      getStatusClass,
      getStockClass,
      isExpiringSoon,
      getExpiryStatus,
      getTotalQuantity,
      printReceipt
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';

.modern-modal {
  border-radius: 16px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  width: min(960px, 90vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--info-light), var(--info));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--info-dark);
}

.modal-header {
  padding: 1.5rem 1.75rem 0.9rem 1.75rem;
  background: linear-gradient(135deg, var(--surface-tertiary), var(--surface-secondary));
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.modal-body {
  padding: 1.5rem 1.75rem;
  max-height: calc(90vh - 220px);
  overflow-y: auto;
  background-color: var(--surface-elevated);
}

.modal-footer {
  padding: 1.25rem 1.75rem 1.75rem 1.75rem;
  background-color: var(--surface-tertiary);
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

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
  backdrop-filter: blur(4px);
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.receipt-header {
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  background-color: var(--surface-primary);
  box-shadow: var(--shadow-sm);
}

.dark-theme .receipt-header {
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: var(--shadow-md);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-primary);
}

.info-row:last-child {
  border-bottom: none;
}

.info-row .label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.card h6,
.card .card-header h6 {
  color: var(--text-primary) !important;
}

.card .text-muted,
.card-header .text-muted {
  color: var(--text-secondary) !important;
}

code {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 0.875rem;
}

.card {
  background-color: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
}

.dark-theme .card {
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: var(--shadow-md);
}

.card-header {
  background-color: var(--surface-tertiary) !important;
  border-bottom: 1px solid rgba(0, 0, 0, 0.15) !important;
  color: var(--text-primary);
}

.dark-theme .card-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
}

.dark-theme .table thead th {
  border-bottom: 2px solid rgba(255, 255, 255, 0.15);
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.card-body {
  background-color: var(--surface-primary);
  color: var(--text-secondary);
}

.bg-light,
.table-light {
  background-color: var(--surface-tertiary) !important;
  color: var(--text-primary) !important;
}

.card-body h6 {
  color: var(--text-primary);
}

.table thead th {
  font-weight: 600;
  font-size: 0.875rem;
  background-color: var(--surface-tertiary);
  color: var(--text-primary);
  border-bottom: 2px solid rgba(0, 0, 0, 0.18);
  border-top: 1px solid rgba(0, 0, 0, 0.18);
}

.table tbody td {
  vertical-align: middle;
  color: var(--text-secondary);
  background-color: var(--surface-primary);
}

.dark-theme .table tbody tr {
  border-color: rgba(255, 255, 255, 0.08);
}

.table tfoot td {
  background-color: var(--surface-tertiary);
  color: var(--text-primary);
  border-top: 1px solid var(--border-primary);
}

.modal-heading {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.modal-title {
  color: var(--text-primary);
  font-weight: 600;
  margin: 0;
  letter-spacing: 0.02em;
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
</style>
