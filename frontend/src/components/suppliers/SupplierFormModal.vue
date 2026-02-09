<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content modern-supplier-modal" @click.stop>
        <!-- Modal Header -->
        <div class="modal-header border-0 pb-0">
          <div class="d-flex align-items-center">
            <div class="modal-icon me-3">
              <Building :size="24" />
            </div>
            <div>
              <h4 class="modal-title mb-1">{{ isEdit ? 'Edit Supplier' : 'Add New Supplier' }}</h4>
              <p class="text-muted mb-0 small">{{ isEdit ? 'Update supplier information' : 'Enter supplier details to add them to your network' }}</p>
            </div>
          </div>
          <button 
            type="button" 
            class="btn-close" 
            @click="$emit('close')"
            aria-label="Close"
          ></button>
        </div>

        <!-- Modal Body -->
        <div class="modal-body pt-4">
          <form @submit.prevent="handleSubmit">
            <div class="row g-4">
              <!-- Left Column -->
              <div class="col-md-6">
                <!-- Company/Supplier Name -->
                <div class="form-group">
                  <label for="supplierName" class="form-label required">
                    <Building :size="16" class="me-2" />
                    Company Name
                  </label>
                  <input 
                    type="text" 
                    class="form-control modern-input" 
                    :class="{ 'is-invalid': formErrors.name }"
                    id="supplierName"
                    v-model="formData.name"
                    @input="$emit('clear-error', 'name')"
                    placeholder="Enter company or supplier name"
                    required
                  >
                  <div v-if="formErrors.name" class="invalid-feedback">
                    {{ formErrors.name }}
                  </div>
                </div>

                <!-- Contact Person -->
                <div class="form-group">
                  <label for="contactPerson" class="form-label">
                    <i class="bi bi-person me-2"></i>
                    Contact Person
                  </label>
                  <input 
                    type="text" 
                    class="form-control modern-input"
                    id="contactPerson"
                    v-model="formData.contactPerson"
                    placeholder="Primary contact name"
                  >
                </div>

                <!-- Email -->
                <div class="form-group">
                  <label for="email" class="form-label">
                    <Mail :size="16" class="me-2" />
                    Email Address
                  </label>
                  <input 
                    type="email" 
                    class="form-control modern-input" 
                    :class="{ 'is-invalid': formErrors.email }"
                    id="email"
                    v-model="formData.email"
                    @input="$emit('clear-error', 'email')"
                    placeholder="company@example.com"
                  >
                  <div v-if="formErrors.email" class="invalid-feedback">
                    {{ formErrors.email }}
                  </div>
                </div>
              </div>

              <!-- Right Column -->
              <div class="col-md-6">
                <!-- Phone Number -->
                <div class="form-group">
                  <label for="phone" class="form-label">
                    <Phone :size="16" class="me-2" />
                    Phone Number
                  </label>
                  <input 
                    type="tel" 
                    class="form-control modern-input" 
                    :class="{ 'is-invalid': formErrors.phone }"
                    id="phone"
                    v-model="formData.phone"
                    @input="$emit('clear-error', 'phone')"
                    placeholder="+63 912 345 6789"
                  >
                  <div v-if="formErrors.phone" class="invalid-feedback">
                    {{ formErrors.phone }}
                  </div>
                </div>

                <!-- Supplier Type -->
                <div class="form-group">
                  <label for="supplierType" class="form-label">
                    <i class="bi bi-tag me-2"></i>
                    Supplier Type
                  </label>
                  <select 
                    class="form-select modern-input" 
                    id="supplierType"
                    v-model="formData.type"
                  >
                    <option value="">Select supplier type</option>
                    <option value="food">Food & Beverages</option>
                    <option value="packaging">Packaging Materials</option>
                    <option value="equipment">Equipment & Tools</option>
                    <option value="services">Services</option>
                    <option value="raw_materials">Raw Materials</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <!-- Status -->
                <div class="form-group">
                  <label for="status" class="form-label">
                    <i class="bi bi-check-circle me-2"></i>
                    Status
                  </label>
                  <select 
                    class="form-select modern-input" 
                    id="status"
                    v-model="formData.status"
                  >
                    <option value="active">Active</option>
                    <option value="pending">Pending Approval</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <!-- Full Width Address -->
              <div class="col-12">
                <div class="form-group">
                  <label for="address" class="form-label">
                    <MapPin :size="16" class="me-2" />
                    Business Address
                  </label>
                  <textarea 
                    class="form-control modern-input" 
                    :class="{ 'is-invalid': formErrors.address }"
                    id="address"
                    v-model="formData.address"
                    @input="$emit('clear-error', 'address')"
                    rows="3"
                    placeholder="Enter complete business address including city and postal code"
                  ></textarea>
                  <div v-if="formErrors.address" class="invalid-feedback">
                    {{ formErrors.address }}
                  </div>
                </div>
              </div>

              <!-- Notes Section -->
              <div class="col-12">
                <div class="form-group mb-0">
                  <label for="notes" class="form-label">
                    <i class="bi bi-file-text me-2"></i>
                    Additional Notes
                  </label>
                  <textarea 
                    class="form-control modern-input" 
                    id="notes"
                    v-model="formData.notes"
                    rows="3"
                    placeholder="Any additional information about this supplier (payment terms, delivery schedules, etc.)"
                  ></textarea>
                  <small class="text-muted">Optional: Add any relevant notes about this supplier relationship</small>
                </div>
              </div>
            </div>
          </form>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer border-0 pt-4">
          <div class="d-flex justify-content-between align-items-center w-100">
            <div class="form-check">
              <input 
                class="form-check-input" 
                type="checkbox" 
                id="addAnother" 
                :checked="addAnother"
                @change="$emit('update:add-another', $event.target.checked)"
                >
              <label class="form-check-label text-muted" for="addAnother">
                Add another supplier after saving
              </label>
            </div>
            <div class="d-flex gap-3">
              <button 
                type="button" 
                class="btn btn-outline-secondary px-4"
                @click="$emit('close')"
              >
                Cancel
              </button>
              <button 
                type="button" 
                class="btn btn-primary px-4"
                @click="handleSubmit"
                :disabled="!isValid || loading"
                :class="{ 'btn-loading': loading }"
              >
                <div v-if="loading" class="spinner-border spinner-border-sm me-2" role="status">
                  <span class="visually-hidden">Loading...</span>
                </div>
                {{ isEdit ? 'Update Supplier' : 'Add Supplier' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { Building, Mail, Phone, MapPin } from 'lucide-vue-next'

export default {
  name: 'SupplierFormModal',
  components: {
    Building,
    Mail,
    Phone,
    MapPin
  },
  emits: ['close', 'save', 'clear-error', 'update:add-another'],
  props: {
    show: {
      type: Boolean,
      default: false
    },
    isEdit: {
      type: Boolean,
      default: false
    },
    formData: {
      type: Object,
      required: true
    },
    formErrors: {
      type: Object,
      default: () => ({})
    },
    loading: {
      type: Boolean,
      default: false
    },
    isValid: {
      type: Boolean,
      default: false
    },
    addAnother: {
      type: Boolean,
      default: false
    }
  },
  methods: {
    handleSubmit() {
      this.$emit('save')
    },
    handleOverlayClick() {
      if (!this.loading) {
        this.$emit('close')
      }
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';
/* Modal Overlay */
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

/* Modal Content */
.modal-content {
  position: relative !important;
  max-width: 800px;
  width: 95%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
  z-index: 10000 !important;
  background-color: var(--surface-elevated);
  border-radius: 16px;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-2xl);
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

/* Modern Modal styling */
.modern-supplier-modal {
  overflow: hidden;
}

.modal-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--primary-light), var(--primary));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-dark);
}

.modal-title {
  color: var(--text-primary);
  font-weight: 600;
  margin: 0;
}

.form-label {
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
}

.form-label.required::after {
  content: '*';
  color: var(--error);
  margin-left: 4px;
}

.modern-input {
  border: 2px solid var(--input-border);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  background-color: var(--input-bg);
  color: var(--input-text);
}

.modern-input:focus {
  border-color: var(--border-accent);
  box-shadow: 0 0 0 0.2rem rgba(160, 123, 227, 0.15);
  background-color: var(--input-bg);
}

.modern-input:hover:not(:focus) {
  border-color: var(--border-accent);
  background-color: var(--surface-tertiary);
}

.modern-input.is-invalid {
  border-color: var(--border-error);
  background-color: var(--surface-tertiary);
}

.form-group {
  margin-bottom: 1.5rem;
}

.modal-header {
  padding: 2rem 2rem 1rem 2rem;
  background-color: var(--surface-tertiary);
  border-bottom: 1px solid var(--border-primary);
}

.modal-body {
  padding: 1.5rem 2rem;
  background-color: var(--surface-elevated);
  overflow-y: auto;
}

.modal-footer {
  padding: 1rem 2rem 2rem 2rem;
  background-color: var(--surface-tertiary);
  border-top: 1px solid var(--border-primary);
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border: none;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(115, 146, 226, 0.3);
}

.btn-outline-secondary {
  border: 2px solid var(--neutral-medium);
  color: var(--tertiary-dark);
  border-radius: 8px;
  font-weight: 500;
}

.btn-outline-secondary:hover {
  background-color: var(--neutral-medium);
  border-color: var(--neutral-dark);
  color: white;
}

.form-check-label {
  color: var(--tertiary-dark);
  margin-left: 0.5rem;
}

.form-check-input:checked {
  background-color: var(--primary);
  border-color: var(--primary);
}

/* Responsive Styles */
@media (max-width: 768px) {
  .modal-content {
    margin: 1rem;
    max-height: calc(100vh - 2rem);
    width: calc(100% - 2rem);
  }

  .modal-header {
    padding: 1rem 1.5rem 0.75rem 1.5rem !important;
  }

  .modal-header h4 {
    font-size: 1.25rem;
  }

  .modal-body {
    padding: 1rem 1.5rem !important;
  }

  .modal-footer {
    padding: 0.75rem 1.5rem 1.5rem 1.5rem !important;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  /* Stack columns on mobile */
  .row > [class*="col-md-"] {
    width: 100%;
    flex: 0 0 100%;
    max-width: 100%;
  }
}

@media (max-width: 480px) {
  .modal-content {
    margin: 0.5rem;
    max-height: calc(100vh - 1rem);
    width: calc(100% - 1rem);
    border-radius: 8px;
  }

  .modal-header {
    padding: 0.75rem 1rem 0.5rem 1rem !important;
  }

  .modal-header h4 {
    font-size: 1.1rem;
  }

  .modal-body {
    padding: 0.75rem 1rem !important;
  }

  .modal-footer {
    padding: 0.5rem 1rem 1rem 1rem !important;
    flex-direction: column;
    gap: 0.75rem !important;
  }

  .modal-footer > div {
    flex-direction: column;
    width: 100%;
  }

  .modal-footer .form-check {
    width: 100%;
    margin-bottom: 0.5rem;
  }

  .modal-footer .d-flex {
    width: 100%;
    flex-direction: column;
    gap: 0.5rem !important;
  }

  .modal-footer .btn {
    width: 100%;
  }

  .form-group {
    margin-bottom: 0.75rem;
  }

  .modal-icon {
    width: 40px !important;
    height: 40px !important;
  }
}

/* Custom Scrollbar */
.modal-content::-webkit-scrollbar {
  width: 6px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--neutral-light);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--neutral-medium);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--primary);
}

/* Prevent body scroll when modal is open */
body:has(.modal-overlay) {
  overflow: hidden !important;
}
</style>