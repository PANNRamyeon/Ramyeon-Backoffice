<template>
  <div class="promotions-page">
    <!-- Page Header -->
    <div class="page-header">
      <h1 class="page-title">Promotion Management</h1>
      <p class="page-subtitle">Manage promotional campaigns and discounts</p>
    </div>

    <!-- Action Bar -->
    <ActionBar
      entity-name="promotion"
      add-button-text="ADD PROMO"
      search-placeholder="Search promotions by name..."
      :add-options="addOptions"
      :selected-items="selectedPromotions"
      :selection-actions="selectionActions"
      :filters="filterOptions"
      :search-value="searchQuery"
      :show-columns-button="false"
      :show-export-button="true"
      :exporting="exporting"
      @add-action="handleAddAction"
      @selection-action="handleSelectionAction"
      @filter-change="handleFilterChange"
      @search-input="handleSearchInput"
      @search-clear="handleSearchClear"
      @export="exportData"
    />

    <!-- Loading State -->
    <div v-if="loading && promotions.length === 0" class="loading-state">
      <div class="spinner-border"></div>
      <p>Loading promotions...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-state">
      <div class="alert alert-danger">
        <p>{{ error }}</p>
        <button class="btn btn-primary" @click="refreshPromotions">
          Try Again
        </button>
      </div>
    </div>

    <!-- Data Table -->
    <TableTemplate
      v-if="!loading || promotions.length > 0"
      :items-per-page="pagination.items_per_page"
      :total-items="pagination.total_items"
      :current-page="pagination.current_page"
      :show-pagination="true"
      @page-changed="handlePageChange"
    >
      <template #header>
        <tr>
          <th class="checkbox-column">
            <input 
              type="checkbox" 
              class="form-check-input"
              @change="toggleSelectAll" 
              :checked="isAllSelected"
              :indeterminate.prop="isIndeterminate"
            />
          </th>
          <th>Promotion Name</th>
          <th>Discount Type</th>
          <th>Discount Value</th>
          <th>Start Date</th>
          <th>End Date</th>
          <th>Status</th>
          <th>Last Updated</th>
          <th class="actions-column">Actions</th>
        </tr>
      </template>

      <template #body>
        <tr 
          v-for="promotion in promotions" 
          :key="promotion.promotion_id"
          :class="{ 'table-primary': selectedPromotions.includes(promotion.promotion_id) }"
        >
          <td class="checkbox-column">
            <input 
              type="checkbox" 
              class="form-check-input"
              :value="promotion.promotion_id"
              v-model="selectedPromotions"
            />
          </td>
          <td>{{ promotion.promotion_name }}</td>
          <td>
            <span 
              class="badge"
              :class="getDiscountTypeBadgeClass(promotion.discount_type)"
            >
              {{ formatDiscountType(promotion.discount_type) }}
            </span>
          </td>
          <td class="text-tertiary-medium">
            {{ formatDiscountValue(promotion.discount_value, promotion.discount_type) }}
          </td>
          <td class="text-tertiary-medium">
            {{ formatDate(promotion.start_date) }}
          </td>
          <td class="text-tertiary-medium">
            {{ formatDate(promotion.end_date) }}
          </td>
          <td>
            <span 
              class="badge"
              :class="getStatusBadgeClass(promotion.status)"
            >
              {{ formatStatus(promotion.status) }}
            </span>
          </td>
          <td class="text-tertiary-medium">
            {{ formatDateTime(promotion.last_updated) }}
          </td>
          <td>
            <div class="d-flex gap-1 justify-content-start">
              <!-- View Button -->
              <button
                class="btn btn-outline btn-sm action-btn action-btn-view"
                @click="viewPromotion(promotion)"
                title="View Details"
              >
                <Eye :size="14" />
              </button>
              
              <!-- Edit Button -->
              <button
                class="btn btn-outline btn-sm action-btn action-btn-edit"
                @click="editPromotion(promotion)"
                title="Edit Promotion"
              >
                <Edit :size="14" />
              </button>
              
              <!-- ✅ Deactivate/Reactivate Button -->
              <button
                v-if="promotion.status === 'active'"
                class="btn btn-outline btn-sm action-btn action-btn-pause"
                @click="handleDeactivatePromotion(promotion)"
                :disabled="togglingStatus[promotion.promotion_id]"
                title="Deactivate Promotion"
              >
                <PauseCircle :size="14" v-if="!togglingStatus[promotion.promotion_id]" />
                <span v-else class="spinner-border spinner-border-sm"></span>
              </button>
              
              <button
                v-else-if="promotion.status === 'inactive' || promotion.status === 'scheduled'"
                class="btn btn-outline btn-sm action-btn action-btn-play"
                @click="handleActivatePromotion(promotion)"
                :disabled="togglingStatus[promotion.promotion_id]"
                title="Activate Promotion"
              >
                <PlayCircle :size="14" v-if="!togglingStatus[promotion.promotion_id]" />
                <span v-else class="spinner-border spinner-border-sm"></span>
              </button>
              
              <!-- Delete Button -->
              <button
                class="btn btn-outline btn-sm action-btn action-btn-delete"
                @click="handleDeletePromotion(promotion)"
                title="Delete Promotion"
              >
                <Trash2 :size="14" />
              </button>
            </div>
          </td>
        </tr>
      </template>
    </TableTemplate>

    <!-- Empty State -->
    <div v-if="!loading && promotions.length === 0 && !error" class="empty-state">
      <div class="card">
        <div class="card-body">
          <p class="empty-message">No promotions found</p>
          <p class="empty-submessage">Get started by creating your first promotional campaign</p>
          <button class="btn btn-add" @click="handleSinglePromo">
            Add First Promotion
          </button>
        </div>
      </div>
    </div>

    <!-- Add Promo Modal -->
    <AddPromoModal ref="addPromoModal" @promotion-saved="handlePromotionSaved" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Eye, Edit, Trash2, PauseCircle, PlayCircle } from 'lucide-vue-next'
import ActionBar from '@/components/common/ActionBar.vue'
import TableTemplate from '@/components/common/TableTemplate.vue'
import AddPromoModal from '@/components/promotions/AddPromoModal.vue'
import { usePromotions } from '@/composables/api/usePromotions'
import { useToast } from '@/composables/ui/useToast'

// ✅ Composables
const {
  promotions,
  loading,
  error,
  pagination,
  filters,
  searchQuery,
  selectedPromotions,
  fetchPromotions,
  deletePromotion: deletePromotionAction,
  deleteMultiplePromotions,
  activatePromotion: activatePromotionAction,
  deactivatePromotion: deactivatePromotionAction,
  setFilters,
  setSearchQuery,
  setPage,
  clearSelection
} = usePromotions()

const { success: showSuccess, error: showError } = useToast()
const searchDebounce = ref(null)

// ✅ Local State
const addPromoModal = ref(null)
const exporting = ref(false)
const togglingStatus = ref({}) // Track loading state for each promo

// ✅ Computed
const isAllSelected = computed(() => {
  return promotions.value.length > 0 && selectedPromotions.value.length === promotions.value.length
})

const isIndeterminate = computed(() => {
  return selectedPromotions.value.length > 0 && selectedPromotions.value.length < promotions.value.length
})

const addOptions = computed(() => [
  {
    key: 'single',
    icon: 'Plus',
    title: 'Add Single Promotion',
    description: 'Create a new promotional campaign'
  }
])

const selectionActions = computed(() => [
  {
    key: 'delete',
    icon: 'Trash2',
    label: 'Delete',
    buttonClass: selectedPromotions.value.length > 0 ? 'btn-delete-dynamic has-items' : 'btn-delete-dynamic no-items'
  }
])

// ✅ Filter options for ActionBar
const filterOptions = computed(() => [
  {
    key: 'discountType',
    label: 'Discount Type',
    value: filters.value.discountType,
    options: [
      { value: 'all', label: 'All Types' },
      { value: 'percentage', label: 'Percentage' },
      { value: 'fixed_amount', label: 'Fixed Amount' },
      { value: 'buy_x_get_y', label: 'BOGO' }
    ]
  },
  {
    key: 'status',
    label: 'Status',
    value: filters.value.status,
    options: [
      { value: 'all', label: 'All Status' },
      { value: 'active', label: 'Active' },
      { value: 'inactive', label: 'Inactive' },
      { value: 'expired', label: 'Expired' },
      { value: 'scheduled', label: 'Scheduled' }
    ]
  }
])

// ✅ Methods
const handleAddAction = (actionKey) => {
  if (actionKey === 'single') {
    handleSinglePromo()
  }
}

const handleSelectionAction = async (actionKey) => {
  if (actionKey === 'delete') {
    await deleteSelected()
  }
}

const handleFilterChange = (filterKey, value) => {
  setFilters({ [filterKey]: value })
  fetchPromotions()
}


const handleSearchInput = (value) => {
  setSearchQuery(value)

  if (searchDebounce.value) clearTimeout(searchDebounce.value)

  searchDebounce.value = setTimeout(() => {
    fetchPromotions()
  }, 300)
}

const handleSearchClear = () => {
  setSearchQuery('')

  if (searchDebounce.value) clearTimeout(searchDebounce.value)

  fetchPromotions()
}


const toggleSelectAll = (event) => {
  if (event.target.checked) {
    selectedPromotions.value = promotions.value.map(p => p.promotion_id)
  } else {
    clearSelection()
  }
}


const handlePageChange = (page) => {
  setPage(page)
  fetchPromotions()
}


const refreshPromotions = async () => {
  clearSelection()
  await fetchPromotions()
}

const handleSinglePromo = () => {
  if (addPromoModal.value && addPromoModal.value.openAdd) {
    addPromoModal.value.openAdd()
  }
}

const exportData = async () => {
  exporting.value = true

  try {
    // Optional: apply filtering logic here if needed
    const data = promotions.value
    if (!Array.isArray(data) || data.length === 0) {
      throw new Error('No data available for export.')
    }
    const keys = Object.keys(data[0])
    const csvRows = [
      keys.join(','), // header
      ...data.map(row =>
        keys.map(key =>
          `"${row[key] !== undefined ? String(row[key]).replace(/"/g, '""') : ''}"`
        ).join(',')
      )
    ]
    const csvContent = csvRows.join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `promotions_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
    window.URL.revokeObjectURL(url)

    showSuccess('✅ Export completed successfully!')
  } catch (err) {
    console.error('Export error:', err)
    showError('❌ Export failed: ' + err.message)
  } finally {
    exporting.value = false
  }
}

const deleteSelected = async () => {
  if (selectedPromotions.value.length === 0) return
  
  const confirmed = confirm(`Delete ${selectedPromotions.value.length} promotion(s)?`)
  if (!confirmed) return

  try {
    const result = await deleteMultiplePromotions(selectedPromotions.value)
    
    if (result.success) {
      const successCount = result.results.filter(r => r.success).length
      showSuccess(`✅ Successfully deleted ${successCount} promotion(s)`)
      clearSelection()
      await fetchPromotions()
    } else {
      showError('❌ Some promotions could not be deleted')
    }
  } catch (err) {
    console.error('Bulk delete error:', err)
    showError('❌ Delete failed: ' + err.message)
  }
}

const handleDeletePromotion = async (promotion) => {
  const confirmed = confirm(`Delete promotion "${promotion.promotion_name}"?`)
  if (!confirmed) return

  try {
    const result = await deletePromotionAction(promotion.promotion_id)
    
    if (result.success) {
      showSuccess('✅ Promotion deleted successfully')
      await fetchPromotions()
    } else {
      showError('❌ Delete failed: ' + (result.message || 'Unknown error'))
    }
  } catch (err) {
    console.error('Delete error:', err)
    showError('❌ Delete failed: ' + err.message)
  }
}

// ✅ Activate Promotion
const handleActivatePromotion = async (promotion) => {
  const confirmed = confirm(`Activate promotion "${promotion.promotion_name}"?`)
  if (!confirmed) return

  try {
    togglingStatus.value[promotion.promotion_id] = true
    const result = await activatePromotionAction(promotion.promotion_id)
    
    if (result && result.success) {
      showSuccess(`✅ Promotion "${promotion.promotion_name}" activated successfully`)
      await fetchPromotions()
    } else {
      showError('❌ Activation failed: ' + (result?.message || 'Unknown error'))
    }
  } catch (err) {
    console.error('Activation error:', err)
    showError('❌ Activation failed: ' + err.message)
  } finally {
    togglingStatus.value[promotion.promotion_id] = false
  }
}

// ✅ Deactivate Promotion
const handleDeactivatePromotion = async (promotion) => {
  const confirmed = confirm(`Deactivate promotion "${promotion.promotion_name}"?`)
  if (!confirmed) return

  try {
    togglingStatus.value[promotion.promotion_id] = true
    const result = await deactivatePromotionAction(promotion.promotion_id)
    
    if (result && result.success) {
      showSuccess(`✅ Promotion "${promotion.promotion_name}" deactivated successfully`)
      await fetchPromotions()
    } else {
      showError('❌ Deactivation failed: ' + (result?.message || 'Unknown error'))
    }
  } catch (err) {
    console.error('Deactivation error:', err)
    showError('❌ Deactivation failed: ' + err.message)
  } finally {
    togglingStatus.value[promotion.promotion_id] = false
  }
}

const handlePromotionSaved = async () => {
  await refreshPromotions()
}

const viewPromotion = (promotion) => {
  if (addPromoModal.value && addPromoModal.value.openView) {
    addPromoModal.value.openView(promotion)
  }
}

const editPromotion = (promotion) => {
  if (addPromoModal.value && addPromoModal.value.openEdit) {
    addPromoModal.value.openEdit(promotion)
  }
}

// ✅ Formatting methods
const formatDiscountType = (type) => {
  const types = {
    'percentage': 'Percentage',
    'fixed_amount': 'Fixed Amount',
    'buy_x_get_y': 'BOGO'
  }
  return types[type] || type
}

const formatDiscountValue = (value, type) => {
  if (type === 'percentage') return `${value}%`
  if (type === 'fixed_amount') return `₱${value}`
  return value
}

const formatStatus = (status) => {
  const statuses = {
    'active': 'Active',
    'inactive': 'Inactive',
    'expired': 'Expired',
    'scheduled': 'Scheduled'
  }
  return statuses[status] || status
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}

const getDiscountTypeBadgeClass = (type) => {
  const classes = {
    'percentage': 'bg-primary',
    'fixed_amount': 'bg-success',
    'buy_x_get_y': 'bg-info'
  }
  return classes[type] || 'bg-secondary'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    'active': 'bg-success',
    'inactive': 'bg-secondary',
    'expired': 'bg-danger',
    'scheduled': 'bg-warning'
  }
  return classes[status] || 'bg-secondary'
}

// ✅ Lifecycle
onMounted(async () => {
  await fetchPromotions()
})
</script>

<style scoped>
/* ... keep all existing styles ... */
.promotions-page {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.page-subtitle {
  color: var(--text-tertiary);
  margin: 0;
  font-size: 0.875rem;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 3rem;
  background: var(--surface-primary);
  border-radius: 0.75rem;
  box-shadow: var(--shadow-md);
  margin-top: 1rem;
}

.spinner-border {
  width: 2rem;
  height: 2rem;
  border: 0.25em solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spinner-border 0.75s linear infinite;
}

.spinner-border-sm {
  width: 0.875rem;
  height: 0.875rem;
  border-width: 0.15em;
}

@keyframes spinner-border {
  to { transform: rotate(360deg); }
}

.alert {
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.alert-danger {
  background-color: var(--status-error-bg);
  color: var(--status-error);
  border: 1px solid var(--status-error);
}

.empty-state .card {
  background: var(--surface-primary);
  border: 1px solid var(--border-secondary);
  border-radius: 0.75rem;
}

.empty-state .card-body {
  padding: 3rem;
}

.empty-message {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-submessage {
  color: var(--text-tertiary);
  margin-bottom: 1.5rem;
}

.checkbox-column {
  width: 40px;
  text-align: center;
}

.actions-column {
  width: 180px;
  text-align: left;
}

.d-flex {
  display: flex;
}

.gap-1 {
  gap: 0.25rem;
}

.justify-content-start {
  justify-content: flex-start;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.bg-primary {
  background: var(--primary-light);
  color: var(--primary-dark);
}

.badge.bg-warning {
  background: var(--status-warning-bg);
  color: var(--status-warning);
}

.badge.bg-info {
  background: var(--status-info-bg);
  color: var(--status-info);
}

.badge.bg-success {
  background: var(--status-success-bg);
  color: var(--status-success);
}

.badge.bg-secondary {
  background: var(--surface-tertiary);
  color: var(--text-tertiary);
}

.badge.bg-danger {
  background: var(--status-error-bg);
  color: var(--status-error);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>