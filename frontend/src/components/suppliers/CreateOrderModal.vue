<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content modern-order-modal" @click.stop>
        <!-- Modal Header -->
        <div class="modal-header new-order-modal-header">
          <div class="d-flex align-items-center">
            <div class="modal-icon modal-icon-pending me-3">
              <ShoppingCart :size="24" />
            </div>
            <div class="modal-heading">
              <h4 class="modal-title mb-1">New Order</h4>
              <p class="modal-subtitle mb-0">
                Order stock from <strong>{{ supplier?.name }}</strong>
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
        <div class="modal-body pt-4 scrollable-content">
          <!-- Order Information -->
          <div class="row mb-4">
            <!-- Left Column - Order Details -->
            <div class="col-md-6">
              <div class="order-info-card">
                <h5 class="mb-3">
                  <FileText :size="18" class="me-2" />
                  Order Information
                </h5>
                
                <div class="row g-3">
                  <div class="col-md-6">
                    <label for="orderId" class="form-label">Order ID</label>
                    <input 
                      type="text" 
                      class="form-control order-id-input" 
                      id="orderId"
                      v-model="orderData.orderId"
                      readonly
                    >
                  </div>
                  
                  <div class="col-md-6">
                    <label for="orderDate" class="form-label">Order Date</label>
                    <input 
                      type="date" 
                      class="form-control" 
                      id="orderDate"
                      v-model="orderData.orderDate"
                    >
                  </div>
                  
                  <div class="col-md-6">
                    <label for="referenceNumber" class="form-label">Batch Number</label>
                    <input 
                      type="text" 
                      class="form-control" 
                      id="referenceNumber"
                      v-model="orderData.referenceNumber"
                      placeholder="Leave empty to auto-generate"
                    >
                    <small class="text-muted d-block mt-1">
                      <Clock :size="12" class="me-1" />
                      Will auto-generate if left empty
                    </small>
                  </div>
                  
                  <div class="col-md-6">
                    <label for="expectedDeliveryDate" class="form-label">Expected Delivery <span class="text-danger">*</span></label>
                    <input 
                      type="date" 
                      class="form-control" 
                      id="expectedDeliveryDate"
                      v-model="orderData.expectedDeliveryDate"
                      :min="orderData.orderDate"
                    >
                  </div>
                  
                  <div class="col-12">
                    <label for="orderNotes" class="form-label">Order Notes</label>
                    <textarea 
                      class="form-control" 
                      id="orderNotes"
                      v-model="orderData.notes"
                      rows="3"
                      placeholder="Any notes about this order..."
                    ></textarea>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Right Column - Supplier Info -->
            <div class="col-md-6">
              <div class="supplier-info-card">
                <h5 class="mb-3">
                  <Building :size="18" class="me-2" />
                  Supplier Information
                </h5>
                
                <div class="supplier-details">
                  <div class="detail-row">
                    <strong>Company:</strong>
                    <span>{{ supplier?.name }}</span>
                  </div>
                  <div class="detail-row">
                    <strong>Contact:</strong>
                    <span>{{ supplier?.contactPerson || 'Not specified' }}</span>
                  </div>
                  <div class="detail-row">
                    <strong>Email:</strong>
                    <span>{{ supplier?.email || 'Not provided' }}</span>
                  </div>
                  <div class="detail-row">
                    <strong>Phone:</strong>
                    <span>{{ supplier?.phone || 'Not provided' }}</span>
                  </div>
                  <div class="detail-row">
                    <strong>Type:</strong>
                    <span>{{ getSupplierTypeLabel(supplier?.type) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Order Items Section -->
          <div class="order-items-section">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h5 class="mb-0">
                <Package :size="18" class="me-2" />
                Order Items
              </h5>
              <button 
                class="btn btn-outline-primary btn-sm"
                @click="addOrderItem"
              >
                <Plus :size="16" class="me-1" />
                Add Item
              </button>
            </div>

            <!-- Items Table -->
            <div class="table-responsive">
              <table class="table order-items-table">
                <thead class="table-light">
                  <tr>
                    <th style="width: 40px;">#</th>
                    <th style="width: 180px;">Category <span class="text-danger">*</span></th>
                    <th style="width: 180px;">Subcategory <span class="text-danger">*</span></th>
                    <th style="width: 200px;">Product <span class="text-danger">*</span></th>
                    <th style="width: 100px;">Quantity <span class="text-danger">*</span></th>
                    <th style="width: 120px;">Est. Unit Cost (₱)</th>
                    <th style="width: 100px;">Expected Expiry</th>
                    <th style="width: 120px;">Total Cost</th>
                    <th style="width: 60px;">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="(item, index) in orderData.items" 
                    :key="`item-${index}`"
                    :class="{ 'table-danger': item.errors && Object.keys(item.errors).length > 0 }"
                  >
                    <td class="text-center">{{ index + 1 }}</td>
                    
                    <!-- Category Dropdown -->
                    <td>
                      <select 
                        class="form-select form-select-sm"
                        :class="{ 'is-invalid': item.errors?.category }"
                        v-model="item.categoryId"
                        @change="onCategoryChange(index)"
                      >
                        <option value="">Select Category</option>
                        <option 
                          v-for="category in categories" 
                          :key="category._id"
                          :value="category._id"
                        >
                          {{ category.category_name }}
                        </option>
                      </select>
                      <div v-if="item.errors?.category" class="invalid-feedback">
                        {{ item.errors.category }}
                      </div>
                    </td>
                    
                    <!-- Subcategory Dropdown -->
                    <td>
                      <select 
                        class="form-select form-select-sm"
                        :class="{ 'is-invalid': item.errors?.subcategory }"
                        v-model="item.subcategoryName"
                        @change="onSubcategoryChange(index)"
                        :disabled="!item.categoryId"
                      >
                        <option value="">Select Subcategory</option>
                        <option 
                          v-for="subcategory in getSubcategoriesForItem(item)" 
                          :key="subcategory.name"
                          :value="subcategory.name"
                        >
                          {{ subcategory.name }} ({{ subcategory.product_count }})
                        </option>
                      </select>
                      <div v-if="item.errors?.subcategory" class="invalid-feedback">
                        {{ item.errors.subcategory }}
                      </div>
                    </td>
                    
                    <!-- Product Dropdown -->
                    <td>
                      <select 
                        class="form-select form-select-sm"
                        :class="{ 'is-invalid': item.errors?.product }"
                        v-model="item.productId"
                        @change="onProductChange(index)"
                        :disabled="!item.subcategoryName"
                      >
                        <option value="">Select Product</option>
                        <option 
                          v-for="product in getProductsForItem(item)" 
                          :key="product._id"
                          :value="product._id"
                        >
                          {{ product.product_name }} - {{ product.SKU }}
                        </option>
                      </select>
                      <div v-if="item.errors?.product" class="invalid-feedback">
                        {{ item.errors.product }}
                      </div>
                      <small v-if="item.selectedProduct" class="text-muted d-block mt-1">
                        Current stock: {{ item.selectedProduct.total_stock || 0 }}
                      </small>
                    </td>
                    
                    <!-- Quantity -->
                    <td>
                      <input 
                        type="number" 
                        class="form-control form-control-sm"
                        :class="{ 'is-invalid': item.errors?.quantity }"
                        v-model.number="item.quantity"
                        @input="validateItem(index); calculateItemTotal(index)"
                        min="1"
                        step="1"
                        placeholder="0"
                      >
                      <div v-if="item.errors?.quantity" class="invalid-feedback">
                        {{ item.errors.quantity }}
                      </div>
                    </td>
                    
                    <!-- Unit Cost -->
                    <td>
                      <input 
                        type="number" 
                        class="form-control form-control-sm"
                        v-model.number="item.estimatedCost"
                        @input="calculateItemTotal(index)"
                        min="0"
                        step="0.01"
                        placeholder="0.00"
                      >
                    </td>
                    
                    <!-- Expected Expiry Date -->
                    <td>
                      <input 
                        type="date" 
                        class="form-control form-control-sm"
                        v-model="item.expectedExpiryDate"
                        :min="orderData.expectedDeliveryDate"
                      >
                    </td>
                    
                    <!-- Total Cost -->
                    <td>
                      <div class="total-price">
                        ₱{{ formatCurrency(item.totalCost || 0) }}
                      </div>
                    </td>
                    
                    <!-- Actions -->
                    <td class="text-center">
                      <button 
                        class="btn btn-outline-danger btn-sm"
                        @click="removeOrderItem(index)"
                        :disabled="orderData.items.length <= 1"
                        title="Remove item"
                      >
                        <Trash2 :size="14" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Add Item Button (if no items) -->
            <div v-if="orderData.items.length === 0" class="text-center py-4">
              <Package :size="48" class="text-muted mb-3" />
              <p class="text-muted mb-3">No items added yet</p>
              <button class="btn btn-primary" @click="addOrderItem">
                <Plus :size="16" class="me-1" />
                Add First Item
              </button>
            </div>
          </div>

          <!-- Order Summary -->
          <div class="order-summary-section mt-4">
            <div class="row">
              <div class="col-md-8">
                <div class="alert alert-warning">
                  <Clock :size="16" class="me-2" />
                  <strong>Purchase Order (Pending Delivery):</strong> Batches will be created with "pending" status. 
                  Use "Receive Stock" button to activate them when delivery arrives.
                </div>
              </div>
              
              <div class="col-md-4">
                <!-- Order Totals -->
                <div class="order-totals">
                  <h6 class="mb-3">Order Summary</h6>
                  
                  <div class="summary-row">
                    <span>Total Items:</span>
                    <span class="fw-bold">{{ validItemsCount }}</span>
                  </div>
                  
                  <div class="summary-row">
                    <span>Total Quantity:</span>
                    <span class="fw-bold">{{ totalQuantity }}</span>
                  </div>
                  
                  <div class="summary-row">
                    <span>Total Products:</span>
                    <span class="fw-bold">{{ uniqueProductsCount }}</span>
                  </div>
                  
                  <hr>
                  
                  <div class="summary-row total-row">
                    <span class="fw-bold">Estimated Total:</span>
                    <span class="fw-bold text-primary fs-5">₱{{ formatCurrency(grandTotal) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer sticky-footer border-0">
          <div class="d-flex justify-content-between align-items-center w-100">
            <div class="text-muted small">
              <Clock :size="16" class="me-1" />
              {{ validItemsCount }} pending batch(es) will be created
            </div>
            
            <div class="d-flex gap-3">
              <button 
                type="button" 
                class="btn btn-outline-secondary px-4"
                @click="handleClose"
                :disabled="saving"
              >
                Cancel
              </button>
              <button 
                type="button" 
                class="btn btn-primary px-4"
                @click="saveOrder"
                :disabled="!isOrderValid || saving"
                :class="{ 'btn-loading': saving }"
              >
                <div v-if="saving" class="spinner-border spinner-border-sm me-2"></div>
                <ShoppingCart :size="16" class="me-1" />
                Create Pending Order
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { 
  Package,
  FileText,
  Building,
  Plus,
  Trash2,
  ShoppingCart,
  Clock
} from 'lucide-vue-next'
import { useCategories } from '@/composables/api/useCategories'
import { useProducts } from '@/composables/api/useProducts'
import { useBatches } from '@/composables/api/useBatches'
import { useToast } from '@/composables/ui/useToast'

export default {
  name: 'CreateOrderModal',
  components: {
    Package,
    FileText,
    Building,
    Plus,
    Trash2,
    ShoppingCart,
    Clock
  },
  emits: ['close', 'saved'],
  props: {
    show: {
      type: Boolean,
      default: false
    },
    supplier: {
      type: Object,
      required: false,
      default: null
    }
  },
  setup(props, { emit }) {
    const { success: showSuccess, error: showError } = useToast()
    const { categories, fetchCategories } = useCategories()
    const { fetchProductsByCategory } = useProducts()
    const { createBatch } = useBatches()
    
    const saving = ref(false)
    const productsByCategory = ref({})
    
    const orderData = ref({
      orderId: generateOrderId(),
      orderDate: new Date().toISOString().split('T')[0],
      expectedDeliveryDate: '',
      referenceNumber: '',
      notes: '',
      items: [createEmptyItem()]
    })
    
    // ================ HELPER FUNCTIONS ================
    
    function generateOrderId() {
      const prefix = 'OD'
      const timestamp = Date.now().toString().slice(-6)
      const random = Math.floor(Math.random() * 100).toString().padStart(2, '0')
      return `${prefix}-${timestamp}${random}`
    }
    
    function generateBatchNumber() {
      // Generate a unique batch number in format BATCH-0001
      // All items in the same purchase order will share this batch number
      const timestamp = Date.now().toString().slice(-6)
      const random = Math.floor(Math.random() * 100).toString().padStart(2, '0')
      return `BATCH-${timestamp}${random}`
    }
    
    function createEmptyItem() {
      return {
        categoryId: '',
        subcategoryName: '',
        productId: '',
        selectedProduct: null,
        quantity: null,
        estimatedCost: null,
        expectedExpiryDate: '',
        totalCost: 0,
        errors: {}
      }
    }
    
    function getSupplierTypeLabel(type) {
      const labels = {
        'food': 'Food & Beverages',
        'packaging': 'Packaging Materials',
        'equipment': 'Equipment & Tools',
        'services': 'Services',
        'raw_materials': 'Raw Materials',
        'other': 'Other'
      }
      return labels[type] || 'Not specified'
    }
    
    function formatCurrency(amount) {
      return new Intl.NumberFormat('en-PH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount || 0)
    }
    
    // ================ COMPUTED PROPERTIES ================
    
    const validItems = computed(() => {
      return orderData.value.items.filter(item => 
        item.productId && 
        item.quantity && 
        item.quantity > 0 &&
        (!item.errors || Object.keys(item.errors).length === 0)
      )
    })
    
    const validItemsCount = computed(() => validItems.value.length)
    
    const totalQuantity = computed(() => {
      return validItems.value.reduce((sum, item) => sum + (item.quantity || 0), 0)
    })
    
    const uniqueProductsCount = computed(() => {
      const uniqueProducts = new Set(validItems.value.map(item => item.productId))
      return uniqueProducts.size
    })
    
    const grandTotal = computed(() => {
      return validItems.value.reduce((sum, item) => sum + (item.totalCost || 0), 0)
    })
    
    const isOrderValid = computed(() => {
      return validItems.value.length > 0 && 
             orderData.value.expectedDeliveryDate
    })
    
    // ================ CASCADE DROPDOWN METHODS ================
    
    function getSubcategoriesForItem(item) {
      if (!item.categoryId) return []
      
      const category = categories.value.find(cat => cat._id === item.categoryId)
      return category?.sub_categories || []
    }
    
    function getProductsForItem(item) {
      if (!item.categoryId || !item.subcategoryName) return []
      
      const key = `${item.categoryId}-${item.subcategoryName}`
      const products = productsByCategory.value[key] || []
      
      // ✅ SAFETY CHECK
      if (!Array.isArray(products)) {
        console.error('Products for key is not an array:', key, products)
        return []
      }
      
      return products
    }
    
    async function onCategoryChange(index) {
      const item = orderData.value.items[index]
      
      // Reset dependent fields
      item.subcategoryName = ''
      item.productId = ''
      item.selectedProduct = null
      
      // Clear errors
      if (item.errors?.category) {
        delete item.errors.category
      }
      
      validateItem(index)
    }
    
    async function onSubcategoryChange(index) {
      const item = orderData.value.items[index]
      
      // Reset product selection
      item.productId = ''
      item.selectedProduct = null
      
      // Clear errors
      if (item.errors?.subcategory) {
        delete item.errors.subcategory
      }
      
      // Load products for this category-subcategory combination
      if (item.categoryId && item.subcategoryName) {
        await loadProductsForCategorySubcategory(item.categoryId, item.subcategoryName)
      }
      
      validateItem(index)
    }
    
    async function onProductChange(index) {
      const item = orderData.value.items[index]
      
      // Find and store the selected product
      const products = getProductsForItem(item)
      
      // ✅ ADD SAFETY CHECK
      if (!Array.isArray(products)) {
        console.error('Products is not an array:', products)
        item.selectedProduct = null
        return
      }
      
      item.selectedProduct = products.find(p => p._id === item.productId)
      
      // Set default cost if available
      if (item.selectedProduct && !item.estimatedCost) {
        item.estimatedCost = item.selectedProduct.cost_price || item.selectedProduct.selling_price || 0
      }
      
      // Clear errors
      if (item.errors?.product) {
        delete item.errors.product
      }
      
      validateItem(index)
      calculateItemTotal(index)
    }
    
    async function loadProductsForCategorySubcategory(categoryId, subcategoryName) {
      const key = `${categoryId}-${subcategoryName}`
      
      // Skip if already loaded
      if (productsByCategory.value[key]) {
        return
      }
      
      try {
        const response = await fetchProductsByCategory(categoryId, subcategoryName)
        
        // ✅ HANDLE DIFFERENT RESPONSE FORMATS
        let productsArray = []
        
        if (Array.isArray(response)) {
          productsArray = response
        } else if (response && Array.isArray(response.data)) {
          productsArray = response.data
        } else if (response && Array.isArray(response.products)) {
          productsArray = response.products
        } else {
          console.warn('Unexpected response format:', response)
          productsArray = []
        }
        
        productsByCategory.value[key] = productsArray
        
      } catch (error) {
        console.error('Error loading products:', error)
        productsByCategory.value[key] = []
      }
    }
    
    // ================ ITEM MANAGEMENT ================
    
    function addOrderItem() {
      orderData.value.items.push(createEmptyItem())
    }
    
    function removeOrderItem(index) {
      if (orderData.value.items.length > 1) {
        orderData.value.items.splice(index, 1)
      }
    }
    
    function validateItem(index) {
      const item = orderData.value.items[index]
      const errors = {}
      
      if (!item.categoryId) {
        errors.category = 'Category is required'
      }
      
      if (!item.subcategoryName) {
        errors.subcategory = 'Subcategory is required'
      }
      
      if (!item.productId) {
        errors.product = 'Product is required'
      }
      
      if (!item.quantity || item.quantity <= 0) {
        errors.quantity = 'Quantity must be greater than 0'
      } else if (!Number.isInteger(item.quantity)) {
        errors.quantity = 'Quantity must be a whole number'
      }
      
      item.errors = errors
    }
    
    function validateAllItems() {
      orderData.value.items.forEach((item, index) => {
        validateItem(index)
      })
    }
    
    function calculateItemTotal(index) {
      const item = orderData.value.items[index]
      const quantity = item.quantity || 0
      const unitPrice = item.estimatedCost || 0
      item.totalCost = quantity * unitPrice
    }
    
    // ================ SAVE ORDER ================
    
    async function saveOrder() {
      saving.value = true
      
      try {
        validateAllItems()
        
        if (!isOrderValid.value) {
          showError('Please fix validation errors before saving')
          return
        }
        
        const itemsToProcess = validItems.value
        const results = {
          successful: [],
          failed: []
        }
        
        // Use user-provided batch number or generate one automatically
        const sharedBatchNumber = orderData.value.referenceNumber?.trim() || generateBatchNumber()
        
        // Update the orderData with the final batch number (in case it was auto-generated)
        if (!orderData.value.referenceNumber?.trim()) {
          orderData.value.referenceNumber = sharedBatchNumber
        }
        
        // Validate supplier exists
        if (!props.supplier?.id) {
          showError('Supplier information is required to create an order')
          return
        }

        // Create a batch for each valid item with the same batch number
        for (const item of itemsToProcess) {
          try {
            const batchData = {
              product_id: item.productId,
              supplier_id: props.supplier.id,
              batch_number: sharedBatchNumber, // ✅ Same batch number for all items in this order
              quantity_received: item.quantity,
              cost_price: item.estimatedCost || 0,
              expiry_date: item.expectedExpiryDate || null,
              expected_delivery_date: orderData.value.expectedDeliveryDate, // ✅ Expected delivery date (for pending orders)
              // date_received will be null until stock is actually received/activated
              status: 'pending', // ✅ CREATE AS PENDING (on-going delivery)
              notes: `Receipt: ${orderData.value.orderId} | Batch: ${sharedBatchNumber}${orderData.value.notes ? ` | ${orderData.value.notes}` : ''}`
            }
            
            const response = await createBatch(batchData)
            
            results.successful.push({
              product: item.selectedProduct?.product_name,
              batch: response
            })
            
          } catch (error) {
            console.error('Error creating batch for item:', item, error)
            results.failed.push({
              product: item.selectedProduct?.product_name,
              error: error.message
            })
          }
        }
        
        // ✅ Don't show toast here - let parent handle it to avoid duplicates
        // Parent (SupplierDetails) will show the success/error toast
        
        // Emit saved event with results
        emit('saved', {
          orderId: orderData.value.orderId,
          supplierId: props.supplier?.id,
          supplierName: props.supplier?.name,
          results
        })
        
        // Close modal
        handleClose()
        
      } catch (error) {
        console.error('Error saving order:', error)
        showError('Failed to process order. Please try again.')
      } finally {
        saving.value = false
      }
    }
    
    // ================ MODAL CONTROLS ================
    
    function handleOverlayClick() {
      if (!saving.value) {
        handleClose()
      }
    }

    function handleClose() {
      emit('close')
      resetForm()
    }
    
    function resetForm() {
      orderData.value = {
        orderId: generateOrderId(),
        orderDate: new Date().toISOString().split('T')[0],
        expectedDeliveryDate: '',
        referenceNumber: '', // Leave empty - will auto-generate when saving if not filled
        notes: '',
        items: [createEmptyItem()]
      }
      productsByCategory.value = {}
      saving.value = false
    }
    
    // ================ LIFECYCLE ================
    
    onMounted(async () => {
      try {
        await fetchCategories()
      } catch (error) {
        console.error('Error loading categories:', error)
        showError('Failed to load categories')
      }
    })
    
    watch(() => props.show, (newVal) => {
      if (newVal) {
        resetForm()
      }
    })
    
    return {
      // Data
      orderData,
      saving,
      categories,
      
      // Computed
      validItemsCount,
      totalQuantity,
      uniqueProductsCount,
      grandTotal,
      isOrderValid,
      
      // Methods
      getSupplierTypeLabel,
      formatCurrency,
      getSubcategoriesForItem,
      getProductsForItem,
      onCategoryChange,
      onSubcategoryChange,
      onProductChange,
      addOrderItem,
      removeOrderItem,
      validateItem,
      calculateItemTotal,
      saveOrder,
      handleClose,
      handleOverlayClick
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';
/* Keep all existing styles from CreateOrderModal */
.modern-order-modal {
  border-radius: 16px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

.modal-icon-pending {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--primary-light), var(--primary));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-dark);
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

.modal-body {
  padding: 1.5rem 1.75rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.scrollable-content {
  overflow-y: auto;
  overflow-x: hidden;
}

.order-info-card,
.supplier-info-card {
  padding: 1.25rem 1.5rem;
  background-color: var(--surface-tertiary);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  height: 100%;
  box-shadow: var(--shadow-sm);
}

.supplier-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-primary);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row strong {
  color: var(--text-primary);
  min-width: 80px;
}

.detail-row span {
  color: var(--text-secondary);
  text-align: right;
  flex: 1;
}

.dark-theme .detail-row strong,
.dark-theme .detail-row span {
  color: var(--text-secondary);
}

.order-items-section {
  background-color: var(--surface-primary);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  padding: 1.5rem 1.5rem 1.25rem;
  box-shadow: var(--shadow-sm);
}

.order-items-table {
  margin-bottom: 0;
  border-collapse: separate;
  border-spacing: 0;
}

.order-items-table th {
  background-color: var(--surface-tertiary);
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-primary);
  font-size: 0.875rem;
  border-top: 1px solid var(--border-primary);
  border-left: 1px solid var(--border-primary);
}

.order-items-table th:first-child {
  border-left: 1px solid var(--border-primary);
  border-top-left-radius: 8px;
}

.order-items-table th:last-child {
  border-right: 1px solid var(--border-primary);
  border-top-right-radius: 8px;
}

.order-items-table td {
  vertical-align: middle;
  padding: 0.65rem 0.5rem;
  border: 1px solid var(--border-primary);
  border-top: none;
  color: var(--text-secondary);
}

.order-items-table tr:last-child td {
  border-bottom: 1px solid var(--border-primary);
}

.order-items-table tr td:first-child {
  border-left: 1px solid var(--border-primary);
}

.order-items-table tr td:last-child {
  border-right: 1px solid var(--border-primary);
}

.order-items-table tr:last-child td:first-child {
  border-bottom-left-radius: 8px;
}

.order-items-table tr:last-child td:last-child {
  border-bottom-right-radius: 8px;
}

.total-price {
  font-weight: 600;
  color: var(--text-primary);
  text-align: right;
  padding: 0.5rem;
  background-color: var(--surface-tertiary);
  border-radius: 4px;
}

.order-summary-section {
  background-color: var(--surface-tertiary);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-sm);
}

.order-totals {
  background-color: var(--surface-primary);
  border-radius: 8px;
  padding: 1.5rem;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-sm);
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-primary);
  color: var(--text-secondary);
}

.summary-row:last-child {
  border-bottom: none;
}

.total-row {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 2px solid var(--border-primary);
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border: none;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(115, 146, 226, 0.3);
}

.sticky-footer {
  padding: 1.25rem 1.75rem 1.5rem 1.75rem;
  background-color: var(--surface-tertiary);
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
  position: sticky;
  bottom: 0;
  z-index: 10;
  box-shadow: var(--shadow-md);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-id-input {
  background-color: var(--input-bg) !important;
  color: var(--input-text) !important;
  border-color: var(--input-border) !important;
}

.table-danger {
  background-color: rgba(220, 53, 69, 0.1) !important;
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
  max-width: 1350px;
  width: 95%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
  z-index: 10000 !important;
  background-color: var(--surface-elevated);
  border-radius: 16px;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-2xl);
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
    padding: 1.25rem 1.5rem !important;
  }

  .scrollable-content {
    padding: 0 !important;
  }

  .new-order-modal-header {
    padding: 1.5rem 1.75rem 1rem 1.75rem !important;
    background: linear-gradient(135deg, var(--surface-tertiary), var(--surface-secondary));
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  }
  
  .sticky-footer {
    padding: 1rem 1.5rem 1.5rem 1.5rem !important;
  }

  .order-info-card,
  .supplier-info-card {
    margin-bottom: 1rem;
    height: auto;
  }

  .order-info-card h5,
  .order-items-section h5 {
    color: var(--text-primary);
    font-weight: 600;
    letter-spacing: 0.01em;
  }

  .order-info-card label,
  .supplier-info-card label {
    font-weight: 500;
    color: var(--text-secondary);
  }

  /* Stack columns on mobile */
  .row > [class*="col-md-"] {
    width: 100%;
    flex: 0 0 100%;
    max-width: 100%;
  }

  .order-items-section {
    padding: 1rem;
  }

  .order-items-table {
    font-size: 0.85rem;
  }

  .order-items-table th,
  .order-items-table td {
    padding: 0.5rem 0.25rem;
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

  .modal-body {
    padding: 1rem 1.25rem !important;
    max-height: calc(100vh - 200px);
  }

  .sticky-footer {
    padding: 0.75rem 1rem 1rem 1rem !important;
  }

  .sticky-footer > div {
    flex-direction: column;
    gap: 0.75rem;
  }

  .sticky-footer > div > div:first-child {
    text-align: center;
    margin-bottom: 0.5rem;
  }

  .sticky-footer > div > div:last-child {
    flex-direction: column;
    width: 100%;
    gap: 0.5rem;
  }

  .sticky-footer .btn {
    width: 100%;
  }

  .modal-icon {
    width: 40px !important;
    height: 40px !important;
  }

  .order-info-card,
  .supplier-info-card,
  .order-items-section {
    padding: 1rem;
  }

  .order-items-table {
    font-size: 0.8rem;
  }

  .order-items-table th,
  .order-items-table td {
    padding: 0.4rem 0.2rem;
  }

  .btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
  }
}

/* Custom Scrollbar */
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
  background: var(--primary);
}

/* Prevent body scroll when modal is open */
body:has(.modal-overlay) {
  overflow: hidden !important;
}
</style>