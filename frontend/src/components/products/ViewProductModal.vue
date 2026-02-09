<template>
  <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header bg-light border-bottom">
        <h2 class="text-tertiary-dark">Product Details</h2>
        <button class="btn-close" @click="closeModal" aria-label="Close">
          ✕
        </button>
      </div>

      <div v-if="product" class="product-view">
        <!-- Product Header -->
        <div class="product-header pb-3 mb-4 border-bottom">
          <div class="product-main-info">
            <h3 class="product-name text-tertiary-dark">{{ product.product_name }}</h3>
            <div class="product-badges d-flex gap-2 flex-wrap">
              <span :class="getStatusBadgeClass(product.status)">
                {{ formatStatus(product.status) }}
              </span>
              <span :class="getCategoryBadgeClass(product.category_id)">
                {{ getCategoryName(product.category_id) }}
              </span>
              <span v-if="product.is_taxable" class="badge text-bg-secondary">
                Taxable
              </span>
            </div>
          </div>
          <div class="product-actions">
            <button @click="handleEdit(onEdit)" class="btn btn-edit btn-with-icon">
              <Edit :size="16" />
              Edit Product
            </button>
          </div>
        </div>

        <!-- Product Details Grid -->
        <div class="product-details">
          <div class="details-section mb-4">
            <h4 class="section-title text-tertiary-dark">Basic Information</h4>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">Product ID</label>
                  <div class="detail-value font-monospace bg-light p-2 rounded">{{ product._id }}</div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">SKU</label>
                  <div class="detail-value font-monospace bg-light p-2 rounded">{{ product.SKU }}</div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">Barcode</label>
                  <div class="detail-value font-monospace bg-light p-2 rounded">{{ product.barcode || 'Not set' }}</div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">Unit</label>
                  <div class="detail-value">{{ product.unit }}</div>
                </div>
              </div>
              <div v-if="product.description" class="col-12">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">Description</label>
                  <div class="detail-value">{{ product.description }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="details-section mb-4">
            <h4 class="section-title text-tertiary-dark">Stock Information</h4>
            <div class="row g-3">
              <div class="col-md-4">
                <div class="card h-100" :class="stockCardClass">
                  <div class="card-body text-center">
                    <div class="stock-label text-uppercase text-tertiary-medium small">Current Stock</div>
                    <div class="stock-value display-6 fw-bold" :class="getStockClass(product)">{{ product.stock }}</div>
                    <div class="stock-unit text-tertiary-medium">{{ product.unit }}</div>
                  </div>
                </div>
              </div>
              <div class="col-md-4">
                <div class="card h-100" :class="thresholdCardClass">
                  <div class="card-body text-center">
                    <div class="stock-label text-uppercase text-tertiary-medium small">Low Stock Threshold</div>
                    <div class="stock-value display-6 fw-bold">{{ product.low_stock_threshold }}</div>
                    <div class="stock-unit text-tertiary-medium">{{ product.unit }}</div>
                  </div>
                </div>
              </div>
              <div class="col-md-4">
                <div class="card h-100" :class="statusCardClass">
                  <div class="card-body text-center">
                    <div class="stock-label text-uppercase text-tertiary-medium small">Stock Status</div>
                    <div class="mt-2">
                      <span :class="getStockStatusClass(product)">
                        {{ getStockStatusText(product) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="details-section mb-4">
            <h4 class="section-title text-tertiary-dark">Pricing Information</h4>
            <div class="row g-3">
              <div class="col-md-3">
                <div class="card bg-light">
                  <div class="card-body text-center">
                    <div class="price-label text-uppercase text-tertiary-medium small">Cost Price</div>
                    <div class="price-value h4 fw-bold text-tertiary-dark">₱{{ formatPrice(product.cost_price) }}</div>
                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="card bg-light">
                  <div class="card-body text-center">
                    <div class="price-label text-uppercase text-tertiary-medium small">Selling Price</div>
                    <div class="price-value h4 fw-bold text-tertiary-dark">₱{{ formatPrice(product.selling_price) }}</div>
                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="card bg-success-subtle border-success">
                  <div class="card-body text-center">
                    <div class="price-label text-uppercase text-success small">Profit Margin</div>
                    <div class="price-value h4 fw-bold text-success">{{ getProfitMargin(product) }}%</div>
                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="card bg-success-subtle border-success">
                  <div class="card-body text-center">
                    <div class="price-label text-uppercase text-success small">Profit per Unit</div>
                    <div class="price-value h4 fw-bold text-success">₱{{ getProfitPerUnit(product) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="details-section mb-4">
            <h4 class="section-title text-tertiary-dark">Date Information</h4>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">Date Received</label>
                  <div class="detail-value">{{ formatDate(product.date_received) }}</div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">Expiry Date</label>
                  <div class="detail-value" :class="getExpiryClass(product.expiry_date)">
                    {{ formatDate(product.expiry_date) }}
                    <small v-if="product.expiry_date" class="d-block text-tertiary-medium">
                      {{ getDaysUntilExpiry(product.expiry_date) }}
                    </small>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">Created At</label>
                  <div class="detail-value">{{ formatDateTime(product.created_at) }}</div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="detail-item">
                  <label class="form-label text-tertiary-medium">Last Updated</label>
                  <div class="detail-value">{{ formatDateTime(product.updated_at) }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="details-section">
            <h4 class="section-title text-tertiary-dark">Quick Actions</h4>
            <div class="row g-3">
              <div class="col-12">
                <button @click="handleRestock(onRestock)" class="btn btn-outline-info w-100 p-3 text-start">
                  <div class="d-flex align-items-center">
                    <Package :size="24" class="me-3" />
                    <div>
                      <div class="fw-semibold">Update Stock</div>
                      <small class="text-muted">Add, remove, or set stock quantity</small>
                    </div>
                  </div>
                </button>
              </div>
              <div class="col-12">
                <button @click="handleToggleStatus(onToggleStatus)" class="btn btn-outline-secondary w-100 p-3 text-start">
                  <div class="d-flex align-items-center">
                    <component 
                      :is="product.status === 'active' ? Lock : Unlock" 
                      :size="24" 
                      class="me-3" 
                    />
                    <div>
                      <div class="fw-semibold">{{ statusToggleText }}</div>
                      <small class="text-muted">{{ statusToggleSubtext }}</small>
                    </div>
                  </div>
                </button>
              </div>
              <div class="col-12">
                <button 
                  @click="handleGenerateBarcode(onGenerateBarcode)" 
                  class="btn btn-outline-primary w-100 p-3 text-start"
                  :disabled="!canGenerateBarcode"
                >
                  <div class="d-flex align-items-center">
                    <BarChart3 :size="24" class="me-3" />
                    <div>
                      <div class="fw-semibold">Generate Barcode</div>
                      <small class="text-muted">
                        {{ product.barcode ? 'Barcode already exists' : 'Create new barcode for product' }}
                      </small>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer bg-light border-top">
        <div class="d-flex gap-2 justify-content-end w-100">
          <button @click="closeModal" class="btn btn-cancel">
            Close
          </button>
          <button @click="handleEdit(onEdit)" class="btn btn-edit btn-with-icon">
            <Edit :size="16" />
            Edit Product
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useProducts } from '@/composables/api/useProducts'
import { onMounted, onBeforeUnmount } from 'vue'
import { Edit, Package, Lock, Unlock, BarChart3 } from 'lucide-vue-next'

export default {
  name: 'ViewProductModal',
  components: {
    Edit,
    Package,
    Lock,
    Unlock,
    BarChart3
  },
  emits: ['edit', 'restock', 'toggle-status', 'generate-barcode'],
  
  setup(props, { emit }) {
    const {
      // State
      showViewProductModal: show,
      viewProductModalProduct: product,
      
      // Computed
      stockCardClass,
      thresholdCardClass,
      statusCardClass,
      canGenerateBarcode,
      statusToggleText,
      statusToggleSubtext,
      
      // Actions
      openViewProductModal: openViewModal,
      closeViewProductModal: closeModal,
      handleViewProductEdit: handleEdit,
      handleViewProductRestock: handleRestock,
      handleViewProductToggleStatus: handleToggleStatus,
      handleViewProductGenerateBarcode: handleGenerateBarcode,
      
      // Helper methods
      getCategoryName,
      getStockClass,
      getStockStatusClass,
      getStockStatusText,
      getStatusBadgeClass,
      getCategoryBadgeClass,
      getExpiryClass,
      getDaysUntilExpiry,
      getProfitMargin,
      getProfitPerUnit,
      
      // Formatting methods
      formatPrice,
      formatStatus,
      formatDate,
      formatDateTime,
      
      // Utility methods
      setupViewProductKeyboardListeners: setupKeyboardListeners,
      cleanupViewProductKeyboardListeners: cleanupKeyboardListeners
    } = useProducts()
    
    // Setup keyboard listeners on mount
    onMounted(() => {
      setupKeyboardListeners()
    })
    
    // Cleanup on unmount
    onBeforeUnmount(() => {
      cleanupKeyboardListeners()
    })
    
    // Event handlers
    const onEdit = (productData) => {
      emit('edit', productData)
    }
    
    const onRestock = (productData) => {
      emit('restock', productData)
    }
    
    const onToggleStatus = (productData) => {
      emit('toggle-status', productData)
    }
    
    const onGenerateBarcode = (productData) => {
      emit('generate-barcode', productData)
    }
    
    const handleOverlayClick = () => {
      closeModal()
    }
    
    // Expose methods for parent component
    const openView = (productData) => {
      openViewModal(productData)
    }
    
    return {
      // State
      show,
      product,
      
      // Computed
      stockCardClass,
      thresholdCardClass,
      statusCardClass,
      canGenerateBarcode,
      statusToggleText,
      statusToggleSubtext,
      
      // Methods
      closeModal,
      handleOverlayClick,
      handleEdit,
      handleRestock,
      handleToggleStatus,
      handleGenerateBarcode,
      getCategoryName,
      getStockClass,
      getStockStatusClass,
      getStockStatusText,
      getStatusBadgeClass,
      getCategoryBadgeClass,
      getExpiryClass,
      getDaysUntilExpiry,
      getProfitMargin,
      getProfitPerUnit,
      formatPrice,
      formatStatus,
      formatDate,
      formatDateTime,
      
      // Event handlers
      onEdit,
      onRestock,
      onToggleStatus,
      onGenerateBarcode,
      
      // Exposed methods
      openView
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
  max-width: 900px;
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
  border-radius: 12px 12px 0 0;
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

.product-view {
  padding: 2rem;
}

.product-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.product-main-info {
  flex: 1;
}

.product-name {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
}

.product-actions {
  margin-left: 1rem;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--neutral);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item label {
  font-size: 0.875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-value {
  font-size: 1rem;
  font-weight: 500;
  color: var(--tertiary-dark);
}

.stock-label,
.price-label {
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.stock-value,
.price-value {
  margin-bottom: 0.25rem;
}

.stock-unit {
  margin-top: 0.25rem;
}

.modal-footer {
  padding: 1.5rem 2rem;
  border-radius: 0 0 12px 12px;
}

/* Custom text colors using colors.css variables */
.text-tertiary-dark {
  color: var(--tertiary-dark) !important;
}

.text-tertiary-medium {
  color: var(--tertiary-medium) !important;
}

/* Stock status colors */
.text-success {
  color: var(--success) !important;
}

.text-warning {
  color: var(--warning, #ffc107) !important;
}

.text-danger {
  color: var(--error) !important;
}

.text-info {
  color: var(--info) !important;
}

/* Background subtle colors */
.bg-success-subtle {
  background-color: var(--success-light) !important;
}

.bg-warning-subtle {
  background-color: var(--warning-light, #fff3cd) !important;
}

.bg-danger-subtle {
  background-color: var(--error-light) !important;
}

.bg-info-subtle {
  background-color: var(--info-light) !important;
}

.bg-primary-subtle {
  background-color: var(--primary-light) !important;
}

/* Border colors */
.border-success {
  border-color: var(--success) !important;
}

.border-warning {
  border-color: var(--warning, #ffc107) !important;
}

.border-danger {
  border-color: var(--error) !important;
}

.border-info {
  border-color: var(--info) !important;
}

.border-primary {
  border-color: var(--primary) !important;
}

/* Responsive Design */
@media (max-width: 768px) {
  .modal-content {
    margin: 1rem;
    max-height: calc(100vh - 2rem);
  }

  .modal-header {
    padding: 1rem 1.5rem;
  }

  .modal-header h2 {
    font-size: 1.25rem;
  }

  .product-view {
    padding: 1.5rem;
  }

  .product-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .product-actions {
    margin-left: 0;
  }

  .product-name {
    font-size: 1.5rem;
  }

  .modal-footer {
    padding: 1rem 1.5rem;
  }

  .modal-footer .d-flex {
    flex-direction: column-reverse;
    gap: 0.75rem;
  }

  .modal-footer .btn {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .modal-content {
    margin: 0.5rem;
    max-height: calc(100vh - 1rem);
    border-radius: 8px;
  }

  .modal-header {
    padding: 0.75rem 1rem;
    border-radius: 8px 8px 0 0;
  }

  .product-view {
    padding: 1rem;
  }

  .product-badges {
    flex-direction: column;
    align-items: flex-start;
  }

  .modal-footer {
    padding: 0.75rem 1rem;
    border-radius: 0 0 8px 8px;
  }
}

/* Custom scrollbar */
.modal-content::-webkit-scrollbar {
  width: 8px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--neutral-light);
  border-radius: 4px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--neutral-medium);
  border-radius: 4px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--neutral-dark);
}
</style>