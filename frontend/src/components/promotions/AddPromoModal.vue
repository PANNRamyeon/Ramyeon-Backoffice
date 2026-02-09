<template>
  <!-- ✅ Updated: Use v-if for better performance and proper cleanup -->
  <div 
    v-if="isVisible" 
    class="modal fade show" 
    id="addPromoModal" 
    tabindex="-1" 
    aria-labelledby="addPromoModalLabel" 
    style="display: block;"
    @click.self="handleClose"
  >
    <div class="modal-dialog modal-lg modal-dialog-scrollable">
      <div class="modal-content surface-card border-theme">
        <!-- Modal Header -->
        <div class="modal-header border-theme">
          <h5 class="modal-title text-primary" id="addPromoModalLabel">{{ modalTitle }}</h5>
          <button type="button" class="btn-close" @click="handleClose" aria-label="Close"></button>
        </div>
        
        <!-- Modal Body - Scrollable -->
        <div class="modal-body">
          <!-- Warning Banner for Active Promotions -->
          <div v-if="mode === 'edit' && selectedPromotion?.status === 'active'" class="alert alert-warning">
            <div class="d-flex align-items-start">
              <span class="me-2">⚠️</span>
              <div>
                <strong>Active Promotion:</strong> 
                Discount settings cannot be modified while the promotion is active. 
                Only name, description, dates, and usage limit can be changed.
              </div>
            </div>
          </div>

          <!-- Error Display -->
          <div v-if="error" class="alert alert-danger alert-dismissible fade show">
            {{ error }}
            <button type="button" class="btn-close" @click="clearError"></button>
          </div>

          <!-- Add Mode -->
          <div v-if="mode === 'add'" class="add-mode">
            <form @submit.prevent="savePromotion">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Promotion Name <span class="text-danger">*</span></label>
                  <input 
                    type="text" 
                    class="form-control input-theme" 
                    v-model="formData.promotion_name"
                    placeholder="Enter promotion name"
                    required
                  >
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
                    <input 
                      type="number" 
                      class="form-control input-theme" 
                      v-model="formData.discount_value"
                      :placeholder="formData.discount_type === 'percentage' ? 'Enter percentage (e.g., 20)' : 'Enter amount (e.g., 50)'"
                      :min="formData.discount_type === 'percentage' ? 1 : 0"
                      :max="formData.discount_type === 'percentage' ? 100 : undefined"
                      step="0.01"
                      required
                    >
                    <span class="input-group-text surface-tertiary border-theme text-secondary">
                      {{ formData.discount_type === 'percentage' ? '%' : '₱' }}
                    </span>
                  </div>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Status</label>
                  <select class="form-select input-theme" v-model="formData.status">
                    <option value="scheduled">Scheduled</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Start Date <span class="text-danger">*</span></label>
                  <div class="date-picker-wrapper">
                    <VueDatePicker 
                      v-model="formData.start_date"
                      :enable-time-picker="false"
                      format="MM/dd/yyyy"
                      placeholder="Select start date"
                      :min-date="new Date()"
                      auto-apply
                      required
                    />
                  </div>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">End Date <span class="text-danger">*</span></label>
                  <div class="date-picker-wrapper">
                    <VueDatePicker 
                      v-model="formData.end_date"
                      :enable-time-picker="false"
                      format="MM/dd/yyyy"
                      placeholder="Select end date"
                      :min-date="formData.start_date || new Date()"
                      auto-apply
                      required
                    />
                  </div>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Usage Limit</label>
                  <input 
                    type="number" 
                    class="form-control input-theme" 
                    v-model="formData.usage_limit"
                    placeholder="Leave empty for unlimited"
                    min="1"
                    step="1"
                  >
                  <small class="form-text text-tertiary">Maximum number of times this promotion can be used (optional)</small>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Apply to Category <span class="text-danger">*</span></label>
                  <select 
                    class="form-select input-theme" 
                    v-model="formData.affected_category" 
                    :disabled="loadingCategories"
                    required
                  >
                    <option value="" disabled>
                      {{ loadingCategories ? 'Loading categories...' : 'Select category' }}
                    </option>
                    <option 
                      v-for="category in categories" 
                      :key="category.value"
                      :value="category.value"
                    >
                      {{ category.label }}
                    </option>
                  </select>
                </div>
                
                <div class="col-12 mb-3">
                  <label class="form-label text-secondary">Description</label>
                  <textarea 
                    class="form-control input-theme" 
                    v-model="formData.description"
                    placeholder="Enter promotion description (optional)"
                    rows="3"
                  ></textarea>
                  <small class="form-text text-tertiary">Add details about this promotion (optional)</small>
                </div>
              </div>
            </form>
          </div>

          <!-- Edit Mode -->
          <div v-if="mode === 'edit'" class="edit-mode">
            <form @submit.prevent="updatePromotion">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Promotion Name <span class="text-danger">*</span></label>
                  <input 
                    type="text" 
                    class="form-control input-theme" 
                    v-model="formData.promotion_name"
                    placeholder="Enter promotion name"
                    required
                  >
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Discount Type <span class="text-danger">*</span></label>
                  <select 
                    class="form-select input-theme" 
                    v-model="formData.discount_type" 
                    :disabled="selectedPromotion?.status === 'active'"
                    required
                  >
                    <option value="">Select discount type</option>
                    <option value="percentage">Percentage</option>
                    <option value="fixed_amount">Fixed Amount</option>
                    <option value="buy_x_get_y">Buy One Get One (BOGO)</option>
                  </select>
                  <small v-if="selectedPromotion?.status === 'active'" class="form-text text-warning">
                    Cannot modify while promotion is active
                  </small>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Discount Value <span class="text-danger">*</span></label>
                  <div class="input-group">
                    <input 
                      type="number" 
                      class="form-control input-theme" 
                      v-model="formData.discount_value"
                      :disabled="selectedPromotion?.status === 'active'"
                      :min="formData.discount_type === 'percentage' ? 1 : 0"
                      :max="formData.discount_type === 'percentage' ? 100 : undefined"
                      step="0.01"
                      required
                    >
                    <span class="input-group-text surface-tertiary border-theme text-secondary">
                      {{ formData.discount_type === 'percentage' ? '%' : '₱' }}
                    </span>
                  </div>
                  <small v-if="selectedPromotion?.status === 'active'" class="form-text text-warning">
                    Cannot modify while promotion is active
                  </small>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Status</label>
                  <select class="form-select input-theme" v-model="formData.status">
                    <option value="scheduled">Scheduled</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                    <option value="expired">Expired</option>
                  </select>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Start Date <span class="text-danger">*</span></label>
                  <div class="date-picker-wrapper">
                    <VueDatePicker 
                      v-model="formData.start_date"
                      :enable-time-picker="false"
                      format="MM/dd/yyyy"
                      placeholder="Select start date"
                      :min-date="new Date()"
                      auto-apply
                      required
                    />
                  </div>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">End Date <span class="text-danger">*</span></label>
                  <div class="date-picker-wrapper">
                    <VueDatePicker 
                      v-model="formData.end_date"
                      :enable-time-picker="false"
                      format="MM/dd/yyyy"
                      placeholder="Select end date"
                      :min-date="formData.start_date || new Date()"
                      auto-apply
                      required
                    />
                  </div>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Usage Limit</label>
                  <input 
                    type="number" 
                    class="form-control input-theme" 
                    v-model="formData.usage_limit"
                    placeholder="Leave empty for unlimited"
                    min="1"
                    step="1"
                  >
                  <small class="form-text text-tertiary">Maximum number of times this promotion can be used (optional)</small>
                </div>
                
                <div class="col-md-6 mb-3">
                  <label class="form-label text-secondary">Apply to Category <span class="text-danger">*</span></label>
                  <select 
                    class="form-select input-theme" 
                    v-model="formData.affected_category" 
                    :disabled="loadingCategories || selectedPromotion?.status === 'active'"
                    required
                  >
                    <option value="" disabled>
                      {{ loadingCategories ? 'Loading categories...' : 'Select category' }}
                    </option>
                    <option 
                      v-for="category in categories" 
                      :key="category.value"
                      :value="category.value"
                    >
                      {{ category.label }}
                    </option>
                  </select>
                  <small v-if="selectedPromotion?.status === 'active'" class="form-text text-warning">
                    Cannot modify while promotion is active
                  </small>
                </div>
                
                <div class="col-12 mb-3">
                  <label class="form-label text-secondary">Description</label>
                  <textarea 
                    class="form-control input-theme" 
                    v-model="formData.description"
                    placeholder="Enter promotion description (optional)"
                    rows="3"
                  ></textarea>
                  <small class="form-text text-tertiary">Add details about this promotion (optional)</small>
                </div>
              </div>
            </form>
          </div>

          <!-- View Mode -->
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
                    <span v-if="selectedPromotion.usage_limit" class="text-tertiary">
                      / {{ selectedPromotion.usage_limit }}
                    </span>
                  </div>
                </div>
                <div class="col-12 mb-3">
                  <label class="form-label text-secondary fw-semibold">Applied to Category</label>
                  <div class="form-control-plaintext">
                    <span class="badge bg-info text-white">
                      {{ formatCategory(selectedPromotion.affected_category) }}
                    </span>
                  </div>
                </div>
                <div class="col-12 mb-3" v-if="selectedPromotion.description">
                  <label class="form-label text-secondary fw-semibold">Description</label>
                  <div class="form-control-plaintext text-primary">{{ selectedPromotion.description }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Modal Footer - Sticky -->
        <div class="modal-footer surface-secondary border-theme">
          <template v-if="mode === 'add'">
            <button type="button" class="btn btn-cancel" @click="handleClose" :disabled="isLoading">
              Cancel
            </button>
            <button 
              type="button" 
              class="btn btn-save" 
              @click="savePromotion"
              :disabled="loadingCategories || isLoading"
            >
              <span v-if="isLoading" class="spinner-border spinner-border-sm me-2"></span>
              {{ isLoading ? 'Creating...' : 'Save Promotion' }}
            </button>
          </template>

          <template v-if="mode === 'edit'">
            <button type="button" class="btn btn-cancel" @click="handleClose" :disabled="isLoading">
              Cancel
            </button>
            <button 
              type="button" 
              class="btn btn-save" 
              @click="updatePromotion"
              :disabled="loadingCategories || isLoading"
            >
              <span v-if="isLoading" class="spinner-border spinner-border-sm me-2"></span>
              {{ isLoading ? 'Updating...' : 'Update Promotion' }}
            </button>
          </template>

          <template v-if="mode === 'view'">
            <button type="button" class="btn btn-secondary" @click="switchToEdit">
              <Edit :size="14" class="me-1" />
              Edit
            </button>
            <button type="button" class="btn btn-outline-secondary" @click="handleClose">Close</button>
          </template>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Modal Backdrop -->
  <div v-if="isVisible" class="modal-backdrop fade show"></div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Edit } from 'lucide-vue-next' // ✅ ADDED THIS IMPORT
import { useToast } from '@/composables/ui/useToast'
import { useModal } from '@/composables/ui/useModal'
import categoryApiService from '@/services/apiCategory.js'
import promotionApiService from '@/services/apiPromotions.js'
import VueDatePicker from '@vuepic/vue-datepicker' // ✅ Added DatePicker import
import '@vuepic/vue-datepicker/dist/main.css' // ✅ Added DatePicker styles

// Composables
const { success: showSuccess, error: showError } = useToast()
const { isVisible, isLoading, error, show, hide, setLoading, setError, clearError } = useModal()

// Props & Emits
const emit = defineEmits(['promotion-saved'])

// State
const mode = ref('add')
const selectedPromotion = ref(null)
const categories = ref([])
const loadingCategories = ref(false)

const formData = ref({
  promotion_name: '',
  discount_type: '',
  discount_value: '',
  status: 'scheduled',
  start_date: '',
  end_date: '',
  affected_category: '',
  usage_limit: null,
  description: ''
})

// Computed
const modalTitle = computed(() => {
  const titles = {
    'add': 'Add Promotion',
    'edit': 'Edit Promotion',
    'view': 'View Promotion'
  }
  return titles[mode.value] || 'Promotion'
})

// Methods
const openAdd = () => {
  mode.value = 'add'
  selectedPromotion.value = null
  resetForm()
  loadCategories()
  show()
}

const openEdit = (promotion) => {
  mode.value = 'edit'
  selectedPromotion.value = { ...promotion }
  populateForm(promotion)
  loadCategories()
  show()
}

const openView = (promotion) => {
  mode.value = 'view'
  selectedPromotion.value = { ...promotion }
  show()
}

const switchToEdit = () => {
  mode.value = 'edit'
  populateForm(selectedPromotion.value)
  loadCategories()
}

const handleClose = () => {
  if (!isLoading.value) {
    hide()
    resetForm()
  }
}

const resetForm = () => {
  formData.value = {
    promotion_name: '',
    discount_type: '',
    discount_value: '',
    status: 'scheduled',
    start_date: '',
    end_date: '',
    affected_category: '',
    usage_limit: null,
    description: ''
  }
}

const populateForm = (promotion) => {
  formData.value = {
    promotion_name: promotion.promotion_name || '',
    discount_type: promotion.discount_type || '',
    discount_value: promotion.discount_value || '',
    status: promotion.status || 'scheduled',
    start_date: promotion.start_date || '',
    end_date: promotion.end_date || '',
    affected_category: promotion.affected_category || '',
    usage_limit: promotion.usage_limit || null,
    description: promotion.description || ''
  }
}

const validateForm = () => {
  clearError()
  
  if (!formData.value.promotion_name.trim()) {
    setError('Please enter a promotion name')
    return false
  }
  if (!formData.value.discount_type) {
    setError('Please select a discount type')
    return false
  }
  if (!formData.value.discount_value || formData.value.discount_value <= 0) {
    setError('Please enter a valid discount value')
    return false
  }
  if (formData.value.discount_type === 'percentage' && formData.value.discount_value > 100) {
    setError('Percentage discount cannot exceed 100%')
    return false
  }
  if (!formData.value.affected_category) {
    setError('Please select which category this promotion affects')
    return false
  }
  if (!formData.value.start_date) {
    setError('Please select a start date')
    return false
  }
  if (!formData.value.end_date) {
    setError('Please select an end date')
    return false
  }
  if (new Date(formData.value.end_date) <= new Date(formData.value.start_date)) {
    setError('End date must be after start date')
    return false
  }
  
  return true
}

const loadCategories = async () => {
  try {
    loadingCategories.value = true
    const response = await categoryApiService.getAllCategories()
    
    let categoriesArray = []
    
    if (Array.isArray(response)) {
      categoriesArray = response
    } else if (response?.categories) {
      categoriesArray = response.categories
    }
    
    if (categoriesArray.length > 0) {
      const validCategories = categoriesArray
        .filter(cat => cat._id && cat.category_name)
        .map(cat => ({
          value: cat._id,
          label: cat.category_name
        }))
      
      categories.value = [
        { value: 'all', label: 'All Products' },
        ...validCategories
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

const savePromotion = async () => {
  if (!validateForm()) return
  
  try {
    setLoading(true)
    const result = await promotionApiService.createPromotion(formData.value)
    
    if (result?.success) {
      showSuccess('✅ Promotion created successfully!')
      emit('promotion-saved', { action: 'add', data: result.promotion })
    } else {
      let errorMsg = result?.message || 'Failed to create promotion'
      if (result?.errors?.length > 0) {
        errorMsg += '\n' + result.errors.join('\n')
      }
      setError(errorMsg)
    }
  } catch (err) {
    setError(err.message || 'Error creating promotion')
  } finally {
    setLoading(false)
    // ✅ Move handleClose here so it runs when isLoading = false
    if (!error.value) handleClose()
  }
}


const updatePromotion = async () => {
  if (!validateForm()) return
  
  let shouldClose = false
  try {
    setLoading(true)
    
    // Helper: normalize values so comparisons don't fail because of type differences
    const normalizeForComparison = (key, value) => {
      if (value === undefined || value === null) return value
      
      // Numeric fields may be bound as strings by inputs
      if (['discount_value', 'usage_limit'].includes(key)) {
        const numericValue = Number(value)
        return Number.isNaN(numericValue) ? value : numericValue
      }
      
      // Date fields can be Date objects or strings – compare as ISO strings
      if (['start_date', 'end_date'].includes(key)) {
        const dateValue = value instanceof Date ? value : new Date(value)
        return Number.isNaN(dateValue?.getTime()) ? value : dateValue.toISOString()
      }
      
      // Arrays (e.g., target_ids) – compare by JSON string
      if (Array.isArray(value)) {
        return JSON.stringify(value)
      }
      
      return value
    }
    
    // Only send changed fields
    const changedFields = {}
    Object.keys(formData.value).forEach(key => {
      const newValue = normalizeForComparison(key, formData.value[key])
      const oldValue = normalizeForComparison(key, selectedPromotion.value[key])
      
      if (newValue !== oldValue) {
        changedFields[key] = formData.value[key]
      }
    })
    
    if (Object.keys(changedFields).length === 0) {
      showSuccess('No changes detected')
      handleClose()
      return
    }
    
    const result = await promotionApiService.updatePromotion(
      selectedPromotion.value.promotion_id, 
      changedFields
    )
    
    if (result?.success) {
      showSuccess('✅ Promotion updated successfully!')
      emit('promotion-saved', {
        action: 'edit',
        id: selectedPromotion.value.promotion_id,
        data: result.promotion
      })
      shouldClose = true
    } else {
      let errorMsg = result?.message || 'Failed to update promotion'
      if (result?.errors?.length > 0) {
        errorMsg += '\n' + result.errors.join('\n')
        if (result.errors.some(e => e.includes('while promotion is active'))) {
          errorMsg += '\n\n💡 Tip: Deactivate the promotion first.'
        }
      }
      setError(errorMsg)
    }
  } catch (err) {
    setError(err.message || 'Error updating promotion')
  } finally {
    setLoading(false)
    if (shouldClose && !error.value) {
      handleClose()
    }
  }
}

// Formatting methods
const formatDiscountType = (type) => {
  const types = { 'percentage': 'Percentage', 'fixed_amount': 'Fixed Amount', 'buy_x_get_y': 'BOGO' }
  return types[type] || type
}

const formatDiscountValue = (value, type) => {
  if (type === 'percentage') return `${value}%`
  if (type === 'fixed_amount') return `₱${value}`
  return value
}

const formatStatus = (status) => {
  const statuses = { 'active': 'Active', 'inactive': 'Inactive', 'expired': 'Expired', 'scheduled': 'Scheduled' }
  return statuses[status] || status
}

const formatDate = (dateString) => {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const formatCategory = (categoryId) => {
  if (categoryId === 'all') return 'All Products'
  const category = categories.value.find(cat => cat.value === categoryId)
  return category?.label || categoryId
}

const getDiscountTypeBadgeClass = (type) => {
  const classes = {
    'percentage': 'bg-primary text-white',
    'fixed_amount': 'bg-success text-white',
    'buy_x_get_y': 'bg-info text-white'
  }
  return classes[type] || 'bg-secondary text-white'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    'active': 'bg-success text-white',
    'inactive': 'bg-secondary text-white',
    'expired': 'bg-danger text-white',
    'scheduled': 'bg-warning text-dark'
  }
  return classes[status] || 'bg-secondary text-white'
}

// Expose methods
defineExpose({ openAdd, openEdit, openView })

// Lifecycle
onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.modal {
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal-content {
  border-radius: 0.75rem;
  border-width: 1px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 1.5rem;
  flex-shrink: 0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1 1 auto;
  max-height: calc(90vh - 140px);
}

.modal-footer {
  padding: 1.5rem;
  gap: 0.5rem;
  flex-shrink: 0;
  position: sticky;
  bottom: 0;
  z-index: 10;
}

.alert {
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.form-label {
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.form-control,
.form-select {
  border-radius: 0.5rem;
  padding: 0.625rem 0.875rem;
  font-size: 0.875rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-control:focus,
.form-select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 0.2rem var(--state-focus);
}

.form-control:disabled,
.form-select:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.input-group-text {
  font-weight: 500;
}

.text-warning {
  color: var(--warning) !important;
  font-size: 0.75rem;
  margin-top: 0.25rem;
  display: block;
}

.spinner-border-sm {
  width: 1rem;
  height: 1rem;
  border-width: 0.15em;
}

.form-control-plaintext {
  padding: 0.625rem 0;
}

@media (max-width: 768px) {
  .modal-dialog {
    margin: 0.5rem;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }
  
  .modal-body {
    max-height: calc(100vh - 120px);
  }
}
</style>