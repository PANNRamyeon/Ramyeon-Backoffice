<template>
  <!-- Use Teleport to render modal at body level -->
  <Teleport to="body">
    <div v-if="isVisible" class="modal-overlay modal-overlay-theme" @click="handleOverlayClick">
      <div class="modal-content modal-theme large-modal" @click.stop>
        <div class="modal-header border-bottom-theme">
          <h2 class="text-primary">{{ isEditMode ? 'Edit Product' : 'Add New Product' }}</h2>
          <button class="btn-close" @click="closeModal" :disabled="isLoading" aria-label="Close">
            <X :size="20" />
          </button>
        </div>
        
        <form @submit.prevent="handleSubmit" class="product-form">
          <!-- Product Image Upload Section -->
          <div class="mb-3">
            <label class="form-label text-primary fw-medium">Product Image:</label>
            
            <!-- Image Preview (if exists) -->
            <div v-if="imagePreview" class="mb-3">
              <div class="image-preview-container surface-tertiary rounded p-3 text-center">
                <img 
                  :src="imagePreview" 
                  alt="Product preview" 
                  class="img-fluid rounded mb-2" 
                  style="max-height: 120px;" 
                />
                <br>
                <small class="text-success">Image selected</small>
                <br>
                <button 
                  type="button" 
                  class="btn btn-cancel btn-xs mt-2"
                  @click="removeImage"
                >
                  Remove Image
                </button>
              </div>
            </div>
            
            <!-- File Input (always visible) -->
            <div class="product-image-upload">
              <div class="image-upload-container surface-tertiary rounded p-4 text-center">
                <div class="upload-icon text-accent">
                  <Camera :size="32" />
                </div>
                <p class="text-primary mb-2">
                  {{ imagePreview ? 'Change image' : 'Upload product image' }}
                </p>
                <input 
                  type="file" 
                  class="form-control input-theme" 
                  accept="image/*"
                  @change="handleImageUpload"
                  :key="imageInputKey"
                />
                <small class="text-tertiary-medium mt-2 d-block">
                  Maximum file size: 5MB. Supported formats: JPEG, PNG, GIF, WebP
                </small>
              </div>
            </div>
          </div>

          <div class="row g-3 mb-3">
            <div class="col-md-6">
              <label for="product_name" class="form-label text-primary fw-medium">
                Product Name <span class="text-error">*</span>
              </label>
              <input 
                id="product_name"
                v-model="productForm.product_name" 
                type="text" 
                required 
                :disabled="isLoading"
                placeholder="Enter product name"
                class="form-control input-theme"
                :class="{ 
                  'is-invalid': validationErrors.product_name, 
                  'validation-error': validationErrors.product_name 
                }"
              />
              <div v-if="validationErrors.product_name" class="invalid-feedback">
                {{ validationErrors.product_name }}
              </div>
            </div>

            <div class="col-md-6">
              <label for="SKU" class="form-label text-primary fw-medium">
                SKU <span class="text-error">*</span>
              </label>
              <div class="position-relative">
                <input 
                  id="SKU"
                  v-model="productForm.SKU" 
                  type="text" 
                  required 
                  :disabled="isLoading || isValidatingSku"
                  placeholder="Enter any unique identifier (e.g., ABC123, NOODLE-001, etc.)"
                  class="form-control input-theme"
                  :class="{ 
                    'is-invalid': validationErrors.SKU || skuError,
                    'validation-error': validationErrors.SKU || skuError
                  }"
                  @blur="validateSKU"
                />
                <div v-if="isValidatingSku" class="validation-spinner position-absolute top-50 end-0 translate-middle-y me-3">
                  <div class="spinner-border spinner-border-sm text-accent" role="status">
                    <span class="visually-hidden">Validating...</span>
                  </div>
                </div>
                <div v-if="validationErrors.SKU || skuError" class="invalid-feedback">
                  {{ validationErrors.SKU || skuError }}
                </div>
              </div>
              <small class="text-tertiary-medium">
                Can be any format you prefer - just needs to be unique for each product
              </small>
            </div>
          </div>

          <div class="row g-3 mb-3">
            <div class="col-md-6">
              <label for="category_id" class="form-label text-primary fw-medium">
                Category
                <small class="text-tertiary-medium">(Optional - defaults to Uncategorized)</small>
              </label>
              <select 
                id="category_id"
                v-model="productForm.category_id" 
                class="form-select input-theme"
                :disabled="isLoading"
                @change="onCategoryChange"
              >
                <option value="">Uncategorized</option>
                <option 
                  v-for="category in categories" 
                  :key="category._id" 
                  :value="category._id"
                >
                  {{ category.category_name }}
                </option>
              </select>
            </div>

            <div class="col-md-6">
              <label for="subcategory_name" class="form-label text-primary fw-medium">
                Subcategory
                <small class="text-tertiary-medium">(Optional)</small>
              </label>
              <select 
                id="subcategory_name"
                v-model="productForm.subcategory_name" 
                class="form-select input-theme"
                :disabled="isLoading || !productForm.category_id"
              >
                <option value="">{{ productForm.category_id ? 'Select Subcategory' : 'General' }}</option>
                <option 
                  v-for="subcategory in availableSubcategories" 
                  :key="subcategory.name" 
                  :value="subcategory.name"
                >
                  {{ subcategory.name }}
                </option>
              </select>
              <small v-if="!productForm.category_id" class="text-tertiary-medium">
                Will be placed in "General" subcategory of Uncategorized
              </small>
            </div>
          </div>

          <!-- BATCH STOCK MANAGEMENT SECTION -->
          <div class="mb-4">
            <div class="surface-elevated p-3 rounded border-theme-subtle">
              <h5 class="text-primary mb-3">
                <Package :size="20" />
                Stock & Batch Information
              </h5>
              
              <!-- Stock Mode Toggle -->
              <div class="mb-3">
                <div class="form-check form-switch">
                  <input 
                    id="createWithStock"
                    v-model="createWithStock" 
                    type="checkbox" 
                    class="form-check-input"
                    @change="onStockModeChange"
                  />
                  <label for="createWithStock" class="form-check-label text-secondary">
                    Add initial stock (creates first batch)
                  </label>
                </div>
                <small class="text-tertiary-medium">
                  {{ createWithStock 
                    ? 'This will create the first batch for this product with the stock details below' 
                    : 'Product will be created without stock. Add batches later when receiving inventory' 
                  }}
                </small>
              </div>

              <!-- Initial Stock Fields (only shown when createWithStock is true) -->
              <div v-if="createWithStock" class="batch-fields">
                <div class="row g-3 mb-3">
                  <div class="col-md-6">
                    <label for="initial_stock" class="form-label text-primary fw-medium">
                      Initial Stock Quantity <span class="text-error">*</span>
                    </label>
                    <input 
                      id="initial_stock"
                      v-model.number="batchForm.quantity_received" 
                      type="number" 
                      min="1"
                      :required="createWithStock"
                      :disabled="isLoading"
                      placeholder="0"
                      class="form-control input-theme"
                      :class="{ 
                        'is-invalid': validationErrors.initial_stock,
                        'validation-error': validationErrors.initial_stock 
                      }"
                    />
                    <div v-if="validationErrors.initial_stock" class="invalid-feedback">
                      {{ validationErrors.initial_stock }}
                    </div>
                  </div>

                  <div class="col-md-6">
                    <label for="batch_cost_price" class="form-label text-primary fw-medium">
                      Cost Price per Unit (₱) <span class="text-error">*</span>
                    </label>
                    <input 
                      id="batch_cost_price"
                      v-model.number="batchForm.cost_price" 
                      type="number" 
                      step="0.01"
                      min="0"
                      :required="createWithStock"
                      :disabled="isLoading"
                      placeholder="0.00"
                      class="form-control input-theme"
                      :class="{ 
                        'is-invalid': validationErrors.batch_cost_price,
                        'validation-error': validationErrors.batch_cost_price 
                      }"
                    />
                    <div v-if="validationErrors.batch_cost_price" class="invalid-feedback">
                      {{ validationErrors.batch_cost_price }}
                    </div>
                  </div>
                </div>

                <div class="row g-3 mb-3">
                  <div class="col-md-6">
                    <label for="batch_expiry_date" class="form-label text-primary fw-medium">
                      Expiry Date <span class="text-error">*</span>
                    </label>
                    <input 
                      id="batch_expiry_date"
                      v-model="batchForm.expiry_date" 
                      type="date" 
                      :required="createWithStock"
                      :disabled="isLoading"
                      :min="tomorrow"
                      class="form-control input-theme"
                      :class="{ 
                        'is-invalid': validationErrors.batch_expiry_date,
                        'validation-error': validationErrors.batch_expiry_date 
                      }"
                    />
                    <div v-if="validationErrors.batch_expiry_date" class="invalid-feedback">
                      {{ validationErrors.batch_expiry_date }}
                    </div>
                    <small class="text-tertiary-medium">
                      Expiry date for this batch
                    </small>
                  </div>

                  <div class="col-md-6">
                    <label for="batch_number" class="form-label text-primary fw-medium">
                      Batch Number
                    </label>
                    <input 
                      id="batch_number"
                      v-model="batchForm.batch_number" 
                      type="text" 
                      :disabled="isLoading"
                      placeholder="Auto-generated if empty"
                      class="form-control input-theme"
                    />
                    <small class="text-tertiary-medium">
                      Leave empty to auto-generate
                    </small>
                  </div>
                </div>

                <div class="row g-3 mb-3">
                  <div class="col-md-6">
                    <label for="supplier_id" class="form-label text-primary fw-medium">
                      Supplier
                    </label>
                    <select 
                      id="supplier_id"
                      v-model="batchForm.supplier_id" 
                      class="form-select input-theme"
                      :disabled="isLoading"
                    >
                      <option value="">Select Supplier</option>
                      <option 
                        v-for="supplier in suppliers" 
                        :key="supplier._id" 
                        :value="supplier._id"
                      >
                        {{ supplier.supplier_name || supplier.name }}
                      </option>
                    </select>
                  </div>

                  <div class="col-md-6">
                    <label for="date_received" class="form-label text-primary fw-medium">
                      Date Received
                    </label>
                    <input 
                      id="date_received"
                      v-model="batchForm.date_received" 
                      type="date" 
                      :disabled="isLoading"
                      :max="today"
                      class="form-control input-theme"
                    />
                    <small class="text-tertiary-medium">
                      Defaults to today if empty
                    </small>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="row g-3 mb-3">
            <div class="col-md-6">
              <label for="unit" class="form-label text-primary fw-medium">
                Unit <span class="text-error">*</span>
              </label>
              <select 
                id="unit"
                v-model="productForm.unit" 
                required 
                :disabled="isLoading"
                class="form-select input-theme"
                :class="{ 
                  'is-invalid': validationErrors.unit,
                  'validation-error': validationErrors.unit 
                }"
              >
                <option value="">Select Unit</option>
                <option value="piece">Pieces</option>
                <option value="pack">Pack</option>
                <option value="bottle">Bottle</option>
                <option value="can">Can</option>
                <option value="kg">Kilogram</option>
                <option value="liter">Liter</option>
              </select>
              <div v-if="validationErrors.unit" class="invalid-feedback">
                {{ validationErrors.unit }}
              </div>
            </div>

            <div class="col-md-6">
              <label for="selling_price" class="form-label text-primary fw-medium">
                Selling Price (₱) <span class="text-error">*</span>
              </label>
              <input 
                id="selling_price"
                v-model.number="productForm.selling_price" 
                type="number" 
                step="0.01"
                min="0"
                required 
                :disabled="isLoading"
                placeholder="0.00"
                class="form-control input-theme"
                :class="{ 
                  'is-invalid': validationErrors.selling_price,
                  'validation-error': validationErrors.selling_price 
                }"
                @input="calculateMargin"
              />
              <div v-if="validationErrors.selling_price" class="invalid-feedback">
                {{ validationErrors.selling_price }}
              </div>
              <small v-if="marginPercentage && createWithStock" class="text-tertiary-medium">
                Profit Margin: {{ marginPercentage }}%
              </small>
            </div>
          </div>

          <div class="row g-3 mb-3">
            <div class="col-md-6">
              <label for="low_stock_threshold" class="form-label text-primary fw-medium">
                Low Stock Threshold <span class="text-error">*</span>
              </label>
              <input 
                id="low_stock_threshold"
                v-model.number="productForm.low_stock_threshold" 
                type="number" 
                min="0"
                required 
                :disabled="isLoading"
                placeholder="10"
                class="form-control input-theme"
                :class="{ 
                  'is-invalid': validationErrors.low_stock_threshold,
                  'validation-error': validationErrors.low_stock_threshold 
                }"
              />
              <div v-if="validationErrors.low_stock_threshold" class="invalid-feedback">
                {{ validationErrors.low_stock_threshold }}
              </div>
            </div>

            <div class="col-md-6">
              <label for="status" class="form-label text-primary fw-medium">
                Status <span class="text-error">*</span>
              </label>
              <select 
                id="status"
                v-model="productForm.status" 
                required 
                :disabled="isLoading"
                class="form-select input-theme"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>

          <div class="row g-3 mb-3">
            <div class="col-md-8">
              <label for="barcode" class="form-label text-primary fw-medium">Barcode:</label>
              <div class="input-group">
                <input 
                  id="barcode"
                  v-model="productForm.barcode" 
                  type="text" 
                  :disabled="isLoading"
                  placeholder="Enter barcode or generate automatically"
                  class="form-control input-theme"
                />
                <button 
                  type="button" 
                  @click="generateBarcode"
                  :disabled="isLoading"
                  class="btn btn-export btn-with-icon-sm"
                >
                  <BarChart3 :size="16" />
                  Generate
                </button>
              </div>
            </div>

            <div class="col-md-4 d-flex align-items-end">
              <div class="form-check">
                <input 
                  id="is_taxable"
                  v-model="productForm.is_taxable" 
                  type="checkbox" 
                  :disabled="isLoading"
                  class="form-check-input"
                />
                <label for="is_taxable" class="form-check-label text-secondary">
                  Taxable Item
                </label>
              </div>
            </div>
          </div>

          <div class="mb-3">
            <label for="description" class="form-label text-primary fw-medium">Description:</label>
            <textarea 
              id="description"
              v-model="productForm.description" 
              :disabled="isLoading"
              placeholder="Enter product description (optional)"
              class="form-control input-theme"
              rows="3"
            ></textarea>
          </div>

          <!-- Validation Error Summary -->
          <div v-if="showValidationSummary && Object.keys(validationErrors).length > 0" 
               class="status-error mb-3" 
               role="alert">
            <strong>Please fix the following errors:</strong>
            <ul class="mb-0 mt-2">
              <li v-for="(error, field) in validationErrors" :key="field">
                {{ error }}
              </li>
            </ul>
          </div>

          <!-- General Error -->
          <div v-if="error" class="status-error mb-3" role="alert">
            <strong>Error:</strong> {{ error }}
          </div>

          <div class="d-flex gap-2 justify-content-end pt-3 divider-theme">
            <button 
              type="button" 
              @click="closeModal" 
              :disabled="isLoading"
              class="btn btn-cancel"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              :disabled="isLoading" 
              class="btn btn-save btn-with-icon-sm"
              :class="{ 'btn-loading': isLoading }"
            >
              <span v-if="isLoading" class="spinner-border spinner-border-sm me-2" role="status">
                <span class="visually-hidden">Loading...</span>
              </span>
              <Save :size="16" />
              {{ isLoading ? 'Saving...' : (isEditMode ? 'Update Product' : 'Create Product') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { X, Camera, Save, BarChart3, Package } from 'lucide-vue-next'
import { useModal } from '@/composables/ui/useModal'
import { useProducts } from '@/composables/api/useProducts'
import apiProductsService from '@/services/apiProducts'   // ✅ supplier API already available

export default {
  name: 'AddProductModal',
  components: { X, Camera, Save, BarChart3, Package },

  props: {
    categories: { type: Array, default: () => [] }
  },

  emits: ['success'],

  setup(props, { emit }) {
    // ========== EXISTING MODAL STATE ==========
    const {
      isVisible,
      isLoading,
      error,
      show,
      hide,
      setLoading,
      setError,
      clearError
    } = useModal()

    const { createProduct, updateProduct, checkSkuExists } = useProducts()

    // ========== ADDED SUPPLIER STATE ==========
    const suppliers = ref([])

    const loadSuppliers = async () => {
      try {
        const res = await apiProductsService.getAllSuppliers()

        // Extract the supplier list correctly
        if (Array.isArray(res.suppliers)) {
          suppliers.value = res.suppliers
        } else if (Array.isArray(res.data?.suppliers)) {
          suppliers.value = res.data.suppliers
        } else {
          suppliers.value = []
        }

      } catch (err) {
        console.error("❌ Failed to load suppliers:", err)
      }
    }


    // Fetch suppliers when modal mounts
    onMounted(() => {
      loadSuppliers()
      document.addEventListener('keydown', handleKeydown)
    })

    onBeforeUnmount(() => {
      document.removeEventListener('keydown', handleKeydown)
    })

    // ========== EXISTING FORM STATE ==========
    const editingProduct = ref(null)
    const imagePreview = ref(null)
    const skuError = ref('')
    const isValidatingSku = ref(false)
    const imageInputKey = ref(0)
    const validationErrors = ref({})
    const showValidationSummary = ref(false)
    const createWithStock = ref(false)

    const today = computed(() => new Date().toISOString().split('T')[0])
    const tomorrow = computed(() => {
      const date = new Date()
      date.setDate(date.getDate() + 1)
      return date.toISOString().split('T')[0]
    })

    const productForm = ref({
      product_name: '',
      SKU: '',
      category_id: '',
      subcategory_name: '',
      unit: '',
      selling_price: 0,
      low_stock_threshold: 10,
      status: 'active',
      barcode: '',
      is_taxable: true,
      description: '',
      image_url: '',
      image_filename: '',
      image_size: 0,
      image_type: ''
    })

    const batchForm = ref({
      quantity_received: 0,
      cost_price: 0,
      expiry_date: '',
      batch_number: '',
      supplier_id: '',
      date_received: today.value
    })

    const isEditMode = computed(() => editingProduct.value !== null)

    const availableSubcategories = computed(() => {
      if (!productForm.value.category_id) return []
      const category = props.categories.find(c => c._id === productForm.value.category_id)
      return category?.sub_categories || []
    })

    const marginPercentage = computed(() => {
      if (!createWithStock.value) return 0
      const { cost_price } = batchForm.value
      const { selling_price } = productForm.value
      if (!cost_price || !selling_price || cost_price >= selling_price) return 0
      return Math.round(((selling_price - cost_price) / selling_price) * 100)
    })

    // ========== VALIDATION + METHODS (UNCHANGED) ==========
    const validateForm = () => {
      const errors = {}

      if (!productForm.value.product_name.trim()) {
        errors.product_name = 'Product name is required'
      }
      if (!productForm.value.SKU.trim()) {
        errors.SKU = 'SKU is required'
      }
      if (!productForm.value.unit) {
        errors.unit = 'Unit is required'
      }
      if (!productForm.value.selling_price || productForm.value.selling_price <= 0) {
        errors.selling_price = 'Selling price must be greater than 0'
      }
      if (productForm.value.low_stock_threshold < 0) {
        errors.low_stock_threshold = 'Low stock threshold cannot be negative'
      }

      if (createWithStock.value) {
        if (!batchForm.value.quantity_received || batchForm.value.quantity_received <= 0) {
          errors.initial_stock = 'Initial stock must be greater than 0'
        }
        if (!batchForm.value.cost_price || batchForm.value.cost_price <= 0) {
          errors.batch_cost_price = 'Cost price is required'
        }
        if (!batchForm.value.expiry_date) {
          errors.batch_expiry_date = 'Expiry date is required'
        } else {
          const exp = new Date(batchForm.value.expiry_date)
          const todayDate = new Date()
          todayDate.setHours(0, 0, 0, 0)
          if (exp <= todayDate) {
            errors.batch_expiry_date = 'Expiry date must be in the future'
          }
        }
      }

      if (skuError.value) errors.SKU = skuError.value

      validationErrors.value = errors
      showValidationSummary.value = Object.keys(errors).length > 0

      return Object.keys(errors).length === 0
    }

    const resetForm = () => {
      productForm.value = {
        product_name: '',
        SKU: '',
        category_id: '',
        subcategory_name: '',
        unit: '',
        selling_price: 0,
        low_stock_threshold: 10,
        status: 'active',
        barcode: '',
        is_taxable: true,
        description: '',
        image_url: '',
        image_filename: '',
        image_size: 0,
        image_type: ''
      }

      batchForm.value = {
        quantity_received: 0,
        cost_price: 0,
        expiry_date: '',
        batch_number: '',
        supplier_id: '',
        date_received: today.value
      }

      createWithStock.value = false
      editingProduct.value = null
      imagePreview.value = null
      skuError.value = ''
      imageInputKey.value++
      clearError()
      validationErrors.value = {}
      showValidationSummary.value = false
    }

    const onCategoryChange = () => {
      productForm.value.subcategory_name = ''
    }

    const onStockModeChange = () => {
      delete validationErrors.value.initial_stock
      delete validationErrors.value.batch_cost_price
      delete validationErrors.value.batch_expiry_date
    }

    const validateSKU = async () => {
      if (!productForm.value.SKU.trim()) return skuError.value = ''
      if (isEditMode.value && productForm.value.SKU === editingProduct.value?.SKU) {
        return skuError.value = ''
      }

      isValidatingSku.value = true
      skuError.value = ''

      try {
        const exists = await checkSkuExists(productForm.value.SKU)
        if (exists) skuError.value = 'This SKU is already used'
      } catch {
        skuError.value = 'Unable to validate SKU'
      } finally {
        isValidatingSku.value = false
      }
    }

    const generateBarcode = () => {
      const timestamp = Date.now().toString()
      const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0')
      productForm.value.barcode = `${timestamp}${random}`
    }

    const handleImageUpload = (event) => {
      const file = event.target.files[0]
      if (!file) return

      const reader = new FileReader()
      reader.onload = e => {
        imagePreview.value = e.target.result
        productForm.value.image_url = e.target.result
      }
      reader.readAsDataURL(file)

      productForm.value.image_filename = file.name
      productForm.value.image_size = file.size
      productForm.value.image_type = file.type
    }

    const removeImage = () => {
      imagePreview.value = null
      productForm.value.image_url = ''
      productForm.value.image_filename = ''
      productForm.value.image_size = 0
      productForm.value.image_type = ''
      imageInputKey.value++
    }

    const handleSubmit = async () => {
      if (!validateForm()) return
      setLoading(true)
      clearError()

      try {
        let result
        const formData = { ...productForm.value }

        if (createWithStock.value) {
          formData.stock = batchForm.value.quantity_received
          formData.cost_price = batchForm.value.cost_price
          formData.expiry_date = batchForm.value.expiry_date
          formData.supplier_id = batchForm.value.supplier_id || undefined
          formData.date_received = batchForm.value.date_received || undefined
        } else {
          formData.stock = 0
        }

        if (!formData.category_id) {
          formData.category_id = 'UNCTGRY-001'
          formData.subcategory_name = 'General'
        }

        if (isEditMode.value) {
          result = await updateProduct(editingProduct.value._id, formData)
        } else {
          result = await createProduct(formData)
        }

        emit('success', {
          message: `Product "${formData.product_name}" ${isEditMode.value ? 'updated' : 'created'} successfully`,
          product: result.data,
          action: isEditMode.value ? 'updated' : 'created',
          withBatch: !isEditMode.value && createWithStock.value
        })

      } catch (err) {
        setError(err.message || 'Failed to save product')
      } finally {
        setLoading(false)
        closeModal()
      }
    }

    const closeModal = () => {
      if (!isLoading.value) {
        hide()
        resetForm()
      }
    }

    const handleOverlayClick = () => {
      if (!isLoading.value) closeModal()
    }

    const handleKeydown = (event) => {
      if (event.key === 'Escape' && isVisible.value && !isLoading.value) {
        closeModal()
      }
    }

    return {
      // state
      isVisible,
      isLoading,
      error,
      productForm,
      batchForm,
      suppliers,   // ✅ ADDED
      imagePreview,
      skuError,
      isValidatingSku,
      imageInputKey,
      validationErrors,
      showValidationSummary,
      createWithStock,

      // computed
      isEditMode,
      availableSubcategories,
      marginPercentage,
      today,
      tomorrow,

      // methods
      closeModal,
      handleSubmit,
      handleOverlayClick,
      onCategoryChange,
      onStockModeChange,
      validateSKU,
      generateBarcode,
      handleImageUpload,
      removeImage,
      validateForm,

      // modal triggers
      openAdd: () => { resetForm(); show() },
      openEdit: (product) => {
        resetForm()
        editingProduct.value = { ...product }
        Object.keys(productForm.value).forEach(key => {
          if (product[key] !== undefined) {
            productForm.value[key] = product[key]
          }
        })
        if (product.image_url) imagePreview.value = product.image_url
        show()
      }
    }
  }
}
</script>

<style scoped>
/* Existing styles plus new batch-specific styles */
.batch-fields {
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: 0.5rem;
  padding: 1rem;
  margin-top: 0.5rem;
}

.surface-elevated {
  background-color: var(--surface-elevated);
  border: 1px solid var(--border-secondary);
}

.batch-fields .form-label {
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.form-check-input:checked {
  background-color: var(--text-accent);
  border-color: var(--text-accent);
}

/* All other existing styles remain the same */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background-color: rgba(0, 0, 0, 0.5) !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  z-index: 9999 !important;
  animation: fadeIn 0.3s ease;
  backdrop-filter: blur(4px);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  position: relative !important;
  max-width: 800px;
  width: 95%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
  z-index: 10000 !important;
}

@keyframes slideIn {
  from { 
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  padding: 1.5rem 2rem 1rem 2rem;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
  padding: 0.25rem;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover:not(:disabled) {
  background-color: var(--state-hover);
  color: var(--text-primary);
}

.btn-close:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.product-form {
  padding: 1.5rem 2rem 2rem 2rem;
}

.image-upload-container {
  width: 100%;
  border: 2px dashed var(--border-secondary);
  transition: border-color 0.2s ease;
}

.image-upload-container:hover {
  border-color: var(--border-accent);
}

.upload-icon {
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: center;
}

.divider-theme {
  border-top: 1px solid var(--border-secondary) !important;
  margin: 0;
  padding-top: 1rem;
}

.validation-spinner {
  z-index: 10;
}

.validation-error {
  border-color: var(--status-error) !important;
  animation: errorPulse 0.6s ease-in-out;
}

@keyframes errorPulse {
  0% { 
    border-color: var(--status-error);
    box-shadow: 0 0 0 0 rgba(229, 57, 53, 0.4);
  }
  50% { 
    border-color: var(--status-error);
    box-shadow: 0 0 0 4px rgba(229, 57, 53, 0.2);
  }
  100% { 
    border-color: var(--status-error);
    box-shadow: 0 0 0 0 rgba(229, 57, 53, 0);
  }
}

.is-invalid {
  border-color: var(--status-error) !important;
}

.invalid-feedback {
  display: block !important;
  color: var(--status-error) !important;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

@media (max-width: 768px) {
  .modal-content {
    margin: 1rem;
    max-height: calc(100vh - 2rem);
  }

  .modal-header {
    padding: 1rem 1.5rem 0.75rem 1.5rem;
  }

  .modal-header h2 {
    font-size: 1.25rem;
  }

  .product-form {
    padding: 1rem 1.5rem 1.5rem 1.5rem;
  }
}

@media (max-width: 480px) {
  .modal-content {
    margin: 0.5rem;
    max-height: calc(100vh - 1rem);
    border-radius: 8px;
  }

  .modal-header {
    padding: 0.75rem 1rem 0.5rem 1rem;
  }

  .product-form {
    padding: 0.75rem 1rem 1rem 1rem;
  }
}

.modal-content::-webkit-scrollbar {
  width: 6px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--surface-tertiary);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--border-accent);
}

body:has(.modal-overlay) {
  overflow: hidden !important;
}
</style>