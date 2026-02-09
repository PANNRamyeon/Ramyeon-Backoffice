<template>
  <div class="adjustments-container">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="text-primary mb-0">Stock Adjustments</h2>
      <div class="d-flex gap-2">
        <button class="btn btn-filter btn-sm" @click="toggleFilters">
          <Filter :size="16" class="me-1" />
          Filter
        </button>
        <!--<button class="btn btn-export btn-sm" @click="handleExport">
          <Download :size="16" class="me-1" />
          Export
        </button>-->
      </div>
    </div>

    <!-- Filter Panel -->
    <div v-if="showFilters" class="card-theme p-3 mb-4">
      <div class="row g-3">
        <div class="col-md-4">
          <label class="form-label text-secondary">Adjustment Type</label>
          <select v-model="selectedType" class="form-select">
            <option value="">All Types</option>
            <option value="sale">Sale</option>
            <option value="damage">Damage</option>
            <option value="theft">Theft/Loss</option>
            <option value="spoilage">Spoilage</option>
            <option value="return">Return</option>
            <option value="shrinkage">Shrinkage</option>
            <option value="correction">Correction</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label text-secondary">Date Filter</label>
          <input 
            v-model="dateRange" 
            type="date" 
            class="form-control"
          />
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
          <h4 class="text-info mb-0">{{ formatDate(lastAdjustmentDate) }}</h4>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="text-tertiary-medium mt-2">Loading adjustments...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger" role="alert">
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
          <th class="text-start">Batch Number</th>
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
            <span class="badge bg-danger">-{{ adjustment.quantity_used }}</span>
          </td>
          <td class="text-center">
            <span class="text-secondary fw-semibold">{{ adjustment.remaining_after }}</span>
          </td>
          <td>
            <span class="text-secondary">{{ formatAdjustedBy(adjustment.adjusted_by) }}</span>
          </td>
          <td>
            <span class="text-tertiary-medium">{{ adjustment.notes || '-' }}</span>
          </td>
          <td class="text-center">
            <button 
              @click="viewDetails(adjustment)"
              class="btn btn-outline-primary action-btn action-btn-view"
              title="View Details"
            >
              <Eye :size="14" />
            </button>
          </td>
        </tr>
      </template>
    </TableTemplate>

    <!-- Adjustment Details Modal -->
    <AdjustmentDetailsModal
      ref="adjustmentDetailsModal"
      @close="handleModalClose"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { Filter, Download, Eye, ClipboardList } from 'lucide-vue-next'
import TableTemplate from '@/components/common/TableTemplate.vue'
import AdjustmentDetailsModal from './AdjustmentDetailsModal.vue'
import { useBatches } from '@/composables/api/useBatches'

export default {
  name: 'ProductAdjustments',
  components: {
    TableTemplate,
    AdjustmentDetailsModal,
    Filter,
    Download,
    Eye,
    ClipboardList
  },
  props: {
    productId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const {
      batches,
      loading,
      error,
      fetchBatchesByProduct
    } = useBatches()

    const currentPage = ref(1)
    const itemsPerPage = 10
    const showFilters = ref(false)
    const selectedType = ref('')
    const dateRange = ref('')
    const adjustmentDetailsModal = ref(null)

    // Flatten all usage_history from all batches into one array
    const allAdjustments = computed(() => {
      const adjustments = []

      batches.value.forEach(batch => {
        if (batch.usage_history && batch.usage_history.length > 0) {
          batch.usage_history.forEach(entry => {
            adjustments.push({
              ...entry,
              batch_id: batch._id,
              batch_number: batch.batch_number,
              id: `${batch._id}-${entry.timestamp}` // Unique ID
            })
          })
        }
      })
      
      // Sort by timestamp (newest first)
      return adjustments.sort((a, b) => 
        new Date(b.timestamp) - new Date(a.timestamp)
      )
    })

    // Apply filters
    const filteredAdjustments = computed(() => {
      let result = allAdjustments.value
      
      if (selectedType.value) {
        result = result.filter(adj => adj.adjustment_type === selectedType.value)
      }
      
      if (dateRange.value) {
        const filterDate = new Date(dateRange.value)
        result = result.filter(adj => {
          const adjDate = new Date(adj.timestamp)
          return adjDate.toDateString() === filterDate.toDateString()
        })
      }
      
      return result
    })

    // Paginate filtered adjustments
    const paginatedAdjustments = computed(() => {
      const start = (currentPage.value - 1) * itemsPerPage
      const end = start + itemsPerPage
      return filteredAdjustments.value.slice(start, end)
    })

    // Summary statistics
    const totalAdjustments = computed(() => allAdjustments.value.length)

    const totalUnitsAdjusted = computed(() => {
      return allAdjustments.value.reduce((sum, adj) => sum + (adj.quantity_used || 0), 0)
    })

    const mostCommonType = computed(() => {
      if (allAdjustments.value.length === 0) return 'N/A'
      
      const typeCounts = {}
      allAdjustments.value.forEach(adj => {
        const type = adj.adjustment_type || 'unknown'
        typeCounts[type] = (typeCounts[type] || 0) + 1
      })
      
      const sortedTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])
      return formatType(sortedTypes[0]?.[0] || 'N/A')
    })

    const lastAdjustmentDate = computed(() => {
      if (allAdjustments.value.length === 0) return null
      return allAdjustments.value[0]?.timestamp
    })

    // Methods
    const formatDate = (dateString) => {
      if (!dateString) return 'N/A'
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const formatTime = (dateString) => {
      if (!dateString) return ''
      return new Date(dateString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const formatType = (type) => {
      if (!type) return 'Unknown'
      return type.charAt(0).toUpperCase() + type.slice(1)
    }

    const formatAdjustedBy = (userId) => {
      if (!userId) return 'System'
      return userId
    }

    const getTypeBadgeClass = (type) => {
      const typeClasses = {
        'sale': 'badge bg-success',
        'damage': 'badge bg-danger',
        'theft': 'badge bg-danger',
        'spoilage': 'badge bg-warning',
        'return': 'badge bg-info',
        'shrinkage': 'badge bg-warning',
        'correction': 'badge bg-secondary'
      }
      return typeClasses[type] || 'badge bg-secondary'
    }

    const handlePageChange = (page) => {
      currentPage.value = page
    }

    const toggleFilters = () => {
      showFilters.value = !showFilters.value
    }

    const handleClearFilters = () => {
      selectedType.value = ''
      dateRange.value = ''
      showFilters.value = false
    }

    const handleExport = () => {
      // TODO: Implement export functionality
    }

    const viewDetails = (adjustment) => {
      adjustmentDetailsModal.value?.open(adjustment)
    }

    const handleModalClose = () => {
      // Refresh if needed
    }

    // Initialize data
    const loadData = async () => {
      try {
        await fetchBatchesByProduct(props.productId)
      } catch (err) {
        console.error('❌ Failed to load batches:', err)
      }
    }

    // Watch for product ID changes
    watch(() => props.productId, (newId) => {
      if (newId) {
        currentPage.value = 1
        loadData()
      }
    })

    onMounted(() => {
      loadData()
    })

    return {
      // State
      batches,
      loading,
      error,
      currentPage,
      itemsPerPage,
      showFilters,
      selectedType,
      dateRange,
      adjustmentDetailsModal,
      
      // Computed
      allAdjustments,
      filteredAdjustments,
      paginatedAdjustments,
      totalAdjustments,
      totalUnitsAdjusted,
      mostCommonType,
      lastAdjustmentDate,
      
      // Methods
      formatDate,
      formatTime,
      formatType,
      formatAdjustedBy,
      getTypeBadgeClass,
      handlePageChange,
      toggleFilters,
      handleClearFilters,
      handleExport,
      viewDetails,
      handleModalClose
    }
  }
}
</script>

<style scoped>
.adjustments-container {
  padding: 1.5rem;
}

.form-check-input {
  cursor: pointer;
  margin-top: 0;
}

.opacity-50 {
  opacity: 0.5;
}
</style>