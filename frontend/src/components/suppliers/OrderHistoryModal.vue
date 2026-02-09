<template>
  <div class="container-fluid pt-2 pb-4 orders-history-page">
    <!-- Page Title with Back Button -->
    <div class="d-flex align-items-center mb-3">
      <button class="btn btn-outline-secondary btn-sm me-3" @click="goBack">
        <ArrowLeft :size="16" />
        Back
      </button>
      <h1 class="h3 fw-semibold text-primary-dark mb-0">Purchase Orders History</h1>
    </div>

    <!-- Summary Cards -->
    <div class="row mb-3" v-if="!loading">
      <div class="col-6 col-md-3 mb-2">
        <CardTemplate
          size="xs"
          border-color="success"
          border-position="start"
          title="Total Orders"
          :value="ordersComposable.totalOrders"
          value-color="success"
          subtitle="All Time"
        />
      </div>
      <div class="col-6 col-md-3 mb-2">
        <CardTemplate
          size="xs"
          border-color="warning"
          border-position="start"
          title="Active"
          :value="ordersComposable.activeOrdersCount"
          value-color="warning"
          subtitle="Currently Processing"
        />
      </div>
      <div class="col-6 col-md-3 mb-2">
        <CardTemplate
          size="xs"
          border-color="primary"
          border-position="start"
          title="This Month"
          :value="ordersComposable.thisMonthOrders"
          value-color="primary"
          subtitle="Monthly Orders"
        />
      </div>
      <div class="col-6 col-md-3 mb-2">
        <CardTemplate
          size="xs"
          border-color="info"
          border-position="start"
          title="Total Value"
          :value="`₱${formatCurrency(ordersComposable.totalOrderValue)}`"
          value-color="info"
          subtitle="All Orders"
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="mt-3 text-tertiary-medium">Loading orders...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="alert alert-danger text-center" role="alert">
      <p class="mb-3">{{ error }}</p>
      <button class="btn btn-primary" @click="refreshData">Try Again</button>
    </div>

    <!-- Filters and Actions -->
    <div v-if="!loading" class="action-bar-container mb-3">
      <div class="action-bar-controls">
        <div class="action-row">
          <!-- Left Side: Actions -->
          <div class="d-flex gap-2">
            <button class="btn btn-success btn-sm btn-with-icon-sm" @click="createNewOrder">
              <Plus :size="14" />
              NEW ORDER
            </button>
            <button class="btn btn-outline-secondary btn-sm" @click="exportOrders">
              EXPORT
            </button>
          </div>

          <!-- Right Side: Filters and Search -->
          <div class="d-flex align-items-center gap-2">
            <!-- Search Toggle -->
            <button 
              class="btn btn-secondary btn-sm"
              @click="toggleSearchMode"
              :class="{ 'active': searchMode }"
              style="height: calc(1.5em + 0.75rem + 2px); display: flex; align-items: center; justify-content: center; padding: 0 0.75rem;"
            >
              <Search :size="16" />
            </button>

            <!-- Filter Dropdowns -->
            <template v-if="!searchMode">
              <div class="filter-dropdown">
                <label class="filter-label">Status</label>
                <select 
                  class="form-select form-select-sm" 
                  v-model="ordersComposable.filters.status" 
                  @change="applyFilters"
                >
                  <option value="all">All Status</option>
                  <option value="pending">Pending Delivery</option>
                  <option value="confirmed">Partially Received</option>
                  <option value="delivered">Received</option>
                  <option value="cancelled">Depleted</option>
                </select>
              </div>

              <div class="filter-dropdown">
                <label class="filter-label">Supplier</label>
                <select 
                  class="form-select form-select-sm" 
                  v-model="ordersComposable.filters.supplier" 
                  @change="applyFilters"
                >
                  <option value="all">All Suppliers</option>
                  <option value="bravo_warehouse">Bravo Warehouse</option>
                  <option value="john_doe_supplies">John Doe Supplies</option>
                  <option value="san_juan_groups">San Juan Groups</option>
                  <option value="bagatayam_inc">Bagatayam Inc.</option>
                </select>
              </div>

              <div class="filter-dropdown">
                <label class="filter-label">Date Range</label>
                <select 
                  class="form-select form-select-sm" 
                  v-model="ordersComposable.filters.dateRange" 
                  @change="applyFilters"
                >
                  <option value="all">All Time</option>
                  <option value="today">Today</option>
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                  <option value="quarter">This Quarter</option>
                </select>
              </div>
            </template>

            <!-- Search Bar -->
            <div v-if="searchMode" class="search-container">
              <div class="position-relative">
                <input 
                  ref="searchInput"
                  v-model="ordersComposable.filters.search" 
                  @input="applyFilters"
                  type="text" 
                  class="form-control form-control-sm search-input"
                  placeholder="Search orders, suppliers..."
                />
                <button 
                  class="btn btn-sm btn-link position-absolute end-0 top-50 translate-middle-y"
                  @click="clearSearch"
                  style="border: none; padding: 0.25rem;"
                >
                  <X :size="16" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Orders Table -->
    <DataTable
      v-if="!loading"
      :total-items="ordersComposable.filteredOrders.length"
      :current-page="currentPage"
      :items-per-page="itemsPerPage"
      @page-changed="handlePageChange"
    >
      <template #header>
        <tr>
          <th style="width: 40px;">
            <input 
              type="checkbox" 
              class="form-check-input" 
              @change="selectAll" 
              :checked="allSelected"
              :indeterminate="someSelected"
            />
          </th>
          <th>Order ID</th>
          <th>Supplier</th>
          <th style="width: 120px;">Status</th>
          <th style="width: 120px;">Order Date</th>
          <th style="width: 120px;">Delivery Date</th>
          <th style="width: 100px;">Amount</th>
          <th style="width: 80px;">Items</th>
          <th style="width: 120px;">Actions</th>
        </tr>
      </template>

      <template #body>
        <tr 
          v-for="order in paginatedOrders"
          :key="order.id"
          :class="getRowClass(order)"
        >
          <td>
            <input 
              type="checkbox" 
              class="form-check-input"
              :value="order.id"
              v-model="selectedOrders"
            />
          </td>
          <td>
            <div class="fw-medium text-primary">{{ order.id }}</div>
          </td>
          <td>
            <div class="fw-medium text-tertiary-dark">{{ order.supplier }}</div>
            <small class="text-muted">{{ order.supplierEmail }}</small>
          </td>
          <td>
            <span :class="getStatusBadgeClass(order.status)" class="badge">
              {{ getStatusText(order.status) }}
            </span>
          </td>
          <td>
            <div class="fw-medium">{{ formatDate(order.orderDate) }}</div>
            <small class="text-muted">{{ getDaysAgo(order.orderDate) }}</small>
          </td>
          <td>
            <div class="fw-medium">{{ formatDate(order.expectedDelivery) }}</div>
            <small :class="getDeliveryStatusClass(order)">{{ getDeliveryStatus(order) }}</small>
          </td>
          <td class="text-end">
            <div class="fw-bold">₱{{ formatCurrency(order.totalAmount) }}</div>
          </td>
          <td class="text-center">
            <span class="badge bg-light text-dark">{{ order.items?.length || 0 }}</span>
          </td>
          <td>
            <div class="d-flex gap-1 justify-content-center">
              <button 
                class="btn action-btn action-btn-view" 
                @click="viewOrder(order)"
                data-bs-toggle="tooltip"
                title="View Details"
              >
                <Eye :size="12" />
              </button>
              <button 
                class="btn action-btn action-btn-edit" 
                @click="editOrder(order)"
                data-bs-toggle="tooltip"
                title="Edit Order"
                :disabled="order.status === 'Received' || order.status === 'Depleted'"
              >
                <Edit :size="12" />
              </button>
              <button 
                class="btn action-btn action-btn-download" 
                @click="downloadOrder(order)"
                data-bs-toggle="tooltip"
                title="Download PDF"
              >
                <Download :size="12" />
              </button>
            </div>
          </td>
        </tr>
      </template>
    </DataTable>

    <!-- Empty State -->
    <div v-if="!loading && ordersComposable.filteredOrders.length === 0" class="text-center py-5">
      <div class="card">
        <div class="card-body py-5">
          <Package :size="48" class="text-tertiary-medium mb-3" />
          <p class="text-tertiary-medium mb-3">
            {{ ordersComposable.allOrders.length === 0 ? 'No orders found' : 'No orders match the current filters' }}
          </p>
          <button 
            v-if="ordersComposable.allOrders.length === 0" 
            class="btn btn-primary btn-with-icon" 
            @click="createNewOrder"
          >
            <Plus :size="16" />
            Create First Order
          </button>
          <button 
            v-else 
            class="btn btn-secondary btn-with-icon"
            @click="clearFilters"
          >
            <RefreshCw :size="16" />
            Clear Filters
          </button>
        </div>
      </div>
    </div>

    <!-- Order History Modal -->
    <OrderHistoryModal
      :show="showOrderDetailsModal"
      :order="selectedOrder"
      @close="showOrderDetailsModal = false"
      @edit="editOrder"
      @download="downloadOrder"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  ArrowLeft,
  Plus,
  Search,
  X,
  Eye,
  Edit,
  Download,
  Package,
  RefreshCw
} from 'lucide-vue-next'

// Composables
import { useSuppliers } from '@/composables/api/useSuppliers'

// Components
import CardTemplate from '@/components/common/CardTemplate.vue'
import DataTable from '@/components/common/TableTemplate.vue'
import OrderHistoryModal from '@/components/suppliers/OrderHistoryModal.vue'

export default {
  name: 'OrdersHistory',
  components: {
    ArrowLeft,
    Plus,
    Search,
    X,
    Eye,
    Edit,
    Download,
    Package,
    RefreshCw,
    CardTemplate,
    DataTable,
    OrderHistoryModal
  },
  setup() {
    const router = useRouter()
    const ordersComposable = useSuppliers() // All orders history methods are in useSuppliers
    
    // Local state
    const loading = ref(false)
    const error = ref(null)
    const searchMode = ref(false)
    const searchInput = ref(null)
    const currentPage = ref(1)
    const itemsPerPage = ref(15)
    const selectedOrders = ref([])
    const showOrderDetailsModal = ref(false)
    const selectedOrder = ref(null)

    // Computed
    const paginatedOrders = computed(() => {
      const start = (currentPage.value - 1) * itemsPerPage.value
      const end = start + itemsPerPage.value
      return ordersComposable.filteredOrders.slice(start, end)
    })

    const allSelected = computed(() => {
      return paginatedOrders.value.length > 0 && 
             selectedOrders.value.length === paginatedOrders.value.length
    })

    const someSelected = computed(() => {
      return selectedOrders.value.length > 0 && 
             selectedOrders.value.length < paginatedOrders.value.length
    })

    // Methods
    const goBack = () => {
      router.go(-1)
    }

    const refreshData = async () => {
      loading.value = true
      error.value = null
      try {
        await ordersComposable.fetchOrders()
      } catch (err) {
        error.value = err.message
      } finally {
        loading.value = false
      }
    }

    const toggleSearchMode = () => {
      searchMode.value = !searchMode.value
      
      if (searchMode.value) {
        setTimeout(() => {
          if (searchInput.value) {
            searchInput.value.focus()
          }
        }, 50)
      } else {
        ordersComposable.filters.search = ''
        applyFilters()
      }
    }

    const clearSearch = () => {
      ordersComposable.filters.search = ''
      searchMode.value = false
      applyFilters()
    }

    const applyFilters = () => {
      ordersComposable.applyFilters()
      currentPage.value = 1
      selectedOrders.value = []
    }

    const clearFilters = () => {
      ordersComposable.clearFilters()
      searchMode.value = false
    }

    const selectAll = (event) => {
      if (event.target.checked) {
        selectedOrders.value = paginatedOrders.value.map(order => order.id)
      } else {
        selectedOrders.value = []
      }
    }

    const handlePageChange = (page) => {
      currentPage.value = page
      selectedOrders.value = []
    }

    const viewOrder = (order) => {
      selectedOrder.value = order
      showOrderDetailsModal.value = true
    }

    const editOrder = (order) => {
      // Navigate to edit page or open edit modal
    }

    const downloadOrder = (order) => {
      // Generate and download PDF
    }

    const createNewOrder = () => {
      // Navigate to create order page or open modal
    }

    const exportOrders = () => {
      // Export filtered orders to CSV/Excel
    }

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      })
    }

    const formatCurrency = (amount) => {
      return new Intl.NumberFormat('en-PH').format(amount)
    }

    const getDaysAgo = (dateString) => {
      const date = new Date(dateString)
      const now = new Date()
      const diffTime = Math.abs(now - date)
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays === 1) return '1 day ago'
      if (diffDays < 7) return `${diffDays} days ago`
      if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
      return `${Math.floor(diffDays / 30)} months ago`
    }

    const getDeliveryStatus = (order) => {
      const expectedDate = new Date(order.expectedDelivery)
      const now = new Date()
      
      if (order.status === 'Received') return 'Delivered'
      if (order.status === 'Depleted') return 'Depleted'
      
      const diffTime = expectedDate - now
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays < 0) return `${Math.abs(diffDays)} days overdue`
      if (diffDays === 0) return 'Due today'
      if (diffDays === 1) return 'Due tomorrow'
      return `${diffDays} days remaining`
    }

    const getDeliveryStatusClass = (order) => {
      const expectedDate = new Date(order.expectedDelivery)
      const now = new Date()
      const diffDays = Math.ceil((expectedDate - now) / (1000 * 60 * 60 * 24))
      
      if (order.status === 'Received') return 'text-success'
      if (order.status === 'Depleted') return 'text-muted'
      if (diffDays < 0) return 'text-danger'
      if (diffDays <= 2) return 'text-warning'
      return 'text-muted'
    }

    const getStatusBadgeClass = (status) => {
      const statusClasses = {
        'Pending Delivery': 'bg-warning text-dark',
        'Partially Received': 'bg-info text-white',
        'Received': 'bg-success text-white',
        'Depleted': 'bg-secondary text-white',
        'Mixed Status': 'bg-primary text-white'
      }
      return statusClasses[status] || 'bg-secondary text-white'
    }

    const getStatusText = (status) => {
      return status // Status is already in the correct format
    }

    const getRowClass = (order) => {
      const classes = []
      
      if (selectedOrders.value.includes(order.id)) {
        classes.push('table-primary')
      }
      
      if (order.status === 'Depleted') {
        classes.push('text-muted')
      }
      
      return classes.join(' ')
    }

    // Initialize
    onMounted(async () => {
      await refreshData()
    })

    return {
      // Composables
      ordersComposable,
      
      // Local state
      loading,
      error,
      searchMode,
      searchInput,
      currentPage,
      itemsPerPage,
      selectedOrders,
      showOrderDetailsModal,
      selectedOrder,
      
      // Computed
      paginatedOrders,
      allSelected,
      someSelected,
      
      // Methods
      goBack,
      refreshData,
      toggleSearchMode,
      clearSearch,
      applyFilters,
      clearFilters,
      selectAll,
      handlePageChange,
      viewOrder,
      editOrder,
      downloadOrder,
      createNewOrder,
      exportOrders,
      formatDate,
      formatCurrency,
      getDaysAgo,
      getDeliveryStatus,
      getDeliveryStatusClass,
      getStatusBadgeClass,
      getStatusText,
      getRowClass
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';
@import '@/assets/styles/buttons.css';

.orders-history-page {
  background-color: var(--neutral-light);
  min-height: 100vh;
}

.text-primary-dark {
  color: var(--primary-dark) !important;
}

.text-tertiary-dark {
  color: var(--tertiary-dark) !important;
}

.text-tertiary-medium {
  color: var(--tertiary-medium) !important;
}

/* Action Bar Container */
.action-bar-container {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  overflow: visible;
  position: relative;
  z-index: 1000;
}

.action-bar-controls {
  border-bottom: 1px solid var(--neutral);
  background-color: white;
  position: relative;
  z-index: 1001;
}

.action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  flex-wrap: wrap;
  gap: 1rem;
}

/* Filter Dropdown */
.filter-dropdown {
  min-width: 120px;
}

.filter-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--tertiary-medium);
  margin-bottom: 0.25rem;
  display: block;
}

/* Search Container */
.search-container {
  min-width: 300px;
}

.search-input {
  padding-right: 2.5rem;
  height: calc(1.5em + 0.75rem + 2px);
}

.search-container .position-relative .btn {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Button States */
.btn.active {
  background-color: var(--primary);
  border-color: var(--primary);
  color: white;
}

/* Form controls focus states */
.form-select:focus,
.form-control:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem rgba(115, 146, 226, 0.25);
}

/* Table row selection */
.table tbody tr.table-primary {
  background-color: var(--primary-light) !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .action-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-container {
    min-width: 100%;
  }
}

@media (max-width: 576px) {
  .btn-sm {
    font-size: 0.8rem;
    padding: 0.375rem 0.5rem;
  }
}
</style>