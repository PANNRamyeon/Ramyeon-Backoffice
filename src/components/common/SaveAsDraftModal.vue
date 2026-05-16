<template>
  <!-- Bootstrap Modal with Teleport -->
  <Teleport to="body">
    <div 
      v-if="shouldRender"
      class="modal fade show d-block"
      :id="modalId" 
      tabindex="-1" 
      :aria-labelledby="`${modalId}Label`"
      aria-hidden="true"
      data-bs-backdrop="static"
      data-bs-keyboard="false"
      ref="modalElement"
      style="background-color: rgba(0, 0, 0, 0.5); z-index: 1055;"
      @click="handleBackdropClick"
    >
      <div class="modal-dialog modal-dialog-centered" style="max-width: 580px;">
        <div class="modal-content border-0 shadow-lg" style="border-radius: 1rem;" @click.stop>
          
          <!-- Modal Header -->
          <div class="modal-header border-0 bg-light px-4 py-4 position-relative" style="border-radius: 1rem 1rem 0 0;">
            <div class="d-flex align-items-center w-100">
              <!-- Warning Icon -->
              <div class="me-3">
                <div class="d-flex align-items-center justify-content-center bg-warning bg-opacity-20 border border-warning border-3 rounded-circle"
                     style="width: 60px; height: 60px;">
                  <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="text-warning" viewBox="0 0 16 16">
                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
                  </svg>
                </div>
              </div>
              
              <!-- Title Section -->
              <div class="flex-grow-1">
                <h4 class="modal-title fw-bold text-dark mb-1 fs-4" :id="`${modalId}Label`">
                  {{ title }}
                </h4>
                <p class="text-muted mb-0 fs-6">{{ subtitle }}</p>
              </div>
            </div>
            
            <!-- Close Button -->
            <button 
              type="button" 
              class="position-absolute top-0 end-0 mt-3 me-3 close-button"
              @click="handleCancel"
              aria-label="Close"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 16 16">
                <path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8 2.146 2.854Z"/>
              </svg>
            </button>
          </div>

          <!-- Modal Body -->
          <div class="modal-body px-4 py-4">
            
            <!-- Main Message -->
            <div class="mb-4">
              <p class="text-secondary fs-6 lh-base mb-3">
                {{ message }}
              </p>
              
              <!-- Data Summary Card -->
              <div v-if="dataSummary" class="summary-card border-start border-4 rounded-3">
                <div class="row g-3">
                  <div class="col-6" v-for="(value, key) in dataSummary" :key="key">
                    <div class="d-flex flex-column">
                      <small class="summary-label text-uppercase fw-semibold mb-1" style="font-size: 0.75rem; letter-spacing: 0.5px;">
                        {{ formatLabel(key) }}
                      </small>
                      <span class="summary-value fw-bold fs-5">{{ value }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Draft Name Input Section -->
            <div v-if="showDraftNameInput">
              <label :for="`${modalId}DraftName`" class="form-label fw-semibold text-dark mb-2 d-flex align-items-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="text-primary me-2" viewBox="0 0 16 16">
                  <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v13.5a.5.5 0 0 1-.777.416L8 13.101l-5.223 2.815A.5.5 0 0 1 2 15.5V2zm2-1a1 1 0 0 0-1 1v12.566l4.723-2.482a.5.5 0 0 1 .554 0L13 14.566V2a1 1 0 0 0-1-1H4z"/>
                </svg>
                Draft Name
              </label>
              
              <input 
                type="text" 
                class="form-control form-control-lg border-2 rounded-3"
                :id="`${modalId}DraftName`"
                v-model="draftName"
                :placeholder="defaultDraftName"
                maxlength="50"
                ref="draftNameInput"
                style="padding: 0.875rem 1.125rem; font-weight: 500;"
              >
              
              <div class="form-text mt-2 d-flex align-items-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="text-info me-2" viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                  <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/>
                </svg>
                <span class="small">This will help you identify the draft later</span>
              </div>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="modal-footer border-0 bg-light px-4 py-4 justify-content-end" style="border-radius: 0 0 1rem 1rem;">
            <div class="d-flex gap-3">
              
              <!-- Discard Button -->
              <button 
                type="button" 
                class="btn btn-outline-danger d-flex align-items-center px-4 fw-semibold rounded-3 btn-hover-effect"
                @click="handleDiscard"
                :disabled="loading"
                style="min-width: 140px; transition: all 0.2s ease; padding-top: 0.5rem; padding-bottom: 0.5rem;"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="me-2" viewBox="0 0 16 16">
                  <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6Z"/>
                  <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1ZM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118ZM2.5 3h11V2h-11v1Z"/>
                </svg>
                {{ discardText }}
              </button>

              <!-- Save Draft Button -->
              <button 
                type="button" 
                class="btn btn-primary d-flex align-items-center px-4 fw-semibold rounded-3 btn-hover-effect"
                @click="handleSaveDraft"
                :disabled="loading || (showDraftNameInput && !draftName.trim())"
                style="min-width: 140px; transition: all 0.2s ease; padding-top: 0.5rem; padding-bottom: 0.5rem;"
              >
                <div v-if="loading" class="spinner-border spinner-border-sm me-2" role="status">
                  <span class="visually-hidden">Loading...</span>
                </div>
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="me-2" viewBox="0 0 16 16">
                  <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v13.5a.5.5 0 0 1-.777.416L8 13.101l-5.223 2.815A.5.5 0 0 1 2 15.5V2zm2-1a1 1 0 0 0-1 1v12.566l4.723-2.482a.5.5 0 0 1 .554 0L13 14.566V2a1 1 0 0 0-1-1H4z"/>
                  <path d="M8 4a.5.5 0 0 1 .5.5V6H10a.5.5 0 0 1 0 1H8.5v1.5a.5.5 0 0 1-1 0V7H6a.5.5 0 0 1 0-1h1.5V4.5A.5.5 0 0 1 8 4z"/>
                </svg>
                {{ loading ? savingText : saveText }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
export default {
  name: 'SaveAsDraftModal',
  props: {
    show: { type: Boolean, default: false },
    modalId: { type: String, default: 'saveDraftModal' },
    title: { type: String, default: 'Unsaved Changes' },
    subtitle: { type: String, default: 'You have unsaved work' },
    message: { type: String, default: 'You have unsaved changes that will be lost if you leave this page. Would you like to save your progress as a draft?' },
    dataSummary: { type: Object, default: null },
    showDraftNameInput: { type: Boolean, default: true },
    defaultDraftName: { type: String, default: () => `Draft ${new Date().toLocaleDateString()}` },
    saveText: { type: String, default: 'Save as Draft' },
    savingText: { type: String, default: 'Saving...' },
    cancelText: { type: String, default: 'Cancel' },
    discardText: { type: String, default: 'Discard Changes' },
    loading: { type: Boolean, default: false }
  },
  emits: ['save-draft', 'discard', 'cancel', 'close'],
  data() {
    return {
      draftName: '',
      shouldRender: false
    }
  },
  watch: {
    show: {
      handler(newValue) {
        if (newValue) {
          this.openModal()
        } else {
          this.closeModal()
        }
      },
      immediate: false
    }
  },
  mounted() {
    this.draftName = this.defaultDraftName
    if (this.show) {
      this.openModal()
    }
  },
  methods: {
    async openModal() {
      this.shouldRender = true
      await this.$nextTick()
      this.focusInput()
    },
    
    closeModal() {
      this.shouldRender = false
      this.$emit('close')
    },
    
    handleBackdropClick(event) {
      if (event.target === this.$refs.modalElement) {
        this.closeModal()
      }
    },
    
    focusInput() {
      if (this.$refs.draftNameInput) {
        setTimeout(() => {
          this.$refs.draftNameInput.focus()
          this.$refs.draftNameInput.select()
        }, 200)
      }
    },
    
    handleSaveDraft() {
      const draftData = {
        name: this.draftName.trim() || this.defaultDraftName,
        timestamp: new Date().toISOString(),
        id: `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      }
      this.$emit('save-draft', draftData)
    },
    
    handleDiscard() {
      this.$emit('discard')
      this.closeModal()
    },
    
    handleCancel() {
      this.$emit('cancel')
      this.closeModal()
    },
    
    formatLabel(key) {
      return key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase()).trim()
    }
  }
}
</script>

<style scoped>
/* Minimal custom CSS - only for hover effects and colors.css integration */
@import '../../assets/styles/colors.css';

/* Button hover effects using colors.css variables */
.btn-hover-effect:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn-hover-effect:active:not(:disabled) {
  transform: translateY(0);
}

/* Override Bootstrap colors with colors.css variables */
.btn-primary {
  background-color: var(--primary) !important;
  border-color: var(--primary) !important;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--primary-dark) !important;
  border-color: var(--primary-dark) !important;
}

.btn-outline-danger {
  color: var(--error) !important;
  border-color: var(--error) !important;
}

.btn-outline-danger:hover:not(:disabled) {
  background-color: var(--error) !important;
  border-color: var(--error) !important;
}

.text-primary {
  color: var(--primary) !important;
}

.text-secondary {
  color: var(--tertiary-medium) !important;
}

.text-dark {
  color: var(--tertiary-dark) !important;
}

.text-muted {
  color: var(--tertiary-medium) !important;
}

/* Enhanced data summary card with lighter background */
.summary-card {
  background: linear-gradient(135deg, var(--primary-light) 0%, rgba(171, 189, 237, 0.6) 100%);
  border-color: var(--primary-medium) !important;
  padding: 1.25rem;
}

.summary-label {
  color: var(--primary-dark) !important;
  font-weight: 700 !important;
}

.summary-value {
  color: var(--primary-dark) !important;
  font-weight: 800 !important;
}

.border-primary {
  border-color: var(--primary) !important;
}

/* Close button styling with proper focus alignment */
.close-button {
  background: none;
  border: none;
  padding: 0.5rem;
  cursor: pointer;
  color: var(--tertiary-medium);
  border-radius: 0.375rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  transition: all 0.2s ease;
}

.close-button:hover {
  color: var(--tertiary-dark);
  background-color: rgba(0, 0, 0, 0.05);
}

.close-button:focus {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
  color: var(--tertiary-dark);
}

.close-button:active {
  background-color: rgba(0, 0, 0, 0.1);
  transform: scale(0.95);
}

/* Remove old btn-close styling */
.btn-close:hover {
  color: var(--tertiary-dark) !important;
  opacity: 0.8;
}

/* Form control focus using colors.css */
.form-control:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 0.2rem rgba(115, 146, 226, 0.25) !important;
}

/* Responsive - only what Bootstrap can't handle */
@media (max-width: 576px) {
  .modal-dialog {
    margin: 1rem;
    max-width: calc(100% - 2rem);
  }
  
  .d-flex.gap-3 {
    flex-direction: column;
    gap: 0.75rem !important;
  }
  
  .btn-hover-effect {
    width: 100%;
    min-width: auto !important;
  }
}
</style>