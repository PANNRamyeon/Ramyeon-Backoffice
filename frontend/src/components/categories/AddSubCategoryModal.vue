<template>
  <div 
    class="modal fade" 
    id="addSubcategoryModal" 
    tabindex="-1" 
    aria-labelledby="addSubcategoryModalLabel" 
    aria-hidden="true"
    ref="modal"
  >
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <!-- Modal Header -->
        <div class="modal-header">
          <h5 class="modal-title" id="addSubcategoryModalLabel">
            <Plus :size="20" class="me-2" />
            Add New Subcategory
          </h5>
          <button 
            type="button" 
            class="btn-close" 
            data-bs-dismiss="modal" 
            aria-label="Close"
            @click="closeModal"
          ></button>
        </div>

        <!-- Modal Body -->
        <div class="modal-body">
          <!-- Category Info -->
          <div class="mb-3">
            <small class="text-muted">
              Adding subcategory to: <strong>{{ categoryName }}</strong>
            </small>
          </div>

          <!-- Subcategory Name Input -->
          <div class="mb-3">
            <label for="subcategoryName" class="form-label">
              Subcategory Name <span class="text-danger">*</span>
            </label>
            <input
              id="subcategoryName"
              ref="nameInput"
              v-model="subcategoryData.name"
              type="text"
              class="form-control"
              :class="{ 'is-invalid': errors.name }"
              placeholder="Enter subcategory name"
              @input="clearError('name')"
              @keypress.enter="submitForm"
              maxlength="100"
            />
            <div v-if="errors.name" class="invalid-feedback">
              {{ errors.name }}
            </div>
          </div>

          <!-- Add Product Name Input Optional for now -->
          <!--<div class="mb-3">
            <label for="productName" class="form-label">
              Add Product Name <span class="text-muted">(Optional)</span>
            </label>
            <input
              id="productName"
              v-model="subcategoryData.productName"
              type="text"
              class="form-control"
              :class="{ 'is-invalid': errors.productName }"
              placeholder="Enter product name to add to this subcategory"
              @input="clearError('productName')"
              @keypress.enter="submitForm"
              maxlength="100"
            />
            <div v-if="errors.productName" class="invalid-feedback">
              {{ errors.productName }}
            </div>
            <small class="form-text text-muted">
              You can add a product to this subcategory immediately
            </small>
          </div>-->

          <!-- Preview -->
          <div v-if="subcategoryData.name" class="mb-3">
            <small class="text-muted d-block mb-1">Preview:</small>
            <div class="p-2 bg-light rounded border">
              <div class="fw-medium">{{ subcategoryData.name }}</div>
              <small class="text-muted d-block">
                Description: {{ subcategoryData.name }} products
              </small>
              <small v-if="subcategoryData.productName" class="text-success d-block mt-1">
                <strong>Initial Product:</strong> {{ subcategoryData.productName }}
              </small>
            </div>
          </div>

          <!-- Error Alert -->
          <div v-if="generalError" class="alert alert-danger" role="alert">
            <strong>Error:</strong> {{ generalError }}
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button 
            type="button" 
            class="btn btn-secondary" 
            @click="closeModal"
            :disabled="isSubmitting"
          >
            Cancel
          </button>
          <button 
            type="button" 
            class="btn btn-success" 
            @click="submitForm"
            :disabled="!isFormValid || isSubmitting"
          >
            <div v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <Plus v-else :size="16" class="me-1" />
            {{ isSubmitting ? 'Adding...' : 'Add Subcategory' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import categoryApiService from '@/services/apiCategory'
import { Plus } from 'lucide-vue-next'

export default {
  name: 'AddSubcategoryModal',
  components: {
    Plus
  },
  data() {
    return {
      // Form data
      subcategoryData: {
        name: '',
        productName: ''
      },
      
      // Modal state
      isSubmitting: false,
      categoryId: null,
      categoryName: '',
      
      // Validation
      errors: {},
      generalError: null,
      
      // Bootstrap modal instance
      modalInstance: null
    }
  },
  computed: {
    isFormValid() {
      return this.subcategoryData.name.trim().length > 0 && 
             Object.keys(this.errors).length === 0
    }
  },
  mounted() {
    // Initialize Bootstrap modal
    if (typeof window !== 'undefined' && window.bootstrap) {
      this.modalInstance = new window.bootstrap.Modal(this.$refs.modal, {
        backdrop: 'static', // Prevent closing by clicking backdrop
        keyboard: true      // Allow closing with Escape key
      })
    }
  },
  methods: {
    /**
     * Open the modal for adding a subcategory
     * @param {string} categoryId - Category ID to add subcategory to
     * @param {string} categoryName - Category name for display
     */
    openModal(categoryId, categoryName = 'Unknown Category') {
      // Set category info
      this.categoryId = categoryId
      this.categoryName = categoryName
      
      // Reset form
      this.resetForm()
      
      // Show modal
      if (this.modalInstance) {
        this.modalInstance.show()
      }
      
      // Focus on name input after modal is shown
      this.$nextTick(() => {
        if (this.$refs.nameInput) {
          this.$refs.nameInput.focus()
        }
      })
    },

    /**
     * Close the modal
     */
    closeModal() {
      if (this.modalInstance) {
        this.modalInstance.hide()
      }
      this.resetForm()
    },

    /**
     * Reset form data and errors
     */
    resetForm() {
      this.subcategoryData = {
        name: '',
        productName: ''
      }
      this.errors = {}
      this.generalError = null
      this.isSubmitting = false
    },

    /**
     * Clear specific field error
     */
    clearError(field) {
      if (this.errors[field]) {
        delete this.errors[field]
      }
      this.generalError = null
    },

    /**
     * Validate form data
     */
    validateForm() {
      const errors = {}
      
      // Validate name
      if (!this.subcategoryData.name.trim()) {
        errors.name = 'Subcategory name is required'
      } else if (this.subcategoryData.name.trim().length < 2) {
        errors.name = 'Subcategory name must be at least 2 characters'
      } else if (this.subcategoryData.name.trim().length > 100) {
        errors.name = 'Subcategory name must be less than 100 characters'
      }
      
      // Validate product name length (optional field)
      if (this.subcategoryData.productName && this.subcategoryData.productName.trim().length > 100) {
        errors.productName = 'Product name must be less than 100 characters'
      }
      
      this.errors = errors
      return Object.keys(errors).length === 0
    },

    /**
     * Submit the form
     */
    async submitForm() {
      try {
        // Validate form
        if (!this.validateForm()) {
          return
        }

        // Set loading state
        this.isSubmitting = true
        this.generalError = null

        // Prepare data
        const subcategoryData = {
          name: this.subcategoryData.name.trim(),
          description: `${this.subcategoryData.name.trim()} products`,
          productName: this.subcategoryData.productName.trim() || null
        }

        // Call API
        const result = await categoryApiService.AddSubCategoryData(
          this.categoryId,
          subcategoryData
        )
        
        // Emit success event to parent component
        this.$emit('subcategory-added', {
          categoryId: this.categoryId,
          subcategory: subcategoryData,
          result: result
        })
        
        // Show success message
        this.showSuccessMessage(`Subcategory "${subcategoryData.name}" added successfully!`)
        
        // Close modal
        this.closeModal()
        
      } catch (error) {
        console.error('❌ Error adding subcategory:', error)
        
        // Show error
        this.generalError = error.message || 'Failed to add subcategory. Please try again.'
        
        // Show error message
        this.showErrorMessage(`Failed to add subcategory: ${error.message}`)
        
      } finally {
        this.isSubmitting = false
      }
    },

    /**
     * Show success message (you can customize this based on your notification system)
     */
    showSuccessMessage(message) {
      // Replace with your notification system
      // this.$toast.success(message)
    },

    /**
     * Show error message (you can customize this based on your notification system)
     */
    showErrorMessage(message) {
      // Replace with your notification system
      // this.$toast.error(message)
    }
  }
}
</script>

<style scoped>
/* Modal customizations */
.modal-content {
  border-radius: 0.75rem;
  border: none;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
}

.modal-header {
  background-color: var(--primary-light, #f8f9ff);
  border-bottom: 1px solid var(--neutral, #e9ecef);
  border-radius: 0.75rem 0.75rem 0 0;
}

.modal-title {
  color: var(--primary-dark, #2c3e50);
  font-weight: 600;
  display: flex;
  align-items: center;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--neutral, #e9ecef);
  background-color: var(--neutral-light, #f8f9fa);
  border-radius: 0 0 0.75rem 0.75rem;
}

/* Form styling */
.form-control:focus {
  border-color: var(--primary, #007bff);
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.form-label {
  font-weight: 500;
  color: var(--tertiary-dark, #495057);
  margin-bottom: 0.5rem;
}

.is-invalid {
  border-color: #dc3545;
}

.invalid-feedback {
  display: block;
  font-size: 0.875rem;
  color: #dc3545;
  margin-top: 0.25rem;
}

/* Preview styling */
.bg-light {
  background-color: var(--neutral-light, #f8f9fa) !important;
}

/* Button styling */
.btn-success {
  background-color: var(--success, #28a745);
  border-color: var(--success, #28a745);
}

.btn-success:hover {
  background-color: var(--success-dark, #218838);
  border-color: var(--success-dark, #218838);
}

.btn-success:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Loading spinner */
.spinner-border-sm {
  width: 1rem;
  height: 1rem;
}

/* Responsive adjustments */
@media (max-width: 576px) {
  .modal-dialog {
    margin: 1rem;
  }
  
  .modal-body {
    padding: 1rem;
  }
  
  .modal-footer {
    padding: 0.75rem 1rem;
  }
}
</style>