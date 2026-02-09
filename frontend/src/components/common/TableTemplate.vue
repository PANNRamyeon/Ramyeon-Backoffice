<template>
  <div class="table-container">
    <div class="table-responsive">
      <table class="table table-hover data-table">
        <thead class="table-header table-header-sticky">
          <slot name="header"></slot>
        </thead>
        <tbody>
          <slot name="body"></slot>
        </tbody>
      </table>
    </div>
    
    <!-- Pagination section -->
    <div v-if="showPagination && totalPages > 1" class="pagination-container">
      <div class="d-flex justify-content-between align-items-center">
        <div class="pagination-info">
          <small style="color: var(--tertiary-medium);">
            Showing {{ startItem }}-{{ endItem }} of {{ totalItems }} items
          </small>
        </div>
        
        <nav aria-label="Table pagination">
          <ul class="pagination pagination-sm mb-0">
            <li class="page-item" :class="{ disabled: currentPage === 1 }">
              <button 
                class="page-link page-link-icon" 
                @click="previousPage" 
                :disabled="currentPage === 1"
                aria-label="Previous page"
              >
                <ChevronLeft :size="16" />
              </button>
            </li>
            
            <li 
              v-for="page in totalPages" 
              :key="page"
              class="page-item" 
              :class="{ active: page === currentPage }"
            >
              <button class="page-link" @click="goToPage(page)">
                {{ page }}
              </button>
            </li>
            
            <li class="page-item" :class="{ disabled: currentPage === totalPages }">
              <button 
                class="page-link page-link-icon" 
                @click="nextPage" 
                :disabled="currentPage === totalPages"
                aria-label="Next page"
              >
                <ChevronRight :size="16" />
              </button>
            </li>
          </ul>
        </nav>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: 'DataTable',

  props: {
    // Pagination props
    itemsPerPage: {
      type: Number,
      default: 10
    },
    showPagination: {
      type: Boolean,
      default: true
    },
    totalItems: {
      type: Number,
      default: 0
    },
    currentPage: {
      type: Number,
      default: 1
    }
  },
  
  emits: ['page-changed'],
  
  computed: {
    totalPages() {
      return Math.ceil(this.totalItems / this.itemsPerPage)
    },
    startItem() {
      if (this.totalItems === 0) return 0
      return (this.currentPage - 1) * this.itemsPerPage + 1
    },
    endItem() {
      return Math.min(this.currentPage * this.itemsPerPage, this.totalItems)
    }
  },
  
  methods: {
    handleScroll(event) {
      const scrollTop = event.target.scrollTop
      const tableContainer = event.target
      
      if (scrollTop > 0) {
        tableContainer.classList.add('scrolled')
      } else {
        tableContainer.classList.remove('scrolled')
      }
    },

    goToPage(page) {
      if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
        this.$emit('page-changed', page)
      }
    },
    
    previousPage() {
      this.goToPage(this.currentPage - 1)
    },
    
    nextPage() {
      this.goToPage(this.currentPage + 1)
    }
  }
}


</script>

<style scoped>
.table-container {
  background-color: var(--surface-primary);
  border-radius: 0.75rem;
  box-shadow: var(--shadow-lg);
  /* Changed from overflow: hidden to overflow: visible for dropdown */
  overflow: visible;
  border: 1px solid var(--border-secondary);
  position: relative;
  z-index: 1;
  transition: background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

.table-responsive {
  border-radius: 0.75rem 0.75rem 0 0;
  /* Only clip horizontal overflow, allow vertical overflow for dropdown */
  overflow-x: auto;
  overflow-y: visible;
  position: relative;
  max-width: 100%;
}

.data-table {
  margin-bottom: 0;
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
}

/* Header Styling */
.table-header {
  background-color: var(--primary-medium) !important;
  color: var(--text-inverse) !important;
}

.data-table :deep(.table-header th) {
  padding: 1rem;
  font-weight: 600;
  font-size: 0.875rem;
  letter-spacing: 0.025em;
  border: none !important;
  color: var(--text-inverse) !important;
  text-transform: uppercase;
  position: relative;
  background-color: var(--primary-medium) !important;
}

.data-table :deep(.table-header th:first-child) {
  border-top-left-radius: 0.75rem;
}

.data-table :deep(.table-header th:last-child) {
  border-top-right-radius: 0.75rem;
}

/* Body Styling */
.data-table :deep(tbody td) {
  padding: 0.875rem 1rem;
  border-bottom: 1px solid var(--border-secondary);
  font-size: 0.875rem;
  color: var(--text-secondary);
  vertical-align: middle;
  transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

.data-table :deep(tbody tr:last-child td) {
  border-bottom: none;
}

.data-table :deep(tbody tr:hover) {
  background-color: var(--state-hover);
}

.data-table :deep(tbody tr.table-primary) {
  background-color: var(--state-selected);
}

.data-table :deep(tbody tr.text-muted) {
  opacity: 0.6;
}

/* Action Button Base Styles */
.data-table :deep(.action-btn) {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  border-width: 1.5px;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
  padding: 0;
  margin: 0 1px;
  box-shadow: 0 3px 6px 0 rgba(0, 0, 0, 0.12);
}

.data-table :deep(.action-btn:hover) {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.25);
}

.data-table :deep(.action-btn:active) {
  transform: translateY(0);
}

.data-table :deep(.action-btn svg) {
  transition: transform 0.2s ease;
}

.data-table :deep(.action-btn:hover svg) {
  transform: scale(1.1);
}

/* Action Button Color Overrides */
.data-table :deep(.action-btn-edit) {
  --bs-btn-color: var(--secondary);
  --bs-btn-border-color: var(--secondary);
  --bs-btn-hover-color: var(--secondary-dark);
  --bs-btn-hover-bg: var(--secondary-light);
  --bs-btn-hover-border-color: var(--secondary-dark);
  --bs-btn-active-color: var(--secondary-dark);
  --bs-btn-active-bg: var(--secondary-medium);
  --bs-btn-active-border-color: var(--secondary-dark);
}

.data-table :deep(.action-btn-view) {
  --bs-btn-color: var(--primary);
  --bs-btn-border-color: var(--primary);
  --bs-btn-hover-color: var(--primary-dark);
  --bs-btn-hover-bg: var(--primary-light);
  --bs-btn-hover-border-color: var(--primary-dark);
  --bs-btn-active-color: var(--primary-dark);
  --bs-btn-active-bg: var(--primary-medium);
  --bs-btn-active-border-color: var(--primary-dark);
}

.data-table :deep(.action-btn-stock) {
  --bs-btn-color: var(--info);
  --bs-btn-border-color: var(--info);
  --bs-btn-hover-color: var(--info-dark);
  --bs-btn-hover-bg: var(--info-light);
  --bs-btn-hover-border-color: var(--info-dark);
  --bs-btn-active-color: var(--info-dark);
  --bs-btn-active-bg: var(--info-medium);
  --bs-btn-active-border-color: var(--info-dark);
}

.data-table :deep(.action-btn-status) {
  --bs-btn-color: var(--success);
  --bs-btn-border-color: var(--success);
  --bs-btn-hover-color: var(--success-dark);
  --bs-btn-hover-bg: var(--success-light);
  --bs-btn-hover-border-color: var(--success-dark);
  --bs-btn-active-color: var(--success-dark);
  --bs-btn-active-bg: var(--success-medium);
  --bs-btn-active-border-color: var(--success-dark);
}

.data-table :deep(.action-btn-status-inactive) {
  --bs-btn-color: var(--tertiary-medium);
  --bs-btn-border-color: var(--tertiary-medium);
  --bs-btn-hover-color: var(--tertiary-dark);
  --bs-btn-hover-bg: var(--neutral-medium);
  --bs-btn-hover-border-color: var(--tertiary-dark);
  --bs-btn-active-color: var(--tertiary-dark);
  --bs-btn-active-bg: var(--neutral-dark);
  --bs-btn-active-border-color: var(--tertiary-dark);
}

.data-table :deep(.action-btn-delete) {
  --bs-btn-color: var(--error);
  --bs-btn-border-color: var(--error);
  --bs-btn-hover-color: var(--error-dark);
  --bs-btn-hover-bg: var(--error-light);
  --bs-btn-hover-border-color: var(--error-dark);
  --bs-btn-active-color: var(--error-dark);
  --bs-btn-active-bg: var(--error-medium);
  --bs-btn-active-border-color: var(--error-dark);
}

/* Additional action button variants */
.data-table :deep(.action-btn-duplicate) {
  --bs-btn-color: var(--secondary-medium);
  --bs-btn-border-color: var(--secondary-medium);
  --bs-btn-hover-color: var(--secondary-dark);
  --bs-btn-hover-bg: var(--secondary-light);
  --bs-btn-hover-border-color: var(--secondary-dark);
}

.data-table :deep(.action-btn-archive) {
  --bs-btn-color: var(--neutral-dark);
  --bs-btn-border-color: var(--neutral-dark);
  --bs-btn-hover-color: var(--tertiary-dark);
  --bs-btn-hover-bg: var(--neutral-medium);
  --bs-btn-hover-border-color: var(--tertiary-dark);
}

.data-table :deep(.action-btn-restore) {
  --bs-btn-color: var(--success-medium);
  --bs-btn-border-color: var(--success-medium);
  --bs-btn-hover-color: var(--success-dark);
  --bs-btn-hover-bg: var(--success-light);
  --bs-btn-hover-border-color: var(--success-dark);
}

.data-table :deep(.action-btn-download) {
  --bs-btn-color: var(--info-medium);
  --bs-btn-border-color: var(--info-medium);
  --bs-btn-hover-color: var(--info-dark);
  --bs-btn-hover-bg: var(--info-light);
  --bs-btn-hover-border-color: var(--info-dark);
}

/* Badge and Status Styling */
.data-table :deep(.badge) {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.375rem 0.75rem;
}

.data-table :deep(.text-tertiary-dark) {
  color: var(--tertiary-dark) !important;
}

.data-table :deep(.text-tertiary-medium) {
  color: var(--tertiary-medium) !important;
}

.data-table :deep(.text-primary-dark) {
  color: var(--primary-dark) !important;
}

/* Pagination Container with Shadow */
.pagination-container {
  padding: 1rem;
  border-top: 1px solid var(--border-secondary);
  background-color: var(--surface-secondary);
  box-shadow: inset 0 2px 4px 0 var(--shadow-sm);
  border-radius: 0 0 0.75rem 0.75rem;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.pagination-info {
  font-size: 0.875rem;
}

.pagination .page-link {
  color: var(--text-accent);
  border-color: var(--border-primary);
  padding: 0.375rem 0.75rem;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
  background-color: var(--surface-primary);
}

.pagination .page-link:hover {
  color: var(--text-accent);
  background-color: var(--state-hover);
  border-color: var(--border-accent);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.pagination .page-item.active .page-link {
  background-color: var(--primary);
  border-color: var(--primary);
  color: var(--text-inverse);
  box-shadow: var(--shadow-lg);
}

.pagination .page-item.disabled .page-link {
  color: var(--text-disabled);
  background-color: var(--surface-tertiary);
  border-color: var(--border-secondary);
  box-shadow: none;
}

.page-link-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.5rem;
  min-width: 32px;
}

.page-link-icon:hover:not(:disabled) {
  transform: translateY(-2px) translateX(1px);
}

.page-item.disabled .page-link-icon {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-link-icon svg {
  transition: transform 0.2s ease;
}

/* Sticky Header */
.table-header-sticky {
  position: sticky;
  top: 0;
  z-index: 10; /* Lower than dropdown but above table content */
  background-color: var(--primary-medium) !important;
  box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.15);
}

.table-header-sticky th {
  position: relative;
  background-color: var(--primary-medium) !important;
}

/* Add shadow when scrolling for better visual separation */
.table-header-sticky::after {
  content: '';
  position: absolute;
  bottom: -3px;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.15), transparent);
  opacity: 0;
  transition: opacity 0.2s ease;
}

/* Enhanced scroll shadow effect */
.table-responsive.scrolled .table-header-sticky::after {
  opacity: 1;
}

/* Checkbox Styling */
.data-table :deep(.form-check-input) {
  border-width: 2px !important;
  border-color: var(--border-primary) !important;
  background-color: var(--surface-primary);
  width: 1.1em;
  height: 1.1em;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.data-table :deep(.form-check-input:hover) {
  border-color: var(--border-accent) !important;
  box-shadow: var(--shadow-md);
}

.data-table :deep(.form-check-input:focus) {
  border-color: var(--border-accent) !important;
  box-shadow: 0 0 0 3px rgba(160, 123, 227, 0.25) !important;
}

.data-table :deep(.form-check-input:checked) {
  background-color: var(--primary) !important;
  border-color: var(--primary) !important;
  border-width: 2px !important;
  box-shadow: var(--shadow-md);
}

.data-table :deep(.form-check-input:indeterminate) {
  background-color: var(--primary) !important;
  border-color: var(--primary) !important;
  border-width: 2px !important;
  box-shadow: var(--shadow-md);
}

/* Responsive Design */
@media (max-width: 1024px) {
  .table-responsive {
    border-radius: 0.75rem 0.75rem 0 0;
  }
  
  .data-table {
    min-width: 1000px;
  }
}

@media (max-width: 768px) {
  .data-table :deep(th),
  .data-table :deep(td) {
    padding: 0.75rem 0.5rem;
    font-size: 0.8125rem;
  }
  
  .data-table :deep(.action-btn) {
    width: 22px;
    height: 22px;
    margin: 0;
  }
  
  .data-table :deep(.action-btn svg) {
    width: 12px;
    height: 12px;
  }
}

@media (max-width: 576px) {
  .data-table :deep(.action-btn) {
    width: 20px;
    height: 20px;
  }
  
  .data-table :deep(.action-btn svg) {
    width: 10px;
    height: 10px;
  }
}

/* Reduced Motion Preferences */
@media (prefers-reduced-motion: reduce) {
  .data-table :deep(.action-btn),
  .pagination .page-link,
  .page-link-icon,
  .data-table :deep(.action-btn svg),
  .page-link-icon svg {
    transition: none !important;
  }
  
  .data-table :deep(.action-btn:hover),
  .pagination .page-link:hover,
  .page-link-icon:hover {
    transform: none !important;
  }
}

</style>