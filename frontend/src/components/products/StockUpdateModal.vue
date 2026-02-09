<template>
  <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2 class="text-tertiary-dark">Update Stock</h2>
        <button class="btn-close" @click="closeModal" :disabled="loading" aria-label="Close">
          ✕
        </button>
      </div>

      <div v-if="product" class="product-info bg-light border-bottom">
        <div class="product-details">
          <div class="product-name fw-semibold text-tertiary-dark">{{ product.product_name }}</div>
          <div class="product-meta d-flex gap-3">
            <span class="text-tertiary-medium">SKU: {{ product.SKU }}</span>
            <span class="text-tertiary-medium">{{ getCategoryName(product.category_id) }}</span>
          </div>
        </div>
        <div class="current-stock text-end">
          <div class="stock-label text-uppercase text-tertiary-medium">Current Stock</div>
          <div class="stock-value" :class="getStockClass(product)">
            {{ getCurrentStock(product) }} {{ product.unit }}
          </div>
          <div class="stock-threshold text-tertiary-medium">Min: {{ product.low_stock_threshold }}</div>
        </div>
      </div>
      
      <form @submit.prevent="handleSubmit" class="stock-form">
        <div class="mb-3">
          <label for="operation_type" class="form-label text-tertiary-dark fw-medium">
            Operation <span class="text-danger">*</span>
          </label>
          <select 
            id="operation_type" 
            v-model="form.operation_type" 
            required
            :disabled="loading"
            class="form-select"
            @change="onOperationChange"
          >
            <option value="new_batch">New Purchase/Batch</option>
            <option value="adjust">Adjust Existing Stock</option>
          </select>
          <div class="form-text text-tertiary-medium">
            {{ operationDescription }}
          </div>
        </div>

        <!-- NEW BATCH SECTION -->
        <div v-if="form.operation_type === 'new_batch'" class="batch-section mb-4 p-3 border rounded bg-light">
          <h6 class="text-tertiary-dark mb-3">New Batch Information</h6>
          
          <div class="row">
            <div class="col-md-6 mb-3">
              <label for="batch_number" class="form-label text-tertiary-dark fw-medium">
                Batch Number
              </label>
              <input 
                id="batch_number"
                v-model="form.batch_number" 
                type="text" 
                :disabled="loading"
                placeholder="Auto-generated if left blank"
                class="form-control"
              />
              <div class="form-text text-tertiary-medium">
                Leave blank to auto-generate
              </div>
            </div>
            
            <div class="col-md-6 mb-3">
              <label for="supplier_id" class="form-label text-tertiary-dark fw-medium">
                Supplier ID
              </label>
              <input 
                id="supplier_id"
                v-model="form.supplier_id" 
                type="text" 
                :disabled="loading"
                placeholder="Supplier ID (optional)"
                class="form-control"
              />
            </div>
          </div>
          
          <div class="row">
            <div class="col-md-6 mb-3">
              <label for="quantity_received" class="form-label text-tertiary-dark fw-medium">
                Quantity Received <span class="text-danger">*</span>
              </label>
              <input 
                id="quantity_received"
                v-model.number="form.quantity_received" 
                type="number" 
                min="1"
                required 
                :disabled="loading"
                placeholder="Enter quantity"
                class="form-control"
                @input="calculateNewStock"
              />
            </div>
            
            <div class="col-md-6 mb-3">
              <label for="cost_price" class="form-label text-tertiary-dark fw-medium">
                Cost Price <span class="text-danger">*</span>
              </label>
              <div class="input-group">
                <span class="input-group-text">₱</span>
                <input 
                  id="cost_price"
                  v-model.number="form.cost_price" 
                  type="number" 
                  min="0"
                  step="0.01"
                  required 
                  :disabled="loading"
                  placeholder="0.00"
                  class="form-control"
                />
              </div>
            </div>
          </div>
          
          <div class="mb-3">
            <label for="expiry_date" class="form-label text-tertiary-dark fw-medium">
              Expiry Date <span class="text-danger">*</span>
            </label>
            <input 
              id="expiry_date"
              v-model="form.expiry_date" 
              type="date" 
              required
              :disabled="loading"
              class="form-control"
              :min="today"
            />
          </div>
          
          <div class="alert alert-info d-flex align-items-start mb-0">
            <span class="me-2">ℹ️</span>
            <div>
              <strong>New Batch:</strong> This will create a new batch with {{ form.quantity_received || 0 }} units.
              <br>Total stock after: <strong>{{ newStockPreview }}</strong> {{ product?.unit }}
            </div>
          </div>
        </div>

        <!-- ADJUSTMENT SECTION -->
        <div v-else class="adjustment-section mb-4">
          <div class="mb-3">
            <label for="adjustment_type" class="form-label text-tertiary-dark fw-medium">
              Adjustment Type <span class="text-danger">*</span>
            </label>
            <select 
              id="adjustment_type" 
              v-model="form.adjustment_type" 
              required
              :disabled="loading"
              class="form-select"
            >
              <option value="">Select adjustment type</option>
              <option value="sale">Sale</option>
              <option value="damage">Damage</option>
              <option value="theft">Theft/Loss</option>
              <option value="spoilage">Spoilage/Expiry</option>
              <option value="return">Return</option>
              <option value="shrinkage">Shrinkage</option>
              <option value="correction">Correction</option>
            </select>
          </div>

          <div class="mb-3">
            <label for="quantity_used" class="form-label text-tertiary-dark fw-medium">
              Quantity to Adjust <span class="text-danger">*</span>
            </label>
            <input 
              id="quantity_used"
              v-model.number="form.quantity_used" 
              type="number" 
              :min="1"
              :max="getCurrentStock(product)"
              required 
              :disabled="loading"
              placeholder="Enter quantity"
              class="form-control"
              @input="calculateNewStock"
            />
            <div v-if="newStockPreview !== null" class="mt-2 p-2 bg-light border rounded">
              <small class="text-tertiary-medium">
                New stock will be: 
                <span :class="getPreviewStockClass(newStockPreview)" class="fw-semibold">
                  {{ newStockPreview }} {{ product?.unit }}
                </span>
              </small>
            </div>
          </div>

          <div class="mb-3">
            <label for="notes" class="form-label text-tertiary-dark fw-medium">
              Notes
            </label>
            <textarea 
              id="notes"
              v-model="form.notes" 
              rows="3"
              :disabled="loading"
              placeholder="Add detailed explanation for this adjustment..."
              class="form-control"
            />
            <div class="form-text text-tertiary-medium">
              Optional: Provide additional context for this adjustment
            </div>
          </div>

          <div v-if="form.adjustment_type" class="alert alert-warning d-flex align-items-start">
            <span class="me-2">⚠️</span>
            <div>
              <strong>Warning:</strong> This will {{ form.adjustment_type === 'return' ? 'add' : 'remove' }} 
              {{ form.quantity_used || 0 }} units {{ form.adjustment_type === 'return' ? 'to' : 'from' }} stock using FIFO method.
              <br>This action will be logged in batch usage history.
            </div>
          </div>
        </div>

        <div v-if="error" class="alert alert-danger d-flex align-items-center mb-3" role="alert">
          <span class="me-2">⚠️</span>
          {{ error }}
        </div>

        <div class="d-flex gap-2 justify-content-end pt-3 border-top">
          <button 
            type="button" 
            @click="closeModal" 
            :disabled="loading"
            class="btn btn-cancel"
          >
            Cancel
          </button>
          <button 
            type="submit" 
            :disabled="loading || !isFormValid" 
            :class="['btn', getSubmitButtonClass()]"
          >
            <span v-if="loading" class="spinner-border spinner-border-sm me-2" role="status">
              <span class="visually-hidden">Loading...</span>
            </span>
            {{ loading ? 'Processing...' : getSubmitButtonText() }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import { useBatches } from '@/composables/api/useBatches'
import { useCategories } from '@/composables/api/useCategories'
import { useToast } from '@/composables/ui/useToast'
import { useAuth } from '@/composables/auth/useAuth'
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

export default {
  name: 'StockUpdateModal',
  emits: ['success'],
  
  setup(props, { emit }) {
    // Composables - FIX: Properly destructure toast
    const { createBatch, processBatchAdjustment, error: batchError, loading: batchLoading } = useBatches()
    const { activeCategories } = useCategories()
    const { success, error: showError, info } = useToast() // ✅ Fixed: destructure methods from useToast
    const { user } = useAuth() 
    
    // State
    const show = ref(false)
    const product = ref(null)
    const newStockPreview = ref(null)
    
    // Form data
    const form = ref({
      operation_type: 'new_batch',
      // New batch fields
      batch_number: '',
      supplier_id: '',
      quantity_received: null,
      cost_price: null,
      expiry_date: '',
      // Adjustment fields
      adjustment_type: '',
      quantity_used: null,
      notes: ''
    })
    
    // Computed properties
    const loading = computed(() => batchLoading.value)
    const error = computed(() => batchError.value)
    
    const today = computed(() => {
      return new Date().toISOString().split('T')[0]
    })
    
    const isFormValid = computed(() => {
      if (form.value.operation_type === 'new_batch') {
        return form.value.quantity_received > 0 && 
               form.value.cost_price > 0 && 
               form.value.expiry_date
      } else {
        return form.value.adjustment_type && form.value.quantity_used > 0
      }
    })
    
    const operationDescription = computed(() => {
      if (form.value.operation_type === 'new_batch') {
        return 'Create a new batch from purchase order or stock receipt'
      } else {
        return 'Adjust existing stock using FIFO (First In, First Out) method'
      }
    })
    
    // Helper functions
    const getCurrentStock = (product) => {
      return product?.total_stock ?? product?.stock ?? 0
    }
    
    const getCategoryName = (categoryId) => {
      if (!categoryId) return 'Uncategorized'
      const category = activeCategories.value.find(c => c._id === categoryId)
      return category?.category_name || 'Unknown'
    }
    
    const getStockClass = (product) => {
      const stock = getCurrentStock(product)
      if (stock === 0) return 'text-danger'
      if (stock <= (product?.low_stock_threshold || 15)) return 'text-warning'
      return 'text-success'
    }
    
    const getPreviewStockClass = (newStock) => {
      if (newStock === 0) return 'text-danger'
      if (newStock <= (product.value?.low_stock_threshold || 15)) return 'text-warning'
      return 'text-success'
    }
    
    const getSubmitButtonClass = () => {
      if (form.value.operation_type === 'adjust' && 
          form.value.adjustment_type !== 'return') {
        return 'btn-delete'
      }
      return 'btn-add'
    }
    
    const getSubmitButtonText = () => {
      return form.value.operation_type === 'new_batch' ? 'Create Batch' : 'Adjust Stock'
    }
    
    const generateBatchNumber = () => {
      const now = new Date()
      const year = now.getFullYear()
      const month = String(now.getMonth() + 1).padStart(2, '0')
      const day = String(now.getDate()).padStart(2, '0')
      const timestamp = now.getTime().toString().slice(-4)
      
      return `B-${year}${month}${day}-${timestamp}`
    }
    
    const calculateNewStock = () => {
      if (!product.value) return
      
      const currentStock = getCurrentStock(product.value)
      
      if (form.value.operation_type === 'new_batch') {
        const quantity = form.value.quantity_received || 0
        newStockPreview.value = currentStock + quantity
      } else {
        const quantity = form.value.quantity_used || 0
        if (form.value.adjustment_type === 'return') {
          newStockPreview.value = currentStock + quantity
        } else {
          newStockPreview.value = Math.max(0, currentStock - quantity)
        }
      }
    }
    
    // Event handlers
    const onOperationChange = () => {
      // Reset form fields
      form.value.batch_number = ''
      form.value.supplier_id = ''
      form.value.quantity_received = null
      form.value.cost_price = null
      form.value.expiry_date = ''
      form.value.adjustment_type = ''
      form.value.quantity_used = null
      form.value.notes = ''
      newStockPreview.value = null
    }
    
    // Modal actions
    const openStockModal = (productData) => {
      product.value = productData
      show.value = true
      resetForm()
    }
    
    const closeModal = () => {
      show.value = false
      product.value = null
      resetForm()
    }
    
    const resetForm = () => {
      form.value = {
        operation_type: 'new_batch',
        batch_number: '',
        supplier_id: '',
        quantity_received: null,
        cost_price: null,
        expiry_date: '',
        adjustment_type: '',
        quantity_used: null,
        notes: ''
      }
      newStockPreview.value = null
    }
    
    const handleSubmit = async () => {
      try {
        let result
        
        if (form.value.operation_type === 'new_batch') {
          // Create new batch
          const batchNumber = form.value.batch_number || generateBatchNumber()
          
          const batchData = {
            product_id: product.value._id,
            batch_number: batchNumber,
            quantity_received: form.value.quantity_received,
            cost_price: form.value.cost_price,
            expiry_date: form.value.expiry_date,
            supplier_id: form.value.supplier_id || null
          }

          result = await createBatch(batchData)
          
          success(`New batch created: ${form.value.quantity_received} units added`)
          
        } else {
          // Adjust existing stock using FIFO
          result = await processBatchAdjustment(
            product.value._id,
            form.value.quantity_used,
            form.value.adjustment_type,
            user.value?._id, // ✅ Pass user ID here
            form.value.notes
          )
          
          success(`Stock adjusted: ${form.value.quantity_used} units (${form.value.adjustment_type})`)
        }
        
        emit('success', {
          message: 'Stock updated successfully',
          product: result,
          operation: form.value
        })
        
        closeModal()
        
      } catch (err) {
        console.error('Stock update failed:', err)
        showError(err.message || 'Failed to update stock')
      }
    }
    
    const handleOverlayClick = () => {
      if (!loading.value) {
        closeModal()
      }
    }
    
    // Keyboard shortcuts
    const handleKeydown = (event) => {
      if (show.value && event.key === 'Escape' && !loading.value) {
        closeModal()
      }
    }
    
    onMounted(() => {
      document.addEventListener('keydown', handleKeydown)
    })
    
    onBeforeUnmount(() => {
      document.removeEventListener('keydown', handleKeydown)
    })
    
    // Expose methods for parent component
    const openStock = (productData) => {
      openStockModal(productData)
    }
    
    return {
      // State
      show,
      product,
      loading,
      error,
      form,
      newStockPreview,
      today,
      
      // Computed
      isFormValid,
      operationDescription,
      
      // Methods
      closeModal,
      handleSubmit,
      handleOverlayClick,
      onOperationChange,
      calculateNewStock,
      getCategoryName,
      getStockClass,
      getPreviewStockClass,
      getSubmitButtonClass,
      getSubmitButtonText,
      getCurrentStock,
      generateBatchNumber,
      
      // Exposed methods
      openStock
    }
  }
}
</script>

<style scoped>
/* Modal overlay and animation */
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
  padding: 1.5rem 2rem 1rem 2rem;
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

.btn-close:hover:not(:disabled) {
  background-color: var(--neutral-light);
  color: var(--tertiary-dark);
}

.btn-close:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.product-info {
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-details {
  flex: 1;
}

.product-name {
  font-size: 1.125rem;
  margin-bottom: 0.25rem;
}

.product-meta {
  font-size: 0.875rem;
}

.current-stock {
  text-align: right;
}

.stock-label {
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.stock-value {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.stock-threshold {
  font-size: 0.75rem;
}

.stock-form {
  padding: 1.5rem 2rem 2rem 2rem;
}

.batch-section {
  background-color: var(--neutral-light);
  border-color: var(--primary-light) !important;
}

.batch-section h6 {
  color: var(--primary-dark);
  font-weight: 600;
}

/* Custom text colors using colors.css variables */
.text-tertiary-dark {
  color: var(--tertiary-dark) !important;
}

.text-tertiary-medium {
  color: var(--tertiary-medium) !important;
}

/* Form controls focus states using colors.css */
.form-select:focus,
.form-control:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem rgba(115, 146, 226, 0.25);
}

/* Stock status colors using colors.css variables */
.text-success {
  color: var(--success) !important;
}

.text-warning {
  color: var(--warning, #ffc107) !important;
}

.text-danger {
  color: var(--error) !important;
}

/* Input group styling */
.input-group-text {
  background-color: var(--neutral-light);
  border-color: var(--neutral-medium);
  color: var(--tertiary-dark);
}

/* Responsive Design */
@media (max-width: 768px) {
  .modal-content {
    margin: 1rem;
    max-height: calc(100vh - 2rem);
    max-width: 500px;
  }

  .modal-header {
    padding: 1rem 1.5rem 0.75rem 1.5rem;
  }

  .modal-header h2 {
    font-size: 1.25rem;
  }

  .product-info {
    padding: 1rem 1.5rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .current-stock {
    text-align: left;
    width: 100%;
  }

  .stock-form {
    padding: 1rem 1.5rem 1.5rem 1.5rem;
  }

  .batch-section {
    padding: 1rem;
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

  .product-meta {
    flex-direction: column;
    gap: 0.25rem;
  }

  .batch-section {
    padding: 0.75rem;
  }
}

/* Custom scrollbar */
.modal-content::-webkit-scrollbar {
  width: 6px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--neutral-light);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--neutral-medium);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--neutral-dark);
}
</style>