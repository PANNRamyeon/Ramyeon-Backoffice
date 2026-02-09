<!-- components/common/ActionBar.vue -->
<template>
  <div class="action-bar mb-3">
    <div class="action-controls">
      <div class="action-row">
        <!-- Left Side: Main Actions -->
        <div v-if="selectedItems.length === 0" class="d-flex gap-2">
          <!-- Add Items Dropdown -->
          <div class="dropdown dropdown-container" ref="addDropdown">
            <button 
              class="btn btn-add btn-sm btn-with-icon-sm dropdown-toggle"
              type="button"
              @click="toggleAddDropdown"
              :class="{ 'active': showAddDropdown }"
            >
              <Plus :size="14" />
              {{ addButtonText }}
            </button>
            
            <div 
              class="dropdown-menu add-dropdown-menu" 
              :class="{ 'show': showAddDropdown }"
            >
              <button 
                v-for="option in addOptions" 
                :key="option.key"
                class="dropdown-item" 
                @click="handleAddAction(option.key)"
              >
                <div class="d-flex align-items-center gap-3">
                  <component :is="option.icon" :size="16" class="text-accent" />
                  <div>
                    <div class="fw-semibold">{{ option.title }}</div>
                    <small class="text-tertiary">{{ option.description }}</small>
                  </div>
                </div>
              </button>
            </div>
          </div>

          <!-- Additional Action Buttons -->
          <button 
            v-if="showColumnsButton"
            class="btn btn-filter btn-sm" 
            @click="$emit('toggle-columns')"
          >
            <Settings :size="14" class="me-1" />
            COLUMNS
          </button>
          
          <button 
            v-if="showExportButton"
            class="btn btn-export btn-sm" 
            @click="$emit('export')"
            :disabled="exporting"
          >
            <Download :size="14" class="me-1" />
            {{ exporting ? 'EXPORTING...' : 'EXPORT' }}
          </button>
        </div>

        <!-- Selection Actions -->
        <div v-if="selectedItems.length > 0" class="d-flex gap-2">
          <button 
            v-for="action in selectionActions"
            :key="action.key"
            class="btn btn-sm btn-with-icon-sm"
            :class="action.buttonClass"
            @click="handleSelectionAction(action.key)"
          >
            <component :is="action.icon" :size="14" />
            {{ action.label }} ({{ selectedItems.length }})
          </button>
        </div>

        <!-- Right Side: Filters and Search -->
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <!-- Search Toggle -->
          <button 
            class="btn btn-filter btn-sm search-toggle"
            @click="toggleSearchMode"
            :class="{ 'active': searchMode }"
          >
            <Search :size="16" />
          </button>

          <!-- Filter Dropdowns -->
          <template v-if="!searchMode">
            <div 
              v-for="filter in filters" 
              :key="filter.key"
              class="filter-dropdown-wrapper"
            >
              <label class="filter-label">{{ filter.label }}</label>
              <select 
                class="form-select form-select-sm filter-select" 
                :value="filter.value"
                @change="handleFilterChange(filter.key, $event.target.value)"
              >
                <option 
                  v-for="option in filter.options" 
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>
          </template>

          <!-- Search Bar -->
          <div v-if="searchMode" class="search-container">
            <div class="position-relative">
              <input 
                ref="searchInput"
                :value="searchValue"
                @input="handleSearchInput"
                type="text" 
                class="form-control form-control-sm search-input"
                :placeholder="searchPlaceholder"
              />
              <button 
                class="btn btn-sm btn-link position-absolute end-0 top-50 translate-middle-y text-tertiary"
                @click="clearSearch"
                style="border: none; padding: 0.25rem;"
              >
                <X :size="16" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// Props
const props = defineProps({
  // Entity configuration
  entityName: {
    type: String,
    required: true
  },
  addButtonText: {
    type: String,
    default: 'ADD ITEM'
  },
  searchPlaceholder: {
    type: String,
    default: 'Search items...'
  },

  // Add dropdown options
  addOptions: {
    type: Array,
    default: () => []
  },

  // Selection
  selectedItems: {
    type: Array,
    default: () => []
  },
  selectionActions: {
    type: Array,
    default: () => []
  },

  // Filters
  filters: {
    type: Array,
    default: () => []
  },
  searchValue: {
    type: String,
    default: ''
  },

  // Button visibility
  showColumnsButton: {
    type: Boolean,
    default: true
  },
  showExportButton: {
    type: Boolean,
    default: true
  },

  // States
  exporting: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits([
  'add-action',
  'selection-action', 
  'filter-change',
  'search-input',
  'search-clear',
  'toggle-columns',
  'export'
])

// Local state
const showAddDropdown = ref(false)
const searchMode = ref(false)
const searchInput = ref(null)
const addDropdown = ref(null)

// Methods
const toggleAddDropdown = () => {
  showAddDropdown.value = !showAddDropdown.value
}

const handleAddAction = (actionKey) => {
  emit('add-action', actionKey)
  showAddDropdown.value = false
}

const handleSelectionAction = (actionKey) => {
  emit('selection-action', actionKey, props.selectedItems)
}

const handleFilterChange = (filterKey, value) => {
  emit('filter-change', filterKey, value)
}

const toggleSearchMode = () => {
  searchMode.value = !searchMode.value
  if (searchMode.value) {
    setTimeout(() => {
      searchInput.value?.focus()
    }, 100)
  } else {
    emit('search-clear')
  }
}

const handleSearchInput = (event) => {
  emit('search-input', event.target.value)
}

const clearSearch = () => {
  emit('search-clear')
}

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  if (addDropdown.value && !addDropdown.value.contains(event.target)) {
    showAddDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* Action Bar Styles */
.action-bar {
  background-color: var(--surface-primary);
  border: 1px solid var(--border-secondary);
  border-radius: 0.75rem;
  padding: 1rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
}

.action-controls {
  width: 100%;
}

.action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

/* Dropdown Styles */
.dropdown-container {
  position: relative;
}

.dropdown-toggle.active {
  background-color: var(--state-active);
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1050;
  display: none;
  min-width: 280px;
  padding: 0.5rem 0;
  margin: 0.125rem 0 0;
  background-color: var(--surface-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  box-shadow: var(--shadow-lg);
}

.dropdown-menu.show {
  display: block;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 0.75rem 1rem;
  clear: both;
  font-weight: 400;
  color: var(--text-primary);
  text-align: inherit;
  background-color: transparent;
  border: 0;
  transition: all 0.15s ease-in-out;
  cursor: pointer;
}

.dropdown-item:hover {
  background-color: var(--state-hover);
}

/* Filter Styles - FIXED */
.filter-dropdown-wrapper {
  display: inline-flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 140px;
}

.filter-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.025em;
  margin: 0;
  padding: 0 0.25rem;
  line-height: 1;
  white-space: nowrap;
}

.filter-select {
  width: 100%;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1.5;
  border-radius: 0.375rem;
  border: 1px solid var(--border-primary);
  background-color: var(--surface-primary);
  color: var(--text-primary);
  transition: all 0.2s ease;
  cursor: pointer;
}

.filter-select:focus {
  border-color: var(--border-accent);
  outline: 0;
  box-shadow: 0 0 0 0.2rem rgba(160, 123, 227, 0.25);
}

.filter-select:hover {
  border-color: var(--border-accent);
}

/* Search Styles */
.search-toggle {
  flex-shrink: 0;
}

.search-toggle.active {
  background-color: var(--state-selected);
  color: var(--text-accent);
}

.search-container {
  min-width: 250px;
}

.search-input {
  padding-right: 2rem;
  border: 1px solid var(--border-primary);
  background-color: var(--surface-primary);
  color: var(--text-primary);
  transition: all 0.2s ease;
}

.search-input:focus {
  border-color: var(--border-accent);
  box-shadow: 0 0 0 0.2rem rgba(160, 123, 227, 0.25);
}

/* Utility Classes */
.d-flex {
  display: flex !important;
}

.align-items-center {
  align-items: center !important;
}

.flex-wrap {
  flex-wrap: wrap !important;
}

.gap-1 {
  gap: 0.25rem !important;
}

.gap-2 {
  gap: 0.5rem !important;
}

.gap-3 {
  gap: 0.75rem !important;
}

.fw-semibold {
  font-weight: 600 !important;
}

.me-1 {
  margin-right: 0.25rem !important;
}

.position-relative {
  position: relative !important;
}

.position-absolute {
  position: absolute !important;
}

.end-0 {
  right: 0 !important;
}

.top-50 {
  top: 50% !important;
}

.translate-middle-y {
  transform: translateY(-50%) !important;
}

/* Responsive Design */
@media (max-width: 768px) {
  .action-row {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
  
  .search-container {
    min-width: auto;
    width: 100%;
  }
  
  .filter-dropdown-wrapper {
    min-width: 100%;
  }
}

@media (max-width: 576px) {
  .action-bar {
    padding: 0.75rem;
  }
  
  .d-flex.gap-2 {
    flex-wrap: wrap;
  }
  
  .filter-dropdown-wrapper {
    flex: 1 1 auto;
    min-width: 120px;
  }
}
</style>