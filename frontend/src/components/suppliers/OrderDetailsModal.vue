<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content modern-modal order-details-modal" @click.stop>
        <div class="modal-header border-0 pb-0">
          <div class="d-flex align-items-center flex-grow-1">
            <div class="modal-icon me-3">
              <component :is="isEditMode ? Edit : Eye" :size="24" />
            </div>
            <div class="flex-grow-1">
              <h4 class="modal-title mb-1">
                {{ isEditMode ? 'Edit Order' : 'Order Details' }}
              </h4>
              <p class="text-secondary mb-0 small">
                {{ isEditMode ? 'Modify order information' : 'View order information' }}
              </p>
            </div>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button 
              v-if="!isEditMode && canEdit" 
              type="button" 
              class="btn btn-edit btn-sm"
              @click="toggleEditMode"
            >
              <Edit :size="16" class="me-1" />
              Edit Order
            </button>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
        </div>
        
        <div class="modal-body pt-4">
          <!-- Order Header Info -->
          <div class="row mb-4">
            <div class="col-md-6">
              <div class="info-card">
                <h6 class="info-card-title">
                  <FileText :size="16" class="me-2" />
                  Order Information
                </h6>
                <div class="info-item">
                  <label>Order ID:</label>
                  <span class="order-id-text">{{ order.id }}</span>
                </div>
                <div class="info-item">
                  <label>Order Date:</label>
                  <span>{{ formatDate(order.date) }}</span>
                </div>
                <div class="info-item">
                  <label>Expected Date:</label>
                  <div v-if="!isEditMode">
                    <span>{{ formatDate(order.expectedDate) }}</span>
                    <br>
                    <small :class="['text-secondary', { 'text-status-error': isOverdue(order) }]">
                      {{ getTimeRemaining(order.expectedDate) }}
                    </small>
                  </div>
                  <input 
                    v-else
                    type="date" 
                    class="form-control form-control-sm"
                    v-model="editForm.expectedDate"
                  >
                </div>
                <div class="info-item mb-0">
                  <label>Status:</label>
                  <div v-if="!isEditMode">
                    <span :class="['badge', 'order-status', getOrderStatusClass(order.status)]">
                      {{ order.status }}
                    </span>
                  </div>
                  <select v-else class="form-select form-select-sm" v-model="editForm.status">
                    <option value="Pending Delivery">Pending Delivery</option>
                    <option value="Partially Received">Partially Received</option>
                    <option value="Received">Received</option>
                    <option value="Cancelled">Cancelled</option>
                  </select>
                </div>
              </div>
            </div>
            
            <div class="col-md-6">
              <div class="info-card">
                <h6 class="info-card-title">
                  <DollarSign :size="16" class="me-2" />
                  Financial Summary
                </h6>
                <div class="info-item">
                  <label>Total Items:</label>
                  <span>{{ displayItemCount }} item(s)</span>
                </div>
                <div class="info-item">
                  <label>Total Quantity:</label>
                  <span>{{ displayTotalQuantity }}</span>
                </div>
                <div class="info-item">
                  <label>Subtotal:</label>
                  <span class="text-secondary">₱{{ formatCurrency(order.subtotal || 0) }}</span>
                </div>
                <div class="info-item">
                  <label>Tax ({{ order.taxRate || 12 }}%):</label>
                  <span class="text-secondary">₱{{ formatCurrency(order.tax || 0) }}</span>
                </div>
                <div class="info-item">
                  <label>Shipping:</label>
                  <div v-if="!isEditMode">
                    <span class="text-secondary">₱{{ formatCurrency(order.shippingCost || 0) }}</span>
                  </div>
                  <div v-else class="input-group input-group-sm">
                    <span class="input-group-text">₱</span>
                    <input 
                      type="number" 
                      class="form-control"
                      v-model.number="editForm.shippingCost"
                      min="0"
                      step="0.01"
                    >
                  </div>
                </div>
                <div class="info-item mb-0">
                  <label>Total Cost:</label>
                  <span class="amount-text">₱{{ formatCurrency(order.total) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Order Items (if available) -->
          <div v-if="orderItems && orderItems.length > 0" class="info-card mb-4">
            <h6 class="info-card-title">
              <List :size="16" class="me-2" />
              Order Items
              <span class="badge ms-2">{{ orderItems.length }}</span>
            </h6>
            <div class="table-responsive">
              <table class="table table-sm items-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Item Name / Description</th>
                    <th>Quantity</th>
                    <th>Unit</th>
                    <th>Unit Price</th>
                    <th>Total Price</th>
                    <th v-if="!isEditMode">Notes</th>
                    <th v-if="isEditMode">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in orderItems" :key="`item-${index}`">
                    <td>{{ index + 1 }}</td>
                    <td>
                      <input 
                        v-if="isEditMode"
                        type="text" 
                        class="form-control form-control-sm"
                        v-model="item.name"
                        placeholder="Enter item name or description"
                      >
                      <span v-else class="fw-medium">{{ item.name }}</span>
                    </td>
                    <td>
                      <input 
                        v-if="isEditMode"
                        type="number" 
                        class="form-control form-control-sm"
                        v-model.number="item.quantity"
                        min="1"
                        @input="calculateItemTotal(item)"
                        style="width: 80px;"
                      >
                      <span v-else class="fw-bold">{{ item.quantity }}</span>
                    </td>
                    <td>
                      <select 
                        v-if="isEditMode"
                        class="form-select form-select-sm"
                        v-model="item.unit"
                        style="width: 80px;"
                      >
                        <option value="pcs">pcs</option>
                        <option value="kg">kg</option>
                        <option value="lbs">lbs</option>
                        <option value="box">box</option>
                        <option value="pack">pack</option>
                        <option value="bottle">bottle</option>
                        <option value="can">can</option>
                      </select>
                      <span v-else class="text-secondary">{{ item.unit || 'pcs' }}</span>
                    </td>
                    <td>
                      <div v-if="isEditMode" class="input-group input-group-sm" style="width: 120px;">
                        <span class="input-group-text">₱</span>
                        <input 
                          type="number" 
                          class="form-control"
                          v-model.number="item.unitPrice"
                          min="0"
                          step="0.01"
                          @input="calculateItemTotal(item)"
                        >
                      </div>
                      <span v-else>₱{{ formatCurrency(item.unitPrice) }}</span>
                    </td>
                    <td>
                      <span class="fw-bold text-status-success">₱{{ formatCurrency(item.totalPrice) }}</span>
                    </td>
                    <td v-if="!isEditMode">
                      <small class="text-secondary">{{ item.notes || '-' }}</small>
                    </td>
                    <td v-if="isEditMode">
                      <div class="d-flex gap-1">
                        <input 
                          type="text" 
                          class="form-control form-control-sm"
                          v-model="item.notes"
                          placeholder="Notes"
                          style="width: 100px;"
                        >
                        <button 
                          type="button" 
                          class="btn btn-delete btn-sm"
                          @click="removeItem(index)"
                          :disabled="orderItems.length <= 1"
                          title="Remove Item"
                        >
                          <Trash2 :size="12" />
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
                <tfoot v-if="orderItems.length > 1">
                  <tr class="table-light">
                    <td colspan="2" class="fw-bold">Total</td>
                    <td class="fw-bold">{{ displayTotalQuantity }}</td>
                    <td></td>
                    <td></td>
                    <td class="fw-bold text-status-success">₱{{ formatCurrency(displayTotalAmount) }}</td>
                    <td v-if="!isEditMode"></td>
                    <td v-if="isEditMode"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          <!-- Show message if no items -->
          <div v-else class="info-card mb-4">
            <h6 class="info-card-title">
              <List :size="16" class="me-2" />
              Order Items
            </h6>
            <div class="text-center py-4 text-secondary">
              <Package :size="48" class="mb-2 opacity-50" />
              <p class="mb-0">
                {{ loadingBatches ? 'Loading items...' : 'No items found for this order' }}
              </p>
            </div>
          </div>

          <!-- Order Description -->
          <div class="info-card mb-4">
            <h6 class="info-card-title">
              <Package :size="16" class="me-2" />
              Order Description
            </h6>
            <div v-if="!isEditMode" class="description-content">
              {{ order.description || 'No description provided' }}
            </div>
            <textarea 
              v-else
              class="form-control"
              v-model="editForm.description"
              rows="3"
              placeholder="Enter order description..."
            ></textarea>
          </div>

          <!-- Order Notes -->
          <div class="info-card mb-4">
            <h6 class="info-card-title">
              <MessageSquare :size="16" class="me-2" />
              Order Notes
            </h6>
            <div v-if="!isEditMode" class="notes-content">
              {{ order.notes || 'No notes available' }}
            </div>
            <textarea 
              v-else
              class="form-control"
              v-model="editForm.notes"
              rows="3"
              placeholder="Add notes about this order..."
            ></textarea>
          </div>

          <!-- Order Timeline/History -->
          <div v-if="orderHistory && orderHistory.length > 0" class="info-card">
            <h6 class="info-card-title">
              <Clock :size="16" class="me-2" />
              Order History
            </h6>
            <div class="timeline">
              <div v-for="event in orderHistory" :key="event.id" class="timeline-item">
                <div class="timeline-marker" :class="getEventMarkerClass(event.type)">
                  <component :is="getEventIcon(event.type)" :size="12" />
                </div>
                <div class="timeline-content">
                  <div class="timeline-header">
                    <strong>{{ event.title }}</strong>
                    <small class="text-secondary ms-auto">{{ formatTimeAgo(event.date) }}</small>
                  </div>
                  <p class="mb-1 text-secondary">{{ event.description }}</p>
                  <small class="text-secondary">by {{ event.user }}</small>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer border-0 pt-4">
          <div class="d-flex justify-content-between w-100">
            <div>
              <button 
                v-if="!isEditMode" 
                type="button" 
                class="btn btn-export"
                @click="printOrder"
              >
                <Printer :size="16" class="me-1" />
                Print
              </button>
            </div>
            <div class="d-flex gap-2">
              <button type="button" class="btn btn-cancel" @click="handleCancel">
                {{ isEditMode ? 'Cancel' : 'Close' }}
              </button>
              <button 
                v-if="isEditMode" 
                type="button" 
                class="btn btn-save"
                @click="saveOrder"
                :disabled="saving || !isFormValid"
              >
                <div v-if="saving" class="spinner-border spinner-border-sm me-2"></div>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  Eye, Edit, FileText, DollarSign, Package, List,
  MessageSquare, Clock, Plus, Trash2, Printer,
  AlertTriangle, CheckCircle, XCircle, Activity
} from 'lucide-vue-next'
import { useShipments } from '@/composables/api/useShipments'
import { useToast } from '@/composables/ui/useToast'

const props = defineProps({
  show:        { type: Boolean, default: false },
  order:       { type: Object,  required: true },
  canEdit:     { type: Boolean, default: true },
  initialMode: { type: String,  default: 'view', validator: v => ['view', 'edit'].includes(v) }
})

const emit = defineEmits(['close', 'save', 'edit-mode-changed'])

const { fetchShipmentWithBatches, updateShipment } = useShipments()
const { success: showSuccess, error: showError } = useToast()

// ── State ─────────────────────────────────────────────────────────────────────
const isEditMode  = ref(false)
const saving      = ref(false)
const loadingBatches = ref(false)
const orderItems  = ref([])
const orderHistory = ref([])
const itemsReady  = ref(false)

const editForm = ref({
  expectedDate: '',
  status:       '',
  notes:        '',
  shippingCost: 0
})

// ── Status mapping (frontend label ↔ backend value) ───────────────────────────
const STATUS_TO_BACKEND = {
  'Pending Delivery': 'pending',
  'Received':        'received',
  'Cancelled':       'cancelled'
}
const STATUS_FROM_BACKEND = Object.fromEntries(
  Object.entries(STATUS_TO_BACKEND).map(([k, v]) => [v, k])
)

// ── Computed ──────────────────────────────────────────────────────────────────
const displayItemCount    = computed(() => orderItems.value.length)
const displayTotalQuantity = computed(() =>
  orderItems.value.reduce((s, i) => s + (Number(i.quantity) || 0), 0)
)
const displayTotalAmount = computed(() =>
  orderItems.value.reduce((s, i) => s + (Number(i.totalPrice) || 0), 0)
)
const isFormValid = computed(() => !!editForm.value.expectedDate && !!editForm.value.status)

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDate(d) {
  if (!d) return 'N/A'
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatTimeAgo(d) {
  if (!d) return ''
  const diff = Math.abs(Date.now() - new Date(d))
  const days  = Math.floor(diff / 86400000)
  const hours = Math.floor(diff / 3600000)
  if (days  > 0) return `${days} day${days  > 1 ? 's' : ''} ago`
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`
  return 'Just now'
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount || 0)
}

function isOverdue(order) {
  return new Date(order.expectedDate) < new Date() &&
    ['Pending Delivery', 'Partially Received'].includes(order.status)
}

function getTimeRemaining(dateString) {
  if (!dateString) return ''
  const diff  = new Date(dateString) - new Date()
  const days  = Math.ceil(diff / 86400000)
  if (days < 0)  return `${Math.abs(days)} days overdue`
  if (days === 0) return 'Due today'
  if (days === 1) return 'Due tomorrow'
  return `${days} days remaining`
}

function getOrderStatusClass(status) {
  return { 'Received': 'status-success', 'Pending Delivery': 'status-warning',
           'Cancelled': 'status-error',   'Partially Received': 'status-info' }[status] ?? ''
}

function getEventIcon(type) {
  return { created: Plus, updated: Edit, cancelled: XCircle, received: CheckCircle }[type] || Activity
}

function getEventMarkerClass(type) {
  return { created: 'marker-info', updated: 'marker-info',
           cancelled: 'marker-error', received: 'marker-success' }[type] || 'marker-default'
}

// ── Load batches from API when modal opens ────────────────────────────────────
async function loadBatches() {
  if (!props.order?.id) return
  loadingBatches.value = true
  itemsReady.value = false
  try {
    const shipment = await fetchShipmentWithBatches(props.order.id, true)
    const batches  = shipment?.batches || []
    orderItems.value = batches.map(b => ({
      name:       b.product_name || 'Unknown Product',
      quantity:   Number(b.quantity_received) || 0,
      unit:       'pcs',
      unitPrice:  Number(b.cost_price)  || 0,
      totalPrice: (Number(b.cost_price) || 0) * (Number(b.quantity_received) || 0),
      notes:      '',
      productId:  b.product_id,
      batchId:    b.batch_id,
      expiryDate: b.expiry_date,
      status:     b.status
    }))
    orderHistory.value = props.order.orderHistory || []
  } catch {
    orderItems.value  = []
    orderHistory.value = props.order.orderHistory || []
  } finally {
    loadingBatches.value = false
    itemsReady.value     = true
  }
}

function resetEditForm() {
  editForm.value = {
    expectedDate: props.order.expectedDate || '',
    status:       props.order.status || 'Pending Delivery',
    notes:        props.order.notes  || '',
    shippingCost: props.order.shippingCost || 0
  }
}

function initializeModal() {
  isEditMode.value = props.initialMode === 'edit'
  resetEditForm()
  loadBatches()
  emit('edit-mode-changed', isEditMode.value)
}

// ── Watch show prop ───────────────────────────────────────────────────────────
watch(() => props.show, newVal => { if (newVal) initializeModal() }, { immediate: true })

// ── Actions ───────────────────────────────────────────────────────────────────
function toggleEditMode() {
  isEditMode.value = !isEditMode.value
  if (isEditMode.value) resetEditForm()
  emit('edit-mode-changed', isEditMode.value)
}

function handleCancel() {
  if (isEditMode.value) {
    isEditMode.value = false
    resetEditForm()
  } else {
    closeModal()
  }
}

function closeModal() {
  isEditMode.value = false
  emit('close')
}

function handleOverlayClick(event) {
  if (event.target === event.currentTarget && !saving.value) closeModal()
}

async function saveOrder() {
  saving.value = true
  try {
    const backendStatus = STATUS_TO_BACKEND[editForm.value.status] || editForm.value.status

    await updateShipment(props.order.id, {
      expected_delivery_date: editForm.value.expectedDate || null,
      status:      backendStatus,
      notes:       editForm.value.notes || null,
      freight_cost: editForm.value.shippingCost || null
    })

    showSuccess('Order updated successfully')

    emit('save', {
      ...props.order,
      expectedDate: editForm.value.expectedDate,
      status:       editForm.value.status,
      notes:        editForm.value.notes,
      shippingCost: editForm.value.shippingCost
    })

    isEditMode.value = false
  } catch (err) {
    showError(err.message || 'Failed to save order')
  } finally {
    saving.value = false
  }
}

function printOrder() { window.print() }
</script>

<style scoped>
@import '@/assets/styles/colors.css';

.modern-modal {
  border-radius: 16px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
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

.order-details-modal {
  width: min(1100px, 95vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 10000 !important;
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2rem 2rem 1rem 2rem;
  border-bottom: 1px solid var(--border-primary);
  background-color: var(--surface-tertiary);
  flex-shrink: 0;
}

.modal-body {
  padding: 1.5rem 2rem 2rem 2rem;
  overflow-y: auto;
  background-color: var(--surface-elevated);
  flex: 1;
  max-height: calc(90vh - 220px);
}

.modal-footer {
  padding: 1.5rem 2rem 2rem 2rem;
  background-color: var(--surface-tertiary);
  border-top: 1px solid var(--border-primary);
  flex-shrink: 0;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-header .d-flex.align-items-center.flex-grow-1 {
  min-width: 0;
}

.modal-header .d-flex.align-items-center.gap-2 {
  flex-shrink: 0;
  margin-left: auto;
}

.modal-header .btn {
  white-space: nowrap;
}

.modal-header .btn-close {
  padding: 0.5rem;
  margin-left: 0.5rem;
}

.info-card {
  background: var(--surface-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.info-card:last-child {
  margin-bottom: 0;
}

.info-card-title {
  color: var(--text-primary);
  font-weight: 600;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--border-primary);
  padding-bottom: 0.5rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-primary);
}

.info-item:last-child {
  margin-bottom: 0;
  border-bottom: none;
  padding-bottom: 0;
}

.info-item label {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-bottom: 0;
  flex-shrink: 0;
  width: 120px;
}

.info-item span, .info-item div {
  color: var(--text-primary);
  font-weight: 500;
  text-align: right;
  flex-grow: 1;
}

.order-id-text {
  font-family: 'Monaco', 'Menlo', monospace;
  color: var(--text-accent) !important;
  font-weight: 600;
}

.amount-text {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--status-success) !important;
}

.description-content, .notes-content {
  background: var(--surface-primary);
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  min-height: 60px;
  color: var(--text-primary);
  line-height: 1.6;
}

.items-table {
  background: var(--surface-primary);
  border-radius: 8px;
  overflow: hidden;
  font-size: 0.875rem;
}

.items-table th {
  background: var(--surface-tertiary);
  color: var(--text-primary);
  font-weight: 600;
  border: none;
  padding: 0.75rem 0.5rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.items-table td {
  padding: 0.75rem 0.5rem;
  border-top: 1px solid var(--border-primary);
  vertical-align: middle;
}

.items-table tbody tr:hover {
  background-color: var(--state-hover);
}

.items-table tfoot tr {
  border-top: 2px solid var(--border-accent);
}

.items-table tfoot td {
  font-weight: 600;
  background-color: var(--surface-secondary);
}

/* Form controls in table */
.items-table .form-control-sm,
.items-table .form-select-sm {
  font-size: 0.75rem;
}

.items-table .input-group-sm .input-group-text {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
}

.timeline {
  position: relative;
}

.timeline-item {
  display: flex;
  margin-bottom: 1.5rem;
  position: relative;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 30px;
  bottom: -24px;
  width: 2px;
  background-color: var(--border-primary);
}

.timeline-marker {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 1rem;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.timeline-content {
  flex-grow: 1;
}

.timeline-header {
  display: flex;
  justify-content: between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.order-status {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

/* Semantic timeline marker colors */
.timeline-marker.marker-info {
  background-color: var(--status-info);
}
.timeline-marker.marker-success {
  background-color: var(--status-success);
}
.timeline-marker.marker-error {
  background-color: var(--status-error);
}
.timeline-marker.marker-default {
  background-color: var(--border-primary);
}

/* Form controls in edit mode */
.form-control:focus,
.form-select:focus {
  border-color: var(--border-accent);
  box-shadow: 0 0 0 0.2rem var(--state-hover);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .info-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .info-item label {
    width: auto;
    margin-bottom: 0.25rem;
  }
  
  .info-item span, .info-item div {
    text-align: left;
  }
}
</style>