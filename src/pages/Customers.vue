<template>
  <div class="page-container p-4">

    <!-- Loading State -->
    <div v-if="isLoading && !hasCustomers" class="text-center py-12">
      <div class="spinner-border text-accent mb-4" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="text-secondary">Loading customers...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="status-error rounded-lg p-4 mb-4">
      <h3 class="text-lg fw-medium text-status-error mb-2">Error Loading Customers</h3>
      <p class="text-status-error mb-3">{{ error }}</p>
      <button 
        @click="handleRetry" 
        class="btn btn-submit transition-theme"
        :disabled="isLoading"
      >
        {{ isLoading ? 'Retrying...' : 'Try Again' }}
      </button>
    </div>

    <!-- Action Bar -->
    <ActionBar
      v-if="!isLoading || hasCustomers"
      entity-name="customer"
      add-button-text="ADD CUSTOMER"
      search-placeholder="Search customers..."
      :add-options="addOptions"
      :selected-items="selectedCustomers"
      :selection-actions="selectionActions"
      :filters="filters"
      :search-value="searchValue"
      :exporting="exporting"
      :show-columns-button="false"
      @add-action="handleAddAction"
      @selection-action="handleSelectionAction"
      @filter-change="handleFilterChange"
      @search-input="handleSearchInput"
      @search-clear="handleSearchClear"
      @export="handleExport"
    />

    <!-- Hidden input for Import -->
    <input
      id="customer-import"
      type="file"
      accept=".csv"
      class="d-none"
      @change="handleImport"
    />

    <!-- Table -->
    <TableTemplate
        v-if="hasCustomers || isLoading"
        :items-per-page="itemsPerPage"
        :total-items="totalItemsForPagination"
        :current-page="currentPage"
        :show-pagination="totalItemsForPagination > itemsPerPage"
        @page-changed="handlePageChange"
        class="shadow-md"
      >
      <template #header>
        <tr>
          <th style="width: 150px;">Customer ID</th>
          <th style="width: 140px;">Username</th>
          <th>Full Name</th>
          <th>Email</th>
          <th>Phone</th>
          <th style="width: 120px;">Loyalty Points</th>
          <th style="width: 100px;">Status</th>
          <th style="width: 140px;">Date Created</th>
          <th style="width: 120px;" class="text-center">Actions</th>
        </tr>
      </template>

      <template #body>
         <tr v-for="customer in paginatedCustomers" :key="customer.customer_id" class="hover-surface transition-theme">
          <td>
            <span class="badge bg-primary">{{ customer.customer_id }}</span>
          </td>
          <td>
            <div class="fw-medium text-tertiary-dark">
              {{ customer.username || 'N/A' }}
            </div>
          </td>
          <td>
            <div class="fw-medium text-primary">
              {{ customer.full_name || 'N/A' }}
            </div>
          </td>
          <td><div class="text-secondary">{{ customer.email }}</div></td>
          <td><div class="text-secondary">{{ customer.phone_number || 'N/A' }}</div></td>
          <td class="text-center">
            <span class="badge bg-success text-inverse fw-medium">
              {{ customer.loyalty_points || 0 }}
            </span>
          </td>
          <td class="text-center">
            <span
              class="badge fw-medium"
              :class="customer.status === 'active' ? 'bg-success text-inverse' : 'surface-tertiary text-tertiary border-theme'"
            >
              {{ customer.status || 'active' }}
            </span>
          </td>
          <td>
            <div class="text-tertiary small">
              {{ formatDate(customer.date_created) }}
            </div>
          </td>
          <td>
            <div class="d-flex justify-content-center gap-1">
              <!-- ✅ Fixed View Button -->
              <button 
                class="btn btn-outline-primary action-btn btn-icon-only btn-sm shadow-sm"
                @click="openViewCustomerModal(customer)"
                title="View Customer Details"
              >
                <Eye :size="14" />
              </button>

              <!-- ✅ Fixed Edit Button -->
              <button 
                class="btn btn-outline-secondary action-btn btn-icon-only btn-sm shadow-sm"
                @click="openEditCustomerModal(customer)"
                title="Edit Customer"
              >
                <Edit :size="14" />
              </button>

              <button 
                class="btn btn-outline-danger action-btn btn-icon-only btn-sm shadow-sm"
                @click="deleteCustomer(customer)"
                title="Delete Customer"
                :disabled="deletingCustomerId === customer.customer_id"
              >
                <Trash2 v-if="deletingCustomerId !== customer.customer_id" :size="14" />
                <div v-else class="spinner-border spinner-border-sm"></div>
              </button>
            </div>
          </td>
        </tr>
      </template>
    </TableTemplate>

    <!-- Empty State -->
    <div
      v-if="!hasCustomers && !isLoading && !error"
      class="text-center py-12 surface-card rounded shadow-md"
    >
      <div class="display-1 mb-4">👥</div>
      <h3 class="h4 fw-medium text-primary mb-2">No Customers Found</h3>
      <p class="text-secondary mb-4">Get started by adding your first customer.</p>
      <button 
        class="btn btn-submit px-4 py-2 shadow-sm transition-theme"
        @click="openAddCustomerModal"
      >
        Add First Customer
      </button>
    </div>

  </div>

  <!-- Customer Modal -->
  <AddCustomerModal
    ref="customerModal"
    :mode="modalMode"
    :customer="selectedCustomer"
    @close="handleModalClose"
    @success="handleModalSuccess"
    @mode-changed="handleModeChanged"
  />

  <!-- Delete Confirmation Modal -->
  <DeleteConfirmationModal
    ref="deleteModal"
    :is-loading="deletingCustomerId !== null"
    @confirm="confirmDelete"
    @cancel="cancelDelete"
  />
</template>


<script setup>
import { ref, computed, onMounted } from 'vue'
import { Eye, Edit, Trash2 } from 'lucide-vue-next'
import { useCustomers } from '@/composables/api/useCustomers.js'
import { useToast } from '@/composables/ui/useToast.js'
import TableTemplate from '@/components/common/TableTemplate.vue'
import ActionBar from '@/components/common/ActionBar.vue'
import AddCustomerModal from '@/components/customers/AddCustomerModal.vue'
import DeleteConfirmationModal from '@/components/common/DeleteConfirmationModal.vue'

const toast = useToast()

const addOptions = [
  { key: 'single', icon: 'Plus', title: 'Add Customer', description: 'Add manually' },
  { key: 'import', icon: 'Upload', title: 'Import Customers', description: 'Upload CSV/Excel' },
  { key: 'template', icon: 'FileText', title: 'Download Template', description: 'For imports' }
];


// =====================
// COMPOSABLE HOOKS
// =====================
const {
  customers,
  isLoading,
  error,
  statistics,
  totalCustomers,
  hasMore,
  nextKey,
  hasCustomers,
  fetchCustomers,
  fetchStatistics,
  deleteCustomer: deleteCustomerAPI,
  exportCustomers,
  importCustomers,
  clearError
} = useCustomers()

// =====================
// STATE & MODAL REFS
// =====================
const currentPage = ref(1)
const itemsPerPage = ref(10)
const pageKeys = ref({ 1: null }) // cursor map: page number → start_key
const exporting = ref(false)
const searchValue = ref('')
const customerModal = ref(null)
const searchDebounce = ref(null)
const modalMode = ref('create')
const selectedCustomer = ref(null)
const customerToDelete = ref(null)
const deletingCustomerId = ref(null)
const selectedCustomers = ref([])
const selectionActions = ref([])

// =====================
// FILTERS
// =====================
const filters = ref([
  {
    key: 'status',
    label: 'Status',
    value: 'all',
    options: [
      { value: 'all', label: 'All customers' },
      { value: 'active', label: 'Active' },
      { value: 'inactive', label: 'Inactive' }
    ]
  },
  {
    key: 'points',
    label: 'Loyalty Points',
    value: 'all',
    options: [
      { value: 'all', label: 'All points' },
      { value: 'high', label: 'High (100+)' },
      { value: 'medium', label: 'Medium (50-99)' },
      { value: 'low', label: 'Low (0-49)' }
    ]
  }
])

// =====================
// QUERY PARAM MAPPER
// =====================
const buildQueryParams = () => {
  const params = {}
  const statusFilter = filters.value.find(f => f.key === 'status')?.value
  if (statusFilter && statusFilter !== 'all') params.status = statusFilter
  const pointsFilter = filters.value.find(f => f.key === 'points')?.value
  if (pointsFilter && pointsFilter !== 'all') {
    if (pointsFilter === 'high') params.min_loyalty_points = 100
    else if (pointsFilter === 'medium') {
      params.min_loyalty_points = 50
      params.max_loyalty_points = 99
    } else if (pointsFilter === 'low') {
      params.min_loyalty_points = 0
      params.max_loyalty_points = 49
    }
  }
  if (searchValue.value?.trim()) params.search = searchValue.value.trim()
  params.limit = itemsPerPage.value
  const startKey = pageKeys.value[currentPage.value]
  if (startKey) params.start_key = startKey
  return params
}

const resetPageKeys = () => {
  pageKeys.value = { 1: null }
}

// =====================
// TABLE DATA
// =====================
const paginatedCustomers = computed(() => customers.value)

// Derives total item count for TableTemplate without a true total from the backend.
// When has_more is true: signal at least (currentPage + 1) pages worth of items.
// When on the last page: compute exact total from pages seen so far.
const totalItemsForPagination = computed(() => {
  if (hasMore.value) {
    return currentPage.value * itemsPerPage.value + 1
  }
  return (currentPage.value - 1) * itemsPerPage.value + customers.value.length
})

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch { return 'Invalid Date' }
}

// =====================
// FETCH WITH CURSOR TRACKING
// =====================
const fetchAndTrackCursor = async () => {
  const response = await fetchCustomers(buildQueryParams())
  if (hasMore.value && nextKey.value) {
    pageKeys.value[currentPage.value + 1] = nextKey.value
  }
  return response
}

// =====================
// CORE HANDLERS
// =====================
const handleRetry = async () => {
  clearError()
  resetPageKeys()
  currentPage.value = 1
  await fetchAndTrackCursor()
}

const handlePageChange = async (page) => {
  currentPage.value = page
  await fetchAndTrackCursor()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleFilterChange = async (filterKey, value) => {
  const filter = filters.value.find(f => f.key === filterKey)
  if (filter) filter.value = value
  resetPageKeys()
  currentPage.value = 1
  await fetchAndTrackCursor()
}

const handleSearchInput = (value) => {
  searchValue.value = value
  if (searchDebounce.value) clearTimeout(searchDebounce.value)
  searchDebounce.value = setTimeout(async () => {
    resetPageKeys()
    currentPage.value = 1
    await fetchAndTrackCursor()
  }, 400)
}

const handleSearchClear = async () => {
  searchValue.value = ''
  if (searchDebounce.value) clearTimeout(searchDebounce.value)
  resetPageKeys()
  currentPage.value = 1
  await fetchAndTrackCursor()
}

const handleImport = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const result = await importCustomers(file)
    toast.success(result?.message || 'Import completed.')
    resetPageKeys()
    currentPage.value = 1
    await fetchAndTrackCursor()
  } catch (err) {
    toast.error(`Import failed: ${err.message}`)
  }
}

const handleExport = async () => {
  exporting.value = true
  try {
    const params = {}
    const statusFilter = filters.value.find(f => f.key === 'status')?.value
    if (statusFilter && statusFilter !== 'all') params.status = statusFilter
    await exportCustomers(params)
  } catch (err) {
    toast.error(`Export failed: ${err.message}`)
  } finally {
    exporting.value = false
  }
}

const downloadTemplate = () => {
  const csvTemplate = `username,full_name,email,phone,loyalty_points,status\njohndoe,John Doe,john@example.com,09171234567,100,active\njanedoe,Jane Doe,jane@example.com,09181112222,50,inactive\n`
  const blob = new Blob([csvTemplate], { type: 'text/csv' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'customer_import_template.csv'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

const handleAddAction = (actionKey) => {
  switch (actionKey) {
    case 'single': openAddCustomerModal(); break
    case 'import': document.getElementById('customer-import')?.click(); break
    case 'template': downloadTemplate(); break
  }
}

const handleSelectionAction = (actionKey, selectedItems) => {
  switch (actionKey) {
    case 'delete': break
  }
}

const openAddCustomerModal = () => {
  modalMode.value = 'create'
  selectedCustomer.value = null
  customerModal.value?.openModal()
}
const openViewCustomerModal = (customer) => {
  modalMode.value = 'view'
  selectedCustomer.value = customer
  customerModal.value?.openModal()
}
const openEditCustomerModal = (customer) => {
  modalMode.value = 'edit'
  selectedCustomer.value = customer
  customerModal.value?.openModal()
}
const handleModalClose = () => {
  modalMode.value = 'create'
  selectedCustomer.value = null
}
const handleModalSuccess = async () => {
  try {
    resetPageKeys()
    currentPage.value = 1
    await fetchAndTrackCursor()
  } catch (error) {
    console.error('Failed to refresh customer list:', error)
  }
}

// delete
const openDeleteModal = (customer) => {
  customerToDelete.value = customer
  deleteModal.value?.openModal({
    title: 'Delete Customer',
    message: `Are you sure you want to delete customer <strong>${customer.full_name}</strong>?<br><br><small>This will hide the customer from the active list, but they can be restored later if needed.</small>`,
    confirmText: 'Delete Customer'
  })
}
const closeDeleteModal = () => {
  customerToDelete.value = null
  deleteModal.value?.closeModal()
}
const cancelDelete = closeDeleteModal
const handleModeChanged = (mode) => { modalMode.value = mode }
const confirmDelete = async () => {
  if (!customerToDelete.value) return
  try {
    deletingCustomerId.value = customerToDelete.value.customer_id
    await deleteCustomerAPI(deletingCustomerId.value)
    closeDeleteModal()
    deletingCustomerId.value = null
    resetPageKeys()
    currentPage.value = 1
    await fetchAndTrackCursor()
  } catch (error) {
    console.error('Failed to delete customer:', error)
  }
}
const deleteCustomer = (customer) => {
  openDeleteModal(customer)
}

// INIT
onMounted(async () => {
  try {
    await Promise.all([fetchAndTrackCursor(), fetchStatistics()])
  } catch (err) {
    console.error('Failed to initialize customers page:', err)
  }
})
</script>



<style scoped>
/* Utility classes that complement the semantic system */
.spinner-border {
  width: 3rem;
  height: 3rem;
  border-width: 0.3em;
}

.spinner-border-sm {
  width: 0.875rem;
  height: 0.875rem;
  border-width: 0.125em;
}

.display-1 {
  font-size: 3.5rem;
  line-height: 1.2;
}

.small {
  font-size: 0.875rem;
}

/* Badge enhancements */
.badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
}

/* Action button spacing */
.action-btn {
  transition: all 0.2s ease;
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* Responsive typography */
@media (max-width: 768px) {
  .p-4 {
    padding: 1rem;
  }
  
  .display-1 {
    font-size: 2.5rem;
  }
  
  .h4 {
    font-size: 1.25rem;
  }
}

/* Ensure proper text color inheritance for buttons */
.btn-icon-only {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* Loading animation */
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.spinner-border {
  animation: spin 0.75s linear infinite;
}
</style>