<template>
  <div class="overview-container">
    <!-- Loading State -->
    <div v-if="isLoading && !currentProduct" class="text-center py-5" style="grid-column: 1 / -1;">
      <div class="spinner-border text-accent" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="text-tertiary-medium mt-2">Loading product details...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage && !currentProduct" class="status-error" role="alert" style="grid-column: 1 / -1;">
      <strong>Error:</strong> {{ errorMessage }}
      <button @click="retryLoad" class="btn btn-save btn-sm ms-3">Retry</button>
    </div>

    <!-- Content -->
    <template v-else-if="currentProduct">
      <!-- Left Column -->
      <div class="details-column">
        <div class="card-theme p-4">
          <h3 class="text-primary mb-3">Primary Details</h3>

          <div class="row mb-3">
            <div class="col-6">
              <small class="text-tertiary d-block">Product Name</small>
              <span class="text-secondary">{{ currentProduct.product_name }}</span>
            </div>
            <div class="col-6">
              <small class="text-tertiary d-block">SKU</small>
              <span class="text-secondary">{{ currentProduct.sku || currentProduct.SKU || 'N/A' }}</span>
            </div>
          </div>

          <div class="row mb-3">
            <div class="col-6">
              <small class="text-tertiary d-block">Category</small>
              <span class="text-secondary">{{ categoryName }}</span>
            </div>
            <div class="col-6">
              <small class="text-tertiary d-block">Subcategory</small>
              <span class="text-secondary">{{ currentProduct.subcategory_name || 'General' }}</span>
            </div>
          </div>

          <div class="row mb-3">
            <div class="col-6">
              <small class="text-tertiary d-block">Low Stock Threshold</small>
              <span class="text-secondary">{{ currentProduct.low_stock_threshold || 0 }}</span>
            </div>
            <div class="col-6">
              <small class="text-tertiary d-block">Nearest Expiry</small>
              <span class="text-secondary">{{ formatDate(nearestExpiryDate) }}</span>
            </div>
          </div>

          <div class="row">
            <div class="col-6">
              <small class="text-tertiary d-block">Created</small>
              <span class="text-secondary">{{ formatDate(currentProduct.created_at) }}</span>
            </div>
            <div class="col-6">
              <small class="text-tertiary d-block">Status</small>
              <span :class="getStatusBadgeClass(currentProduct.status)">
                {{ formatStatus(currentProduct.status) }}
              </span>
            </div>
          </div>
        </div>

        <div class="card-theme p-4">
          <h3 class="text-primary mb-3">Supplier Details</h3>
          <div class="row">
            <div class="col-6">
              <small class="text-tertiary d-block">Supplier</small>
              <span class="text-secondary">{{ resolvedSupplierName }}</span>
            </div>
            <div class="col-6">
              <small class="text-tertiary d-block">Barcode</small>
              <span class="text-secondary">{{ currentProduct.barcode || 'No barcode' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="sidebar-column">
        <div class="card-theme p-3 text-center">
          <div v-if="currentProduct.image_url" class="image-wrapper">
            <img :src="currentProduct.image_url" :alt="currentProduct.product_name" class="product-image" />
          </div>
          <div v-else class="image-placeholder">
            <Package :size="48" class="text-tertiary-medium" />
            <p class="text-tertiary-medium mt-2 mb-0">{{ currentProduct.product_name }}</p>
          </div>
          <button class="btn btn-edit btn-sm mt-3 w-100" @click="$emit('change-image')">
            Change Image
          </button>
        </div>

        <div class="card-theme p-4">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="text-primary mb-0">Stock Information</h5>
            <button class="btn btn-edit btn-sm" @click="$emit('adjust-stock')">
              Adjust Stock
            </button>
          </div>

          <div class="d-flex justify-content-between align-items-center mb-2">
            <small class="text-tertiary">Current Stock</small>
            <span :class="getStockClass(currentStock)" class="fw-semibold fs-5">
              {{ currentStock }} {{ currentProduct.unit }}
            </span>
          </div>

          <div class="d-flex justify-content-between mb-2">
            <small class="text-tertiary">Low Stock Threshold</small>
            <span class="text-secondary fw-semibold">{{ currentProduct.low_stock_threshold || 10 }}</span>
          </div>

          <div class="d-flex justify-content-between mb-2">
            <small class="text-tertiary">Cost Price</small>
            <span class="text-secondary fw-semibold">₱{{ formatPrice(averageCostPrice) }}</span>
          </div>

          <div class="d-flex justify-content-between mb-2">
            <small class="text-tertiary">Selling Price</small>
            <div class="d-flex flex-column align-items-end">
              <span v-if="hasActivePromotion" class="text-tertiary text-decoration-line-through small">
                ₱{{ formatPrice(currentProduct.selling_price) }}
              </span>
              <span class="text-secondary fw-semibold">₱{{ formatPrice(effectiveSellingPrice) }}</span>
            </div>
          </div>

          <div v-if="hasActivePromotion" class="promotion-badge mb-2">
            <CheckCircle :size="14" class="me-1" />
            {{ activePromotion.name }}
          </div>

          <div class="d-flex justify-content-between mb-2">
            <small class="text-tertiary">Profit Margin</small>
            <span :class="profitMarginClass" class="fw-semibold">{{ profitMargin }}%</span>
          </div>

          <div class="d-flex justify-content-between align-items-center">
            <small class="text-tertiary">Unit Type</small>
            <span class="text-accent fw-semibold">{{ currentProduct.unit || 'pcs' }}</span>
          </div>

          <div v-if="isLowStock" class="low-stock-alert mt-3 d-flex align-items-center gap-2">
            <AlertTriangle :size="16" />
            <small>Low stock alert!</small>
          </div>
        </div>
      </div>
    </template>

    <!-- Not Found -->
    <div v-else class="text-center py-5" style="grid-column: 1 / -1;">
      <Package :size="64" class="text-tertiary-medium mb-3" />
      <h5 class="text-tertiary">Product not found</h5>
      <p class="text-tertiary-medium">The requested product could not be loaded.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Package, CheckCircle, AlertTriangle } from 'lucide-vue-next'
import { useProducts } from '@/composables/api/useProducts.js'
import { useBatches } from '@/composables/api/useBatches.js'
import { useCategories } from '@/composables/api/useCategories.js'
import { useSuppliers } from '@/composables/api/useSuppliers.js'

const props = defineProps({
  productId: { type: String, required: true }
})

defineEmits(['adjust-stock', 'change-image', 'reorder', 'view-history'])

const { currentProduct, loading: productLoading, error: productError, fetchProductById } = useProducts()
const { batches, loading: batchLoading, error: batchError, fetchBatchesByProduct } = useBatches()
const { currentCategory, fetchCategoryById } = useCategories()
const { suppliers, fetchSuppliers } = useSuppliers()

const activePromotion = ref(null)

const isLoading = computed(() => productLoading.value || batchLoading.value)

const errorMessage = computed(() => {
  if (productError.value && !productError.value.includes('aborted')) return productError.value
  if (batchError.value && !batchError.value.includes('aborted')) return batchError.value
  return null
})

// ===================== STOCK =====================

// total_stock is the authoritative value maintained by the backend via batch sync.
// Use it directly; batch data is used for pricing/expiry details, not stock count.
const currentStock = computed(() => currentProduct.value?.total_stock ?? 0)

// ===================== PRICING =====================

const averageCostPrice = computed(() => {
  const now = new Date()
  const usable = batches.value.filter(
    b => USABLE_STATUSES.has(b.status) && (b.quantity_remaining > 0) && (!b.expiry_date || new Date(b.expiry_date) >= now)
  )

  if (usable.length > 0) {
    // FEFO: pick the batch with the nearest expiry (same batch that would be consumed first)
    const fefo = [...usable].sort((a, b) => {
      if (!a.expiry_date && !b.expiry_date) return 0
      if (!a.expiry_date) return 1
      if (!b.expiry_date) return -1
      return new Date(a.expiry_date) - new Date(b.expiry_date)
    })
    return fefo[0]?.cost_price || currentProduct.value?.cost_price || 0
  }

  // Fallback: most recently received batch, then product cost price
  if (batches.value.length > 0) {
    const latest = [...batches.value].sort((a, b) => new Date(b.date_received) - new Date(a.date_received))
    return latest[0]?.cost_price || currentProduct.value?.cost_price || 0
  }

  return currentProduct.value?.cost_price || 0
})

const hasActivePromotion = computed(() => activePromotion.value !== null)

const effectiveSellingPrice = computed(() => {
  const base = currentProduct.value?.selling_price || 0
  if (hasActivePromotion.value && activePromotion.value.discount_percentage)
    return base - (base * activePromotion.value.discount_percentage) / 100
  return base
})

const profitMargin = computed(() => {
  if (!effectiveSellingPrice.value || !averageCostPrice.value) return '0.00'
  const p = effectiveSellingPrice.value - averageCostPrice.value
  return ((p / effectiveSellingPrice.value) * 100).toFixed(2)
})

const profitMarginClass = computed(() => {
  const margin = parseFloat(profitMargin.value)
  if (margin < 0) return 'text-error'
  if (margin < 10) return 'text-warning'
  return 'text-success'
})

// ===================== BATCH INFO =====================

const USABLE_STATUSES = new Set(['active', 'low_stock', 'expiring_soon'])

const nearestExpiryDate = computed(() => {
  const now = new Date()
  const usable = batches.value.filter(
    b => USABLE_STATUSES.has(b.status) && b.expiry_date && new Date(b.expiry_date) >= now
  )
  if (!usable.length) return null
  return [...usable].sort((a, b) => new Date(a.expiry_date) - new Date(b.expiry_date))[0]?.expiry_date
})

// ===================== SUPPLIER =====================

const resolvedSupplierName = computed(() => {
  if (!batches.value.length) return 'No supplier specified'
  const sorted = [...batches.value].sort((a, b) => new Date(b.date_received) - new Date(a.date_received))
  const supplierId = sorted[0]?.supplier_id
  if (!supplierId) return 'No supplier specified'
  const match = suppliers.value.find(s => s.supplier_id === supplierId)
  if (!match) return 'N/A'
  return match.supplier_name || match.name || 'N/A'
})

// ===================== CATEGORY =====================

const categoryName = computed(() => {
  if (!currentProduct.value?.category_id) return 'Uncategorized'
  return currentCategory.value?.category_name || currentProduct.value.category_id
})

// ===================== STATUS =====================

const isLowStock = computed(() => {
  const threshold = currentProduct.value?.low_stock_threshold || 0
  return currentStock.value > 0 && currentStock.value <= threshold
})

// ===================== METHODS =====================

const formatPrice = (price) => parseFloat(price || 0).toFixed(2)

const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A'
  try {
    return new Date(dateStr).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return 'N/A'
  }
}

const formatStatus = (s) => (!s ? 'Unknown' : s.charAt(0).toUpperCase() + s.slice(1).replace('_', ' '))

const getStatusBadgeClass = (s) => ({
  active: 'status-badge status-badge-success',
  inactive: 'status-badge status-badge-neutral',
  low_stock: 'status-badge status-badge-warning',
  out_of_stock: 'status-badge status-badge-danger',
  discontinued: 'status-badge status-badge-danger',
  deleted: 'status-badge status-badge-danger'
}[s] || 'status-badge status-badge-neutral')

const getStockClass = (stock) => {
  const threshold = currentProduct.value?.low_stock_threshold || 0
  if (stock === 0) return 'text-error'
  if (stock <= threshold) return 'text-warning'
  return 'text-success'
}

// ===================== DATA LOADING =====================

const loadSuppliers = async () => {
  if (!suppliers.value.length) await fetchSuppliers()
}

const loadProductData = async () => {
  if (!props.productId) return
  try {
    await Promise.allSettled([
      fetchProductById(props.productId),
      fetchBatchesByProduct(props.productId)
    ])

    if (currentProduct.value?.category_id) {
      fetchCategoryById(currentProduct.value.category_id).catch(() => {})
    }
    activePromotion.value = currentProduct.value?.active_promotion || null
  } catch (err) {
    console.error('loadProductData error:', err)
  }
}

const retryLoad = () => loadProductData()

onMounted(() => {
  loadSuppliers()
  if (props.productId) loadProductData()
})

watch(() => props.productId, () => loadProductData())

defineExpose({ loadProductData })
</script>

<style scoped>
.overview-container {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
  max-width: 1400px;
}

.details-column,
.sidebar-column {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.image-wrapper {
  width: 100%;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--surface-secondary);
  border-radius: 0.5rem;
  overflow: hidden;
}

.product-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 0.5rem;
}

.image-placeholder {
  width: 100%;
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: var(--surface-secondary);
  border: 2px dashed var(--border-primary);
  border-radius: 0.5rem;
  color: var(--text-tertiary);
  padding: 1rem;
}

.promotion-badge {
  display: flex;
  align-items: center;
  padding: 0.5rem;
  background-color: var(--surface-secondary);
  color: var(--text-success, #16a34a);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 600;
  border: 1px solid var(--border-secondary);
}

.low-stock-alert {
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-secondary);
  border-left: 3px solid var(--status-warning, #f59e0b);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  color: var(--status-warning, #f59e0b);
  font-size: 0.875rem;
}

/* Status badges using theme vars */
.status-badge {
  display: inline-block;
  padding: 0.2em 0.6em;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 0.375rem;
  line-height: 1.4;
}

.status-badge-success {
  background-color: color-mix(in srgb, var(--status-success, #16a34a) 15%, transparent);
  color: var(--status-success, #16a34a);
}

.status-badge-warning {
  background-color: color-mix(in srgb, var(--status-warning, #f59e0b) 15%, transparent);
  color: var(--status-warning, #f59e0b);
}

.status-badge-danger {
  background-color: color-mix(in srgb, var(--status-error, #dc2626) 15%, transparent);
  color: var(--status-error, #dc2626);
}

.status-badge-neutral {
  background-color: var(--surface-tertiary);
  color: var(--text-tertiary);
}

.fs-5 { font-size: 1.25rem; }

@media (max-width: 1024px) {
  .overview-container { grid-template-columns: 1fr; gap: 1.5rem; }
}

@media (max-width: 768px) {
  .overview-container { gap: 1rem; }
  .details-column, .sidebar-column { gap: 1rem; }
  .row > .col-6 { flex: 0 0 100%; max-width: 100%; }
}
</style>
