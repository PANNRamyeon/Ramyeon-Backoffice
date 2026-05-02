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
                    <h6 class="text-secondary mb-3">Order Information</h6>
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
                      <span v-if="receipt.receivedDate" class="text-status-success">
                        {{ formatDate(receipt.receivedDate) }}
                      </span>
                      <span v-else class="text-status-warning">
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
                    <h6 class="text-secondary mb-3">Summary</h6>
                    <div class="info-row">
                      <span class="label">Total Items:</span>
                      <strong>{{ loading ? '…' : totalItems }}</strong>
                    </div>
                    <div class="info-row">
                      <span class="label">Total Quantity:</span>
                      <strong>{{ loading ? '…' : totalQuantity }}</strong>
                    </div>
                    <div class="info-row">
                      <span class="label">Subtotal:</span>
                      <span>₱{{ formatCurrency(totalCost) }}</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Total Cost:</span>
                      <strong class="text-accent fs-5">₱{{ formatCurrency(totalCost) }}</strong>
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
                      <tr v-if="loading">
                        <td colspan="8" class="text-center py-4">
                          <div class="spinner-border spinner-border-sm text-accent me-2"></div>
                          Loading items…
                        </td>
                      </tr>
                      <tr v-else-if="batchItems.length === 0">
                        <td colspan="8" class="text-center py-4 text-secondary">No items found for this order</td>
                      </tr>
                      <tr v-for="(item, index) in batchItems" :key="index" v-else>
                        <td>{{ index + 1 }}</td>
                        <td>
                          <strong>{{ item.name }}</strong>
                          <br>
                          <small class="text-secondary">{{ item.productId }}</small>
                        </td>
                        <td>
                          <code class="text-accent">{{ item.batchNumber }}</code>
                        </td>
                        <td class="text-center">
                          <span class="badge">{{ item.quantity }}</span>
                        </td>
                        <td>₱{{ formatCurrency(item.unitPrice) }}</td>
                        <td class="fw-bold">₱{{ formatCurrency(item.totalPrice) }}</td>
                        <td>
                          <span v-if="item.expiryDate">
                            {{ formatDate(item.expiryDate) }}
                            <br>
                            <small :class="['text-secondary', { 'text-status-error': isExpiringSoon(item.expiryDate) }]">
                              {{ getExpiryStatus(item.expiryDate) }}
                            </small>
                          </span>
                          <span v-else class="text-secondary">N/A</span>
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
                          <strong>{{ totalQuantity }}</strong>
                        </td>
                        <td colspan="2" class="text-end">
                          <strong class="text-accent">₱{{ formatCurrency(totalCost) }}</strong>
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
          <button type="button" class="btn btn-cancel" @click="handleClose">
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

<script setup>
import { ref, computed, watch } from 'vue'
import { FileText, Package, Printer } from 'lucide-vue-next'
import { useShipments } from '@/composables/api/useShipments'

const props = defineProps({
  show:    { type: Boolean, default: false },
  receipt: { type: Object,  default: null  }
})

const emit = defineEmits(['close'])

const { fetchShipmentWithBatches } = useShipments()

// ── State ─────────────────────────────────────────────────────────────────────
const batchItems  = ref([])
const loading     = ref(false)

// ── Derived totals from live batch data ───────────────────────────────────────
const totalItems    = computed(() => batchItems.value.length)
const totalQuantity = computed(() => batchItems.value.reduce((s, i) => s + (i.quantity || 0), 0))
const totalCost     = computed(() => batchItems.value.reduce((s, i) => s + (i.totalPrice || 0), 0))

// ── Fetch batches when modal opens ────────────────────────────────────────────
async function loadBatches() {
  if (!props.receipt?.id) return
  loading.value = true
  batchItems.value = []
  try {
    const shipment = await fetchShipmentWithBatches(props.receipt.id, true)
    batchItems.value = (shipment?.batches || []).map(b => ({
      name:              b.product_name || 'Unknown Product',
      productId:         b.product_id   || '',
      batchNumber:       b.batch_number || '',
      quantity:          Number(b.quantity_received) || 0,
      unitPrice:         Number(b.cost_price)        || 0,
      totalPrice:        (Number(b.cost_price) || 0) * (Number(b.quantity_received) || 0),
      expiryDate:        b.expiry_date  || null,
      quantityRemaining: Number(b.quantity_remaining) || 0,
      status:            b.status       || ''
    }))
  } catch {
    batchItems.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.show, newVal => { if (newVal) loadBatches() }, { immediate: true })

// ── Helpers ───────────────────────────────────────────────────────────────────
function handleClose() { emit('close') }

function handleOverlayClick(event) {
  if (event.target === event.currentTarget) handleClose()
}

function formatDate(d) {
  if (!d) return 'N/A'
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount || 0)
}

function getStatusClass(status) {
  return { 'Received': 'status-success', 'Pending Delivery': 'status-warning',
           'Partially Received': 'status-info', 'Depleted': '' }[status] ?? ''
}

function getStockClass(remaining, total) {
  const pct = total > 0 ? (remaining / total) * 100 : 0
  if (pct === 0) return ''
  if (pct < 25)  return 'status-error'
  if (pct < 50)  return 'status-warning'
  return 'status-success'
}

function isExpiringSoon(expiryDate) {
  if (!expiryDate) return false
  const days = Math.ceil((new Date(expiryDate) - new Date()) / 86400000)
  return days > 0 && days <= 30
}

function getExpiryStatus(expiryDate) {
  if (!expiryDate) return ''
  const days = Math.ceil((new Date(expiryDate) - new Date()) / 86400000)
  if (days < 0)  return 'Expired'
  if (days === 0) return 'Expires today'
  if (days === 1) return 'Expires tomorrow'
  if (days <= 30) return `Expires in ${days} days`
  return `${days} days until expiry`
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
  background-color: var(--status-info-bg);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--status-info);
}

.modal-header {
  padding: 1.5rem 1.75rem 0.9rem 1.75rem;
  background: linear-gradient(135deg, var(--surface-tertiary), var(--surface-secondary));
  border-bottom: 1px solid var(--border-primary);
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
  border-top: 1px solid var(--border-primary);
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
  border: 1px solid var(--border-primary);
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

.card-header {
  background-color: var(--surface-tertiary) !important;
  border-bottom: 1px solid var(--border-primary) !important;
  color: var(--text-primary);
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
  border-bottom: 2px solid var(--border-primary);
  border-top: 1px solid var(--border-primary);
}

.table tbody td {
  vertical-align: middle;
  color: var(--text-secondary);
  background-color: var(--surface-primary);
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
