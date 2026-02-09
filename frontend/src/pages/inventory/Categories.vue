<template>
  <div class="container-fluid pt-2 pb-4 categories-page surface-secondary">
    <!-- Page Title and Uncategorized Link -->
    <div class="d-flex justify-content-between align-items-start mb-3">
      <div>
        <h1 class="h3 fw-semibold text-primary mb-0">Category Management</h1>
      </div>
      <div>
        <router-link 
          to="/uncategorized" 
          class="btn btn-filter btn-sm btn-with-icon-sm"
        >
          <Package :size="14" class="me-1" />
          Uncategorized ({{ uncategorizedCount }})
        </router-link>
      </div>
    </div>

    <!-- Action Bar and Filters -->
    <div class="action-bar-container mb-3">
      <div class="action-bar-controls surface-card border-theme">
        <div class="action-row">
          <!-- Left Side: Main Actions -->
          <div class="d-flex gap-2">
            <button 
              class="btn btn-add btn-sm btn-with-icon-sm"
              @click="handleAddCategory"
              :disabled="loading"
            >
              <Plus :size="14" />
              ADD CATEGORY
            </button>
            
            <button 
              class="btn btn-export btn-sm btn-with-icon-sm"
              @click="handleExport" 
              :disabled="loading || filteredCategories.length === 0"
            >
              <FileDown :size="14" />
              EXPORT
            </button>
          </div>

          <!-- Right Side: Filters and Search -->
          <div class="d-flex align-items-center gap-2">
            <button 
              class="btn btn-filter btn-sm"
              @click="handleToggleSearchMode"
              :class="{ 'state-active': searchMode }"
              style="height: calc(1.5em + 0.75rem + 2px); display: flex; align-items: center; justify-content: center; padding: 0 0.75rem;"
            >
              <Search :size="16" />
            </button>

            <!-- Filter Dropdowns -->
            <template v-if="!searchMode">
              <div class="filter-dropdown">
                <label class="filter-label text-tertiary-medium">Status</label>
                <select 
                  class="form-select form-select-sm input-theme" 
                  v-model="filters.status" 
                  @change="applyFilters"
                >
                  <option value="">All categories</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            </template>

            <!-- Search Bar -->
            <div v-if="searchMode" class="search-container">
              <div class="position-relative">
                <input 
                  ref="searchInput"
                  v-model="filters.search" 
                  @input="handleSearchInput"
                  type="text" 
                  class="form-control form-control-sm search-input input-theme"
                  placeholder="Search categories..."
                />
                <button 
                  class="btn btn-sm btn-link position-absolute end-0 top-50 translate-middle-y text-tertiary-medium"
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

    <!-- Loading State -->
    <div v-if="loading && categories.length === 0" class="text-center py-4">
      <div class="spinner-border text-accent" role="status">
        <span class="visually-hidden">Loading categories...</span>
      </div>
      <p class="mt-2 text-tertiary-medium">Loading categories...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="status-error" role="alert">
      <strong>Error:</strong> {{ error }}
      <button @click="refreshCategories" class="btn btn-sm btn-export ms-2">
        Retry
      </button>
    </div>

    <!-- Category Cards Section -->
    <div v-if="!loading && !error" class="row g-3 mb-4">
      <div 
        v-for="category in displayedCategories" 
        :key="category._id"
        class="col-6 col-md-3"
      >
        <CardTemplate
          class="category-card"
          :class="{ 'category-card--inactive': isCategoryInactive(category) }"
          size="md"
          :border-color="getCategoryBorderColor(category)"
          border-position="start"
          :title="category.category_name"
          :subtitle="getCategorySubtitle(category)"
          shadow="sm"
          clickable
        >
          <template #content>
            <div 
              v-if="isCategoryInactive(category)" 
              class="category-status-chip"
              aria-label="Category inactive"
            >
              <AlertTriangle :size="12" />
              Inactive
            </div>
            <div class="category-card-content">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                  <div class="text-primary fw-bold h5 mb-1">
                    {{ getProductCount(category) }}
                  </div>
                  <small class="text-tertiary-medium">Products</small>
                </div>
                <div class="category-icon surface-primary-light rounded-circle p-2">
                  <Package :size="20" class="text-status-primary" />
                </div>
              </div>
            </div>

            <!-- Action buttons -->
            <div class="d-flex gap-1 mt-2 category-card-actions">
              <button 
                class="btn btn-view btn-sm"
                @click.stop="viewCategory(category._id)"
                :disabled="loading"
              >
                <Eye :size="14" />
                View
              </button>
              <button 
                class="btn btn-delete btn-sm"
                @click.stop="handleDeleteCategory(category)"
                :disabled="loading || deleteLoading"
              >
                <Trash2 :size="14" />
                Delete
              </button>
            </div>
          </template>
        </CardTemplate>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && !error && displayedCategories.length === 0" class="text-center py-5">
      <Package :size="64" class="text-tertiary-medium mb-3" />
      <h5 class="text-tertiary-dark">No categories found</h5>
      <p class="text-tertiary-medium mb-3">
        {{ hasCategories ? 'No categories match your current filters.' : 'Get started by creating your first category.' }}
      </p>
      <button 
        v-if="!hasCategories"
        class="btn btn-add"
        @click="handleAddCategory"
      >
        <Plus :size="16" class="me-1" />
        Add First Category
      </button>
      <button 
        v-else
        class="btn btn-filter"
        @click="handleClearFilters"
      >
        Clear Filters
      </button>
    </div>

    <!-- Add Category Modal -->
    <AddCategoryModal ref="addCategoryModal" @category-added="onCategoryAdded" />
  </div>
</template>

<script>
import { ref, nextTick, computed } from 'vue'
import CardTemplate from '@/components/common/CardTemplate.vue'
import AddCategoryModal from '@/components/categories/AddCategoryModal.vue'
import { useCategories } from '@/composables/api/useCategories'

export default {
  name: 'Categories',
  components: {
    CardTemplate,
    AddCategoryModal
  },

  setup() {
    const searchInput = ref(null)
    const searchMode = ref(false)
    const uncategorizedCount = ref(0)
    
    // Use the categories composable
    const {
      // State
      categories,
      filteredCategories,
      filters,
      loading,
      deleteLoading,
      error,
      hasCategories,
      categoriesWithProductCounts,
      
      // Methods
      fetchCategories,
      softDeleteCategory,
      exportCategories,
      setFilters,
      resetFilters,
      clearError,
      initializeCategories
    } = useCategories()

    // Filter out uncategorized category from display
    const displayedCategories = computed(() => {
      return filteredCategories.value.filter(category => {
        // Filter out categories with names like "Uncategorized" or IDs starting with "UNCTGRY-"
        return !(
          category._id?.startsWith('UNCTGRY-') ||
          category.category_name?.toLowerCase() === 'uncategorized'
        )
      })
    })

    // Count uncategorized products
    const getUncategorizedCount = () => {
      const uncategorizedCategory = categories.value.find(category => 
        category._id?.startsWith('UNCTGRY-') || 
        category.category_name?.toLowerCase() === 'uncategorized'
      )
      
      if (uncategorizedCategory) {
        return uncategorizedCategory.sub_categories?.reduce((total, sub) => 
          total + (sub.product_count || 0), 0
        ) || 0
      }
      
      return 0
    }

    // Computed properties
    const isCategoryInactive = (category) => category?.status === 'inactive'

    const getCategoryBorderColor = (category) => (
      isCategoryInactive(category) ? 'neutral' : 'primary'
    )

    const getCategorySubtitle = (category) => {
      const subcategoryCount = category.sub_categories?.length || 0
      return `${subcategoryCount} subcategories`
    }

    const getProductCount = (category) => {
      return category.sub_categories?.reduce((total, sub) => 
        total + (sub.product_count || 0), 0
      ) || 0
    }

    // Search mode handling
    const handleToggleSearchMode = async () => {
      searchMode.value = !searchMode.value
      
      if (searchMode.value) {
        await nextTick()
        if (searchInput.value) {
          searchInput.value.focus()
        }
      } else {
        // Clear search when exiting search mode
        setFilters({ search: '' })
      }
    }

    const handleSearchInput = () => {
      // Filters are reactive, so this will automatically trigger filtering
    }

    const clearSearch = () => {
      setFilters({ search: '' })
      searchMode.value = false
    }

    const applyFilters = () => {
      // Filters are reactive in the composable
    }

    const handleClearFilters = () => {
      resetFilters()
      searchMode.value = false
    }

    const refreshCategories = async () => {
      try {
        clearError()
        await fetchCategories()
        // Update uncategorized count after refresh
        uncategorizedCount.value = getUncategorizedCount()
      } catch (error) {
        console.error('Error refreshing categories:', error)
      }
    }

    const fetchUncategorizedCount = async () => {
      try {
        // Update the count from current categories
        uncategorizedCount.value = getUncategorizedCount()
      } catch (error) {
        console.error('Error fetching uncategorized count:', error)
        uncategorizedCount.value = 0
      }
    }

    return {
      // Refs
      searchInput,
      searchMode,
      uncategorizedCount,
      
      // State from composable
      categories,
      filteredCategories,
      displayedCategories, // Use this instead of filteredCategories
      filters,
      loading,
      deleteLoading,
      error,
      hasCategories,
      categoriesWithProductCounts,
      
      // Methods from composable
      fetchCategories,
      softDeleteCategory,
      exportCategories,
      setFilters,
      resetFilters,
      clearError,
      initializeCategories,
      
      // Local computed
      getCategorySubtitle,
      getProductCount,
      isCategoryInactive,
      getCategoryBorderColor,
      getUncategorizedCount,
      
      // Local methods
      handleToggleSearchMode,
      handleSearchInput,
      clearSearch,
      applyFilters,
      handleClearFilters,
      refreshCategories,
      fetchUncategorizedCount
    }
  },

  async mounted() {
    try {
      await this.initializeCategories()
      await this.fetchUncategorizedCount()
    } catch (error) {
      console.error('Error initializing categories page:', error)
    }
  },

  methods: {
    // Modal handlers - keeping these untouched as requested
    async handleAddCategory() {
      if (this.$refs.addCategoryModal) {
        this.$refs.addCategoryModal.openAddMode()
      } else {
        console.error('AddCategoryModal ref not found')
      }
    },

    async onCategoryAdded(newCategory) {
      try {
        await this.refreshCategories()
      } catch (error) {
        console.error('Error refreshing categories after add:', error)
      }
    },

    // Navigation
    viewCategory(categoryId) {
      if (!categoryId || !categoryId.startsWith('CTGY-')) {
        console.error('Invalid category ID format:', categoryId)
        alert(`Invalid category ID format: ${categoryId}. Expected CTGY-XXX format.`)
        return
      }
      
      this.$router.push({
        name: 'Category Details', 
        params: { id: categoryId }
      })
    },

    // Delete handler
    async handleDeleteCategory(category) {
      try {
        const confirmed = confirm(
          `Are you sure you want to delete "${category.category_name}"?\n\n` +
          `This will move the category to trash. Products will be moved to Uncategorized.`
        )
        
        if (!confirmed) return

        await this.softDeleteCategory(category._id)
        
        // Refresh uncategorized count since products might be moved there
        await this.fetchUncategorizedCount()
        
      } catch (error) {
        console.error('Error deleting category:', error)
      }
    },

    // Export handler
    async handleExport() {
      try {
        // Export only the displayed categories (excluding uncategorized)
        await this.exportCategories(this.displayedCategories)
      } catch (error) {
        console.error('Export failed:', error)
        alert('Export failed. Please try again.')
      }
    }
  }
}
</script>

<style scoped>
.categories-page {
  min-height: 100vh;
}

.action-bar-controls {
  border-radius: 0.75rem;
}

.action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.filter-dropdown {
  min-width: 120px;
}

.filter-label {
  font-size: 0.75rem;
  font-weight: 500;
  margin-bottom: 0.25rem;
  display: block;
}

.search-container {
  min-width: 300px;
}

.search-input {
  padding-right: 2.5rem;
  height: calc(1.5em + 0.75rem + 2px);
}

.search-container .position-relative .btn {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.category-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
}

.category-card {
  position: relative;
  overflow: hidden;
}

.category-card-content,
.category-card-actions {
  position: relative;
  z-index: 1;
}

.category-card--inactive .category-card-content {
  filter: grayscale(1);
  opacity: 0.55;
}

.category-card--inactive .category-card-actions {
  filter: none;
  opacity: 1;
}

.category-card--inactive .category-icon {
  background-color: rgba(130, 130, 130, 0.18);
}

.category-status-chip {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.6rem;
  font-size: 0.7rem;
  font-weight: 600;
  border-radius: 999px;
  background-color: rgba(110, 110, 110, 0.18);
  color: var(--text-secondary, #5f5f5f);
  border: 1px solid rgba(110, 110, 110, 0.35);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.state-active {
  background-color: var(--state-selected) !important;
  color: var(--text-accent) !important;
}

@media (max-width: 768px) {
  .action-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-container {
    min-width: 100%;
  }
  
  .col-6 {
    flex: 0 0 100%;
    max-width: 100%;
  }
}

@media (max-width: 576px) {
  .categories-page {
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
  }
}
</style>