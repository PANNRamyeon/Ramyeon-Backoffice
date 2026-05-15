<template>
  <div v-if="isVisible" class="modal fade show" id="addPromoModal" tabindex="-1"
       aria-labelledby="addPromoModalLabel" style="display: block;" @click.self="handleClose">
    <div class="modal-dialog modal-lg modal-dialog-scrollable">
      <div class="modal-content surface-card border-theme">
        <div class="modal-header border-theme">
          <h5 class="modal-title text-primary" id="addPromoModalLabel">{{ modalTitle }}</h5>
          <button type="button" class="btn-close" @click="handleClose" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <!-- Warning for active promotion edit -->
          <div v-if="mode === 'edit' && selectedPromotion?.status === 'active'" class="alert alert-warning">
            <div class="d-flex align-items-start">
              <span class="me-2">⚠️</span>
              <div>
                <strong>Active Promotion:</strong> Discount settings cannot be modified while the promotion is active.
                Only name, description, dates, and usage limit can be changed.
              </div>
            </div>
          </div>

          <div v-if="error" class="alert alert-danger alert-dismissible fade show">
            {{ error }}
            <button type="button" class="btn-close" @click="clearError"></button>
          </div>

          <!-- ADD MODE -->
          <div v-if="mode === 'add'" class="add-mode">
            <form @submit.prevent="savePromotion">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Promotion Name <span class="text-danger">*</span></label>
                  <input type="text" class="form-control input-theme" v-model="formData.promotion_name" placeholder="Enter promotion name" required />
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Discount Type <span class="text-danger">*</span></label>
                  <select class="form-select input-theme" v-model="formData.discount_type" required>
                    <option value="">Select discount type</option>
                    <option value="percentage">Percentage</option>
                    <option value="fixed_amount">Fixed Amount</option>
                  </select>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Discount Value <span class="text-danger">*</span></label>
                  <div class="input-group">
                    <input type="number" class="form-control input-theme" v-model="formData.discount_value"
                           :placeholder="formData.discount_type === 'percentage' ? 'Enter percentage (e.g., 20)' : 'Enter amount (e.g., 50)'"
                           :min="formData.discount_type === 'percentage' ? 1 : 0"
                           :max="formData.discount_type === 'percentage' ? 100 : undefined"
                           step="0.01" required />
                    <span class="input-group-text surface-tertiary border-theme text-secondary">
                      {{ formData.discount_type === 'percentage' ? '%' : '₱' }}
                    </span>
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Status</label>
                  <select class="form-select input-theme" v-model="formData.status">
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Start Date <span class="text-danger">*</span></label>
                  <div class="date-picker-wrapper">
                    <VueDatePicker v-model="formData.start_date" :enable-time-picker="false" format="MM/dd/yyyy"
                                   placeholder="Select start date" :min-date="new Date()" auto-apply required />
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">End Date <span class="text-danger">*</span></label>
                  <div class="date-picker-wrapper">
                    <VueDatePicker v-model="formData.end_date" :enable-time-picker="false" format="MM/dd/yyyy"
                                   placeholder="Select end date" :min-date="formData.start_date || new Date()" auto-apply required />
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Usage Limit</label>
                  <input type="number" class="form-control input-theme" v-model="formData.usage_limit"
                         placeholder="Leave empty for unlimited" min="1" step="1" />
                  <small class="form-text text-tertiary">Maximum total number of times this promotion can be used (optional)</small>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Minimum Purchase (₱)</label>
                  <input type="number" class="form-control input-theme" v-model="formData.min_purchase_amount"
                         placeholder="100" min="0" step="0.01" />
                  <small class="form-text text-tertiary">Minimum cart total required. Default is ₱100. Set 0 for no minimum.</small>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Per Customer Limit</label>
                  <input type="number" class="form-control input-theme" v-model="formData.per_customer_limit"
                         placeholder="Leave empty for unlimited" min="1" step="1" />
                  <small class="form-text text-tertiary">Maximum number of times a single customer can use this promotion (optional)</small>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Apply to Category <span class="text-danger">*</span></label>
                  <select class="form-select input-theme" v-model="formData.affected_category" :disabled="loadingCategories" required>
                    <option value="" disabled>{{ loadingCategories ? 'Loading categories...' : 'Select category' }}</option>
                    <option v-for="category in categories" :key="category.value" :value="category.value">{{ category.label }}</option>
                  </select>
                </div>
                <div class="col-12 mb-3">
                  <label class="form-label text-secondary">Description</label>
                  <textarea class="form-control input-theme" v-model="formData.description" placeholder="Enter promotion description (optional)" rows="3"></textarea>
                </div>
                <div class="col-12 mb-3">
                  <label class="form-label text-secondary">Recurrence Rule (optional)</label>
                  <input type="text" class="form-control input-theme" v-model="formData.recurrence_rule"
                         placeholder="e.g., monthly:15,30 or yearly:12-25" />
                  <small class="form-text text-tertiary">Leave empty for a non‑recurring promotion.</small>
                </div>
              </div>
            </form>
          </div>

          <!-- EDIT MODE -->
          <div v-if="mode === 'edit'" class="edit-mode">
            <form @submit.prevent="updatePromotion">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Promotion Name <span class="text-danger">*</span></label>
                  <input type="text" class="form-control input-theme" v-model="formData.promotion_name" required />
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Discount Type <span class="text-danger">*</span></label>
                  <select class="form-select input-theme" v-model="formData.discount_type" :disabled="selectedPromotion?.status === 'active'" required>
                    <option value="">Select discount type</option>
                    <option value="percentage">Percentage</option>
                    <option value="fixed_amount">Fixed Amount</option>
                  </select>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Discount Value <span class="text-danger">*</span></label>
                  <div class="input-group">
                    <input type="number" class="form-control input-theme" v-model="formData.discount_value"
                           :disabled="selectedPromotion?.status === 'active'"
                           :min="formData.discount_type === 'percentage' ? 1 : 0"
                           :max="formData.discount_type === 'percentage' ? 100 : undefined"
                           step="0.01" required />
                    <span class="input-group-text">{{ formData.discount_type === 'percentage' ? '%' : '₱' }}</span>
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Status</label>
                  <select class="form-select input-theme" v-model="formData.status">
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                    <option value="expired">Expired</option>
                  </select>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Start Date <span class="text-danger">*</span></label>
                  <VueDatePicker v-model="formData.start_date" :enable-time-picker="false" format="MM/dd/yyyy"
                                 :min-date="new Date()" auto-apply required />
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">End Date <span class="text-danger">*</span></label>
                  <VueDatePicker v-model="formData.end_date" :enable-time-picker="false" format="MM/dd/yyyy"
                                 :min-date="formData.start_date || new Date()" auto-apply required />
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Usage Limit</label>
                  <input type="number" class="form-control input-theme" v-model="formData.usage_limit"
                         :disabled="selectedPromotion?.status === 'active'" min="1" step="1" />
                  <small class="form-text text-tertiary">Maximum total uses (optional)</small>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Minimum Purchase (₱)</label>
                  <input type="number" class="form-control input-theme" v-model="formData.min_purchase_amount"
                         :disabled="selectedPromotion?.status === 'active'" min="0" step="0.01" />
                  <small class="form-text text-tertiary">0 = no minimum</small>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Per Customer Limit</label>
                  <input type="number" class="form-control input-theme" v-model="formData.per_customer_limit"
                         :disabled="selectedPromotion?.status === 'active'" min="1" step="1" />
                  <small class="form-text text-tertiary">Max uses per customer (optional)</small>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Apply to Category <span class="text-danger">*</span></label>
                  <select class="form-select input-theme" v-model="formData.affected_category"
                          :disabled="loadingCategories || selectedPromotion?.status === 'active'" required>
                    <option value="" disabled>{{ loadingCategories ? 'Loading...' : 'Select category' }}</option>
                    <option v-for="cat in categories" :key="cat.value" :value="cat.value">{{ cat.label }}</option>
                  </select>
                </div>
                <div class="col-12 mb-3">
                  <label class="form-label text-secondary">Description</label>
                  <textarea class="form-control input-theme" v-model="formData.description" rows="3"></textarea>
                </div>
                <div class="col-12 mb-3">
                  <label class="form-label text-secondary">Recurrence Rule (optional)</label>
                  <input type="text" class="form-control input-theme" v-model="formData.recurrence_rule"
                         :disabled="selectedPromotion?.status === 'active'" />
                </div>
              </div>
            </form>
          </div>

          <!-- VIEW MODE -->
          <div v-if="mode === 'view'" class="view-mode">
            <div class="promotion-details" v-if="selectedPromotion">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Promotion Name</label>
                  <div class="form-control-plaintext text-primary">{{ selectedPromotion.promotion_name }}</div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Discount Type</label>
                  <div class="form-control-plaintext">
                    <span :class="getDiscountTypeBadgeClass(selectedPromotion.discount_type)" class="badge">
                      {{ formatDiscountType(selectedPromotion.discount_type) }}
                    </span>
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Discount Value</label>
                  <div class="form-control-plaintext text-primary">{{ formatDiscountValue(selectedPromotion.discount_value, selectedPromotion.discount_type) }}</div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Status</label>
                  <div class="form-control-plaintext">
                    <span :class="getStatusBadgeClass(selectedPromotion.status)" class="badge">
                      {{ formatStatus(selectedPromotion.status) }}
                    </span>
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Start Date</label>
                  <div class="form-control-plaintext text-primary">{{ formatDate(selectedPromotion.start_date) }}</div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">End Date</label>
                  <div class="form-control-plaintext text-primary">{{ formatDate(selectedPromotion.end_date) }}</div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Usage Limit</label>
                  <div class="form-control-plaintext text-primary">
                    {{ selectedPromotion.usage_limit || 'Unlimited' }}
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Current Usage</label>
                  <div class="form-control-plaintext text-primary">
                    {{ selectedPromotion.current_usage || 0 }}
                    <span v-if="selectedPromotion.usage_limit" class="text-tertiary"> / {{ selectedPromotion.usage_limit }}</span>
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Minimum Purchase</label>
                  <div class="form-control-plaintext text-primary">
                    {{ selectedPromotion.min_purchase_amount ? `₱${selectedPromotion.min_purchase_amount}` : '₱100 (default)' }}
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary fw-semibold">Per Customer Limit</label>
                  <div class="form-control-plaintext text-primary">
                    {{ selectedPromotion.per_customer_limit || 'Unlimited' }}
                  </div>
                </div>
                <div class="col-12 mb-3">
                  <label class="form-label text-secondary fw-semibold">Applied to Category</label>
                  <div class="form-control-plaintext">
                    <span class="badge bg-info text-white">{{ formatCategory(selectedPromotion.affected_category) }}</span>
                  </div>
                </div>
                <div class="col-12 mb-3" v-if="selectedPromotion.recurrence_rule">
                  <label class="form-label text-secondary fw-semibold">Recurrence Rule</label>
                  <div class="form-control-plaintext text-primary">{{ selectedPromotion.recurrence_rule }}</div>
                </div>
                <div class="col-12 mb-3" v-if="selectedPromotion.description">
                  <label class="form-label text-secondary fw-semibold">Description</label>
                  <div class="form-control-plaintext text-primary">{{ selectedPromotion.description }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer surface-secondary border-theme">
          <template v-if="mode === 'add'">
            <button type="button" class="btn btn-cancel" @click="handleClose" :disabled="isLoading">Cancel</button>
            <button type="button" class="btn btn-save" @click="savePromotion" :disabled="loadingCategories || isLoading">
              <span v-if="isLoading" class="spinner-border spinner-border-sm me-2"></span>
              {{ isLoading ? 'Creating...' : 'Save Promotion' }}
            </button>
          </template>
          <template v-if="mode === 'edit'">
            <button type="button" class="btn btn-cancel" @click="handleClose" :disabled="isLoading">Cancel</button>
            <button type="button" class="btn btn-save" @click="updatePromotion" :disabled="loadingCategories || isLoading">
              <span v-if="isLoading" class="spinner-border spinner-border-sm me-2"></span>
              {{ isLoading ? 'Updating...' : 'Update Promotion' }}
            </button>
          </template>
          <template v-if="mode === 'view'">
            <button type="button" class="btn btn-secondary" @click="switchToEdit"><Edit :size="14" class="me-1" /> Edit</button>
            <button type="button" class="btn btn-outline-secondary" @click="handleClose">Close</button>
          </template>
        </div>
      </div>
    </div>
  </div>
  <div v-if="isVisible" class="modal-backdrop fade show"></div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Edit } from 'lucide-vue-next'
import { useToast } from '@/composables/ui/useToast'
import { useModal } from '@/composables/ui/useModal'
import categoryApiService from '@/services/apiCategory.js'
import promotionApiService from '@/services/apiPromotions.js'
import VueDatePicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

const { success: showSuccess, error: showError } = useToast()
const { isVisible, isLoading, error, show, hide, setLoading, setError, clearError } = useModal()
const emit = defineEmits(['promotion-saved'])

const mode = ref('add')
const selectedPromotion = ref(null)
const categories = ref([])
const loadingCategories = ref(false)

const formData = ref({
  promotion_name: '',
  discount_type: '',
  discount_value: '',
  status: 'draft',
  start_date: '',
  end_date: '',
  affected_category: '',
  usage_limit: null,
  min_purchase_amount: 100,    // default ₱100
  per_customer_limit: null,
  description: '',
  recurrence_rule: ''
})

const modalTitle = computed(() => {
  const titles = { add: 'Add Promotion', edit: 'Edit Promotion', view: 'View Promotion' }
  return titles[mode.value] || 'Promotion'
})

const openAdd = () => { mode.value = 'add'; selectedPromotion.value = null; resetForm(); loadCategories(); show(); }
const openEdit = (promotion) => { mode.value = 'edit'; selectedPromotion.value = { ...promotion }; populateForm(promotion); loadCategories(); show(); }
const openView = (promotion) => { mode.value = 'view'; selectedPromotion.value = { ...promotion }; show(); }
const switchToEdit = () => { mode.value = 'edit'; populateForm(selectedPromotion.value); loadCategories(); }

// UPDATED: directly control the modal visibility
const handleClose = () => {
  if (!isLoading.value) {
    isVisible.value = false   // force close
    resetForm()
  }
}

const resetForm = () => {
  formData.value = {
    promotion_name: '', discount_type: '', discount_value: '', status: 'draft',
    start_date: '', end_date: '', affected_category: '', usage_limit: null,
    min_purchase_amount: 100, per_customer_limit: null, description: '', recurrence_rule: ''
  }
}

const populateForm = (promotion) => {
  formData.value = {
    promotion_name: promotion.promotion_name || '',
    discount_type: promotion.discount_type || '',
    discount_value: promotion.discount_value || '',
    status: promotion.status || 'draft',
    start_date: promotion.start_date || '',
    end_date: promotion.end_date || '',
    affected_category: promotion.affected_category || '',
    usage_limit: promotion.usage_limit || null,
    min_purchase_amount: promotion.min_purchase_amount ?? 100,
    per_customer_limit: promotion.per_customer_limit || null,
    description: promotion.description || '',
    recurrence_rule: promotion.recurrence_rule || ''
  }
}

const validateForm = () => {
  clearError()
  if (!formData.value.promotion_name.trim()) { setError('Please enter a promotion name'); return false }
  if (!formData.value.discount_type) { setError('Please select a discount type'); return false }
  if (!formData.value.discount_value || parseFloat(formData.value.discount_value) <= 0) { setError('Please enter a valid discount value'); return false }
  if (formData.value.discount_type === 'percentage' && parseFloat(formData.value.discount_value) > 100) { setError('Percentage cannot exceed 100%'); return false }
  if (!formData.value.affected_category) { setError('Please select a category'); return false }
  if (!formData.value.start_date) { setError('Please select a start date'); return false }
  if (!formData.value.end_date) { setError('Please select an end date'); return false }
  if (formData.value.end_date < formData.value.start_date) { setError('End date cannot be before start date'); return false }
  return true
}

const loadCategories = async () => {
  try {
    loadingCategories.value = true
    const response = await categoryApiService.getAllCategories()
    let cats = []
    if (Array.isArray(response)) cats = response
    else if (response?.categories) cats = response.categories
    if (cats.length > 0) {
      categories.value = [
        { value: 'all', label: 'All Products' },
        ...cats.filter(c => c._id && c.category_name).map(c => ({ value: c._id, label: c.category_name }))
      ]
    } else {
      categories.value = [{ value: 'all', label: 'All Products' }]
    }
  } catch (err) {
    console.error('Error loading categories:', err)
    categories.value = [{ value: 'all', label: 'All Products' }]
  } finally {
    loadingCategories.value = false
  }
}

// UPDATED: force close after success
const savePromotion = async () => {
  if (!validateForm()) return
  try {
    setLoading(true)
    const result = await promotionApiService.createPromotion(formData.value)
    if (result?.success) {
      showSuccess('✅ Promotion created successfully!')
      emit('promotion-saved', { action: 'add', data: result.promotion })
      isVisible.value = false   // force close
      resetForm()
    } else {
      let msg = result?.message || 'Failed to create promotion'
      if (result?.errors?.length) msg += '\n' + result.errors.join('\n')
      setError(msg)
    }
  } catch (err) {
    setError(err.message || 'Error creating promotion')
  } finally {
    setLoading(false)
  }
}

const updatePromotion = async () => {
  if (!validateForm()) return
  let shouldClose = false
  try {
    setLoading(true)
    const changedFields = {}
    Object.keys(formData.value).forEach(key => {
      const newVal = formData.value[key]
      const oldVal = selectedPromotion.value?.[key]
      if (JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
        changedFields[key] = newVal
      }
    })
    if (Object.keys(changedFields).length === 0) {
      showSuccess('No changes detected')
      isVisible.value = false
      resetForm()
      return
    }
    const result = await promotionApiService.updatePromotion(
      selectedPromotion.value.promotion_id, changedFields
    )
    if (result?.success) {
      showSuccess('✅ Promotion updated successfully!')
      emit('promotion-saved', { action: 'edit', id: selectedPromotion.value.promotion_id, data: result.promotion })
      isVisible.value = false   // force close after update
      resetForm()
    } else {
      let msg = result?.message || 'Failed to update promotion'
      if (result?.errors?.length) msg += '\n' + result.errors.join('\n')
      setError(msg)
    }
  } catch (err) {
    setError(err.message || 'Error updating promotion')
  } finally {
    setLoading(false)
  }
}

const formatDiscountType = (type) => {
  const types = { percentage: 'Percentage', fixed_amount: 'Fixed Amount' }
  return types[type] || type
}

const formatDiscountValue = (value, type) => {
  if (!value) return '—'
  if (typeof value === 'string' && value.includes('%')) return value
  if (type === 'fixed_amount') return `₱${value}`
  return value
}

const formatStatus = (status) => {
  const statuses = { active: 'Active', inactive: 'Inactive', expired: 'Expired', draft: 'Draft', scheduled: 'Draft' }
  return statuses[status] || status
}

const formatDate = (dateString) => {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const formatCategory = (categoryId) => {
  if (categoryId === 'all') return 'All Products'
  const cat = categories.value.find(c => c.value === categoryId)
  return cat?.label || categoryId
}

const getDiscountTypeBadgeClass = (type) => {
  const classes = { percentage: 'bg-primary text-white', fixed_amount: 'bg-success text-white' }
  return classes[type] || 'bg-secondary text-white'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    active: 'bg-success text-white',
    inactive: 'bg-secondary text-white',
    expired: 'bg-danger text-white',
    draft: 'bg-warning text-dark'
  }
  return classes[status] || 'bg-secondary text-white'
}

defineExpose({ openAdd, openEdit, openView })
onMounted(() => loadCategories())
</script>

<style scoped>
.modal { background-color: rgba(0,0,0,0.5); backdrop-filter: blur(4px); }
.modal-content { border-radius: 0.75rem; border-width: 1px; max-height: 90vh; display: flex; flex-direction: column; }
.modal-header { padding: 1.5rem; flex-shrink: 0; }
.modal-title { font-size: 1.25rem; font-weight: 600; }
.modal-body { padding: 1.5rem; overflow-y: auto; flex: 1 1 auto; max-height: calc(90vh - 140px); }
.modal-footer { padding: 1.5rem; gap: 0.5rem; flex-shrink: 0; position: sticky; bottom: 0; z-index: 10; }
.alert { margin-bottom: 1rem; font-size: 0.875rem; }
.form-label { font-weight: 500; margin-bottom: 0.5rem; }
.form-control, .form-select { border-radius: 0.5rem; padding: 0.625rem 0.875rem; font-size: 0.875rem; }
.input-group-text { font-weight: 500; }
.text-warning { color: var(--warning) !important; font-size: 0.75rem; margin-top: 0.25rem; }
.spinner-border-sm { width: 1rem; height: 1rem; border-width: 0.15em; }
.form-control-plaintext { padding: 0.625rem 0; }
</style>