<template>
  <div class="purchases-container">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="text-primary mb-0">Purchase History</h2>
      <div class="d-flex gap-2">
        <button class="btn btn-filter btn-sm" @click="toggleFilters">
          <Filter :size="16" class="me-1" />
          Filter
        </button>
      </div>
    </div>

    <!-- Filter Panel -->
    <div v-if="showFilters" class="card-theme p-3 mb-4">
      <div class="row g-3">
        <div class="col-md-4">
          <label class="form-label text-secondary">Status</label>
          <select v-model="filters.status" class="form-select input-theme">
            <option :value="null">All Statuses</option>
            <option value="active">Active</option>
            <option value="depleted">Depleted</option>
            <option value="expired">Expired</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label text-secondary">Expiring Soon</label>
          <div class="d-flex gap-2 align-items-center">
            <input type="checkbox" v-model="filters.expiringSoon" class="form-check-input" />
            <input
              v-if="filters.expiringSoon"
              v-model.number="filters.daysAhead"
              type="number"
              class="form-control input-theme form-control-sm"
              placeholder="Days"
              min="1"
            />
          </div>
        </div>
        <div class="col-md-4 d-flex align-items-end">
          <button @click="handleClearFilters" class="btn btn-cancel btn-sm w-100">
            Clear Filters
          </button>
        </div>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="row g-3 mb-4">
      <div class="col-md-3">
        <div class="card-theme p-3">
          <small class="text-tertiary-medium d-block mb-1">Total Batches</small>
          <h4 class="text-primary mb-0">{{ batches.length }}</h4>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card-theme p-3">
          <small class="text-tertiary-medium d-block mb-1">Active Stock</small>
          <h4 class="text-success mb-0">{{ totalActiveQuantity }} units</h4>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card-theme p-3">
          <small class="text-tertiary-medium d-block mb-1">Total Cost</small>
          <h4 class="text-secondary mb-0">₱{{ formatPrice(totalCost) }}</h4>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card-theme p-3">
          <small class="text-tertiary-medium d-block mb-1">Last Purchase</small>
          <h4 class="text-accent mb-0">{{ formatDate(lastPurchaseDate) }}</h4>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-accent" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="text-tertiary-medium mt-2">Loading purchase history...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="status-error" role="alert">
      <strong>Error:</strong> {{ error }}
    </div>

    <!-- Purchases Table -->
    <TableTemplate
      v-else
      :items-per-page="itemsPerPage"
      :total-items="batches.length"
      :current-page="currentPage"
      @page-changed="handlePageChange"
    >
      <template #header>
        <tr>
          <th class="text-start">Batch Number</th>
          <th class="text-start">Purchase Date</th>
          <th class="text-start">Expiry Date</th>
          <th class="text-center">Initial Qty</th>
          <th class="text-center">Current Qty</th>
          <th class="text-center">Unit Cost</th>
          <th class="text-center">Total Cost</th>
          <th class="text-center">Status</th>
          <th class="text-center">Actions</th>
        </tr>
      </template>

      <template #body>
        <tr v-if="paginatedBatches.length === 0">
          <td colspan="9" class="text-center py-4">
            <div class="text-tertiary-medium">
              <Package :size="48" class="mb-2 opacity-50" />
              <p class="mb-0">No purchase records found for this product</p>
              <small v-if="hasActiveFilters">Try adjusting your filters</small>
            </div>
          </td>
        </tr>

        <tr v-for="batch in paginatedBatches" :key="batch.batch_id">
          <td>
            <span class="fw-semibold text-accent">{{ batch.batch_number }}</span>
          </td>
          <td>
            <span class="text-secondary">{{ formatDate(batch.date_received) }}</span>
          </td>
          <td>
            <span class="text-secondary" :class="getExpiryClass(batch.expiry_date)">
              {{ batch.expiry_date ? formatDate(batch.expiry_date) : 'N/A' }}
            </span>
          </td>
          <td class="text-center">
            <span class="status-badge badge-lg status-badge-neutral">{{ batch.quantity_received || 0 }}</span>
          </td>
          <td class="text-center">
            <span class="status-badge badge-lg" :class="getQuantityBadgeClass(batch)">
              {{ batch.quantity_remaining || 0 }}
            </span>
          </td>
          <td class="text-center">
            <span class="text-secondary">₱{{ formatPrice(batch.cost_price) }}</span>
          </td>
          <td class="text-center">
            <span class="fw-semibold text-primary">₱{{ formatPrice(calculateTotalCost(batch)) }}</span>
          </td>
          <td class="text-center">
            <span :class="getStatusBadgeClass(batch.status)">
              {{ formatStatus(batch.status) }}
            </span>
          </td>
          <td class="text-center">
            <div class="d-flex gap-1 justify-content-center">
              <button
                @click="viewDetails(batch)"
                class="btn btn-edit btn-xs"
                title="View Details"
              >
                <Eye :size="14" />
              </button>
              <button
                v-if="batch.status === 'active'"
                @click="adjustQuantity(batch)"
                class="btn btn-export btn-xs"
                title="Adjust Quantity"
              >
                <Edit :size="14" />
              </button>
            </div>
          </td>
        </tr>
      </template>
    </TableTemplate>

    <BatchDetailsModal ref="batchDetailsModal" />
    <StockUpdateModal ref="stockUpdateModal" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Filter, Eye, Edit, Package } from 'lucide-vue-next'
import TableTemplate from '@/components/common/TableTemplate.vue'
import BatchDetailsModal from '@/components/products/BatchDetailsModal.vue'
import StockUpdateModal from '@/components/products/StockUpdateModal.vue'
import { useBatches } from '@/composables/api/useBatches'

const props = defineProps({
  productId: { type: String, required: true },
  product: { type: Object, required: true }
})

const { batches, loading, error, filters, hasActiveFilters, fetchBatchesByProduct, clearFilters } = useBatches()

const currentPage = ref(1)
const itemsPerPage = 10
const showFilters = ref(false)
const batchDetailsModal = ref(null)
const stockUpdateModal = ref(null)

const ACTIVE_STATUSES = new Set(['active', 'low_stock', 'expiring_soon'])

const sortedBatches = computed(() => {
  return [...batches.value].sort((a, b) => {
    // Priority 1: active batches on top, depleted/cancelled/exhausted/expired on bottom
    const aActive = ACTIVE_STATUSES.has(a.status) ? 0 : 1
    const bActive = ACTIVE_STATUSES.has(b.status) ? 0 : 1
    if (aActive !== bActive) return aActive - bActive

    // Priority 2: closest expiry first (no expiry goes after batches that have one)
    const aHasExpiry = !!a.expiry_date
    const bHasExpiry = !!b.expiry_date
    if (aHasExpiry && bHasExpiry) {
      const expiryDiff = new Date(a.expiry_date) - new Date(b.expiry_date)
      if (expiryDiff !== 0) return expiryDiff
    } else if (aHasExpiry !== bHasExpiry) {
      return aHasExpiry ? -1 : 1
    }

    // Priority 3: oldest purchase date first (FIFO)
    return new Date(a.date_received) - new Date(b.date_received)
  })
})

const paginatedBatches = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  return sortedBatches.value.slice(start, start + itemsPerPage)
})

const totalActiveQuantity = computed(() => {
  const now = new Date()
  return batches.value
    .filter(b => {
      if (b.status !== 'active') return false
      if (b.expiry_date && new Date(b.expiry_date) < now) return false
      return true
    })
    .reduce((sum, b) => sum + (b.quantity_remaining || 0), 0)
})

const totalCost = computed(() =>
  batches.value.reduce((sum, b) => sum + ((b.cost_price || 0) * (b.quantity_received || 0)), 0)
)

const lastPurchaseDate = computed(() => {
  if (!batches.value.length) return null
  return [...batches.value].sort((a, b) => new Date(b.date_received) - new Date(a.date_received))[0]?.date_received
})

const calculateTotalCost = (batch) => (batch.cost_price || 0) * (batch.quantity_received || 0)

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch { return 'N/A' }
}

const formatPrice = (price) => parseFloat(price || 0).toFixed(2)

const formatStatus = (status) =>
  status ? status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ') : 'Unknown'

const getStatusBadgeClass = (status) => ({
  active: 'status-badge status-badge-success',
  low_stock: 'status-badge status-badge-warning',
  expiring_soon: 'status-badge status-badge-warning',
  depleted: 'status-badge status-badge-neutral',
  expired: 'status-badge status-badge-danger',
  exhausted: 'status-badge status-badge-neutral'
}[status] || 'status-badge status-badge-neutral')

const getQuantityBadgeClass = (batch) => {
  if (batch.status === 'depleted' || batch.status === 'exhausted') return 'status-badge-danger'
  if (batch.status === 'expired') return 'status-badge-neutral'
  const pct = ((batch.quantity_remaining || 0) / (batch.quantity_received || 1)) * 100
  if (pct <= 20) return 'status-badge-danger'
  if (pct <= 50) return 'status-badge-warning'
  return 'status-badge-success'
}

const getExpiryClass = (expiryDate) => {
  if (!expiryDate) return ''
  const days = Math.ceil((new Date(expiryDate) - new Date()) / (1000 * 60 * 60 * 24))
  if (days < 0) return 'text-error'
  if (days <= 7) return 'text-warning'
  return ''
}

const handlePageChange = (page) => { currentPage.value = page }
const toggleFilters = () => { showFilters.value = !showFilters.value }
const handleClearFilters = () => {
  clearFilters()
  showFilters.value = false
  loadData()
}

const viewDetails = (batch) => batchDetailsModal.value?.open(batch)
const adjustQuantity = () => stockUpdateModal.value?.openStock?.(props.product)

const loadData = async () => {
  try {
    await fetchBatchesByProduct(props.productId)
  } catch (err) {
    console.error('Failed to load batches:', err)
  }
}

watch(() => props.productId, (newId) => {
  if (newId) {
    currentPage.value = 1
    loadData()
  }
})

onMounted(() => loadData())
</script>

<style scoped>
.badge-lg {
  font-size: 1rem;
  padding: 0.35em 0.85em;
  font-weight: 700;
  min-width: 2.5rem;
  text-align: center;
}

.purchases-container {
  padding: 1.5rem;
}

.status-badge {
  display: inline-block;
  padding: 0.2em 0.6em;
  font-size: 0.78rem;
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

.opacity-50 { opacity: 0.5; }

.btn-xs {
  padding: 0.2rem 0.4rem;
  font-size: 0.75rem;
}
</style>
