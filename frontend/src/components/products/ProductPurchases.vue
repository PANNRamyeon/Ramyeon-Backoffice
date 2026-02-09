<template>
  <div class="purchases-container">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="text-primary mb-0">Purchase History</h2>
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
          <label class="form-label text-secondary">Status</label>
          <select v-model="filters.status" class="form-select">
            <option :value="null">All Statuses</option>
            <option value="active">Active</option>
            <option value="depleted">Depleted</option>
            <option value="expired">Expired</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label text-secondary">Expiring Soon</label>
          <div class="d-flex gap-2 align-items-center">
            <input 
              type="checkbox" 
              v-model="filters.expiringSoon" 
              class="form-check-input"
            />
            <input 
              v-if="filters.expiringSoon"
              v-model.number="filters.daysAhead" 
              type="number" 
              class="form-control form-control-sm"
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
          <h4 class="text-info mb-0">{{ formatDate(lastPurchaseDate) }}</h4>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="text-tertiary-medium mt-2">Loading purchase history...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger" role="alert">
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
        
        <tr v-for="batch in paginatedBatches" :key="batch._id">
          <td>
            <span class="fw-semibold text-accent">{{ batch.batch_number }}</span>
          </td>
          <td>
            <span class="text-secondary">{{ formatDate(batch.date_received) }}</span>
          </td>
          <td>
            <span class="text-secondary" :class="getExpiryClass(batch.expiry_date)">
              {{ formatDate(batch.expiry_date) }}
            </span>
          </td>
          <td class="text-center">
            <span class="badge bg-primary">{{ batch.quantity_received || 0 }}</span>
          </td>
          <td class="text-center">
            <span class="badge" :class="getQuantityBadgeClass(batch)">
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
                class="btn btn-outline-primary action-btn action-btn-view"
                title="View Details"
              >
                <Eye :size="14" />
              </button>
              <button 
                v-if="batch.status === 'active'"
                @click="adjustQuantity(batch)"
                class="btn btn-outline-secondary action-btn action-btn-edit"
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

<script>
import { ref, computed, onMounted, watch } from 'vue'
import TableTemplate from '@/components/common/TableTemplate.vue'
import { useBatches } from '@/composables/api/useBatches'

// ✅ Import the new BatchDetailsModal
import BatchDetailsModal from '@/components/products/BatchDetailsModal.vue'

// ✅ Import your existing StockUpdateModal
import StockUpdateModal from '@/components/products/StockUpdateModal.vue'

export default {
  name: 'ProductPurchases',
  components: {
    TableTemplate,
    BatchDetailsModal,
    StockUpdateModal
  },
  props: {
    productId: {
      type: String,
      required: true
    },
    product: {        // ✅ NEW
      type: Object,
      required: true
    }
  },
  setup(props) {
    // --- Composables ---
    const {
      batches,
      loading,
      error,
      filters,
      hasActiveFilters,
      fetchBatchesByProduct,
      clearFilters
    } = useBatches()

    // --- Pagination ---
    const currentPage = ref(1)
    const itemsPerPage = 10
    const showFilters = ref(false)

    // --- Modal Refs ---
    const batchDetailsModal = ref(null)
    const stockUpdateModal = ref(null)

    // --- Set initial product filter ---
    filters.productId = props.productId

    // --- Computed Data ---
    const paginatedBatches = computed(() => {
      const start = (currentPage.value - 1) * itemsPerPage
      const end = start + itemsPerPage
      return batches.value.slice(start, end)
    })

    const totalActiveQuantity = computed(() => {
      const now = new Date()
      return batches.value
        .filter(batch => {
          // Only count active batches that are not expired
          if (batch.status !== 'active') return false
          
          // Exclude expired batches based on expiry_date
          if (batch.expiry_date) {
            const expiryDate = new Date(batch.expiry_date)
            if (expiryDate < now) return false
          }
          
          return true
        })
        .reduce((sum, batch) => sum + (batch.quantity_remaining || 0), 0)
    })

    const totalCost = computed(() => {
      return batches.value.reduce((sum, batch) => {
        const batchCost = (batch.cost_price || 0) * (batch.quantity_received || 0)
        return sum + batchCost
      }, 0)
    })

    const lastPurchaseDate = computed(() => {
      if (batches.value.length === 0) return null
      const sorted = [...batches.value].sort((a, b) =>
        new Date(b.date_received) - new Date(a.date_received)
      )
      return sorted[0]?.date_received
    })

    // --- Utility Functions ---
    const calculateTotalCost = (batch) => {
      return (batch.cost_price || 0) * (batch.quantity_received || 0)
    }

    const formatDate = (dateString) => {
      if (!dateString) return 'N/A'
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const formatPrice = (price) => parseFloat(price || 0).toFixed(2)

    const formatStatus = (status) =>
      status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown'

    const getStatusBadgeClass = (status) => {
      const statusClasses = {
        'active': 'badge bg-success',
        'depleted': 'badge bg-warning',
        'expired': 'badge bg-danger'
      }
      return statusClasses[status] || 'badge bg-secondary'
    }

    const getQuantityBadgeClass = (batch) => {
      if (batch.status === 'depleted') return 'bg-danger'
      if (batch.status === 'expired') return 'bg-secondary'

      const percentage = ((batch.quantity_remaining || 0) / (batch.quantity_received || 1)) * 100
      if (percentage <= 20) return 'bg-danger'
      if (percentage <= 50) return 'bg-warning'
      return 'bg-success'
    }

    const getExpiryClass = (expiryDate) => {
      if (!expiryDate) return ''
      const now = new Date()
      const expiry = new Date(expiryDate)
      const daysUntilExpiry = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24))
      if (daysUntilExpiry < 0) return 'text-error'
      if (daysUntilExpiry <= 7) return 'text-warning'
      return ''
    }

    // --- Table Pagination & Filters ---
    const handlePageChange = (page) => {
      currentPage.value = page
    }

    const toggleFilters = () => {
      showFilters.value = !showFilters.value
    }

    const handleClearFilters = () => {
      clearFilters()
      filters.productId = props.productId // keep product context
      showFilters.value = false
    }

    // --- Actions ---
    const handleExport = () => {
      // Optional: Connect to CSV export logic here
    }

    const viewDetails = (batch) => {
      // ✅ Opens batch details modal
      batchDetailsModal.value?.open(batch)
    }

    const adjustQuantity = () => {
      stockUpdateModal.value?.openStock?.(props.product)
    }

    // --- Data Initialization ---
    const loadData = async () => {
      try {
        await fetchBatchesByProduct(props.productId)
      } catch (err) {
        console.error('Failed to load batches:', err)
      }
    }

    // Watch for product changes
    watch(() => props.productId, (newId) => {
      if (newId) {
        filters.productId = newId
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
      filters,
      hasActiveFilters,
      currentPage,
      itemsPerPage,
      showFilters,

      // Modals
      batchDetailsModal,
      stockUpdateModal,

      // Computed
      paginatedBatches,
      totalActiveQuantity,
      totalCost,
      lastPurchaseDate,

      // Methods
      calculateTotalCost,
      formatDate,
      formatPrice,
      formatStatus,
      getStatusBadgeClass,
      getQuantityBadgeClass,
      getExpiryClass,
      handlePageChange,
      toggleFilters,
      handleClearFilters,
      handleExport,
      viewDetails,
      adjustQuantity
    }
  }
}
</script>


<style scoped>
.purchases-container {
  padding: 1.5rem;
}

.form-check-input {
  cursor: pointer;
  margin-top: 0;
}

.opacity-50 {
  opacity: 0.5;
}

/* Utility classes for dynamic text colors */
.text-warning {
  color: var(--status-warning) !important;
}

.text-error {
  color: var(--status-error) !important;
}
</style>