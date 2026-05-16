<template>
  <Teleport to="body">
    <div v-if="isVisible" class="modal-overlay modal-overlay-theme" @click="handleOverlayClick">
      <div class="modal-content modal-theme" @click.stop>
        <div class="modal-header border-bottom-theme">
          <h2 class="text-primary">Update Stock</h2>
          <button class="btn-close" @click="closeModal" :disabled="isLoading" aria-label="Close">
            <X :size="20" />
          </button>
        </div>

        <!-- Product Info Banner -->
        <div v-if="product" class="product-info surface-secondary border-bottom-theme">
          <div class="product-details">
            <div class="product-name fw-semibold text-primary">{{ product.product_name }}</div>
            <div class="d-flex gap-3">
              <span class="text-tertiary-medium">SKU: {{ product.sku || product.SKU }}</span>
              <span class="text-tertiary-medium">{{ getCategoryName(product.category_id) }}</span>
            </div>
          </div>
          <div class="current-stock text-end">
            <div class="stock-label text-uppercase text-tertiary-medium">Current Stock</div>
            <div class="stock-value fw-bold" :class="getStockClass(product)">
              {{ getCurrentStock(product) }} {{ product.unit }}
            </div>
            <small class="text-tertiary-medium">Min: {{ product.low_stock_threshold }}</small>
          </div>
        </div>

        <form @submit.prevent="handleSubmit" class="stock-form">
          <!-- Operation Selector -->
          <div class="mb-3">
            <label for="operation_type" class="form-label text-primary fw-medium">
              Operation <span class="text-error">*</span>
            </label>
            <select
              id="operation_type"
              v-model="form.operation_type"
              required
              :disabled="isLoading"
              class="form-select input-theme"
              @change="onOperationChange"
            >
              <option value="new_batch">New Purchase / Add Stock</option>
              <option value="adjust">Adjust Existing Stock</option>
            </select>
            <small class="text-tertiary-medium">{{ operationDescription }}</small>
          </div>

          <!-- ===== NEW BATCH SECTION ===== -->
          <div v-if="form.operation_type === 'new_batch'" class="surface-elevated p-3 rounded border-theme-subtle mb-4">
            <h5 class="text-primary mb-3 d-flex align-items-center gap-2">
              <Package :size="18" />
              New Batch Details
            </h5>

            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <label for="batch_number" class="form-label text-primary fw-medium">Batch Number</label>
                <input
                  id="batch_number"
                  v-model="form.batch_number"
                  type="text"
                  :disabled="isLoading"
                  placeholder="Auto-generated if left blank"
                  class="form-control input-theme"
                />
                <small class="text-tertiary-medium">Leave blank to auto-generate</small>
              </div>

              <div class="col-md-6">
                <label for="date_received" class="form-label text-primary fw-medium">Date Received</label>
                <input
                  id="date_received"
                  v-model="form.date_received"
                  type="date"
                  :disabled="isLoading"
                  :max="today"
                  class="form-control input-theme"
                />
                <small class="text-tertiary-medium">Defaults to today if empty</small>
              </div>
            </div>

            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <label for="quantity_received" class="form-label text-primary fw-medium">
                  Quantity Received <span class="text-error">*</span>
                </label>
                <input
                  id="quantity_received"
                  v-model.number="form.quantity_received"
                  type="number"
                  min="1"
                  required
                  :disabled="isLoading"
                  placeholder="0"
                  class="form-control input-theme"
                  @input="calculateNewStock"
                />
              </div>

              <div class="col-md-6">
                <label for="cost_price" class="form-label text-primary fw-medium">
                  Cost Price per Unit (₱) <span class="text-error">*</span>
                </label>
                <input
                  id="cost_price"
                  v-model.number="form.cost_price"
                  type="number"
                  min="0"
                  step="0.01"
                  required
                  :disabled="isLoading"
                  placeholder="0.00"
                  class="form-control input-theme"
                />
              </div>
            </div>

            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <label for="expiry_date" class="form-label text-primary fw-medium">Expiry Date</label>
                <input
                  id="expiry_date"
                  v-model="form.expiry_date"
                  type="date"
                  :disabled="isLoading"
                  :min="tomorrow"
                  class="form-control input-theme"
                />
                <small class="text-tertiary-medium">Optional — leave blank if unknown</small>
              </div>

              <div class="col-md-6">
                <label for="supplier_select" class="form-label text-primary fw-medium">Supplier</label>
                <select
                  id="supplier_select"
                  v-model="form.supplierMode"
                  :disabled="isLoading"
                  class="form-select input-theme"
                  @change="onSupplierModeChange"
                >
                  <option value="">No supplier</option>
                  <option
                    v-for="s in suppliers"
                    :key="s.supplier_id"
                    :value="s.supplier_id"
                  >
                    {{ s.supplier_name || s.name }}
                  </option>
                  <option value="__other__">Other (not in system)</option>
                </select>
              </div>
            </div>

            <!-- Custom supplier name -->
            <div v-if="form.supplierMode === '__other__'" class="mb-3">
              <label for="supplier_custom" class="form-label text-primary fw-medium">Supplier Name</label>
              <input
                id="supplier_custom"
                v-model="form.supplierCustomName"
                type="text"
                :disabled="isLoading"
                placeholder="Enter supplier name"
                class="form-control input-theme"
              />
              <small class="text-tertiary-medium">Recorded in batch notes</small>
            </div>

            <!-- Stock preview -->
            <div class="info-callout d-flex align-items-start gap-2">
              <Info :size="16" class="mt-1 flex-shrink-0" />
              <div>
                <strong>New Batch:</strong> Adds {{ form.quantity_received || 0 }} units.
                Stock after: <strong class="text-success">{{ newStockPreview }} {{ product?.unit }}</strong>
              </div>
            </div>
          </div>

          <!-- ===== ADJUST SECTION ===== -->
          <div v-else class="surface-elevated p-3 rounded border-theme-subtle mb-4">
            <h5 class="text-primary mb-3 d-flex align-items-center gap-2">
              <SlidersHorizontal :size="18" />
              Stock Adjustment
            </h5>

            <div class="mb-3">
              <label for="adjustment_type" class="form-label text-primary fw-medium">
                Reason <span class="text-error">*</span>
              </label>
              <select
                id="adjustment_type"
                v-model="form.adjustment_type"
                required
                :disabled="isLoading"
                class="form-select input-theme"
              >
                <option value="">Select reason</option>
                <option value="damage">Damage</option>
                <option value="theft">Theft / Loss</option>
                <option value="spoilage">Spoilage / Expiry</option>
                <option value="return">Return (add back to stock)</option>
                <option value="shrinkage">Shrinkage</option>
                <option value="correction">Correction</option>
              </select>
            </div>

            <!-- Batch selector -->
            <div class="mb-3">
              <label for="batch_select" class="form-label text-primary fw-medium">Target Batch</label>
              <select
                id="batch_select"
                v-model="form.selectedBatchId"
                :disabled="isLoading || loadingBatches"
                class="form-select input-theme"
              >
                <option value="">
                  {{ loadingBatches ? 'Loading batches...' : 'Auto — FEFO (recommended)' }}
                </option>
                <option
                  v-for="batch in productActiveBatches"
                  :key="batch.batch_id"
                  :value="batch.batch_id"
                >
                  {{ batch.batch_id }} — {{ batch.quantity_remaining }} {{ product?.unit }}{{ batch.expiry_date ? ' · Exp: ' + formatExpiry(batch.expiry_date) : '' }}
                </option>
              </select>
              <small class="text-tertiary-medium">
                {{ form.selectedBatchId
                  ? 'Adjusting this specific batch directly'
                  : 'FEFO automatically targets the soonest-expiring batch first' }}
              </small>
            </div>

            <div class="mb-3">
              <label for="quantity_used" class="form-label text-primary fw-medium">
                Quantity <span class="text-error">*</span>
              </label>
              <input
                id="quantity_used"
                v-model.number="form.quantity_used"
                type="number"
                min="1"
                :max="adjustMaxQty"
                required
                :disabled="isLoading"
                placeholder="0"
                class="form-control input-theme"
                @input="calculateNewStock"
              />
              <div v-if="newStockPreview !== null" class="mt-2 p-2 surface-secondary rounded">
                <small class="text-tertiary-medium">
                  Stock after adjustment:
                  <span :class="getPreviewStockClass(newStockPreview)" class="fw-semibold">
                    {{ newStockPreview }} {{ product?.unit }}
                  </span>
                </small>
              </div>
            </div>

            <div class="mb-3">
              <label for="notes" class="form-label text-primary fw-medium">Notes</label>
              <textarea
                id="notes"
                v-model="form.notes"
                rows="2"
                :disabled="isLoading"
                placeholder="Optional: add context for this adjustment"
                class="form-control input-theme"
              />
            </div>

            <div v-if="form.adjustment_type" class="warning-callout d-flex align-items-start gap-2">
              <AlertTriangle :size="16" class="mt-1 flex-shrink-0" />
              <div>
                This will {{ form.adjustment_type === 'return' ? 'add' : 'remove' }}
                <strong>{{ form.quantity_used || 0 }} {{ product?.unit }}</strong>
                {{ form.adjustment_type === 'return' ? 'back to' : 'from' }} stock.
                This action is logged in batch history.
              </div>
            </div>
          </div>

          <!-- Error -->
          <div v-if="error" class="status-error mb-3" role="alert">
            <strong>Error:</strong> {{ error }}
          </div>

          <div class="d-flex gap-2 justify-content-end pt-3 divider-theme">
            <button type="button" @click="closeModal" :disabled="isLoading" class="btn btn-cancel">
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isLoading || !isFormValid"
              class="btn btn-with-icon-sm"
              :class="submitButtonClass"
            >
              <span v-if="isLoading" class="spinner-border spinner-border-sm me-2" role="status">
                <span class="visually-hidden">Loading...</span>
              </span>
              <Save :size="16" />
              {{ isLoading ? 'Processing...' : submitButtonText }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { X, Package, Save, Info, AlertTriangle, SlidersHorizontal } from 'lucide-vue-next'
import { useModal } from '@/composables/ui/useModal'
import { useBatches } from '@/composables/api/useBatches'
import { useCategories } from '@/composables/api/useCategories'
import { useToast } from '@/composables/ui/useToast'
import { useAuth } from '@/composables/auth/useAuth'
import apiProductsService from '@/services/apiProducts'

const emit = defineEmits(['success'])

const { isVisible, isLoading, error, show, hide, setLoading, setError, clearError } = useModal()
const { fetchBatchesByProduct, createBatch, processBatchAdjustment, updateBatchQuantity } = useBatches()
const { activeCategories } = useCategories()
const { success: showSuccess } = useToast()
const { user } = useAuth()

const product = ref(null)
const suppliers = ref([])
const productActiveBatches = ref([])
const loadingBatches = ref(false)
const newStockPreview = ref(null)

const today = computed(() => new Date().toISOString().split('T')[0])
const tomorrow = computed(() => {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return d.toISOString().split('T')[0]
})

const form = ref({
  operation_type: 'new_batch',
  batch_number: '',
  date_received: '',
  quantity_received: null,
  cost_price: null,
  expiry_date: '',
  supplierMode: '',
  supplierCustomName: '',
  adjustment_type: '',
  selectedBatchId: '',
  quantity_used: null,
  notes: ''
})

const operationDescription = computed(() =>
  form.value.operation_type === 'new_batch'
    ? 'Add new stock from a purchase or delivery'
    : 'Record a loss, damage, return, or correction against existing stock'
)

const isFormValid = computed(() => {
  if (form.value.operation_type === 'new_batch') {
    return form.value.quantity_received > 0 && form.value.cost_price >= 0
  }
  return !!form.value.adjustment_type && form.value.quantity_used > 0
})

const adjustMaxQty = computed(() => {
  if (form.value.selectedBatchId) {
    const batch = productActiveBatches.value.find(b => b.batch_id === form.value.selectedBatchId)
    return batch?.quantity_remaining ?? getCurrentStock(product.value)
  }
  return getCurrentStock(product.value)
})

const submitButtonClass = computed(() =>
  form.value.operation_type === 'adjust' && form.value.adjustment_type !== 'return'
    ? 'btn-delete'
    : 'btn-save'
)

const submitButtonText = computed(() =>
  form.value.operation_type === 'new_batch' ? 'Create Batch' : 'Adjust Stock'
)

const getCurrentStock = (p) => p?.total_stock ?? p?.stock ?? 0

const getCategoryName = (categoryId) => {
  if (!categoryId) return 'Uncategorized'
  return activeCategories.value.find(c => c.category_id === categoryId)?.category_name || 'Unknown'
}

const getStockClass = (p) => {
  const s = getCurrentStock(p)
  if (s === 0) return 'text-error'
  if (s <= (p?.low_stock_threshold || 15)) return 'text-warning'
  return 'text-success'
}

const getPreviewStockClass = (n) => {
  if (n <= 0) return 'text-error'
  if (n <= (product.value?.low_stock_threshold || 15)) return 'text-warning'
  return 'text-success'
}

const formatExpiry = (dateStr) => {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}

const calculateNewStock = () => {
  if (!product.value) return
  const current = getCurrentStock(product.value)
  if (form.value.operation_type === 'new_batch') {
    newStockPreview.value = current + (form.value.quantity_received || 0)
  } else {
    const qty = form.value.quantity_used || 0
    newStockPreview.value = form.value.adjustment_type === 'return'
      ? current + qty
      : Math.max(0, current - qty)
  }
}

const onOperationChange = () => {
  form.value.batch_number = ''
  form.value.date_received = ''
  form.value.quantity_received = null
  form.value.cost_price = null
  form.value.expiry_date = ''
  form.value.supplierMode = ''
  form.value.supplierCustomName = ''
  form.value.adjustment_type = ''
  form.value.selectedBatchId = ''
  form.value.quantity_used = null
  form.value.notes = ''
  newStockPreview.value = null
}

const onSupplierModeChange = () => {
  if (form.value.supplierMode !== '__other__') {
    form.value.supplierCustomName = ''
  }
}

const loadSuppliers = async () => {
  try {
    const res = await apiProductsService.getAllSuppliers()
    suppliers.value = Array.isArray(res.suppliers) ? res.suppliers
      : Array.isArray(res.data?.suppliers) ? res.data.suppliers : []
  } catch {
    suppliers.value = []
  }
}

const loadProductBatches = async (productId) => {
  loadingBatches.value = true
  try {
    const all = await fetchBatchesByProduct(productId)
    productActiveBatches.value = (all || []).filter(
      b => ['active', 'low_stock', 'expiring_soon'].includes(b.status)
    )
  } catch {
    productActiveBatches.value = []
  } finally {
    loadingBatches.value = false
  }
}

const resetForm = () => {
  form.value = {
    operation_type: 'new_batch',
    batch_number: '',
    date_received: '',
    quantity_received: null,
    cost_price: null,
    expiry_date: '',
    supplierMode: '',
    supplierCustomName: '',
    adjustment_type: '',
    selectedBatchId: '',
    quantity_used: null,
    notes: ''
  }
  newStockPreview.value = null
  productActiveBatches.value = []
  clearError()
}

const handleSubmit = async () => {
  setLoading(true)
  clearError()
  try {
    let result

    const rawId = product.value.product_id || ''
    const fullProductId = rawId.toUpperCase().startsWith('PROD-') ? rawId : `PROD-${rawId}`

    if (form.value.operation_type === 'new_batch') {
      const supplierId = form.value.supplierMode && form.value.supplierMode !== '__other__'
        ? form.value.supplierMode : null

      // If a custom supplier name was entered, append it to the batch_number
      // so it's visible in the batch record (Batch model has no dedicated notes field)
      let batchNumber = form.value.batch_number || undefined
      if (form.value.supplierMode === '__other__' && form.value.supplierCustomName.trim()) {
        const suffix = `(${form.value.supplierCustomName.trim()})`
        batchNumber = batchNumber ? `${batchNumber} ${suffix}` : suffix
      }

      result = await createBatch({
        product_id: fullProductId,
        batch_number: batchNumber,
        quantity_received: form.value.quantity_received,
        cost_price: form.value.cost_price,
        expiry_date: form.value.expiry_date || undefined,
        supplier_id: supplierId,
        date_received: form.value.date_received || undefined,
        status: 'active',
      })

      showSuccess(`Batch created: ${form.value.quantity_received} units added`)
    } else {
      if (form.value.selectedBatchId) {
        result = await updateBatchQuantity(
          form.value.selectedBatchId,
          form.value.quantity_used,
          form.value.adjustment_type,
          user.value?.user_id,
          form.value.notes || undefined
        )
      } else {
        result = await processBatchAdjustment(
          fullProductId,
          form.value.quantity_used,
          form.value.adjustment_type,
          user.value?.user_id,
          form.value.notes || undefined
        )
      }
      showSuccess(`Stock adjusted: ${form.value.quantity_used} units (${form.value.adjustment_type})`)
    }

    setLoading(false)
    emit('success', { message: 'Stock updated successfully', product: result, operation: form.value })
    closeModal()
  } catch (err) {
    setError(err.message || 'Failed to update stock')
    setLoading(false)
  }
}

const closeModal = () => {
  if (!isLoading.value) {
    hide()
    product.value = null
    resetForm()
  }
}

const handleOverlayClick = () => {
  if (!isLoading.value) closeModal()
}

const handleKeydown = (e) => {
  if (e.key === 'Escape' && isVisible.value && !isLoading.value) closeModal()
}

onMounted(() => {
  loadSuppliers()
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

defineExpose({
  openStock: (productData) => {
    product.value = { ...productData }
    resetForm()
    const id = productData.product_id || ''
    loadProductBatches(id.toUpperCase().startsWith('PROD-') ? id : `PROD-${id}`)
    show()
  }
})
</script>

<style scoped>
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

.modal-content {
  position: relative !important;
  max-width: 600px;
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

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem 1rem 2rem;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
  padding: 0.25rem;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover:not(:disabled) {
  background-color: var(--state-hover);
  color: var(--text-primary);
}

.btn-close:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.product-info {
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-name {
  font-size: 1.05rem;
  margin-bottom: 0.25rem;
}

.stock-label {
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.stock-value {
  font-size: 1.4rem;
  margin-bottom: 0.125rem;
}

.stock-form {
  padding: 1.5rem 2rem 2rem 2rem;
}

.info-callout {
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-secondary);
  border-left: 3px solid var(--text-accent);
  border-radius: 0.375rem;
  padding: 0.75rem 1rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.warning-callout {
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-secondary);
  border-left: 3px solid var(--status-warning, #f59e0b);
  border-radius: 0.375rem;
  padding: 0.75rem 1rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.divider-theme {
  border-top: 1px solid var(--border-secondary) !important;
  margin: 0;
  padding-top: 1rem;
}

@media (max-width: 768px) {
  .modal-content {
    margin: 1rem;
    max-height: calc(100vh - 2rem);
  }

  .modal-header {
    padding: 1rem 1.5rem 0.75rem 1.5rem;
  }

  .product-info {
    padding: 0.75rem 1.5rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .current-stock {
    text-align: left;
    width: 100%;
  }

  .stock-form {
    padding: 1rem 1.5rem 1.5rem 1.5rem;
  }
}

@media (max-width: 480px) {
  .modal-content {
    margin: 0.5rem;
    max-height: calc(100vh - 1rem);
    border-radius: 8px;
  }

  .modal-header {
    padding: 0.75rem 1rem 0.5rem 1rem;
  }

  .product-info {
    padding: 0.75rem 1rem;
  }

  .stock-form {
    padding: 0.75rem 1rem 1rem 1rem;
  }
}

.modal-content::-webkit-scrollbar {
  width: 6px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--surface-tertiary);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--border-accent);
}

body:has(.modal-overlay) {
  overflow: hidden !important;
}
</style>
