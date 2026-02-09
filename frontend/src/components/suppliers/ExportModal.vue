<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Export Suppliers</h5>
          <button 
            type="button" 
            class="btn-close" 
            @click="$emit('close')"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <p class="mb-4 text-muted">
            Choose the format you want to export your suppliers data:
          </p>
          
          <div class="export-options">
            <div class="row g-3">
              <div class="col-6">
                <div 
                  class="export-option"
                  :class="{ active: selectedFormat === 'excel' }"
                  @click="$emit('select-format', 'excel')"
                >
                  <div class="export-icon excel">
                    <i class="bi bi-file-earmark-excel"></i>
                  </div>
                  <div class="export-details">
                    <h6>Excel</h6>
                    <small class="text-muted">.xlsx format</small>
                  </div>
                </div>
              </div>
              
              <div class="col-6">
                <div 
                  class="export-option"
                  :class="{ active: selectedFormat === 'csv' }"
                  @click="$emit('select-format', 'csv')"
                >
                  <div class="export-icon csv">
                    <i class="bi bi-file-earmark-text"></i>
                  </div>
                  <div class="export-details">
                    <h6>CSV</h6>
                    <small class="text-muted">.csv format</small>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Export Options -->
          <div class="mt-4">
            <h6 class="mb-3">Export Options</h6>
            <div class="form-check">
              <input 
                class="form-check-input" 
                type="checkbox" 
                id="includeInactive"
                :checked="options.includeInactive"
                @change="$emit('update-option', 'includeInactive', $event.target.checked)"
              >
              <label class="form-check-label" for="includeInactive">
                Include inactive suppliers
              </label>
            </div>
            <div class="form-check">
              <input 
                class="form-check-input" 
                type="checkbox" 
                id="includeDetails"
                :checked="options.includeDetails"
                @change="$emit('update-option', 'includeDetails', $event.target.checked)"
              >
              <label class="form-check-label" for="includeDetails">
                Include detailed information
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button 
            type="button" 
            class="btn btn-secondary" 
            @click="$emit('close')"
          >
            Cancel
          </button>
          <button 
            type="button" 
            class="btn btn-primary"
            @click="$emit('export')"
            :disabled="!selectedFormat"
          >
            <i class="bi bi-download me-2"></i>
            Export
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ExportModal',
  emits: ['close', 'select-format', 'update-option', 'export'],
  props: {
    show: {
      type: Boolean,
      default: false
    },
    selectedFormat: {
      type: String,
      default: ''
    },
    options: {
      type: Object,
      default: () => ({
        includeInactive: false,
        includeDetails: true
      })
    }
  }
}
</script>

<style scoped>
/* Export modal styling */
.export-option {
  padding: 1rem;
  border: 2px solid var(--neutral-medium);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
  background-color: white;
}

.export-option:hover {
  border-color: var(--primary-light);
  box-shadow: 0 2px 8px rgba(115, 146, 226, 0.1);
}

.export-option.active {
  border-color: var(--primary);
  background-color: var(--primary-light);
}

.export-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 0.5rem;
  font-size: 1.5rem;
}

.export-icon.excel {
  background-color: #e8f5e8;
  color: #28a745;
}

.export-icon.csv {
  background-color: #fff3cd;
  color: #ffc107;
}

.export-details h6 {
  margin-bottom: 0.25rem;
  color: var(--tertiary-dark);
  font-weight: 600;
}

.export-details small {
  color: var(--tertiary-medium);
}

.form-check-label {
  color: var(--tertiary-dark);
  margin-left: 0.5rem;
}

.form-check-input:checked {
  background-color: var(--primary);
  border-color: var(--primary);
}
</style>