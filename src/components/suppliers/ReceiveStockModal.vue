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
            <p class="mt-3 loading-text">Loading pending shipments...</p>
          </div>

          <template v-else>
            <!-- Summary Card -->
            <CardTemplate size="compact" shadow="sm" border-color="accent" border-position="start" class="mb-3">
              <template #content>
                <div class="d-flex align-items-center">
                  <Clock :size="16" class="me-2 text-accent" />
                  <span class="summary-text">
                    <strong>{{ pendingShipments.length }}</strong>
                    pending shipment(s) awaiting receipt
                  </span>
                </div>
              </template>
            </CardTemplate>

            <!-- Table Card -->
            <CardTemplate v-if="pendingShipments.length > 0" size="custom" padding="0" shadow="sm">
              <template #content>
                <div class="table-responsive">
                  <table class="table table-hover receive-stock-table mb-0">
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
                        <th>Shipment ID</th>
                        <th>Batch Number</th>
                        <th>Invoice</th>
                        <th>Shipment Date</th>
                        <th>Expected Delivery</th>
                        <th>Freight Cost</th>
                        <th>Days Pending</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="shipment in pendingShipments"
                        :key="shipment.shipment_id"
                        :class="{ 'table-warning': isOverdue(shipment), 'table-active': selectedShipments.includes(shipment.shipment_id) }"
                      >
                        <td>
                          <input
                            type="checkbox"
                            class="form-check-input"
                            :value="shipment.shipment_id"
                            v-model="selectedShipments"
                          >
                        </td>
                        <td>
                          <code class="batch-number-text">{{ shipment.shipment_id }}</code>
                        </td>
                        <td>
                          <code class="batch-number-text">{{ shipment.batch_number || 'N/A' }}</code>
                        </td>
                        <td class="table-cell-text">{{ shipment.invoice_number || 'N/A' }}</td>
                        <td class="table-cell-text">{{ formatDate(shipment.shipment_date) }}</td>
                        <td>
                          <div class="table-cell-text">
                            {{ formatDate(shipment.expected_delivery_date) }}
                            <br>
                            <small v-if="isOverdue(shipment)" class="text-status-error">
                              <AlertTriangle :size="12" class="me-1" />
                              Overdue
                            </small>
                            <small v-else class="date-status-text">
                              {{ getDaysUntil(shipment.expected_delivery_date) }}
                            </small>
                          </div>
                        </td>
                        <td class="table-cell-text">₱{{ formatCurrency(shipment.freight_cost || 0) }}</td>
                        <td class="text-center">
                          <span class="badge" :class="getDaysPendingClass(shipment)">
                            {{ getDaysPending(shipment) }} days
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </CardTemplate>

            <!-- Empty State Card -->
            <CardTemplate v-else size="md" shadow="sm">
              <template #content>
                <div class="text-center py-4">
                  <Package :size="56" class="empty-state-icon mb-3" />
                  <h5 class="empty-state-text">No Pending Shipments</h5>
                  <p class="empty-state-text mb-0">All shipments from this supplier have been received.</p>
                </div>
              </template>
            </CardTemplate>
          </template>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer border-0 pt-4">
          <div class="d-flex justify-content-between align-items-center w-100">
            <div class="footer-info small">
              <span v-if="selectedShipments.length > 0">
                {{ selectedShipments.length }} shipment(s) selected
              </span>
            </div>

            <div class="d-flex gap-3">
              <button
                type="button"
                class="btn btn-cancel px-4"
                @click="handleClose"
              >
                Cancel
              </button>
              <button
                type="button"
                class="btn btn-save px-4"
                @click="receiveSelected"
                :disabled="selectedShipments.length === 0 || receiving"
              >
                <div v-if="receiving" class="spinner-border spinner-border-sm me-2"></div>
                <Package :size="16" class="me-1" />
                Receive {{ selectedShipments.length }} Shipment(s)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Package, Clock, AlertTriangle } from 'lucide-vue-next'
import { useToast } from '@/composables/ui/useToast'
import { useShipments } from '@/composables/api/useShipments'
import CardTemplate from '@/components/common/CardTemplate.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  supplier: { type: Object, required: true }
})

const emit = defineEmits(['close', 'received'])

const { error: showError } = useToast()
const { pendingShipments, loading, fetchShipmentsBySupplier, updateShipment } = useShipments()

const receiving = ref(false)
const selectedShipments = ref([])
const selectAll = ref(false)

async function loadPendingShipments() {
  try {
    await fetchShipmentsBySupplier(props.supplier.id)
  } catch {
    showError('Failed to load pending shipments')
  }
}

function toggleSelectAll() {
  if (selectAll.value) {
    selectedShipments.value = pendingShipments.value.map(s => s.shipment_id)
  } else {
    selectedShipments.value = []
  }
}

async function receiveSelected() {
  if (!selectedShipments.value.length) return

  receiving.value = true
  const results = { successful: [], failed: [] }

  for (const shipmentId of selectedShipments.value) {
    try {
      await updateShipment(shipmentId, { status: 'received' })
      results.successful.push(shipmentId)
    } catch (err) {
      results.failed.push({ id: shipmentId, error: err.message })
    }
  }

  receiving.value = false
  emit('received', results)
  handleClose()
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric'
  })
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-PH', {
    minimumFractionDigits: 2, maximumFractionDigits: 2
  }).format(amount || 0)
}

function isOverdue(shipment) {
  if (!shipment.expected_delivery_date) return false
  return new Date(shipment.expected_delivery_date) < new Date()
}

function getDaysUntil(dateString) {
  if (!dateString) return 'No date set'
  const diffDays = Math.ceil((new Date(dateString) - new Date()) / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return `${Math.abs(diffDays)} days overdue`
  if (diffDays === 0) return 'Due today'
  if (diffDays === 1) return 'Due tomorrow'
  return `${diffDays} days remaining`
}

function getDaysPending(shipment) {
  return Math.ceil(Math.abs(new Date() - new Date(shipment.shipment_date)) / (1000 * 60 * 60 * 24))
}

function getDaysPendingClass(shipment) {
  const days = getDaysPending(shipment)
  if (days <= 3) return 'status-success'
  if (days <= 7) return 'status-warning'
  return 'status-error'
}

function handleClose() {
  emit('close')
  selectedShipments.value = []
  selectAll.value = false
}

function handleOverlayClick() {
  if (!receiving.value) handleClose()
}

watch(() => props.show, (newVal) => {
  if (newVal) loadPendingShipments()
})

onMounted(() => {
  if (props.show) loadPendingShipments()
})
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
  background-color: var(--status-success-bg);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--status-success);
}

.modal-header {
  padding: 1.5rem 1.75rem 0.9rem 1.75rem;
  background-color: var(--surface-secondary);
  border-bottom: 1px solid var(--border-primary);
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
  border-left: 3px solid var(--status-warning) !important;
}

.dark-theme .table-warning {
  background-color: var(--surface-secondary) !important;
  border-left: 3px solid var(--status-warning) !important;
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

.summary-text {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.summary-text strong {
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
