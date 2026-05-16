<template>
  <div class="container-fluid pt-2 pb-4 orders-history-page surface-secondary">
    <!-- Page Title with Back Button -->
    <div class="d-flex align-items-center justify-content-between mb-4">
      <div class="d-flex align-items-center">
        <button class="btn btn-outline-secondary btn-sm me-3" @click="goBack">
          <ArrowLeft :size="16" />
          Back
        </button>
        <div>
          <h1 class="h3 fw-semibold text-primary mb-0">Purchase Orders History</h1>
          <p class="text-tertiary mb-0" v-if="!loading">
            {{ displayOrders?.length || 0 }} orders found
          </p>
        </div>
      </div>
      
      <!-- Quick Actions -->
      <div class="d-flex gap-2">
        <button class="btn btn-outline-secondary btn-sm" @click="exportOrders">
          <Download :size="14" class="me-1" />
          Export
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-accent" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="mt-3 text-tertiary">Loading orders...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="alert alert-danger" role="alert">
      <div class="d-flex align-items-center">
        <AlertCircle :size="20" class="me-2" />
        <div>
          <strong>Error loading orders:</strong> {{ error }}
          <button class="btn btn-sm btn-outline-danger ms-2" @click="refreshData">
            <RefreshCw :size="14" class="me-1" />
            Retry
          </button>
        </div>
      </div>
    </div>

    <!-- Filters Bar -->
    <div v-if="!loading" class="surface-card border-theme mb-3 rounded">
      <div class="card-body py-2">
        <div class="row align-items-center">
          <div class="col-md-8">
            <div class="d-flex gap-3 align-items-center flex-wrap">
              <!-- Status Filter -->
              <div class="d-flex align-items-center gap-2">
                <label class="form-label mb-0 text-secondary fw-medium">Status:</label>
                <select 
                  class="form-select form-select-sm input-theme" 
                  v-model="statusFilter" 
                  @change="applyFilters"
                  style="min-width: 130px;"
                >
                  <option value="all">All Status</option>
                  <option value="pending_delivery">Pending Delivery</option>
                  <option value="partially_received">Partially Received</option>
                  <option value="received">Received</option>
                  <option value="depleted">Depleted</option>
                  <option value="mixed_status">Mixed Status</option>
                </select>
              </div>

              <!-- Supplier Filter -->
              <div class="d-flex align-items-center gap-2">
                <label class="form-label mb-0 text-secondary fw-medium">Supplier:</label>
                <select 
                  class="form-select form-select-sm input-theme" 
                  v-model="supplierFilter" 
                  @change="applyFilters"
                  style="min-width: 150px;"
                >
                  <option value="all">All Suppliers</option>
                  <option 
                    v-for="supplier in supplierOptions" 
                    :key="`supplier-${supplier.value}`" 
                    :value="supplier.value"
                  >
                    {{ supplier.label }}
                  </option>
                </select>
              </div>

              <!-- Date Range Filter -->
              <div class="d-flex align-items-center gap-2">
                <label class="form-label mb-0 text-secondary fw-medium">Period:</label>
                <select 
                  class="form-select form-select-sm input-theme" 
                  v-model="dateFilter" 
                  @change="applyFilters"
                  style="min-width: 120px;"
                >
                  <option value="all">All Time</option>
                  <option value="today">Today</option>
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                  <option value="quarter">This Quarter</option>
                </select>
              </div>
            </div>
          </div>
          
          <div class="col-md-4">
            <!-- Search -->
            <div class="position-relative">
              <Search :size="16" class="position-absolute top-50 start-0 translate-middle-y ms-3 text-tertiary" />
              <input 
                v-model="searchFilter" 
                @input="applyFilters"
                type="text" 
                class="form-control form-control-sm ps-5 input-theme"
                placeholder="Search orders, suppliers..."
              />
              <button 
                v-if="searchFilter"
                class="btn btn-sm btn-link position-absolute top-50 end-0 translate-middle-y me-2 p-0"
                @click="clearSearch"
              >
                <X :size="16" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Orders Table -->
    <div v-if="!loading" class="surface-card border-theme rounded">
      <div class="card-header surface-accent text-white border-theme">
        <div class="d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Purchase Orders</h5>
          <div class="d-flex align-items-center gap-3">
            <span class="badge bg-white text-accent">
              {{ displayOrders?.length || 0 }} orders
            </span>
            <button 
              v-if="hasFilters" 
              class="btn btn-sm btn-outline-light" 
              @click="clearAllFilters"
            >
              <X :size="14" class="me-1" />
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      <div class="table-responsive" v-if="displayOrders?.length > 0">
        <table class="table table-hover mb-0">
          <thead class="surface-tertiary sticky-top">
            <tr>
              <th style="width: 140px;">
                <div class="d-flex align-items-center text-secondary">
                  Order ID
                  <ChevronUp :size="14" class="ms-1 text-tertiary" />
                </div>
              </th>
              <th style="width: 180px;" class="text-secondary">Supplier</th>
              <th style="width: 110px;" class="text-secondary">Status</th>
              <th style="width: 120px;" class="text-secondary">Order Date</th>
              <th style="width: 120px;" class="text-secondary">Expected Delivery</th>
              <th style="width: 100px;" class="text-end text-secondary">Amount</th>
              <th style="width: 80px;" class="text-center text-secondary">Items</th>
              <th style="width: 140px;" class="text-center text-secondary">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="order in paginatedOrders" 
              :key="order.id"
              :class="getRowClass(order)"
            >
              <!-- Order ID -->
              <td>
                <div class="fw-semibold text-accent">{{ order.id }}</div>
              </td>
              
              <!-- Supplier -->
              <td>
                <div>
                  <div class="fw-medium text-primary">{{ order.supplier }}</div>
                  <small class="text-tertiary">{{ order.supplierEmail }}</small>
                </div>
              </td>
              
              <!-- Status -->
              <td>
                <span :class="getStatusBadgeClass(order.status)" class="badge">
                  {{ getStatusText(order.status) }}
                </span>
              </td>
              
              <!-- Order Date -->
              <td>
                <div>
                  <div class="fw-medium text-primary">{{ formatDate(order.orderDate) }}</div>
                  <small class="text-tertiary">{{ getDaysAgo(order.orderDate) }}</small>
                </div>
              </td>
              
              <!-- Expected Delivery -->
              <td>
                <div>
                  <div class="fw-medium text-primary">{{ formatDate(order.expectedDelivery) }}</div>
                  <small :class="getDeliveryStatusClass(order)">
                    {{ getDeliveryStatus(order) }}
                  </small>
                </div>
              </td>
              
              <!-- Amount -->
              <td class="text-end">
                <div class="fw-bold text-primary">₱{{ formatCurrency(order.totalAmount) }}</div>
              </td>
              
              <!-- Items Count -->
              <td class="text-center">
                <span class="badge surface-tertiary text-primary border-theme">
                  {{ order.items?.length || 0 }}
                </span>
              </td>
              
              <!-- Actions -->
              <td>
                <div class="d-flex gap-1 justify-content-center">
                  <button 
                    class="btn btn-sm btn-outline-primary" 
                    @click="viewOrder(order)"
                    title="View Details"
                  >
                    <Eye :size="14" />
                  </button>
                  <button 
                    :class="getEditButtonClass(order)"
                    @click="editOrder(order)"
                    :title="getEditTooltip(order)"
                    :disabled="!canEditOrder(order) && !canEditLimited(order)"
                  >
                    <Edit :size="14" />
                  </button>
                  <button 
                    class="btn btn-sm btn-outline-info" 
                    @click="downloadOrder(order)"
                    title="Download PDF"
                  >
                    <Download :size="14" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div v-if="displayOrders?.length === 0" class="text-center py-5">
        <div class="py-4">
          <Package :size="48" class="text-tertiary mb-3" />
          <h5 class="text-primary">No Orders Found</h5>
          <p class="text-tertiary mb-3">
            {{ hasFilters ? 'No orders match your current filters.' : 'No purchase orders have been created yet.' }}
          </p>
          <div class="d-flex gap-2 justify-content-center">
            <button v-if="hasFilters" class="btn btn-outline-secondary" @click="clearAllFilters">
              <RefreshCw :size="16" class="me-1" />
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="displayOrders?.length > itemsPerPage" class="card-footer surface-secondary border-theme">
        <nav class="d-flex justify-content-between align-items-center">
          <div class="text-tertiary">
            Showing {{ startItem }}-{{ endItem }} of {{ displayOrders.length }} orders
          </div>
          <ul class="pagination pagination-sm mb-0">
            <li class="page-item" :class="{ disabled: currentPage === 1 }">
              <button class="page-link" @click="goToPage(currentPage - 1)" :disabled="currentPage === 1">
                <ChevronLeft :size="16" />
              </button>
            </li>
            <li 
              v-for="page in visiblePages" 
              :key="page"
              class="page-item" 
              :class="{ active: page === currentPage }"
            >
              <button class="page-link" @click="goToPage(page)">{{ page }}</button>
            </li>
            <li class="page-item" :class="{ disabled: currentPage === totalPages }">
              <button class="page-link" @click="goToPage(currentPage + 1)" :disabled="currentPage === totalPages">
                <ChevronRight :size="16" />
              </button>
            </li>
          </ul>
        </nav>
      </div>
    </div>

    <!-- Order Details Modal -->
    <div v-if="showOrderModal" class="modal fade show" style="display: block;" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content surface-card border-theme">
          <div class="modal-header border-theme">
            <h5 class="modal-title text-primary">
              <Package :size="20" class="me-2" />
              Order Details - {{ selectedOrder?.id }}
            </h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <div v-if="selectedOrder" class="row">
              <div class="col-md-6">
                <h6 class="fw-bold text-primary">Order Information</h6>
                <p class="text-secondary"><strong>Order ID:</strong> {{ selectedOrder.id }}</p>
                <p class="text-secondary"><strong>Status:</strong> 
                  <span :class="getStatusBadgeClass(selectedOrder.status)" class="badge ms-1">
                    {{ getStatusText(selectedOrder.status) }}
                  </span>
                </p>
                <p class="text-secondary"><strong>Order Date:</strong> {{ formatDate(selectedOrder.orderDate) }}</p>
                <p class="text-secondary"><strong>Expected Delivery:</strong> {{ formatDate(selectedOrder.expectedDelivery) }}</p>
                <p class="text-secondary"><strong>Total Amount:</strong> <strong>₱{{ formatCurrency(selectedOrder.totalAmount) }}</strong></p>
              </div>
              <div class="col-md-6">
                <h6 class="fw-bold text-primary">Supplier Information</h6>
                <p class="text-secondary"><strong>Supplier:</strong> {{ selectedOrder.supplier }}</p>
                <p class="text-secondary"><strong>Email:</strong> {{ selectedOrder.supplierEmail }}</p>
              </div>
              <div class="col-12 mt-3">
                <h6 class="fw-bold text-primary">Items ({{ selectedOrder.items?.length || 0 }})</h6>
                <div class="table-responsive">
                  <table class="table table-sm">
                    <thead class="surface-tertiary">
                      <tr>
                        <th class="text-secondary">Item</th>
                        <th class="text-secondary">Quantity</th>
                        <th class="text-secondary">Unit Price</th>
                        <th class="text-secondary">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(item, index) in selectedOrder.items" :key="index">
                        <td class="text-primary">{{ item.name }}</td>
                        <td class="text-primary">{{ item.quantity }}</td>
                        <td class="text-primary">₱{{ formatCurrency(item.unitPrice) }}</td>
                        <td class="text-primary">₱{{ formatCurrency(item.quantity * item.unitPrice) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer border-theme surface-secondary">
            <button type="button" class="btn btn-secondary" @click="closeModal">Close</button>
            <button type="button" class="btn btn-outline-primary" @click="editOrder(selectedOrder)" :disabled="!canEditOrder(selectedOrder) && !canEditLimited(selectedOrder)">
              <Edit :size="16" class="me-1" />
              {{ canEditOrder(selectedOrder) ? 'Edit Order' : canEditLimited(selectedOrder) ? 'Edit Details' : 'Cannot Edit' }}
            </button>
            <button type="button" class="btn btn-outline-info" @click="downloadOrder(selectedOrder)">
              <Download :size="16" class="me-1" />
              Download PDF
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showOrderModal" class="modal-backdrop fade show" @click="closeModal"></div>

    <!-- Edit Order Modal -->
    <div v-if="showEditModal" class="modal fade show" style="display: block;" tabindex="-1">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header bg-warning text-dark">
            <h5 class="modal-title">
              <Edit :size="20" class="me-2" />
              Edit Order - {{ editingOrder?.id }}
            </h5>
            <button type="button" class="btn-close" @click="closeEditModal"></button>
          </div>
          <div class="modal-body">
            <div v-if="editingOrder" class="row">
              <!-- Order Details Section -->
              <div class="col-md-6">
                <h6 class="fw-bold text-tertiary-dark mb-3">Order Information</h6>
                <div class="mb-3">
                  <label class="form-label text-tertiary-dark">Order ID</label>
                  <input type="text" class="form-control" :value="editingOrder.id" disabled>
                </div>
                <div class="mb-3">
                  <label class="form-label text-tertiary-dark">Order Date</label>
                  <input type="date" class="form-control" v-model="editingOrder.orderDate">
                </div>
                <div class="mb-3">
                  <label class="form-label text-tertiary-dark">Expected Delivery</label>
                  <input type="date" class="form-control" v-model="editingOrder.expectedDelivery">
                </div>
                <div class="mb-3">
                  <label class="form-label text-tertiary-dark">Status</label>
                  <select class="form-select" v-model="editingOrder.status">
                    <option value="pending">Pending</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="in_transit">In Transit</option>
                    <option value="delivered">Delivered</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
              </div>

              <!-- Supplier Details Section -->
              <div class="col-md-6">
                <h6 class="fw-bold text-tertiary-dark mb-3">Supplier Information</h6>
                <div class="mb-3">
                  <label class="form-label text-tertiary-dark">Supplier Name</label>
                  <select class="form-select" v-model="editingOrder.supplier">
                    <option value="Bravo Warehouse">Bravo Warehouse</option>
                    <option value="John Doe Supplies">John Doe Supplies</option>
                    <option value="San Juan Groups">San Juan Groups</option>
                    <option value="Bagatayam Inc.">Bagatayam Inc.</option>
                  </select>
                </div>
                <div class="mb-3">
                  <label class="form-label text-tertiary-dark">Supplier Email</label>
                  <input type="email" class="form-control" v-model="editingOrder.supplierEmail">
                </div>
                <div class="mb-3">
                  <label class="form-label text-tertiary-dark">Total Amount</label>
                  <div class="input-group">
                    <span class="input-group-text">₱</span>
                    <input type="number" class="form-control" v-model="editingOrder.totalAmount" step="0.01">
                  </div>
                </div>
              </div>

              <!-- Items Section -->
              <div class="col-12 mt-4">
                <h6 class="fw-bold text-tertiary-dark mb-3">Order Items</h6>
                <div class="table-responsive">
                  <table class="table table-bordered">
                    <thead class="table-light">
                      <tr>
                        <th>Item Name</th>
                        <th style="width: 120px;">Quantity</th>
                        <th style="width: 140px;">Unit Price (₱)</th>
                        <th style="width: 140px;">Total (₱)</th>
                        <th style="width: 80px;">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(item, index) in editingOrder.items" :key="index">
                        <td>
                          <input type="text" class="form-control form-control-sm" v-model="item.name">
                        </td>
                        <td>
                          <input type="number" class="form-control form-control-sm" v-model="item.quantity" min="1">
                        </td>
                        <td>
                          <input type="number" class="form-control form-control-sm" v-model="item.unitPrice" step="0.01" min="0">
                        </td>
                        <td>
                          <span class="fw-bold">₱{{ formatCurrency(item.quantity * item.unitPrice) }}</span>
                        </td>
                        <td>
                          <button class="btn btn-sm btn-outline-danger" @click="removeItem(index)" title="Remove Item">
                            <X :size="14" />
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-3">
                  <button class="btn btn-outline-success btn-sm" @click="addNewItem">
                    <Plus :size="14" class="me-1" />
                    Add Item
                  </button>
                  <div class="text-end">
                    <strong class="text-tertiary-dark">Total Amount: ₱{{ formatCurrency(calculateTotal()) }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeEditModal">Cancel</button>
            <button type="button" class="btn btn-warning" @click="saveOrderChanges">
              <Edit :size="16" class="me-1" />
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showEditModal" class="modal-backdrop fade show" @click="closeEditModal"></div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  ArrowLeft,
  Download,
  Search,
  X,
  Eye,
  Edit,
  Package,
  RefreshCw,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Plus
} from 'lucide-vue-next'

// Composables
import { useSuppliers } from '@/composables/api/useSuppliers'

export default {
  name: 'OrdersHistory',
  components: {
    ArrowLeft,
    Download,
    Search,
    X,
    Eye,
    Edit,
    Package,
    RefreshCw,
    ChevronUp,
    ChevronLeft,
    ChevronRight,
    AlertCircle,
    Plus
  },
  setup() {
    const router = useRouter()
    const ordersComposable = useSuppliers() // All orders history methods are in useSuppliers
    
    // Use composable's loading and error states
    const loading = computed(() => ordersComposable.ordersHistoryLoading?.value)
    const error = computed(() => ordersComposable.ordersHistoryError?.value)
    
    // Local state for UI
    const currentPage = ref(1)
    const itemsPerPage = ref(15)
    const statusFilter = ref('all')
    const supplierFilter = ref('all')
    const dateFilter = ref('all')
    const searchFilter = ref('')
    const showOrderModal = ref(false)
    const selectedOrder = ref(null)
    const showEditModal = ref(false)
    const editingOrder = ref(null)

    // Use composable's filtered orders directly
    const displayOrders = computed(() => ordersComposable.ordersHistoryFilteredOrders?.value || [])

    const supplierOptions = computed(() => ordersComposable.ordersHistorySupplierOptions?.value || [])

    const paginatedOrders = computed(() => {
      if (!displayOrders.value?.length) return []
      const start = (currentPage.value - 1) * itemsPerPage.value
      const end = start + itemsPerPage.value
      return displayOrders.value.slice(start, end)
    })

    const totalPages = computed(() => {
      return Math.ceil((displayOrders.value?.length || 0) / itemsPerPage.value)
    })

    const startItem = computed(() => {
      return (currentPage.value - 1) * itemsPerPage.value + 1
    })

    const endItem = computed(() => {
      return Math.min(currentPage.value * itemsPerPage.value, displayOrders.value?.length || 0)
    })

    const visiblePages = computed(() => {
      const pages = []
      const total = totalPages.value
      const current = currentPage.value
      
      if (total <= 7) {
        for (let i = 1; i <= total; i++) {
          pages.push(i)
        }
      } else {
        if (current <= 4) {
          for (let i = 1; i <= 5; i++) {
            pages.push(i)
          }
          pages.push('...', total)
        } else if (current >= total - 3) {
          pages.push(1, '...')
          for (let i = total - 4; i <= total; i++) {
            pages.push(i)
          }
        } else {
          pages.push(1, '...')
          for (let i = current - 1; i <= current + 1; i++) {
            pages.push(i)
          }
          pages.push('...', total)
        }
      }
      
      return pages
    })

    const hasFilters = computed(() => {
      return statusFilter.value !== 'all' || 
             supplierFilter.value !== 'all' || 
             dateFilter.value !== 'all' || 
             searchFilter.value.trim() !== ''
    })

    // Methods
    const goBack = () => {
      router.go(-1)
    }

    const refreshData = async () => {
      await ordersComposable.fetchOrders()
    }

    const applyFilters = () => {
      if (ordersComposable?.filters?.value) {
        if (ordersComposable.ordersHistoryFilters?.value) {
          ordersComposable.ordersHistoryFilters.value.status = statusFilter.value
          ordersComposable.ordersHistoryFilters.value.supplier = supplierFilter.value
          ordersComposable.ordersHistoryFilters.value.dateRange = dateFilter.value
          ordersComposable.ordersHistoryFilters.value.search = searchFilter.value
        }
        if (ordersComposable.applyOrdersFilters) {
          ordersComposable.applyOrdersFilters()
        }
      }
      currentPage.value = 1
    }

    const clearSearch = () => {
      searchFilter.value = ''
      applyFilters()
    }

    const clearAllFilters = () => {
      statusFilter.value = 'all'
      supplierFilter.value = 'all'
      dateFilter.value = 'all'
      searchFilter.value = ''
      applyFilters()
    }

    const goToPage = (page) => {
      if (page >= 1 && page <= totalPages.value) {
        currentPage.value = page
      }
    }

    const viewOrder = (order) => {
      selectedOrder.value = order
      showOrderModal.value = true
    }

    const closeModal = () => {
      showOrderModal.value = false
      selectedOrder.value = null
    }

    const closeEditModal = () => {
      showEditModal.value = false
      editingOrder.value = null
    }

    const editOrder = (order) => {
      closeModal()
      
      if (canEditOrder(order)) {
        editingOrder.value = JSON.parse(JSON.stringify(order))
        showEditModal.value = true
      } else if (canEditLimited(order)) {
        alert(`Limited edit for order ${order.id} - Only delivery date and contact details can be edited`)
      } else {
        alert(`Order ${order.id} cannot be edited due to its current status: ${order.status}`)
      }
    }

    const saveOrderChanges = () => {
      alert(`Order ${editingOrder.value.id} saved successfully!`)
      closeEditModal()
    }

    const addNewItem = () => {
      editingOrder.value.items.push({
        name: '',
        quantity: 1,
        unitPrice: 0
      })
    }

    const removeItem = (index) => {
      if (editingOrder.value.items.length > 1) {
        editingOrder.value.items.splice(index, 1)
      } else {
        alert('Order must have at least one item')
      }
    }

    const calculateTotal = () => {
      if (!editingOrder.value?.items) return 0
      return editingOrder.value.items.reduce((total, item) => {
        return total + (item.quantity * item.unitPrice)
      }, 0)
    }

    const downloadOrder = (order) => {
      try {
        // Import jsPDF dynamically
        import('jspdf').then(({ default: jsPDF }) => {
          const doc = new jsPDF()
          
          // PDF Settings
          const pageWidth = doc.internal.pageSize.getWidth()
          const pageHeight = doc.internal.pageSize.getHeight()
          const margin = 20
          const maxWidth = pageWidth - (margin * 2)
          let yPosition = margin
          
          // Helper function to add text and return new y position
          const addTextLine = (text, x, y, maxWidth, fontSize = 10, fontWeight = 'normal', align = 'left') => {
            doc.setFontSize(fontSize)
            doc.setFont(undefined, fontWeight)
            const lines = doc.splitTextToSize(String(text || 'N/A'), maxWidth)
            doc.text(lines, x, y, { align })
            return y + (lines.length * fontSize * 0.4)
          }
          
          // Helper function to add horizontal line
          const addHorizontalLine = (y) => {
            doc.setLineWidth(0.5)
            doc.setDrawColor(200, 200, 200)
            doc.line(margin, y, pageWidth - margin, y)
            return y + 8
          }
          
          // Helper function to check if new page needed
          const checkNewPage = (requiredHeight) => {
            if (yPosition + requiredHeight > pageHeight - 30) {
              doc.addPage()
              yPosition = margin
              return true
            }
            return false
          }
          
          // Header Section
          doc.setFillColor(59, 130, 246) // Blue color
          doc.rect(0, 0, pageWidth, 45, 'F')
          
          doc.setTextColor(255, 255, 255)
          doc.setFontSize(22)
          doc.setFont(undefined, 'bold')
          doc.text('PURCHASE ORDER', pageWidth / 2, 28, { align: 'center' })
          
          doc.setFontSize(11)
          doc.text('PANNTECH POS & Inventory', pageWidth / 2, 38, { align: 'center' })
          
          // Reset text color
          doc.setTextColor(0, 0, 0)
          yPosition = 55
          
          // Order Information Section
          doc.setFontSize(14)
          doc.setFont(undefined, 'bold')
          doc.text('Order Information', margin, yPosition)
          yPosition += 8
          
          yPosition = addHorizontalLine(yPosition)
          yPosition += 3
          
          // Order Details - Two column layout
          doc.setFontSize(10)
          const labelX = margin
          const valueX = margin + 55
          const lineSpacing = 7
          
          // Left column
          doc.setFont(undefined, 'bold')
          doc.text('Order ID:', labelX, yPosition)
          doc.setFont(undefined, 'normal')
          doc.text(String(order.id || 'N/A'), valueX, yPosition)
          yPosition += lineSpacing
          
          doc.setFont(undefined, 'bold')
          doc.text('Supplier:', labelX, yPosition)
          doc.setFont(undefined, 'normal')
          doc.text(String(order.supplier || 'N/A'), valueX, yPosition)
          yPosition += lineSpacing
          
          doc.setFont(undefined, 'bold')
          doc.text('Supplier Email:', labelX, yPosition)
          doc.setFont(undefined, 'normal')
          doc.text(String(order.supplierEmail || 'N/A'), valueX, yPosition)
          yPosition += lineSpacing
          
          // Right column (if space allows)
          let rightColumnY = yPosition - (lineSpacing * 3)
          const rightLabelX = pageWidth / 2 + 10
          const rightValueX = rightLabelX + 45
          
          doc.setFont(undefined, 'bold')
          doc.text('Order Date:', rightLabelX, rightColumnY)
          doc.setFont(undefined, 'normal')
          doc.text(formatDate(order.orderDate), rightValueX, rightColumnY)
          rightColumnY += lineSpacing
          
          doc.setFont(undefined, 'bold')
          doc.text('Expected Delivery:', rightLabelX, rightColumnY)
          doc.setFont(undefined, 'normal')
          doc.text(formatDate(order.expectedDelivery), rightValueX, rightColumnY)
          rightColumnY += lineSpacing
          
          doc.setFont(undefined, 'bold')
          doc.text('Status:', rightLabelX, rightColumnY)
          doc.setFont(undefined, 'normal')
          doc.text(String(order.status || 'N/A'), rightValueX, rightColumnY)
          
          // Use the right column Y if it's further down
          yPosition = Math.max(yPosition, rightColumnY) + lineSpacing
          
          yPosition = addHorizontalLine(yPosition)
          yPosition += 8
          
          // Items Section
          checkNewPage(30)
          doc.setFontSize(14)
          doc.setFont(undefined, 'bold')
          doc.text('Order Items', margin, yPosition)
          yPosition += 8
          
          yPosition = addHorizontalLine(yPosition)
          yPosition += 3
          
          // Column positions (adjusted to fit within page width) - define before table
          const colItem = margin + 3
          const colQuantity = pageWidth - margin - 115  // Right-aligned, 115mm from right
          const colUnitPrice = pageWidth - margin - 75  // Right-aligned, 75mm from right
          const colTotal = pageWidth - margin  // Right-aligned at right margin
          
          // Table Header
          checkNewPage(25)
          doc.setFillColor(240, 240, 240)
          doc.rect(margin, yPosition - 6, maxWidth, 10, 'F')
          
          doc.setFontSize(10)
          doc.setFont(undefined, 'bold')
          doc.setTextColor(0, 0, 0)
          doc.text('Item', colItem, yPosition)
          doc.text('Quantity', colQuantity, yPosition, { align: 'right' })
          doc.text('Unit Price', colUnitPrice, yPosition, { align: 'right' })
          doc.text('Total', colTotal, yPosition, { align: 'right' })
          yPosition += 12
          
          // Items Table
          doc.setFont(undefined, 'normal')
          doc.setFontSize(9)
          let itemsTotal = 0
          
          if (!order.items || order.items.length === 0) {
            doc.text('No items in this order', margin + 3, yPosition)
            yPosition += 10
          } else {
            order.items.forEach((item) => {
              checkNewPage(15)
              
              const itemName = String(item.name || item.product_name || 'Unknown Product')
              // Debug logging for Unknown Product
              if (itemName === 'Unknown Product' && item.product_id) {
                console.warn(`[PDF] Unknown Product detected for item:`, {
                  product_id: item.product_id,
                  name: item.name,
                  product_name: item.product_name,
                  fullItem: item
                })
              }
              const quantity = parseFloat(item.quantity || 0)
              const unitPrice = parseFloat(item.unitPrice || 0)
              const itemTotal = quantity * unitPrice
              itemsTotal += itemTotal
              
              // Wrap item name if needed - adjust max width to account for columns
              const itemNameMaxWidth = colQuantity - colItem - 5
              const itemNameLines = doc.splitTextToSize(itemName, itemNameMaxWidth)
              const rowHeight = Math.max(itemNameLines.length * 4, 8)
              
              // Item name (first line)
              doc.text(itemNameLines[0], colItem, yPosition)
              
              // Quantity - right aligned
              doc.text(quantity.toString(), colQuantity, yPosition, { align: 'right' })
              
              // Unit Price - right aligned
              doc.text(`₱${formatCurrency(unitPrice)}`, colUnitPrice, yPosition, { align: 'right' })
              
              // Total - right aligned
              doc.text(`₱${formatCurrency(itemTotal)}`, colTotal, yPosition, { align: 'right' })
              
              // Additional lines of item name
              if (itemNameLines.length > 1) {
                for (let i = 1; i < itemNameLines.length; i++) {
                  yPosition += 4
                  doc.text(itemNameLines[i], margin + 3, yPosition)
                }
              }
              
              yPosition += rowHeight - (itemNameLines.length - 1) * 4 + 3
              
              // Product ID (small text below item)
              if (item.product_id) {
                doc.setFontSize(7)
                doc.setTextColor(128, 128, 128)
                doc.text(`ID: ${item.product_id}`, margin + 5, yPosition)
                doc.setTextColor(0, 0, 0)
                doc.setFontSize(9)
                yPosition += 5
              }
            })
          }
          
          yPosition += 5
          yPosition = addHorizontalLine(yPosition)
          yPosition += 8
          
          // Total Amount
          checkNewPage(20)
          doc.setFont(undefined, 'bold')
          doc.setFontSize(12)
          
          const totalLabel = 'Total Amount:'
          const finalTotal = order.totalAmount || itemsTotal
          const totalValue = `₱${formatCurrency(finalTotal)}`
          
          // Position label from left
          doc.text(totalLabel, margin, yPosition)
          
          // Position value aligned with the "Total" column (same position as table total column)
          doc.setFontSize(14)
          doc.text(totalValue, colTotal, yPosition, { align: 'right' })
          
          // Footer on all pages
          const pageCount = doc.internal.getNumberOfPages()
          for (let i = 1; i <= pageCount; i++) {
            doc.setPage(i)
            doc.setFontSize(8)
            doc.setTextColor(128, 128, 128)
            doc.setFont(undefined, 'normal')
            doc.text(
              `Page ${i} of ${pageCount}`,
              pageWidth / 2,
              pageHeight - 10,
              { align: 'center' }
            )
            doc.text(
              `Generated: ${new Date().toLocaleString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
              })}`,
              pageWidth - margin,
              pageHeight - 10,
              { align: 'right' }
            )
          }
          
          // Download PDF
          const filename = `Purchase_Order_${order.id}_${new Date().toISOString().split('T')[0]}.pdf`
          doc.save(filename)
        }).catch((error) => {
          console.error('Error generating PDF:', error)
          alert('Failed to generate PDF. Please install jsPDF library: npm install jspdf')
        })
      } catch (error) {
        console.error('Error downloading order:', error)
        alert('Error downloading order PDF')
      }
    }

    const exportOrders = () => {
      if (ordersComposable?.exportOrdersData) {
        ordersComposable.exportOrdersData?.('csv')
        alert('Orders exported to CSV successfully!')
      } else {
        alert('Export functionality not available')
      }
    }

    // Utility methods for order editing
    const canEditOrder = (order) => {
      return order.status === 'pending'
    }

    const canEditLimited = (order) => {
      return order.status === 'confirmed'
    }

    const getEditTooltip = (order) => {
      switch (order.status) {
        case 'pending':
          return 'Edit Order'
        case 'confirmed':
          return 'Edit delivery details only'
        case 'in_transit':
          return 'Cannot edit - Order is in transit'
        case 'delivered':
          return 'Cannot edit - Order has been delivered'
        case 'cancelled':
          return 'Cannot edit - Order has been cancelled'
        default:
          return 'Edit not available'
      }
    }

    const getEditButtonClass = (order) => {
      if (canEditOrder(order)) {
        return 'btn btn-sm btn-outline-secondary'
      } else if (canEditLimited(order)) {
        return 'btn btn-sm btn-outline-warning'
      } else {
        return 'btn btn-sm btn-outline-secondary'
      }
    }

    // Utility methods
    const formatDate = (dateString) => {
      try {
        return new Date(dateString).toLocaleDateString('en-US', { 
          year: 'numeric', month: 'short', day: 'numeric' 
        })
      } catch {
        return dateString
      }
    }

    const formatCurrency = (amount) => {
      try {
        return new Intl.NumberFormat('en-PH').format(amount || 0)
      } catch {
        return amount || 0
      }
    }

    const getDaysAgo = (dateString) => {
      try {
        const date = new Date(dateString)
        const now = new Date()
        const diffTime = Math.abs(now - date)
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        
        if (diffDays === 1) return '1 day ago'
        if (diffDays < 7) return `${diffDays} days ago`
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
        return `${Math.floor(diffDays / 30)} months ago`
      } catch {
        return ''
      }
    }

    const getDeliveryStatus = (order) => {
      try {
        const expectedDate = new Date(order.expectedDelivery)
        const now = new Date()
        
        if (order.status === 'delivered') return 'Delivered'
        if (order.status === 'cancelled') return 'Cancelled'
        
        const diffTime = expectedDate - now
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        
        if (diffDays < 0) return `${Math.abs(diffDays)} days overdue`
        if (diffDays === 0) return 'Due today'
        if (diffDays === 1) return 'Due tomorrow'
        return `${diffDays} days remaining`
      } catch {
        return ''
      }
    }

    const getDeliveryStatusClass = (order) => {
      try {
        const expectedDate = new Date(order.expectedDelivery)
        const now = new Date()
        const diffDays = Math.ceil((expectedDate - now) / (1000 * 60 * 60 * 24))
        
        if (order.status === 'delivered') return 'text-success'
        if (order.status === 'cancelled') return 'text-tertiary-medium'
        if (diffDays < 0) return 'text-danger'
        if (diffDays <= 2) return 'text-warning'
        return 'text-tertiary-medium'
      } catch {
        return 'text-tertiary-medium'
      }
    }

    const getStatusBadgeClass = (status) => {
      const classes = {
        'pending': 'bg-warning text-dark',
        'confirmed': 'bg-info text-white',
        'in_transit': 'bg-primary text-white',
        'delivered': 'bg-success text-white',
        'cancelled': 'bg-danger text-white'
      }
      return classes[status] || 'bg-secondary text-white'
    }

    const getStatusText = (status) => {
      const texts = {
        'pending': 'Pending',
        'confirmed': 'Confirmed',
        'in_transit': 'In Transit',
        'delivered': 'Delivered',
        'cancelled': 'Cancelled'
      }
      return texts[status] || status
    }

    const getRowClass = (order) => {
      if (order.status === 'cancelled') return 'text-muted'
      return ''
    }

    // Initialize - fetch from backend
    onMounted(async () => {
      await refreshData()
    })

    return {
      ordersComposable,
      loading,
      error,
      currentPage,
      itemsPerPage,
      statusFilter,
      supplierFilter,
      dateFilter,
      searchFilter,
      showOrderModal,
      selectedOrder,
      showEditModal,
      editingOrder,
      displayOrders,
      supplierOptions,
      paginatedOrders,
      totalPages,
      startItem,
      endItem,
      visiblePages,
      hasFilters,
      canEditOrder,
      canEditLimited,
      getEditTooltip,
      getEditButtonClass,
      goBack,
      refreshData,
      applyFilters,
      clearSearch,
      clearAllFilters,
      goToPage,
      viewOrder,
      closeModal,
      closeEditModal,
      editOrder,
      downloadOrder,
      exportOrders,
      saveOrderChanges,
      addNewItem,
      removeItem,
      calculateTotal,
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
.orders-history-page {
  min-height: 100vh;
}

.sticky-top {
  position: sticky;
  top: 0;
  z-index: 10;
}

.modal-backdrop.show {
  opacity: 0.5;
}

.table th {
  border-bottom: 2px solid var(--border-primary);
  font-weight: 600;
  font-size: 0.875rem;
}

.table td {
  vertical-align: middle;
  border-bottom: 1px solid var(--border-secondary);
}

.table tbody tr:hover {
  background-color: var(--state-hover);
}

.page-link {
  border-color: var(--border-primary);
}

.page-link:hover {
  background-color: var(--state-hover);
  border-color: var(--border-accent);
}

.page-item.active .page-link {
  background-color: var(--accent);
  border-color: var(--accent);
}

.page-item.disabled .page-link {
  background-color: var(--surface-secondary);
}
</style>