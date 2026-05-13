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
            <div class="col-md-6 mb-3 mb-md-0">
              <CardTemplate size="md" shadow="sm" class="h-100">
                <template #content>
                  <h5 class="section-heading mb-3">
                    <FileText :size="18" class="me-2" />
                    Order Information
                  </h5>

                  <div class="row g-3">
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
                      <label for="expectedDeliveryDate" class="form-label">Expected Delivery <span class="text-status-error">*</span></label>
                      <input
                        type="date"
                        class="form-control"
                        :class="{ 'is-invalid': formErrors.expectedDelivery }"
                        id="expectedDeliveryDate"
                        v-model="orderData.expectedDeliveryDate"
                        :min="orderData.orderDate"
                        @change="clearDeliveryError"
                      >
                      <div v-if="formErrors.expectedDelivery" class="invalid-feedback">
                        {{ formErrors.expectedDelivery }}
                      </div>
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
                </template>
              </CardTemplate>
            </div>
            
            <!-- Right Column - Supplier Info -->
            <div class="col-md-6">
              <CardTemplate size="md" shadow="sm" class="h-100">
                <template #content>
                  <h5 class="section-heading mb-3">
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
                </template>
              </CardTemplate>
            </div>
          </div>

          <!-- Order Items Section - Two Column: Browse + Checkout -->
          <div class="row g-3">

            <!-- Left: Product Browser -->
            <div class="col-lg-5">
              <CardTemplate shadow="sm" class="h-100">
                <template #content>
                  <div class="d-flex align-items-center mb-3">
                    <h5 class="section-heading mb-0">
                      <Package :size="18" class="me-2" />
                      Product Catalog
                    </h5>
                    <span class="badge ms-auto">{{ filteredBrowseProducts.length }} product(s)</span>
                  </div>

                  <!-- Filters -->
                  <div class="row g-2 mb-3">
                    <div class="col-12">
                      <input
                        type="text"
                        class="form-control form-control-sm"
                        v-model="productSearchQuery"
                        placeholder="Search by name or SKU..."
                      >
                    </div>
                    <div class="col-6">
                      <select class="form-select form-select-sm" v-model="filterCategoryId" @change="onFilterCategoryChange">
                        <option value="">All Categories</option>
                        <option v-for="cat in categories" :key="cat.category_id" :value="cat.category_id">
                          {{ cat.category_name }}
                        </option>
                      </select>
                    </div>
                    <div class="col-6">
                      <select
                        class="form-select form-select-sm"
                        v-model="filterSubcategoryId"
                        :disabled="!filterCategoryId"
                      >
                        <option value="">All Subcategories</option>
                        <option v-for="sub in filterSubcategories" :key="sub.name" :value="sub.name">
                          {{ sub.name }} ({{ sub.product_count }})
                        </option>
                      </select>
                    </div>
                  </div>

                  <!-- Product List -->
                  <div class="product-browser-list">
                    <div v-if="isBrowseLoading" class="browser-empty-state">
                      <div class="spinner-border spinner-border-sm text-accent"></div>
                      <p class="mb-0 small mt-2">Loading products...</p>
                    </div>
                    <div v-else-if="filteredBrowseProducts.length === 0" class="browser-empty-state">
                      <Package :size="32" class="mb-2" />
                      <p class="mb-0 small">No products found</p>
                    </div>
                    <template v-else>
                      <div
                        v-for="product in filteredBrowseProducts"
                        :key="product.product_id"
                        class="product-browser-item"
                        :class="{ 'is-selected': isProductSelected(product.product_id) }"
                        @click="toggleProduct(product)"
                      >
                        <input
                          type="checkbox"
                          class="form-check-input flex-shrink-0"
                          :checked="isProductSelected(product.product_id)"
                          @click.stop
                          @change="toggleProduct(product)"
                        >
                        <div class="product-browser-info ms-2">
                          <div class="product-browser-name">{{ product.product_name }}</div>
                          <div class="product-browser-meta">
                            <span>{{ product.sku }}</span>
                            <span class="ms-2">Stock: {{ product.total_stock > 0 ? product.total_stock : '—' }}</span>
                          </div>
                        </div>
                      </div>
                    </template>
                  </div>
                </template>
              </CardTemplate>
            </div>

            <!-- Right: Selected Items / Checkout -->
            <div class="col-lg-7">
              <CardTemplate shadow="sm" class="h-100">
                <template #content>
                  <div class="d-flex align-items-center mb-3">
                    <h5 class="section-heading mb-0">
                      <ShoppingCart :size="18" class="me-2" />
                      Order Items
                    </h5>
                    <span class="badge ms-auto">{{ orderData.items.length }} selected</span>
                  </div>

                  <!-- Empty state -->
                  <div v-if="orderData.items.length === 0" class="checkout-empty-state" :class="{ 'has-error': formErrors.noItems }">
                    <ShoppingCart :size="36" class="mb-2" />
                    <p class="mb-0 small">Tick products from the catalog to add them here</p>
                    <p v-if="formErrors.noItems" class="mb-0 small text-status-error mt-1">
                      {{ formErrors.noItems }}
                    </p>
                  </div>

                  <!-- Selected Items -->
                  <div v-else class="selected-items-list">
                    <div
                      v-for="(item, index) in orderData.items"
                      :key="`item-${index}`"
                      class="selected-item-card"
                      :class="{ 'has-error': item.errors && Object.keys(item.errors).length > 0 }"
                    >
                      <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                          <div class="fw-semibold item-product-name">{{ item.selectedProduct?.product_name }}</div>
                          <small v-if="item.selectedProduct?.sku" class="text-secondary">{{ item.selectedProduct.sku }}</small>
                        </div>
                        <button class="btn btn-delete btn-sm ms-2 flex-shrink-0" @click="toggleProduct(item.selectedProduct)" title="Remove">
                          <Trash2 :size="13" />
                        </button>
                      </div>

                      <div class="row g-2">
                        <div class="col-4">
                          <label class="form-label small mb-1">Qty <span class="text-status-error">*</span></label>
                          <input
                            type="number"
                            class="form-control form-control-sm"
                            :class="{ 'is-invalid': item.errors?.quantity }"
                            v-model.number="item.quantity"
                            @input="validateItem(index); calculateItemTotal(index)"
                            min="1" step="1" placeholder="0"
                          >
                          <div v-if="item.errors?.quantity" class="invalid-feedback">{{ item.errors.quantity }}</div>
                        </div>
                        <div class="col-4">
                          <label class="form-label small mb-1">Unit Cost (₱)</label>
                          <input
                            type="number"
                            class="form-control form-control-sm"
                            v-model.number="item.estimatedCost"
                            @input="calculateItemTotal(index)"
                            min="0" step="0.01" placeholder="0.00"
                          >
                        </div>
                        <div class="col-4">
                          <label class="form-label small mb-1">Expiry Date</label>
                          <input
                            type="date"
                            class="form-control form-control-sm"
                            v-model="item.expectedExpiryDate"
                            :min="orderData.expectedDeliveryDate"
                          >
                        </div>
                      </div>

                      <div class="d-flex justify-content-end align-items-center mt-2">
                        <span class="text-secondary small me-2">Total:</span>
                        <span class="fw-semibold text-accent">₱{{ formatCurrency(item.totalCost || 0) }}</span>
                      </div>
                    </div>
                  </div>
                </template>
              </CardTemplate>
            </div>

          </div>

          <!-- Order Summary -->
          <CardTemplate shadow="sm" class="mt-4">
            <template #content>
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
                  <CardTemplate size="sm" shadow="sm">
                    <template #content>
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
                        <span class="fw-bold text-accent fs-5">₱{{ formatCurrency(grandTotal) }}</span>
                      </div>
                    </template>
                  </CardTemplate>
                </div>
              </div>
            </template>
          </CardTemplate>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer sticky-footer border-0">
          <div class="d-flex justify-content-between align-items-center w-100">
            <div class="text-secondary small">
              <Clock :size="16" class="me-1" />
              {{ validItemsCount }} pending batch(es) will be created
            </div>

            <div class="d-flex gap-3">
              <button
                type="button"
                class="btn btn-cancel px-4"
                @click="handleClose"
                :disabled="saving"
              >
                Cancel
              </button>
              <button
                type="button"
                class="btn btn-save px-4"
                @click="saveOrder"
                :disabled="saving"
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
  Trash2,
  ShoppingCart,
  Clock
} from 'lucide-vue-next'
import CardTemplate from '@/components/common/CardTemplate.vue'
import { useCategories } from '@/composables/api/useCategories'
import { useBatches } from '@/composables/api/useBatches'
import { useShipments } from '@/composables/api/useShipments'
import { useToast } from '@/composables/ui/useToast'
import apiProductsService from '@/services/apiProducts'

export default {
  name: 'CreateOrderModal',
  components: {
    CardTemplate,
    Package,
    FileText,
    Building,
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
    },
    prefillItems: {
      type: Array,
      default: () => []
    }
  },
  setup(props, { emit }) {
    const { success: showSuccess, error: showError } = useToast()
    const { categories, fetchCategories } = useCategories()
    const { createBatch } = useBatches()
    const { createShipment } = useShipments()

    const saving = ref(false)
    const formErrors = ref({})

    // Browser state — all products loaded once, filtered client-side
    const filterCategoryId = ref('')
    const filterSubcategoryId = ref('')
    const productSearchQuery = ref('')
    const browseProducts = ref([])
    const isBrowseLoading = ref(false)

    const orderData = ref({
      orderDate: new Date().toISOString().split('T')[0],
      expectedDeliveryDate: '',
      notes: '',
      items: []
    })
    
    // ================ HELPER FUNCTIONS ================
    
    
    function generateBatchNumber() {
      // Generate a unique batch number in format BATCH-0001
      // All items in the same purchase order will share this batch number
      const timestamp = Date.now().toString().slice(-6)
      const random = Math.floor(Math.random() * 100).toString().padStart(2, '0')
      return `BATCH-${timestamp}${random}`
    }
    
    function createEmptyItem() {
      return {
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

    const filterSubcategories = computed(() => {
      if (!filterCategoryId.value) return []
      const cat = categories.value.find(c => c.category_id === filterCategoryId.value)
      return cat?.sub_categories || []
    })

    const filteredBrowseProducts = computed(() => {
      let list = browseProducts.value

      if (filterCategoryId.value) {
        list = list.filter(p => p.category_id === filterCategoryId.value)
      }
      if (filterSubcategoryId.value) {
        list = list.filter(p => p.subcategory_name === filterSubcategoryId.value)
      }
      if (productSearchQuery.value) {
        const q = productSearchQuery.value.toLowerCase()
        list = list.filter(p =>
          p.product_name?.toLowerCase().includes(q) ||
          p.sku?.toLowerCase().includes(q)
        )
      }
      return list
    })

    // ================ PRODUCT BROWSER METHODS ================

    function onFilterCategoryChange() {
      filterSubcategoryId.value = ''
    }

    function isProductSelected(productId) {
      return orderData.value.items.some(item => item.productId === productId)
    }

    function clearDeliveryError() {
      if (orderData.value.expectedDeliveryDate) delete formErrors.value.expectedDelivery
    }

    function toggleProduct(product) {
      if (!product) return
      const existingIndex = orderData.value.items.findIndex(item => item.productId === product.product_id)
      if (existingIndex >= 0) {
        orderData.value.items.splice(existingIndex, 1)
      } else {
        const newItem = createEmptyItem()
        newItem.productId = product.product_id
        newItem.selectedProduct = product
        newItem.estimatedCost = product.cost_price || null
        orderData.value.items.push(newItem)
        // Clear the "no items" error as soon as the user adds something
        if (formErrors.value.noItems) delete formErrors.value.noItems
      }
    }

    async function loadAllProducts() {
      isBrowseLoading.value = true
      try {
        const products = await apiProductsService.getAllProductsAllPages({})
        browseProducts.value = Array.isArray(products) ? products : []
      } catch (error) {
        console.error('Error loading products:', error)
        browseProducts.value = []
        showError('Failed to load product catalog')
      } finally {
        isBrowseLoading.value = false
      }
    }

    function applyPrefillItems() {
      const prefill = props.prefillItems || []
      if (!prefill.length) return

      orderData.value.items = prefill.map(item => {
        const newItem = createEmptyItem()
        newItem.productId = item.productId
        // Prefer the full catalog entry (current name, SKU, stock) over the
        // partial product info passed in by the caller.
        const catalogProduct = browseProducts.value.find(p => p.product_id === item.productId)
        newItem.selectedProduct = catalogProduct || item.selectedProduct || null
        newItem.quantity = item.quantity ?? null
        newItem.estimatedCost = item.estimatedCost ?? null
        // Expiry intentionally left blank — applies to a fresh delivery
        newItem.totalCost = (newItem.quantity || 0) * (newItem.estimatedCost || 0)
        return newItem
      })
    }
    
    // ================ ITEM MANAGEMENT ================

    function validateItem(index) {
      const item = orderData.value.items[index]
      const errors = {}

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
      // Run item-level validation first so quantity errors surface inline
      validateAllItems()

      // Collect form-level errors
      const errors = {}
      if (!orderData.value.expectedDeliveryDate) {
        errors.expectedDelivery = 'Expected delivery date is required'
      }
      if (orderData.value.items.length === 0) {
        errors.noItems = 'Select at least one product from the catalog'
      }
      const hasItemErrors = orderData.value.items.some(
        item => item.errors && Object.keys(item.errors).length > 0
      )

      formErrors.value = errors

      if (Object.keys(errors).length > 0 || hasItemErrors) return

      saving.value = true

      try {
        if (!props.supplier?.id) {
          showError('Supplier information is required to create an order')
          return
        }

        const itemsToProcess = validItems.value
        const results = { successful: [], failed: [] }

        // Batch number auto-generated — used as the supplier lot reference on both
        // the shipment record and every batch so they're traceable together
        const batchNumber = generateBatchNumber()

        // Step 1: Create a shipment record that groups all batches in this order
        let shipmentId = null
        try {
          const shipment = await createShipment({
            supplier_id: props.supplier.id,
            batch_number: batchNumber,
            shipment_date: orderData.value.orderDate,
            expected_delivery_date: orderData.value.expectedDeliveryDate,
            status: 'pending',
            notes: orderData.value.notes || null
          })
          shipmentId = shipment?.shipment_id
        } catch (error) {
          console.error('Error creating shipment:', error)
          showError('Failed to create shipment record. Please try again.')
          return
        }

        // Step 2: Create a pending batch per item, all linked to the shipment
        for (const item of itemsToProcess) {
          try {
            const batchData = {
              product_id: `PROD-${item.productId}`,
              supplier_id: props.supplier.id,
              batch_number: batchNumber,
              shipment_id: shipmentId,
              quantity_received: item.quantity,
              cost_price: item.estimatedCost || 0,
              expiry_date: item.expectedExpiryDate || null,
              date_received: orderData.value.orderDate,
              status: 'pending'
            }

            const response = await createBatch(batchData)
            results.successful.push({ product: item.selectedProduct?.product_name, batch: response })
          } catch (error) {
            console.error('Error creating batch for item:', item, error)
            results.failed.push({ product: item.selectedProduct?.product_name, error: error.message })
          }
        }

        // Let the parent (SupplierDetails) show the result toast to avoid duplicates
        emit('saved', {
          shipmentId,
          supplierId: props.supplier?.id,
          supplierName: props.supplier?.name,
          results
        })

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
        orderDate: new Date().toISOString().split('T')[0],
        expectedDeliveryDate: '',
        notes: '',
        items: []
      }
      filterCategoryId.value = ''
      filterSubcategoryId.value = ''
      productSearchQuery.value = ''
      formErrors.value = {}
      saving.value = false
    }

    // ================ LIFECYCLE ================

    onMounted(async () => {
      // Component re-mounts each time the modal opens (v-if), so this also
      // serves as the per-open initialization hook. Items are seeded by the
      // prefillItems watcher below; here we just load the catalog so the
      // selectedProduct on each item can be hydrated against fresh data.
      try {
        await Promise.all([fetchCategories(), loadAllProducts()])
      } catch (error) {
        console.error('Error loading initial data:', error)
        showError('Failed to load catalog data')
      }
      applyPrefillItems()
    })

    // Seed orderData from prefillItems on mount and whenever the prop changes.
    // immediate:true handles the initial mount case (prop is set before setup
    // returns, so onMounted alone could miss timing).
    watch(
      () => props.prefillItems,
      (items) => {
        if (items && items.length) applyPrefillItems()
      },
      { immediate: true, deep: true }
    )

    return {
      // Data
      orderData,
      saving,
      categories,

      // Browser state
      filterCategoryId,
      filterSubcategoryId,
      productSearchQuery,
      browseProducts,
      isBrowseLoading,

      // Computed
      filterSubcategories,
      filteredBrowseProducts,
      validItemsCount,
      totalQuantity,
      uniqueProductsCount,
      grandTotal,

      // Form errors
      formErrors,

      // Methods
      getSupplierTypeLabel,
      formatCurrency,
      onFilterCategoryChange,
      isProductSelected,
      toggleProduct,
      clearDeliveryError,
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

/* ── Modal Overlay ──────────────────────────────────────────────────────── */
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

/* ── Modal Content ──────────────────────────────────────────────────────── */
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

/* ── Modal Structure ────────────────────────────────────────────────────── */
.modern-order-modal {
  border-radius: 16px;
  border: none;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
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
  filter: var(--btn-close-filter, none);
}

.dark-theme .modal-header .btn-close {
  filter: invert(1);
}

.modal-header .btn-close:hover {
  opacity: 1;
  transform: scale(1.05);
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

/* ── Modal Icon ─────────────────────────────────────────────────────────── */
.modal-icon-pending {
  width: 48px;
  height: 48px;
  background-color: var(--surface-tertiary);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-accent);
}

/* ── Section headings inside card slots ─────────────────────────────────── */
.section-heading {
  color: var(--text-primary);
  font-weight: 600;
  letter-spacing: 0.01em;
}

.card-template .form-label {
  font-weight: 500;
  color: var(--text-secondary);
}

/* ── Supplier Detail Rows ───────────────────────────────────────────────── */
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

/* ── Product Browser ────────────────────────────────────────────────────── */
.product-browser-list {
  max-height: 340px;
  overflow-y: auto;
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
}

.browser-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  color: var(--text-tertiary);
  text-align: center;
}

.product-browser-item {
  display: flex;
  align-items: center;
  padding: 0.6rem 0.75rem;
  cursor: pointer;
  border-bottom: 1px solid var(--border-secondary);
  transition: background-color 0.15s ease;
}

.product-browser-item:last-child {
  border-bottom: none;
}

.product-browser-item:hover {
  background-color: var(--state-hover);
}

.product-browser-item.is-selected {
  background-color: var(--state-selected);
}

.product-browser-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.3;
}

.product-browser-meta {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  margin-top: 0.1rem;
}

/* ── Selected Items / Checkout ──────────────────────────────────────────── */
.checkout-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  color: var(--text-tertiary);
  text-align: center;
  min-height: 200px;
  border-radius: 8px;
  border: 2px dashed transparent;
  transition: border-color 0.2s ease;
}

.checkout-empty-state.has-error {
  border-color: var(--border-error);
}

.selected-items-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 2px;
}

.selected-item-card {
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: 10px;
  padding: 0.875rem 1rem;
  transition: border-color 0.15s ease;
}

.selected-item-card.has-error {
  border-color: var(--border-error);
  background-color: var(--status-error-bg);
}

.item-product-name {
  color: var(--text-primary);
  font-size: 0.9rem;
}

/* ── Order Summary Rows ─────────────────────────────────────────────────── */
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

/* ── Footer ─────────────────────────────────────────────────────────────── */
.sticky-footer {
  padding: 1.25rem 1.75rem 1.5rem 1.75rem;
  background-color: var(--surface-secondary);
  border-top: 1px solid var(--border-primary);
  flex-shrink: 0;
  position: sticky;
  bottom: 0;
  z-index: 10;
  box-shadow: var(--shadow-md);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* ── Custom Scrollbar ───────────────────────────────────────────────────── */
.modal-content::-webkit-scrollbar {
  width: 6px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--surface-secondary);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--border-accent);
}

/* Prevent body scroll when modal is open */
body:has(.modal-overlay) {
  overflow: hidden !important;
}

/* ── Responsive ─────────────────────────────────────────────────────────── */
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

  .sticky-footer {
    padding: 1rem 1.5rem 1.5rem 1.5rem !important;
  }

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
</style>