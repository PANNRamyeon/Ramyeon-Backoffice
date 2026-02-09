<template>
  <div class="container-fluid pt-2 pb-4 uncategorized-page surface-secondary">
    <!-- Breadcrumb Navigation -->
    <nav aria-label="breadcrumb" class="mb-3">
      <ol class="breadcrumb">
        <li class="breadcrumb-item">
          <router-link to="/inventory" class="text-tertiary-medium">Inventory</router-link>
        </li>
        <li class="breadcrumb-item">
          <router-link to="/categories" class="text-tertiary-medium">Categories</router-link>
        </li>
        <li class="breadcrumb-item active text-primary" aria-current="page">Uncategorized Products</li>
      </ol>
    </nav>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border text-accent" role="status">
        <span class="visually-hidden">Loading uncategorized products...</span>
      </div>
      <p class="mt-2 text-tertiary-medium">Loading uncategorized products...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="status-error" role="alert">
      <strong>Error:</strong> {{ error }}
      <button @click="retryLoad" class="btn btn-sm btn-export ms-2">
        Retry
      </button>
    </div>

    <!-- Main Content -->
    <div v-if="!loading && !error">
      <!-- Page Header -->
      <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
          <h1 class="h2 fw-bold text-primary mb-1">Uncategorized Products</h1>
          <p class="text-tertiary-medium mb-0">Manage products that need to be categorized</p>
        </div>
        <div class="d-flex gap-2">
          <!-- Export button -->
          <button 
            class="btn btn-export btn-sm btn-with-icon-sm" 
            type="button" 
            :disabled="isExporting || uncategorizedProducts.length === 0"
            @click="exportUncategorizedProducts()"
            title="Export uncategorized products as CSV"
          >
            <Download :size="14" />
            {{ isExporting ? 'Exporting...' : `Export (${uncategorizedProducts.length})` }}
          </button>
        </div>
      </div>

      <!-- Summary Card -->
      <div class="row mb-4">
        <div class="col-12">
          <div class="card-theme">
            <div class="card-body">
              <div class="row">
                <div class="col-md-3">
                  <div class="text-center">
                    <div class="h2 fw-bold text-warning mb-1">{{ uncategorizedProducts.length }}</div>
                    <small class="text-tertiary-medium">Total Uncategorized</small>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="text-center">
                    <div class="h2 fw-bold text-info mb-1">{{ selectedProducts.length }}</div>
                    <small class="text-tertiary-medium">Selected</small>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="text-center">
                    <div class="h2 fw-bold text-success mb-1">{{ activeCategories.length }}</div>
                    <small class="text-tertiary-medium">Available Categories</small>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="text-center">
                    <div class="h2 fw-bold text-primary mb-1">₱{{ totalValue.toFixed(2) }}</div>
                    <small class="text-tertiary-medium">Total Value</small>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Bar -->
      <div class="action-bar-container mb-3">
        <div class="action-bar-controls surface-card border-theme">
          <div class="action-row">
            <div class="d-flex align-items-center gap-3 flex-wrap">
              <!-- Bulk Categorization -->
              <div v-if="selectedProducts.length > 0" class="d-flex align-items-center gap-2">
                <span class="text-tertiary-medium">Move {{ selectedProducts.length }} product(s) to:</span>
                <select 
                  class="form-select form-select-sm input-theme" 
                  v-model="bulkTargetCategory"
                  style="min-width: 200px;"
                >
                  <option value="">Choose Category</option>
                  <option 
                    v-for="category in activeCategories" 
                    :key="category._id" 
                    :value="category._id"
                  >
                    {{ category.category_name }}
                  </option>
                </select>
                <select 
                  class="form-select form-select-sm input-theme" 
                  v-model="bulkTargetSubcategory"
                  :disabled="!bulkTargetCategory"
                  style="min-width: 150px;"
                >
                  <option value="">Choose Subcategory</option>
                  <option 
                    v-for="subcategory in getSubcategoriesForCategory(bulkTargetCategory)" 
                    :key="subcategory.name" 
                    :value="subcategory.name"
                  >
                    {{ subcategory.name }}
                  </option>
                </select>
                <button 
                  class="btn btn-success btn-sm"
                  @click="moveSelectedToCategory"
                  :disabled="!bulkTargetCategory || !bulkTargetSubcategory || bulkMoveLoading"
                >
                  <div v-if="bulkMoveLoading" class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">Moving...</span>
                  </div>
                  {{ bulkMoveLoading ? 'Moving...' : 'Move' }}
                </button>
                <button 
                  class="btn btn-cancel btn-sm"
                  @click="clearSelection"
                >
                  Clear
                </button>
              </div>

              <!-- Search -->
              <div class="search-container ms-auto">
                <div class="position-relative">
                  <input 
                    v-model="searchFilter" 
                    type="text" 
                    class="form-control form-control-sm search-input input-theme"
                    placeholder="Search products..."
                    style="min-width: 250px;"
                  />
                  <button 
                    v-if="searchFilter"
                    class="btn btn-sm btn-link position-absolute end-0 top-50 translate-middle-y text-tertiary-medium"
                    @click="searchFilter = ''"
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

      <!-- Products Table -->
      <DataTable
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
                :checked="isAllSelected"
                @change="toggleSelectAll"
                :indeterminate.prop="isIndeterminate"
              />
            </th>
            <th style="width: 120px;">Product ID</th>
            <th>Product Name</th>
            <th style="width: 180px;">Move to Category</th>
            <th style="width: 140px;">Subcategory</th>
            <th style="width: 120px;">Stock</th>
            <th style="width: 120px;">Selling Price</th>
            <th style="width: 120px;">Cost Price</th>
            <th style="width: 100px;">Date Added</th>
          </tr>
        </template>

        <template #body>
          <tr v-for="product in paginatedProducts" :key="product._id">
            <td>
              <input 
                type="checkbox" 
                class="form-check-input" 
                :value="product._id"
                v-model="selectedProducts"
              />
            </td>
            <td>
              <code class="text-tertiary surface-tertiary px-2 py-1 rounded">
                {{ product._id }}
              </code>
            </td>
            <td>
              <div class="fw-medium text-primary">{{ product.product_name }}</div>
            </td>
            <td>
              <select 
                class="form-select form-select-sm input-theme"
                v-model="product.selectedCategory"
                @change="onCategorySelect(product)"
                :disabled="moveProductLoading"
              >
                <option value="">Select Category</option>
                <option 
                  v-for="category in activeCategories" 
                  :key="category._id" 
                  :value="category._id"
                >
                  {{ category.category_name }}
                </option>
              </select>
            </td>
            <td>
              <select 
                class="form-select form-select-sm input-theme"
                v-model="product.selectedSubcategory"
                @change="moveProductToCategory(product._id, product.selectedCategory, product.selectedSubcategory)"
                :disabled="!product.selectedCategory || moveProductLoading"
              >
                <option value="">Select Subcategory</option>
                <option 
                  v-for="subcategory in getSubcategoriesForCategory(product.selectedCategory)" 
                  :key="subcategory.name" 
                  :value="subcategory.name"
                >
                  {{ subcategory.name }}
                </option>
              </select>
            </td>
            <td class="text-center">
              <span :class="getStockClass(product.stock)">
                {{ product.stock || 0 }}
              </span>
            </td>
            <td class="text-end fw-medium text-secondary">
              ₱{{ formatPrice(product.selling_price) }}
            </td>
            <td class="text-end fw-medium text-secondary">
              ₱{{ formatPrice(product.cost_price) }}
            </td>
            <td class="text-secondary">
              {{ formatDate(product.date_created || product.created_at) }}
            </td>
          </tr>
        </template>
      </DataTable>

      <!-- Empty State -->
      <div v-if="filteredProducts.length === 0" class="text-center py-5">
        <div class="card-theme">
          <div class="card-body py-5">
            <Package :size="64" class="text-success mb-3" />
            <h5 class="text-success">All Products Categorized!</h5>
            <p class="text-tertiary-medium mb-3">
              {{ uncategorizedProducts.length === 0 ? 
                'No uncategorized products found. All products have been properly categorized.' :
                'No products match your search criteria.' }}
            </p>
            <router-link to="/categories" class="btn btn-primary btn-with-icon">
              <ArrowLeft :size="16" />
              Back to Categories
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import DataTable from '@/components/common/TableTemplate.vue'
import { useProducts } from '@/composables/api/useProducts'
import { useCategories } from '@/composables/api/useCategories'

export default {
  name: 'UncategorizedProducts',
  components: { DataTable },

  setup() {
    // Composables
    const {
      products: allProducts,
      loading: productsLoading,
      error: productsError,
      fetchProducts,
      moveProductToCategory: moveProduct,
      bulkMoveProductsToCategory,
      moveProductLoading,
      bulkMoveLoading
    } = useProducts()

    const {
      activeCategories,
      loading: categoriesLoading,
      fetchCategories
    } = useCategories()

    // Local state
    const searchFilter = ref('')
    const selectedProducts = ref([])
    const bulkTargetCategory = ref('')
    const bulkTargetSubcategory = ref('')
    const currentPage = ref(1)
    const itemsPerPage = ref(10)
    const isExporting = ref(false)

    // Computed properties
    const loading = computed(() => productsLoading.value || categoriesLoading.value)
    const error = computed(() => productsError.value)

    // ✅ True uncategorized filter
    const uncategorizedProducts = computed(() =>
      allProducts.value
        .filter(p => !p.category_id || p.category_id === 'UNCTGRY-001')
        .map(p => ({
          ...p,
          selectedCategory: '',
          selectedSubcategory: ''
        }))
    )

    const filteredProducts = computed(() => {
      const term = searchFilter.value.trim().toLowerCase()
      if (!term) return uncategorizedProducts.value

      return uncategorizedProducts.value.filter(p =>
        (p.product_name || '').toLowerCase().includes(term) ||
        (p.SKU || '').toLowerCase().includes(term) ||
        (p._id || '').toLowerCase().includes(term) ||
        (p.supplier || '').toLowerCase().includes(term)
      )
    })

    const paginatedProducts = computed(() => {
      const start = (currentPage.value - 1) * itemsPerPage.value
      return filteredProducts.value.slice(start, start + itemsPerPage.value)
    })

    const isAllSelected = computed(() => {
      const ids = paginatedProducts.value.map(p => p._id)
      return ids.length > 0 && ids.every(id => selectedProducts.value.includes(id))
    })

    const isIndeterminate = computed(() => {
      const ids = paginatedProducts.value.map(p => p._id)
      const selectedOnPage = ids.filter(id => selectedProducts.value.includes(id))
      return selectedOnPage.length > 0 && selectedOnPage.length < ids.length
    })

    const totalValue = computed(() =>
      uncategorizedProducts.value.reduce(
        (sum, p) => sum + (parseFloat(p.selling_price) || 0) * (parseInt(p.stock) || 0),
        0
      )
    )

    // Methods
    const getSubcategoriesForCategory = id => {
      const cat = activeCategories.value.find(c => c._id === id)
      return cat?.sub_categories || []
    }

    const onCategorySelect = product => (product.selectedSubcategory = '')

    const moveProductToCategory = async (id, catId, subcat) => {
      if (!catId || !subcat) return
      try {
        await moveProduct(id, catId, subcat)
        selectedProducts.value = selectedProducts.value.filter(pid => pid !== id)
      } catch (err) {
        console.error('Error moving product:', err)
        alert(`Failed to move product: ${err.message}`)
      }
    }

    const moveSelectedToCategory = async () => {
      if (!selectedProducts.value.length || !bulkTargetCategory.value || !bulkTargetSubcategory.value) return
      try {
        await bulkMoveProductsToCategory(selectedProducts.value, bulkTargetCategory.value, bulkTargetSubcategory.value)
        selectedProducts.value = []
        bulkTargetCategory.value = ''
        bulkTargetSubcategory.value = ''
      } catch (err) {
        console.error('Bulk move error:', err)
        alert(`Bulk move failed: ${err.message}`)
      }
    }

    const toggleSelectAll = () => {
      const ids = paginatedProducts.value.map(p => p._id)
      if (isAllSelected.value)
        selectedProducts.value = selectedProducts.value.filter(id => !ids.includes(id))
      else
        selectedProducts.value = [...new Set([...selectedProducts.value, ...ids])]
    }

    const clearSelection = () => {
      selectedProducts.value = []
      bulkTargetCategory.value = ''
      bulkTargetSubcategory.value = ''
    }

    const handlePageChange = page => (currentPage.value = page)

    // ✅ Frontend-only CSV export
    const exportUncategorizedProducts = async () => {
      try {
        isExporting.value = true
        const data = uncategorizedProducts.value
        if (!data.length) {
          alert('No uncategorized products to export.')
          return
        }

        // Build CSV
        const headers = [
          'Product ID', 'Product Name', 'SKU', 'Category ID', 'Subcategory',
          'Stock', 'Cost Price', 'Selling Price', 'Status', 'Created At'
        ]
        const rows = data.map(p => [
          p._id,
          p.product_name,
          p.SKU,
          p.category_id || 'None',
          p.subcategory_name || 'None',
          p.stock ?? p.total_stock ?? 0,
          p.cost_price ?? 0,
          p.selling_price ?? 0,
          p.status ?? 'active',
          p.created_at ?? ''
        ])

        const csvContent = [
          headers.join(','),
          ...rows.map(row =>
            row.map(String).map(v => `"${v.replace(/"/g, '""')}"`).join(',')
          )
        ].join('\n')

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = 'uncategorized_products.csv'
        link.click()
        URL.revokeObjectURL(url)
      } catch (err) {
        console.error('Export failed:', err)
        alert(`Export failed: ${err.message}`)
      } finally {
        isExporting.value = false
      }
    }

    const retryLoad = async () => {
      await Promise.all([fetchProducts(), fetchCategories()])
    }

    const formatPrice = p => parseFloat(p || 0).toFixed(2)
    const formatDate = d => {
      if (!d) return 'N/A'
      const date = new Date(d)
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    }
    const getStockClass = s => {
      if (s === 0) return 'text-error fw-bold'
      if (s <= 15) return 'text-warning fw-semibold'
      return 'text-success fw-medium'
    }

    // Init
    onMounted(async () => {
      await Promise.all([fetchProducts(), fetchCategories()])
    })

    return {
      // state
      loading,
      error,
      uncategorizedProducts,
      activeCategories,
      searchFilter,
      selectedProducts,
      bulkTargetCategory,
      bulkTargetSubcategory,
      currentPage,
      itemsPerPage,
      isExporting,
      moveProductLoading,
      bulkMoveLoading,

      // computed
      filteredProducts,
      paginatedProducts,
      isAllSelected,
      isIndeterminate,
      totalValue,

      // methods
      getSubcategoriesForCategory,
      onCategorySelect,
      moveProductToCategory,
      moveSelectedToCategory,
      toggleSelectAll,
      clearSelection,
      handlePageChange,
      exportUncategorizedProducts,
      retryLoad,
      formatPrice,
      formatDate,
      getStockClass
    }
  }
}
</script>



<style scoped>
.uncategorized-page {
  min-height: 100vh;
}

.action-bar-controls {
  border-radius: 0.75rem;
}

.action-row {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  padding: 1rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.search-input {
  padding-right: 2.5rem;
}

.breadcrumb {
  background: none;
  padding: 0;
  margin: 0;
}

.breadcrumb-item + .breadcrumb-item::before {
  content: ">";
  color: var(--text-tertiary);
}

.breadcrumb-item a {
  text-decoration: none;
}

.breadcrumb-item a:hover {
  text-decoration: underline;
}

.spinner-border-sm {
  width: 0.875rem;
  height: 0.875rem;
}

@media (max-width: 768px) {
  .action-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-container {
    margin-left: 0 !important;
    margin-top: 1rem;
  }
}
</style>