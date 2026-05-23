<template>
  <div class="promotions-page">
    <div class="page-header">
      <h1 class="page-title">Promotion Management</h1>
    </div>

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

    <div v-if="loading && promotions.length === 0" class="loading-state">
      <div class="spinner-border"></div>
      <p>Loading promotions...</p>
    </div>

    <div v-if="error" class="error-state">
      <div class="alert alert-danger">
        <p>{{ error }}</p>
        <button class="btn btn-primary" @click="refreshPromotions">Try Again</button>
      </div>
    </div>

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
            <input type="checkbox" class="form-check-input"
                   @change="toggleSelectAll" :checked="isAllSelected"
                   :indeterminate.prop="isIndeterminate" />
          </th>
          <th>Promotion Name</th>
          <th>Discount Type</th>
          <th>Discount Value</th>
          <th>Start Date</th>
          <th>End Date</th>
          <th>Status</th>
          <th>Min Purchase</th>
          <th>Per Customer Limit</th>
          <th>Last Updated</th>
          <th class="actions-column">Actions</th>
        </tr>
      </template>

      <template #body>
        <tr v-for="promotion in promotions" :key="promotion.promotion_id"
            :class="{ 'table-primary': selectedPromotions.includes(promotion.promotion_id) }">
          <td class="checkbox-column">
            <input type="checkbox" class="form-check-input"
                   :value="promotion.promotion_id" v-model="selectedPromotions" />
          </td>
          <td>{{ promotion.promotion_name }}</td>
          <td>
            <span class="badge" :class="getDiscountTypeBadgeClass(promotion.discount_type)">
              {{ formatDiscountType(promotion.discount_type) }}
            </span>
          </td>
          <td class="text-tertiary-medium">
            {{ formatDiscountValue(promotion.discount_value, promotion.discount_type) }}
          </td>
          <td class="text-tertiary-medium">{{ formatDate(promotion.start_date) }}</td>
          <td class="text-tertiary-medium">{{ formatDate(promotion.end_date) }}</td>
          <td>
            <span class="badge" :class="getStatusBadgeClass(getEffectiveStatus(promotion))">
              {{ formatStatus(getEffectiveStatus(promotion)) }}
            </span>
          </td>
          <td class="text-tertiary-medium">₱{{ promotion.min_purchase_amount ?? 100 }}</td>
          <td class="text-tertiary-medium">{{ promotion.per_customer_limit || 'Unlimited' }}</td>
          <td class="text-tertiary-medium">{{ formatDateTime(promotion.last_updated) }}</td>
          <td>
            <div class="d-flex gap-1 justify-content-start">
              <button class="btn btn-outline btn-sm action-btn action-btn-view"
                      @click="viewPromotion(promotion)" title="View Details">
                <Eye :size="14" />
              </button>
              <button class="btn btn-outline btn-sm action-btn action-btn-edit"
                      @click="editPromotion(promotion)" title="Edit Promotion">
                <Edit :size="14" />
              </button>
              <button v-if="promotion.status === 'active'"
                      class="btn btn-outline btn-sm action-btn action-btn-pause"
                      @click="handleDeactivatePromotion(promotion)"
                      :disabled="togglingStatus[promotion.promotion_id]" title="Deactivate Promotion">
                <PauseCircle :size="14" v-if="!togglingStatus[promotion.promotion_id]" />
                <span v-else class="spinner-border spinner-border-sm"></span>
              </button>
              <button v-else-if="promotion.status === 'inactive' || promotion.status === 'draft'"
                      class="btn btn-outline btn-sm action-btn action-btn-play"
                      @click="handleActivatePromotion(promotion)"
                      :disabled="togglingStatus[promotion.promotion_id]" title="Activate Promotion">
                <PlayCircle :size="14" v-if="!togglingStatus[promotion.promotion_id]" />
                <span v-else class="spinner-border spinner-border-sm"></span>
              </button>
              <button class="btn btn-outline btn-sm action-btn action-btn-delete"
                      @click="handleDeletePromotion(promotion)" title="Delete Promotion">
                <Trash2 :size="14" />
              </button>
            </div>
          </td>
        </tr>
      </template>
    </TableTemplate>

    <div v-if="!loading && promotions.length === 0 && !error" class="empty-state">
      <div class="card">
        <div class="card-body">
          <p class="empty-message">No promotions found</p>
          <p class="empty-submessage">Get started by creating your first promotional campaign</p>
          <button class="btn btn-add" @click="handleSinglePromo">Add First Promotion</button>
        </div>
      </div>
    </div>

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

const {
  promotions, loading, error, pagination, filters, searchQuery,
  selectedPromotions, fetchPromotions,
  deletePromotion: deletePromotionAction,
  deleteMultiplePromotions,
  activatePromotion: activatePromotionAction,
  deactivatePromotion: deactivatePromotionAction,
  setFilters, setSearchQuery, setPage, clearSelection
} = usePromotions()

const { success: showSuccess, error: showError } = useToast()
const searchDebounce = ref(null)
const addPromoModal = ref(null)
const exporting = ref(false)
const togglingStatus = ref({})

const isAllSelected = computed(() =>
  promotions.value.length > 0 && selectedPromotions.value.length === promotions.value.length
)
const isIndeterminate = computed(() =>
  selectedPromotions.value.length > 0 && selectedPromotions.value.length < promotions.value.length
)

const addOptions = computed(() => [{
  key: 'single', icon: 'Plus', title: 'Add Single Promotion',
  description: 'Create a new promotional campaign'
}])

const selectionActions = computed(() => [{
  key: 'delete', icon: 'Trash2', label: 'Delete',
  buttonClass: selectedPromotions.value.length > 0 ? 'btn-delete-dynamic has-items' : 'btn-delete-dynamic no-items'
}])

const filterOptions = computed(() => [
  {
    key: 'discountType', label: 'Discount Type', value: filters.value.discountType,
    options: [
      { value: 'all', label: 'All Types' },
      { value: 'percentage', label: 'Percentage' },
      { value: 'fixed_amount', label: 'Fixed Amount' }
    ]
  },
  {
    key: 'status', label: 'Status', value: filters.value.status,
    options: [
      { value: 'all', label: 'All Status' },
      { value: 'active', label: 'Active' },
      { value: 'inactive', label: 'Inactive' },
      { value: 'expired', label: 'Expired' },
      { value: 'draft', label: 'Draft' }
    ]
  }
])

const handleAddAction = (actionKey) => { if (actionKey === 'single') handleSinglePromo() }
const handleSelectionAction = async (actionKey) => { if (actionKey === 'delete') await deleteSelected() }
const handleFilterChange = (filterKey, value) => { setFilters({ [filterKey]: value }); fetchPromotions() }
const handleSearchInput = (value) => {
  setSearchQuery(value)
  if (searchDebounce.value) clearTimeout(searchDebounce.value)
  searchDebounce.value = setTimeout(() => fetchPromotions(), 300)
}
const handleSearchClear = () => {
  setSearchQuery('')
  if (searchDebounce.value) clearTimeout(searchDebounce.value)
  fetchPromotions()
}
const toggleSelectAll = (event) => {
  if (event.target.checked) selectedPromotions.value = promotions.value.map(p => p.promotion_id)
  else clearSelection()
}
const handlePageChange = (page) => { setPage(page); fetchPromotions() }
const refreshPromotions = async () => { clearSelection(); await fetchPromotions() }
const handleSinglePromo = () => { addPromoModal.value?.openAdd?.() }

const exportData = async () => {
  exporting.value = true
  try {
    const data = promotions.value
    if (!Array.isArray(data) || data.length === 0) throw new Error('No data')
    const keys = Object.keys(data[0])
    const csvRows = [keys.join(','), ...data.map(row => keys.map(key => `"${String(row[key] ?? '').replace(/"/g, '""')}"`).join(','))]
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `promotions_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
    showSuccess('✅ Export completed!')
  } catch (err) { showError('❌ Export failed: ' + err.message) }
  finally { exporting.value = false }
}

const deleteSelected = async () => {
  if (selectedPromotions.value.length === 0) return
  if (!confirm(`Delete ${selectedPromotions.value.length} promotion(s)?`)) return
  const result = await deleteMultiplePromotions(selectedPromotions.value)
  if (result.success) {
    showSuccess(`✅ Deleted ${result.results.filter(r => r.success).length} promotion(s)`)
    clearSelection()
    await fetchPromotions()
  } else showError('❌ Some promotions could not be deleted')
}

const handleDeletePromotion = async (promotion) => {
  if (!confirm(`Delete "${promotion.promotion_name}"?`)) return
  const result = await deletePromotionAction(promotion.promotion_id)
  result.success ? showSuccess('✅ Deleted successfully') : showError('❌ ' + (result.message || 'Delete failed'))
  await fetchPromotions()
}

const handleActivatePromotion = async (promotion) => {
  if (!confirm(`Activate "${promotion.promotion_name}"?`)) return
  togglingStatus.value[promotion.promotion_id] = true
  const result = await activatePromotionAction(promotion.promotion_id)
  if (result?.success) {
    showSuccess(`✅ Activated "${promotion.promotion_name}"`)
    await fetchPromotions()
  } else showError('❌ ' + (result?.message || 'Activation failed'))
  togglingStatus.value[promotion.promotion_id] = false
}

const handleDeactivatePromotion = async (promotion) => {
  if (!confirm(`Deactivate "${promotion.promotion_name}"?`)) return
  togglingStatus.value[promotion.promotion_id] = true
  const result = await deactivatePromotionAction(promotion.promotion_id)
  if (result?.success) {
    showSuccess(`✅ Deactivated "${promotion.promotion_name}"`)
    await fetchPromotions()
  } else showError('❌ ' + (result?.message || 'Deactivation failed'))
  togglingStatus.value[promotion.promotion_id] = false
}

const handlePromotionSaved = async () => { await refreshPromotions() }
const viewPromotion = (p) => addPromoModal.value?.openView?.(p)
const editPromotion = (p) => addPromoModal.value?.openEdit?.(p)

// Formatting
const formatDiscountType = (type) => ({ percentage: 'Percentage', fixed_amount: 'Fixed Amount' }[type] || type)
const formatDiscountValue = (value, type) => {
  if (!value) return '—'
  if (typeof value === 'string' && value.includes('%')) return value
  if (type === 'fixed_amount') return `₱${value}`
  return value
}

// Returns the display status based on dates, overriding the stored status when needed.
// A stored 'active' is shown as 'scheduled' if the start date is in the future,
// or 'expired' if the end date has already passed.
const getEffectiveStatus = (promotion) => {
  const now = new Date()
  const start = promotion.start_date ? new Date(promotion.start_date) : null
  const end = promotion.end_date ? new Date(promotion.end_date) : null
  if (promotion.status === 'active') {
    if (start && now < start) return 'scheduled'
    if (end && now > end) return 'expired'
  }
  return promotion.status
}

const formatStatus = (status) => ({
  active: 'Active', inactive: 'Inactive', expired: 'Expired',
  draft: 'Draft', scheduled: 'Scheduled'
}[status] || status)
const formatDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '—'
const formatDateTime = (d) => d ? new Date(d).toLocaleString() : '—'
const getDiscountTypeBadgeClass = (type) => ({ percentage: 'bg-primary', fixed_amount: 'bg-success' }[type] || 'bg-secondary')
const getStatusBadgeClass = (status) => ({
  active: 'bg-success', inactive: 'bg-secondary',
  expired: 'bg-danger', draft: 'bg-warning', scheduled: 'bg-info'
}[status] || 'bg-secondary')

onMounted(async () => { await fetchPromotions() })
</script>

<style scoped>
/* Keep existing styles, unchanged */
.promotions-page { padding: 1.5rem; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 1.5rem; }
.page-title { font-size: 2rem; font-weight: 600; color: var(--text-primary); margin: 0 0 0.25rem 0; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 3rem; background: var(--surface-primary); border-radius: 0.75rem; box-shadow: var(--shadow-md); margin-top: 1rem; }
.spinner-border { width: 2rem; height: 2rem; border: 0.25em solid currentColor; border-right-color: transparent; border-radius: 50%; animation: spinner-border 0.75s linear infinite; }
.spinner-border-sm { width: 0.875rem; height: 0.875rem; border-width: 0.15em; }
@keyframes spinner-border { to { transform: rotate(360deg); } }
.alert { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; }
.alert-danger { background-color: var(--status-error-bg); color: var(--status-error); border: 1px solid var(--status-error); }
.empty-state .card { background: var(--surface-primary); border: 1px solid var(--border-secondary); border-radius: 0.75rem; }
.empty-state .card-body { padding: 3rem; }
.empty-message { font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; }
.empty-submessage { color: var(--text-tertiary); margin-bottom: 1.5rem; }
.checkbox-column { width: 40px; text-align: center; }
.actions-column { width: 180px; text-align: left; }
.d-flex { display: flex; }
.gap-1 { gap: 0.25rem; }
.justify-content-start { justify-content: flex-start; }
.badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.badge.bg-primary { background: var(--primary-light); color: var(--primary-dark); }
.badge.bg-warning { background: var(--status-warning-bg); color: var(--status-warning); }
.badge.bg-info { background: var(--status-info-bg); color: var(--status-info); }
.badge.bg-success { background: var(--status-success-bg); color: var(--status-success); }
.badge.bg-secondary { background: var(--surface-tertiary); color: var(--text-tertiary); }
.badge.bg-info { background: var(--status-info-bg); color: var(--status-info); }
.badge.bg-danger { background: var(--status-error-bg); color: var(--status-error); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>