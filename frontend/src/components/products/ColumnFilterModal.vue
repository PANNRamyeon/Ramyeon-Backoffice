<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" @click="handleOverlayClick">
    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content modal-theme" @click.stop>
        <div class="modal-header surface-secondary border-bottom-theme">
          <div>
            <h5 class="modal-title text-accent fw-semibold">Column Visibility</h5>
            <p class="text-tertiary-medium small mb-0">Customize which columns are visible in your table</p>
          </div>
          <button type="button" class="btn-close" @click="$emit('close')">
            <X :size="20" />
          </button>
        </div>

        <div class="modal-body">
          <!-- Quick Actions -->
          <div class="d-flex gap-3 mb-4 pb-3 divider-theme">
            <button @click="selectAll" class="btn btn-add btn-sm">
              Show All
            </button>
            <button @click="selectNone" class="btn btn-cancel btn-sm">
              Hide All
            </button>
            <button @click="resetToDefault" class="btn btn-filter btn-sm">
              Reset Default
            </button>
          </div>

          <!-- Column Groups -->
          <div class="column-groups">
            <!-- Essential Columns (Always Required) -->
            <div class="mb-4">
              <h6 class="d-flex align-items-center gap-2 mb-3 text-primary fw-semibold">
                <Lock :size="18" class="text-accent" />
                Essential Columns
                <small class="text-tertiary-medium fw-normal ms-2">(Always visible)</small>
              </h6>
              <div class="row g-3">
                <div 
                  v-for="column in essentialColumns" 
                  :key="column.key"
                  class="col-12 col-md-6"
                >
                  <div class="card surface-tertiary border-secondary opacity-75">
                    <div class="card-body p-3">
                      <div class="form-check">
                        <input 
                          class="form-check-input" 
                          type="checkbox" 
                          :id="`col-${column.key}`"
                          :checked="true"
                          disabled
                        />
                        <label class="form-check-label d-flex flex-column" :for="`col-${column.key}`">
                          <span class="fw-semibold text-accent">{{ column.name }}</span>
                          <small class="text-tertiary-medium">{{ column.description }}</small>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Basic Information -->
            <div class="mb-4">
              <h6 class="d-flex align-items-center gap-2 mb-3 text-primary fw-semibold">
                <FileText :size="18" class="text-accent" />
                Basic Information
              </h6>
              <div class="row g-3">
                <div 
                  v-for="column in basicColumns" 
                  :key="column.key"
                  class="col-12 col-md-6"
                >
                  <div 
                    class="card column-card" 
                    :class="{ 
                      'border-accent state-selected': visibleColumns[column.key],
                      'surface-card border-secondary': !visibleColumns[column.key]
                    }"
                  >
                    <div class="card-body p-3">
                      <div class="form-check">
                        <input 
                          class="form-check-input" 
                          type="checkbox" 
                          :id="`col-${column.key}`"
                          v-model="visibleColumns[column.key]"
                          @change="updateColumnVisibility"
                        />
                        <label class="form-check-label d-flex flex-column" :for="`col-${column.key}`">
                          <span class="fw-semibold text-primary">{{ column.name }}</span>
                          <small class="text-tertiary-medium">{{ column.description }}</small>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Financial Information -->
            <div class="mb-4">
              <h6 class="d-flex align-items-center gap-2 mb-3 text-primary fw-semibold">
                <DollarSign :size="18" class="text-accent" />
                Financial Information
              </h6>
              <div class="row g-3">
                <div 
                  v-for="column in financialColumns" 
                  :key="column.key"
                  class="col-12 col-md-6"
                >
                  <div 
                    class="card column-card" 
                    :class="{ 
                      'border-accent state-selected': visibleColumns[column.key],
                      'surface-card border-secondary': !visibleColumns[column.key]
                    }"
                  >
                    <div class="card-body p-3">
                      <div class="form-check">
                        <input 
                          class="form-check-input" 
                          type="checkbox" 
                          :id="`col-${column.key}`"
                          v-model="visibleColumns[column.key]"
                          @change="updateColumnVisibility"
                        />
                        <label class="form-check-label d-flex flex-column" :for="`col-${column.key}`">
                          <span class="fw-semibold text-primary">{{ column.name }}</span>
                          <small class="text-tertiary-medium">{{ column.description }}</small>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Status & Dates -->
            <div class="mb-4">
              <h6 class="d-flex align-items-center gap-2 mb-3 text-primary fw-semibold">
                <Calendar :size="18" class="text-accent" />
                Status & Dates
              </h6>
              <div class="row g-3">
                <div 
                  v-for="column in statusColumns" 
                  :key="column.key"
                  class="col-12 col-md-6"
                >
                  <div 
                    class="card column-card" 
                    :class="{ 
                      'border-accent state-selected': visibleColumns[column.key],
                      'surface-card border-secondary': !visibleColumns[column.key]
                    }"
                  >
                    <div class="card-body p-3">
                      <div class="form-check">
                        <input 
                          class="form-check-input" 
                          type="checkbox" 
                          :id="`col-${column.key}`"
                          v-model="visibleColumns[column.key]"
                          @change="updateColumnVisibility"
                        />
                        <label class="form-check-label d-flex flex-column" :for="`col-${column.key}`">
                          <span class="fw-semibold text-primary">{{ column.name }}</span>
                          <small class="text-tertiary-medium">{{ column.description }}</small>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Summary -->
          <div class="mt-4 pt-4 divider-theme">
            <div class="card border-accent surface-tertiary">
              <div class="card-body">
                <h6 class="card-title text-accent fw-semibold">Current Selection</h6>
                <p class="text-secondary small mb-3">
                  <strong>{{ visibleColumnCount }}</strong> of {{ totalColumns }} columns visible
                </p>
                <div class="d-flex flex-wrap gap-2">
                  <span 
                    v-for="columnKey in visibleColumnKeys" 
                    :key="columnKey"
                    class="badge bg-primary text-white"
                  >
                    {{ getColumnName(columnKey) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer surface-secondary border-top-theme">
          <button @click="cancelChanges" class="btn btn-cancel">
            Cancel
          </button>
          <button @click="applyChanges" class="btn btn-save">
            Apply Changes
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ColumnFilterModal',
  props: {
    show: {
      type: Boolean,
      default: false
    },
    currentVisibleColumns: {
      type: Object,
      required: true
    }
  },
  emits: ['close', 'apply'],
  data() {
    return {
      visibleColumns: {},
      originalColumns: {},
      
      // Essential columns (always visible)
      essentialColumns: [
        {
          key: 'checkbox',
          name: 'Selection',
          description: 'Select multiple items'
        },
        {
          key: 'productName',
          name: 'Product Name',
          description: 'Primary product identifier'
        },
        {
          key: 'actions',
          name: 'Actions',
          description: 'Edit, view, delete options'
        }
      ],
      
      // Basic information columns
      basicColumns: [
        {
          key: 'sku',
          name: 'SKU',
          description: 'Stock keeping unit code'
        },
        {
          key: 'category',
          name: 'Category',
          description: 'Product category'
        },
        {
          key: 'stock',
          name: 'Stock Level',
          description: 'Current inventory count'
        }
      ],
      
      // Financial information columns
      financialColumns: [
        {
          key: 'costPrice',
          name: 'Cost Price',
          description: 'Purchase cost per unit'
        },
        {
          key: 'sellingPrice',
          name: 'Selling Price',
          description: 'Retail price per unit'
        }
      ],
      
      // Status and date columns
      statusColumns: [
        {
          key: 'status',
          name: 'Status',
          description: 'Active/inactive state'
        },
        {
          key: 'expiryDate',
          name: 'Expiry Date',
          description: 'Product expiration date'
        }
      ]
    }
  },
  computed: {
    allColumns() {
      return [
        ...this.essentialColumns,
        ...this.basicColumns,
        ...this.financialColumns,
        ...this.statusColumns
      ]
    },
    totalColumns() {
      return this.basicColumns.length + this.financialColumns.length + this.statusColumns.length
    },
    visibleColumnCount() {
      return Object.values(this.visibleColumns).filter(visible => visible).length
    },
    visibleColumnKeys() {
      return Object.keys(this.visibleColumns).filter(key => this.visibleColumns[key])
    }
  },
  watch: {
    show(newVal) {
      if (newVal) {
        this.initializeColumns()
        document.body.classList.add('modal-open')
      } else {
        document.body.classList.remove('modal-open')
      }
    },
    currentVisibleColumns: {
      handler() {
        if (this.show) {
          this.initializeColumns()
        }
      },
      deep: true
    }
  },
  methods: {
    handleOverlayClick(e) {
      if (e.target.classList.contains('modal')) {
        this.$emit('close')
      }
    },
    
    initializeColumns() {
      this.visibleColumns = { ...this.currentVisibleColumns }
      this.originalColumns = { ...this.currentVisibleColumns }
    },
    
    updateColumnVisibility() {
      // This method is called when any checkbox changes
    },
    
    selectAll() {
      this.basicColumns.forEach(col => {
        this.visibleColumns[col.key] = true
      })
      this.financialColumns.forEach(col => {
        this.visibleColumns[col.key] = true
      })
      this.statusColumns.forEach(col => {
        this.visibleColumns[col.key] = true
      })
    },
    
    selectNone() {
      this.basicColumns.forEach(col => {
        this.visibleColumns[col.key] = false
      })
      this.financialColumns.forEach(col => {
        this.visibleColumns[col.key] = false
      })
      this.statusColumns.forEach(col => {
        this.visibleColumns[col.key] = false
      })
    },
    
    resetToDefault() {
      const defaultColumns = {
        sku: true,
        category: true,
        stock: true,
        costPrice: false,
        sellingPrice: true,
        status: true,
        expiryDate: true
      }
      
      this.visibleColumns = { ...defaultColumns }
    },
    
    getColumnName(columnKey) {
      const column = this.allColumns.find(col => col.key === columnKey)
      return column ? column.name : columnKey
    },
    
    cancelChanges() {
      this.visibleColumns = { ...this.originalColumns }
      this.$emit('close')
    },
    
    applyChanges() {
      this.$emit('apply', { ...this.visibleColumns })
      this.$emit('close')
    }
  },
  
  mounted() {
    this.handleEscape = (e) => {
      if (e.key === 'Escape' && this.show) {
        this.cancelChanges()
      }
    }
    
    document.addEventListener('keydown', this.handleEscape)
  },

  beforeUnmount() {
    if (this.handleEscape) {
      document.removeEventListener('keydown', this.handleEscape)
    }
    document.body.classList.remove('modal-open')
  }
}
</script>

<style scoped>
/* Override Bootstrap modal background */
.modal {
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

/* Column card hover effects */
.column-card {
  transition: all 0.2s ease;
  cursor: pointer;
}

.column-card:hover {
  border-color: var(--border-accent) !important;
  background-color: var(--surface-elevated) !important;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

/* Close button styling */
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

.btn-close:hover {
  background-color: var(--state-hover);
  color: var(--text-primary);
}

/* Custom form check styling */
.form-check {
  padding-left: 2rem;
}

.form-check-input {
  width: 1.125rem;
  height: 1.125rem;
  margin-top: 0.125rem;
}

.form-check-input:checked {
  background-color: var(--secondary);
  border-color: var(--secondary);
}

.form-check-input:focus {
  border-color: var(--border-accent);
  box-shadow: 0 0 0 0.2rem rgba(160, 123, 227, 0.25);
}

.form-check-label {
  cursor: pointer;
}

/* Badge customization */
.badge {
  font-weight: 500;
  padding: 0.375rem 0.625rem;
}

/* Modal customizations */
.modal-dialog {
  max-width: 800px;
}

.modal-content {
  border: none;
  border-radius: 0.75rem;
  overflow: hidden;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .modal-dialog {
    margin: 0.5rem;
  }
  
  .btn {
    width: 100%;
  }
  
  .modal-footer {
    flex-direction: column-reverse;
    gap: 0.5rem;
  }
  
  .d-flex.gap-3 {
    flex-direction: column;
  }
}

/* Animation for modal appearance */
.modal.show {
  animation: fadeIn 0.3s ease;
}

.modal-dialog {
  animation: slideIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { 
    transform: translate(0, -20px) scale(0.95);
    opacity: 0;
  }
  to { 
    transform: translate(0, 0) scale(1);
    opacity: 1;
  }
}
</style>