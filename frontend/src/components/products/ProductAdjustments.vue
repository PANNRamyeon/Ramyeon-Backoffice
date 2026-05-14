<template>
  <div class="adjustments-container">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="text-primary mb-0">Stock Adjustments</h2>
      <button class="btn btn-filter btn-sm" @click="toggleFilters">
        <Filter :size="16" class="me-1" />
        Filter
      </button>
    </div>

    <!-- Filter Panel -->
    <div v-if="showFilters" class="card-theme p-3 mb-4">
      <div class="row g-3">
        <div class="col-md-4">
          <label class="form-label text-secondary">Adjustment Type</label>
          <select v-model="selectedType" class="form-select input-theme">
            <option value="">All Types</option>
            <option value="sale">Sale</option>
            <option value="damage">Damage</option>
            <option value="theft">Theft / Loss</option>
            <option value="spoilage">Spoilage</option>
            <option value="return">Return</option>
            <option value="shrinkage">Shrinkage</option>
            <option value="correction">Correction</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label text-secondary">Date</label>
          <input v-model="dateRange" type="date" class="form-control input-theme" />
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
          <small class="text-tertiary-medium d-block mb-1">Total Adjustments</small>
          <h4 class="text-primary mb-0">{{ totalAdjustments }}</h4>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card-theme p-3">
          <small class="text-tertiary-medium d-block mb-1">Units Adjusted</small>
          <h4 class="text-error mb-0">{{ totalUnitsAdjusted }}</h4>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card-theme p-3">
          <small class="text-tertiary-medium d-block mb-1">Most Common</small>
          <h4 class="text-secondary mb-0">{{ mostCommonType }}</h4>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card-theme p-3">
          <small class="text-tertiary-medium d-block mb-1">Last Adjustment</small>
          <h4 class="text-accent mb-0">{{ formatDate(lastAdjustmentDate) }}</h4>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-accent" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="text-tertiary-medium mt-2">Loading adjustments...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="status-error" role="alert">
      <strong>Error:</strong> {{ error }}
    </div>

    <!-- Adjustments Table -->
    <TableTemplate
      v-else
      :items-per-page="itemsPerPage"
      :total-items="filteredAdjustments.length"
      :current-page="currentPage"
      @page-changed="handlePageChange"
    >
      <template #header>
        <tr>
          <th class="text-start">Date & Time</th>
          <th class="text-start">Batch</th>
          <th class="text-center">Type</th>
          <th class="text-center">Quantity</th>
          <th class="text-center">Remaining After</th>
          <th class="text-start">Adjusted By</th>
          <th class="text-start">Notes</th>
          <th class="text-center">Actions</th>
        </tr>
      </template>

      <template #body>
        <tr v-if="paginatedAdjustments.length === 0">
          <td colspan="8" class="text-center py-4">
            <div class="text-tertiary-medium">
              <ClipboardList :size="48" class="mb-2 opacity-50" />
              <p class="mb-0">No adjustments found for this product</p>
              <small v-if="selectedType || dateRange">Try adjusting your filters</small>
            </div>
          </td>
        </tr>

        <tr v-for="adjustment in paginatedAdjustments" :key="adjustment.id">
          <td>
            <div class="d-flex flex-column">
              <span class="fw-semibold text-secondary">{{ formatDate(adjustment.timestamp) }}</span>
              <small class="text-tertiary-medium">{{ formatTime(adjustment.timestamp) }}</small>
            </div>
          </td>
          <td>
            <span class="text-accent fw-semibold">{{ adjustment.batch_number }}</span>
          </td>
          <td class="text-center">
            <span :class="getTypeBadgeClass(adjustment.adjustment_type)">
              {{ formatType(adjustment.adjustment_type) }}
            </span>
          </td>
          <td class="text-center">
            <span class="status-badge status-badge-danger">-{{ adjustment.quantity_used }}</span>
          </td>
          <td class="text-center">
            <span class="text-secondary fw-semibold">{{ adjustment.remaining_after }}</span>
          </td>
          <td>
            <span class="text-secondary">{{ adjustment.adjusted_by || 'System' }}</span>
          </td>
          <td>
            <span class="text-tertiary-medium">{{ adjustment.notes || '—' }}</span>
          </td>
          <td class="text-center">
            <button
              @click="viewDetails(adjustment)"
              class="btn btn-edit btn-xs"
              title="View Details"
            >
              <Eye :size="14" />
            </button>
          </td>
        </tr>
      </template>
    </TableTemplate>

    <AdjustmentDetailsModal ref="adjustmentDetailsModal" @close="handleModalClose" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Filter, Eye, ClipboardList } from 'lucide-vue-next'
import TableTemplate from '@/components/common/TableTemplate.vue'
import AdjustmentDetailsModal from './AdjustmentDetailsModal.vue'
import { useBatches } from '@/composables/api/useBatches'

const props = defineProps({
  productId: { type: String, required: true }
})

const { batches, loading, error, fetchBatchesByProduct } = useBatches()

const currentPage = ref(1)
const itemsPerPage = 10
const showFilters = ref(false)
const selectedType = ref('')
const dateRange = ref('')
const adjustmentDetailsModal = ref(null)

const allAdjustments = computed(() => {
  const adjustments = []
  batches.value.forEach(batch => {
    if (batch.usage_history?.length) {
      batch.usage_history.forEach(entry => {
        adjustments.push({
          ...entry,
          batch_id: batch.batch_id,
          batch_number: batch.batch_number,
          id: `${batch.batch_id}-${entry.timestamp}`
        })
      })
    }
  })
  return adjustments.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
})

const filteredAdjustments = computed(() => {
  let result = allAdjustments.value
  if (selectedType.value) result = result.filter(adj => adj.adjustment_type === selectedType.value)
  if (dateRange.value) {
    const filterDate = new Date(dateRange.value)
    result = result.filter(adj => new Date(adj.timestamp).toDateString() === filterDate.toDateString())
  }
  return result
})

const paginatedAdjustments = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  return filteredAdjustments.value.slice(start, start + itemsPerPage)
})

const totalAdjustments = computed(() => allAdjustments.value.length)

const totalUnitsAdjusted = computed(() =>
  allAdjustments.value.reduce((sum, adj) => sum + (adj.quantity_used || 0), 0)
)

const mostCommonType = computed(() => {
  if (!allAdjustments.value.length) return 'N/A'
  const counts = {}
  allAdjustments.value.forEach(adj => {
    const t = adj.adjustment_type || 'unknown'
    counts[t] = (counts[t] || 0) + 1
  })
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'
  return formatType(top)
})

const lastAdjustmentDate = computed(() => allAdjustments.value[0]?.timestamp || null)

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch { return 'N/A' }
}

const formatTime = (dateString) => {
  if (!dateString) return ''
  try {
    return new Date(dateString).toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit' })
  } catch { return '' }
}

const formatType = (type) => {
  if (!type || type === 'N/A') return type || 'Unknown'
  return type.charAt(0).toUpperCase() + type.slice(1)
}

const getTypeBadgeClass = (type) => ({
  sale: 'status-badge status-badge-success',
  return: 'status-badge status-badge-info',
  damage: 'status-badge status-badge-danger',
  theft: 'status-badge status-badge-danger',
  spoilage: 'status-badge status-badge-warning',
  shrinkage: 'status-badge status-badge-warning',
  correction: 'status-badge status-badge-neutral'
}[type] || 'status-badge status-badge-neutral')

const handlePageChange = (page) => { currentPage.value = page }
const toggleFilters = () => { showFilters.value = !showFilters.value }
const handleClearFilters = () => {
  selectedType.value = ''
  dateRange.value = ''
  showFilters.value = false
}

const viewDetails = (adjustment) => adjustmentDetailsModal.value?.open(adjustment)
const handleModalClose = () => {}

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
.adjustments-container {
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

.status-badge-info {
  background-color: color-mix(in srgb, var(--text-accent, #6366f1) 15%, transparent);
  color: var(--text-accent, #6366f1);
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
