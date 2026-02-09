<template>
  <div class="container-fluid pt-2 pb-4 products-page surface-secondary">
    <!-- Reports Section -->
    <div class="row mb-3" v-if="!loading">
      <div class="col-6 col-md-3 mb-2">
        <CardTemplate
          size="xs"
          border-color="error"
          border-position="start"
          title="Low Stock"
          :value="productStats.lowStock"
          subtitle="Critical Items"
        />
      </div>
      <div class="col-6 col-md-3 mb-2">
        <CardTemplate
          size="xs"
          border-color="info"
          border-position="start"
          title="Expiring"
          :value="expiringCount"
          subtitle="30 Days"
        />
      </div>
      <div class="col-6 col-md-3 mb-2">
        <CardTemplate
          size="xs"
          border-color="success"
          border-position="start"
          title="Total"
          :value="productStats.total"
          subtitle="Products"
        />
      </div>
      <div class="col-6 col-md-3 mb-2">
        <CardTemplate
          size="xs"
          border-color="accent"
          border-position="start"
          title="Categories"
          :value="totalActiveCategories"
          subtitle="Total"
          :loading="categoriesLoading"
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !hasProducts" class="text-center py-5">
      <div class="spinner-border text-accent" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="mt-3 text-tertiary-medium">Loading products...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="status-error text-center" role="alert">
      <p class="mb-3">{{ error }}</p>
      <button class="btn btn-submit" @click="handleRefresh">Try Again</button>
    </div>

    <!-- Action Bar and Filters -->
    <div v-if="!loading || hasProducts" class="action-bar-container mb-3">
      <div class="action-bar-controls surface-card border-theme">
        <div class="action-row">
          <!-- Left Side: Main Actions -->
          <div v-if="selectedProductIds.length === 0" class="d-flex gap-2">
            <!-- Add Products Dropdown -->
            <div class="dropdown dropdown-container" ref="addDropdown">
              <button 
                class="btn btn-add btn-sm btn-with-icon-sm dropdown-toggle"
                type="button"
                @click="toggleAddDropdown"
                :class="{ 'active': showAddDropdown }"
              >
                <Plus :size="14" />
                ADD ITEM
              </button>
              
              <div 
                class="dropdown-menu add-dropdown-menu" 
                :class="{ 'show': showAddDropdown }"
              >
                <button class="dropdown-item" @click="handleSingleProduct">
                  <div class="d-flex align-items-center gap-3">
                    <Plus :size="16" class="text-accent" />
                    <div>
                      <div class="fw-semibold">Single Product</div>
                      <small class="text-tertiary-medium">Add one product manually</small>
                    </div>
                  </div>
                </button>
                
                
                <button class="dropdown-item" @click="handleImport">
                  <div class="d-flex align-items-center gap-3">
                    <FileText :size="16" class="text-accent" />
                    <div>
                      <div class="fw-semibold">Import File</div>
                      <small class="text-tertiary-medium">Upload CSV/Excel (20+ items)</small>
                    </div>
                  </div>
                </button>
              </div>
            </div>

            <button class="btn btn-filter btn-sm btn-with-icon-sm" @click="toggleColumnFilter">
              <Settings :size="14" />
              COLUMNS
            </button>
            <button 
              class="btn btn-export btn-sm" 
              @click="handleExport"
              :disabled="filteredProducts.length === 0 || exportLoading"
            >
              {{ exportLoading ? 'EXPORTING...' : 'EXPORT' }}
            </button>
          </div>

          <!-- Selection Actions -->
          <div v-if="selectedProductIds.length > 0" class="d-flex gap-2">
            <button 
              class="btn btn-delete btn-sm btn-with-icon-sm"
              @click="handleDeleteSelected"
              :disabled="bulkDeleteLoading"
            >
              <Trash2 :size="14" />
              {{ bulkDeleteLoading ? 'DELETING...' : `DELETE (${selectedProductIds.length})` }}
            </button>
          </div>

          <!-- Right Side: Filters and Search -->
          <div class="d-flex align-items-center gap-2">
            <!-- Search Toggle -->
            <button 
              class="btn btn-filter btn-sm search-toggle"
              @click="toggleSearchMode"
              :class="{ 'state-active': searchMode }"
            >
              <Search :size="16" />
            </button>

            <!-- Filter Dropdowns -->
            <template v-if="!searchMode">
              <div class="filter-dropdown">
                <label class="filter-label text-tertiary-medium">Category</label>
                <select 
                  class="form-select form-select-sm input-theme" 
                  :value="filters.category_id" 
                  @change="handleCategoryFilter"
                >
                  <option value="">All items</option>
                  <option 
                    v-for="category in activeCategories" 
                    :key="category._id" 
                    :value="category._id"
                  >
                    {{ category.category_name }}
                  </option>
                </select>
              </div>

              <div class="filter-dropdown">
                <label class="filter-label text-tertiary-medium">Stock alert</label>
                <select 
                  class="form-select form-select-sm input-theme" 
                  :value="filters.stock_level" 
                  @change="handleStockFilter"
                >
                  <option value="">All items</option>
                  <option value="low_stock">Low Stock</option>
                  <option value="out_of_stock">Out of Stock</option>
                </select>
              </div>
            </template>

            <!-- Search Bar -->
            <div v-if="searchMode" class="search-container">
              <div class="position-relative">
                <input 
                  ref="searchInput"
                  :value="filters.search" 
                  @input="handleSearchInput"
                  type="text" 
                  class="form-control form-control-sm search-input input-theme"
                  placeholder="Search products..."
                />
                <button 
                  class="btn btn-sm btn-link position-absolute end-0 top-50 translate-middle-y text-tertiary-medium"
                  @click="handleClearSearch"
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

    <!-- Data Table -->
    <div class="table-wrapper">
      <DataTable
        v-if="!loading || hasProducts"
        :total-items="filteredProducts.length"
        :current-page="currentPage"
        :items-per-page="itemsPerPage"
        @page-changed="handlePageChange"
      >
        <template #header>
          <tr>
            <th style="width: 40px;">
              <input 
                type="checkbox" 
                class="form-check-input" 
                @change="handleSelectAll" 
                :checked="allSelected"
                :indeterminate.prop="someSelected"
              />
            </th>
            <th>
              Item name 
              <ChevronUp :size="14" class="ms-1" />
            </th>
            <th v-if="isColumnVisible('sku')" style="width: 200px;">SKU</th>
            <th v-if="isColumnVisible('category')" style="width: 160px;">Category</th>
            <th v-if="isColumnVisible('sellingPrice')" style="width: 120px; text-align: right;">Selling Price</th>
            <th v-if="isColumnVisible('costPrice')" style="width: 120px; text-align: right;">Cost Price</th>
            <th style="width: 80px;">Margin</th>
            <th v-if="isColumnVisible('stock')" style="width: 100px;">In stock</th>
            <th v-if="isColumnVisible('status')" style="width: 100px;">Status</th>
            <th v-if="isColumnVisible('expiryDate')" style="width: 130px;">Expiry Date</th>
            <th style="width: 160px;">Actions</th>
          </tr>
        </template>

        <template #body>
          <tr 
            v-for="product in paginatedProducts"
            :key="product._id"
            :class="getRowClass(product)"
          >
            <td>
              <input 
                type="checkbox" 
                class="form-check-input"
                :value="product._id"
                :checked="selectedProductIds.includes(product._id)"
                @change="handleProductSelect(product._id, $event.target.checked)"
              />
            </td>
            <td>
              <div :class="['fw-medium', getProductNameClass(product)]">
                {{ product.product_name }}
              </div>
            </td>
            <td v-if="isColumnVisible('sku')" class="text-left">
              <code class="text-primary surface-tertiary px-2 py-1 rounded">
                {{ product.SKU || '—' }}
              </code>
            </td>
            <td v-if="isColumnVisible('category')">
              <span :class="['badge', 'rounded-pill', getCategoryBadgeClass(product.category_id)]">
                {{ getCategoryName(product.category_id) }}
              </span>
            </td>
            <td v-if="isColumnVisible('sellingPrice')" class="text-end fw-medium text-secondary">
              ₱{{ formatPrice(product.selling_price) }}
            </td>
            <td v-if="isColumnVisible('costPrice')" class="text-end fw-medium text-secondary">
              ₱{{ formatPrice(getProductCostPrice(product)) }}
            </td>
            <td class="text-center fw-medium">
              <span :class="getMarginClass(getProductCostPrice(product), product.selling_price)">
                {{ calculateMargin(getProductCostPrice(product), product.selling_price) }}%
              </span>
            </td>
            <td v-if="isColumnVisible('stock')" class="text-end">
              <span :class="getStockDisplayClass(product)">
                {{ getProductStock(product) || '—' }}
              </span>
            </td>
            <td v-if="isColumnVisible('status')" class="text-center">
              <span :class="getStatusBadgeClass(product.status)">
                {{ getStatusText(product.status) }}
              </span>
            </td>
            <td v-if="isColumnVisible('expiryDate')" class="text-center">
              <small :class="getExpiryDateClass(getProductExpiryDate(product))">
                {{ formatExpiryDate(getProductExpiryDate(product)) }}
              </small>
            </td>
            <td>
              <div class="d-flex gap-1 justify-content-center">
                <button 
                  class="btn btn-outline-secondary btn-icon-only btn-xs action-btn action-btn-edit" 
                  @click="editProduct(product)"
                  title="Edit"
                >
                  <Edit :size="12" />
                </button>
                <button 
                  class="btn btn-outline-primary btn-icon-only btn-xs action-btn action-btn-view" 
                  @click="viewProduct(product)"
                  title="View"
                >
                  <Eye :size="12" />
                </button>
                <button 
                  class="btn btn-outline-info btn-icon-only btn-xs action-btn action-btn-stock" 
                  @click="restockProduct(product)"
                  title="Stock"
                >
                  <Package :size="12" />
                </button>
                <button 
                  class="btn btn-outline-danger btn-icon-only btn-xs action-btn action-btn-delete" 
                  @click="handleDeleteProduct(product)"
                  title="Delete"
                  :disabled="deleteLoading"
                >
                  <Trash2 :size="12" />
                </button>
              </div>
            </td>
          </tr>
        </template>
      </DataTable>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && filteredProducts.length === 0 && !error" class="text-center py-5">
      <div class="card-theme">
        <div class="card-body py-5">
          <Package :size="48" class="text-tertiary-medium mb-3" />
          <p class="text-tertiary-medium mb-3">
            {{ !hasProducts ? 'No products found' : 'No products match the current filters' }}
          </p>
          <button 
            v-if="!hasProducts" 
            class="btn btn-add btn-with-icon" 
            @click="handleSingleProduct"
          >
            <Plus :size="16" />
            Add First Product
          </button>
          <button 
            v-else 
            class="btn btn-filter btn-with-icon"
            @click="handleClearFilters"
          >
            <RefreshCw :size="16" />
            Clear Filters
          </button>
        </div>
      </div>
    </div>

    <!-- Modular Components -->
    <AddProductModal
      ref="addProductModal"
      :categories="activeCategories"
      @success="handleProductSuccess"
    />

    <StockUpdateModal
      ref="stockUpdateModal"
      @success="handleStockUpdateSuccess"
    />

    <ViewProductModal
      ref="viewProductModal"
      @edit="editProduct"
      @restock="restockProduct"
      @toggle-status="toggleProductStatus"
      @generate-barcode="generateProductBarcode"
    />

    <ImportModal
      ref="importModal"
      @import-completed="handleImportSuccess"
      @import-failed="handleImportError"
    />

    <ColumnFilterModal
      :show="showColumnFilter"
      :current-visible-columns="visibleColumns"
      @close="showColumnFilter = false"
      @apply="handleColumnChanges"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useProducts } from '@/composables/api/useProducts'
import { useCategories } from '@/composables/api/useCategories'
import AddProductModal from '@/components/products/AddProductModal.vue'
import StockUpdateModal from '@/components/products/StockUpdateModal.vue'
import ViewProductModal from '@/components/products/ViewProductModal.vue'
import DataTable from '@/components/common/TableTemplate.vue'
import CardTemplate from '@/components/common/CardTemplate.vue'
import ImportModal from '@/components/products/ImportModal.vue'
import ColumnFilterModal from '@/components/products/ColumnFilterModal.vue'

export default {
  name: 'Products',
  components: {
    AddProductModal,
    StockUpdateModal,
    ViewProductModal,
    ColumnFilterModal,
    ImportModal,
    DataTable,
    CardTemplate
  },
  
  setup() {
    // Use the products composable
    const {
      products,
      filteredProducts,
      productStats,
      hasProducts,
      filters,
      error,
      loading,
      deleteLoading,
      bulkDeleteLoading,
      exportLoading,
      fetchProducts,
      deleteProduct,
      bulkDeleteProducts,
      updateProduct,
      exportProducts,
      setFilters,
      resetFilters,
      initializeProducts,
      clearError
    } = useProducts()

    // Use categories composable
    const {
      activeCategories,
      totalActiveCategories,
      loading: categoriesLoading,
      initializeCategories
    } = useCategories()

    // Local state for UI
    const searchMode = ref(false)
    const showAddDropdown = ref(false)
    const showColumnFilter = ref(false)
    const selectedProductIds = ref([])
    const currentPage = ref(1)
    const itemsPerPage = ref(20)
    const expiringCount = ref(0)
    const addDropdown = ref(null)
    const searchInput = ref(null)

    // Visible columns state
    const visibleColumns = ref({
      sku: true,
      category: true,
      sellingPrice: true,
      costPrice: true,
      stock: true,
      status: true,
      expiryDate: true
    })

    // Computed properties for pagination and selection
    const paginatedProducts = computed(() => {
      const start = (currentPage.value - 1) * itemsPerPage.value
      const end = start + itemsPerPage.value
      return filteredProducts.value.slice(start, end)
    })

    const allSelected = computed(() => {
      return paginatedProducts.value.length > 0 && 
             paginatedProducts.value.every(p => selectedProductIds.value.includes(p._id))
    })

    const someSelected = computed(() => {
      return selectedProductIds.value.length > 0 && !allSelected.value
    })

    const selectedProducts = computed(() => {
      return products.value.filter(p => selectedProductIds.value.includes(p._id))
    })

    // Calculate expiring products (updated for batch system)
    const calculateExpiringCount = () => {
      const now = new Date()
      const thirtyDaysFromNow = new Date(now.getTime() + (30 * 24 * 60 * 60 * 1000))
      
      expiringCount.value = products.value.filter(product => {
        const expiryDate = getProductExpiryDate(product)
        if (!expiryDate) return false
        const expiry = new Date(expiryDate)
        return expiry <= thirtyDaysFromNow && expiry >= now
      }).length
    }

    // Helper functions for batch-aware data
    const getProductStock = (product) => {
      return product.total_stock ?? product.stock ?? 0
    }

    const getProductCostPrice = (product) => {
      return product.average_cost_price ?? product.cost_price ?? 0
    }

    const getProductExpiryDate = (product) => {
      return product.oldest_batch_expiry ?? product.expiry_date
    }

    // Event handlers
    const handleRefresh = async () => {
      clearError()
      await fetchProducts()
      calculateExpiringCount()
    }

    const handleCategoryFilter = (event) => {
      setFilters({ category_id: event.target.value })
      currentPage.value = 1
    }

    const handleStockFilter = (event) => {
      setFilters({ stock_level: event.target.value })
      currentPage.value = 1
    }

    const handleSearchInput = (event) => {
      setFilters({ search: event.target.value })
      currentPage.value = 1
    }

    const handleClearSearch = () => {
      setFilters({ search: '' })
      searchMode.value = false
    }

    const handleClearFilters = () => {
      resetFilters()
      searchMode.value = false
      currentPage.value = 1
    }

    const handleSelectAll = (event) => {
      if (event.target.checked) {
        selectedProductIds.value = [...new Set([
          ...selectedProductIds.value,
          ...paginatedProducts.value.map(p => p._id)
        ])]
      } else {
        const currentPageIds = paginatedProducts.value.map(p => p._id)
        selectedProductIds.value = selectedProductIds.value.filter(id => !currentPageIds.includes(id))
      }
    }

    const handleProductSelect = (productId, checked) => {
      if (checked) {
        selectedProductIds.value.push(productId)
      } else {
        selectedProductIds.value = selectedProductIds.value.filter(id => id !== productId)
      }
    }

    const handleDeleteProduct = async (product) => {
      if (confirm(`Are you sure you want to delete "${product.product_name}"?`)) {
        try {
          await deleteProduct(product._id)
        } catch (error) {
          console.error('Failed to delete product:', error)
        }
      }
    }

    const handleDeleteSelected = async () => {
      if (confirm(`Are you sure you want to delete ${selectedProductIds.value.length} products?`)) {
        try {
          await bulkDeleteProducts(selectedProductIds.value)
          selectedProductIds.value = []
        } catch (error) {
          console.error('Failed to delete products:', error)
        }
      }
    }

    const handleExport = async () => {
      try {
        await exportProducts(filters.value)
      } catch (error) {
        console.error('Export failed:', error)
      }
    }

    const handlePageChange = (page) => {
      currentPage.value = page
    }

    const toggleSearchMode = async () => {
      searchMode.value = !searchMode.value
      if (searchMode.value) {
        await nextTick()
        if (searchInput.value) {
          searchInput.value.focus()
        }
      }
    }

    const toggleAddDropdown = () => {
      showAddDropdown.value = !showAddDropdown.value
    }

    const closeAddDropdown = () => {
      showAddDropdown.value = false
    }

    const toggleColumnFilter = () => {
      showColumnFilter.value = !showColumnFilter.value
    }

    // Utility functions
    const isColumnVisible = (column) => {
      return visibleColumns.value[column]
    }

    const getRowClass = (product) => {
      const stock = getProductStock(product)
      if (stock === 0) return 'table-danger'
      if (stock <= (product.low_stock_threshold || 15)) return 'table-warning'
      return ''
    }

    const getProductNameClass = (product) => {
      if (product.status === 'inactive') return 'text-tertiary-medium'
      return 'text-primary'
    }

    const getCategoryBadgeClass = (categoryId) => {
      const category = activeCategories.value.find(c => c._id === categoryId)
      if (!category) return 'bg-secondary'
      
      const colors = ['bg-primary', 'bg-info', 'bg-success', 'bg-warning', 'bg-danger']
      const index = categoryId ? categoryId.length % colors.length : 0
      return colors[index]
    }

    const getCategoryName = (categoryId) => {
      if (!categoryId) return 'Uncategorized'
      const category = activeCategories.value.find(c => c._id === categoryId)
      return category?.category_name || 'Unknown'
    }

    const getStockDisplayClass = (product) => {
      const stock = getProductStock(product)
      if (stock === 0) return 'text-error fw-bold'
      if (stock <= (product.low_stock_threshold || 15)) return 'text-warning fw-bold'
      return 'text-success'
    }

    const getStatusBadgeClass = (status) => {
      return status === 'active' ? 'badge bg-success text-white' : 'badge bg-secondary text-white'
    }

    const getStatusText = (status) => {
      return status === 'active' ? 'Active' : 'Inactive'
    }

    const getMarginClass = (cost, selling) => {
      const margin = calculateMargin(cost, selling)
      if (margin >= 40) return 'text-success'
      if (margin >= 20) return 'text-warning'
      return 'text-error'
    }

    const calculateMargin = (cost, selling) => {
      if (!cost || !selling || cost >= selling) return 0
      return Math.round(((selling - cost) / selling) * 100)
    }

    const formatPrice = (price) => {
      return parseFloat(price || 0).toFixed(2)
    }

    const formatExpiryDate = (date) => {
      if (!date) return '—'
      return new Date(date).toLocaleDateString()
    }

    const getExpiryDateClass = (date) => {
      if (!date) return 'text-tertiary-medium'
      const now = new Date()
      const expiry = new Date(date)
      const diffDays = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24))
      
      if (diffDays < 0) return 'text-error'
      if (diffDays <= 30) return 'text-warning'
      return 'text-success'
    }

    const toggleProductStatus = async (product) => {
      try {
        const newStatus = product.status === 'active' ? 'inactive' : 'active'
        await updateProduct(product._id, { status: newStatus })
      } catch (error) {
        console.error('Error toggling product status:', error)
      }
    }

    const generateProductBarcode = async (product) => {
      try {
        const timestamp = Date.now().toString()
        const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0')
        const newBarcode = `${timestamp}${random}`

        await updateProduct(product._id, { barcode: newBarcode })
      } catch (error) {
        console.error('Error generating barcode:', error)
      }
    }

    // Click outside handler
    const handleClickOutside = (event) => {
      if (addDropdown.value && !addDropdown.value.contains(event.target)) {
        showAddDropdown.value = false
      }
    }

    // Initialize on mount
    onMounted(async () => {
      document.addEventListener('click', handleClickOutside)
      await Promise.all([
        initializeProducts(),
        initializeCategories()
      ])
      calculateExpiringCount()
    })

    onBeforeUnmount(() => {
      document.removeEventListener('click', handleClickOutside)
    })

    return {
      // Composable state and methods
      products,
      filteredProducts,
      productStats,
      hasProducts,
      filters,
      error,
      loading,
      deleteLoading,
      bulkDeleteLoading,
      exportLoading,
      activeCategories,
      totalActiveCategories,
      categoriesLoading,
      
      // Local state
      searchMode,
      showAddDropdown,
      showColumnFilter,
      selectedProductIds,
      selectedProducts,
      currentPage,
      itemsPerPage,
      expiringCount,
      visibleColumns,
      addDropdown,
      searchInput,
      
      // Computed
      paginatedProducts,
      allSelected,
      someSelected,
      
      // Helper functions
      getProductStock,
      getProductCostPrice,
      getProductExpiryDate,
      
      // Event handlers
      handleRefresh,
      handleCategoryFilter,
      handleStockFilter,
      handleSearchInput,
      handleClearSearch,
      handleClearFilters,
      handleSelectAll,
      handleProductSelect,
      handleDeleteProduct,
      handleDeleteSelected,
      handleExport,
      handlePageChange,
      toggleSearchMode,
      toggleAddDropdown,
      closeAddDropdown,
      toggleColumnFilter,
      
      // Utility functions
      isColumnVisible,
      getRowClass,
      getProductNameClass,
      getCategoryBadgeClass,
      getCategoryName,
      getStockDisplayClass,
      getStatusBadgeClass,
      getStatusText,
      getMarginClass,
      calculateMargin,
      formatPrice,
      formatExpiryDate,
      getExpiryDateClass,
      toggleProductStatus,
      generateProductBarcode
    }
  },

  methods: {
    // Modal methods
    showAddProductModal() {
      this.$refs.addProductModal?.openAdd?.()
    },
    
    editProduct(product) {
      const enrichedProduct = {
        ...product,
        category_id: product.category_id || ''
      }
      
      this.$refs.viewProductModal?.close?.()
      this.$refs.addProductModal?.openEdit?.(enrichedProduct)
    },
    
    viewProduct(product) {
      if (!product || !product._id) {
        console.error('Cannot view product: missing ID')
        return
      }

      try {
        this.$router.push(`/products/${product._id}`)
      } catch (error) {
        console.error('Navigation error:', error)
      }
    },
        
    restockProduct(product) {
      this.$refs.stockUpdateModal?.openStock?.(product)
    },

    handleSingleProduct(event) {
      event?.stopPropagation()
      this.showAddProductModal()
      this.closeAddDropdown()
    },

    handleBulkAdd(event) {
      event?.stopPropagation()
      this.closeAddDropdown()
    },
    
    handleImport(event) {
      event?.stopPropagation()
      
      const importModalElement = document.getElementById('importModal')
      if (importModalElement) {
        try {
          const modal = new bootstrap.Modal(importModalElement)
          modal.show()
        } catch (error) {
          console.error('Error showing modal:', error)
        }
      }
      
      this.closeAddDropdown()
    },

    handleProductSuccess(result) {
      // Item added successfully
    },

    handleStockUpdateSuccess(result) {
      // Stock updated successfully
    },

    handleImportSuccess(result) {
      // Import completed
    },

    handleImportError(error) {
      console.error(`Import failed: ${error.message || 'An unexpected error occurred'}`)
    },

    handleColumnChanges(newColumns) {
      this.visibleColumns = { ...newColumns }
      this.showColumnFilter = false
    }
  }
}
</script>

<style scoped>
.products-page {
  min-height: 100vh;
}

.action-bar-container {
  position: relative;
  z-index: 100;
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

.dropdown-container {
  position: relative;
  z-index: 1050;
}

.add-dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1055;
  min-width: 280px;
  margin-top: 0.25rem;
  background-color: var(--surface-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  box-shadow: var(--shadow-xl);
  animation: dropdownSlide 0.2s ease;
  transform: translateZ(0);
}

.add-dropdown-menu.show {
  display: block;
}

@keyframes dropdownSlide {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.dropdown-item {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-primary);
  background: transparent;
  border-left: none;
  border-right: none;
  border-top: none;
  transition: background-color 0.2s ease;
  cursor: pointer;
  width: 100%;
  text-align: left;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background-color: var(--state-hover);
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

.search-toggle {
  height: calc(1.5em + 0.75rem + 2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 0.75rem;
  margin-top: 5px;
}

.state-active {
  background-color: var(--state-selected) !important;
  color: var(--text-accent) !important;
}

.table-wrapper {
  position: relative;
  z-index: 1;
}

.table-wrapper :deep(.table-container) {
  position: relative;
  z-index: 1;
}

@media (max-width: 768px) {
  .action-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-container {
    min-width: 100%;
  }
  
  .add-dropdown-menu {
    min-width: 250px;
    right: 0;
    left: auto;
  }
  
  .dropdown-item {
    padding: 0.875rem 1rem;
  }
}

/* Make search button + filters perfectly aligned */
.filters-row,
.search-container,
.filter-group {
  display: flex;
  align-items: center !important; /* forces vertical alignment */
}

/* Ensure search button container does not stretch */
.search-container {
  min-width: unset !important;
  width: auto !important;
}

/* Optional: small spacing cleanup */
.filters-row {
  gap: 1rem;
}


</style>